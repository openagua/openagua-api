from flask import jsonify, request, current_app

from openagua.security import login_required
from openagua.lib.files import duplicate_objects, rename_object, delete_objects

from openagua.apis import api0


@api0.route('/network/object/name')
def _rename_object():
    network_key = request.json.get('network_key')
    old_key = request.json.get('old_key', '')
    new_key = request.json.get('new_key', '')
    bucket_name = current_app.config['AWS_S3_BUCKET']
    if len(network_key) < 12 or network_key != new_key[:len(network_key)]:
        return 'Network key must be provided', 400
    s3 = current_app.s3
    updated = rename_object(bucket_name, old_key, new_key, s3)
    return jsonify(object=updated)


@api0.route('/network/move_objects', methods=['POST'])
@login_required
def _move_objects():
    network_key = request.json.get('network_key')
    bucket_name = current_app.config['AWS_S3_BUCKET']
    s3 = current_app.s3
    objects = request.json.get('objects', [])
    for object in objects:
        old_key = object.get('old_key', '')
        new_key = object.get('new_key', '')
        if len(network_key) < 12 or network_key != new_key[:len(network_key)]:
            return 'Network key must be provided', 400
        rename_object(bucket_name, old_key, new_key, s3)
    return '', 204


@api0.route('/network/duplicate_objects', methods=['POST'])
@login_required
def _duplicate_objects():
    network_key = request.json.get('network_key')
    bucket_name = current_app.config['AWS_S3_BUCKET']
    s3 = current_app.s3
    objects = request.json.get('objects', [])
    try:
        new_files, new_folders = duplicate_objects(bucket_name, objects, network_key, s3)
        return jsonify(files=new_files, folders=new_folders)
    except Exception as err:
        return str(err), 400


@api0.route('/network/objects', methods=['DELETE'])
@login_required
def _delete_objects():
    files = request.args.getlist('files[]')
    folders = request.args.getlist('folders[]')
    bucket_name = current_app.config['AWS_S3_BUCKET']
    delete_objects(bucket_name, files, folders)
    return '', 200
