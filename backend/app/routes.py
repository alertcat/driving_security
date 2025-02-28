from flask import Blueprint
from .functions import get_air_quality, get_navigation, get_nearby
from .models import intent_detect
import json

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

@bp.route('/agent/<user_prompt>')
def agent(user_prompt):
    intent = json.loads(intent_detect(user_prompt))
    if(intent["intent"] == "adjust_facilities"):
        return intent
    elif(intent["intent"] == "navigation"):
        return get_navigation("NUS", intent["destination"])
    elif(intent["intent"] == "poi_search"):
        return get_nearby("NUS", intent["categories"])
    elif(intent["intent"] == "query"):
        if(intent["type"] == "weather"):
            return get_air_quality("NUS")
        elif(intent["type"] == "air_quality"):
            return get_air_quality("NUS")