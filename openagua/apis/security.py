from flask import request, session, jsonify, Blueprint, make_response
from openagua.security import login_user, logout_user, current_user
from flask_wtf.csrf import generate_csrf
from flask_restx import Namespace, Resource

from openagua import db
from openagua.models import User
from openagua.security.registerable import register_user
from openagua.security.confirmable import send_confirmation_instructions, confirm_email_token_status, confirm_user
from openagua.security.recoverable import send_reset_password_instructions, reset_password_token_status, update_password
from openagua.security.decorators import anonymous_user_required
from openagua.lib.users import register_datauser, get_client_user

auth0 = Blueprint('auth', __name__, url_prefix='/auth0')

auth = Namespace(
    'Authentication API',
    path='/auth',
    description='Operations related to authentication'
)


# @cross_origin(origins=auth_origins, supports_credentials=False, methods=['GET'],
#               allow_headers=['XSRF-TOKEN', 'X-XSRF-TOKEN'])
# @anonymous_user_required
@auth0.route('/csrf_token')
def get_crsf_token():
    csrf_token = session.get('csrf_token', None)
    if csrf_token is None:
        csrf_token = generate_csrf()
    return jsonify(csrf_token=csrf_token)


@auth0.route('/cookie')
def get_cookie():
    res = make_response("Setting a cookie")
    for key, value in session.items():
        res.set_cookie(key, str(value), max_age=60 * 60 * 24 * 365 * 2)
    return res


@auth0.route('/check_login')
def check_login():
    if current_user.is_authenticated:
        user = User.query.filter_by(id=current_user.id).first()
        client_user = get_client_user(user)
    else:
        client_user = None
    return jsonify(user=client_user)


# reference: https://dev.to/paurakhsharma/series/3672
@auth.route('/login')
class Login(Resource):
    @anonymous_user_required
    def post(self):
        body = request.get_json()
        # csrf_token = body.get('csrf_token')
        # try:
        #     validate_csrf(csrf_token)
        # except:
        #     return '', 405

        email = body.get('email')
        user = User.query.filter_by(email=email).first()

        authorized = user and user.verify_password(body.get('password'))  # and valid_csrf_token
        if not authorized:
            return {'error': 'Email or password invalid'}, 401

        remember = body.get('remember', False)

        login_user(user, remember=remember)
        generate_csrf()
        # session_json = {k: str(v) for k, v in session.items()}

        client_user = get_client_user(user)

        return jsonify(user=client_user)


@auth0.route('/register', methods=['POST'])
@anonymous_user_required
def register():
    body = request.get_json()
    email = body.get('email')
    user = User.query.filter_by(email=email).first()
    if user:
        return 'Sorry, this email is already registered.', 409

    password = body.get('password')

    if body.pop('g-recaptcha-response', True):

        kwargs = body  # openagua
        user = register_user(**kwargs)  # openagua

        # Register on Hydra Platform
        # from openagua.lib.users import register_datauser
        register_datauser(
            username=email,
            password=password,
            user_id=user.id,
        )

        # Commented out for now. We could reimplement later
        # if not _security.confirmable or _security.login_without_confirmation:
        #     after_this_request(_commit)
        #     login_user(user)

        ret_user = user.to_json()
        return jsonify(user=ret_user)

    else:
        return 'Are you a robot?', 409


@auth0.route('/validate_email', methods=['GET'])
@anonymous_user_required
def validate_email():
    email = request.args.get('email', '')
    user = User.query.filter_by(email=email).first()
    if user:
        return '', 200
    else:
        return '', 404


# reference: https://dev.to/paurakhsharma/series/3672
@auth0.route('/login', methods=['POST'])
@anonymous_user_required
def login():
    body = request.get_json()
    # csrf_token = body.get('csrf_token')
    # try:
    #     validate_csrf(csrf_token)
    # except:
    #     return '', 405

    user = User.query.filter_by(email=body.get('email')).first()

    authorized = user and user.verify_password(body.get('password'))  # and valid_csrf_token
    if not authorized:
        return {'error': 'Email or password invalid'}, 401

    remember = body.get('remember', False)

    login_user(user, remember=remember)
    generate_csrf()
    session_json = {k: str(v) for k, v in session.items()}

    client_user = get_client_user(user)

    return jsonify(user=client_user, cookie=session_json)


@auth0.route('/confirm', methods=['POST'])
@anonymous_user_required
def confirm():
    token = request.json.get('token')
    if token:
        expired, invalid, user = confirm_email_token_status(token)
        if expired:
            return 'expired', 409
        elif invalid:
            return 'invalid', 409
        elif user.confirmed_at:
            return 'confirmed', 409
        # if user != current_user:
        #     logout_user()
        #     login_user(user)
        confirm_user(user)
        db.session.commit()
        return '', 200

    email = request.json.get('email')
    user = User.query.filter_by(email=email).one()
    if user and not user.confirmed_at:
        origin = request.json.get('origin')
        send_confirmation_instructions(user, origin=origin)
        return '', 200
    else:
        return '', 400


@auth0.route('/reset', methods=['POST'])
@anonymous_user_required
def reset_password():
    body = request.get_json()
    email = body.get('email')
    password = body.get('password')
    token = body.get('token')

    if email:
        user = User.query.filter_by(email=email).first()
        if user:
            origin = request.json.get('origin')
            send_reset_password_instructions(user, origin=origin)
            return '', 200
        else:
            return 'unknown', 409
    elif password and token:
        expired, invalid, user = reset_password_token_status(token)

        if expired:
            return 'expired', 409
        elif invalid:
            return 'invalid', 409
        else:
            update_password(user, password)
            db.session.commit()

            # Register (or update registration) on Hydra Platform
            # from openagua.lib.users import register_datauser
            register_datauser(
                username=user.email,
                password=password,
                user_id=user.id,
            )

            return '', 200

    else:
        return 'unknown', 409


@auth0.route('/logout', methods=['POST'])
def logout():
    logout_user()
    return '', 200
