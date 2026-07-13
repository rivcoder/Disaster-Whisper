"""
tests/test_server.py — Server-Side Unit Tests
===============================================
Tests for:
    - Route validation (bounds, min/max waypoints, step distances)
    - RDP route simplification
    - Alert generation (payload correctness)
    - Audit record structure
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from server.route_optimizer import validate_waypoints, optimize_route, route_summary
from server.alert_generator import generate_alert, generate_alert_with_audit
from codec.payload import decode_payload


INDORE_ROUTE = [
    (22.7181, 75.8574),
    (22.7325, 75.8763),
    (22.7410, 75.9006),
    (22.7527, 75.8944),
    (22.7284, 75.9112),
]


class TestRouteValidator:

    def test_valid_route(self):
        result = validate_waypoints(INDORE_ROUTE)
        assert result["valid"] == True
        assert len(result["errors"]) == 0

    def test_single_point_invalid(self):
        result = validate_waypoints([(22.7181, 75.8574)])
        assert result["valid"] == False
        assert any("2" in e for e in result["errors"])   # needs at least 2

    def test_out_of_india_bounds(self):
        bad_route = [(91.0, 75.8574), (22.7325, 75.8763)]   # lat > 38
        result    = validate_waypoints(bad_route)
        assert result["valid"] == False

    def test_distance_computed(self):
        result = validate_waypoints(INDORE_ROUTE)
        assert len(result["distances"]) == len(INDORE_ROUTE) - 1
        for d in result["distances"]:
            assert d > 0

    def test_duplicate_points_warning(self):
        duped = [INDORE_ROUTE[0], INDORE_ROUTE[0], INDORE_ROUTE[1]]
        result = validate_waypoints(duped)
        # Duplicates produce a warning about 0m distance
        assert len(result["warnings"]) > 0 or not result["valid"]

    def test_too_far_apart(self):
        # Points 500 km apart — exceeds limit
        far_route = [(22.7181, 75.8574), (28.6139, 77.2090)]  # Indore→Delhi
        result    = validate_waypoints(far_route)
        # Should produce error(s) about exceeding max step
        assert not result["valid"] or len(result["errors"]) > 0


class TestRouteOptimizer:

    def test_optimize_preserves_start_end(self):
        # Make a dense route with extra interpolated points
        dense = [
            (22.7181 + i * 0.001, 75.8574 + i * 0.001)
            for i in range(15)
        ]
        optimised = optimize_route(dense, target_waypoints=5)
        assert optimised[0]  == dense[0]
        assert optimised[-1] == dense[-1]

    def test_optimize_reduces_points(self):
        dense = [(22.7181 + i * 0.001, 75.8574 + i * 0.001) for i in range(12)]
        optimised = optimize_route(dense, target_waypoints=5)
        assert len(optimised) <= len(dense)
        assert len(optimised) >= 2

    def test_optimize_short_route_unchanged(self):
        short = INDORE_ROUTE[:3]
        optimised = optimize_route(short, target_waypoints=5)
        assert len(optimised) >= 2

    def test_route_summary_structure(self):
        summary = route_summary(INDORE_ROUTE)
        assert "n_waypoints"       in summary
        assert "total_km"          in summary
        assert "start"             in summary
        assert "end"               in summary
        assert summary["n_waypoints"] == len(INDORE_ROUTE)
        assert summary["total_km"]    > 0


class TestAlertGenerator:

    def test_generate_alert_returns_string(self):
        payload = generate_alert("F", 0x3, INDORE_ROUTE)
        assert isinstance(payload, str)
        assert len(payload) > 4

    def test_generated_payload_is_valid(self):
        payload = generate_alert("F", 0x3, INDORE_ROUTE)
        result  = decode_payload(payload)
        assert result["checksum_ok"]    == True
        assert result["hazard"]["code"] == "F"
        assert result["role"]["value"]  == 0x3

    def test_generate_all_hazards(self):
        for code in "FCLWETH":
            payload = generate_alert(code, 0x0, INDORE_ROUTE)
            result  = decode_payload(payload)
            assert result["hazard"]["code"] == code

    def test_generate_invalid_route_raises(self):
        with pytest.raises(ValueError):
            generate_alert("F", 0x0, [(22.7181, 75.8574)])  # single point

    def test_audit_record_structure(self):
        audit = generate_alert_with_audit(
            hazard="F",
            role_flags=0x3,
            coordinates=INDORE_ROUTE,
            plain_text_suffix=" Flood Alert Indore. Please evacuate.",
        )
        assert "payload"         in audit
        assert "full_sms"        in audit
        assert "breakdown"       in audit
        assert "route_summary"   in audit
        assert "sms_budget"      in audit
        assert "audit_timestamp" in audit

        bd = audit["breakdown"]
        assert "hazard_code" in bd
        assert "role_flag"   in bd
        assert "polyline"    in bd
        assert "checksum"    in bd

    def test_sms_budget_accuracy(self):
        suffix = " Flood Alert Indore."
        audit  = generate_alert_with_audit("F", 0x0, INDORE_ROUTE, plain_text_suffix=suffix)
        budget = audit["sms_budget"]
        assert budget["total_chars"] == len(audit["full_sms"])
        assert budget["limit"]       == 160
        assert budget["remaining"]   == 160 - budget["total_chars"]

    def test_payload_fits_sms(self):
        audit  = generate_alert_with_audit("F", 0x0, INDORE_ROUTE)
        budget = audit["sms_budget"]
        assert budget["payload_chars"] <= 160


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
