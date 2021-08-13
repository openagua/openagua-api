from flask import render_template, send_from_directory, session, request, current_app, jsonify, g
from openagua.security import login_required, current_user
from openagua import app
from openagua.request_functions import _load_active_study, _make_connection, _load_datauser
import urllib.parse
import hashlib

from functools import wraps

KEY_NAMES = {
    'google': 'GOOGLE_PLACES_API_KEY',
    'mapbox': 'MAPBOX_ACCESS_TOKEN',
    'pubnub': 'PUBNUB_SUBSCRIBE_KEY'
}


# def load_the_basics(f):
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         _load_active_study()
#         _load_datauser()
#         _make_connection()
#         return f(*args, **kwargs)
#
#     return decorated_function


def set_active_network_panel(panel_name):
    network_id = session.get('network_id', None)
    study_id = session.get('study_id')
    if study_id and network_id:
        nid = '{}-{}'.format(study_id, network_id)
        session['active_panel'] = session.get('active_panel', {})
        session['active_panel'][nid] = panel_name


@app.route('/node_modules/<path:filename>')
def node_modules(filename):
    return send_from_directory('../node_modules', filename)


@app.route('/cookies')
def show_cookies():
    return render_template('cookies.html')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/utils/key')
@login_required
def _get_key():
    name = request.args.get('name')
    if name not in KEY_NAMES.values():
        return '', 405
    value = current_app.config.get(name)
    return jsonify(value=value)


@app.route('/utils/keys')
@login_required
def _get_keys():
    names = request.args.getlist('names[]')
    keys = {}
    for name in names:
        key_name = KEY_NAMES.get(name)
        if not key_name:
            continue
        keys[name] = current_app.config.get(key_name)
    return jsonify(keys=keys)


@app.route('/utils/gravatar')
@login_required
def _get_gravatar():
    # Set your variables here
    email = current_user.email
    default = "identicon"
    size = 30

    # construct the url
    gravatar_url = "//www.gravatar.com/avatar/" + hashlib.md5(email.lower().encode()).hexdigest() + "?"
    gravatar_url += urllib.parse.urlencode({'d': default, 's': str(size)})

    return jsonify(url=gravatar_url)
