import json

from flask import current_app as app

from cryptography.fernet import Fernet

from hydra_base import HydraError

from openagua.models import DataUrl, DataUser, User
from openagua.connection import HydraConnection
from openagua import db


def get_users(user_ids):
    users = User.query.filter(User.id.in_(user_ids)).all() if user_ids else []
    return {user.id: user.to_json() for user in users}


def get_user(user_id):
    user = User.query.filter(User.id == user_id).one()
    return user.to_json()


def get_user_settings(user_id):
    user = User.query.filter(User.id == user_id).one()
    return user.get_settings()


def get_user_setting(user_id, key):
    user = User.query.filter(User.id == user_id).one()
    user_settings = user.get_settings()
    return user_settings.get(key, None)


def save_user_setting(user_id, key, value):
    user = User.query.filter(User.id == user_id).one()
    settings = user.settings
    settings = json.loads(user.settings) if settings else {}
    settings[key] = value
    user.settings = json.dumps(settings)
    db.session.commit()


def save_user_settings(user_id, settings):
    user = User.query.filter(User.id == user_id).one()
    if isinstance(settings, object):
        user.settings = json.dumps(settings)
    else:
        user.settings = settings
    db.session.commit()


def update_socketid(user, value):
    user.socketid = value
    db.session.commit()


def update_datauser_sessionid(datauser, session_id):
    return update_datauser(
        datauser,
        sessionid=session_id
    )


def add_dataurl(url):
    dataurl = DataUrl.query.filter(DataUrl.url == url).first()
    if dataurl is None:  # this should be done via manage.py, not here
        dataurl = DataUrl(url=url)
        db.session.add(dataurl)
        db.session.commit()
    return DataUrl.query.filter(DataUrl.url == url).first()


def register_datauser(**kwargs):
    kwargs.update(
        url=app.config['DATA_URL'],
        admin_username=app.config['DATA_ROOT_USERNAME'],
        admin_password=app.config['DATA_ROOT_PASSWORD'],
        key=app.config['SECRET_ENCRYPT_KEY']
    )

    # URL record for Hydra Platforms
    dataurl = add_dataurl(kwargs['url'])

    # add to Hydra Platform database
    conn = HydraConnection(url=kwargs['url'])
    data_user = conn.update_add_data_user(
        kwargs['admin_username'],
        kwargs['admin_password'],
        kwargs['username'],
        kwargs['password']
    )

    # add Hydrauser record
    kwargs['dataurl_id'] = dataurl.id
    datauser = add_update_datauser(
        user_id=kwargs['user_id'],
        dataurl_id=dataurl.id,
        username=kwargs['username'],
        userid=data_user.id,
        # password=kwargs.get('password', ''),
        key=kwargs['key']
    )

    return datauser


def add_update_datauser(**kwargs):
    datauser = DataUser.query.filter_by(
        username=kwargs['username'],
        dataurl_id=kwargs['dataurl_id']
    ).first()
    if datauser:  # update datauser
        datauser = update_datauser(datauser, **kwargs)
    else:  # add datauser
        datauser = add_datauser(**kwargs)
    return datauser


def update_datauser(datauser, **kwargs):
    if 'password' in kwargs:
        kwargs['password'] = encrypt(kwargs['password'], kwargs['key'])
    fields = ['user_id', 'dataurl_id', 'username', 'userid', 'password', 'sessionid']
    for field in fields:
        if field in kwargs:
            exec('datauser.{} = "{}"'.format(field, kwargs[field]))
    db.session.commit()
    return datauser


def add_datauser(**kwargs):
    if 'password' in kwargs:
        kwargs['password'] = encrypt(kwargs['password'], kwargs['key'])
    datauser = DataUser.query.filter_by(
        username=kwargs['username'],
        dataurl_id=kwargs['dataurl_id']
    ).first()
    if datauser is None:
        datauser = DataUser(
            user_id=kwargs['user_id'],
            dataurl_id=kwargs['dataurl_id'],
            userid=kwargs['userid'],
            username=kwargs['username'],
            password=kwargs.get('password', ''),
        )
        db.session.add(datauser)
        db.session.commit()

    return datauser


def delete_datauser(user_id, dataurl_id):
    datauser = DataUser.query.filter_by(
        user_id=user_id,
        dataurl_id=dataurl_id
    ).first()
    db.session.delete(datauser)
    db.session.commit()


def get_datausers(**kwargs):
    url = kwargs.get('url')
    dataurl_id = kwargs.get('dataurl_id')
    user_id = kwargs.get('user_id')
    if url:
        dataurl = get_dataurl(url)
        datausers = DataUser.query.filter_by(
            dataurl_id=dataurl.id
        ).all()
    elif dataurl_id:
        datausers = DataUser.query.filter_by(
            dataurl_id=dataurl_id
        ).all()
    elif user_id:
        datausers = DataUser.query.filter_by(
            user_id=user_id
        ).all()
    else:
        datausers = None
    return datausers


def get_datauser(id=None, user_id=None, username=None, url=None, dataurl_id=None):
    dataurl = None
    datauser = None

    if id:
        datauser = DataUser.query.filter_by(id=id).first()
    else:
        if url or username:
            dataurl = get_dataurl(url)
        elif dataurl_id:
            dataurl = get_dataurl_by_id(dataurl_id)
        if dataurl:
            if username:
                datauser = DataUser.query.filter_by(
                    username=username,
                    dataurl_id=dataurl.id
                ).first()
            elif user_id:
                datauser = DataUser.query.filter_by(
                    user_id=user_id,
                    dataurl_id=dataurl.id
                ).first()

    if datauser:
        dataurl = get_dataurl_by_id(datauser.dataurl_id)
        datauser.data_url = dataurl.url

    return datauser


def get_client_user(user):
    client_user = user.to_json()
    client_user['id'] = user.id
    client_user['is_admin'] = len(set(user.roles) | {'admin', 'superuser'}) > 0
    return client_user


def get_dataurl(url):
    dataurl = DataUrl.query.filter_by(url=url or '').first()
    return dataurl


def get_dataurl_by_id(id):
    dataurl = DataUrl.query.filter_by(id=id).first()
    return dataurl


def encrypt(text, key):
    f = Fernet(key)
    return f.encrypt(str.encode(text)).decode()


def update_user_network_settings(datauser_id, network_id, settings):
    datauser = get_datauser(id=datauser_id)
    network_id = str(network_id)
    user_settings = json.loads(datauser.settings or '{}')
    user_settings['networks'] = user_settings.get('networks', {})
    user_settings['networks'][network_id] = user_settings['networks'].get(network_id, {})
    user_settings['networks'][network_id].update(settings)
    datauser.settings = json.dumps(user_settings)
    db.session.commit()
