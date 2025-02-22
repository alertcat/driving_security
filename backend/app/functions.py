import requests
import json
from flask import current_app

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
        print(f"请求失败，状态码: {response.status_code}, 错误信息: {response.text}")