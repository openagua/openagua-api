from flask import current_app

from openagua.constants import KEY_NAMES

def get_key_value(key):
    key_value = None

    if key in KEY_NAMES:
        key_value = current_app.config.get(KEY_NAMES[key])

    return key_value


def authorize_pubnub_user(unique_id):
    secret_key = current_app.config.get('PUBNUB_SECRET_KEY')
    return
