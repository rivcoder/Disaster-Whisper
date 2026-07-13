"""
client/clipboard_bridge.py — Pathway A: Clipboard-Based Payload Ingestion
==========================================================================
Implements Pathway A (Section 3.5):

    "When an emergency alert appears, the user copies the message text from
    the system notification. When they open the companion app, the app reads
    the copied text offline and extracts the coded data from it."

The bridge:
    1. Reads the current clipboard contents.
    2. Searches for the Disaster-Whisper payload pattern within the text.
    3. Extracts the payload prefix (first N characters) from the full message.
    4. Returns the extracted payload and any trailing plain-text suffix.

Payload pattern:
    - Character 0: one of {F, C, L, W, E, T, H}  (hazard code)
    - Character 1: one of {0-9, A-F}               (role flag hex)
    - Characters 2…n-2: printable ASCII '?' .. '~' (polyline)
    - Character n-1: printable ASCII '?' .. '~'    (checksum)
    - Followed by optional plain-text space + suffix

The bridge does NOT require internet access or any OS permission beyond
clipboard read, which is granted automatically to foreground apps on Android/iOS.
"""

from __future__ import annotations
import re

# Characters valid in a Disaster-Whisper payload (all printable ASCII from ? to ~)
_PAYLOAD_CHARS = re.compile(r"[?-~]+")

# Hazard codes
_HAZARD_CODES  = set("FCLWETH")

# Role flag characters (hex digits)
_ROLE_CHARS    = set("0123456789ABCDEF")

# Minimum payload length: 1 hazard + 1 role + 4 polyline (2 coords min) + 1 checksum = 7
MIN_PAYLOAD_LEN = 7
MAX_PAYLOAD_LEN = 40   # 1 + 1 + 37 (max polyline at 5-decimal, 10 waypoints) + 1


def _read_clipboard() -> str:
    """
    Read clipboard contents using the best available method for the platform.
    Returns empty string on failure.
    """
    # Method 1: pyperclip (cross-platform, recommended)
    try:
        import pyperclip
        text = pyperclip.paste()
        return text if text else ""
    except ImportError:
        pass
    except Exception:
        pass

    # Method 2: tkinter (standard library, works on Windows/Linux/macOS)
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        text = root.clipboard_get()
        root.destroy()
        return text if text else ""
    except Exception:
        pass

    # Method 3: Windows-specific win32clipboard
    try:
        import win32clipboard
        win32clipboard.OpenClipboard()
        text = win32clipboard.GetClipboardData()
        win32clipboard.CloseClipboard()
        return text if text else ""
    except Exception:
        pass

    return ""


def _extract_payload_from_text(text: str) -> dict:
    """
    Parse a message string and extract the Disaster-Whisper payload prefix.

    Returns:
        dict with keys:
            found       — bool
            payload     — extracted payload string (or "")
            suffix      — plain-text remainder after payload (or "")
            raw_text    — original input text
            reason      — explanation if not found
    """
    text = text.strip()

    if not text:
        return {"found": False, "payload": "", "suffix": "", "raw_text": text, "reason": "Empty clipboard."}

    # 1. Check for segmented/spaced payload (e.g., "F 3 yuzL{qhm@_HyJiDeNiFzBdNoI x Suffix")
    # This happens when copying from browser elements with whitespace between spans.
    words = text.split()
    if len(words) >= 4:
        # Check if they look like:
        # words[0]: 1 character hazard
        # words[1]: 1 character role hex
        # words[2]: polyline string
        # words[3]: 1 character checksum
        if len(words[0]) == 1 and len(words[1]) == 1 and len(words[3]) == 1:
            h_cand = words[0].upper()
            r_cand = words[1].upper()
            p_cand = words[2]
            c_cand = words[3]

            if (h_cand in _HAZARD_CODES and
                r_cand in _ROLE_CHARS and
                all('?' <= ch <= '~' for ch in p_cand) and
                '?' <= c_cand <= '~'):
                
                payload = h_cand + r_cand + p_cand + c_cand
                # Reconstruct human-readable suffix preserving spacing/layout of the rest
                # Find the location of words[3] (checksum) in the original string to get the suffix exactly
                checksum_idx = text.find(words[3])
                if checksum_idx != -1:
                    suffix = text[checksum_idx + 1:].strip()
                else:
                    suffix = " ".join(words[4:])

                return {
                    "found":    True,
                    "payload":  payload,
                    "suffix":   suffix,
                    "raw_text": text,
                    "reason":   "Payload successfully extracted (reconstructed from segmented text).",
                }

    # 2. Standard Contiguous Case: payload is the prefix of the first word (or entire string)
    # Check for valid hazard code at position 0
    if text[0].upper() not in _HAZARD_CODES:
        return {
            "found":    False,
            "payload":  "",
            "suffix":   text,
            "raw_text": text,
            "reason":   f"First character '{text[0]}' is not a valid hazard code {_HAZARD_CODES}.",
        }

    # Check for valid role flag at position 1
    if len(text) < 2 or text[1].upper() not in _ROLE_CHARS:
        return {
            "found":    False,
            "payload":  "",
            "suffix":   text,
            "raw_text": text,
            "reason":   f"Second character '{text[1] if len(text) > 1 else ''}' is not a valid role hex digit.",
        }

    # Find the end of the payload: scan printable '?'..'~' characters starting from index 2
    end = 2
    for i in range(2, len(text)):
        ch = text[i]
        if '?' <= ch <= '~':
            end = i + 1
        else:
            break   # first non-payload character (space, newline, etc.)

    if end < MIN_PAYLOAD_LEN:
        return {
            "found":    False,
            "payload":  "",
            "suffix":   text,
            "raw_text": text,
            "reason":   f"Payload section too short ({end} chars). Minimum: {MIN_PAYLOAD_LEN}.",
        }

    payload = text[:end]
    suffix  = text[end:].lstrip()

    return {
        "found":    True,
        "payload":  payload,
        "suffix":   suffix,
        "raw_text": text,
        "reason":   "Payload successfully extracted.",
    }


def read_payload_from_clipboard() -> dict:
    """
    Read the device clipboard and attempt to extract a Disaster-Whisper payload.

    Returns:
        dict with keys:
            found       — bool: True if a valid payload was found
            payload     — extracted payload string
            suffix      — plain-text suffix (human-readable part of SMS)
            raw_text    — full clipboard text (for audit)
            reason      — human-readable extraction status message
    """
    raw = _read_clipboard()
    return _extract_payload_from_text(raw)


def parse_sms_text(sms_text: str) -> dict:
    """
    Parse a raw SMS string (e.g. from UI paste input) for payload extraction.
    Same logic as read_payload_from_clipboard but operates on a provided string.
    """
    return _extract_payload_from_text(sms_text)
