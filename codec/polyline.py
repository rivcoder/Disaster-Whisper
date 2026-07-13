"""
codec/polyline.py — Compact Evacuation Route Encoder/Decoder
==============================================================
Implements the polyline compression algorithm described in Section 3.3.

Algorithm: Modified Google Polyline Encoding at configurable decimal precision.
Reference: Google Maps Encoded Polyline Algorithm Format (developers.google.com)

Key modification from standard Google Polyline (which uses 10^5):
    - Default scale factor: 10^4 (4 decimal places)
    - This reduces encoded length by ~20% vs 5-decimal encoding
    - 4-decimal precision = ±5.5 m horizontal accuracy (sufficient for street-level routing)

Encoding steps (per coordinate value):
    1.  Round coordinate to `precision` decimal places
    2.  Multiply by 10^precision → integer
    3.  Delta-encode: subtract previous integer value (first coordinate: absolute value)
    4.  Left-shift by 1 (multiply by 2)
    5.  If the delta is negative, bitwise-invert the result (two's complement sign trick)
    6.  Split into 5-bit chunks from LSB to MSB
    7.  Set bit 5 (0x20) on every chunk except the last (continuation flag)
    8.  Add ASCII offset 63 to each chunk → printable character in '?' .. '~'
    9.  Concatenate all characters

Decoding is the exact bitwise reverse.

Precision vs character-count table (5-waypoint route, Indore city scale):
    Precision  | Scale  | Grid Resolution | Polyline Length
    -----------+--------+-----------------+----------------
    3 decimals | 1,000  | ~110 m          | ~18–22 chars
    4 decimals | 10,000 |  ~11 m          | ~22–28 chars  ← optimal
    5 decimals | 100,000|   ~1 m          | ~30–36 chars

Note: Exact lengths depend on coordinate magnitudes; the dominant factor is the
size of the absolute first coordinate pair (typically 4–5 chars each at 4-decimal).
"""

from __future__ import annotations
from typing import List, Tuple

Coord = Tuple[float, float]   # (latitude, longitude)

VALID_PRECISIONS = {3: 1_000, 4: 10_000, 5: 100_000}
DEFAULT_PRECISION = 4


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _encode_value(value: int) -> str:
    """
    Encode a single signed integer using the Google Polyline chunk scheme.

    Steps:
      1. Left-shift by 1.
      2. Bitwise-invert if negative.
      3. Split into 5-bit chunks (LSB first), set continuation bit (0x20) on all
         but the last chunk.
      4. Add 63 → printable ASCII ('?' .. '~').
    """
    value <<= 1
    if value < 0:
        value = ~value

    chunks: list[str] = []
    while value >= 0x20:
        chunks.append(chr((0x20 | (value & 0x1F)) + 63))
        value >>= 5
    chunks.append(chr(value + 63))
    return "".join(chunks)


def _decode_value(encoded: str, index: int) -> tuple[int, int]:
    """
    Decode one signed integer from `encoded` starting at `index`.

    Returns:
        (decoded_int, next_index)
    """
    result = 0
    shift  = 0

    while True:
        b = ord(encoded[index]) - 63
        index += 1
        result |= (b & 0x1F) << shift
        shift  += 5
        if b < 0x20:          # no continuation bit → last chunk
            break

    # Undo the left-shift and sign trick
    if result & 1:
        result = ~result
    result >>= 1
    return result, index


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def encode_polyline(
    coordinates: List[Coord],
    precision: int = DEFAULT_PRECISION,
) -> str:
    """
    Encode a list of (lat, lng) tuples to a compact ASCII polyline string.

    Args:
        coordinates: Ordered list of waypoints as (latitude, longitude) tuples.
                     Minimum 2 points.
        precision:   Decimal places to retain (3, 4, or 5). Default 4.

    Returns:
        Compact ASCII string. All characters are in the printable range '?' .. '~'
        and are safe for SMS / Cell Broadcast transmission.

    Raises:
        ValueError: If precision is not in {3, 4, 5} or fewer than 2 coordinates.
    """
    if precision not in VALID_PRECISIONS:
        raise ValueError(f"Precision must be one of {list(VALID_PRECISIONS)}.")
    if len(coordinates) < 2:
        raise ValueError("At least 2 coordinate pairs are required.")

    scale    = VALID_PRECISIONS[precision]
    output   = []
    prev_lat = 0
    prev_lng = 0

    for lat, lng in coordinates:
        curr_lat = int(round(lat * scale))
        curr_lng = int(round(lng * scale))
        output.append(_encode_value(curr_lat - prev_lat))
        output.append(_encode_value(curr_lng - prev_lng))
        prev_lat = curr_lat
        prev_lng = curr_lng

    return "".join(output)


def decode_polyline(
    encoded: str,
    precision: int = DEFAULT_PRECISION,
) -> List[Coord]:
    """
    Decode a compact polyline string back to a list of (lat, lng) tuples.

    Args:
        encoded:   Polyline string produced by encode_polyline.
        precision: Must match the precision used during encoding. Default 4.

    Returns:
        List of (latitude, longitude) float tuples.

    Raises:
        ValueError: If precision is not in {3, 4, 5} or string is malformed.
    """
    if precision not in VALID_PRECISIONS:
        raise ValueError(f"Precision must be one of {list(VALID_PRECISIONS)}.")
    if not encoded:
        raise ValueError("Encoded polyline string is empty.")

    scale  = VALID_PRECISIONS[precision]
    coords = []
    index  = 0
    lat    = 0
    lng    = 0

    while index < len(encoded):
        delta_lat, index = _decode_value(encoded, index)
        delta_lng, index = _decode_value(encoded, index)
        lat += delta_lat
        lng += delta_lng
        coords.append((round(lat / scale, precision), round(lng / scale, precision)))

    return coords


def polyline_char_count(
    coordinates: List[Coord],
    precision: int = DEFAULT_PRECISION,
) -> dict:
    """
    Analyse the character count of an encoded polyline and produce a breakdown.

    Returns:
        dict with keys:
            polyline      — the encoded string
            total_chars   — total character count
            precision     — precision used
            n_waypoints   — number of waypoints
            breakdown     — list of per-waypoint encoding info
            payload_bytes — total payload size (hazard + role + polyline + checksum)
            sms_remaining — characters remaining in a 160-char SMS
    """
    encoded = encode_polyline(coordinates, precision)
    total   = len(encoded)
    # Full payload = 1 (hazard) + 1 (role) + total (polyline) + 1 (checksum) = total + 3
    payload_bytes = total + 3
    sms_remaining = 160 - payload_bytes

    return {
        "polyline":      encoded,
        "total_chars":   total,
        "precision":     precision,
        "n_waypoints":   len(coordinates),
        "payload_bytes": payload_bytes,
        "sms_remaining": sms_remaining,
        "sms_fits":      sms_remaining >= 0,
    }


def haversine_distance(coord1: Coord, coord2: Coord) -> float:
    """
    Calculate great-circle distance between two (lat, lng) points in kilometres.
    Used by route_optimizer to validate waypoint spacing.
    """
    import math
    lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
    lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(a))
