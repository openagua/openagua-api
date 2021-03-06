from flask import request, jsonify, g
from flask_restx import Resource
from openagua.lib.scenarios import delete_data_scenario

from openagua.apis import api


@api.route('/scenarios')
class Scenarios(Resource):

    @staticmethod
    def post():
        incoming_scenario = request.json['scenario']
        network_id = request.json.get('network_id')
        incoming_scenario['network_id'] = network_id
        parent_id = incoming_scenario.get('parent_id')

        if parent_id:
            scenario = g.conn.call('create_child_scenario', parent_id, incoming_scenario['name'])
            scenario.update(incoming_scenario)
            scenario = g.conn.call('update_scenario', scenario)
        else:
            scenario = g.conn.call('add_scenario', network_id, incoming_scenario, return_summary=True)

        return jsonify(scenario)

    @staticmethod
    def put():
        scenarios = request.json.get('scenarios')
        for scenario in scenarios:
            g.conn.call('update_scenario', scenario)

        return '', 204


@api.route('/scenarios/<int:scenario_id>')
class Scenario(Resource):

    @staticmethod
    @api.doc(description='Get a scenario.')
    def get(scenario_id):
        include_data = request.args.get('include_data') in ['1', 'True', 'true']
        scenario = g.conn.call('get_scenario', scenario_id, include_data=include_data)
        return jsonify(scenario)

    @staticmethod
    def put(scenario_id):
        return_summary = request.args.get('return_summary', 'true') == 'true'
        scenario = request.json['scenario']
        scenario = g.conn.call('update_scenario', scenario)
        return jsonify(scenario)

    @staticmethod
    def patch(scenario_id):
        updates = request.json
        scenario = g.conn.call('get_scenario', scenario_id)
        scenario.update(updates)
        scenario = g.conn.call('update_scenario', scenario)
        return jsonify(scenario)

    @staticmethod
    def delete(scenario_id):
        scenario_class = request.args.get('scenario_class', 'input')

        if scenario_class == 'result':
            study_id = g.study.id
            result = delete_data_scenario(g.conn, scenario_id, study_id)
        else:
            result = delete_data_scenario(g.conn, scenario_id)

        return '', 204


@api.route('/scenarios/<int:scenario_id>/resource_group_items')
class ResourceGroupItems(Resource):

    @staticmethod
    def post(scenario_id):
        items = request.json.get('items')
        scenario = g.conn.call('get_scenario', scenario_id)
        scenario['resourcegroupitems'] = items
        result = g.conn.call('update_scenario', scen=scenario)
        ret_items = result.resourcegroupitems[-len(items):]

        return jsonify(ret_items)

    @staticmethod
    def delete(scenario_id):
        item_ids = request.args.getlist('ids[]', type=int)
        for item_id in item_ids:
            g.conn.call('delete_resourcegroupitem', item_id=item_id)
        return '', 204
