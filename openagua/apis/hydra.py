from flask import jsonify, g, request
from flask_restx import Namespace, Resource, fields

hydra = Namespace('Hydra Platform RPC API', path='/hydra',
                  description='A pass-through to Hydra Platform functions.'
                              ' Good for when you can\'t find what you need in the core API.')

hydra_fields = hydra.model('HydraRPC', {
    'args': fields.String,
    'kwargs': fields.String
})


@hydra.route('/<string:function_name>')
class Hydra(Resource):

    @hydra.doc(
        description='The Hydra Platform RPC consists of this single post call with any arbitrary Hydra function.',
        body=hydra_fields
    )
    def post(self, function_name):
        try:
            data = request.json or {}
            hydra_args = data.get('args', [])
            hydra_kwargs = data.get('kwargs', {})
            if not hydra_args and not hydra_kwargs:
                hydra_kwargs = data
            hydra_kwargs['uid'] = hydra_kwargs.pop('uid', g.datauser.userid)
            resp = g.conn.call(function_name, *hydra_args, **hydra_kwargs)
            return jsonify(resp)
        except AttributeError:
            return "Server error. g.conn not defined?"
        except Exception as err:
            return str(err)
