"""
tests/test_codec.py — Codec Unit Tests
========================================
Tests for:
    - Hazard code encode/decode round-trips
    - Role flag encode/decode all 16 combinations
    - Polyline encode/decode round-trips at all precision levels
    - Checksum generation and corruption detection
    - Full payload assembly and parsing
    - Payload integrity check on corrupted data
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from codec.hazard    import encode_hazard, decode_hazard, VALID_CODES
from codec.role      import encode_role, decode_role, build_role_flags, role_description
from codec.polyline  import encode_polyline, decode_polyline, polyline_char_count
from codec.checksum  import compute_checksum, verify_checksum, xor_bytes
from codec.payload   import encode_payload, decode_payload, payload_breakdown


# ─────────────────────────────────────────────────────────────────────────────
# Reference test route (Indore evacuation route from the paper)
# ─────────────────────────────────────────────────────────────────────────────
INDORE_ROUTE = [
    (22.7181, 75.8574),   # Rajwada Palace
    (22.7325, 75.8763),   # LIG Square
    (22.7410, 75.9006),   # Geeta Bhawan
    (22.7527, 75.8944),   # Vijay Nagar Square
    (22.7284, 75.9112),   # Scheme 54
]


# ─────────────────────────────────────────────────────────────────────────────
# Hazard codec tests
# ─────────────────────────────────────────────────────────────────────────────

class TestHazardCodec:

    def test_encode_by_code(self):
        assert encode_hazard("F") == "F"
        assert encode_hazard("C") == "C"
        assert encode_hazard("f") == "F"  # case insensitive

    def test_encode_by_full_name(self):
        assert encode_hazard("Flood")     == "F"
        assert encode_hazard("Cyclone")   == "C"
        assert encode_hazard("Landslide") == "L"
        assert encode_hazard("Wildfire")  == "W"
        assert encode_hazard("Earthquake")== "E"
        assert encode_hazard("Tsunami")   == "T"
        assert encode_hazard("Heatwave")  == "H"

    def test_encode_invalid(self):
        with pytest.raises(ValueError):
            encode_hazard("X")
        with pytest.raises(ValueError):
            encode_hazard("Tornado")

    def test_decode_all_codes(self):
        for code in VALID_CODES:
            result = decode_hazard(code)
            assert result["code"]     == code
            assert "name"             in result
            assert "severity"         in result
            assert "default_action"   in result
            assert result["severity"] in ("MODERATE", "HIGH", "EXTREME")

    def test_decode_invalid(self):
        with pytest.raises(ValueError):
            decode_hazard("X")

    def test_round_trip(self):
        for code in VALID_CODES:
            decoded = decode_hazard(encode_hazard(code))
            assert decoded["code"] == code


# ─────────────────────────────────────────────────────────────────────────────
# Role flag tests
# ─────────────────────────────────────────────────────────────────────────────

class TestRoleCodec:

    def test_encode_all_values(self):
        for i in range(16):
            char = encode_role(i)
            assert len(char) == 1
            assert char in "0123456789ABCDEF"

    def test_decode_general_public(self):
        result = decode_role("0")
        assert result["is_general"] == True
        assert result["all_groups"] == False
        assert result["active_roles"][0]["key"] == "general"

    def test_decode_all_groups(self):
        result = decode_role("F")
        assert result["all_groups"] == True
        assert len(result["active_roles"]) == 4

    def test_decode_agricultural(self):
        result = decode_role("1")
        assert any(r["key"] == "agricultural" for r in result["active_roles"])

    def test_decode_elderly(self):
        result = decode_role("2")
        assert any(r["key"] == "elderly" for r in result["active_roles"])

    def test_decode_combination(self):
        # Agricultural (0x1) + Elderly (0x2) = 0x3 = '3'
        result = decode_role("3")
        keys = [r["key"] for r in result["active_roles"]]
        assert "agricultural" in keys
        assert "elderly"      in keys

    def test_build_role_flags(self):
        assert build_role_flags(agricultural=True)              == 0x1
        assert build_role_flags(elderly=True)                   == 0x2
        assert build_role_flags(agricultural=True, elderly=True)== 0x3
        assert build_role_flags(volunteers=True)                == 0x8
        assert build_role_flags(
            agricultural=True, elderly=True,
            physically_challenged=True, volunteers=True
        ) == 0xF

    def test_round_trip_all_values(self):
        for i in range(16):
            char   = encode_role(i)
            result = decode_role(char)
            assert result["value"] == i

    def test_encode_invalid(self):
        with pytest.raises(ValueError):
            encode_role(16)
        with pytest.raises(ValueError):
            encode_role(-1)

    def test_role_description(self):
        desc = role_description(0x3)
        assert "Agricultural" in desc or "Elderly" in desc


# ─────────────────────────────────────────────────────────────────────────────
# Polyline tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPolylineCodec:

    def test_encode_decode_round_trip_4decimal(self):
        encoded  = encode_polyline(INDORE_ROUTE, precision=4)
        decoded  = decode_polyline(encoded, precision=4)
        assert len(decoded) == len(INDORE_ROUTE)
        for orig, dec in zip(INDORE_ROUTE, decoded):
            assert abs(orig[0] - dec[0]) < 0.0001   # within 4-decimal precision
            assert abs(orig[1] - dec[1]) < 0.0001

    def test_encode_decode_round_trip_3decimal(self):
        encoded = encode_polyline(INDORE_ROUTE, precision=3)
        decoded = decode_polyline(encoded, precision=3)
        for orig, dec in zip(INDORE_ROUTE, decoded):
            assert abs(orig[0] - dec[0]) < 0.001
            assert abs(orig[1] - dec[1]) < 0.001

    def test_encode_decode_round_trip_5decimal(self):
        encoded = encode_polyline(INDORE_ROUTE, precision=5)
        decoded = decode_polyline(encoded, precision=5)
        for orig, dec in zip(INDORE_ROUTE, decoded):
            assert abs(orig[0] - dec[0]) < 0.00001
            assert abs(orig[1] - dec[1]) < 0.00001

    def test_precision_ordering(self):
        """4-decimal encoding should be shorter than 5-decimal for same route."""
        enc3 = encode_polyline(INDORE_ROUTE, precision=3)
        enc4 = encode_polyline(INDORE_ROUTE, precision=4)
        enc5 = encode_polyline(INDORE_ROUTE, precision=5)
        assert len(enc3) <= len(enc4) <= len(enc5)

    def test_output_characters_printable(self):
        """All encoded characters must be in printable ASCII range '?' to '~'."""
        encoded = encode_polyline(INDORE_ROUTE, precision=4)
        for ch in encoded:
            assert '?' <= ch <= '~', f"Non-printable char '{ch}' (ord={ord(ch)}) in polyline."

    def test_sms_fits(self):
        """Full payload for reference route must fit in 160-char SMS."""
        stats = polyline_char_count(INDORE_ROUTE, precision=4)
        assert stats["sms_fits"], (
            f"Payload too large: {stats['payload_bytes']} bytes > 160. "
            f"Polyline: '{stats['polyline']}'"
        )

    def test_invalid_precision(self):
        with pytest.raises(ValueError):
            encode_polyline(INDORE_ROUTE, precision=6)

    def test_single_point_raises(self):
        with pytest.raises(ValueError):
            encode_polyline([(22.7181, 75.8574)])

    def test_negative_coordinates(self):
        """Test with southern hemisphere coordinates (negative lat)."""
        route = [(-33.8688, 151.2093), (-33.8750, 151.2100)]   # Sydney area
        encoded = encode_polyline(route, precision=4)
        decoded = decode_polyline(encoded, precision=4)
        for orig, dec in zip(route, decoded):
            assert abs(orig[0] - dec[0]) < 0.0001
            assert abs(orig[1] - dec[1]) < 0.0001


# ─────────────────────────────────────────────────────────────────────────────
# Checksum tests
# ─────────────────────────────────────────────────────────────────────────────

class TestChecksum:

    def test_compute_and_verify(self):
        data    = "F3" + encode_polyline(INDORE_ROUTE)
        cs      = compute_checksum(data)
        assert len(cs) == 1
        assert verify_checksum(data + cs)

    def test_detect_single_bit_corruption(self):
        data    = "F3" + encode_polyline(INDORE_ROUTE)
        cs      = compute_checksum(data)
        payload = data + cs
        # Flip one byte
        corrupted = payload[:5] + chr(ord(payload[5]) ^ 0x01) + payload[6:]
        assert not verify_checksum(corrupted)

    def test_detect_role_corruption(self):
        data    = "F3" + encode_polyline(INDORE_ROUTE)
        cs      = compute_checksum(data)
        payload = data + cs
        # Change role flag from '3' to '4'
        corrupted = payload[0] + "4" + payload[2:]
        assert not verify_checksum(corrupted)

    def test_checksum_character_printable(self):
        data = "F3" + encode_polyline(INDORE_ROUTE)
        cs   = compute_checksum(data)
        assert '?' <= cs <= '~', f"Checksum char '{cs}' not printable."

    def test_empty_payload_fails_verify(self):
        assert not verify_checksum("")
        assert not verify_checksum("AB")


# ─────────────────────────────────────────────────────────────────────────────
# Full payload tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPayload:

    def test_encode_decode_round_trip(self):
        payload = encode_payload("F", 0x3, INDORE_ROUTE, precision=4)
        result  = decode_payload(payload, precision=4)

        assert result["hazard"]["code"]         == "F"
        assert result["role"]["value"]          == 0x3
        assert result["checksum_ok"]            == True
        assert len(result["coordinates"])       == len(INDORE_ROUTE)

    def test_payload_sms_fits(self):
        payload = encode_payload("F", 0x3, INDORE_ROUTE, precision=4)
        assert len(payload) <= 160, f"Payload '{payload}' is {len(payload)} chars > 160."

    def test_payload_all_printable(self):
        payload = encode_payload("C", 0xF, INDORE_ROUTE, precision=4)
        for ch in payload:
            assert ch.isprintable(), f"Non-printable char '{ch}' in payload."

    def test_payload_checksum_integrity(self):
        payload   = encode_payload("F", 0x3, INDORE_ROUTE)
        result    = decode_payload(payload)
        assert result["checksum_ok"] == True

    def test_corrupted_payload_detected(self):
        payload   = encode_payload("F", 0x3, INDORE_ROUTE)
        corrupted = payload[:-1] + chr(ord(payload[-1]) ^ 0x01)
        result    = decode_payload(corrupted)
        assert result["checksum_ok"] == False

    def test_all_hazard_codes_produce_valid_payload(self):
        for code in VALID_CODES:
            payload = encode_payload(code, 0x0, INDORE_ROUTE)
            result  = decode_payload(payload)
            assert result["hazard"]["code"] == code
            assert result["checksum_ok"]    == True

    def test_all_role_flags_produce_valid_payload(self):
        for flags in range(16):
            payload = encode_payload("F", flags, INDORE_ROUTE)
            result  = decode_payload(payload)
            assert result["role"]["value"] == flags
            assert result["checksum_ok"]   == True

    def test_breakdown_structure(self):
        bd = payload_breakdown("F", 0x3, INDORE_ROUTE)
        assert "hazard_code"  in bd
        assert "role_flag"    in bd
        assert "polyline"     in bd
        assert "checksum"     in bd
        assert "full_payload" in bd
        assert "sms_remaining" in bd
        # Total bytes = 1 (hazard) + 1 (role) + polyline_len + 1 (checksum)
        expected = 3 + bd["polyline"]["bytes"]
        assert bd["total_bytes"] == expected

    def test_precision_3_vs_4_vs_5_payload_sizes(self):
        p3 = encode_payload("F", 0x0, INDORE_ROUTE, precision=3)
        p4 = encode_payload("F", 0x0, INDORE_ROUTE, precision=4)
        p5 = encode_payload("F", 0x0, INDORE_ROUTE, precision=5)
        assert len(p3) <= len(p4) <= len(p5), (
            f"Expected p3({len(p3)}) ≤ p4({len(p4)}) ≤ p5({len(p5)})"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
