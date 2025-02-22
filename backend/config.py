class Config:
    

    GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={API_KEY}"
    GOOGLE_AIR_QUALITY_URL = "https://airquality.googleapis.com/v1/currentConditions:lookup?key={API_KEY}"
    GOOGLE_SEARCH_NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"

    OLLAMA_URL = "http://localhost:11434/v1/"