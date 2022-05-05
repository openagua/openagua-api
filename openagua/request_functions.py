from flask import g, request, current_app, session
from openagua.security import current_user
from openagua.connection import HydraConnection, root_connection
from openagua.lib.users import get_datauser
from openagua.lib.studies import load_active_study


def get_value_from_request(key, dtype=int, default=None):
    args = request.args
    body = request.json if request.method in ['POST', 'PUT', 'PATCH'] else {}
    form = request.form
    return args.get(key, type=dtype) or body.get(key) or form.get(key, type=dtype) or default


def _load_request_params():
    g.dataurl_id = get_value_from_request('sourceId', default=1)
    g.project_id = get_value_from_request('projectId')
    g.network_id = get_value_from_request('networkId')
    g.template_id = get_value_from_request('templateId')


def _load_active_study():
    g.dataurl_id = get_value_from_request('sourceId', default=1)
    g.project_id = get_value_from_request('projectId')
    load_active_study(dataurl_id=g.dataurl_id, project_id=g.project_id)

    return


def _load_datauser(url=None, user_id=None, source_id=None):
    datauser = None
    if source_id:
        g.source_id = source_id
    elif not hasattr(g, 'source_id'):
        g.source_id = get_value_from_request('sourceId', default=1)

    if not user_id and not current_user.is_anonymous:
        user_id = current_user.id

        if g.source_id:
            datauser = get_datauser(user_id=user_id, dataurl_id=g.source_id)
        else:
            url = url or get_value_from_request('url', dtype=str, default=session.get('data_url'))
            if url or not g.get('datauser'):
                url = url or current_app.config['DATA_URL']
                datauser = get_datauser(user_id=user_id, url=url) if url else None

    g.datauser = datauser

    return


def _make_connection(is_public_user=False, user_id=None):
    if is_public_user:
        g.conn = root_connection()
        return
    elif user_id and not g.get('datauser'):
        _load_datauser(user_id=user_id)
    make_user_connection()

    return


def make_root_connection():
    g.conn = root_connection()


def make_user_connection():
    if g.get('datauser'):
        g.conn = HydraConnection(
            url=g.datauser.data_url,
            session_id=g.datauser.sessionid,
            username=g.datauser.username,
            user_id=g.datauser.userid,
            app_name=current_app.config.get('APP_NAME')
        )
    else:
        g.conn = None

    return
