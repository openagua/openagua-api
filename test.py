import os
import requests
import json

from tests.hydra import Hydra


# main openagua class for testing
# again
class OpenAgua:
    def __init__(self, base_uri='/', api_key=None, source_id=1, project_id=None):
        self.base_uri = base_uri

        api_key = api_key or os.environ.get('OPENAGUA_API_KEY')
        self.headers = {'X-API-KEY': api_key}

        self.default_params = {'sourceId': source_id, 'projectId': project_id}

        self.hydra = Hydra(base_uri + 'hydra', api_key=api_key)

    def __setattr__(self, key, value):
        if key in ['source_id', 'project_id']:
            self.default_params[key.split('_')[0] + 'Id'] = value
        self.__dict__[key] = value

    def get(self, path, params=None):
        all_params = self.default_params.copy()
        if params:
            all_params.update(params)
        resp = requests.get(self.base_uri + path, headers=self.headers, params=params)
        return resp

    def post(self, path, params=None, data=None):
        params = {**self.default_params, **params} if params else self.default_params
        path = self.base_uri + path
        resp = requests.post(path, headers=self.headers, params=params, json=data)
        ret = json.loads(resp.content.decode())
        return ret

    def put(self, path, params=None, data=None):
        if params:
            params = self.default_params.update(params)
        resp = requests.put(self.base_uri + path, headers=self.headers, params=params, data=data)
        return resp

    def delete(self, path, params=None):
        params = {**self.default_params, **params} if params else self.default_params
        resp = requests.delete(self.base_uri + path, headers=self.headers, params=params)
        return resp

    def patch(self, path, params=None, data=None):
        if params:
            params = self.default_params.update(params)
        resp = requests.patch(self.base_uri + path, headers=self.headers, params=params, data=data)
        return resp


if __name__ == '__main__':
    api_key = os.environ.get('OPENAGUA_SECRET_KEY')
    base_uri = 'http://localhost:5000/api/v1/'
    # base_uri = 'https://www.openagua.org/api/v1/'

    oa = OpenAgua(base_uri=base_uri, api_key=api_key)
    user = oa.hydra.get_user()

    # project

    # add project
    i = 1
    resp = {}
    while True and i <= 10:
        proj_name = 'TEST PROJECT'
        proj = dict(name=proj_name, description='test project')
        resp = oa.post('projects', data=proj)
        if 'error' not in resp:
            break
        else:
            projects = oa.hydra.get_project_by_name(proj_name)
            project = [p for p in projects if p['created_by'] == user['id']][0]
            resp = oa.delete('projects/{}'.format(project['id']))
            i += 1

    try:
        assert 'project' in resp
    except:
        raise Exception('Could not add project')

    # delete a project
    project = resp['project']
    resp = oa.delete('projects/{}'.format(project['id']))

    try:
        assert resp.status_code == 204
    except:
        raise Exception('Could not delete project')

    print('done!')
