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

def reverse_geocode(lat, lng):
    api_key = "AIzaSyDj--w-mh3zKme37CGd-BbAH__NaceuhVM"
    params = {
        "latlng": f"{lat},{lng}",
        "key": api_key
    }
    response = requests.get("https://maps.googleapis.com/maps/api/geocode/json", params=params)
    data = response.json()
    if data['status'] == 'OK':
        address = data['results'][0]['formatted_address']
        return address
    else:
        return None

def get_air_quality(lat, lon):
    url = current_app.config['GOOGLE_AIR_QUALITY_URL'].format(API_KEY=current_app.config['GOOGLE_API_KEY'])
    location = {"latitude": lat, "longitude": lon}
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, headers=headers, data=json.dumps({"location": location}))
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Request failed: {response.status_code}, error message: {response.text}")

def get_navigation(lat, lon, destination):
    gmaps = googlemaps.Client(key=current_app.config['GOOGLE_API_KEY'])
    now = datetime.now()
    origin = reverse_geocode(lat, lon)
    print("origin:", origin)
    directions = gmaps.directions(origin, destination, mode="driving", departure_time=now)
    leg = directions[0]['legs'][0]

    response = {
        'start_address': leg['start_address'],
        'end_address': leg['end_address'],
        'distance': leg['distance']['text'],
        'duration': leg['duration']['text']
    }
    return response

def get_nearby(lat, lon, keyword):
    url = current_app.config['GOOGLE_SEARCH_NEARBY_URL']
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
                    "latitude": lat,
                    "longitude": lon
                },
                "radius": 500.0
            }
        }
    }
    response = requests.post(url, json=params, headers=headers)
    return response.json()

def get_weather(lat, lon):
    url = current_app.config['OPEN_WEATHER_URL'].format(lat=lat, lon=lon, API_key=current_app.config['OPEN_WEATHER_API_KEY'])
    weather_data = requests.get(url)
    weather_data = weather_data.json()["current"]
    response = {
        "temperature": weather_data["temp"],
        "feels_like": weather_data["feels_like"],
        "humidity": weather_data["humidity"],
        "weather": weather_data["weather"][0]["description"]
    }
    return response

def get_place_id(restaurant_name, location=""):
    """ 根据餐厅名称获取 place_id """
    params = {
        "input": restaurant_name if not location else f"{restaurant_name}, {location}",
        "inputtype": "textquery",
        "fields": "place_id",
        "key": current_app.config['GOOGLE_API_KEY']
    }
    response = requests.get(current_app.config['GOOGLE_FIND_PLACE_URL'], params=params)
    data = response.json()
    
    if "candidates" in data and data["candidates"]:
        return data["candidates"][0]["place_id"]
    return None

def get_restaurant_reviews(place_id):
    """ 根据 place_id 获取餐厅评价 """
    params = {
        "place_id": place_id,
        "fields": "name,rating,reviews",
        "key": current_app.config['GOOGLE_API_KEY']
    }
    response = requests.get(current_app.config['GOOGLE_PLACE_DETAILS_URL'], params=params)
    data = response.json()

    if "result" in data:
        restaurant = data["result"]
        reviews = restaurant.get("reviews", [])
        return {
            "name": restaurant.get("name"),
            "rating": restaurant.get("rating"),
            "reviews": [{"author": reviews[0]["author_name"], "rating": reviews[0]["rating"], "text": reviews[0]["text"]}]
        } if reviews else {"name": restaurant.get("name"), "rating": restaurant.get("rating")}
    return None

def get_restaurant_info(restaurant_name, location=""):
    """ 获取餐厅信息（评分和评论） """
    place_id = get_place_id(restaurant_name, location)
    if not place_id:
        return f"未找到餐厅: {restaurant_name}"
    
    return get_restaurant_reviews(place_id)

def get_place(location, place):
    # restaurant_name = "Din Tai Fung"  # 鼎泰丰
    # location = "Los Angeles"  # 可选
    info = get_restaurant_info(place, location)
    return info