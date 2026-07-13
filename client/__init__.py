"""
Disaster-Whisper Client Package
=================================
Client-side processing pipeline described in Sections 3.4 and 3.5.

Device tier detection → Pathway A/B ingestion → Tier 1 or Tier 2 rendering → Validation

Modules:
    tier_detector    — RAM-based hardware capability classification
    tier1_engine     — Template-based deterministic alert renderer (Tier 1)
    tier2_engine     — SLM-based personalised alert generator (Tier 2)
    validator        — Post-generation output validation against offline DB
    clipboard_bridge — Pathway A: extract payload from clipboard (OS-agnostic)
"""

from client.tier_detector   import detect_tier, get_system_info
from client.tier1_engine    import render_tier1
from client.tier2_engine    import render_tier2, is_model_available
from client.validator       import validate_alert_output
from client.clipboard_bridge import read_payload_from_clipboard

__all__ = [
    "detect_tier",
    "get_system_info",
    "render_tier1",
    "render_tier2",
    "is_model_available",
    "validate_alert_output",
    "read_payload_from_clipboard",
]
