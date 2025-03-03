from flask import Blueprint
from .functions import get_air_quality, get_navigation, get_nearby, get_weather
from .models import intent_detect, json_summarize, manual_refer
import json

bp = Blueprint('main', __name__)

@bp.route('/')
def home():
    return 'Hello, World!'

@bp.route('/agent/<user_prompt>')
def agent(user_prompt):
    intent = json.loads(intent_detect(user_prompt))
    print(intent)

    if(intent["intent"] == "adjust_facilities"):
        return intent
    
    elif(intent["intent"] == "navigation"):
        result = get_navigation("NUS", intent["destination"])
        return json_summarize(json.dumps(result))
    
    elif(intent["intent"] == "poi_search"):
        result = get_nearby("NUS", intent["categories"])
        return json_summarize(json.dumps(result))
    
    elif(intent["intent"] == "query"):
        if(intent["type"] == "weather"):
            result = get_weather("NUS")
            return json_summarize(json.dumps(result))
        elif(intent["type"] == "air_quality"):
            result = get_air_quality("NUS")
            return json_summarize(json.dumps(result))
        elif(intent["type"] == "vehicle"):
            result = manual_refer(user_prompt)
            return result
    else:
        return "I'm sorry, I don't understand. Could you please provide more information?"