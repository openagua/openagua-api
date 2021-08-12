from flask import current_app

import pubnub

KEY_NAMES = {
    'google': 'GOOGLE_PLACES_API_KEY',
    'mapbox': 'MAPBOX_ACCESS_TOKEN',
    'pubnub': 'PUBNUB_SUBSCRIBE_KEY'
}


def get_key_value(key):
    key_value = None

    if key in KEY_NAMES:
        key_value = current_app.config.get(KEY_NAMES[key])

    return key_value


def authorize_pubnub_user(unique_id):
    secret_key = current_app.config.get('PUBNUB_SECRET_KEY')
    return
