"""
Disaster-Whisper Codec Package
===============================
Implements the compact 4-part payload format described in Section 3.2:

    Payload = [Hazard_Code][Role_Flag][Polyline_Payload][Checksum]

Modules:
    hazard   — Single-character disaster type codes
    role     — 4-bit audience bitmask encoder/decoder
    polyline — Delta + variable-length + Google-style polyline codec
    checksum — XOR-based integrity verification
    payload  — Full payload assembler and parser

Usage:
    from codec.payload import encode_payload, decode_payload
"""

from codec.payload import encode_payload, decode_payload
from codec.hazard  import encode_hazard, decode_hazard
from codec.role    import encode_role, decode_role, build_role_flags
from codec.polyline import encode_polyline, decode_polyline, polyline_char_count
from codec.checksum import compute_checksum, verify_checksum

__all__ = [
    "encode_payload", "decode_payload",
    "encode_hazard",  "decode_hazard",
    "encode_role",    "decode_role",    "build_role_flags",
    "encode_polyline","decode_polyline","polyline_char_count",
    "compute_checksum","verify_checksum",
]
