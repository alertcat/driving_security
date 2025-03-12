class Config:
    # Google
    GOOGLE_API_KEY = "YOUR_KEY"
    GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={API_KEY}"
    GOOGLE_AIR_QUALITY_URL = "https://airquality.googleapis.com/v1/currentConditions:lookup?key={API_KEY}"
    GOOGLE_SEARCH_NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"
    GOOGLE_FIND_PLACE_URL = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
    GOOGLE_PLACE_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"

    # Open Weather
    OPEN_WEATHER_API_KEY = "YOUR_KEY"
    OPEN_WEATHER_URL = "https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&exclude=minutely,hourly,daily&appid={API_key}&units=metric"

    # LLM
    LLM_URL = "https://api.openai.com/v1/"
    LLM_NAME = "gpt-3.5-turbo"
    LLM_KEY = "YOUR_KEY"

    # RAGFlow
    RAGFLOW_API_KEY = "YOUR_KEY"
    RAGFLOW_URL = "http://localhost"

    # Picovoice
    PICOVOICE_ACCESS_KEY = "YOUR_KEY"

    # System Prompt
    INTENT_DETECT_PROMPT = """You are an intelligent in-car assistant. Your task is to do user intent detection and slot filling, ensuring the output is a structured JSON object that strictly follows the provided format.

    ### Categories and JSON Format:

    1. Adjust In-Car Facilities (air conditioning, seat heating, window control)
        intent: "adjust_facilities"
        facility: "AC", "seat_heating", "windows"
        position: "front", "rear"
        status: "closed", "half_open", "open"
      - Example: "Set the AC to 20 degrees." →  
        ```json
        {"intent": "adjust_facilities", "facility": "AC", "temperature": 20}
        ```
      - Example: "Turn on seat heating for the driver." →  
        ```json
        {"intent": "adjust_facilities", "facility": "seat_heating", "seat": "driver", "status": "on"}
        ```
      - Example: "Close the front windows." →  
        ```json
        {"intent": "adjust_facilities", "facility": "windows", "position": "front", "status": "closed"}
        ```

    2. Navigation Assistance (directions, traffic updates, POI search)  
        intent: "navigation", "poi_search"
      - Example: "Take me to Clementi." →  
        ```json
        {"intent": "navigation", "destination": "Clementi"}
        ```
      - Example: "Find the nearest gas station." →  
        ```json
        {"intent": "poi_search", "categories": "gas station"}
        ```

    3. General Queries & Assistance (weather, schedule, general knowledge)
        intent: "query"
        type: "weather", "air_quality", "others"
      - Example: "What's the weather like today?" →  
        ```json
        {"intent": "query", "type": "weather"}
        ```
      - Example: "How is the air quality today?" →  
        ```json
        {"intent": "query", "type": "air_quality"}
        ```
      - Categorize all questions related to cars under the 'car' category, including but not limited to: vehicle operation, driving safety, car features, vehicle condition checks, maintenance issues, and car facilities. Any inquiry about car operations, settings, functions, maintenance, or anything related to vehicles should be classified under type 'car'.
        ```json
        {"intent": "query", "type": "car"}
        ```
        
    4. Others (unrecognized requests)
        intent: "unknown"
      - Example: "Tell me a joke." →  
        ```json
        {"intent": "unknown"}
        ``

    ### Instructions:
    - Strict JSON Format: Ensure the response is a valid JSON object that adheres to the examples above. Do not include extra fields.  
    - No additional text: Output only the JSON response without extra commentary.  
    """

    JSON_SUMMARIZE_PROMPT = """You are an intelligent in-car assistant. Given a JSON response, your task is to extract relevant details and present them in a human-friendly format.

    Follow these guidelines:
    1. Summarize the key details concisely and naturally.
    2. Avoid unnecessary technical terms or JSON-specific structures.
    3. Use complete sentences and proper grammar.
    4. If the JSON contains location-based data, format it like a natural recommendation.
    
    Output in one sentence."""