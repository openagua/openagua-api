from flask import request, jsonify, g
from flask_restx import Resource, fields

from openagua.lib.favorites import get_favorites, validate_favorites, add_update_favorite, delete_favorite
from openagua.lib.users import get_dataurl

from openagua.apis import api

favorite_fields = api.model('Favorite', {
    'network_id': fields.String,
    'favorite': fields.String
})


@api.route('/favorites')
class Favorites(Resource):
    @api.doc(description='Get favorites associated with a network')
    @api.param('network_id', 'Network ID (required)')
    @api.param('project_id', 'Project ID (optional; used to speed up lookup)')
    def get(self):
        study_id = g.study.id if g.study else None
        dataurl = get_dataurl(g.conn.url) if not study_id else None
        dataurl_id = dataurl.id if dataurl else None
        network_id = request.args.get('network_id', type=int)
        project_id = request.args.get('project_id', type=int) or g.project_id
        if not study_id and not project_id:
            network = g.conn.call('get_network', network_id, include_resources=False, summary=True,
                                  include_data=False)
            project_id = network['project_id']
        all_favorites = get_favorites(dataurl_id=dataurl_id, study_id=study_id, project_id=project_id,
                                      network_id=network_id)
        validated_favorites = validate_favorites(conn=g.conn, network_id=network_id, favorites=all_favorites)
        return jsonify(favorites=validated_favorites)

    @api.doc(description='Add a favorite', body=favorite_fields)
    def post(self):
        study_id = g.study and g.study.id

        network_id = request.json.get('network_id')
        favorite = request.json.get('favorite')

        # TODO: fix this
        favorite['filters']['attr_data_type'] = 'timeseries'

        ret = add_update_favorite(study_id=study_id, network_id=network_id, favorite=favorite)

        return jsonify(favorite=ret.to_json())


@api.route('/favorites/<int:favorite_id>')
class Favorite(Resource):
    @api.doc(description='Update a favorite')
    def put(self, favorite_id):
        study_id = g.study and g.study.id
        favorite = request.json.get('favorite')
        # TODO: fix this
        favorite['filters']['attr_data_type'] = 'timeseries'

        ret = add_update_favorite(study_id=study_id, favorite_id=favorite_id, favorite=favorite)

        return jsonify(favorite=ret.to_json())

    @api.doc(description='Delete a favorite')
    def delete(self, favorite_id):
        result = delete_favorite(favorite_id=favorite_id)
        return jsonify(error=result)
