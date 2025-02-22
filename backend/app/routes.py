from flask import Blueprint
from .functions import get_air_quality

bp = Blueprint('main', __name__)

@bp.route('/')
def home():
    return 'Hello, World!'

@bp.route('/airquality/<address>')
def airquality(address):
    response = get_air_quality(address)
    return response

@bp.route('/navigation')
def navigation():
    return 'Navigation'

@bp.route('/nearby')
def nearby():
    return 'Nearby'

@bp.route('/facilities')
def facilities():
    return 'Facilities'