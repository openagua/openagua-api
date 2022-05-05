from flask import g
from boltons.iterutils import remap
from munch import Munch


def prepare_template_for_import(template, internal=True):
    def visit(path, key, value):
        if key in {'cr_date', 'created_by', 'owners', 'image', 'id', 'template_id'}:
            return False
        if key in {'attr_id'}:
            return (key, abs(value)) if internal else (key, -abs(value))
        elif key in {'template_id', 'type_id'}:
            return key, -abs(value)
        return key, value

    return remap(dict(template), visit=visit)


def clean_template(template=None):
    def visit(path, key, value):
        if key in {'created_by', 'cr_date', 'owners', 'image'}:
            return False
        elif key in {'type_id'}:
            # return key, -abs(value)
            return False
        elif key in {'id', 'attr_id', 'template_id'}:
            return key, None
        elif key == 'types':
            return 'templatetypes', value
        return key, value

    cleaned = remap(dict(template), visit=visit)

    return cleaned


def clean_template2(template):
    if 'layout' not in template:
        template['layout'] = {}
    for key in ['id', 'created_by', 'cr_date', 'owners']:
        template.pop(key, None)
    for i, tt in enumerate(template['templatetypes']):
        for key in ['id', 'template_id', 'cr_date']:
            tt.pop(key, None)
        for ta in tt['typeattrs']:
            for key in ['type_id', 'cr_date']:
                ta.pop(key, None)
            ta['attr_id'] = None
            if 'attr' in ta:
                ta['name'] = ta['attr']['name']
                ta['attr_id'] = ta['attr']['id']

    return template


def add_template(template, is_public=False):
    i = 0
    old_name = template['name']
    while True:
        result = g.conn.call('add_template', template)
        if result.get('name'):
            break
        elif 'Duplicate' in result.get('error', '') and i < 100:
            i += 1
            template['name'] = '{} ({})'.format(old_name, i)
        else:
            break

    return result


def get_default_types(template, mapping=None):
    template_default_types = template.layout.get('default_types', {})
    mapping = mapping or dict(
        inflow="Inflow",
        outflow="Outflow",
        junction="Junction"
    )
    default_types = {}
    for key in ['inflow', 'outflow', 'junction']:
        if key in template_default_types:
            templatetypes = [tt for tt in template['templatetypes'] if tt['id'] == int(template_default_types[key])]
            if templatetypes:
                default_types[key] = templatetypes[0]
        else:
            default_name = mapping[key]
            templatetypes = [tt for tt in template['templatetypes'] if tt['name'] == default_name]
            if templatetypes:
                default_types[key] = templatetypes[0]
    return Munch(default_types)
