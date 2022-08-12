from flask import request, jsonify, g
from flask_restx import Resource, fields
from openagua.lib.dashboards import get_dashboard, get_dashboards, add_dashboard, update_dashboard, delete_dashboard

# import blueprint definition
from openagua.apis import api

dashboards_fields = api.model('Dashboards', {
    'network_id': fields.Integer(description="The network ID"),
})

dashboard_fields = api.model('Dashboard', {
    'network_id': fields.Integer(description="The network ID"),
    'dashboard': fields.String(description="JSON formatted dashboard")
})


@api.route('/dashboards')
class Dashboards(Resource):
    """Get dashboards or post a new dashboard"""

    @api.doc(description='Get dashboards associated with a network')
    @api.param('network_id', 'Network ID')
    def get(self):
        network_id = request.args.get('network_id', type=int)
        project_id = request.args.get('project_id', type=int) or g.get('projectId')
        if network_id:
            dashboards = get_dashboards(network_id=network_id)
        elif network_id:
            dashboards = get_dashboards(project_id=project_id)
        else:
            dashboards = []
        return jsonify(dashboards)

    @api.doc(description='Add a dashboard associated with a network', body=dashboard_fields)
    def post(self):
        network_id = request.json.get('network_id')
        dashboard = request.json.get('dashboard')
        dashboard = add_dashboard(study_id=g.study.id, network_id=network_id, dashboard=dashboard)
        return jsonify(dashboard.to_json())


@api.route('/dashboards/<int:dashboard_id>')
class Dashboard(Resource):

    @api.doc(description='Get a dashboard')
    def get(self, dashboard_id):
        dashboard = get_dashboard(dashboard_id)
        return jsonify(dashboard)

    @api.doc(description='Update a dashboard')
    def put(self, dashboard_id):
        dashboard = request.json.get('dashboard')
        dashboard = update_dashboard(**dashboard)
        return jsonify(dashboard.to_json())

    @api.doc(description='Delete a dashboard')
    @api.response(204, 'Success')
    def delete(self, dashboard_id):
        delete_dashboard(dashboard_id=dashboard_id)
        return 'Dashboard deleted', 204
