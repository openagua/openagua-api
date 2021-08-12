import os
import datetime as dt
from dotenv import load_dotenv


class Config(object):
    load_dotenv()

    VERSION = dt.datetime.now().strftime('%y.%m.%d')

    APP_NAME = os.environ.get('OA_APP_NAME', 'TEST')
    APP_ROOT = os.path.dirname(os.path.abspath(__file__))
    INSTANCE_DIR = os.path.join(APP_ROOT, 'instance')
    DATA_DIR = os.path.join(APP_ROOT, 'data')

    ORGANIZATION = None
    SITE_ENCRYPTED = False

    DEBUG = False
    SECRET_KEY = os.environ.get('OPENAGUA_SECRET_KEY', 'a deep, dark secret')
    WTF_CSRF_SECRET_KEY = SECRET_KEY

    # Key needed for server (multi-user) installs for encrypting/decrypting secret db values.
    # For key generation, use `from cryptography.fernet import Fernet`, `key = Fernet.generate_key()`
    SECRET_ENCRYPT_KEY = os.environ.get('SECRET_ENCRYPT_KEY', 'another key')
    DEFAULT_DATABASE_URI = 'sqlite:///{}/openagua.sqlite'.format(DATA_DIR)
    SQLALCHEMY_DATABASE_URI = os.environ.get('OA_DATABASE_URI', DEFAULT_DATABASE_URI)

    KEYS_DIR = INSTANCE_DIR
    UPLOADED_FILES_DEST = INSTANCE_DIR

    # Data Server
    DATA_URL = 'base'
    DATA_ROOT_USERNAME = 'root'
    DATA_ROOT_PASSWORD = ''

    # Other Data Server-related settings
    DATA_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f000Z'  # must be the same as in data.ini
    DATA_SEASONAL_YEAR = 1678  # not used yet
    DEFAULT_SCENARIO_NAME = 'Baseline'
    DEFAULT_SCENARIO_DESCRIPTION = 'Default management option and scenario'

    POST_URL = 'http://127.0.0.1:5000'
    WEBSOCKET_URL = 'ws://127.0.0.1:9000'
    # WAMP_URL = 'ws://xxx.xxx.xxx.xxx:8080/ws'

    MESSAGE_PROTOCOL = 'pubnub'
    # MESSAGE_PROTOCOL = 'socketio'
    PUBNUB_SECRET_KEY = os.environ.get('PUBNUB_SECRET_KEY')
    PUBNUB_SUBSCRIBE_KEY = os.environ.get('PUBNUB_SUBSCRIBE_KEY')
    PUBNUB_PUBLISH_KEY = os.environ.get('PUBNUB_PUBLISH_KEY')

    AWS_MODEL_KEY_NAME = os.environ.get('AWS_MODEL_KEY_NAME')  # .pem key file used by OpenAgua for EC2 modeling

    HYDROLOGY_API_URL = "http://localhost:8000"
    ADD_REFERENCE_LAYER_URL = "/network/reference_layer"
    OPENAGUA_API_KEY = 'abc'

    # Flask-Security

    SECURITY_CONFIRMABLE = False
    SECURITY_LOGIN_WITHOUT_CONFIRMATION = True

    # Flask-Security settings
    # SECURITY_FLASH_MESSAGES = True
    SECURITY_PASSWORD_HASH = 'sha256_crypt'
    SECURITY_PASSWORD_SALT = 'salty'

    # SECURITY_POST_REGISTER_VIEW = 'base.entrance'
    # SECURITY_POST_LOGIN_VIEW = 'base.entrance'
    # # SECURITY_POST_LOGOUT_VIEW = 'base.exit'
    # SECURITY_POST_CONFIRM_VIEW = 'base.entrance'

    SECURITY_SEND_REGISTER_EMAIL = False
    SECURITY_REGISTERABLE = True
    SECURITY_RECOVERABLE = True
    SECURITY_TRACKABLE = False
    SECURITY_PASSWORDLESS = False  # experimental, but seems to work
    SECURITY_CHANGEABLE = True

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Use Amazon Web Services for EC2?
    USE_AWS = False
    CLOUD_COMPUTER_TYPES = []
    AUTOTERMINATE_HOURS = 1

    # Include hydrology - change to True once OpenAgua API is set up
    INCLUDE_HYDROLOGY = False

    # Model running
    # URL passed to the model so it can "phone home" with it's status
    HEARTBEAT_ENT = '/model'
    # socket.io
    NETWORK_ROOM_NAME = '{source_id}-{network_id}'
    RUN_STUDY_ROOM_NAME = '{source_id}-{project_id}'

    # Necessary if install type is server and AWS EC2 machines are used
    AWS_ACCOUNT_ID = '123456789123'
    AWS_MODEL_EC2_USERNAME = 'ec2-user'  # this assumes an Amazon Linux machine
    AWS_DEFAULT_REGION = ''  # e.g., 'us-west-2'
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_MODEL_SECURITY_GROUP = ''  # Security group to SSH to EC2s

    # For map access...
    USE_GOOGLE = True
    PREFERRED_MAP_PROVIDER = 'mapbox'
    GOOGLE_PLACES_API_KEY = os.environ.get('GOOGLE_PLACES_API_KEY')  # https://console.developers.google.com
    MAPBOX_ACCESS_TOKEN = ''  # Mapbox access token

    AWS_S3_BUCKET = ''  # define in instance configuration
    NETWORK_FILES_STORAGE_LOCATION = 's3'

    # For Google Earth Engine access
    # If either of these are set to True, must also set up machine-specific GEE credentials
    INCLUDE_GEOPROCESSING = False  # For advanced geoprocessing (not available yet)

    # Google Earth Engine
    EE_SERVICE_ACCOUNT_ID = os.environ.get('EE_SERVICE_ACCOUNT_ID')  # 'my-service-account@...gserviceaccount.com'
    EE_PRIVATE_KEY = os.environ.get('EE_PRIVATE_KEY')  # 'xxxxxxxxxxxxx.json'

    # Charts
    DEFAULT_CHART_RENDERER = 'plotly'


class ServerConfig(Config):
    USE_AWS = False
    INCLUDE_HYDROLOGY = True

    DATA_ROOT_USERNAME = os.environ.get('DATA_ROOT_USERNAME')
    DATA_ROOT_PASSWORD = os.environ.get('DATA_ROOT_PASSWORD')

    RECAPTCHA_SITE_KEY = os.environ.get('RECAPTCHA_SITE_KEY')
    RECAPTCHA_SECRET_KEY = os.environ.get('RECAPTCHA_SECRET_KEY')

    SECURITY_CONFIRMABLE = True
    SECURITY_LOGIN_WITHOUT_CONFIRMATION = False

    SECURITY_PASSWORD_HASH = os.environ.get('SECURITY_PASSWORD_HASH')
    SECURITY_PASSWORD_SALT = os.environ.get('SECURITY_PASSWORD_SALT')
    SECURITY_EMAIL_SENDER = (
        os.environ.get('OA_APP_NAME', 'OpenAgua'),
        os.environ.get('SECURITY_EMAIL_SENDER')
    )
    SECURITY_SEND_REGISTER_EMAIL = True
    SECURITY_REGISTERABLE = True
    SECURITY_RECOVERABLE = True
    SECURITY_TRACKABLE = False
    SECURITY_PASSWORDLESS = False
    SECURITY_CHANGEABLE = True

    MAIL_API_ENDPOINT = os.environ.get('MAIL_API_ENDPOINT')
    MAIL_API_KEY = os.environ.get('MAIL_API_KEY')

    # API Keys, etc.
    OPENAGUA_API_KEY = os.environ.get('OPENAGUA_API_KEY')
    MAPBOX_USERNAME = os.environ.get('MAPBOX_USERNAME')
    MAPBOX_DISCOVERY_TILESET_NAME = os.environ.get('MAPBOX_DISCOVERY_TILESET_NAME')
    MAPBOX_ACCESS_TOKEN = os.environ.get('MAPBOX_ACCESS_TOKEN')
    MAPBOX_CREATION_TOKEN = os.environ.get('MAPBOX_CREATION_TOKEN')
    MAPBOX_DATASET_NAME = os.environ.get('MAPBOX_DATASET_NAME')
    MAPBOX_UPDATE_ENDPOINT = os.environ.get('MAPBOX_UPDATE_ENDPOINT')
    MAPBOX_DATASET_ID = os.environ.get('MAPBOX_DATASET_ID')
    MAPBOX_DISCOVER_MAP = os.environ.get('MAPBOX_DISCOVER_MAP')

    AWS_S3_BUCKET = os.environ.get('AWS_S3_BUCKET')
    AWS_S3_BUCKET_IMAGES = os.environ.get('AWS_S3_BUCKET_IMAGES')
    AWS_ACCOUNT_ID = os.environ.get('AWS_ACCOUNT_ID')
    AWS_SSH_SECURITY_GROUP = os.environ.get('AWS_SSH_SECURITY_GROUP')
    AWS_DEFAULT_REGION = os.environ.get('AWS_DEFAULT_REGION')
    AMI_ID = os.environ.get('AMI_ID')

    BOX_CLIENT_ID = os.environ.get('BOX_CLIENT_ID')
    BOX_CLIENT_SECRET = os.environ.get('BOX_CLIENT_SECRET')
    BOX_REDIRECT_URI = os.environ.get('BOX_REDIRECT_URI')

    RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST')
    RABBITMQ_DEFAULT_USERNAME = os.environ.get('RABBITMQ_DEFAULT_USERNAME')
    RABBITMQ_DEFAULT_PASSWORD = os.environ.get('RABBITMQ_DEFAULT_PASSWORD')
    RABBITMQ_VHOST = os.environ.get('RABBITMQ_VHOST')

    # Flask-Babel options
    LANGUAGES = {
        'en': 'English',
        'es': 'Español',
        'zh_Hans': '中文（简体）',
        'zh_Hant': '中文（繁體）',
        'fr': 'Français',
        'de': 'Deutsch',
        'ru': 'русский',
        'it': 'Italiano',
        'hi': 'हिंदी',
        'ar': 'العربية',
        'pt': 'Português',
        'fa': 'فارسی',
        'ja': '日本語',
        'am': 'አማርኛ',
    }


class WebsiteConfig(ServerConfig):
    SITE_ENCRYPTED = True

    MAIL_API_ENDPOINT = os.environ.get('MAIL_API_ENDPOINT')
    MAIL_API_KEY = os.environ.get('MAIL_API_KEY')

    USE_AWS = True
    CLOUD_COMPUTER_TYPES = ['ec2']
    NETWORK_FILES_STORAGE_LOCATION = 's3'


class DevelopmentConfig(WebsiteConfig):
    # SECURITY_CONFIRMABLE = False
    # SECURITY_LOGIN_WITHOUT_CONFIRMATION = True

    HYDROLOGY_API_URL = "http://localhost:8000"
    ADD_REFERENCE_LAYER_URL = "/network/reference_layer"

    CLOUD_COMPUTER_TYPES = ['ec2']

    NETWORK_FILES_STORAGE_LOCATION = 's3'

configs = {
    'desktop': Config,
    'server': ServerConfig,
    'website': WebsiteConfig,
    'development': DevelopmentConfig
}
