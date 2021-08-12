from flask import request, session, g, flash, url_for, jsonify, make_response

from openagua.security import login_required, logout_user
from openagua.security.authentication import api_authentication_required
from openagua.lib.studies import load_active_study
from openagua.decorator_utilities import _load_datauser, _make_connection

from openagua import app


@app.before_request
def _load_active_study():
    g.dataurl_id = request.args.get('sourceId', type=int) or request.json and request.json.get(
        'sourceId') or request.form and request.form.get('sourceId', type=int)
    g.project_id = request.args.get('projectId', type=int) or request.json and request.json.get('projectId')
    load_active_study(dataurl_id=g.dataurl_id, project_id=g.project_id)


@app.before_request
@login_required
def _before_most_requests():
    if request.method == 'OPTIONS':  # pre-flight request
        return
    g.dataurl_id = request.args.get('sourceId', type=int) or request.json and request.json.get(
        'sourceId') or request.form.get('sourceId')
    g.project_id = request.args.get('projectId', type=int) or request.json and request.json.get('projectId')
    g.network_id = request.args.get('networkId', type=int) or request.json and request.json.get('networkId')
    g.template_id = request.args.get('templateId', type=int) or request.json and request.json.get('templateId')

    load_active_study(dataurl_id=g.dataurl_id, project_id=g.project_id)
    _load_datauser()

    is_public_user = request.args.get('user') == 'public' or request.args.get('public') == 'true'
    _make_connection(is_public_user)

    return


@app.before_request
@api_authentication_required
def _before_api_requests():
    if request.method == 'OPTIONS':  # pre-flight request
        return
    args = request.args
    body = request.get_json() or {}
    form = request.form
    g.dataurl_id = args.get('sourceId', type=int) or body.get('sourceId') or form.get('sourceId')
    g.project_id = args.get('projectId', type=int) or body.get('projectId')
    g.network_id = args.get('networkId', type=int) or body.get('networkId')
    g.template_id = args.get('templateId', type=int) or body.get('templateId')

    load_active_study(dataurl_id=g.dataurl_id, project_id=g.project_id)
    _load_datauser()

    g.is_public_user = args.get('user') == "public" or args.get('scope') == 'public' or args.get('public') == 'true'
    _make_connection(g.is_public_user)


@app.after_request
def _check_data_session(response):
    if hasattr(g, 'invalid_data_session') or response.status_code == 511:
        logout_user()
        session['_flashes'] = []
        flash("Oops! Your data session appears to be invalid. Please login again.", "danger")
        return make_response(jsonify(url=url_for('security.logout')), 511)

    return response
