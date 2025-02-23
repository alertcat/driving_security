from flask import Blueprint
from .functions import get_air_quality, get_navigation, get_nearby
from .models import adjust_aircon

bp = Blueprint('main', __name__)

@bp.route('/')
def home():
    return 'Hello, World!'

@bp.route('/airquality/<address>')
def airquality(address):
    response = get_air_quality(address)
    return response

@bp.route('/navigation/<origin>/<destination>')
def navigation(origin, destination):
    response = get_navigation(origin, destination)
    return response

@bp.route('/nearby/<address>/<keyword>')
def nearby(address, keyword):
    response = get_nearby(address, keyword)
    return response


@bp.route('/facilities/<user_prompt>')
def facilities(user_prompt):
    response = adjust_aircon(user_prompt)
    return response