import requests

def get_real_environmental_data(city):
    """
    Fetches real-world environmental data using the Open-Meteo open-source APIs.
    Raises ValueError if the city is not found.
    """
    # 1. Geocoding API to get Latitude & Longitude
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=5&language=en&format=json"
    
    try:
        geo_response = requests.get(geo_url, timeout=5)
        geo_response.raise_for_status()
        geo_data = geo_response.json()
        
        if not geo_data.get("results"):
            raise ValueError(f"City '{city}' not found.")
            
        # Select the best matching result
        # Preference: If any of the top results match the user input (name or admin area),
        # we take the first one that matches to respect the API's relevance ranking.
        results = geo_data["results"]
        location = results[0] # Fallback
        
        city_lower = city.lower()
        for res in results:
            res_name = res.get("name", "").lower()
            res_admin2 = res.get("admin2", "").lower()
            res_admin3 = res.get("admin3", "").lower()
            
            if city_lower in [res_name, res_admin2, res_admin3]:
                location = res
                break # Take the FIRST result that matches any of these
        
        lat = location["latitude"]
        lon = location["longitude"]
        
        # Build a more descriptive name
        # If the user's input matches an administrative name (like "Indore" in "Indhur" result), 
        # let's prioritize showing what the user typed if it's a valid part of the result.
        name = location.get("name", city.title())
        
        # Logic for "Indore/Indhur" fix: 
        # If user typed "Indore" and it matched admin2/admin3 of the result, use "Indore" as name
        if city_lower in [location.get("admin2", "").lower(), location.get("admin3", "").lower()] and city_lower != name.lower():
            name = city.title()

        admin1 = location.get("admin1", "")
        country = location.get("country", "")
        
        parts = [name]
        if admin1 and admin1 != name:
            parts.append(admin1)
        if country and country not in parts:
            parts.append(country)
            
        resolved_city_name = ", ".join(parts)
        
        # 2. Weather API (Current, Hourly for 24h, Daily for 7 days)
        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code"
            f"&hourly=temperature_2m,precipitation"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
            f"&timezone=auto"
        )
        weather_response = requests.get(weather_url, timeout=5)
        weather_response.raise_for_status()
        weather_json = weather_response.json()
        
        current_weather = weather_json["current"]
        hourly_data = weather_json.get("hourly", {})
        daily_data = weather_json.get("daily", {})
        
        timestamp = current_weather.get("time")
        
        # 3. Air Quality API (AQI)
        aqi_url = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}&current=us_aqi"
        aqi_response = requests.get(aqi_url, timeout=5)
        aqi_response.raise_for_status()
        aqi_data = aqi_response.json()["current"]
        
        # Map to our expected format
        data = {
            "resolved_city": resolved_city_name,
            "timestamp": timestamp,
            "Temperature": current_weather.get("temperature_2m", 0),
            "Humidity": current_weather.get("relative_humidity_2m", 0),
            "Wind_Speed": current_weather.get("wind_speed_10m", 0),
            "Rainfall": current_weather.get("precipitation", 0),
            "AQI": aqi_data.get("us_aqi", 0),
            "weather_code": current_weather.get("weather_code", 0),
            "trends": {
                "hourly": {
                    "time": hourly_data.get("time", [])[:24], # Next 24 hours
                    "temp": hourly_data.get("temperature_2m", [])[:24],
                    "rain": hourly_data.get("precipitation", [])[:24]
                },
                "daily": {
                    "time": daily_data.get("time", []),
                    "temp_max": daily_data.get("temperature_2m_max", []),
                    "temp_min": daily_data.get("temperature_2m_min", []),
                    "rain_sum": daily_data.get("precipitation_sum", [])
                }
            }
        }
        
        return data

    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"Error connecting to weather service: {str(e)}")
