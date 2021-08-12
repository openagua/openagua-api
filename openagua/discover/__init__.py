from flask import Blueprint

discover = Blueprint('discover',
                       __name__,
                       template_folder='templates',
                       static_folder='static',
                       static_url_path='/discover/static')

from . import views
