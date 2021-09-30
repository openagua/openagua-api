import requests
from flask import jsonify, g, request
from flask_restx import Resource, reqparse
from openagua.security import current_user
from openagua.lib.users import get_user_settings, get_user_setting, save_user_settings
from openagua.lib.users import get_datausers, get_dataurl_by_id
from openagua.models import User

from openagua.apis import api0, api


@api0.route('/roles')
def get_roles():
    roles = g.conn.call('get_all_roles')
    return jsonify(roles=roles)


@api.route('/users/<int:user_id>')
class UserValidation(Resource):

    @api.doc(description='Get a single user')
    def get(self, user_id):
        if user_id != current_user.id:
            return '', 500

        user = User.query.filter_by(id=user_id).first()
        ret_user = user.to_json()
        ret_user['id'] = user_id
        return jsonify(user=ret_user)


@api.route('/users/<int:user_id>/sources')
class Sources(Resource):
    def get(self, user_id):
        sources = []
        for datauser in get_datausers(user_id=user_id):
            source = get_dataurl_by_id(datauser.dataurl_id)
            try:
                source.url != 'base' and requests.get(source.url, timeout=3)
                source = source.to_json()
                source['user_id'] = datauser.userid  # id of user on data web service
                sources.append(source)
            except:
                continue

        return jsonify(sources=sources)


@api.route('/users/<int:user_id>/setting/<string:key>')
class Setting(Resource):

    def get(self, user_id, key):
        user_setting = get_user_setting(user_id, key)
        return jsonify(setting=user_setting)

    def post(self, user_id, key):
        user_setting = get_user_setting(user_id, key)
        if user_setting is not None:
            return '', 405

        self.add_or_update(user_id, key)

    def put(self, user_id, key):
        user_setting = get_user_setting(user_id, key)
        if user_setting is None:
            return '', 405

        self.add_or_update(user_id, key)

    def add_or_update(self, user_id, key):
        all_settings = get_user_settings(user_id)
        new_setting = request.json
        all_settings.update({key: new_setting})
        save_user_settings(user_id, all_settings)

        return '', 204

    def delete(self, user_id, key):
        all_settings = get_user_settings(user_id)
        all_settings.pop(key, None)
        save_user_settings(user_id, all_settings)

        return '', 204


@api.route('/users/<int:user_id>/settings')
class Settings(Resource):

    def get(self, user_id):
        user_settings = get_user_settings(user_id)
        return jsonify(user_settings)

    def put(self, user_id):
        new_settings = request.json

        user_settings = get_user_settings(user_id)
        user_settings.update(new_settings)

        save_user_settings(user_id, user_settings)

        return '', 204

# @api.route('/settings/<int:user_id>')
# class Settings(Resource):
#     decorators = [login_required]
#
#     def __init__(self):
#         self.reqparse = reqparse.RequestParser()
#         self.reqparse.add_argument('settings', type=dict, location='json')
#         super(Settings, self).__init__()
#
#     def get(self, user_id):
#         user_settings = get_user_settings(user_id)
#         return jsonify(settings=user_settings)
#
#     def put(self, user_id):
#         args = self.reqparse.parse_args()
#         settings = args.get('settings')
#         save_user_settings(user_id, settings)
#         return '', 204
