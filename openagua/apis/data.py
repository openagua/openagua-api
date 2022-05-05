from flask import request, jsonify, g, current_app, json
from flask_restx import Namespace, Resource
from munch import Munch as AttrDict

from openagua.security import current_user
from openagua.lib.data import get_scenarios_data, make_eval_data, filter_input_data, prepare_dataset, \
    filter_results_data
from openagua.lib.favorites import get_favorite
from openagua.lib.pivot import save_pivot_input

api = Namespace('Data API', path='/data',
                description='Data API for the OpenAgua app. This varies significantly from Hydra, '
                            'so Hydra is probably better for simple operations.')


@api.route('/resource_scenario_data')
class ResourceScenarioData(Resource):

    @api.doc(
        description='Get data from a resource scenario.',
        params={
            'network_id': 'The network ID',
            'res_type': 'The resource type (node, link or network)',
            'res_id': 'The resource ID',
            'attr_id': 'The attribute ID',
            'type_id': 'The template type ID',
            'data_type': 'The data type. This is needed to populate with default data.',
            'nblocks': 'The number of blocks (or columns) in the data, such as for piecewise linear data.',
            'language': 'The default language input for text-based rules (default=python)。',
            'flavor': 'Language flavor. This can help with interpreting input for preview.',
            'settings': 'Time settings (start, end and step)',
            'network_folder': 'Network folder. This is from the network layout.'
        }
    )
    def get(self):
        network_id = request.args.get('network_id', type=int)
        res_type = request.args.get('res_type', type=str).lower()
        res_id = request.args.get('resource_id', type=int)
        attr_id = request.args.get('attr_id', type=int)
        lineage = request.args.getlist('lineage[]', type=int)
        type_id = request.args.get('type_id', type=int)
        data_type = request.args.get('data_type', type=str)
        nblocks = request.args.get('nblocks', 0, type=int)
        settings = request.args.get('settings', '{}', type=str)
        language = request.args.get('language', 'python', type=str)
        flavor = request.args.get('flavor', 'openagua')

        time_settings = json.loads(settings)
        files_path = request.args.get('network_folder')

        attr = g.conn.call('get_attribute_by_id', attr_id)

        kwargs = dict(
            conn=g.conn,
            scenario_ids=lineage,
            network_id=network_id,
            resource_type=res_type,
            resource_id=res_id,
            type_id=type_id,
            attr_id=attr_id,
            data_type=data_type,
            time_settings=time_settings,
            files_path=files_path,
            nblocks=nblocks,
            flavor='json',
            for_eval=True,
            function_language=(language, flavor)
        )
        attr_data = get_scenarios_data(**kwargs)

        return jsonify(attr_data=attr_data, attr=attr)

    @api.doc('Add data to a resource scenario.')
    def post(self):
        data = request.json
        action = data['action']
        resource_type = data['resource_type']
        resource_id = data['resource_id']
        data_type = data.get('data_type', 'timeseries')
        scenario_data = data['scenario_data']
        attr_id = data['attr_id']
        attr_is_var = data.get('attr_is_var')
        res_attr_id = data.get('res_attr_id')
        unit_id = data.pop('unit_id', None)
        variation = data.pop('variation', None)
        time_settings = data.pop('settings', None)
        language = data.pop('language', None)
        flavor = data.pop('flavor', None)

        network_folder = data.get('network_folder')
        files_path = network_folder

        scenario_id = scenario_data.get('id')

        # PREPARE DATA
        attr = g.conn.call('get_attribute_by_id', attr_id)
        user_id = g.datauser.id
        user_email = current_user.email
        dataset = prepare_dataset(scenario_data, unit_id, attr, data_type, user_id, user_email)
        res_attr = None

        # SAVE DATA
        if action == 'save':
            # TODO: In the future the dataset should be created in the client machine, and this can be just a pass-through,
            # so no need for an extra save_data function

            # add resource attribute if it doesn't exist
            if not res_attr_id:
                # def add_resource_attribute(resource_type, resource_id, attr_id, is_var, error_on_duplicate=True, **kwargs):
                res_attr = g.conn.call(
                    'add_resource_attribute',
                    resource_type.upper(),
                    resource_id,
                    attr_id,
                    False,
                )
                res_attr_id = res_attr['id']

            if variation:
                scenario = g.conn.call('get_scenario', scenario_id)
                variations = scenario.layout.get('variations', [])
                if variation.get('id'):
                    variations = [variation if v.get('id') == variation['id'] else v for v in variations]
                else:
                    variation['id'] = variations[-1].get('id', 0) + 1 if variations else 1
                    variations.append(variation)
                scenario['layout']['variations'] = variations
                g.conn.call('update_scenario', scenario)

            # result = g.conn.call('add_data_to_attribute', scenario_id, res_attr_id, dataset)
            resource_scenarios = [dict(
                resource_attr_id=res_attr_id,
                dataset=dataset
            )]
            result = g.conn.call('update_resourcedata', scenario_id, resource_scenarios)

            if 'error' in result:
                status = -1
                errmsg = json.dumps(result)

                result = {
                    # 'id': scenario_id,
                    'status': status,
                    'errcode': -1,
                    'errmsg': errmsg,
                    'eval_value': None
                }

                return jsonify(result=result)

            else:
                status = 1

        else:
            status = 0  # no save attempt - just report error

        # CHECK DATA

        scen_id = scenario_data['id']
        errcode = 0
        errmsg = ''
        try:
            eval_value = make_eval_data(
                scenario_id=scen_id,
                conn=g.conn,
                data_type=data_type,
                files_path=files_path,
                time_settings=time_settings,
                dataset=dataset,
                function_language=(language, flavor)
            )
        except Exception as err:
            if hasattr(err, 'code'):
                errcode = err.code
                errmsg = err.message
            else:
                errcode = -1
                errmsg = str(err)
            eval_value = None

        result = {
            'id': scen_id,
            'status': status,
            'errcode': errcode,
            'errmsg': errmsg,
            'eval_value': eval_value
        }

        return jsonify(result=result, res_attr=res_attr, variation=variation)


@api.route('/pivot_input')
class PivotInputData(Resource):

    def get(self):

        template_id = request.args.get('template_id', type=int)
        network_id = request.args.get('network_id', type=int)

        favorite_id = request.args.get('favorite_id', type=int)
        if favorite_id:
            favorite = get_favorite(favorite_id=favorite_id)
            if favorite:
                filters = AttrDict(json.loads(favorite.filters))
                setup = json.loads(favorite.setup)
            else:
                return jsonify(error=1)  # no favorite found
        else:
            filters = json.loads(request.args.get('filters'))
            setup = {'aggregatorName': 'Unique Values'}  # renderer is defined in Utilities.js

            input_method = filters.get('input_method')

            data_type = filters.get('data_type', 'timeseries')

            if input_method == 'native':
                if data_type == 'timeseries':  # TODO: add more types
                    setup['cols'] = ['Scenario', 'Feature type', 'Feature', 'Variable']
                    setup['rows'] = ['Date']  # TODO: customize according to the model timestep
                if data_type in ['scalar', 'descriptor']:  # TODO: add more types
                    setup['cols'] = ['Scenario', 'Variable']
                    setup['rows'] = ['Feature type', 'Feature']  # TODO: customize according to the model timestep
            else:
                setup['cols'] = ['Scenario', 'Variable']
                setup['rows'] = ['Feature type', 'Feature']

        # filter and organize the data
        result = filter_input_data(
            conn=g.conn,
            network_id=network_id,
            template_id=template_id,
            filters=filters,
            maxrows=100000,
        )

        if not favorite_id:
            if 'Block' in result:
                blocks = result.Block.unique()
                if not (len(blocks) == 1 and blocks[0] == 'None'):
                    setup['cols'].append('Block')
            setup['vals'] = ['value']

        setup['hiddenFromAggregators'] = [c for c in result.columns if c != 'value']

        data = result.to_dict(orient='records')

        return jsonify(data=data, setup=setup)

    def put(self):
        error = 0
        network_id = request.json.get('network_id')
        setup = request.json.get('setup')
        filters = request.json.get('filters')
        data = request.json.get('data')

        network = g.conn.call('get_network', network_id, include_resources=True, include_data=False,
                              summary=False)
        template = g.conn.call('get_template', network.layout.get('active_template_id'))

        error = save_pivot_input(setup, filters, data, network, template, current_app.config['DATA_DATETIME_FORMAT'])

        return jsonify(error=error)


@api.route('/pivot_results')
class PivotResultsData(Resource):

    def get(self):

        favorite_id = request.args.get('favorite_id', type=int)
        network_id = request.args.get('network_id', type=int)
        template_id = request.args.get('template_id', type=int)
        project_id = request.args.get('project_id', type=int) or request.args.get('projectId', type=int)
        filters_str = request.args.get('filters', '{}')
        filters = AttrDict(json.loads(filters_str))

        agg = filters.get('agg', {})

        if not favorite_id:
            filters['attr_data_type'] = 'timeseries'  # TODO: get from user filters
        data_type = filters.get('attr_data_type', 'timeseries')

        # filter and organize the data
        data, perturbations = filter_results_data(
            conn=g.conn, filters=filters, network_id=network_id, template_id=template_id,
            project_id=project_id, maxrows=500000, include_tags=False)

        if type(data) == int:
            return jsonify(error=data)
        elif data is None:
            return jsonify(error=-3)

        if favorite_id:
            favorite = get_favorite(favorite_id=favorite_id)
            if favorite:
                setup = json.loads(favorite.setup)
            else:
                return jsonify(error=1)  # no favorite found
        else:
            default_chart_renderer = current_app.config['DEFAULT_CHART_RENDERER']
            setup = {
                'renderer': default_chart_renderer,
                'rendererName': 'Line Chart',
                'aggregatorName': 'Average',
                'rows': [],
                'cols': [],
                'type': 'results'
            }

            time_step = agg.get('time', {}).get('step')
            if len(filters.get('scenarios', [])) > 1 or time_step == 'year':
                if len(set(data.scenario_id)) > 1:
                    setup['rows'].append('Scenario')

            if data_type == 'timeseries':  # TODO: add more types
                setup['renderer'] = default_chart_renderer,
                if not agg.get('space'):
                    setup['rows'].append('Feature')
                if not filters.get('unstack'):
                    setup['rows'].append('Variable')
                if 'block' in data and len(set(data.block)) > 1:
                    setup['rows'].append('Block')

                if time_step == 'year':
                    setup['cols'] = ['Year']
                else:
                    setup['cols'] = ['Date']

            if perturbations:
                setup['rows'].extend(perturbations)

        columns = list(data.columns)
        data = data.to_json(orient='values', date_format='iso')

        return jsonify(columns=columns, values=data, setup=setup, error=None)
