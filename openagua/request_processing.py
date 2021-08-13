from flask import session, g, flash, url_for, jsonify, make_response

from openagua.security import logout_user

from openagua import app


# @login_required
# def load_active_study():
#     g.dataurl_id = request.args.get('sourceId', type=int) or request.json and request.json.get(
#         'sourceId') or request.form and request.form.get('sourceId', type=int)
#     g.project_id = request.args.get('projectId', type=int) or request.json and request.json.get('projectId')
#     _load_active_study(dataurl_id=g.dataurl_id, project_id=g.project_id)

@app.after_request
def check_data_session(response):
    if hasattr(g, 'invalid_data_session') or response.status_code == 511:
        logout_user()
        session['_flashes'] = []
        flash("Oops! Your data session appears to be invalid. Please login again.", "danger")
        return make_response(jsonify(url=url_for('security.logout')), 511)

    return response
