"""
Disaster-Whisper Web Demo Server
=================================
Flask web server implementing JSON API endpoints for:
1. Encoding disaster parameters into a compact broadcast payload.
2. Decoding payloads and simulating device-asymmetric alert rendering.
3. Fetching hazard and role metadata registries.
4. Simulating cell broadcasting (storing and fetching active transmissions).
"""

from __future__ import annotations
import os
import json
from flask import Flask, request, jsonify, render_template

from codec.payload import decode_payload
from client.clipboard_bridge import parse_sms_text
from client.tier1_engine import render_tier1
from client.validator import validate_alert_output
from server.alert_generator import generate_alert_with_audit
from deep_translator import GoogleTranslator

app = Flask(__name__)

# Ensure absolute paths for JSON database files
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# Simulated active cell broadcast transmission channel
ACTIVE_BROADCAST_MESSAGE: str | None = None

# Simulated databases for 2-way rescue requests and communication
RESCUE_REQUESTS: list[dict] = []
USER_MESSAGES: dict[str, list[dict]] = {}



def _read_data_file(filename: str) -> dict:
    path = os.path.join(DATA_DIR, filename)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ── ROUTING ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Render the main landing menu page."""
    return render_template("index.html")


@app.route("/manifest.json")
def serve_manifest():
    return app.send_static_file("manifest.json")


@app.route("/sw.js")
def serve_sw():
    return app.send_static_file("sw.js")



@app.route("/server")
def server_dashboard():
    """Render the Server Command Center page."""
    return render_template("server.html")


@app.route("/client")
def client_companion():
    """Render the Client smartphone screen emulator."""
    return render_template("client.html")


# ── BROADCAST SIMULATOR API ──────────────────────────────────────────────────

@app.route("/api/broadcast", methods=["POST"])
def post_broadcast():
    """Store the transmitted broadcast message on the server."""
    global ACTIVE_BROADCAST_MESSAGE
    req_data = request.get_json() or {}
    message  = req_data.get("message")
    
    if not message:
        return jsonify({"error": "Cannot broadcast an empty message."}), 400
        
    ACTIVE_BROADCAST_MESSAGE = message
    return jsonify({"status": "success", "broadcasted": message})


@app.route("/api/active_broadcast", methods=["GET"])
def get_active_broadcast():
    """Retrieve the currently active broadcast from airwaves."""
    if ACTIVE_BROADCAST_MESSAGE is None:
        return jsonify({"error": "No active broadcast message exists on the wireless grid."}), 404
    return jsonify({"message": ACTIVE_BROADCAST_MESSAGE})


# ── CODEC REGISTRIES AND ENCODER API ──────────────────────────────────────────

@app.route("/api/hazards", methods=["GET"])
def get_hazards():
    """Retrieve the static hazard registries."""
    try:
        data = _read_data_file("hazard_registry.json")
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/roles", methods=["GET"])
def get_roles():
    """Retrieve the static role bitmask registries."""
    try:
        data = _read_data_file("role_registry.json")
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/encode", methods=["POST"])
def api_encode():
    """
    Encode hazard metadata and a route coordinates list into a payload prefix.
    """
    req_data = request.get_json() or {}
    
    hazard      = req_data.get("hazard")
    role_flags  = req_data.get("role_flags", 0)
    coords      = req_data.get("coordinates")
    suffix      = req_data.get("plain_text_suffix", "")

    if not hazard:
        return jsonify({"error": "Missing 'hazard' parameter."}), 400
    if not coords or not isinstance(coords, list):
        return jsonify({"error": "Missing or invalid 'coordinates' parameter. Must be list of pairs."}), 400

    try:
        # Convert coordinates list to list of tuples for the compiler
        coordinate_tuples = [(float(c[0]), float(c[1])) for c in coords]
        
        audit_record = generate_alert_with_audit(
            hazard=hazard,
            role_flags=role_flags,
            coordinates=coordinate_tuples,
            precision=4,
            plain_text_suffix=suffix,
            auto_optimize=True,
        )
        return jsonify(audit_record)
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Internal encoding error: {str(e)}"}), 500


@app.route("/api/decode", methods=["POST"])
def api_decode():
    """
    Simulate smartphone alert ingestion and decoding.
    """
    req_data = request.get_json() or {}
    
    sms_text = req_data.get("sms_text", "")
    language = req_data.get("language", "en")

    if not sms_text:
        return jsonify({"error": "No message text provided."}), 400

    try:
        # Pathway A Clipboard Bridge logic to parse and strip payload
        extraction = parse_sms_text(sms_text)
        if not extraction["found"]:
            return jsonify({"error": f"Payload extraction failed: {extraction['reason']}"}), 400

        payload = extraction["payload"]
        
        # Decompress 4-part payload
        decoded_payload = decode_payload(payload, precision=4)

        hazard_code = decoded_payload["hazard"]["code"]
        role_flags  = decoded_payload["role"]["value"]
        coordinates = decoded_payload["coordinates"]

        # Run standard deterministic template engine
        rendered_alert = render_tier1(
            hazard_code=hazard_code,
            role_flags=role_flags,
            coordinates=coordinates,
            language=language,
        )
        
        # Append the custom plaintext message if one was provided in the SMS
        custom_message = extraction.get("suffix", "").strip()
        if custom_message:
            # Attempt to translate the custom message to the target language
            try:
                if language and language != "en":
                    translator = GoogleTranslator(source='auto', target=language)
                    custom_message = translator.translate(custom_message)
            except Exception as e:
                print(f"Translation failed: {e}")
                
            rendered_alert["alert_text"] += f"\n\n[HQ Broadcast]: {custom_message}"
            
        validation = None


        return jsonify({
            "extraction":      extraction,
            "payload_decoded": decoded_payload,
            "rendered_alert":  rendered_alert,
            "validation":      validation,
        })

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Internal processing error: {str(e)}"}), 500


# ── RESCUE & 2-WAY COMMUNICATION API ──────────────────────────────────────────

@app.route("/api/rescue_request", methods=["POST"])
def post_rescue_request():
    """Submit a rescue request or SOS signal from a client."""
    import time
    req_data = request.get_json() or {}
    client_id = req_data.get("clientId")
    latitude = req_data.get("latitude")
    longitude = req_data.get("longitude")
    status = req_data.get("status", "SOS")
    message = req_data.get("message", "")
    
    if not client_id or latitude is None or longitude is None:
        return jsonify({"error": "Missing clientId, latitude, or longitude."}), 400
        
    req_id = f"req_{int(time.time() * 1000)}"
    request_record = {
        "id": req_id,
        "clientId": client_id,
        "latitude": float(latitude),
        "longitude": float(longitude),
        "status": status,
        "message": message,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Store or update the rescue request
    # If client already has a request, update it, otherwise add
    for r in RESCUE_REQUESTS:
        if r["clientId"] == client_id:
            r.update(request_record)
            break
    else:
        RESCUE_REQUESTS.append(request_record)
        
    # Append the message to the user communication logs
    if client_id not in USER_MESSAGES:
        USER_MESSAGES[client_id] = []
        
    if message:
        USER_MESSAGES[client_id].append({
            "sender": "user",
            "message": message,
            "timestamp": request_record["timestamp"]
        })
        
    return jsonify({"status": "success", "request": request_record})


@app.route("/api/rescue_requests", methods=["GET"])
def get_rescue_requests():
    """Retrieve all active rescue requests (Government dashboard)."""
    return jsonify(RESCUE_REQUESTS)


@app.route("/api/respond_rescue", methods=["POST"])
def respond_rescue():
    """Send a response message from Government operator to a user."""
    import time
    req_data = request.get_json() or {}
    client_id = req_data.get("clientId")
    message = req_data.get("message")
    
    if not client_id or not message:
        return jsonify({"error": "Missing clientId or message."}), 400
        
    if client_id not in USER_MESSAGES:
        USER_MESSAGES[client_id] = []
        
    msg_record = {
        "sender": "gov",
        "message": message,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    USER_MESSAGES[client_id].append(msg_record)
    
    return jsonify({"status": "success", "message": msg_record})


@app.route("/api/user_messages", methods=["GET"])
def get_user_messages():
    """Get chat logs for a specific client."""
    client_id = request.args.get("clientId")
    if not client_id:
        return jsonify({"error": "Missing clientId parameter."}), 400
        
    messages = USER_MESSAGES.get(client_id, [])
    return jsonify(messages)



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
