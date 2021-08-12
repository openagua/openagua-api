from flask import jsonify, current_app
from flask_restx import Namespace, Resource

api = Namespace('Maps API', path='/maps', description='Operations related to maps.')


@api.route('/tiles_provider', doc=False)
class TilesProviders(Resource):
    def get(self):
        google_key = current_app.config.get('GOOGLE_PLACES_API_KEY')
        mapbox_key = current_app.config.get('MAPBOX_ACCESS_TOKEN')
        preferred_map_provider = current_app.config.get('PREFERRED_MAP_PROVIDER', 'mapbox')
        if google_key and preferred_map_provider == 'google':
            key = google_key
        elif mapbox_key and preferred_map_provider == 'mapbox':
            key = mapbox_key
        else:
            key = None
        return jsonify(provider={'name': preferred_map_provider, 'key': key})
