from gevent import monkey

monkey.patch_all()

import os

from openagua import socketio, app

if __name__ == '__main__':
    abspath = os.path.abspath(__file__)
    os.chdir(os.path.dirname(abspath))

    host = os.environ.get('OA_HOST', 'localhost')
    port = os.environ.get('OA_PORT', 5000)
    print("Running OpenAgua on {}:{}".format(host, port))

    socketio.run(app, host=host, port=5000)
