import os
from pathlib import Path

from flask import Flask, g, session, flash, make_response, jsonify, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_babelex import Babel
from flask_socketio import SocketIO
from flask_cors import CORS

import logging

from config import configs
from openagua.mail import Mail
from openagua.security import Security, SQLAlchemyUserDatastore, logout_user
from openagua.lib.messaging import RabbitMQ
from openagua.lib.earth_engine import create_ee
from openagua.realtime import init_socketio

from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub

# create the app
app = Flask(__name__, instance_relative_config=True)

allowed_origin = os.environ.get('OA_AUTH_ORIGIN')
app.config['OA_AUTH_ORIGIN'] = allowed_origin

cors_resources = {
    r"/api/*": {"origins": "*"},
    r"/utils/*": {"origins": allowed_origin},
    r"/model/*": {"origins": allowed_origin},
    r"/network/*": {"origins": allowed_origin},
    r"/auth0/*": {"origins": allowed_origin},
}
cors_headers = ['Content-Type', 'Authorization', 'X-API-KEY']
max_age = 86400
CORS(app, resources=cors_resources, supports_credentials=True, allow_headers=cors_headers, max_age=max_age)

log_level = logging.INFO

logging.basicConfig(level=log_level)
# app = Flask(__name__)

# CONFIGURATION

# set the install type
install_type = os.environ.get('OPENAGUA_INSTALL_TYPE', 'server')
app.config['INSTALL_TYPE'] = install_type
app.config.from_object(configs[install_type])

app.config['SECRET_ENCRYPT_KEY'] = app.config['SECRET_ENCRYPT_KEY'].encode()

# set up instance configuration
instance_cfg = 'config.cfg'
if os.path.exists(Path(app.instance_path, instance_cfg)):
    app.config.from_pyfile(instance_cfg)

app.config.SWAGGER_SUPPORTED_SUBMIT_METHODS = ['get']

# INITIALIZE EXTENSIONS

engine_options = dict(
    pool_size=50,
    max_overflow=25,
    pool_recycle=300,
)

db = SQLAlchemy(app, engine_options=engine_options)
mail = Mail(app)
babel = Babel(app)

# authentication
# from .security import authentication

if install_type == 'development':
    socketio = SocketIO(app, cors_allowed_origins=allowed_origin)
else:
    socketio_url = 'pyamqp://{username}:{password}@{hostname}/flask-socketio'.format(
        username=app.config['RABBITMQ_DEFAULT_USERNAME'],
        password=app.config['RABBITMQ_DEFAULT_PASSWORD'],
        hostname=app.config.get('RABBITMQ_HOST', 'localhost'),
        # vhost=app.config.get('RABBITMQ_VHOST'),
    )
    # print(' [*] Connected to {}'.format(socketio_url.replace(app.config['RABBITMQ_DEFAULT_PASSWORD'], '********')))
    socketio = SocketIO(app, async_mode='gevent', message_queue=socketio_url, cors_allowed_origins=allowed_origin)

logging.getLogger('openagua').setLevel(logging.ERROR)
logging.getLogger('socketio').setLevel(logging.ERROR)
logging.getLogger('engineio').setLevel(logging.ERROR)

# this starts the socketio listener functions
init_socketio()

# Setup Flask-Security
from openagua import models

user_datastore = SQLAlchemyUserDatastore(db, models.User, models.Role)
security = Security(app, user_datastore)

# import blueprints
from openagua.apis import hydra
from openagua.apis import api0, api_blueprint, ping
from openagua.apis.security import auth0
from openagua.admin_openagua import admin_openagua

# from openagua.discover import discover

# register blueprints
app.register_blueprint(api0, url_prefix='')
app.register_blueprint(api_blueprint, url_prefix='/api/v1')
app.register_blueprint(ping, url_prefix='')
app.register_blueprint(admin_openagua, url_prefix='')
# app.register_blueprint(discover, url_prefix='')
app.register_blueprint(auth0)

if app.config['INCLUDE_HYDROLOGY']:
    from openagua.hydrology import hydrology

    app.register_blueprint(hydrology, url_prefix='/hydrology')

create_ee(app)


# app.before_first_request - moved to discover
# if 'MAPBOX_CREATION_TOKEN' in app.config:
#     os.environ['MAPBOX_ACCESS_TOKEN'] = app.config['MAPBOX_CREATION_TOKEN']

@app.after_request
def check_data_session(response):
    if hasattr(g, 'invalid_data_session') or response.status_code == 511:
        logout_user()
        session['_flashes'] = []
        flash("Oops! Your data session appears to be invalid. Please login again.", "danger")
        return make_response(jsonify(url=url_for('security.logout')), 511)

    return response


os.environ['AWS_ACCESS_KEY_ID'] = app.config['AWS_ACCESS_KEY_ID']
os.environ['AWS_SECRET_ACCESS_KEY'] = app.config['AWS_SECRET_ACCESS_KEY']
os.environ['AWS_S3_BUCKET'] = app.config.get('AWS_S3_BUCKET')

from openagua.lib.files import s3_resource

app.s3 = s3_resource()

# PubNub for canceling tasks (can we replace this with Celery?)
pnconfig = PNConfiguration()
pnconfig.subscribe_key = app.config.get('PUBNUB_SUBSCRIBE_KEY')
pnconfig.publish_key = app.config.get('PUBNUB_PUBLISH_KEY')
pnconfig.uuid = app.config.get('PUBNUB_UUID')
pnconfig.ssl = False
app.pubnub = PubNub(pnconfig)

# RabbitMQ for adding model users management
api_url = 'http://{hostname}:15672/api'.format(
    hostname=app.config.get('RABBITMQ_HOST', 'localhost'),
)
app.rabbitmq = RabbitMQ(
    api_url=api_url,
    username=app.config.get('RABBITMQ_DEFAULT_USERNAME'),
    password=app.config.get('RABBITMQ_DEFAULT_PASSWORD')
)

from openagua import views
