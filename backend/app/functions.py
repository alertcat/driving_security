import requests
import json
from flask import current_app
import googlemaps
from datetime import datetime

def get_coordinates(address):
    url = current_app.config['GOOGLE_GEOCODE_URL'].format(address=address, API_KEY=current_app.config['GOOGLE_API_KEY'])
    response = requests.get(url).json()
    if response['status'] == 'OK':
        location = response['results'][0]['geometry']['location']
        return {"latitude": location['lat'], "longitude": location['lng']}
    return None

def get_air_quality(address):
    url = current_app.config['GOOGLE_AIR_QUALITY_URL'].format(API_KEY=current_app.config['GOOGLE_API_KEY'])
    location = get_coordinates(address)
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, headers=headers, data=json.dumps({"location": location}))
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Request failed: {response.status_code}, error message: {response.text}")

def get_navigation(origin, destination):
    gmaps = googlemaps.Client(key=current_app.config['GOOGLE_API_KEY'])
    now = datetime.now()
    directions = gmaps.directions(origin, destination, mode="driving", departure_time=now)
    leg = directions[0]['legs'][0]

    response = {
        'start_address': leg['start_address'],
        'end_address': leg['end_address'],
        'distance': leg['distance']['text'],
        'duration': leg['duration']['text']
    }
    return response

def get_nearby(address, keyword):
    url = current_app.config['GOOGLE_SEARCH_NEARBY_URL']
    location = get_coordinates(address)
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": current_app.config['GOOGLE_API_KEY'],
        "X-Goog-FieldMask": "places.displayName"
    }
    params = {
        "includedTypes": keyword,
        "maxResultCount": 10,
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": location['latitude'],
                    "longitude": location['longitude']
                },
                "radius": 500.0
            }
        }
    }
    response = requests.post(url, json=params, headers=headers)
    return response.json()

def get_weather(address):
    location = get_coordinates(address)
    url = current_app.config['OPEN_WEATHER_URL'].format(lat=location['latitude'], lon=location['longitude'], API_key=current_app.config['OPEN_WEATHER_API_KEY'])
    weather_data = requests.get(url)
    weather_data = weather_data.json()["current"]
    response = {
        "temperature": weather_data["temp"],
        "feels_like": weather_data["feels_like"],
        "humidity": weather_data["humidity"],
        "weather": weather_data["weather"][0]["description"]
    }
    return response