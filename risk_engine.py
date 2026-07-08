import pandas as pd
import os

def calculate_risk_breakdown(env_data):
    """
    Calculates the severity (0-100%) for individual environmental threat vectors.
    Based on weather current values and daily/hourly trends.
    """
    temp = env_data.get('Temperature', 0)
    humidity = env_data.get('Humidity', 0)
    wind = env_data.get('Wind_Speed', 0)
    rain = env_data.get('Rainfall', 0)
    aqi = env_data.get('AQI', 0)
    
    # Extract trends if present
    hourly_temps = env_data.get('trends', {}).get('hourly', {}).get('temp', [])
    hourly_rains = env_data.get('trends', {}).get('hourly', {}).get('rain', [])
    
    max_forecast_temp = max(hourly_temps) if hourly_temps else temp
    min_forecast_temp = min(hourly_temps) if hourly_temps else temp
    max_forecast_rain = max(hourly_rains) if hourly_rains else rain
    
    daily_temp_maxs = env_data.get('trends', {}).get('daily', {}).get('temp_max', [])
    daily_temp_mins = env_data.get('trends', {}).get('daily', {}).get('temp_min', [])
    daily_rain_sums = env_data.get('trends', {}).get('daily', {}).get('rain_sum', [])
    
    max_daily_temp = max(daily_temp_maxs) if daily_temp_maxs else max_forecast_temp
    min_daily_temp = min(daily_temp_mins) if daily_temp_mins else min_forecast_temp
    
    worst_temp = max_daily_temp if abs(max_daily_temp - 20) > abs(min_daily_temp - 20) else min_daily_temp
    worst_rain = max(max_forecast_rain, max(daily_rain_sums) / 10.0 if daily_rain_sums else 0)
    
    # 1. Temperature Risk (Extreme hot >30C or cold <10C)
    if worst_temp > 30:
        temp_risk = ((worst_temp - 30) / (42 - 30)) * 100
    elif worst_temp < 10:
        temp_risk = ((10 - worst_temp) / (10 - -5)) * 100
    else:
        temp_risk = 0
    temp_risk = max(0, min(100, temp_risk))
    
    # 2. Wind Storm Risk (>20 km/h)
    wind_risk = ((wind - 20) / (80 - 20)) * 100 if wind > 20 else 0
    wind_risk = max(0, min(100, wind_risk))
    
    # 3. Rainfall Risk (>5 mm)
    rain_risk = ((worst_rain - 5) / (120 - 5)) * 100 if worst_rain > 5 else 0
    current_rain_risk = ((rain - 5) / (120 - 5)) * 100 if rain > 5 else 0
    rain_risk = max(rain_risk, current_rain_risk)
    rain_risk = max(0, min(100, rain_risk))
    
    # 4. AQI Risk (>50 US-AQI)
    aqi_risk = ((aqi - 50) / (250 - 50)) * 100 if aqi > 50 else 0
    aqi_risk = max(0, min(100, aqi_risk))
    
    # 5. Humidity Risk (Minor factor, mostly relative comfort / heat index)
    humidity_risk = 0
    if humidity > 80 and temp > 30:
        humidity_risk = ((humidity - 80) / 20) * 50
    elif humidity < 20:
        humidity_risk = ((20 - humidity) / 20) * 30
    humidity_risk = max(0, min(100, humidity_risk))
    
    return {
        "Temperature": round(temp_risk, 1),
        "Wind_Speed": round(wind_risk, 1),
        "Rainfall": round(rain_risk, 1),
        "AQI": round(aqi_risk, 1),
        "Humidity": round(humidity_risk, 1)
    }

def generate_alerts(env_data):
    """
    Analyzes environmental conditions and forecasts to generate critical alerts.
    """
    alerts = []
    
    # 1. Weather Code Based Alerts (WMO Codes)
    w_code = env_data.get('weather_code', 0)
    if w_code >= 95:
        alerts.append("Severe Thunderstorm Warning! Seek shelter immediately.")
    elif w_code >= 80:
        alerts.append("Violent rain showers detected. Expect localized flooding.")
    elif w_code >= 71:
        alerts.append("Heavy snowfall detected. Road conditions may be hazardous.")
    elif w_code >= 65:
        alerts.append("Heavy rainfall in progress. High flood risk in low-lying areas.")
    elif w_code in [66, 67, 56, 57]:
        alerts.append("Freezing rain/drizzle warning. Extremely slippery surfaces expected.")

    # 2. Threshold Based Alerts
    if env_data.get('AQI', 0) > 300:
        alerts.append("CRITICAL: Hazardous Air Quality! Avoid all outdoor exertion.")
    elif env_data.get('AQI', 0) > 200:
        alerts.append("Very Unhealthy Air Quality. Stay indoors.")
        
    if env_data.get('Wind_Speed', 0) > 90:
        alerts.append("Extreme Wind Warning! Stay away from trees and power lines.")
        
    if env_data.get('Temperature', 0) > 45:
        alerts.append("Lethal Heatwave Warning. Use cooling systems and stay hydrated.")
    elif env_data.get('Temperature', 0) < -10:
        alerts.append("Extreme Cold Warning. Risk of frostbite in minutes.")

    # 3. Forecast Trends Scanning for Proactive Warning
    hourly_temps = env_data.get('trends', {}).get('hourly', {}).get('temp', [])
    hourly_rains = env_data.get('trends', {}).get('hourly', {}).get('rain', [])
    
    max_forecast_temp = max(hourly_temps) if hourly_temps else env_data.get('Temperature', 20)
    min_forecast_temp = min(hourly_temps) if hourly_temps else env_data.get('Temperature', 20)
    max_forecast_rain = max(hourly_rains) if hourly_rains else env_data.get('Rainfall', 0)
    
    daily_temp_maxs = env_data.get('trends', {}).get('daily', {}).get('temp_max', [])
    daily_temp_mins = env_data.get('trends', {}).get('daily', {}).get('temp_min', [])
    daily_rain_sums = env_data.get('trends', {}).get('daily', {}).get('rain_sum', [])
    
    max_daily_temp = max(daily_temp_maxs) if daily_temp_maxs else max_forecast_temp
    min_daily_temp = min(daily_temp_mins) if daily_temp_mins else min_forecast_temp
    max_daily_rain = max(daily_rain_sums) if daily_rain_sums else max_forecast_rain

    if max_forecast_rain > 15:
        alerts.append(f"Imminent Heavy Rain: Downpour up to {max_forecast_rain:.1f} mm/h expected in the next 24 hours.")
    elif max_daily_rain > 50:
        alerts.append(f"Flood Risk Advisory: Cumulative daily rain up to {max_daily_rain:.1f} mm expected in the coming days.")
        
    if max_daily_temp > 40:
        alerts.append(f"Heatwave Warning: Temperatures expected to peak at {max_daily_temp:.1f}°C in the coming days.")
    elif min_daily_temp < 0:
        alerts.append(f"Frost Warning: Sub-zero conditions ({min_daily_temp:.1f}°C) expected in the coming days.")

    return alerts

def predict_risk(env_data, model, risk_breakdown):
    """
    Predicts the risk level and continuous risk score by blending ML classification 
    probabilities with raw calculated threat vectors.
    """
    if model:
        try:
            features = pd.DataFrame([{
                'Temperature': env_data['Temperature'],
                'Humidity': env_data['Humidity'],
                'Wind_Speed': env_data['Wind_Speed'],
                'Rainfall': env_data['Rainfall'],
                'AQI': env_data['AQI']
            }])
            prediction = model.predict(features)[0]
            risk_level = prediction
            
            # Continuous Risk Score based on probabilities (Weighted Average)
            probabilities = model.predict_proba(features)[0]
            class_probs = dict(zip(model.classes_, probabilities))
            p_low = class_probs.get('Low', 0.0)
            p_medium = class_probs.get('Medium', 0.0)
            p_high = class_probs.get('High', 0.0)
            
            risk_score = int(p_low * 15 + p_medium * 55 + p_high * 95)
            
            # Blend with forecast maximum threat to make it proactive
            forecast_max_threat = max(risk_breakdown.values())
            if forecast_max_threat > risk_score:
                risk_score = int(risk_score * 0.4 + forecast_max_threat * 0.6)
                
            # Recalculate risk level category based on proactive score
            if risk_score >= 70:
                risk_level = "High"
            elif risk_score >= 35:
                risk_level = "Medium"
            else:
                risk_level = "Low"
                
            source = "AI + Forecast Blend"
        except Exception as e:
            print(f"Prediction error: {e}")
            risk_score = int(max(risk_breakdown.values()))
            if risk_score < 35:
                risk_level = "Low"
            elif risk_score < 70:
                risk_level = "Medium"
            else:
                risk_level = "High"
            source = "Prediction Error (Fallback)"
    else:
        risk_score = int(max(risk_breakdown.values()))
        if risk_score < 35:
            risk_level = "Low"
        elif risk_score < 70:
            risk_level = "Medium"
        else:
            risk_level = "High"
        source = "Model not found (Fallback)"

    return risk_level, risk_score, source

def generate_recommendations(env_data, risk_level, alerts):
    """
    Generates actionable safety recommendations based on conditions.
    """
    recommendations = []
    
    if env_data.get('Rainfall', 0) > 50:
        recommendations.append("Heavy rain detected. Avoid flood-prone areas and drive safely.")
    elif env_data.get('Rainfall', 0) > 0:
        recommendations.append("Light precipitation expected. Consider carrying an umbrella.")
        
    if env_data.get('Wind_Speed', 0) > 70:
        recommendations.append("Dangerous wind speeds! Stay indoors and away from windows.")
    elif env_data.get('Wind_Speed', 0) > 40:
        recommendations.append("Strong winds detected. Secure loose outdoor items.")
        
    if env_data.get('Temperature', 0) > 38:
        recommendations.append("Extreme heat warning. Stay hydrated and limit outdoor activity.")
    elif env_data.get('Temperature', 0) < 0:
        recommendations.append("Freezing temperatures. Dress warmly and watch for ice.")
        
    if env_data.get('AQI', 0) > 200:
        recommendations.append("Hazardous air quality. Stay indoors with windows closed.")
    elif env_data.get('AQI', 0) > 100:
        recommendations.append("Poor air quality. Sensitive groups should wear masks outdoors.")
        
    # Fallback recommendations if no warning threshold is triggered
    if not recommendations:
        if risk_level == "Low":
            recommendations.append("Conditions are peaceful. Enjoy your day!")
        elif risk_level == "Medium":
            recommendations.append("Exercise minor caution outdoors. Stay aware of changes.")
        else:
            recommendations.append("High risk detected. Follow official local warnings immediately.")
            
    return recommendations

def generate_resources(resolved_city):
    """
    Generates local resource availability values dynamically.
    For demonstration purposes, uses a deterministic hash based on the city name characters.
    """
    city_sum = sum(ord(c) for c in resolved_city)
    return {
        "Rescue_Squads": (city_sum % 15) + 5,      # 5 to 19 squads
        "Medical_Units": (city_sum % 12) + 4,      # 4 to 15 units
        "Fire_Engines": (city_sum % 10) + 3,       # 3 to 12 engines
        "Emergency_Shelters": (city_sum % 6) + 2,   # 2 to 7 shelters
        "Supply_Kits": ((city_sum * 7) % 400) + 100 # 100 to 499 kits
    }
