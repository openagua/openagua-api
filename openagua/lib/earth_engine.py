import ee
from os import path
from oauth2client.service_account import ServiceAccountCredentials


def create_ee(app):
    try:
        service_account = app.config['EE_SERVICE_ACCOUNT_ID']
        private_key = path.join(app.config['KEYS_DIR'], app.config['EE_PRIVATE_KEY'])
        ServiceAccountCredentials(service_account, private_key)

        ee.Initialize()
        app.ee = ee

    except:
        app.ee = None
