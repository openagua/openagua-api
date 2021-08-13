from functools import wraps

from flask import g, request, current_app
from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth, MultiAuth
from flask_login.config import EXEMPT_METHODS

EXEMPT_ENDPOINTS = {'.doc', '.specs'}

from openagua.models import User
from openagua.request_functions import _make_connection
from flask_login import current_user

from .decorators import _check_http_auth, _check_api_key_auth, abort

basic_auth = HTTPBasicAuth()
api_key_auth = HTTPTokenAuth(header='X-API-KEY')


# see: https://blog.miguelgrinberg.com/post/restful-authentication-with-flask


@basic_auth.verify_password
def verify_password(username_or_token, password_or_key):
    # first try to authenticate by token
    user = User.verify_auth_token(username_or_token)
    if not user:
        # second, try to authenticate by API key
        user = User.verify_api_key(password_or_key)
    if not user:
        # finally, try to authenticate with username/password
        # TODO: update to query by username, rather than email
        user = User.query.filter_by(email=username_or_token).first()
        if not user or not user.verify_password(password_or_key):
            return False

    g.user = user

    _make_connection(user_id=user.id)

    return True


@api_key_auth.verify_token
def verify_api_key(api_key):
    user = User.verify_api_key(api_key)
    g.user = user
    if user:
        _make_connection(user_id=user.id)

    return True


auth = MultiAuth(api_key_auth, basic_auth)


def api_authentication_required(func):
    '''

    NOTE: This is originally from flask_login/utils.py. It has been modified to check for X-API-KEY in the header

    If you decorate a view with this, it will ensure that the current user is
    logged in and authenticated before calling the actual view. (If they are
    not, it calls the :attr:`LoginManager.unauthorized` callback.) For
    example::

        @app.route('/post')
        @login_required
        def post():
            pass

    If there are only certain times you need to require that your user is
    logged in, you can do so with::

        if not current_user.is_authenticated:
            return current_app.login_manager.unauthorized()

    ...which is essentially the code that this function adds to your views.

    It can be convenient to globally turn off authentication when unit testing.
    To enable this, if the application configuration variable `LOGIN_DISABLED`
    is set to `True`, this decorator will be ignored.

    .. Note ::

        Per `W3 guidelines for CORS preflight requests
        <http://www.w3.org/TR/cors/#cross-origin-request-with-preflight-0>`_,
        HTTP ``OPTIONS`` requests are exempt from login checks.

    :param func: The view function to decorate.
    :type func: function
    '''

    @wraps(func)
    def decorated_view(*args, **kwargs):
        if request.method in EXEMPT_METHODS:
            return func(*args, **kwargs)
        elif _check_api_key_auth():
            return func(*args, **kwargs)
        elif _check_http_auth():
            return func(*args, **kwargs)
        elif current_app.login_manager._login_disabled:
            return func(*args, **kwargs)
        elif request.blueprint and request.endpoint.replace(request.blueprint, '') in EXEMPT_ENDPOINTS:
            return func(*args, **kwargs)
        elif not current_user.is_authenticated:
            return abort(401)
        return func(*args, **kwargs)

    return decorated_view
