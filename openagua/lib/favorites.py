import json
from openagua.lib.studies import get_study
from openagua.models import Favorite
from openagua import db


# favorites

def add_favorite(study_id, name, description, thumbnail, filters, setup, content):
    favorite = Favorite()
    favorite.study_id = study_id
    favorite.name = name
    favorite.description = description
    favorite.thumbnail = thumbnail
    favorite.filters = filters
    favorite.setup = setup
    favorite.content = content

    db.session.add(favorite)
    db.session.commit()

    db.session.close()

    return favorite.id


def add_update_favorite(study_id=None, network_id=None, favorite_id=None, favorite=None):
    favorite = favorite or {}
    if favorite_id:
        f = Favorite.query.filter_by(id=favorite_id).first()
    else:
        f = Favorite()

        f.study_id = study_id
        if network_id:
            f.network_id = network_id

    f.name = favorite.get('name')
    f.description = favorite.get('description')
    f.thumbnail = favorite.get('thumbnail', '')
    f.filters = json.dumps(favorite.get('filters', {}))
    f.setup = json.dumps(favorite.get('setup', {}))
    content = favorite.get('content', '')
    if type(content) is not str:
        content = json.dumps(content)
    f.content = content

    if not favorite_id:
        db.session.add(f)
    db.session.commit()

    return f


def get_favorite(favorite_id=None):
    if favorite_id and type(favorite_id) == int:
        favorite = Favorite.query.filter_by(id=favorite_id).first()
    else:
        favorite = None

    return favorite


def get_favorites(dataurl_id=None, project_id=None, study_id=None, network_id=None):
    favorites = []
    if dataurl_id and project_id:
        study = get_study(dataurl_id=dataurl_id, project_id=project_id)
        study_id = study.id
    if study_id and network_id:
        favorites = Favorite.query.filter_by(study_id=study_id, network_id=network_id).all()
    elif study_id:
        favorites = Favorite.query.filter_by(study_id=study_id)

    return [favorite.to_json() for favorite in favorites]


def validate_favorites(conn=None, network_id=None, favorites=()):
    # Check if favorite is still valid
    network = conn.call('get_network', network_id, summary=False, include_data=False, include_resources=False)
    try:
        scenario_ids = set([s.id for s in network['scenarios']])
    except:
        print(network)
    ret = []
    for favorite in favorites:
        if favorite['filters'].get('results'):
            favorite['filters']['scenarios'] = favorite['filters']['results']
            del favorite['filters']['results']
            add_update_favorite(favorite=favorite)
        favorite_scenarios = set(favorite['filters'].get('scenarios', []))
        if favorite_scenarios and favorite_scenarios.issubset(scenario_ids):

            ret.append(favorite)
        else:
            delete_favorite(favorite_id=favorite['id'])
    return ret


def delete_favorite(favorite_id=None):
    try:
        Favorite.query.filter_by(id=favorite_id).delete()
        db.session.commit()
        error = 0
    except:
        error = 1
    return error


def delete_favorites(favorite_ids=None):
    try:
        favorites = Favorite.query.filter(Favorite.id.in_(favorite_ids)).all() if favorite_ids else []
        for favorite in favorites:
            favorite.delete()
        db.session.commit()
        error = 0
    except:
        error = 1
    return error
