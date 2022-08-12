from flask import render_template, send_from_directory, session, request, current_app, jsonify, g
from openagua.security import login_required, current_user
from openagua import app
from openagua.constants import KEY_NAMES
import urllib.parse
import hashlib


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
