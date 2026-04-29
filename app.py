from flask import Flask, request, jsonify, render_template
from backend_utils import get_real_environmental_data
import joblib
import pandas as pd
import os

app = Flask(__name__)

# Load the ML model
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'model', 'model.pkl')
try:
    model = joblib.load(MODEL_PATH)
    print("Model loaded successfully.")
except Exception as e:
    print(f"Error loading model: {e}")
    model = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/predict', methods=['POST'])
def predict():
    data = request.json
    city = data.get('city', '').strip()
    
    if not city:
        return jsonify({"error": "Please enter a valid city name."}), 400
        
    try:
        env_data = get_real_environmental_data(city)
        resolved_city = env_data.pop("resolved_city") # remove from features, use for display
    except ValueError as ve:
        return jsonify({"error": f"We couldn't find the city '{city}'. Please double-check the spelling and try again."}), 404
    except ConnectionError as ce:
        return jsonify({"error": "Our weather service is temporarily unavailable. Please try again in a few moments."}), 503
        
    alerts = []
    
    # Use ML Model to predict risk level
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
            source = "AI Prediction"
        except Exception as e:
            print(f"Prediction error: {e}")
            risk_level = "Unknown"
            source = "Prediction Error"
    else:
        risk_level = "Unknown"
        source = "Model not found"
            
    # Generate Dynamic Recommendations
    recommendations = []
    
    if env_data['Rainfall'] > 50:
        recommendations.append("Heavy rain detected. Avoid flood-prone areas and drive safely.")
    elif env_data['Rainfall'] > 0:
        recommendations.append("Light precipitation expected. Consider carrying an umbrella.")
        
    if env_data['Wind_Speed'] > 70:
        recommendations.append("Dangerous wind speeds! Stay indoors and away from windows.")
    elif env_data['Wind_Speed'] > 40:
        recommendations.append("Strong winds detected. Secure loose outdoor items.")
        
    if env_data['Temperature'] > 38:
        recommendations.append("Extreme heat warning. Stay hydrated and limit outdoor activity.")
    elif env_data['Temperature'] < 0:
        recommendations.append("Freezing temperatures. Dress warmly and watch for ice.")
        
    if env_data['AQI'] > 200:
        recommendations.append("Hazardous air quality. Stay indoors with windows closed.")
    elif env_data['AQI'] > 100:
        recommendations.append("Poor air quality. Sensitive groups should wear masks outdoors.")
        
    # Fallback if no specific threshold is crossed
    if not recommendations:
        if risk_level == "Low":
            recommendations.append("Conditions are peaceful. Enjoy your day!")
        elif risk_level == "Medium":
            recommendations.append("Exercise minor caution outdoors. Stay aware of changes.")
        else:
            recommendations.append("High risk detected. Follow official local warnings immediately.")

            
    response = {
        "city": resolved_city,
        "risk_level": risk_level,
        "source": source,
        "alerts": alerts,
        "data": env_data,
        "recommendations": recommendations
    }
    
    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
