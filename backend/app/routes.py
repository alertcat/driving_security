from flask import Blueprint
from .functions import get_air_quality, get_navigation, get_nearby, get_weather
from .models import intent_detect, json_summarize, manual_refer, STT, TTS
import json

bp = Blueprint('main', __name__)

@bp.route('/')
def home():
    return 'Hello, World!'

@bp.route('/agent')
def agent():
    user_prompt = STT()
    print(user_prompt)
    intent = json.loads(intent_detect(user_prompt))
    print(intent)

    if(intent["intent"] == "adjust_facilities"):
        return intent
    elif(intent["intent"] == "navigation"):
        result = get_navigation("NUS", intent["destination"])
        print(result)
        response = json_summarize(json.dumps(result))
    elif(intent["intent"] == "poi_search"):
        result = get_nearby("NUS", intent["categories"])
        print(result)
        response = json_summarize(json.dumps(result))
    elif(intent["intent"] == "query"):
        if(intent["type"] == "weather"):
            result = get_weather("NUS")
            print(result)
            response = json_summarize(json.dumps(result))
        elif(intent["type"] == "air_quality"):
            result = get_air_quality("NUS")
            print(result)
            response = json_summarize(json.dumps(result))
        elif(intent["type"] == "others"):
            response = manual_refer(user_prompt)
        else:
            response = "I'm sorry, I don't understand this question?"
    else:
        response = "I'm sorry, I don't understand this request?"
    TTS(response)
    return response