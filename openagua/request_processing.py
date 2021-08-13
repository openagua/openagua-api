from flask import session, g, flash, url_for, jsonify, make_response

from openagua.security import logout_user

from openagua import app


# @login_required
# def load_active_study():
#     g.dataurl_id = request.args.get('sourceId', type=int) or request.json and request.json.get(
#         'sourceId') or request.form and request.form.get('sourceId', type=int)
#     g.project_id = request.args.get('projectId', type=int) or request.json and request.json.get('projectId')
#     _load_active_study(dataurl_id=g.dataurl_id, project_id=g.project_id)
