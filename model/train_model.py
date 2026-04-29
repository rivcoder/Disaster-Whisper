import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib
import os

def generate_synthetic_data(num_samples=1000):
    """
    Generates synthetic environmental data.
    Features: Temperature, Humidity, Wind_Speed, Rainfall, AQI
    Target: Risk Level (Low, Medium, High)
    """
    np.random.seed(42)
    
    # Generate random features
    temperature = np.random.uniform(-10, 50, num_samples)
    humidity = np.random.uniform(10, 100, num_samples)
    wind_speed = np.random.uniform(0, 120, num_samples)
    rainfall = np.random.uniform(0, 200, num_samples)
    aqi = np.random.uniform(0, 400, num_samples)
    
    data = pd.DataFrame({
        'Temperature': temperature,
        'Humidity': humidity,
        'Wind_Speed': wind_speed,
        'Rainfall': rainfall,
        'AQI': aqi
    })
    
    def determine_risk(row):
        # High Risk Conditions
        if row['Wind_Speed'] > 80 or row['Rainfall'] > 120 or row['AQI'] > 250 or row['Temperature'] > 42 or row['Temperature'] < -5:
            return 'High'
        # Medium Risk Conditions
        elif row['Wind_Speed'] > 50 or row['Rainfall'] > 60 or row['AQI'] > 150 or row['Temperature'] > 35:
            return 'Medium'
        # Low Risk
        else:
            return 'Low'
            
    data['Risk_Level'] = data.apply(determine_risk, axis=1)
    return data

def train_and_save_model():
    print("Generating synthetic data...")
    df = generate_synthetic_data(5000)
    
    X = df[['Temperature', 'Humidity', 'Wind_Speed', 'Rainfall', 'AQI']]
    y = df['Risk_Level']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("Training Random Forest Classifier...")
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test)
    print("\nModel Evaluation:")
    print(classification_report(y_test, y_pred))
    
    # Save Model
    model_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, 'model.pkl')
    
    joblib.dump(model, model_path)
    print(f"\nModel successfully saved to {model_path}")

if __name__ == "__main__":
    train_and_save_model()
