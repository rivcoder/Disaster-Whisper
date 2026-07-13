"""
server/route_optimizer.py — Evacuation Route Validator & Preprocessor
=======================================================================
Prepares raw coordinate inputs for polyline encoding (Section 3.1).

Responsibilities:
    1. Validate coordinate ranges (India geographic bounds).
    2. Check minimum/maximum waypoint count.
    3. Detect and remove duplicate consecutive waypoints.
    4. Validate that consecutive waypoints are within a reasonable distance
       (too far apart → likely data error; too close → unnecessary density).
    5. Optionally simplify a dense route to a target waypoint count using
       the Ramer-Douglas-Peucker (RDP) algorithm.

The RDP simplification is included so operators can supply GPS tracks with many
points and let the server reduce them to the compact 5-waypoint ideal described
in the paper without losing the overall route shape.
"""

from __future__ import annotations
import math
from typing import List, Tuple

Coord = Tuple[float, float]

# ─────────────────────────────────────────────────────────────────────────────
# Geographic bounds (India + surrounding buffer)
# ─────────────────────────────────────────────────────────────────────────────
LAT_MIN, LAT_MAX =  6.0,  38.0   # includes Andaman & Nicobar
LNG_MIN, LNG_MAX = 66.0,  98.0

# Route distance limits
MIN_STEP_KM = 0.05    # 50 m — below this, points are treated as duplicates
MAX_STEP_KM = 50.0    # 50 km — above this, the route may have a data error

MAX_WAYPOINTS  = 20   # hard maximum before simplification
IDEAL_WAYPOINTS = 5   # target for payload compactness


def _haversine(a: Coord, b: Coord) -> float:
    """Return great-circle distance between two lat/lng points in km."""
    R    = 6371.0
    lat1 = math.radians(a[0]);  lat2 = math.radians(b[0])
    lon1 = math.radians(a[1]);  lon2 = math.radians(b[1])
    dlat = lat2 - lat1;          dlon = lon2 - lon1
    h    = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    return R * 2 * math.asin(math.sqrt(h))


def _perpendicular_distance(point: Coord, line_start: Coord, line_end: Coord) -> float:
    """
    Return perpendicular distance (degrees) from `point` to the line segment
    defined by `line_start` → `line_end`. Used by RDP simplification.
    Uses flat-earth approximation (acceptable for city-scale routes < 50 km).
    """
    if line_start == line_end:
        return _haversine(point, line_start)
    x0, y0 = point
    x1, y1 = line_start
    x2, y2 = line_end
    # Line equation: ax + by + c = 0
    dx, dy = x2 - x1, y2 - y1
    num    = abs(dy * x0 - dx * y0 + x2 * y1 - y2 * x1)
    denom  = math.sqrt(dy**2 + dx**2)
    return num / denom if denom > 0 else 0.0


def _rdp(coords: List[Coord], epsilon: float) -> List[Coord]:
    """
    Ramer-Douglas-Peucker line simplification.
    epsilon: maximum allowed perpendicular deviation (degrees).
    """
    if len(coords) < 3:
        return list(coords)
    # Find point with maximum distance from the line start→end
    max_dist  = 0.0
    max_index = 0
    for i in range(1, len(coords) - 1):
        d = _perpendicular_distance(coords[i], coords[0], coords[-1])
        if d > max_dist:
            max_dist  = d
            max_index = i
    if max_dist > epsilon:
        left  = _rdp(coords[:max_index + 1], epsilon)
        right = _rdp(coords[max_index:], epsilon)
        return left[:-1] + right
    else:
        return [coords[0], coords[-1]]


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def validate_waypoints(coordinates: List[Coord]) -> dict:
    """
    Validate a list of (lat, lng) waypoints.

    Returns:
        dict with keys:
            valid     — True if all checks pass
            errors    — list of error strings (empty if valid)
            warnings  — list of non-fatal warning strings
            distances — list of step distances in km

    Does NOT modify the input list.
    """
    errors:   list[str] = []
    warnings: list[str] = []
    distances: list[float] = []

    if len(coordinates) < 2:
        errors.append(f"At least 2 waypoints required, got {len(coordinates)}.")
        return {"valid": False, "errors": errors, "warnings": warnings, "distances": []}

    if len(coordinates) > MAX_WAYPOINTS:
        errors.append(
            f"Too many waypoints: {len(coordinates)}. Maximum is {MAX_WAYPOINTS}. "
            "Use optimize_route() to simplify."
        )

    for i, (lat, lng) in enumerate(coordinates):
        if not (LAT_MIN <= lat <= LAT_MAX):
            errors.append(f"Waypoint {i+1}: latitude {lat} outside India bounds [{LAT_MIN}, {LAT_MAX}].")
        if not (LNG_MIN <= lng <= LNG_MAX):
            errors.append(f"Waypoint {i+1}: longitude {lng} outside India bounds [{LNG_MIN}, {LNG_MAX}].")

    for i in range(len(coordinates) - 1):
        d = _haversine(coordinates[i], coordinates[i + 1])
        distances.append(round(d, 3))
        if d < MIN_STEP_KM:
            warnings.append(
                f"Steps {i+1}→{i+2}: {d*1000:.0f} m apart — considered duplicate. "
                "Use optimize_route() to clean."
            )
        if d > MAX_STEP_KM:
            errors.append(
                f"Steps {i+1}→{i+2}: {d:.1f} km apart — exceeds {MAX_STEP_KM} km limit. "
                "Check coordinate data."
            )

    return {
        "valid":     len(errors) == 0,
        "errors":    errors,
        "warnings":  warnings,
        "distances": distances,
    }


def optimize_route(
    coordinates: List[Coord],
    target_waypoints: int = IDEAL_WAYPOINTS,
    epsilon: float = 0.0005,
) -> List[Coord]:
    """
    Simplify and clean a coordinate list for compact polyline encoding.

    Steps:
        1. Clamp coordinates to 4 decimal places.
        2. Remove duplicate consecutive points (distance < MIN_STEP_KM).
        3. Apply RDP simplification to approach `target_waypoints`.
        4. Always preserve first and last waypoint.

    Args:
        coordinates:      Raw (lat, lng) list from operator input.
        target_waypoints: Desired waypoint count (default 5 per paper).
        epsilon:          RDP tolerance in degrees (default ≈ 55 m at equator).

    Returns:
        Cleaned, simplified list of (lat, lng) tuples.

    Raises:
        ValueError: If fewer than 2 valid unique points remain after cleaning.
    """
    if len(coordinates) < 2:
        raise ValueError("At least 2 coordinates required.")

    # Step 1: Clamp precision
    clamped = [(round(lat, 4), round(lng, 4)) for lat, lng in coordinates]

    # Step 2: Remove duplicate consecutive points
    deduped: List[Coord] = [clamped[0]]
    for pt in clamped[1:]:
        if _haversine(deduped[-1], pt) >= MIN_STEP_KM:
            deduped.append(pt)
    if len(deduped) < 2:
        raise ValueError("After deduplication, fewer than 2 unique waypoints remain.")

    # Step 3: RDP simplification if needed
    if len(deduped) > target_waypoints:
        simplified = _rdp(deduped, epsilon)
        # If RDP removes too many points, increase epsilon iteratively
        attempt = 0
        while len(simplified) < 2 and attempt < 10:
            epsilon  *= 0.5
            simplified = _rdp(deduped, epsilon)
            attempt   += 1
        deduped = simplified

    return deduped


def route_summary(coordinates: List[Coord]) -> dict:
    """
    Return a human-readable summary of a route for audit logs and demo UI.
    """
    validation = validate_waypoints(coordinates)
    total_km   = sum(validation["distances"]) if validation["distances"] else 0.0
    return {
        "n_waypoints":  len(coordinates),
        "total_km":     round(total_km, 2),
        "start":        coordinates[0]  if coordinates else None,
        "end":          coordinates[-1] if coordinates else None,
        "step_distances_km": validation["distances"],
        "validation":   validation,
    }
