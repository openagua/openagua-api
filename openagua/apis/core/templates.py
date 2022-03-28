from flask import g, request, json, jsonify
from flask_restx import Resource

from pathlib import Path

from openagua.connection import root_connection
from openagua.lib.templates import add_template, clean_template, prepare_template_for_import

from openagua.apis import api

ALLOWED_EXTENSIONS = ['.json']


@api.route('/templates')
class Templates(Resource):

    @api.doc(
        description='Get a list of templates',
        params={
            'ids': 'A list of template IDs'
        }
    )
    def get(self):
        project_id = request.args.get('project_id', 0, type=int)
        template_ids = request.args.getlist('template_ids[]', type=int)
        load_all = request.args.get('load_all', 'true') == 'true'
        templates = []
        project_template_ids = []

        if project_id or template_ids:
            if project_id:
                templates = g.conn.call('get_templates', project_id=project_id)
                try:
                    project_template_ids = [t.id for t in templates]
                except:
                    print(templates)
            if template_ids:
                template_ids = [tid for tid in template_ids if tid not in project_template_ids]
                other_templates = g.conn.call('get_templates', template_ids=template_ids)
                try:
                    templates.extend(other_templates)
                except:
                    print('Something went wrong processing templates: ')
                    print(templates)

            for template in templates:
                try:
                    if template['layout'].get('project_id'):
                        template['project_id'] = template['layout']['project_id']
                        del template['layout']['project_id']
                        g.conn.call('update_template', template, update_types=False)
                except:
                    print('Something went wrong processing template: ')
                    print(template)

        else:
            templates = g.conn.call('get_templates', uid=g.conn.user_id, load_all=load_all)

            if g.is_public_user and request.args.get('exclude_user') == 'true':
                user_id = g.datauser.userid
                templates = [t for t in templates if not any(o for o in t['owners'] if o['user_id'] == user_id)]

            elif request.args.get('exclude_public') == 'true':
                public_conn = root_connection()
                root_id = public_conn.user_id
                templates = [t for t in templates if not any(o for o in t['owners'] if o['user_id'] == root_id)]

        return jsonify(templates=templates)

    def post(self):
        file = request.files.get('file')
        if file:
            if Path(file.filename).suffix in ALLOWED_EXTENSIONS:
                # filename = secure_filename(file.filename)
                content = file.stream.read()
                template = json.loads(content.decode("utf-8-sig"))
                template = clean_template(template=template)
                template = add_template(template)
                return jsonify(template=template)
            else:
                return 'Unsupported media type', 415

        else:
            template = request.json.get('template')
            fork = request.args.get('fork', False, type=bool)
            if fork:
                template.pop('id', None)
                template['layout']['base_template_id'] = template['id']
                cleaned = clean_template(template=template)
            else:
                cleaned = prepare_template_for_import(template, internal=True)
            template = add_template(cleaned)
            return jsonify(template=template)


@api.route('/templates/<int:template_id>')
class Template(Resource):
    def get(self, template_id):
        template = g.conn.call('get_template', template_id)
        return jsonify(template=template)

    def put(self, template_id):
        template = request.json['template']
        updated = g.conn.call('update_template', template)
        return jsonify(template=updated)

    def patch(self, template_id):
        updates = request.json
        template = g.conn.call('get_template', template_id)
        template.update(updates)
        result = g.conn.call('update_template', template)
        if 'faultcode' in result:
            return jsonify(errorcode=1, message='Name already taken.')
        else:
            return '', 204

    def delete(self, template_id):
        resp = g.conn.call('delete_template', template_id)
        return '', 204


@api.route('/templatetypes')
class TemplateTypes(Resource):

    @api.doc(description='Add a template type.')
    def post(self):
        templatetype = request.json['templatetype']
        ttype = g.conn.call('add_templatetype', templatetype)
        return jsonify(templatetype=ttype)


@api.route('/templatetypes/<int:template_type_id>')
class TemplateType(Resource):

    @api.doc(description='Update a template type.')
    def put(self, template_type_id):
        ttype = request.json.get('templatetype')
        if ttype['resource_type'] == 'LINK':
            ttype['layout'].pop('svg', None)
        for ta in ttype.get('typeattrs', []):
            ta.pop('default_dataset', None)  # it's unclear why this is needed
        g.conn.call('update_templatetype', ttype)
        return '', 204

    @api.doc(description='Delete a template type')
    def delete(self, template_type_id):
        g.conn.call('delete_templatetype', template_type_id)
        return '', 204


@api.route('/typeattrs')
class TypeAttrs(Resource):

    @api.doc(description='Add a template type attribute.')
    def post(self):
        tattr = request.json['tattr']
        attr = dict(name=tattr['attr_name'], dimension_id=tattr['dimension_id'])
        attr = g.conn.call('add_attribute', attr)
        tattr['attr_id'] = attr.id
        ret_tattr = g.conn.call('add_typeattr', dict(tattr))
        ret_tattr['attr'] = attr
        return jsonify(tattr=ret_tattr)


@api.route('/typeattrs/<int:typeattr_id>')
class TypeAttr(Resource):

    @api.doc(description='Update a template type attribute.')
    def put(self, typeattr_id):
        typeattr = request.json['tattr']

        if 'attr_is_var' in typeattr:
            typeattr['is_var'] = typeattr.pop('attr_is_var')

        attr = g.conn.call('add_attribute', dict(name=typeattr['attr_name'], dimension_id=typeattr['dimension_id']))
        if typeattr['attr_id'] == attr['id']:
            # attribute hasn't changed
            typeattr.pop('dimension_id')
        ttype = g.conn.call('get_templatetype', typeattr['type_id'])
        existing_attr_ids = [ta['attr_id'] for ta in ttype['typeattrs']]

        if attr.id not in existing_attr_ids:
            g.conn.call('remove_attr_from_type', ttype['id'], typeattr['attr_id'])
            typeattr['attr_id'] = attr['id']
            # TODO: double check if the following is still needed with hydra_base
            typeattr.pop('default_dataset', None)
            ret = g.conn.call('add_typeattr', typeattr)
        else:
            ttype['typeattrs'] = [dict(typeattr) if typeattr['attr_id'] == ta['attr_id'] else dict(ta) for ta in
                                  ttype['typeattrs']]
            g.conn.call('update_templatetype', dict(ttype))
            ret = typeattr

        ret['attr'] = attr

        return jsonify(tattr=ret)

    @api.doc(description='Delete a template type attribute.')
    def delete(self, typeattr_id):
        g.conn.call('delete_typeattr', typeattr_id)
        return '', 204


@api.route('/dimensions')
class Dimensions(Resource):

    @api.doc(description='Get all dimensions')
    def get(self):
        full = request.args.get('full', True, type=bool)
        dimensions = g.conn.call('get_dimensions', full=full)
        return jsonify(dimensions=dimensions)


@api.route('/units/<int:unit_id>')
class Units(Resource):

    @api.doc(description='Get a specified unit')
    def get(self, unit_id):
        include_dimension = request.args.get('include_dimension', True)
        unit = g.conn.call('get_unit', unit_id)
        if include_dimension:
            dimension = g.conn.call('get_dimension', unit['dimension_id'])
            dimension.pop('units', None)
            unit['dimension'] = dimension
        return jsonify(unit)
