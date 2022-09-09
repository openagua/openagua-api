from flask import jsonify, request, current_app
from flask_restx import Resource, Namespace
from openagua.lib.integrations import get_key_value

api = Namespace('GUI', path='/gui')


@api.route('/keys', doc=False)
class Keys(Resource):
    def get(self):
        names = request.args.getlist('names[]')
        keys = {key: get_key_value(key) for key in names}
        return jsonify(keys)


@api.route('/population_grid', doc=False)
class PopulationGrid(Resource):

    def get(self):
        density2020 = current_app.ee.Image('CIESIN/GPWv4/unwpp-adjusted-population-density/2020')
        palette = 'ffffde,509b92,03008d'
        logDensity = density2020.where(density2020.gt(0), density2020.log())
        # combined = composite(colorized, background)
        # antiAliased = combined.reduceResolution(ee.Reducer.mean(), true)
        antiAliased = logDensity.reduceResolution(current_app.ee.Reducer.mean(), True)
        image = antiAliased.getMapId({'min': 0, 'max': 8, 'palette': palette})
        # image = logDensity.getMapId({'min': 0, 'max': 8, 'palette': 'ffffde'})
        # image = logDensity.getMapId()
        url = image["tile_fetcher"]._url_format  # token no longer needed
        return jsonify(url)
