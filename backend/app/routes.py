from flask import Blueprint, Response, stream_with_context
from flask import request
from .functions import get_air_quality, get_navigation, get_nearby, get_weather, get_place, reverse_geocode
from .models import intent_detect, json_summarize, manual_refer, STT, TTS, ai_agent
import json

bp = Blueprint('main', __name__)

@bp.route('/')
def home():
    return 'Hello, World!'

@bp.route('/agent', methods=['POST'])
def agent():
    data = request.get_json()
    # the latitude and longitude of the user's current location
    lat = data.get('latitude')
    lon = data.get('longitude')
    print("current location: ", lat, lon)
    ai_agent(lat, lon)
    return Response(stream_with_context(ai_agent(lat, lon)), content_type='text/plain')

@bp.route('/agent_test/<lat>/<lon>')
def agent_test(lat, lon):
    ai_agent(lat, lon)
    return "end"

@bp.route('/search_place', methods=['POST'])
def search_place():
    data = request.get_json()
    lat = data.get('latitude')
    lon = data.get('longitude')
    place = data.get('place')
    location = reverse_geocode(lat, lon)
    result = get_place(location, place)
    return json.dumps(result)