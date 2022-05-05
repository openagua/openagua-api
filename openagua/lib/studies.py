from flask import g, json
from munch import Munch as AttrDict

from openagua.models import Study, Star
from openagua.security import current_user
from openagua.lib.users import get_datauser, get_dataurl, get_dataurl_by_id, get_datausers

from openagua import db


def add_study(created_by, dataurl_id, project_id):
    study = Study()
    study.created_by = created_by
    study.dataurl_id = dataurl_id
    study.project_id = project_id
    db.session.add(study)
    db.session.commit()

    return study


def update_study(id, **updates):
    study = get_study(id=id)
    settings = json.loads(study.settings if study.settings else '{}')
    settings.update(updates)
    study.settings = json.dumps(settings)
    db.session.commit()
    return


def delete_studies(userid, network_id):
    Study.query.filter_by(userid=userid, network_id=network_id).delete()
    db.session.commit()


def delete_study(**kwargs):
    study = get_study(**kwargs)
    if study:
        study.delete()
        db.session.commit()


def get_study(**kwargs):
    study_id = kwargs.get('id')
    project_id = kwargs.get('project_id')
    datauser_id = kwargs.get('datauser_id')
    dataurl_id = kwargs.get('dataurl_id')
    url = kwargs.get('url')

    if study_id:
        study_id = kwargs['id']
        study = Study.query.filter_by(id=study_id).first()

    elif project_id:
        if url is not None:
            dataurl = get_dataurl(url)
            dataurl_id = dataurl.id
        if dataurl_id:
            studies = Study.query.filter_by(project_id=project_id, dataurl_id=dataurl_id).all()
            if not studies:
                datausers = get_datausers(dataurl_id=dataurl_id)
                datauser_ids = [datauser.id for datauser in datausers]
                try:
                    studies = Study.query.filter(Study.project_id == project_id,
                                                 Study.datauser_id.in_(datauser_ids)).all() if datauser_ids else []
                except:
                    studies = []
                if not studies:
                    study = add_study(created_by=current_user.id, project_id=project_id, dataurl_id=dataurl_id)
                else:
                    for i, s in enumerate(studies):
                        if i == 0:
                            s.created_by = current_user.id
                            s.dataurl_id = dataurl_id
                            study = s
                        else:
                            db.session.delete(study)
                    db.session.commit()
            else:
                study = studies[0]

    else:
        study = None

    return study


def get_studies(**kwargs):
    studies = []
    if 'datauser_id' in kwargs:
        studies = Study.query.filter_by(datauser_id=kwargs['datauser_id'])
    elif 'url' in kwargs:
        datausers = get_datausers(url=kwargs['url'])
        for datauser in datausers:
            studies.extend(Study.query.filter_by(datauser_id=datauser.id))
    return studies


def load_active_study(dataurl_id=None, project_id=None):
    # user_settings = json.loads(current_user.settings if current_user.settings else '{}')

    if dataurl_id and project_id:
        g.study = get_study(dataurl_id=dataurl_id, project_id=project_id)
    else:
        g.study = None

    if g.study:
        # if g.datauser is None:
        g.datauser = get_datauser(user_id=current_user.id, dataurl_id=g.study.dataurl_id)
        g.dataurl = get_dataurl_by_id(g.datauser.dataurl_id)

    else:
        g.datauser = None
    if g.study and type(g.study.settings) is str:
        g.study_settings = AttrDict(json.loads(g.study.settings))
    else:
        g.study_settings = AttrDict({})


def add_default_project(conn, user):
    project_name = user.email
    project_description = 'Default project created for {} {} ({})'.format(
        user.firstname,
        user.lastname,
        user.email
    )

    # add project
    project = conn.call('add_project', {'name': project_name, 'description': project_description})

    return project


def get_stars(user_id):
    stars = Star.query.filter_by(user_id=user_id).all()
    ret = {}
    for star in stars:
        source_id = star.study.dataurl_id
        project_id = star.study.project_id
        if source_id not in ret:
            ret[source_id] = []
        ret[source_id].append(project_id)
    return ret


def add_star(user_id, source_id, project_id):
    star = Star()
    study = get_study(dataurl_id=source_id, project_id=project_id)
    star.user_id = user_id
    star.study_id = study.id
    db.session.add(star)
    db.session.commit()


def remove_star(user_id, source_id, project_id):
    study = get_study(dataurl_id=source_id, project_id=project_id)
    star = Star.query.filter_by(user_id=user_id, study_id=study.id)
    star.delete()
    db.session.commit()
