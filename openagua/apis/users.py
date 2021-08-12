import requests
from flask import jsonify, g
from flask_restx import Resource
from openagua.security import current_user
# from flask_restx import Resource, reqparse
#
# from openagua.security import login_required
# from openagua.lib.users import get_user_settings, get_user_setting, save_user_settings
from openagua.lib.users import get_datausers, get_dataurl_by_id
from openagua.models import User

from openagua.apis import api0, api


@api0.route('/roles')
def get_roles():
    roles = g.conn.call('get_all_roles')
    return jsonify(roles=roles)


@api.route('/user/<int:user_id>')
class UserValidation(Resource):

    @api.doc(description='Get a single user')
    def get(self, user_id):
        if user_id != current_user.id:
            return '', 500

        user = User.query.filter_by(id=user_id).first()
        ret_user = user.to_json()
        ret_user['id'] = user_id
        return jsonify(user=ret_user)


@api.route('/user/<int:user_id>/sources')
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


# @api.route('/setting/<int:user_id>')
# class Setting(Resource):
#     def get(self, user_id, key):
#         user_setting = get_user_setting(user_id, key)
#         return jsonify(setting=user_setting)
