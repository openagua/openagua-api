import json
from os.path import splitext

from flask import current_app, jsonify, g, request, send_file, make_response
from flask_restx import Resource, fields
from attrdict import AttrDict

from openagua.security import login_required, current_user
from openagua.lib.networks import get_network, update_network_on_mapbox, update_types, get_network_for_export, \
    make_network_thumbnail, save_network_preview, clone_network, move_network, import_from_json, \
    get_network_settings, add_update_network_settings, delete_network_settings
from openagua.lib.sharing import set_resource_permissions, share_resource
from openagua.lib.templates import get_default_types
from openagua.lib.files import delete_all_network_files
from openagua.lib.network_editor import add_link, add_network_reference, update_network_reference, \
    delete_network_references, update_links2, split_link_at_nodes2
from openagua.utils import update_network_model, change_active_template
from openagua.lib.addins.weap_import import import_from_weap

from openagua import socketio

from openagua.apis import api0, api


@api.route('/networks')
class Networks(Resource):

    @api.doc(description='Get multiple networks', params={
        'include_resources': 'Should resources (nodes and links) be included? (boolean)',
        'network_ids': 'Network IDs to get.'
    })
    def get(self):
        include_resources = request.args.get('include_resources', type=bool, default=False)
        network_ids = request.args.getlist('network_ids[]', type=int)
        networks = []
        for network_id in network_ids:
            network = g.conn.call('get_network', network_id, include_resources=include_resources, summary=True,
                                  include_data=False)
            networks.append(network)

        return jsonify(networks=networks)

    @api.doc(description='Add a network.')
    @api.param('purpose',
               'Specify an optional purpose before adding; this will invoke some preprocessing steps. Options include "clone" and "move".')
    def post(self):

        purpose = request.args.get('purpose')
        if purpose == 'import':

            file = request.files['file']

            project_id = request.form.get('project_id', type=int)
            network_name = request.form.get('network_name')
            flavor = request.form.get('flavor')
            # filename = secure_filename(file.filename)
            filename = file.filename
            ext = splitext(file.filename)[-1]

            network = None
            template = None

            if ext in ['.zip', '.weap']:
                # TODO: examine contents of zip file to auto-detect if it is from WEAP
                template_name = 'WaterLP v0.3'  # TODO: get from setting or user input
                network, template = import_from_weap(conn=g.conn, file=file, project_id=project_id,
                                                     template_name=template_name, network_name=network_name)

            elif ext == '.json':
                if flavor == 'json':
                    network, template = import_from_json(conn=g.conn, file=file, project_id=project_id)
                else:
                    network, template = import_from_json(conn=g.conn, file=file, project_id=project_id)

            return jsonify(network=network)

        if purpose == 'clone':
            options = request.json.get('options')
            network_id = request.json.get('network_id')
            network = clone_network(conn=g.conn, network_id=network_id, **options)
            return jsonify(network=network)

        if purpose == 'move':
            source = request.json.get('source')
            destination = request.json.get('destination')
            project_id = request.json.get('project_id')
            network_id = request.json.get('network_id')
            move_network(source=source, destination=destination, project_id=project_id, network_id=network_id)
            return '', 204

        net = request.json.get('network')
        # scen = request.json.get('scenario')
        network = g.conn.call('add_network', net)
        # if scen:
        #     scenario = g.conn.call('add_scenario', network.id, scen)
        #     network['scenarios'] = [scenario]
        # else:
        #     network['scenarios'] = network.get('scenarios', [])
        return jsonify(network=network)


@api.route('/networks/<int:network_id>')
class Network(Resource):

    # TODO: move repair to a completely different route?

    @api.doc(description='Get a network')
    @api.param('simple', 'A basic request')
    @api.param('include_resources', 'Whether or not to include resources in a simple request (nodes & links)')
    @api.param('repair', 'Whether or not to repair the network (if not a simple request)')
    @api.param('repair_options[]', 'A list of options to pass when repairing the network')
    def get(self, network_id):

        simple = request.args.get('simple', False)
        summary = request.args.get('summary', True)
        include_resources = request.args.get('include_resources', True)
        repair = request.args.get('repair', type=bool)
        repair_options = request.args.getlist('repair_options[]')

        network = get_network(
            network_id,
            simple=simple,
            summary=summary,
            include_resources=include_resources,
            repair=repair,
            repair_options=repair_options
        )

        if network is None:
            return '', 511

        elif 'error' in network:
            return make_response(jsonify(network), 403)

        return jsonify(network=network)

    @api.doc(description='Patch a network')
    def patch(self, network_id):

        data = request.json
        layout = data.get('layout', {})

        network = g.conn.call('get_network', network_id, include_data=False, include_resources=False)

        if layout:

            # update template ID
            active_template_id = layout.get('active_template_id')
            if active_template_id != network.layout.get('active_template_id'):
                change_active_template(g.conn, g.study.id, network=network, new_template_id=active_template_id)

            # update model ID
            active_model_id = layout.get('model_id')
            if active_model_id != network.layout.get('model_id'):
                update_network_model(g.conn.url, network_id=network_id, model_id=active_model_id)

            network['layout'].update(layout)

        else:
            network.update(data)

        resp = g.conn.call('update_network', network)

        if 'error' in resp:
            return 'error', 501

        else:
            return '', 204

    def delete(self, network_id):
        network = g.conn.call('get_network', network_id, include_resources=False, include_data=False,
                              summary=True)
        # note that purge_data is required, but not used in the Hydra function
        resp = g.conn.call('delete_network', network_id, True)

        if resp == 'OK':
            bucket_name = current_app.config['AWS_S3_BUCKET']
            delete_all_network_files(network, bucket_name, s3=current_app.s3)
            delete_network_settings(current_user.id, g.dataurl_id, network_id)
            return '', 204
        else:
            return '', 500


@api.route('/networks/<int:network_id>/settings')
class NetworkSettings(Resource):
    @api.doc(description='Get a network''s settings')
    def get(self, network_id):
        settings = get_network_settings(current_user.id, g.dataurl_id, network_id)
        return jsonify(settings)

    @api.doc(description='Add a network''s settings')
    def post(self, network_id):
        settings = request.json
        add_update_network_settings(current_user.id, g.dataurl_id, network_id, settings)
        return '', 204

    @api.doc(description='Update a network''s settings')
    def put(self, network_id):
        settings = request.json
        add_update_network_settings(current_user.id, g.dataurl_id, network_id, settings)
        return '', 204


@api.route('/networks/<int:network_id>/download')
class NetworkDownload(Resource):
    @api.doc(description='Get a network and optional associated data for download')
    @api.param('format', 'Download format')
    @api.param('options', 'A stringified object of options to pass when downloading the network')
    def get(self, network_id):
        options = json.loads(request.args.get('options', ''))
        file_format = request.args.get('format', 'json')

        if file_format in ['zip', 'xlsx', 'shapefile']:
            filename, file_buffer = get_network_for_export(g.conn, network_id, options, file_format)
            return send_file(file_buffer, as_attachment=True, attachment_filename=filename)

        elif file_format:
            filename, content = get_network_for_export(g.conn, network_id, options, file_format)
            return jsonify(content)
        else:
            return 'Unknown or invalid file format', 405


@api.route('/networks/<int:network_id>/attribute_scenarios')
class AttributeScenarios(Resource):

    @api.doc('Get a network''s attribute scenarios')
    def get(self, network_id):
        network = g.conn.call('get_network', network_id, include_data=False)
        template_id = g.conn.get_template_id_from_network(network)
        template = g.conn.call('get_template', template_id)

        tattrs = {tt.id: {ta.attr_id: ta for ta in tt.typeattrs} for tt in template.templatetypes}

        def simplify(scenario):
            return {
                'id': scenario.id,
                'name': scenario.name,
                'class': scenario.layout['class'] if 'class' in scenario.layout else 'baseline'
            }

        scenarios = [simplify(s) for s in network.scenarios if
                     s.layout.get('class') in ['baseline', 'option', 'scenario']]
        # for i, scenario in enumerate(network.scenarios):
        #     layout = scenario.layout
        #     if layout.get('class') in ['option', 'scenario']:
        #         scenarios.append(simplify(scenario))

        res_attr_scens = {'nodes': {}, 'links': {}}
        for res_type in ['nodes', 'links']:
            for resource in network[res_type]:
                rattrs = []
                typeids = [rt.id for rt in resource.types if rt.template_id == template_id]
                if typeids:
                    typeid = typeids[0]
                    tas = tattrs.get(typeid)
                    for ra in resource.attributes:
                        # filter by attribute scope and limit to what's in the template
                        ta = tas.get(ra.attr_id)
                        if ta and ta.attr_is_var == 'N':
                            rattrs.append({
                                'id': ra.id,
                                'name': ta.attr.name,
                                'scenarios': scenarios
                            })
                    res_attr_scens[res_type][resource.id] = rattrs

        return jsonify(res_attr_scens=res_attr_scens)


@api.route('/networks/<int:network_id>/preview_url')
class NetworkPreviewUrl(Resource):

    @api.doc('Get a network''s preview URL')
    def get(self, network_id):
        network = g.conn.call('get_network', network_id, summary=True, include_resources=True)
        template_id = network.layout.get('active_template_id')
        template = template_id and g.conn.call('get_template', template_id)
        svg = make_network_thumbnail(network, template)
        url = save_network_preview(
            network=network,
            filename='.thumbnail/preview.svg',
            contents=svg,
            location=current_app.config['NETWORK_FILES_STORAGE_LOCATION'],
            s3=current_app.s3
        )
        return jsonify(url=url)


@api.route('/networks/<int:network_id>/reference_layers')
class ReferenceLayers(Resource):

    @api.doc('Add a reference layer to a network')
    @api.param('realtime', 'Specify this after returning from a long-running task')
    def post(self, network_id):

        realtime = request.args.get('realtime', False, bool)

        reference = request.json.get('reference')
        geojson = request.json.get('geojson')
        network = g.conn.call('get_network', network_id, include_resources=False, summary=True,
                              include_data=False)
        reference = add_network_reference(g.conn, network, reference, geojson)

        if realtime:
            # add the reference to the client via socketio
            room = current_app.config['NETWORK_ROOM_NAME'].format(source_id=g.conn.dataurl_id, network_id=network_id)
            event = 'add-reference-layer'
            socketio.emit(event, reference, room=room)

            return 'success', 200

        else:
            return jsonify(reference=reference)

    def put(self, network_id):
        references = request.json.get('references')

        network = g.conn.call('get_network', network_id, include_data=False, include_resources=False, summary=True)

        updated = []
        updatedIds = []
        for reference in references:
            # filter reference to make sure nothing really large is accidentally passed in (like geojson or paths)
            id = reference.get('id')
            updated.append({
                'id': reference.get('id'),
                'path': reference.get('path'),
                'name': reference.get('name'),
                'visible': reference.get('visible'),
                'style': reference.get('style'),
                'labelField': reference.get('labelField', '')
            })
            updatedIds.append(id)

            geojson = reference.get('geojson')
            if geojson:
                update_network_reference(network, geojson, filename='{}.json'.format(reference['id']))

        refs = [ref for ref in network.layout.get('refs', []) if
                type(ref) in [dict, AttrDict] and ref.get('id') not in updatedIds]
        refs.extend(updated)
        network['layout']['refs'] = refs
        g.conn.call('update_network', network)

        return '', 204

    def delete(self, network_id):
        reference_ids = request.args.getlist('referenceIds[]', type=int)
        delete_network_references(g.conn, network_id, reference_ids)
        return '', 204


@api.route('/networks/<int:network_id>/permissions')
class NetworkPermissions(Resource):

    @api.doc(description='Share a network (add users with permissions)')
    def post(self, network_id):
        data = request.get_json()
        emails = data['emails']
        permissions = data['permissions']
        message = data.get('message', '')
        results = share_resource(g.conn, 'network', network_id, emails, permissions, message=message)
        return jsonify(results)

    @api.doc(description="Update network permissions.")
    @api.response(204, 'Success')
    def put(self, network_id):
        permissions = request.json['permissions']
        for username, _permissions in permissions.items():
            results = set_resource_permissions(g.conn, 'network', network_id, username, _permissions)

        return '', 204


@api.route('/nodes')
class Nodes(Resource):

    @api.doc('Add a node', params={
        'network_id': 'Network ID',
        'template_id': 'Template ID'
    })
    def post(self):
        network_id = request.args.get('network_id')
        template_id = request.args.get('template_id')

        # for single nodes
        incoming_node = request.json.get('node')
        _existing = request.json.get('existing')
        _split_locs = request.json.get('splitLocs')

        # for multiple nodes
        incoming_nodes = request.json.get('nodes', [incoming_node])

        nodes = []
        links = []
        del_nodes = []
        del_links = []

        for incoming in incoming_nodes:

            # create the new node
            if incoming.get('id', 0) > 0:
                incoming['types'] = update_types(incoming, 'NODE')
                node = g.conn.call('update_node', incoming)
                nodes.append(node)
            else:

                existing = incoming.pop('existing', _existing)
                split_locs = incoming.pop('splitLocs', _split_locs)
                incoming.pop('resType', None)

                node = g.conn.add_node(network_id, incoming)
                nodes.append(node)

                if existing:
                    old_node_id = existing['0'].get('nodeId')
                    old_link_id = existing['0'].get('linkId')
                    new_links = []
                    if old_node_id:

                        # update existing links and delete old node
                        old_link_ids = existing['0'].get('linkIds', [])
                        new_links = update_links2(g.conn, old_node_id=old_node_id, new_node_id=node.id,
                                                  old_link_ids=old_link_ids)
                        g.conn.call('delete_node', old_node_id, False)
                        del_nodes.append(old_node_id)

                    elif old_link_id:  # there should be only one, but existing includes an array
                        splits = next(iter(split_locs.values()))
                        new_links = split_link_at_nodes2(conn=g.conn, network_id=network_id,
                                                         template_id=template_id,
                                                         old_link_id=old_link_id,
                                                         nodes=[node],
                                                         splits=splits)
                        del_links.append(old_link_id)
                    else:
                        error = 1  # we shouldn't get here, obviously

                    links.extend(new_links)

                error = 0
        return jsonify(nodes=nodes, links=links, del_nodes=del_nodes, del_links=del_links)

    @api.doc('Bulk update multiple nodes')
    def put(self):
        nodes = request.json.get('nodes', [])
        for node in nodes:
            g.conn.call('update_node', node)

        return '', 204

    @api.doc(description='Bulk delete multiple nodes. WARNING: This currently does not have the "merge" option as '
                         'when deleting a single node; adjacent links will also be deleted.')
    def delete(self):
        ids = request.args.getlist('ids[]')
        for id in ids:
            g.conn.call('delete_node', id, True)

        return '', 204


@api.route('/nodes/<int:node_id>')
class Node(Resource):

    @api.doc('Update a single node')
    def put(self, node_id):

        incoming_node = request.json.get('node')
        should_update_types = request.args.get('update_types', 'false') == 'true'

        links = []
        old_node_id = None
        old_link_ids = []

        if should_update_types:
            incoming_node['types'] = update_types(incoming_node, 'NODE')

        resp = g.conn.call('update_node', incoming_node)
        node = g.conn.call('get_node', incoming_node['id'])

        # This is a hack to account for Hydra Platform differences between nodes from networks and from get_node
        resource_types = []
        for rt in node['types']:
            tt = rt.pop('templatetype')
            tt.pop('typeattrs')
            resource_types.append(tt)
        node['types'] = resource_types
        return jsonify(nodes=[node], links=links, del_nodes=[old_node_id], del_links=old_link_ids)

    @api.doc(
        description='Delete a single node',
        params={
            'method': 'How to handle adjacent links. Options are "delete" or "merge". "merge" (default) joins '
                      'adjacent links (this only works for two adjacent links), while "delete" removes adjacent links '
                      '(the default in Hydra Platform). "merge" merges the downstream link into the upstream link; '
                      'data for the downstream link will be lost.'
        }
    )
    @api.response(200, 'The new link, if the merge method is used')
    @api.response(204, 'Nothing, if the delete method is used')
    def delete(self, node_id):
        node = g.conn.call('get_node', node_id)
        method = request.args.get('method', "merge")
        if method == 'delete':
            resp = g.conn.call('delete_node', node_id, True)
            return 'Node deleted.', 204
        elif method == 'merge':
            up_link_id = request.args.get('up_link_id', type=int)
            down_link_id = request.args.get('down_link_id', type=int)
            links = g.conn.call('get_links', node.network_id, link_ids=[up_link_id, down_link_id])
            up_link = next((x for x in links if x['id'] == up_link_id), None)
            down_link = next((x for x in links if x['id'] == down_link_id), None)

            # merge links...
            up_link['node_2_id'] = down_link['node_2_id']
            if up_link['layout'].get('geojson') and down_link['layout'].get('geojson'):
                up_link['layout']['geojson']['geometry']['coordinates'].extend(
                    down_link['layout']['geojson']['geometry']['coordinates'][1:]
                )
            up_link.pop('types', None)
            new_link = g.conn.call('update_link', up_link)
            new_link = g.conn.get_link(new_link['id'])
            g.conn.call('delete_link', down_link_id, True)
            g.conn.call('delete_node', node_id, True)

            return jsonify(new_link=new_link)


links_fields = api.model('Links', {
    'link': fields.String,
    'links': fields.String,
    'existing': fields.String,
    'splitLocs': fields.String
})


@api.route('/links')
class Links(Resource):

    @api.doc(description='Add multiple links to a network')
    @api.param('network_id', 'Network ID')
    @api.param('template_id', 'Template ID (optional)')
    @api.expect(links_fields)
    def post(self):
        network_id = request.args.get('network_id', type=int)
        template_id = request.args.get('template_id', type=int)

        # for single link
        incoming_link = request.json.get('link')
        _existing = request.json.get('existing')
        _split_locs = request.json.get('splitLocs', {})

        # for multiple links
        incoming_links = request.json.get('links', [incoming_link])

        nodes = []
        links = []
        del_nodes = []
        del_links = []

        if incoming_links:
            network = g.conn.call('get_network', network_id, include_resources=True, include_data=False, summary=True)
            template_id = template_id or network.layout.get('active_template_id')
            template = g.conn.call('get_template', template_id)
            templatetypes = {tt.id: tt for tt in template.templatetypes}

            # TODO: get inflow/outflow node time from template
            default_types = get_default_types(template)

            # create the new link(s)
            for incoming in incoming_links:

                existing = incoming.pop('existing', _existing)
                split_locs = incoming.pop('splitLocs', _split_locs)

                incoming.pop('resType', None)

                if incoming.get('id', -1) <= 0 or existing:

                    _new_nodes, _new_links, _del_nodes, _del_links, network = add_link(
                        conn=g.conn,
                        network=network,
                        template=template,
                        ttypes=templatetypes,
                        incoming_link=incoming_link,
                        existings=existing,
                        split_locs=split_locs,
                        default_types=default_types,
                        del_nodes=[]
                    )

                    nodes.extend(_new_nodes)
                    links.extend(_new_links)
                    del_nodes.extend(_del_nodes)
                    del_links.extend(_del_links)

                else:
                    incoming['types'] = update_types(incoming, 'LINK')
                    g.conn.call('update_link', incoming)
                    links.append(incoming)

        return jsonify(nodes=nodes, links=links, del_nodes=del_nodes, del_links=del_links)

    @api.doc('Update multiple links.')
    def put(self):

        links = request.json.get('links', [])
        for link in links:
            g.conn.call('update_link', link)

        return '', 204

    @api.doc(description='Bulk delete multiple links.')
    def delete(self):
        ids = request.args.getlist('ids[]')
        for id in ids:
            g.conn.call('delete_link', id, True)

        return '', 204


@api.route('/links/<int:link_id>')
class Link(Resource):

    @api.doc(description='Update a link')
    def put(self, link_id):
        link = request.json.get('link')
        link.pop('coords', None)
        update_types = request.json.get('update_types', False)
        if update_types:
            link['types'] = update_types(link, 'LINK')
        updated_link = g.conn.call('update_link', link)
        return jsonify(link=updated_link)

    @api.doc(description='Delete a link')
    def delete(self, link_id):
        g.conn.call('delete_link', link_id, True)
        return '', 204


@api.route('/resources')
class Resources(Resource):

    @api.doc(description='Delete multiple resources (nodes and links)')
    @api.param('node_ids[]', 'The list of node IDs to delete')
    @api.param('link_ids[]', 'The list of link IDs to delete')
    def delete(self):
        node_ids = request.args.getlist('node_ids[]', type=int)
        link_ids = request.args.getlist('link_ids[]', type=int)

        def delete_resource(resource_type, resource_id):
            fn = 'delete_{}'.format(resource_type)
            try:
                g.conn.call(fn, resource_id, True)
            except:
                g.conn.call(fn, resource_id, False)

        for link_id in link_ids:
            delete_resource('link', link_id)
        for node_id in node_ids:
            delete_resource('node', node_id)

        return '', 204


@api.route('/resource_groups')
class ResourceGroups(Resource):

    @api.doc(description='Add resource group')
    def post(self):
        network_id = request.args.get('network_id')
        group = request.json.get('group')
        rg = g.conn.call('add_resourcegroup', group, network_id)
        return jsonify(group=rg)


@api.route('/resource_groups/<int:group_id>')
class ResourceGroup(Resource):

    @api.doc(description='Update resource group')
    def put(self, group_id):
        group = request.json.get('group')
        rg = g.conn.call('update_resourcegroup', group=group)
        return jsonify(group=rg)


@api.route('/resource_attributes')
class ResourceAttributes(Resource):

    # def get(self):
    #     type_id = request.args.get('type_id', type=int)
    #     res_id = request.args.get('id', type=int)
    #     res_type = request.args.get('res_type').lower()
    #     active_res_attr_id = request.args.get('active_res_attr', type=int)
    #
    #     res_attrs = g.conn.call('get_{}_attributes'.format(res_type), **{
    #         '{}_id'.format(res_type): res_id,
    #         'type_id': type_id
    #     })
    #
    #     # add templatetype attribute information to each resource attribute
    #     tattrs = {}
    #     if type_id:
    #         tt = g.conn.call('get_templatetype', type_id)
    #         tattrs = {ta.attr_id: ta for ta in tt.typeattrs if ta.attr_is_var == 'N'}
    #
    #     ret = []
    #     for ra in res_attrs:
    #         if ra.attr_id in tattrs:
    #             ra.update({
    #                 'tattr': tattrs[ra.attr_id],
    #                 'active': ra.id == active_res_attr_id
    #             })
    #             ret.append(ra)
    #     return jsonify(res_attrs=ret)

    @api.doc('Add resource attribute')
    def post(self):
        res_type = request.json['res_type']
        res_id = request.json['res_id']
        attr_id = request.json['attr_id']
        is_var = request.json['is_var']
        group = request.json.get('group')

        # get/create group
        if group and group['id'] is None:
            group = g.conn.call('add_group', group)
        else:
            group = None

        # create attribute
        is_var = 'Y' if is_var else 'N'
        res_attr = g.conn.call(
            'add_resource_attribute', **{
                'resource_type': res_type,
                'resource_id': res_id,
                'attr_id': attr_id,
                'is_var': is_var
            })

        # add to group
        if group:
            group_attr = g.conn.call('add_group_attribute', group_id=group.id, attr_id=res_attr.id, is_var=is_var)
            res_attr['group_id'] = group.id

        return jsonify(res_attr=res_attr)


@api.route('/resource_attribute/<int:res_attr_id>')
class ResourceAttribute(Resource):

    @api.doc(
        description='Update a resource attribute'
    )
    def put(self, res_attr_id):
        res_attr = request.json
        is_var = res_attr.get('attr_is_var', 'N')
        unit = res_attr.get('unit', '')
        data_type = res_attr.get('data_type', '')
        description = res_attr.get('description', '')
        properties = res_attr.get('properties', {})
        resp = g.conn.call(
            'update_resource_attribute',
            resource_attr_id=res_attr_id, is_var=is_var, unit=unit, data_type=data_type,
            description=description, properties=json.dumps(properties))
        return '', 204

    @api.doc(
        description='Delete a resource attribute'
    )
    def delete(self, res_attr_id):
        g.conn.call('delete_resource_attribute', res_attr_id)
        return '', 200


@api.route('/nodes/<int:node_id>/resource_types/<int:type_id>')
class LinkResourceType(Resource):

    @api.doc('Remove a type from a node')
    def delete(self, node_id, type_id):
        g.conn.call('remove_type_from_resource', type_id=type_id, resource_type='NODE', resource_id=node_id)
        return '', 200


@api.route('/links/<int:link_id>/resource_types/<int:type_id>')
class LinkResourceType(Resource):

    @api.doc('Remove a type from a link')
    def delete(self, link_id, type_id):
        g.conn.call('remove_type_from_resource', type_id=type_id, resource_type='LINK', resource_id=link_id)
        return '', 200


# CORS-protected routes

@api0.route('/networks/<int:network_id>/public_map', methods=['PUT'])
@login_required
def update_networks_map(network_id):
    is_public = request.args.get('is_public') == 'true'

    endpoint_url = current_app.config['MAPBOX_UPDATE_ENDPOINT']
    dataset_id = current_app.config['MAPBOX_DATASET_ID']
    mapbox_creation_token = current_app.config['MAPBOX_CREATION_TOKEN']

    network = g.conn.call('get_network', network_id, include_resources=True, include_data=False,
                          summary=True)
    template_id = network.layout.get('active_template_id')
    if not template_id:
        return '', 500
    template = g.conn.call('get_template', template_id)
    update_network_on_mapbox(network, template, endpoint_url, dataset_id, mapbox_creation_token, is_public)
    return '', 200


@api0.route('/network/settings', methods=['PUT'])
@login_required
def _update_network_settings():
    network_id = request.json['network_id']

    settings = request.json.get('settings')
    layout = request.json.get('layout')
    model_id = request.json.get('model_id')

    network = g.conn.call('get_network', network_id, summary=True, include_resources=False,
                          include_data=False)

    if layout:
        network['layout'].update(layout)

        active_template_id = layout.get('active_template_id')
        if active_template_id != network.layout.get('active_template_id'):
            network, new_tpl = change_active_template(g.conn, g.study.id, network=network,
                                                      new_template_id=active_template_id)

    if settings:
        current_settings = network.layout.get('settings', {})
        current_settings.update(settings)
        network['layout']['settings'] = current_settings

    if model_id:
        update_network_model(g.conn.url, network_id=network_id, model_id=model_id)

    if layout or settings:
        g.conn.call('update_network', network)

    return '', 204
