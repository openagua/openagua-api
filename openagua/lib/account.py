from flask import current_app

from openagua.models import DataUser, DataUrl, APIKey

from openagua.connection import HydraConnection
from openagua.utils import decrypt
from openagua.lib.users import add_dataurl, add_datauser, update_datauser, delete_datauser, get_datauser

from openagua.security.recoverable import update_password as _update_password
from openagua.security.utils import _datastore
from openagua.connection import root_connection

from openagua import db


def update_password(user_id, hydra_user_id, old_password, new_password):
    user = _datastore.find_user(id=user_id)
    if user.verify_password(old_password):
        # update the OpenAgua user
        _update_password(user, new_password, encode=True, send_email=False)
        # update the Hydra user
        root_conn = root_connection()
        resp = root_conn.call('update_user_password', hydra_user_id, new_password)
        _datastore.commit()
        return True
    else:
        return False


def get_data_databases(user_id, base_url):
    datausers = DataUser.query.filter_by(user_id=user_id).all()

    databases = []
    for datauser in datausers:
        dataurl = DataUrl.query.filter_by(id=datauser.dataurl_id).first()
        if dataurl.url == base_url:
            continue
        databases.append(
            {
                'url': dataurl.url,
                'userid': datauser.userid,
                'username': datauser.username,
                'password': decrypt(datauser.password, current_app.config['SECRET_ENCRYPT_KEY'])
            }
        )

    return databases


def add_database(user_id, **kwargs):
    username = kwargs['username']
    password = kwargs['password']
    try:
        conn = HydraConnection(url=kwargs['url'])
        result = conn.call('login', username, password)
    except:
        return None, "Bad URI"
    else:
        if result != 'OK':
            return None, "Bad username or password"
        else:
            # add dataurl
            dataurl = add_dataurl(kwargs['url'])

            # get data user ID
            data_user = conn.get_user_by_name(username)

            # add datauser
            add_datauser(
                user_id=user_id,
                dataurl_id=dataurl.id,
                userid=data_user.id,
                **kwargs
            )

    return {'userid': data_user.id}, None


def update_database(user_id, **kwargs):
    username = kwargs['username']
    password = kwargs['password']
    try:
        conn = HydraConnection(url=kwargs['url'])
        result = conn.call('login', username, password)
    except:
        return None, "Bad URI"
    else:
        if result != 'OK':
            return None, "Bad username or password"
        else:
            # add dataurl
            dataurl = add_dataurl(kwargs['url'])

            # get data user ID
            data_user = conn.get_user_by_name(username)
            datauser = get_datauser(
                dataurl_id=dataurl.id,
                user_id=user_id
            )

            # add datauser
            update_datauser(
                datauser,
                user_id=user_id,
                dataurl_id=dataurl.id,
                userid=data_user.id,
                **kwargs
            )

    return {'userid': data_user.id}, None


def remove_database(user_id, url):
    dataurl = DataUrl.query.filter_by(url=url).first()
    delete_datauser(user_id=user_id, dataurl_id=dataurl.id, username=username)


def get_api_keys(user_id):
    keys = APIKey.query.filter_by(user_id=user_id).all()
    prefixes = [key.id.split('.')[0] for key in keys]

    return prefixes


def delete_api_key(user_id):
    apikey = APIKey.query.filter_by(user_id=user_id).first()
    if apikey:
        db.session.delete(apikey)
        db.session.commit()
