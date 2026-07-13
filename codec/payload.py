"""
codec/payload.py — Full Payload Assembler & Parser
====================================================
Implements the complete 4-part compact payload format (Section 3.2):

    Payload = [Hazard_Code][Role_Flag][Polyline_Payload][Checksum]
    Example:  F 3 yuzL{qhm@_HyJiDiNiFzBdNoI q
              ↑ ↑ ────────────────────────── ↑
              │ │  Polyline (variable length)  │
              │ Role flag                      Checksum
              Hazard code

Total size: 1 + 1 + (16–29 chars) + 1 = 19–32 bytes
At 4-decimal, 5-waypoint: typically 26–28 bytes (fits well within SMS 160-char limit).

Usage:
    payload_str = encode_payload(
        hazard="F",
        role_flags=3,
        coordinates=[(22.7181, 75.8574), ...],
        precision=4,
    )
    result = decode_payload(payload_str)
"""

from __future__ import annotations
from typing import List, Tuple

from codec.hazard    import encode_hazard, decode_hazard
from codec.role      import encode_role, decode_role
from codec.polyline  import encode_polyline, decode_polyline, polyline_char_count, VALID_PRECISIONS
from codec.checksum  import compute_checksum, verify_checksum

Coord = Tuple[float, float]


# ─────────────────────────────────────────────────────────────────────────────
# Encode
# ─────────────────────────────────────────────────────────────────────────────

def encode_payload(
    hazard: str,
    role_flags: int,
    coordinates: List[Coord],
    precision: int = 4,
) -> str:
    """
    Build the complete compressed payload string.

    Args:
        hazard:      Hazard type string or code (e.g. "Flood" or "F").
        role_flags:  4-bit audience bitmask (0x0–0xF).
        coordinates: Ordered list of (lat, lng) waypoints (min 2).
        precision:   Coordinate decimal places: 3, 4, or 5. Default 4.

    Returns:
        Compact ASCII payload string, SMS-safe, all printable characters.

    Raises:
        ValueError: If any component fails validation.
    """
    hazard_code  = encode_hazard(hazard)
    role_char    = encode_role(role_flags)
    polyline_str = encode_polyline(coordinates, precision)
    data         = hazard_code + role_char + polyline_str
    checksum     = compute_checksum(data)
    return data + checksum


# ─────────────────────────────────────────────────────────────────────────────
# Decode
# ─────────────────────────────────────────────────────────────────────────────

def decode_payload(
    payload: str,
    precision: int = 4,
) -> dict:
    """
    Parse and decode a complete payload string.

    Args:
        payload:   String produced by encode_payload.
        precision: Must match the precision used during encoding.

    Returns:
        dict with keys:
            hazard      — dict: {code, name, name_hi, severity, default_action, color, icon}
            role        — dict: {value, char, active_roles, is_general, all_groups}
            coordinates — list of (lat, lng) float tuples
            checksum_ok — bool: True if payload passed integrity check
            raw_payload — the original payload string
            stats       — dict: {payload_bytes, polyline_chars, sms_remaining, sms_fits}

    Raises:
        ValueError: If payload is too short or structurally invalid.
    """
    if len(payload) < 4:  # min: 1 hazard + 1 role + 2 poly-chars (1 pair) + 1 checksum
        raise ValueError(
            f"Payload too short: {len(payload)} chars. Minimum is 4."
        )

    # ── Integrity check ──────────────────────────────────────────────────────
    checksum_ok = verify_checksum(payload)

    # ── Field extraction ─────────────────────────────────────────────────────
    hazard_code  = payload[0]           # byte 0
    role_char    = payload[1]           # byte 1
    polyline_str = payload[2:-1]        # bytes 2 … n-2
    # payload[-1] is the checksum char (already validated above)

    hazard_meta = decode_hazard(hazard_code)
    role_meta   = decode_role(role_char)
    coordinates = decode_polyline(polyline_str, precision)

    poly_stats  = polyline_char_count(coordinates, precision)

    return {
        "hazard":      hazard_meta,
        "role":        role_meta,
        "coordinates": coordinates,
        "checksum_ok": checksum_ok,
        "raw_payload": payload,
        "stats": {
            "payload_bytes":  len(payload),
            "polyline_chars": len(polyline_str),
            "sms_remaining":  160 - len(payload),
            "sms_fits":       len(payload) <= 160,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Audit helpers
# ─────────────────────────────────────────────────────────────────────────────

def payload_breakdown(
    hazard: str,
    role_flags: int,
    coordinates: List[Coord],
    precision: int = 4,
) -> dict:
    """
    Return a detailed breakdown of the payload without assembling the final string.
    Useful for the demo UI character-budget display.
    """
    hazard_code  = encode_hazard(hazard)
    role_char    = encode_role(role_flags)
    polyline_str = encode_polyline(coordinates, precision)
    data         = hazard_code + role_char + polyline_str
    checksum     = compute_checksum(data)
    full_payload = data + checksum

    return {
        "hazard_code":   {"char": hazard_code,  "bytes": 1},
        "role_flag":     {"char": role_char,     "bytes": 1},
        "polyline":      {"str":  polyline_str,  "bytes": len(polyline_str)},
        "checksum":      {"char": checksum,      "bytes": 1},
        "full_payload":  full_payload,
        "total_bytes":   len(full_payload),
        "sms_remaining": 160 - len(full_payload),
        "sms_fits":      len(full_payload) <= 160,
        "precision":     precision,
        "n_waypoints":   len(coordinates),
    }
