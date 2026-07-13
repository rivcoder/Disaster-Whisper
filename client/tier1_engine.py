"""
client/tier1_engine.py — Template-Based Alert Renderer
========================================================
Tier 1 processing path (Section 3.4, Point 1):

    Decoded payload → Landmark lookup → Template slot-fill → Validated alert

No AI model required. Pure deterministic logic using only:
    - The decoded payload (hazard code, role flags, coordinates)
    - The offline landmark database (data/landmarks.json)
    - The offline template database (data/templates_en.json / templates_hi.json)

This engine ALWAYS works, even on feature phones and ultra-low-end devices.
It is also the fallback for Tier 2 when the SLM is not loaded or fails validation.

Template slot variables:
    {area}          — name of the starting landmark (flood zone / hazard origin)
    {destination}   — name of the nearest safe zone at the route's end
    {route_description} — human-readable waypoint list (for Tier 2 prompts)
    {target_audience}   — role-based audience label
"""

from __future__ import annotations
import json
import math
import os
from typing import List, Tuple

from codec.role import decode_role, role_description

Coord = Tuple[float, float]

# ─────────────────────────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────────────────────────

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

def _load_json(filename: str) -> dict:
    path = os.path.join(_DATA_DIR, filename)
    with open(path, encoding="utf-8") as f:
        return json.load(f)

_LANDMARKS  = None
_TEMPLATES  = {}   # keyed by language code


def _get_landmarks() -> list:
    global _LANDMARKS
    if _LANDMARKS is None:
        _LANDMARKS = _load_json("landmarks.json")["landmarks"]
    return _LANDMARKS


def _get_templates(language: str = "en") -> dict:
    if language not in _TEMPLATES:
        filename = f"templates_{language}.json"
        try:
            _TEMPLATES[language] = _load_json(filename)
        except FileNotFoundError:
            # Fallback to English
            _TEMPLATES[language] = _load_json("templates_en.json")
    return _TEMPLATES[language]


# ─────────────────────────────────────────────────────────────────────────────
# Landmark lookup
# ─────────────────────────────────────────────────────────────────────────────

def _haversine(a: Coord, b: Coord) -> float:
    R    = 6371.0
    lat1 = math.radians(a[0]); lat2 = math.radians(b[0])
    lon1 = math.radians(a[1]); lon2 = math.radians(b[1])
    dlat = lat2 - lat1;         dlon = lon2 - lon1
    h    = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(h))


def find_nearest_landmark(coord: Coord, prefer_safe_zone: bool = False) -> dict:
    """
    Return the landmark nearest to `coord`.

    If prefer_safe_zone=True, search safe zones first and only fall back to
    any landmark if no safe zone is within 3 km.
    """
    landmarks = _get_landmarks()

    if prefer_safe_zone:
        safe = [lm for lm in landmarks if lm.get("is_safe_zone")]
        if safe:
            best = min(safe, key=lambda lm: _haversine(coord, (lm["lat"], lm["lng"])))
            if _haversine(coord, (best["lat"], best["lng"])) <= 3.0:
                return best

    return min(
        landmarks,
        key=lambda lm: _haversine(coord, (lm["lat"], lm["lng"]))
    )


def build_route_description(coordinates: List[Coord], language: str = "en") -> str:
    """
    Build a human-readable route description string from coordinate list.
    Used in Tier 2 prompts and audit logs.
    """
    parts = []
    for i, coord in enumerate(coordinates):
        lm    = find_nearest_landmark(coord)
        label = lm.get("name_hi" if language == "hi" else "name", lm["name"])
        parts.append(f"({i+1}) {label}")
    return " → ".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# Template rendering
# ─────────────────────────────────────────────────────────────────────────────

def _select_template_key(role_value: int) -> str:
    """
    Select the most specific template key given active role flags.
    Priority: single role > general (0x0) > all (0xF → general).
    For multiple roles, use the highest priority single role.
    """
    priority_order = [
        (0x4, "tier1_physically_challenged"),  # highest priority — most vulnerable
        (0x2, "tier1_elderly"),
        (0x1, "tier1_agricultural"),
        (0x8, "tier1_volunteers"),
    ]
    for bit, key in priority_order:
        if role_value & bit:
            return key
    return "tier1_general"


def render_tier1(
    hazard_code:  str,
    role_flags:   int,
    coordinates:  List[Coord],
    language:     str = "en",
) -> dict:
    """
    Render a Tier 1 (template-based) emergency alert.

    Args:
        hazard_code:  Single character hazard code (e.g. "F").
        role_flags:   4-bit audience bitmask.
        coordinates:  Decoded waypoints from payload.
        language:     "en" or "hi" (default "en").

    Returns:
        dict with keys:
            alert_text      — final alert message string
            template_key    — which template was used
            area            — starting landmark name
            destination     — ending safe-zone landmark name
            route_waypoints — list of landmark names along the route
            language        — language used
            tier            — always 1
    """
    templates = _get_templates(language)

    if hazard_code not in templates:
        # Unknown hazard — use generic fallback
        return {
            "alert_text":     f"⚠️ EMERGENCY ALERT — Please evacuate to the nearest safe zone. Call 112.",
            "template_key":   "fallback",
            "area":           "Unknown",
            "destination":    "Nearest safe zone",
            "route_waypoints": [],
            "language":       language,
            "tier":           1,
        }

    hazard_templates = templates[hazard_code]

    # ── Landmark lookup ───────────────────────────────────────────────────────
    start_lm = find_nearest_landmark(coordinates[0],  prefer_safe_zone=False)
    end_lm   = find_nearest_landmark(coordinates[-1], prefer_safe_zone=True)

    name_key = "name_hi" if language == "hi" else "name"
    area        = start_lm.get(name_key, start_lm["name"])
    destination = end_lm.get(name_key, end_lm["name"])

    route_waypoints = []
    for coord in coordinates:
        lm = find_nearest_landmark(coord)
        route_waypoints.append(lm.get(name_key, lm["name"]))

    # ── Template selection ────────────────────────────────────────────────────
    template_key = _select_template_key(role_flags)
    template_str = hazard_templates.get(template_key) or hazard_templates.get("tier1_general") or hazard_templates.get("fallback", "⚠️ EMERGENCY ALERT")

    # ── Slot fill ─────────────────────────────────────────────────────────────
    target_audience = role_description(role_flags, language)
    alert_text = template_str.format(
        area=area,
        destination=destination,
        target_audience=target_audience,
        route_description=" → ".join(route_waypoints),
    )

    return {
        "alert_text":      alert_text,
        "template_key":    template_key,
        "area":            area,
        "destination":     destination,
        "route_waypoints": route_waypoints,
        "language":        language,
        "tier":            1,
    }
