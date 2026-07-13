"""
codec/checksum.py — XOR Checksum
==================================
Implements the 8-bit error-checking code described in Section 3.2, Point 4.

Algorithm:
    checksum = XOR of all bytes in [Hazard_Code + Role_Flag + Polyline_Payload]

The checksum is encoded as a single printable ASCII character using the same
63-offset mapping as the polyline encoder, keeping it in the range '?' to '~'.
This ensures the full payload is SMS-safe (no control characters).

XOR checksum properties:
    - O(n) computation — negligible overhead on constrained devices
    - Detects all single-bit errors
    - Detects burst errors affecting an odd number of bits
    - Not a cryptographic hash — only provides integrity, not authentication
    - Suitable for unreliable low-bandwidth links where retransmission is unavailable
"""

from __future__ import annotations


def compute_checksum(data: str) -> str:
    """
    Compute XOR checksum over the string data and return as a single character.

    The result character is in ASCII range [63, 126] (printable, SMS-safe).

    Args:
        data: The string to checksum (Hazard_Code + Role_Flag + Polyline).

    Returns:
        Single ASCII character representing the 8-bit XOR checksum.
    """
    xor_val: int = 0
    for ch in data:
        xor_val ^= ord(ch)
    xor_val &= 0xFF  # keep to 8 bits

    # Map 0–255 to printable range: use modulo 64 then add 63
    printable = (xor_val % 64) + 63  # range: 63–126 → '?' to '~'
    return chr(printable)


def verify_checksum(payload: str) -> bool:
    """
    Verify the integrity of a complete payload string.

    The payload must be at least 3 characters:
        payload[:-1] → data portion
        payload[-1]  → checksum character

    Returns:
        True if checksum matches, False if payload is corrupted.
    """
    if len(payload) < 3:
        return False
    data     = payload[:-1]
    received = payload[-1]
    expected = compute_checksum(data)
    return received == expected


def xor_bytes(data: str) -> int:
    """
    Return the raw XOR integer value over all bytes in data (0–255).
    Useful for debugging / audit logs.
    """
    val = 0
    for ch in data:
        val ^= ord(ch)
    return val & 0xFF
