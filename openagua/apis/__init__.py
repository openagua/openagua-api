from flask import Blueprint, url_for, request, g
from flask_restx import Api as UnpatchedApi

from .accounts import api as accounts_ns
from .maps import api as maps_ns
from .hydra import hydra as hydra_ns
from .data import api as data_ns
from .models import api as models_ns
from .gui import api as gui_ns
from .files import api as files_ns

from openagua.security import login_required
from openagua.security.authentication import api_authentication_required
from openagua.lib.studies import load_active_study as _load_active_study
from openagua.request_functions import _load_datauser, _make_connection


# from .security import api as auth_ns

class Api(UnpatchedApi):
    @property
    def specs_url(self):
        return url_for(self.endpoint('specs'))


# Note basic auth is disabled, since passing around usernames and passwords is a security risk (can be stolen)
# However, it could be enabled by uncommenting BasicAuth here
authorizations = {
    # 'BasicAuth': {
    #     'type': 'basic',
    # },
    'ApiKeyAuth': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'X-API-KEY'
    }
}
api_blueprint = Blueprint('api', __name__)
api = Api(
    api_blueprint,
    authorizations=authorizations,
    decorators=[api_authentication_required],
    version='0.1',
    title='OpenAgua API',
    description='A mostly RESTful API for OpenAgua.',
    contact_email='david.rheinheimer@tec.mx',
    default='Core API',
    default_label='The main API of interest to most people. Built on the Hydra Platform API.',
)
api.add_namespace(hydra_ns)
api.add_namespace(data_ns)
api.add_namespace(accounts_ns)
api.add_namespace(maps_ns)
api.add_namespace(models_ns)
api.add_namespace(gui_ns)
api.add_namespace(files_ns)

api0 = Blueprint('api0', __name__)
ping = Blueprint('ping', __name__)


@login_required
@api0.before_request
def before_api0_requests():
    if request.method == 'OPTIONS':  # pre-flight request
        return

    g.dataurl_id = request.args.get('sourceId', type=int) \
                   or request.json and request.json.get('sourceId') or request.form.get('sourceId')
    g.project_id = request.args.get('projectId', type=int) or request.json and request.json.get('projectId')
    g.network_id = request.args.get('networkId', type=int) or request.json and request.json.get('networkId')
    g.template_id = request.args.get('templateId', type=int) or request.json and request.json.get('templateId')

    _load_active_study(dataurl_id=g.dataurl_id, project_id=g.project_id)
    _load_datauser()

    is_public_user = request.args.get('user') == 'public' or request.args.get('public') == 'true'
    _make_connection(is_public_user)

    return


@api_blueprint.before_request
@api_authentication_required
def before_api_requests():
    if request.method == 'OPTIONS':  # pre-flight request
        return
    args = request.args
    body = request.get_json() or {}
    form = request.form
    g.dataurl_id = args.get('sourceId', type=int) or body.get('sourceId') or form.get('sourceId') or 1
    g.project_id = args.get('projectId', type=int) or body.get('projectId')
    g.network_id = args.get('networkId', type=int) or body.get('networkId')
    g.template_id = args.get('templateId', type=int) or body.get('templateId')

    _load_active_study(dataurl_id=g.dataurl_id, project_id=g.project_id)
    _load_datauser()

    g.is_public_user = args.get('user') == "public" or args.get('scope') == 'public' or args.get('public') == 'true'
    _make_connection(g.is_public_user)

    return


from .core import dashboards, favorites, networks, projects, scenarios, templates
from . import data, files0, users, security
