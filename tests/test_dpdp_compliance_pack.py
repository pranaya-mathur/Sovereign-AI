"""Tests for DPDP compliance pack behavior."""

from rules.compliance_packs.india_dpdp import DPDPChecker


def test_dpdp_checker_uses_entity_type_for_detected_field():
    checker = DPDPChecker()
    text = "Customer PAN is ABCDE1234F and phone is +91 9876543210."

    violations = checker.check_response_compliance(text)

    assert violations, "Expected at least one DPDP violation for PAN/phone payload."
    assert all("detected" in v for v in violations)
    assert any(v["detected"] == "IN_PAN" for v in violations)
