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

    new_project_id = conn.call('clone_project', project['id'], recipient_user_id=conn.user_id,
                               new_project_name=project['name'], new_project_description=project['description'])
    new_project = conn.call('get_project', new_project_id)

    old_project_id = project['id']

    # copy templates

    templates_map = {}  # map new templates to old template IDs
    project_templates = g.conn.call('get_templates', project_id=old_project_id)
    for project_template in project_templates:
        tmpl = clean_template2(project_template.copy())
        tmpl['project_id'] = new_project_id
        new_template = conn.call('add_template', tmpl, check_dimensions=False)
        templates_map[project_template['id']] = new_template['id']

    # copy networks
    old_networks = {n['name']: n['id'] for n in project['networks']}

    for new_network in new_project['networks']:

        new_network_id = new_network['id']
        old_network_id = old_networks[new_network['name']]
        old_network = conn.call('get_network', old_network_id)

        # 1. update network template

        old_template_id = new_network.get('layout', {}).get('active_template_id')
        if old_template_id in templates_map:
            new_template_id = templates_map[old_template_id]
        elif old_template_id:
            template = conn.call('get_template', old_template_id)
            template = clean_template2(template)
            template['project_id'] = new_project_id  # make sure it is scoped to the project
            template = conn.call('add_template', template, check_dimensions=False)
            templates_map[old_template_id] = new_template_id = template['id']
        else:
            new_template_id = None

        if new_template_id:
            new_network['layout'] = {'active_template_id': new_template_id}
            resp = conn.call('update_network', new_network)

        if old_template_id and new_template_id:
            # TODO: check the reliability of this!!!
            resp = conn.call('remove_template_from_network', new_network_id, old_template_id, False)
            resp = conn.call('apply_template_to_network', new_template_id, new_network_id)

        # 2. update scenario dependency mapping

        old_scenarios = {s['id']: s for s in old_network['scenarios']}
        new_scenarios = {s['name']: s for s in new_network['scenarios']}
        for new_scenario in new_network['scenarios']:
            if new_scenario['parent_id']:
                new_scenario['parent_id'] = new_scenarios[old_scenarios[new_scenario['parent_id']]['name']]['id']
                conn.call('update_scenario', new_scenario)

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
