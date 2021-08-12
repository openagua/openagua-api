import os
import uuid

from flask import jsonify, request
from flask_restx import Resource, Namespace

from openagua.lib.network_editor import *
from openagua.lib.files import get_file_list, add_folder, \
    generate_presigned_post, generate_presigned_url, generate_presigned_urls

api = Namespace('Files API', path='/files',
                description='Files API for the OpenAgua app.')


@api.route('/network_files', doc=False)
class NetworkFiles(Resource):
    def get(self):
        network_key = request.args.get('network_key', '')
        prefix = request.args.get('prefix', '')
        bucket_name = current_app.config['AWS_S3_BUCKET']
        if len(network_key) < 12 or network_key != prefix[:len(network_key)]:
            folders = files = []
        else:
            folders, files = get_file_list(bucket_name, prefix, s3=current_app.s3)

        return jsonify(folders=folders, files=files)


@api.route('/network_folder', doc=False)
class NetworkFolder(Resource):
    def post(self):
        network_key = request.json.get('network_key', '')
        prefix = request.json.get('prefix', '')
        bucket_name = current_app.config['AWS_S3_BUCKET']
        if len(network_key) < 12 or network_key != prefix[:len(network_key)]:
            return 'Network key must be provided', 400
        else:
            key = add_folder(bucket_name, prefix, s3=current_app.s3)
            return jsonify(folder=key)


@api.route('/presigned_post', doc=False)
class PresignedPost(Resource):
    def post(self):
        dest = request.json.get('dest')
        file_name = request.json.get('file_name')
        file_type = request.json.get('file_type')
        if dest == 'images':
            ext = os.path.splitext(file_name)[-1]
            file_name = uuid.uuid4().hex + ext
            bucket_name = current_app.config.get('AWS_S3_BUCKET_IMAGES')
        else:
            bucket_name = current_app.config.get('AWS_S3_BUCKET')
        region = current_app.config.get('AWS_DEFAULT_REGION')

        presigned_post = generate_presigned_post(region, bucket_name, file_name, file_type, dest=dest)
        public_url = presigned_post['url'] + file_name
        return jsonify(public_url=public_url, **presigned_post)


@api.route('/presigned_urls', doc=False)
class PresignedUrls(Resource):
    def get(self):
        bucket_name = current_app.config.get('AWS_S3_BUCKET')
        key = request.args.get('key', '')  # key is the root folder for the network/project
        paths = request.args.getlist('paths[]')
        urls = request.args.getlist('urls[]')
        keys = ['{}/{}'.format(key, path) for path in paths] + urls
        client_method = request.args.get('client_method', 'get_object')

        urls = generate_presigned_urls(bucket_name, keys, client_method=client_method)

        return jsonify(urls=urls)


@api.route('/presigned_url', doc=False)
class PresignedUrl(Resource):
    def get(self, key):
        bucket_name = current_app.config.get('AWS_S3_BUCKET')
        client_method = request.json.get('client_method', 'get_object')
        key = request.args.get('key')
        urls = generate_presigned_url(bucket_name, key, client_method=client_method)

        return jsonify(urls=urls)
