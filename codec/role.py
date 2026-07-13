"""
codec/role.py — Role Flag Encoder/Decoder
==========================================
Implements the 4-bit audience bitmask described in Section 3.2, Point 2.

The 4 bits are encoded into a single hex ASCII character ('0'–'F'),
making the Role Flag exactly 1 byte in the payload.

Bit assignments:
    Bit 0  (0x1): Agricultural Workers
    Bit 1  (0x2): Elderly Populations
    Bit 2  (0x4): Physically Challenged Individuals
    Bit 3  (0x8): Local Volunteer Responders

Special values:
    0x0  = General Public (no specific group)
    0xF  = All groups simultaneously

Example:
    Agricultural + Elderly → 0x1 | 0x2 = 0x3 → '3'
    All groups             → 0xF        → 'F'
"""

from __future__ import annotations

# Map bit position → audience label
ROLE_BITS: dict[int, dict] = {
    0: {
        "key":     "agricultural",
        "label":   "Agricultural Workers",
        "label_hi": "कृषि कर्मी",
        "bit":     0x1,
    },
    1: {
        "key":     "elderly",
        "label":   "Elderly Populations",
        "label_hi": "वरिष्ठ नागरिक",
        "bit":     0x2,
    },
    2: {
        "key":     "physically_challenged",
        "label":   "Physically Challenged Individuals",
        "label_hi": "दिव्यांग व्यक्ति",
        "bit":     0x4,
    },
    3: {
        "key":     "volunteers",
        "label":   "Local Volunteer Responders",
        "label_hi": "स्थानीय स्वयंसेवी दल",
        "bit":     0x8,
    },
}

GENERAL_PUBLIC = 0x0
ALL_GROUPS     = 0xF

# Build lookup: key → bit
_KEY_TO_BIT: dict[str, int] = {
    meta["key"]: meta["bit"] for meta in ROLE_BITS.values()
}


def encode_role(flags: int) -> str:
    """
    Encode a 4-bit integer (0x0–0xF) to a single uppercase hex character.

    Args:
        flags: Integer in range [0, 15].

    Returns:
        Single character from '0'–'9', 'A'–'F'.

    Raises:
        ValueError: If flags is outside [0, 15].
    """
    if not 0 <= flags <= 0xF:
        raise ValueError(f"Role flag must be in [0, 15], got {flags}.")
    return format(flags, "X")  # e.g. 3 → '3', 15 → 'F'


def decode_role(char: str) -> dict:
    """
    Decode a single hex character to full role metadata.

    Returns:
        dict with keys:
            value       — integer flag value
            char        — the encoded character
            active_roles — list of active audience group labels (EN + HI)
            is_general  — True if General Public (0x0)
            all_groups  — True if all groups (0xF)
    """
    char = char.strip().upper()
    if char not in "0123456789ABCDEF":
        raise ValueError(f"Invalid role character: '{char}'. Expected hex digit.")

    flags = int(char, 16)
    active: list[dict] = []
    for pos, meta in ROLE_BITS.items():
        if flags & meta["bit"]:
            active.append({
                "key":      meta["key"],
                "label":    meta["label"],
                "label_hi": meta["label_hi"],
            })

    return {
        "value":        flags,
        "char":         char,
        "active_roles": active if active else [
            {"key": "general", "label": "General Public", "label_hi": "आम जनता"}
        ],
        "is_general":   flags == GENERAL_PUBLIC,
        "all_groups":   flags == ALL_GROUPS,
    }


def build_role_flags(**kwargs: bool) -> int:
    """
    Build a role flags integer from keyword boolean arguments.

    Keyword Args:
        agricultural        (bool): Include agricultural workers.
        elderly             (bool): Include elderly populations.
        physically_challenged (bool): Include physically challenged.
        volunteers          (bool): Include volunteer responders.

    Returns:
        Integer in [0, 15].

    Example:
        build_role_flags(agricultural=True, elderly=True) → 3
    """
    flags = 0
    for key, val in kwargs.items():
        if key not in _KEY_TO_BIT:
            raise ValueError(
                f"Unknown role key: '{key}'. "
                f"Valid keys: {list(_KEY_TO_BIT.keys())}"
            )
        if val:
            flags |= _KEY_TO_BIT[key]
    return flags


def role_description(flags: int, language: str = "en") -> str:
    """Return a human-readable comma-separated string of active roles."""
    decoded = decode_role(encode_role(flags))
    key = "label_hi" if language == "hi" else "label"
    return ", ".join(r[key] for r in decoded["active_roles"])
