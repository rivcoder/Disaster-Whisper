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
from client.tier2_engine import render_tier2
from client.validator import validate_alert_output
from server.alert_generator import generate_alert_with_audit

app = Flask(__name__)

# Ensure absolute paths for JSON database files
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# Simulated active cell broadcast transmission channel
ACTIVE_BROADCAST_MESSAGE: str | None = None


def _read_data_file(filename: str) -> dict:
    path = os.path.join(DATA_DIR, filename)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ── ROUTING ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Render the main landing menu page."""
    return render_template("index.html")


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
    tier     = int(req_data.get("tier", 1))

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

        # Run device-asymmetric logic
        if tier == 2:
            rendered_alert = render_tier2(
                hazard_code=hazard_code,
                role_flags=role_flags,
                coordinates=coordinates,
                language="en",
            )
            validation = validate_alert_output(
                generated_text=rendered_alert["alert_text"],
                hazard_code=hazard_code,
                coordinates=coordinates,
                language="en",
            )
        else:
            rendered_alert = render_tier1(
                hazard_code=hazard_code,
                role_flags=role_flags,
                coordinates=coordinates,
                language="en",
            )
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


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
