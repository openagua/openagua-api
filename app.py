from gevent import monkey

monkey.patch_all()

import os

abspath = os.path.abspath(__file__)
os.chdir(os.path.dirname(abspath))

from openagua import socketio, app

host = os.environ.get('OA_HOST', 'localhost')
port = os.environ.get('OA_PORT', 5000)
print("Running OpenAgua on {}:{}".format(host, port))
socketio.run(app, host=host, port=port)
