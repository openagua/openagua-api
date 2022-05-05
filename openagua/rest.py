from functools import wraps
from flask_restx import Resource as FlaskResource
from flask import request, g

from openagua.security import login_required
from openagua.lib.studies import load_active_study
from openagua.request_functions import _load_datauser, _make_connection, _load_request_params


def load_study(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        _load_request_params()
        load_active_study(dataurl_id=g.dataurl_id, project_id=g.project_id)
        _load_datauser()

        is_public_user = request.args.get('user') == "public"
        _make_connection(is_public_user)

    return wrapper


class Resource(FlaskResource):
    method_decorators = [login_required, load_study]  # applies to all inherited resources
