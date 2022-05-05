import socket
from datetime import datetime
import json
from cryptography.fernet import Fernet
from munch import Munch
import xml.etree.ElementTree as ET
from flask import g

from openagua.security import current_user
from openagua.lib.users import get_datauser
from openagua.lib.model_editor import get_model, add_model

from openagua import db
from openagua.models import DataUrl, NetworkModel

unknown_svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 15 15" height="15" width="15"><title>circle-15.svg</title><rect fill="none" x="0" y="0" width="15" height="15"></rect><path fill="red" transform="translate(0 0)" d="M14,7.5c0,3.5899-2.9101,6.5-6.5,6.5S1,11.0899,1,7.5S3.9101,1,7.5,1S14,3.9101,14,7.5z"></path></svg>'


def make_ttypes(template):
    ttypes = {}
    for ttype in template.templatetypes:
        ttypes[ttype.id] = ttype
    return ttypes


def make_ttype_dict(template):
    return {tt.name: tt for tt in template.templatetypes}


def get_tattrs(template):
    tattrs = {}
    for t in template.templatetypes:
        for ta in t.typeattrs:
            tattrs[ta.attr_id] = ta.copy()
    return Munch(tattrs)


def get_res_attrs(network, template):
    '''Create a dictionary of resource and attribute information for each resource attribute. Keys are resource attribute IDs.'''

    tattrs = get_tattrs(template)
    # attrs = conn.call('get_all_attributes')
    # attrs = {attr.id: attr for attr in attrs}
    res_attrs = {}
    for obj_type in ['Nodes', 'Links']:
        if obj_type == 'Nodes':
            features = network.nodes
        elif obj_type == 'Links':
            features = network.links
        for f in features:
            ttype = [t.name for t in f.types if t.template_id == template.id][0]
            for ra in f.attributes:
                if ra.attr_id not in tattrs:
                    continue
                res_attr = {'res_name': f.name, 'res_type': ttype, 'obj_type': obj_type}
                res_attr.update(tattrs[ra.attr_id])
                res_attrs[ra.id] = Munch(res_attr)
    return res_attrs


def get_used_ttypes(network, template, incl_vars=False):
    '''Remove template types that do not actually exist in the model'''

    if incl_vars:
        var_types = ['Y', 'N']
    else:
        var_types = ['N']

    res_attrs = get_res_attrs(network, template)
    # TODO: update hydra with get_all_node_attributes
    node_attrs = g.conn.call('get_all_node_attributes', network.id, template.id)
    node_types = []
    for na in node_attrs:
        res_type = res_attrs[na.id].res_type
        if res_type not in node_types:
            node_types.append(res_type)
    link_attrs = g.conn.call('get_all_link_attributes', network.id, template.id)
    link_types = []
    for la in link_attrs:
        res_type = res_attrs[la.id].res_type
        if res_type not in link_types:
            link_types.append(res_type)

    ttypes = {}
    ttypes_all = make_ttypes(template)
    for tt in ttypes_all:
        ttype = ttypes_all[tt]
        if ttype.resource_type == 'NODE' and ttype.name in node_types:
            ttypes[tt] = ttype
        elif ttype.resource_type == 'LINK' and ttype.name in link_types:
            ttypes[tt] = ttype
        else:
            continue

        tattrs = [ta for ta in ttypes[tt].typeattrs if ta.attr_is_var in var_types]
        if len(tattrs):
            ttypes[tt]['typeattrs'] = tattrs
        else:
            ttypes.pop(tt)

    return ttypes


def get_templates(conn):
    datauser = get_datauser(url=conn.url, user_id=current_user.id)
    all_templates = conn.call('get_templates')
    userid = datauser.userid
    templates = []
    for tpl in all_templates or []:
        # is_public = tpl.layout.get('is_public', True)
        # if is_public:
        #     templates.append(tpl)
        # else:
        for owner in tpl.owners:
            if owner.user_id == userid or owner.user_id == 1:
                templates.append(tpl)
                break

    templates.sort(key=lambda x: x.name, reverse=True)
    templates.sort(key=lambda x: x.name, reverse=True)

    return templates


def change_active_template(conn, source_id, network=None, network_id=None, new_template_id=None):
    network = network or conn.call('get_network', network_id, include_resources=True, include_data=False)
    current_tpl = network.layout.get('active_template_id')
    if current_tpl is not None:
        old_template_id = current_tpl if type(current_tpl) == int else current_tpl['id']
    else:
        old_template_id = None
    old_types = None

    new_template_id = new_template_id or network.layout.get('active_template_id')

    new_tpl = conn.call('get_template', new_template_id)

    # update network types
    existing_types = [rt.id for rt in network.types]
    for tt in new_tpl.templatetypes:
        if tt.resource_type != 'NETWORK':
            continue

        if tt.id not in existing_types:
            rts = [rt for rt in network.types if rt.name == tt.name]
            if rts:
                # get from existing network type
                rt = rts[0]
                rt['id'] = tt.id
                rt['template_id'] = new_tpl.id
            else:
                # create new network type
                rt = Munch({
                    'template_id': new_tpl.id,
                    'name': tt['name'],
                    'id': tt['id'],
                })
            network['types'].append(rt)

    # map from old template to new template
    new_types = {(tt.resource_type, tt.name.lower()): tt for tt in new_tpl.templatetypes}
    new_types_by_id = {tt.id: tt for tt in new_tpl.templatetypes}

    def update_resource_types(resource, resource_class=None):
        nonlocal old_types

        rt = None

        matching = [rt for rt in resource['types'] if rt['template_id'] == new_template_id]
        if matching:
            rt = matching[0]

        else:
            tt = None
            for old_rt in reversed(resource.types):  # search newest types first
                old_name_lower = old_rt.name.lower()
                if (resource_class, old_name_lower) in new_types:
                    tt = new_types[(resource_class, old_name_lower)]
                    break
            rt_updated = False
            if not tt and resource.types:
                old_rt = resource.types[-1]
                if old_types is None and old_template_id is not None:
                    old_tpl = conn.call('get_template', old_template_id)
                    old_types = Munch({(resource_class, tt.name.lower()): tt for tt in old_tpl.templatetypes})
                else:
                    old_types = {}
                # add the old template type to the new template
                # this should only work if the user has permission to modify the new template
                old_name_lower = old_rt.name.lower()
                if (resource_class, old_name_lower) in old_types.keys():
                    tt = old_types[(resource_class, old_name_lower)]
                    new_name_lower = tt.name.lower()
                    del tt['id']
                    del tt['cr_date']
                    tt['template_id'] = new_template_id
                    for ta in tt['typeattrs']:
                        ta['attr_id'] = None
                        ta.pop('cr_date')
                    tt = conn.call('add_templatetype', tt)
                    new_types[(resource_class, new_name_lower)] = tt  # add to new template (will update new template at end)
                    new_types_by_id[tt.id] = tt
                    rt_updated = True

                if not rt_updated:
                    # This is bad: it means the resource has no types at all. There are two options, both bad:
                    # 1) delete the resource
                    # 2) assign some arbitrary, catchall type
                    # for now, the latter is selected, with a type of UNKNOWN added to the template
                    tt = new_types.get((resource_class, 'unknown'))
                    if tt is None:
                        unknowntype = {
                            'template_id': new_template_id,
                            'name': 'UNKNOWN',
                            'resource_type': resource_class,
                            'layout': {'svg': unknown_svg}
                        }
                        tt = conn.call('add_templatetype', unknowntype)
                        new_types_by_id[tt.id] = tt

            if tt:
                rt = {
                    'template_id': new_template_id,
                    'name': tt['name'],
                    'id': tt['id']
                }
                # add new template type to network
                # TODO: Add multiple template capability; for now, only one template is assumed

        if rt:
            resource['types'] = [_rt for _rt in resource['types'] if _rt['id'] != rt['id']] + [rt]

            # add missing attributes
            tt = new_types_by_id[rt['id']]
            rattrs = set([ra['attr_id'] for ra in resource['attributes']])
            tattrs = set([ta['attr_id'] for ta in tt['typeattrs']])
            missing_attrs = tattrs - rattrs
            new_attrs = [
                {'attr_id': ta['attr_id'], 'attr_is_var': ta['attr_is_var']}
                         for ta in tt['typeattrs'] if ta['attr_id'] in missing_attrs]
            resource['attributes'].extend(new_attrs)

        return resource

    network['nodes'] = [update_resource_types(res, 'NODE') for res in network['nodes']]
    network['links'] = [update_resource_types(res, 'LINK') for res in network['links']]

    set_active_model(conn, source_id, network)

    return network, new_tpl


def set_active_model(conn, source_id, network):
    update_template = False
    template_id = network.layout.get('active_template_id')
    if template_id is None:
        update_template = True
        template_id = network.types[0].template_id
    elif type(template_id) != int:
        update_template = True
        template_id = network.layout.template_id.id
    if update_template:
        network['layout']['active_template_id'] = template_id

    # get model
    # This is a bit convoluted. General logic is:
    # 1. Get model from network_model (deployment-specific)
    # 2. Look for / create model from network settings (active_model_name)
    # 3. Finally, create model from template name
    model = None
    network_model = get_network_model(url=conn.url, network_id=network.id)
    model_name = None
    if network_model:
        model = get_model(id=network_model.model_id)
        if model is None:
            template = conn.call('get_template', template_id)
            if model_name is None:
                model_name = template.name
            model = get_model(source_id=source_id, project_id=network['project_id'], name=model_name)
            if model is None:
                model = add_model(
                    url=conn.url,
                    model={'name': model_name, 'scope': 'public'},
                    template_id=template.id
                )
                add_network_model(url=conn.url, model_id=model.id, network_id=network.id)

    if update_template:
        network = conn.call('update_network', network)

    return network


def get_dataurl(url):
    return DataUrl.query.filter_by(url=url).first()


def get_network_model(url=None, network_id=None, model_id=None):
    dataurl = get_dataurl(url)
    if url and network_id and model_id:
        return NetworkModel.query.filter_by(dataurl_id=dataurl.id, model_id=model_id, network_id=network_id).first()
    elif url and network_id:
        return NetworkModel.query.filter_by(dataurl_id=dataurl.id, network_id=network_id).first()
    else:
        return None


def add_network_model(url, model_id, network_id, settings={}):
    dataurl = get_dataurl(url)
    nm = get_network_model(url=url, network_id=network_id, model_id=model_id)
    if nm is None:
        if isinstance(settings, dict) or isinstance(settings, Munch):
            settings = json.dumps(settings)
        nm = NetworkModel(
            dataurl_id=dataurl.id,
            model_id=model_id,
            network_id=network_id,
            settings=settings
        )
        db.session.add(nm)
        db.session.commit()


def update_network_model(url, network_id, model_id, settings=None):
    dataurl = get_dataurl(url=url)
    network_models = NetworkModel.query.filter_by(dataurl_id=dataurl.id, network_id=network_id).all()
    if network_models:
        for nm in network_models[1:]:
            db.session.delete(nm)
        nm = network_models[0]
        nm.model_id = model_id
        nm.active = True
    else:
        if isinstance(settings, dict) or isinstance(settings, Munch):
            settings = json.dumps(settings)
        nm = NetworkModel(
            dataurl_id=dataurl.id,
            model_id=model_id,
            network_id=network_id,
            settings=settings,
            active=True
        )
        db.session.add(nm)
    db.session.commit()


def internet_on():
    try:
        socket.create_connection(("www.google.com", 80))
        return True
    except OSError:
        pass
    return False


def encrypt(text, key):
    f = Fernet(key)
    return f.encrypt(str.encode(text))


def decrypt(ciphertext, key):
    key = key
    f = Fernet(key)
    try:
        try:
            txt = f.decrypt(ciphertext).decode()
        except:
            txt = f.decrypt(bytes(ciphertext, 'utf-8')).decode()
    except:
        txt = None
    return txt


def get_utc():
    return int((datetime.utcnow() - datetime(1970, 1, 1, 0, 0, 0, 0)).total_seconds())


def upload_template(conn, zf, tpl_name):
    '''Upload a template from a zipfile.'''

    template_xml_path = zf.namelist()[0]
    template_xml = zf.read(template_xml_path).decode('utf-8')

    root = ET.fromstring(template_xml)
    for name in root.iter('template_name'):
        name.text = tpl_name
    new_xml = ET.tostring(root).decode()

    template = conn.call('upload_template_xml', new_xml)

    return template

