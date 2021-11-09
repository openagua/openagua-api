from flask import current_app
from openagua import db
from openagua.lib.studies import get_study
from openagua.models import Model, NetworkModel, ModelTemplate, DataUrl


def add_model(url, model, template_id):
    m = Model()
    for key, value in model.items():
        setattr(m, key, value)
    db.session.add(m)
    db.session.commit()

    mt = add_model_template(url, m.id, template_id)
    ret = get_model(id=m.id)
    return ret


def update_model(**kwargs):
    model_id = kwargs.pop('id')
    model = Model.query.filter_by(id=model_id).one()

    key = kwargs.get('key')
    model_name = kwargs.get('name')

    if key != model.key:
        rabbitmq = current_app.rabbitmq

        vhost_template = 'model-{}'
        user_template = '{}'

        # delete old vhost and user
        old_vhost = vhost_template.format(model.key)
        old_user = user_template.format(model.key)

        resp = rabbitmq.delete_vhost(old_vhost)
        resp = rabbitmq.delete_user(old_user)

        # add new vhost and user
        new_vhost = vhost_template.format(key)
        new_user = user_template.format(key)
        vhost_kwargs = {"description": "For model ID {}".format(model.id), "tags": "production", "tracing": False}
        resp = rabbitmq.add_vhost(new_vhost, vhost_kwargs)
        resp = rabbitmq.update_user(vhost=new_vhost, user=new_user)

    for k, v in kwargs.items():
        setattr(model, k, v)
    db.session.commit()

    return model


def delete_model(model_id):
    model = Model.query.get(id=model_id).first()
    db.session.delete(model)
    db.session.commit()


def add_model_template(url, model_id, template_id):
    dataurl = DataUrl.query.filter_by(url=url).first()
    mt = ModelTemplate.query.filter_by(model_id=model_id, dataurl_id=dataurl.id, template_id=template_id).first()
    if not mt:
        mt = ModelTemplate(model_id=model_id, dataurl_id=dataurl.id, template_id=template_id)
        db.session.add(mt)
        db.session.commit()
    return mt


def get_model(id=None, source_id=None, project_id=None, name=None):
    if id:
        return Model.query.filter_by(id=id).first()
    elif source_id and name:
        study = get_study(project_id=project_id, dataurl_id=source_id)
        return Model.query.filter_by(study_id=study.id, name=name).first()
    else:
        return None


def get_active_network_model(dataurl_id, network_id):
    network_model = NetworkModel.query.filter_by(
        dataurl_id=dataurl_id,
        network_id=network_id,
        active=True
    ).first()
    return network_model


def get_models(dataurl_id=None, model_ids=None, project_id=None, network_ids=None, scope='public', user_id=None):
    study = get_study(dataurl_id=dataurl_id, project_id=project_id)
    # if project_id is not None and network_ids is not None:
    #     network_models = NetworkModel.query.filter_by(dataurl_id=dataurl_id).filter(
    #         NetworkModel.network_id.in_(network_ids)).all() if network_ids else []
    #     model_ids = [nm.model_id for nm in network_models]
    #     models = Model.query.filter(Model.id.in_(model_ids)) if model_ids else []
    # elif project_id:
    if project_id:
        models = Model.query.filter_by(study_id=study.id).all()
    elif model_ids is not None:
        models = Model.query.filter(Model.id.in_(model_ids)).all() if model_ids else []
    elif user_id and scope == 'private':
        models = Model.query.filter_by(scope=scope, user_id=user_id).all()
    else:
        models = Model.query.filter_by(scope=scope).all()
    ret = []
    for model in models:
        m = model.to_json(include_templates=True, include_network_ids=True)
        m['project_id'] = project_id
        ret.append(m)
    return ret
