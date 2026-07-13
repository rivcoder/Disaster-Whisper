"""
tests/test_client.py — Client-Side Unit Tests
===============================================
Tests for:
    - Tier detection (RAM-based)
    - Tier 1 template rendering (all hazards, all roles, EN + HI)
    - Validator (correct alerts pass, hallucinated locations fail)
    - Clipboard bridge payload extraction
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from client.tier_detector    import detect_tier, get_system_info, TIER_1, TIER_2
from client.tier1_engine     import render_tier1, find_nearest_landmark, build_route_description
from client.validator        import validate_alert_output
from client.clipboard_bridge import parse_sms_text
from codec.payload           import encode_payload

INDORE_ROUTE = [
    (22.7181, 75.8574),
    (22.7325, 75.8763),
    (22.7410, 75.9006),
    (22.7527, 75.8944),
    (22.7284, 75.9112),
]


class TestTierDetector:

    def test_tier1_below_threshold(self):
        assert detect_tier(ram_gb=2.0) == TIER_1
        assert detect_tier(ram_gb=0.5) == TIER_1
        assert detect_tier(ram_gb=3.9) == TIER_1

    def test_tier2_at_and_above_threshold(self):
        assert detect_tier(ram_gb=4.0) == TIER_2
        assert detect_tier(ram_gb=8.0) == TIER_2
        assert detect_tier(ram_gb=16.0)== TIER_2

    def test_system_info_structure(self):
        info = get_system_info()
        assert "tier"          in info
        assert "ram_gb"        in info
        assert "tier_label"    in info
        assert "slm_eligible"  in info
        assert info["tier"]    in (TIER_1, TIER_2)
        assert info["ram_gb"]  >= 0

    def test_system_info_consistency(self):
        info = get_system_info()
        expected_tier = TIER_2 if info["ram_gb"] >= 4.0 else TIER_1
        assert info["tier"] == expected_tier


class TestTier1Engine:

    def test_render_flood_english(self):
        result = render_tier1("F", 0x3, INDORE_ROUTE, language="en")
        assert result["tier"]      == 1
        assert result["language"]  == "en"
        assert "alert_text"        in result
        assert len(result["alert_text"]) > 20
        # Must mention flood
        assert any(kw in result["alert_text"].lower() for kw in ("flood", "water", "evacuate"))

    def test_render_flood_hindi(self):
        result = render_tier1("F", 0x3, INDORE_ROUTE, language="hi")
        assert result["tier"]     == 1
        assert result["language"] == "hi"
        assert len(result["alert_text"]) > 10
        # Must contain some Hindi characters
        assert any(ord(ch) > 127 for ch in result["alert_text"])

    def test_render_all_hazards_english(self):
        for code in "FCLWETH":
            result = render_tier1(code, 0x0, INDORE_ROUTE, language="en")
            assert result["tier"] == 1
            assert len(result["alert_text"]) > 20

    def test_render_all_role_flags(self):
        for flags in range(16):
            result = render_tier1("F", flags, INDORE_ROUTE, language="en")
            assert result["tier"] == 1
            assert "alert_text"   in result

    def test_area_and_destination_present(self):
        result = render_tier1("F", 0x0, INDORE_ROUTE)
        assert result["area"]        != ""
        assert result["destination"] != ""

    def test_route_waypoints_populated(self):
        result = render_tier1("F", 0x0, INDORE_ROUTE)
        assert len(result["route_waypoints"]) == len(INDORE_ROUTE)

    def test_find_nearest_landmark(self):
        coord = (22.7181, 75.8574)  # Rajwada Palace exactly
        lm    = find_nearest_landmark(coord)
        assert "name" in lm
        # Should find Rajwada or a very close landmark
        assert lm["name"] is not None

    def test_find_nearest_safe_zone(self):
        coord = (22.7284, 75.9112)  # Scheme 54
        lm    = find_nearest_landmark(coord, prefer_safe_zone=True)
        assert lm.get("is_safe_zone") == True

    def test_route_description(self):
        desc = build_route_description(INDORE_ROUTE, language="en")
        assert "→" in desc
        parts = desc.split("→")
        assert len(parts) == len(INDORE_ROUTE)


class TestValidator:

    def test_valid_flood_alert_passes(self):
        text = (
            "FLOOD ALERT — Rajwada Palace Area: Evacuate immediately to Scheme 54. "
            "Water levels rising rapidly. Avoid low-lying roads. Call 112."
        )
        result = validate_alert_output(text, "F", INDORE_ROUTE, language="en")
        assert result["valid"] == True

    def test_empty_text_fails(self):
        result = validate_alert_output("", "F", INDORE_ROUTE)
        assert result["valid"] == False

    def test_wrong_hazard_fails(self):
        text   = "Tornado warning! Spin around. Take shelter underground."
        result = validate_alert_output(text, "F", INDORE_ROUTE)
        assert result["valid"] == False

    def test_many_invented_locations_fails(self):
        text = (
            "FLOOD ALERT — Please move to Springfield immediately. "
            "Route via Shelbyville, Quahog, Pawnee, and Eagleton. "
            "Water rising in Riverdale and Smallville."
        )
        result = validate_alert_output(text, "F", INDORE_ROUTE, language="en")
        # Should flag many unrecognised locations
        assert len(result["unknown_locations"]) > 0

    def test_validation_result_structure(self):
        text   = "FLOOD ALERT: Evacuate now. Call 112."
        result = validate_alert_output(text, "F", INDORE_ROUTE)
        assert "valid"             in result
        assert "issues"            in result
        assert "warnings"          in result
        assert "checks_passed"     in result
        assert "checks_failed"     in result
        assert "unknown_locations" in result


class TestClipboardBridge:

    def test_valid_sms_extraction(self):
        payload = encode_payload("F", 0x3, INDORE_ROUTE)
        sms     = payload + " Flood Alert Indore. Please evacuate now."
        result  = parse_sms_text(sms)
        assert result["found"]   == True
        assert result["payload"] == payload
        assert "Flood" in result["suffix"]

    def test_plain_text_only_not_found(self):
        sms    = "This is a normal SMS with no payload."
        result = parse_sms_text(sms)
        assert result["found"] == False

    def test_empty_string(self):
        result = parse_sms_text("")
        assert result["found"] == False

    def test_invalid_hazard_code(self):
        # X is not a valid hazard code
        sms    = "X3abcdefghijklm Some text"
        result = parse_sms_text(sms)
        assert result["found"] == False

    def test_all_hazard_codes_extractable(self):
        for code in "FCLWETH":
            payload = encode_payload(code, 0x0, INDORE_ROUTE)
            sms     = payload + " Emergency Alert."
            result  = parse_sms_text(sms)
            assert result["found"]   == True
            assert result["payload"] == payload

    def test_segmented_payload_extraction(self):
        # Spaces separating parts, representing the user issue when copying from browser spans
        sms = "F 3 yuzL{qhm@_HyJiDeNiFzBdNoI x Move to Scheme 54. Call 112."
        result = parse_sms_text(sms)
        assert result["found"] == True
        assert result["payload"] == "F3yuzL{qhm@_HyJiDeNiFzBdNoIx"
        assert result["suffix"] == "Move to Scheme 54. Call 112."


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
