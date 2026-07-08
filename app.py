from flask import Flask, request, jsonify, render_template
from backend_utils import get_real_environmental_data
import risk_engine
import joblib
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
    """
    Renders the main Disaster Whisper dashboard.
    """
    return render_template('index.html')

@app.route('/api/predict', methods=['POST'])
def predict():
    """
    Orchestrates the environmental risk prediction workflow:
    1. Parse city name from request.
    2. Fetch live and forecast weather and air quality from Open-Meteo.
    3. Calculate individual risk vectors.
    4. Estimate combined risk using ML model.
    5. Generate alerts, recommendations, and local resource values.
    """
    data = request.json
    city = data.get('city', '').strip()
    
    if not city:
        return jsonify({"error": "Please enter a valid city name."}), 400
        
    try:
        # Fetch geocoding, weather, and AQI data
        env_data = get_real_environmental_data(city)
        resolved_city = env_data.pop("resolved_city") # extracted to display to the user
    except ValueError as ve:
        return jsonify({"error": f"We couldn't find the city '{city}'. Please double-check the spelling and try again."}), 404
    except ConnectionError as ce:
        return jsonify({"error": "Our weather service is temporarily unavailable. Please try again in a few moments."}), 503
        
    # Generate Alerts
    alerts = risk_engine.generate_alerts(env_data)
    
    # Calculate Risk Breakdown (Individual Threat Vectors in %)
    risk_breakdown = risk_engine.calculate_risk_breakdown(env_data)
    
    # Predict Risk Level & Score using the ML model (blended with forecast)
    risk_level, risk_score, source = risk_engine.predict_risk(env_data, model, risk_breakdown)
            
    # Generate safety recommendations
    recommendations = risk_engine.generate_recommendations(env_data, risk_level, alerts)
 
    # Generate local resource allocation counts
    resources = risk_engine.generate_resources(resolved_city)

    # Compile the final response payload
    response = {
        "city": resolved_city,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "risk_breakdown": risk_breakdown,
        "source": source,
        "alerts": alerts,
        "data": env_data,
        "recommendations": recommendations,
        "trends": env_data.get("trends", {}),
        "resources": resources
    }
    
    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
