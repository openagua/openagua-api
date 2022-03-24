from flask import request, jsonify, g, current_app

from openagua.security import current_user
from openagua.lib.studies import get_study, delete_study, add_star, remove_star, get_stars
from openagua.lib.files import delete_all_network_files
from openagua.lib.users import get_dataurl_by_id
from openagua.lib.sharing import set_resource_permissions, share_resource
from openagua.lib.projects import prepare_project_for_client, prepare_projects_for_client, copy_project

from openagua import app
from openagua.apis import api
from flask_restx import Resource


@api.route('/projects')
class Projects(Resource):

    @api.doc(params={'public': 'If true, all public projects will be returned.'})
    def get(self):

        source_id = g.source_id

        if g.is_public_user:
            user_id = g.conn.user_id

        else:
            user_id = g.datauser.userid

        is_public = request.args.get('is_public') == 'true'
        page = request.args.get('page', type=int)
        max_per_page = request.args.get('max_per_page', 10, type=int)
        include_networks = request.args.get('include_networks') == 'true'
        search = request.args.get('search')

        projects_count = g.conn.call('get_public_projects_count', search=search) if page == 1 else None
        projects = g.conn.call('get_projects', user_id, user_id=user_id, summary=True, page=page,
                               public_only=is_public, search=search,
                               max_per_page=max_per_page, include_networks=include_networks)

        if projects is None:
            return '', 511
        if 'error' in projects:
            return jsonify(projects=[])

        projects = prepare_projects_for_client(g.conn, projects, source_id, user_id, include_models=True)

        return jsonify(projects=projects, count=projects_count)

    @api.doc(description='Add a project.')
    def post(self):
        project = request.json.get('project')
        purpose = request.args.get('purpose')
        if purpose == 'copy':
            proj = copy_project(project)
        else:
            proj = g.conn.call('add_project', project)


        if 'error' in proj:
            return jsonify(proj)
        else:
            project = proj

        source_id = g.datauser.dataurl_id
        source_url = g.conn.url
        source_user_id = g.datauser.userid
        project = prepare_project_for_client(g.conn, project=project, source_id=source_id,
                                             source_user_id=source_user_id, data_url=source_url, include_models=True)

        # and add a first project note while we're here, to hold the long description
        note = {'ref_key': 'PROJECT', 'ref_id': project.id, 'value': b''}
        g.conn.call('add_note', note)

        return jsonify(project=project)


@api.route('/projects/<int:project_id>')
@api.doc(params={'id': 'The project ID'})
class Project(Resource):

    @api.doc(description='Get a project.')
    def get(self, project_id):

        include_networks = request.args.get('include_networks') == 'true'

        project = g.conn.call('get_project', project_id, include_networks=include_networks)
        if project is None:
            return '', 511
        if 'error' in project:
            return project['error'], 501

        source_id = g.datauser.dataurl_id
        source_url = g.conn.url
        source_user_id = g.datauser.userid
        project = prepare_project_for_client(g.conn, project, source_id, source_user_id, data_url=source_url,
                                             include_models=True)

        return jsonify(project=project)

    @api.doc('Update a project.')
    def put(self, project_id):
        project = request.json
        g.conn.call('update_project', project)
        return '', 204

    @api.doc('Patch a project.')
    def patch(self, project_id):
        data = request.json
        project = g.conn.call('get_project', project_id)
        project.update(data)
        g.conn.call('update_project', project)
        return '', 204

    @api.doc('Delete a project.')
    def delete(self, project_id):
        dataurl = get_dataurl_by_id(id=g.source_id)
        project = g.conn.call('get_project', project_id)

        if not project or not hasattr(project, 'networks'):
            return '', 410

        bucket_name = current_app.config['AWS_S3_BUCKET']
        for network in project.networks:
            delete_all_network_files(network, bucket_name, s3=app.s3)

        templates = g.conn.call('get_templates', project_id=project_id)
        for template in templates:
            g.conn.call('delete_template', template_id=template['id'])
        resp = g.conn.call('delete_project', project_id, purge_data=True)
        if resp == 'OK':
            study = get_study(url=dataurl.url, project_id=project_id)
            delete_study(study_id=study.id)

        return '', 204


@api.route('/projects/<int:project_id>/notes')
class ProjectNotes(Resource):
    @api.doc(description='Get notes from a project.')
    @api.response(200, 'Success')
    def get(self, project_id):
        notes = g.conn.call('get_notes', 'PROJECT', project_id)
        for note in notes:
            try:
                note.pop('project', None)
            except:
                print(notes)
            try:
                if isinstance(note['value'], bytes):
                    note['value'] = note['value'].decode()
            except:
                print('Something went wrong processing note: ')
                print(note)
        return jsonify(notes=notes)

    @api.doc(description='Add a note to a project.')
    @api.response(200, 'Success')
    def post(self, project_id):
        note = request.json
        note['value'] = note['value'].encode()
        note['ref_key'] = 'PROJECT'
        note['ref_id'] = project_id
        note = g.conn.call('add_note', note)
        note['value'] = note.get('value').decode()
        return jsonify(note=note)


@api.route('/projects/<int:project_id>/notes/<int:note_id>')
class ProjectNote(Resource):
    @api.doc(description='Update a project note.')
    @api.response(200, 'Success')
    def put(self, project_id, note_id):
        note = request.json
        note['value'] = note.get('value', '').encode()
        note['ref_key'] = 'PROJECT'
        note['ref_id'] = project_id
        note = g.conn.call('update_note', note)
        note['value'] = note.get('value', b'').decode()
        return jsonify(note=note)


@api.route('/projects/<int:project_id>/permissions')
class ProjectPermissions(Resource):

    @api.doc(description='Share a network (add users with permissions)')
    def post(self, project_id):
        data = request.get_json()
        emails = data['emails']
        permissions = data['permissions']
        message = data.get('message', '')
        results = share_resource(g.conn, 'project', project_id, emails, permissions, message=message)
        return jsonify(results)

    @api.doc(description="Update project permissions.")
    @api.response(204, 'Success')
    def put(self, project_id):
        permissions = request.json['permissions']

        for username, _permissions in permissions.items():
            results = set_resource_permissions(g.conn, 'project', project_id, username, _permissions)

        return '', 204


# TODO: add source_id to path instead of arguments?
@api.route('/projects/<int:project_id>/star')
@api.doc(params={
    'project_id': 'The project ID',
    'source_id': 'The source ID (default = 1)'
}, responses={
    204: 'Success'
})
class ProjectsStar(Resource):

    @api.doc(description='Star a project.')
    def post(self, project_id):
        source_id = request.json.get('source_id', 1)
        user_id = current_user.id
        add_star(user_id, source_id, project_id)
        return 'Project starred', 204

    @api.doc(description='Unstar a project.')
    def delete(self, project_id):
        source_id = request.args.get('source_id', type=int)
        user_id = current_user.id
        remove_star(user_id, source_id, project_id)
        return 'Project unstarred', 204


@api.route('/projects/stars')
class ProjectsStars(Resource):

    @api.doc(description='Get all stars from all user projects (there shouldn\'t be too many).')
    @api.response(200, 'Success')
    def get(self):
        stars = get_stars(user_id=current_user.id)
        return jsonify(stars=stars)

# @api.route('/hydroshare/import')
# @login_required
# def _import_from_hydroshare():
#     res_id = request.args.get('res_id')
#     res_type = request.args.get('res_type')
#     res_username = request.args.get('res_username')
#
#     download_from_hydroshare(res_id, res_type, res_username)
#
#     return '', 204
