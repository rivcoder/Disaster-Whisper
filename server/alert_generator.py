"""
server/alert_generator.py — End-to-End Alert Payload Generator
================================================================
The server-side entry point described in Section 3.1.

Workflow:
    1. Accept raw disaster parameters from forecasting centre.
    2. Validate and optimise the evacuation route.
    3. Encode all components into the compact 4-part payload.
    4. Return the payload string + a human-readable audit record.

The audit record is designed for broadcast station logging — it shows every
encoding decision, character counts, and the SMS budget breakdown.
"""

from __future__ import annotations
import datetime
from typing import List, Tuple

from codec.payload      import encode_payload, payload_breakdown
from codec.hazard       import encode_hazard, decode_hazard
from codec.role         import encode_role, decode_role, build_role_flags, role_description
from codec.polyline     import polyline_char_count
from server.route_optimizer import validate_waypoints, optimize_route, route_summary

Coord = Tuple[float, float]


def generate_alert(
    hazard:      str,
    role_flags:  int,
    coordinates: List[Coord],
    precision:   int = 4,
    auto_optimize: bool = True,
) -> str:
    """
    Generate a compact payload string ready for SMS/Cell Broadcast transmission.

    Args:
        hazard:        Hazard type code or full name (e.g. "F" or "Flood").
        role_flags:    4-bit audience bitmask (use build_role_flags() to construct).
        coordinates:   Ordered list of (lat, lng) evacuation waypoints.
        precision:     Coordinate decimal places: 3, 4, or 5. Default 4.
        auto_optimize: If True, automatically simplify routes with > 20 waypoints.

    Returns:
        Compact ASCII payload string. Append plain-text suffix before broadcasting.

    Raises:
        ValueError: If parameters fail validation.
    """
    # Validate
    validation = validate_waypoints(coordinates)
    if not validation["valid"]:
        raise ValueError(
            "Route validation failed:\n" + "\n".join(validation["errors"])
        )

    # Optimise if required
    route = coordinates
    if auto_optimize and len(coordinates) > 5:
        route = optimize_route(coordinates)

    return encode_payload(hazard, role_flags, route, precision)


def generate_alert_with_audit(
    hazard:      str,
    role_flags:  int,
    coordinates: List[Coord],
    precision:   int = 4,
    plain_text_suffix: str = "",
    auto_optimize: bool = True,
) -> dict:
    """
    Generate a payload and return it together with a full audit record.

    The audit record is suitable for:
        - Broadcast station logs
        - Demo display (web UI / CLI)
        - Paper verification (character counts, budget breakdown)

    Args:
        hazard:             Hazard type.
        role_flags:         4-bit audience bitmask.
        coordinates:        Ordered (lat, lng) waypoints.
        precision:          Coordinate decimal places.
        plain_text_suffix:  Optional plain-text tail appended after the payload prefix.
        auto_optimize:      Auto-simplify long routes.

    Returns:
        dict with keys:
            payload          — compact payload string
            full_sms         — payload + plain_text_suffix
            breakdown        — per-component character counts
            route_summary    — distance, waypoints, validation
            audit_timestamp  — ISO8601 timestamp
            sms_budget       — {total_chars, limit, remaining, fits}
    """
    # ── Validate & optimise ──────────────────────────────────────────────────
    validation = validate_waypoints(coordinates)
    if not validation["valid"]:
        raise ValueError(
            "Route validation failed:\n" + "\n".join(validation["errors"])
        )

    route = coordinates
    optimised = False
    if auto_optimize and len(coordinates) > 5:
        route     = optimize_route(coordinates)
        optimised = True

    # ── Encode ───────────────────────────────────────────────────────────────
    bd      = payload_breakdown(hazard, role_flags, route, precision)
    payload = bd["full_payload"]

    # ── SMS budget ───────────────────────────────────────────────────────────
    full_sms    = payload + plain_text_suffix
    total_chars = len(full_sms)
    sms_budget  = {
        "payload_chars":    len(payload),
        "suffix_chars":     len(plain_text_suffix),
        "total_chars":      total_chars,
        "limit":            160,
        "remaining":        160 - total_chars,
        "fits":             total_chars <= 160,
    }

    # ── Route summary ─────────────────────────────────────────────────────────
    rsummary = route_summary(route)

    # ── Human-readable breakdown ──────────────────────────────────────────────
    hazard_meta = decode_hazard(bd["hazard_code"]["char"])
    role_meta   = decode_role(bd["role_flag"]["char"])

    audit = {
        "payload":          payload,
        "full_sms":         full_sms,
        "breakdown": {
            "hazard_code": {
                "char":        bd["hazard_code"]["char"],
                "bytes":       1,
                "description": f"{hazard_meta['icon']} {hazard_meta['name']} ({hazard_meta['severity']})",
            },
            "role_flag": {
                "char":        bd["role_flag"]["char"],
                "bytes":       1,
                "description": role_description(role_flags),
                "hex_value":   f"0x{role_flags:X}",
                "binary":      f"0b{role_flags:04b}",
            },
            "polyline": {
                "str":         bd["polyline"]["str"],
                "bytes":       bd["polyline"]["bytes"],
                "description": f"{len(route)}-waypoint route at {precision}-decimal precision",
                "precision":   precision,
            },
            "checksum": {
                "char":        bd["checksum"]["char"],
                "bytes":       1,
                "description": "XOR integrity check",
            },
        },
        "route_summary":     rsummary,
        "sms_budget":        sms_budget,
        "precision":         precision,
        "route_optimised":   optimised,
        "audit_timestamp":   datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    return audit
