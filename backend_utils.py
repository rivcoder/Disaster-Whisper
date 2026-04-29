import requests

def get_real_environmental_data(city):
    """
    Fetches real-world environmental data using the Open-Meteo open-source APIs.
    Raises ValueError if the city is not found.
    """
    # 1. Geocoding API to get Latitude & Longitude
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json"
    
    try:
        geo_response = requests.get(geo_url, timeout=5)
        geo_response.raise_for_status()
        geo_data = geo_response.json()
        
        if not geo_data.get("results"):
            raise ValueError(f"City '{city}' not found.")
            
        location = geo_data["results"][0]
        lat = location["latitude"]
        lon = location["longitude"]
        
        # Build a more descriptive name (e.g., "Indhur, Madhya Pradesh, India")
        name = location.get("name", city.title())
        admin1 = location.get("admin1", "")
        country = location.get("country", "")
        
        parts = [name]
        if admin1 and admin1 != name:
            parts.append(admin1)
        if country and country not in parts:
            parts.append(country)
            
        resolved_city_name = ", ".join(parts)
        
        # 2. Weather API (Temperature, Humidity, Wind Speed, Rainfall)
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"
        weather_response = requests.get(weather_url, timeout=5)
        weather_response.raise_for_status()
        weather_data = weather_response.json()["current"]
        
        # 3. Air Quality API (AQI)
        aqi_url = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}&current=us_aqi"
        aqi_response = requests.get(aqi_url, timeout=5)
        aqi_response.raise_for_status()
        aqi_data = aqi_response.json()["current"]
        
        # Map to our expected format
        data = {
            "resolved_city": resolved_city_name,
            "Temperature": weather_data.get("temperature_2m", 0),
            "Humidity": weather_data.get("relative_humidity_2m", 0),
            "Wind_Speed": weather_data.get("wind_speed_10m", 0),
            "Rainfall": weather_data.get("precipitation", 0),
            "AQI": aqi_data.get("us_aqi", 0)
        }
        
        return data

    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"Error connecting to weather service: {str(e)}")
