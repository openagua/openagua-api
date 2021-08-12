from flask import current_app
from flask_socketio import join_room


def init_socketio():

    from openagua import socketio

    @socketio.on('join-network')
    def _join_network(data):
        source_id = data.get('source_id')
        project_id = data.get('project_id')
        network_id = data.get('network_id')
        # study = get_study(project_id=project_id, dataurl_id=source_id)
        room = current_app.config['NETWORK_ROOM_NAME'].format(source_id=source_id, network_id=network_id)
        join_room(room)
