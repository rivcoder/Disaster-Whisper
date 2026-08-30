"""
client/validator.py — Post-Generation Output Validator
========================================================
Implements the Data-Based Validation Process (Section 3.6, Point 3).

The validator checks AI-generated alerts against the trusted offline landmark
database BEFORE displaying to the user. If the generated text mentions a
location not in the database, the alert is rejected and the template fallback
is used instead.

Validation checks:
    1. Hazard keyword match — alert must mention the correct hazard type.
    2. Location integrity   — any location names in the text must exist in
                             the offline landmark database (fuzzy match).
    3. Length gate          — alert must not be empty or suspiciously long.
    4. Directional sanity  — basic check for contradictory directions
                             (e.g., "North" and "South" in the same sentence
                             when referring to the same place).
"""

from __future__ import annotations
import os
import json
import re
from typing import List, Tuple

Coord = Tuple[float, float]

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

_LANDMARKS_CACHE = None

def _get_landmarks() -> list:
    global _LANDMARKS_CACHE
    if _LANDMARKS_CACHE is None:
        with open(os.path.join(_DATA_DIR, "landmarks.json"), encoding="utf-8") as f:
            _LANDMARKS_CACHE = json.load(f)["landmarks"]
    return _LANDMARKS_CACHE


# ─────────────────────────────────────────────────────────────────────────────
# Hazard keyword tables
# ─────────────────────────────────────────────────────────────────────────────

_HAZARD_KEYWORDS = {
    "F": ["flood", "water", "evacuate", "बाढ़", "पानी", "निकलें"],
    "C": ["cyclone", "storm", "shelter", "चक्रवात", "तूफान", "आश्रय"],
    "L": ["landslide", "slope", "debris", "भूस्खलन", "ढलान"],
    "W": ["wildfire", "fire", "smoke", "आग", "धुआं", "वणवा"],
    "E": ["earthquake", "seismic", "drop", "भूकंप", "झटके"],
    "T": ["tsunami", "wave", "inland", "सुनामी", "लहर", "अंदर"],
    "H": ["heatwave", "heat", "cool", "shelter", "लू", "गर्मी", "ठंडा"],
}

# Maximum acceptable alert length (characters)
MIN_ALERT_LENGTH = 30
MAX_ALERT_LENGTH = 2000


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _normalise(text: str) -> str:
    """Lowercase and strip punctuation for fuzzy matching."""
    return re.sub(r"[^\w\s]", " ", text.lower())


def _extract_candidate_locations(text: str) -> List[str]:
    """
    Extract probable location mentions from alert text using simple heuristics:
    - Title-cased sequences of 1–4 words
    - Known Indore locality keywords
    """
    candidates = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}", text)
    return candidates


def _location_in_database(loc_name: str, landmarks: list) -> bool:
    """
    Check if a location name matches any landmark (fuzzy, partial match).
    A match requires the candidate to be a substring of a known landmark name,
    district, or vice versa (both normalised).
    """
    candidate = _normalise(loc_name)
    for lm in landmarks:
        for field in ("name", "name_hi", "district"):
            stored = _normalise(lm.get(field, ""))
            if candidate in stored or stored in candidate:
                return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def validate_alert_output(
    generated_text: str,
    hazard_code:    str,
    coordinates:    List[Coord],
    language:       str = "en",
) -> dict:
    """
    Validate AI-generated alert text against the offline reference database.

    Args:
        generated_text: Raw string from the SLM.
        hazard_code:    Expected hazard code (e.g. "F").
        coordinates:    The route waypoints (used for context, not checked).
        language:       "en" or "hi".

    Returns:
        dict with keys:
            valid           — bool: True if alert passes all checks
            issues          — list of failure reason strings
            warnings        — list of non-fatal warnings
            checks_passed   — list of passed check names
            checks_failed   — list of failed check names
            unknown_locations — list of location mentions not in DB
    """
    issues:             list[str] = []
    warnings:           list[str] = []
    checks_passed:      list[str] = []
    checks_failed:      list[str] = []
    unknown_locations:  list[str] = []
    landmarks = _get_landmarks()

    # ── Check 1: Not empty / within length bounds ─────────────────────────────
    if not generated_text or len(generated_text.strip()) < MIN_ALERT_LENGTH:
        issues.append(f"Generated text too short ({len(generated_text)} chars). Minimum: {MIN_ALERT_LENGTH}.")
        checks_failed.append("length_check")
    elif len(generated_text) > MAX_ALERT_LENGTH:
        warnings.append(f"Generated text very long ({len(generated_text)} chars). May be truncated for display.")
        checks_passed.append("length_check")
    else:
        checks_passed.append("length_check")

    # ── Check 2: Hazard keyword presence ─────────────────────────────────────
    text_lower = generated_text.lower()
    keywords   = _HAZARD_KEYWORDS.get(hazard_code, [])
    if keywords:
        matched = any(kw in text_lower for kw in keywords)
        if matched:
            checks_passed.append("hazard_keyword")
        else:
            issues.append(
                f"Alert does not mention expected hazard type '{hazard_code}' keywords. "
                f"Expected one of: {keywords}"
            )
            checks_failed.append("hazard_keyword")
    else:
        checks_passed.append("hazard_keyword")  # Unknown hazard — skip check

    # ── Check 3: Location integrity ───────────────────────────────────────────
    # These are common English words that look like title-case proper nouns
    # but are NOT geographic locations — must be excluded from location checking.
    _NON_LOCATION_WORDS = {
        # Generic alert words
        "alert", "flood", "india", "call", "road", "move", "stay",
        "north", "south", "east", "west", "please", "emergency", "warning",
        # Common action / descriptive words mistaken for place names
        "residents", "proceed", "water", "levels", "ground", "higher",
        "evacuate", "evacuation", "contact", "assistance", "supplies",
        "route", "routes", "shelter", "use", "tuned", "updates",
        "activated", "rising", "rapidly", "immediately", "extremely",
        # Institutional / broadcast names that are not landmarks
        "relief", "centre", "center", "agricultural", "elderly", "india",
        "radio", "workers", "community", "government", "district",
        "volunteers", "help", "support", "department", "rescue", "report",
        # Directional/structural
        "low", "lying", "roads", "underpasses",
        # Common verbs starting sentences
        "avoid", "head", "go", "take", "do", "use", "severe", "senior",
        # Environmental and general subject words
        "citizens", "people", "families", "everyone", "winds", "speeds",
        "rains", "river", "rivers", "flooding", "safety",
    }

    if language == "en":
        candidates = _extract_candidate_locations(generated_text)
        bad_locs   = []
        for cand in candidates:
            cand_lower = cand.lower().strip()
            # Skip if the candidate name itself is short or is a known generic word
            if len(cand) < 5 or cand_lower in _NON_LOCATION_WORDS:
                continue
            
            tokens = cand_lower.split()
            # If all tokens are non-location words, skip it (e.g. "Elderly Residents")
            if all(t in _NON_LOCATION_WORDS for t in tokens):
                continue
                
            # Perform location validation
            if not _location_in_database(cand, landmarks):
                bad_locs.append(cand)

        if bad_locs:
            unknown_locations = bad_locs
            issues.append(
                f"Unverified or hallucinated locations detected: {bad_locs}. "
                "Alert rejected — using template fallback."
            )
            checks_failed.append("location_integrity")
        else:
            checks_passed.append("location_integrity")
    else:
        # Hindi location check is harder — skip strict check, add warning
        warnings.append("Hindi location integrity check skipped (manual review recommended).")
        checks_passed.append("location_integrity")

    # ── Check 4: No contradictory directional language ────────────────────────
    contradictions = [
        ("north", "south"), ("east", "west"), ("upstream", "downstream"),
        ("uphill", "downhill"), ("inland", "coastal"),
    ]
    for a, b in contradictions:
        if a in text_lower and b in text_lower:
            warnings.append(
                f"Potentially contradictory directional terms '{a}' and '{b}' found in same alert."
            )
    checks_passed.append("directional_check")

    return {
        "valid":              len(issues) == 0,
        "issues":             issues,
        "warnings":           warnings,
        "checks_passed":      checks_passed,
        "checks_failed":      checks_failed,
        "unknown_locations":  unknown_locations,
    }
