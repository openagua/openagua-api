import ee
# from pathlib import Path
# from google.oauth2 import service_account


def create_ee(app):
    try:
        # service_account_id = app.config['EE_SERVICE_ACCOUNT_ID']
        # keys_dir = app.config['KEYS_DIR']
        # private_key = app.config['EE_PRIVATE_KEY']
        # private_key_file = Path(keys_dir, private_key).as_posix()
        # credentials = service_account.Credentials.from_service_account_file(private_key_file)

        # ee.Initialize(credentials=credentials)
        ee.Initialize()
        app.ee = ee

    except Exception as e:
        print(f'Earth Engine initialization error: {str(e)}')
        app.ee = None
