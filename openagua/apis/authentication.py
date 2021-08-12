from flask import jsonify, g, request
# from flask_restx import Resource, reqparse
from functools import wraps
#
from openagua.security import current_user
from openagua.security.decorators import http_auth_required
# from openagua.lib.users import get_user_settings, get_user_setting, save_user_settings

from openagua.apis import auth


def anonymous_user_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if current_user.is_authenticated:
            return None
        return f(*args, **kwargs)

    return wrapper


@auth.route('/auth0/jwt', methods=['GET'])
@http_auth_required
def authenticate():

    jwt = current_user.encode_auth_token()

    return jwt, 200
