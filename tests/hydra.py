import requests
import json


class Hydra(object):
    """
    Example:

    # Set up the class
    hydra = Hydra('https://www.openagua.org/hydra', api_key=os.environ['OPENAGUA_SECRET_KEY'])

    # Method 1: hydra.call(function, **kwargs)
    resp1 = hydra.call('get_project', project_id=123)

    # Method 2: hydra.func_name(**kwargs)
    resp2 = hydra.get_project(project_id=123)

    """

    username = None
    password = None

    def __init__(self, endpoint_url, username=None, password=None, api_key=None):
        if endpoint_url[-1] != '/':
            endpoint_url += '/'
        self.endpoint = endpoint_url

        self.auth = None
        self.headers = {}
        if api_key:
            self.headers['X-API-KEY'] = api_key
            # self.auth = ('', api_key)
        elif username and password:
            self.auth = (username, password)

    def call(self, func, dict_kwargs=None, **kwargs):
        if dict_kwargs is not None:
            return self._call(func, **dict_kwargs)
        else:
            return self._call(func, **kwargs)

    def _call(self, func, *args, **kwargs):
        payload = {}
        if args:
            payload['args'] = list(args)
            payload['kwargs'] = kwargs
        else:
            payload = kwargs
        endpoint = self.endpoint + func
        resp = requests.post(endpoint, auth=self.auth, headers=self.headers, json=payload)
        if not resp.ok:
            raise Exception('{}: {}'.format(resp.status_code, resp.content.decode()))
        try:
            return json.loads(resp.content.decode())
        except:
            return resp.content.decode()

    def __getattr__(self, name):
        def method(*args, **kwargs):
            if name == 'call':
                return self._call(*args, **kwargs)
            else:
                return self._call(name, *args, **kwargs)

        return method


def test_hydra(endpoint, api_key):
    hydra = Hydra(endpoint, api_key=api_key)

    # Add project
    project_name = 'test project'
    proj = {'name': project_name, 'description': 'this is a test project'}

    tries = 0
    project = {}
    while tries <= 1:
        project = hydra.add_project(proj)
        if 'error' in project:
            project = hydra.get_project_by_name(project_name)[0]
            hydra.delete_project(project['id'])
        else:
            break
        tries += 1

    assert 'id' in project

    # Add network
    net = {
        'name': 'test network',
        'description': 'this is a test network',
        'project_id': project['id']
    }

    network = hydra.add_network(net)
    assert 'id' in network

    # Add parent (baseline) scenario
    network_id = network['id']
    scen1 = {
        'name': 'test scenario 1',
        'start_time': '1980-10-01',
        'end_time': '1990-09-30',
        'time_step': 'daily',
    }
    scenario1 = hydra.add_scenario(network_id, scen1)
    try:
        assert 'id' in scenario1
    except AssertionError:
        raise Exception('Scenario 1 not created')

    # Add child scenario with parent_id
    scen2 = scen1.copy()
    scen2['name'] = 'test scenario 2'
    scen2['parent_id'] = scenario1['id']
    scenario2 = hydra.add_scenario(network_id, scen2)
    try:
        assert scenario2['parent_id'] is not None
    except AssertionError:
        raise Exception('Parent ID of scenario 2 is missing')

    # Add a third scenario to update with parent_id
    scen3 = scen1.copy()
    scen3['name'] = 'test scenario 3'
    scenario3 = hydra.add_scenario(network_id, scen3)
    scenario3['parent_id'] = scenario1['id']
    updated_scenario3 = hydra.update_scenario(scenario3)
    try:
        assert updated_scenario3['parent_id'] is not None
    except AssertionError:
        raise Exception('Parent ID of scenario 3 not successfully added')

    # Delete project
    project_id = project['id']
    resp = hydra.delete_project(project_id)
    assert resp == 'OK'

    print('done!')


if __name__ == '__main__':
    import os

    # Set up the hydra class
    # endpoint = 'https://www.openagua.org/hydra'
    endpoint = 'http://localhost:5000/api/v1/hydra'
    api_key = os.environ['OPENAGUA_SECRET_KEY']

    test_hydra(endpoint, api_key)
