"""
codec/hazard.py — Hazard Code Registry
========================================
Maps single-character ASCII codes to disaster categories (Section 3.2, Point 1).

Each code is exactly 1 byte. The registry stores:
  - Full name
  - Default evacuation/response action
  - Severity tier (MODERATE / HIGH / EXTREME)
  - UI color (hex, for the web demo)
"""

from __future__ import annotations

HAZARD_REGISTRY: dict[str, dict] = {
    "F": {
        "name": "Flood",
        "name_hi": "बाढ़",
        "name_mr": "पूर",
        "name_ta": "வெள்ளம்",
        "severity": "EXTREME",
        "default_action": "evacuate",
        "color": "#1565C0",
        "icon": "💧",
    },
    "C": {
        "name": "Cyclone",
        "name_hi": "चक्रवात",
        "name_mr": "चक्रीवादळ",
        "name_ta": "சூறாவளி",
        "severity": "EXTREME",
        "default_action": "shelter",
        "color": "#6A1B9A",
        "icon": "🌀",
    },
    "L": {
        "name": "Landslide",
        "name_hi": "भूस्खलन",
        "name_mr": "भूस्खलन",
        "name_ta": "நிலச்சரிவு",
        "severity": "HIGH",
        "default_action": "evacuate",
        "color": "#4E342E",
        "icon": "⛰️",
    },
    "W": {
        "name": "Wildfire",
        "name_hi": "जंगल की आग",
        "name_mr": "वणवा",
        "name_ta": "காட்டுத் தீ",
        "severity": "HIGH",
        "default_action": "evacuate",
        "color": "#BF360C",
        "icon": "🔥",
    },
    "E": {
        "name": "Earthquake",
        "name_hi": "भूकंप",
        "name_mr": "भूकंप",
        "name_ta": "நிலநடுக்கம்",
        "severity": "EXTREME",
        "default_action": "drop-cover-hold",
        "color": "#F57F17",
        "icon": "🌍",
    },
    "T": {
        "name": "Tsunami",
        "name_hi": "सुनामी",
        "name_mr": "त्सुनामी",
        "name_ta": "சுனாமி",
        "severity": "EXTREME",
        "default_action": "move-inland",
        "color": "#006064",
        "icon": "🌊",
    },
    "H": {
        "name": "Heatwave",
        "name_hi": "लू",
        "name_mr": "उष्णतेची लाट",
        "name_ta": "வெப்ப அலை",
        "severity": "MODERATE",
        "default_action": "shelter",
        "color": "#E65100",
        "icon": "☀️",
    },
}

VALID_CODES: frozenset[str] = frozenset(HAZARD_REGISTRY.keys())


def encode_hazard(hazard_type: str) -> str:
    """
    Encode a hazard type string to its single-character code.

    Accepts either the full name (e.g. "Flood") or the code directly ("F").

    Returns:
        Single uppercase ASCII character code.

    Raises:
        ValueError: If the hazard type is unrecognised.
    """
    candidate = hazard_type.strip().upper()
    # Direct code match
    if candidate in VALID_CODES:
        return candidate
    # Full name match
    for code, meta in HAZARD_REGISTRY.items():
        if meta["name"].upper() == candidate:
            return code
    raise ValueError(
        f"Unknown hazard type: '{hazard_type}'. "
        f"Valid codes: {sorted(VALID_CODES)} or full names e.g. 'Flood'."
    )


def decode_hazard(code: str) -> dict:
    """
    Decode a single-character hazard code to full metadata.

    Returns:
        dict with keys: code, name, name_hi, severity, default_action, color, icon.

    Raises:
        ValueError: If code is not in VALID_CODES.
    """
    code = code.strip().upper()
    if code not in VALID_CODES:
        raise ValueError(
            f"Invalid hazard code: '{code}'. Valid codes: {sorted(VALID_CODES)}"
        )
    return {"code": code, **HAZARD_REGISTRY[code]}
