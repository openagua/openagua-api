from flask import g, request, current_app, session
from openagua.security import current_user
from openagua.connection import HydraConnection, root_connection
from openagua.lib.users import get_datauser
from openagua.lib.studies import load_active_study


def _load_active_study():
    g.dataurl_id = request.args.get('sourceId', type=int) or request.json and request.json.get(
        'sourceId') or request.form and request.form.get('sourceId', type=int)
    g.project_id = request.args.get('projectId', type=int) or request.json and request.json.get('projectId')
    load_active_study(dataurl_id=g.dataurl_id, project_id=g.project_id)

    return


def _load_datauser(url=None, user_id=None, source_id=None):
    datauser = None
    g.source_id = source_id or request.args.get('sourceId', type=int) or request.json and request.json.get(
        'sourceId') or request.form and request.form.get('sourceId')

    # get the user_id
    if not user_id and not current_user.is_anonymous:
        user_id = current_user.id

        if g.source_id:
            datauser = get_datauser(user_id=user_id, dataurl_id=g.source_id)
        else:
            url = url or request.args.get('url') or \
                  request.json and request.json.get('url') or \
                  request.form.get('url') or \
                  session.get('data_url')
            if url or not g.get('datauser'):
                url = url or current_app.config['DATA_URL']
                # session['data_url'] = None # this should be for one time use, if used at all
                datauser = get_datauser(user_id=user_id, url=url) if url else None

    g.datauser = datauser
    return None


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
            # key=app.config['SECRET_ENCRYPT_KEY'],
            app_name=current_app.config.get('APP_NAME')
        )
    else:
        g.conn = None

    return
