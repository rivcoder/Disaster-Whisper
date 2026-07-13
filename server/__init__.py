"""
Disaster-Whisper Server Package
================================
Server-side components responsible for:
    1. Receiving raw disaster data (hazard type, coordinates, target audience)
    2. Optimising the evacuation route (waypoint reduction, distance validation)
    3. Encoding everything into the compact payload string
    4. Producing an audit log suitable for broadcast station logging

Modules:
    route_optimizer  — Coordinate list validation and preprocessing
    alert_generator  — End-to-end payload generation with audit trail
"""

from server.alert_generator import generate_alert, generate_alert_with_audit
from server.route_optimizer import optimize_route, validate_waypoints

__all__ = [
    "generate_alert",
    "generate_alert_with_audit",
    "optimize_route",
    "validate_waypoints",
]
