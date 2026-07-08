# Disaster-Whisper

**Disaster Whisper** is a web-based prototype that estimates environmental risk levels for a given city using real-time weather data and a lightweight machine learning model.


---

## 🚀 Features

🌦️ Live environmental data (temperature, humidity, wind, etc.)

🧠 ML-based risk estimation (Random Forest model)

⚖️ Hybrid system (ML predictions + rule-based corrections)

📊 Risk Index (%) with simple interpretation

📍 City-based search

⏱️ Real-time updates

🌐 Web interface (lightweight, responsive)

---

## 🛠️ Tech Stack

**Backend:** Python (Flask)

**Machine Learning:** Scikit-learn

**Data Processing:** Pandas, NumPy

**Frontend:** HTML, CSS, JavaScript

**API:** Open-Meteo (no API key required)

---

## 🧠 How It Works

* User enters a city in the web interface

* Backend fetches live environmental data

* Key parameters extracted:

  * Temperature
  * Humidity
  * Wind speed
  * AQI

* Data flows through:

  * Trained ML model (`model.pkl`)
  * Rule-based validation layer

* Output displayed on UI:

  * Risk Index (%)
  * Status message
  * Raw environmental data

---

## 📊 Risk Index Explanation

The Risk Index is:

* A **model-based estimate**
* Based on environmental conditions
* Adjusted using simple rule logic for stability

---

## ⚠️ Project Status

* **Prototype (early-stage)**
* No production-level dataset yet
* No API key dependencies (kept simple intentionally)
* Focus: system design + ML integration + real-time flow

---

## 🤖 AI Usage Disclosure

AI tools were used to:

* Assist in development and debugging
* Improve structure and documentation

Core implementation decisions like:

* Architecture
* Risk logic
* Data handling
* UI flow

were built intentionally to demonstrate understanding.

---

## 📌 Use Cases

* Learning Flask + APIs
* Understanding ML integration in web apps
* Environmental data visualization

---

## 📈 Future Improvements

* Better training data → improved accuracy
* Pattern-based risk detection
* Multi-parameter expansion (AQI, rainfall intensity, etc.)
* UI/UX refinement
* Deployment (public access)
