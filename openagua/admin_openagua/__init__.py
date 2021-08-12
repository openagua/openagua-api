from flask import Blueprint

admin_openagua = Blueprint('admin_openagua',
                           __name__,
                           template_folder='templates')

from . import views