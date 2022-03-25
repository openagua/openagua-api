from flask import g

from urllib.parse import urlparse
from openagua.connection import root_connection
from openagua.security import current_user
from openagua.lib.users import get_datauser, get_dataurl
from openagua.lib.networks import prepare_network_for_import
from openagua.lib.templates import clean_template, clean_template2
from openagua.lib.model_editor import get_models, get_active_network_model
from openagua.utils import decrypt
from openagua.connection import HydraConnection


def move_project(key, **kwargs):
    src = kwargs['source']
    dest = kwargs['destination']

    datauser1 = get_datauser(url=src, user_id=current_user.id)
    conn1 = HydraConnection(
        url=src,
        username=datauser1.username,
        password=decrypt(datauser1.password, key)
    )

    datauser2 = get_datauser(url=dest, user_id=current_user.id)
    conn2 = HydraConnection(
        url=dest,
        username=datauser2.username,
        password=decrypt(datauser2.password, key)
    )

    # get existing project
    project1 = conn1.call('get_project', kwargs['project_id'])

    # create new project
    project1['id'] = None
    del project1['created_by']
    del project1['cr_date']

    projects2 = conn2.call('get_projects', user_id=datauser2.userid)
    existing_names = [p.name for p in projects2]
    i = 2
    badname = True
    new_name = project1.name
    while badname:
        if new_name in existing_names:
            new_name = '{} ({})'.format(project1.name, i)
            i += 1
        else:
            badname = False

    project1['name'] = new_name
    project2 = conn2.call('add_project', project1)

    # get project networks
    networks1 = conn1.call('get_networks', project_id=kwargs['project_id'], include_data=True, include_resources=True,
                           summary=False)
    for network1 in networks1:
        try:
            template1 = conn1.call('get_template', network1.types[0].template_id)
            template2 = conn2.call('get_template_by_name', template_name=template1.name)

            ttypes2 = {tt['name']: tt['id'] for tt in template2.templatetypes}

            net = {
                'name': network1.name,
                'description': network1.description,
                'layout': network1.layout,
                'project_id': project2.id,
                'nodes': [],
                'links': [],
                'network': []
            }

            # update some defaults
            net['layout']['public'] = False  # assume not public on new database

            # step 1: add network types
            new_types = []
            for type in network1['types']:
                type['id'] = ttypes2[type.name]
                type['template_id'] = template2.id
                new_types.append(type)
            net['types'] = new_types

            # step 2: add nodes
            for node in network1.nodes:
                del node['id']
                del node['cr_date']
                new_types = []
                for type in node['types']:
                    type['id'] = ttypes2[type.name]
                    type['template_id'] = template2.id
                    new_types.append(type)
                node['types'] = new_types
                net['nodes'].append(node)
            net = conn2.call('add_network', net)

            # step 3: add links
            nodes1 = {node.id: node.name for node in network1.nodes}
            nodes2 = {node.name: node.id for node in net.nodes}
            for link in network1.links:
                del link['id']
                del link['cr_date']
                new_types = []
                for type in link['types']:
                    type['id'] = ttypes2[type.name]
                    type['template_id'] = template2.id
                    new_types.append(type)
                for endnode in ['node_1_id', 'node_2_id']:
                    link[endnode] = nodes2[nodes1[link[endnode]]]
                net['links'].append(link)

            conn2.call('update_network', net=net)
        except:
            continue

    return project2


def get_project_url(request_url, source_url, project_id):
    dataurl = get_dataurl(source_url)
    ru = urlparse(request_url)
    project_url = '{scheme}://{netloc}/public/project/{urlid}/{projid}'.format(
        scheme=ru.scheme,
        netloc=ru.netloc,
        urlid=dataurl.id,
        projid=project_id
    )
    return project_url


def copy_project(project):
    conn = g.conn

    option = 1

    # OPTION 1: 100% Hydra Platform + extra stuff

    if option == 1:
        resp = conn.call('clone_project', project['id'], recipient_user_id=conn.id, new_project_name=project['name'],
                         new_project_description=project['description'])
        new_project_id = resp

    # OPTION 2: roll-your-own

    else:

        root_conn = root_connection()

        old_project_id = project['id']

        # 1. create empty project
        new_project = dict(
            name=project['name'],
            description=project['description'],
            layout=project['layout']
        )
        new_project = conn.call('add_project', new_project)
        new_project_id = new_project['id']

        # copy templates

        templates_map = {}  # map new templates to old template IDs

        project_templates = g.conn.call('get_templates', project_id=old_project_id)
        for project_template in project_templates:
            tmpl = clean_template2(project_template.copy())
            tmpl['project_id'] = new_project_id
            template = conn.call('add_template', tmpl, check_dimensions=False)
            templates_map[project_template['id']] = template

        # copy networks

        for net in project.get('networks'):

            # update network template
            template_id = net['layout'].get('active_template_id')
            if template_id in templates_map:
                template = templates_map[template_id]
            elif template_id:
                template = conn.call('get_template', template_id)
                template = clean_template2(template)
                template['project_id'] = new_project_id  # make sure it is scoped to the project
                template = conn.call('add_template', template, check_dimensions=False)
                templates_map[template_id] = template
            else:
                template = None

            network = root_conn.call('get_network', net['id'], include_data=True, include_results=False,
                                     include_non_template_attributes=True, include_metadata=True)
            network = prepare_network_for_import(network=network, template=template)
            network['project_id'] = new_project_id
            network['scenarios'] = [s for s in network['scenarios'] if s.get('layout', {}).get('class') != 'results']

            new_network = g.conn.call('add_network', network)

            # dictionary of old resource IDs to new resource IDs
            new_network_nodes = {n['name']: n['id'] for n in new_network['nodes']}
            old_to_new_node_id = {n['id']: new_network_nodes[n['name']] for n in network['nodes']}

            # update the network scenarios with data and the correct parent_id
            # TODO: this should be in Hydra Platform
            new_scenario_parent_id_lookup = {}
            for old_scen in network['scenarios']:

                # copy data
                new_scenario = [s for s in new_network['scenarios'] if s['name'] == old_scen['name']][0]
                old_scenario = root_conn.call('get_scenario', old_scen['id'])

                # copy resourcescenarios
                for rs in old_scenario['resourcescenarios']:
                    for res_id in ['node_id', 'link_id', 'network_id']:
                        if rs[res_id]:
                            continue

                old_scenario_parent_id = old_scenario['parent_id']
                if old_scenario_parent_id:
                    if old_scenario_parent_id in new_scenario_parent_id_lookup:
                        new_scenario_parent_id = new_scenario_parent_id_lookup[old_scenario_parent_id]
                    else:
                        old_scenario_parent = [s for s in network['scenarios'] if s['id'] == old_scenario_parent_id][0]
                        new_scenario_parent = \
                            [s for s in new_network['scenarios'] if s['name'] == old_scenario_parent['name']][0]
                        new_scenario_parent_id_lookup[old_scenario_parent_id] = new_scenario_parent_id = \
                            new_scenario_parent['id']
                    new_scenario['parent_id'] = new_scenario_parent_id

                g.conn.call('update_scenario', new_scenario)

    ret_project = g.conn.call('get_project', new_project_id)

    return ret_project


def prepare_projects_for_client(conn, projects, *args, **kwargs):
    kwargs['dataurl_id'] = get_dataurl(conn.url).id
    projects = [prepare_project_for_client(conn, p, *args, **kwargs) for p in projects]
    return projects


def prepare_project_for_client(conn, project, source_id, source_user_id, dataurl_id=None, data_url=None,
                               include_models=False):
    dataurl_id = dataurl_id or get_dataurl(data_url).id
    editable = source_user_id in [owner['user_id'] for owner in project['owners'] if
                                  owner['user_id'] == source_user_id and owner['edit'] == 'Y']

    project.update(
        # public_url=get_project_url(request_url, source_url, project.id),
        source={"id": source_id, "url": conn.url},
        ownership="owned" if project["created_by"] == source_user_id else "shared",
        editable=editable,
        networks=project.get('networks', []),
        layout=project.get('layout', {})
    )

    if include_models:
        model_engines = get_models(
            dataurl_id=dataurl_id,
            project_id=project.id,
            network_ids=[n.id for n in project.networks]
        )
        project['model_engines'] = model_engines

    # if editable:
    #     study = get_study(project_id=project.id, url=source_url)
    #     secrets = decrypt(study.secrets, current_app.config['SECRET_ENCRYPT_KEY']) if study.secrets else {}
    #     project['secrets'] = secrets

    for network in project.networks:
        if network.layout.get('active_template_id') is None:
            net = conn.call('get_network', network.id, include_resources=True, include_data=False,
                            summary=True)
            if hasattr(net, 'name'):
                ttypes = [tt for tt in net.nodes[-1]['types']] if net.nodes else None
                if ttypes:
                    template_id = ttypes[0]['template_id']
                    network['layout']['active_template_id'] = template_id
                    conn.call('update_network', network)

        network_model = get_active_network_model(dataurl_id=dataurl_id, network_id=network.id)
        if network_model:
            network['active_model_id'] = network_model.model_id

    return project
