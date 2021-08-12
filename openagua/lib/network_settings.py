from openagua import db
from ..models import NetworkModel

def get_models(dataurl_id, network_id):

    network_models = NetworkModel.query.filter_by(dataurl_id=dataurl_id, network_id=network_id).all()
    models = [nm.model.to_json() for nm in network_models]

    return models
