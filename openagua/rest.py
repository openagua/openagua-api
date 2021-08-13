from functools import wraps
from flask_restx import Resource as FlaskResource
from flask import request, g

from openagua.security import login_required
from openagua.lib.studies import load_active_study
from openagua.request_functions import _load_datauser, _make_connection


def load_study(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        g.dataurl_id = request.args.get('sourceId', type=int) or request.json and request.json.get(
            'sourceId') or request.form.get('sourceId')
        g.project_id = request.args.get('projectId', type=int) or request.json and request.json.get('projectId')
        g.network_id = request.args.get('networkId', type=int) or request.json and request.json.get('networkId')
        g.template_id = request.args.get('templateId', type=int) or request.json and request.json.get('templateId')

        # _load_active_study()
        load_active_study(dataurl_id=g.dataurl_id, project_id=g.project_id)
        _load_datauser()

        is_public_user = request.args.get('user') == "public"
        _make_connection(is_public_user)

    return wrapper


class Resource(FlaskResource):
    method_decorators = [login_required, load_study]  # applies to all inherited resources
