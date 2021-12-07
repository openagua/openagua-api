from flask import request, jsonify, g
from flask_restx import Resource, Namespace
from ..security import current_user

from openagua.lib.model_editor import get_model, get_models, delete_model, update_model, add_model_template, add_model
from openagua.lib.model_control import start_model_run, cancel_model_run, add_ping, emit_progress, ProcessState, \
    end_model_run, get_run_records, delete_run_record, delete_run_records
from openagua.utils import get_network_model
from openagua.lib.integrations import authorize_pubnub_user

api = Namespace('Model engines API', path='/models', description='Operations related to model engines.')


@api.route('/engines')
class ModelEngines(Resource):
    def get(self):
        project_id = request.args.get('project_id', type=int)
        network_ids = request.args.getlist('network_ids[]', type=int)

        if 'model_ids[]' in request.args:
            model_ids = request.args.getlist('model_ids[]', type=int)
            models = get_models(user_id=current_user.id, model_ids=model_ids)
        elif project_id and 'network_ids[]' in request.args:
            dataurl_id = g.datauser.dataurl_id
            models = get_models(dataurl_id=dataurl_id, project_id=project_id, network_ids=network_ids)
        elif project_id:
            dataurl_id = g.datauser.dataurl_id
            models = get_models(dataurl_id=dataurl_id, project_id=project_id)
        elif 'network_ids[]' in request.args:
            dataurl_id = g.datauser.dataurl_id
            models = get_models(dataurl_id=dataurl_id, network_ids=network_ids)

        else:

            for scope in ['public', 'shared', 'private']:

                models = get_models(scope, project_id=project_id, user_id=current_user.id)

                for m in models:

                    if not m['templates']:
                        template = g.conn.call('get_template_by_name', m.name)
                        if template:
                            modeltemplate = add_model_template(g.conn.url, m.id, template)
                            m['templates'] = [modeltemplate.to_json()]
                        else:
                            m['templates'] = []
                    else:
                        for t in m['templates']:
                            if t.get('template_name'):
                                template = g.conn.call('get_template_by_name', t.template_name)
                                if not template:
                                    del t

        return jsonify(models=models)

    def post(self):
        template_id = request.json.get('template_id')
        model = request.json.get('model')
        model['user_id'] = current_user.id
        model['study_id'] = g.study.id if hasattr(g, "study") else None
        model = add_model(g.conn.url, model, template_id)
        ret_model = model.to_json(include_templates=True)
        return jsonify(model=ret_model)


@api.route('/engines/<int:model_id>')
class ModelEngine(Resource):
    def get(self, model_id):

        network_id = request.args.get('network_id', type=int)

        if network_id:
            network_model = get_network_model(url=g.conn.url, network_id=network_id)
            if network_model:
                model = get_model(id=network_model.model_id)
            else:
                model = None
        else:
            model = get_model(id=model_id)

        return jsonify(model=model.to_json(include_templates=True) if model else None)

    def put(self, model_id):
        model = request.json.get('model')
        template_id = request.json.get('template_id')
        model.pop('templates', None)
        updated_model = update_model(**model)
        ret_model = updated_model.to_json(include_templates=True)
        ret_model['project_id'] = model.get('project_id')
        return jsonify(model=ret_model)

    def delete(self, model_id):
        resp = delete_model(model_id)
        return '', 204


@api.route('/run_configurations')
class RunConfigurations(Resource):
    def post(self):
        network_id = request.json.get('network_id')
        new_config = request.json.get('config')
        new_config.pop('id', None)
        network = g.conn.call('get_network', network_id, include_resources=False, include_data=False, summary=True)
        configs = network['layout'].get('run_configurations', [])

        config = dict(
            id=max([config.id for config in configs]) + 1 if configs else 1,
            **new_config
        )
        configs.append(config)
        network['layout']['run_configurations'] = configs
        g.conn.call('update_network', network)

        return jsonify(config=config)


@api.route('/run_configurations/<int:config_id>')
class RunConfiguration(Resource):
    def put(self, config_id=None):
        network_id = request.json.get('network_id')
        config = request.json.get('config')
        network = g.conn.call('get_network', network_id, include_resources=False, include_data=False, summary=True)
        current_configurations = network['layout'].get('run_configurations', [])
        new_configurations = [config if c['id'] == config['id'] else c for c in current_configurations]
        network['layout']['run_configurations'] = new_configurations
        g.conn.call('update_network', network)

        return jsonify(config=config)

    def delete(self, config_id):
        network_id = request.args.get('network_id', type=int)
        network = g.conn.call('get_network', network_id, include_resources=False, include_data=False, summary=True)
        network['layout']['run_configurations'] = [c for c in network['layout'].get('run_configurations', []) if
                                                   c.id != config_id]
        g.conn.call('update_network', network)

        return '', 204


@api.route('/runs')
class ModelRuns(Resource):

    def post(self):
        """Run a model based on project/network settings and user input."""

        network_id = request.json.get('network_id')
        guid = request.json.get('guid')
        computer_id = request.json.get('computer_id')
        config = request.json.get('config', {})
        ret = start_model_run(g.conn, network_id, guid, config, computer_id=computer_id)

        return jsonify(ret)


@api.route('/runs/<sid>')
class ModelRun(Resource):

    def delete(self, sid):
        source_id = request.args.get('sourceId', type=int)
        network_id = request.args.get('network_id', type=int)
        cancel_model_run(sid=sid)

        data = dict(
            sid=sid,
            name=request.args.get('name'),
            source_id=source_id,
            network_id=network_id,
            scids=request.args.getlist('scids[]', type=int),
            progress=request.args.get('progress', type=int)
        )
        end_model_run(sid, ProcessState.CANCELED, data)

        return '', 204


@api.route('/runs/<sid>/actions/<action>')
class ModelRun(Resource):
    def post(self, sid, action):
        data = request.json
        source_id = data.get('source_id', 1)
        network_id = data.get('network_id')

        if action == 'start':
            data.pop('status', None)
            data.pop('sid', None)
            ping = add_ping(sid, ProcessState.STARTED, **data)
            # emit_progress(source_id=source_id, network_id=network_id, ping=ping.to_json())

        elif action == 'save':
            # emit_progress(source_id=source_id, network_id=network_id, ping=data)
            pass

        elif action == 'error':
            end_model_run(sid, ProcessState.ERROR, data)

        elif action == 'done':
            end_model_run(sid, ProcessState.FINISHED, data)

        elif action == 'stop':
            end_model_run(sid, ProcessState.CANCELED, data)

        elif action == 'pause':
            pass  # TODO: update

        elif action == 'resume':
            pass  # TODO: update

        elif action == 'clear':
            pass  # TODO: is this needed?

        return '', 204


@api.route('/runs/records')
class ModelRunRecords(Resource):
    def get(self):
        network_id = request.args.get('network_id')
        source_id = g.datauser.dataurl_id
        records = get_run_records(source_id=source_id, network_id=network_id)

        return jsonify(records=records)

    def delete(self):
        network_id = request.args.get('network_id')
        record_id = request.args.get('record_id')

        if record_id:
            delete_run_record(record_id)
        else:
            source_id = g.datauser.dataurl_id
            delete_run_records(source_id=source_id, network_id=network_id)

        return '', 204


@api.route('/runs/records/<int:record_id>')
class ModelRunRecord(Resource):

    def delete(self, record_id):
        delete_run_record(record_id)

        return '', 204
