from flask import Blueprint, url_for
from flask_restx import Api as UnpatchedApi

from .accounts import api as accounts_ns
from .maps import api as maps_ns
from .hydra import hydra as hydra_ns
from .data import api as data_ns
from .models import api as models_ns
from .gui import api as gui_ns
from .files import api as files_ns


# from .security import api as auth_ns


# from openagua.security.authentication import api_authentication_required

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
    # decorators=[api_authentication_required],
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

# api.add_namespace(auth_ns)

api0 = Blueprint('api0', __name__)
ping = Blueprint('ping', __name__)

from .core import dashboards, favorites, networks, projects, scenarios, templates
from . import data, files0, users, security
