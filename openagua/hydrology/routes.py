from flask import current_app, jsonify, request
from openagua.security import current_user
import requests
from math import pow, floor

from openagua.security import login_required
# from openagua.lib.network_editor import add_network_reference
# from openagua import socketio

from . import hydrology


class EarthEngineMap(object):

    def get_earth_engine_map_tile_url(self, dataset, **options):
        ee_image = current_app.ee.Image(dataset)
        threshold = options.get('threshold')
        palette = options.get('palette', '0000FF')
        map_id = None
        if dataset == 'WWF/HydroSHEDS/15ACC':
            user_threshold = request.args.get('threshold', type=int)  # i.e., 0 to 100
            real_threshold = pow(10, (100 - user_threshold) / 100 * 7.5)
            masked = ee_image.updateMask(ee_image.gte(real_threshold))

            threshold = pow(10, (100 - threshold) / 100 * 7.5)

            map_id = masked.getMapId({'palette': palette, 'min': 0, 'max': threshold})

        elif dataset == 'CGIAR/SRTM90_V4':
            range = request.args.getlist('range[]', type=int)
            min = range[0]
            max = range[1]
            map_id = ee_image.getMapId({'min': min, 'max': max})

        tile_url = map_id['tile_fetcher'].url_format
        return tile_url


EEMap = EarthEngineMap()


@hydrology.route('/earth_engine_map', methods=['POST'])
@login_required
def get_facc():
    dataset = request.json.get('dataset')
    options = request.json.get('options', {})
    tile_url = EEMap.get_earth_engine_map_tile_url(dataset, **options)
    return jsonify(tile_url=tile_url)


@hydrology.route('/delineate_point', methods=['POST'])
@login_required
def delineate_point():
    latlng = request.json.get('latlng')
    source_id = request.json.get('sourceId')
    network_id = request.json.get('network_id')
    lat = latlng.get('lat')
    lon = latlng.get('lng')
    res = 15 / 60 / 60
    lat = round(floor(lat / res) * res + res / 2, 6)
    lon = round(floor(lon / res) * res + res / 2, 6)

    hydrology_api_url = current_app.config.get('HYDROLOGY_API_URL')
    key = current_app.config.get('OPENAGUA_API_KEY')
    dest = current_app.config.get('POST_URL') + current_app.config.get('ADD_REFERENCE_LAYER_URL')

    name = request.json.get('name')
    response = requests.post(
        '{}/delineate_catchment'.format(hydrology_api_url),
        json={
            'source_id': source_id,
            'user_id': current_user.id,
            'network_id': network_id,
            'name': name,
            'lat': lat,
            'lon': lon,
            'dest': dest,
            'key': key
        })

    if response.ok:
        return '', 200  # job submitted; will be posted when finished
    else:
        return jsonify(message=response.reason, status=response.status_code)

# @hydrology.route('/delineate_points', methods=['POST'])
# @login_required
# def delineate_points():
#     source_id = request.json.get('source_id')
#     network_id = request.json.get('network_id')
#     pour_points = request.json.get('pour_points')
#     name = request.json['name']
#
#     coords = [tuple(pp.get('coords')) for pp in pour_points]
#     response = requests.post(
#         'http://hydrology.openagua.org/api/delineate_points',
#         json={'coords': coords}
#     )
#
#     if response.ok and 'type' in response.json():
#         geojson = response.json()
#         geojson['properties']['name'] = name
#         for i, feature in enumerate(geojson['features']):
#             feature['properties']['name'] = pour_points[i]['name']
#         network = g.conn.get_network_simple('get_network', network_id)
#         reference = add_network_reference(g.conn, network, geojson)
#         return jsonify(reference=reference, geojson=geojson)
#
#     else:
#         return jsonify(message=response.reason, status=response.status_code)


# @public_api.route('/hydrology/add_watershed', methods=['GET', 'POST'])
# def add_hydrology_reference(key=None, source_id=None, network_id=None, geojson=None):
#     if request.method == 'GET':
#         return 'Method Not Allowed (405)', 405
#     key = key or request.json.get('api_key')
#     if key != current_app.config.get('OPENAGUA_API_KEY'):
#         return '', 403
#
#     feature = geojson or request.json.get('geojson')
#     source_id = source_id or request.json.get('source_id')
#     network_id = network_id or request.json.get('network_id')
#     name = feature.get('properties', {}).get('name')
#
#     feature['properties']['name'] = name
#     features = {
#         'type': 'FeatureCollection',
#         'properties': {'name': name},
#         'features': [feature]
#     }
#
#     network = g.conn.get_network_simple(network_id)
#     reference = {
#         'name': name,
#         'description': "Created by OpenAgua.",
#     }
#     reference = add_network_reference(g.conn, network, reference, geojson=features)
#
#     # add the reference to the client via socketio
#     room = current_app.config['NETWORK_ROOM_NAME'].format(source_id, network_id)
#     event = 'add-reference-layer'
#     socketio.emit(event, reference, room=room)
#
#     return 'success', 200
