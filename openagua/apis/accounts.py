from flask import current_app, g, request, jsonify
from flask_restx import Namespace, Resource

from openagua.security import current_user
from openagua.lib.account import update_password

from openagua.lib.account import get_data_databases, add_database, update_database, remove_database, get_api_keys, \
    delete_api_key

api = Namespace(
    'Accounts API',
    path='/accounts',
    description='Operations related to user accounts',
)


@api.route('/passwords', doc=False)
class Passwords(Resource):

    @api.doc(
        description='Update a password'
    )
    def put(self):
        user_id = current_user.id
        old_password = request.json.get('password')
        new_password = request.json.get('new_password')
        hydra_user_id = g.conn.user_id
        result = update_password(user_id, hydra_user_id, old_password, new_password)
        if result:
            return '', 204
        else:
            return 'Password incorrect', 422


@api.route('/databases', doc=False)
class Databases(Resource):
    def get(self):
        databases = get_data_databases(current_user.id, current_app.config.get('DATA_URL'))
        return jsonify(databases)

    def post(self):
        result, error = add_database(
            current_user.id,
            url=request.json['url'],
            username=request.json['username'],
            password=request.json['password'],
            key=current_app.config['SECRET_ENCRYPT_KEY']
        )

        return jsonify(result)


@api.route('/databases/<string:url>', doc=False)
class Database(Resource):

    @api.doc(
        description='Update an external database URL'
    )
    def put(self, url):
        result, error = update_database(
            current_user.id,
            url=request.json['url'],
            username=request.json['username'],
            password=request.json['password'],
            key=current_app.config['SECRET_ENCRYPT_KEY']
        )

        return jsonify(result)

    @api.doc(
        description='Delete an external database URL'
    )
    def delete(self, url):
        remove_database(
            user_id=current_user.user_id,
            url=url,
        )
        return '', 204


@api.route('/api_keys', doc=False)
class Tokens(Resource):

    @api.doc(
        description='Get user tokens'
    )
    def get(self):
        tokens = get_api_keys(current_user.id)
        return jsonify(tokens=tokens)

    @api.doc(
        description='Add a user token'
    )
    def post(self):
        full_token = current_user.generate_api_key()
        token = full_token.split('.')[0]
        return jsonify(token=token, full_token=full_token)


@api.route('/api_keys/<string:token>', doc=False)
class Token(Resource):

    @api.doc(
        description='Delete a user token'
    )
    def delete(self, token):
        delete_api_key(current_user.id)
        return '', 204

# @apis.route('/authorize_box')
# def authorize_box():
#     # Create new OAuth client & csrf token
#     oauth = OAuth2(
#         client_id=current_app.config.get('BOX_CLIENT_ID'),
#         client_secret=current_app.config.get('BOX_CLIENT_SECRET')
#     )
#     # csrf_token = ''
#     global csrf_token
#     redirect_uri = request.host + '/box_authorization'
#     auth_url, csrf_token = oauth.get_authorization_url(redirect_uri)
#
#     return redirect(auth_url)
#
#
# # https://developer.box.com/docs/authenticate-with-oauth-2
# # Fetch access token and make authenticated request
# @apis.route('/box_authorization')
# def capture():
#     # Capture auth code and csrf token via state
#     code = request.args.get('code')
#     state = request.args.get('state')
#
#     oauth = OAuth2(
#         client_id=current_app.config.get('BOX_CLIENT_ID'),
#         client_secret=current_app.config.get('BOX_CLIENT_SECRET')
#     )
#
#     # csrf_token = 0  # get csrf token from db or redis
#
#     # If csrf token matches, fetch tokens
#     assert state == csrf_token
#
#     access_token, refresh_token = oauth.authenticate(code)
#
#     # PERFORM API ACTIONS WITH ACCESS TOKEN
#
#     return redirect('http://127.0.0.1:5000')
