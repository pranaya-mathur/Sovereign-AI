"""Tests for India-focused PII redaction helpers."""

from rules.pii_india import detect_india_pii, redact_india_pii


def test_pan_detection():
    text = "My PAN is ABCDE1234F for KYC."
    m = detect_india_pii(text)
    types = {x.entity_type for x in m}
    assert "IN_PAN" in types


def test_phone_detection():
    text = "Call me at +91 9876543210 tomorrow."
    m = detect_india_pii(text)
    assert any(x.entity_type == "PHONE_IN" for x in m)


def test_redact_structure():
    text = "Email user@example.com and GST 22AAAAA0000A1Z5 here."
    out = redact_india_pii(text)
    assert "redacted_text" in out
    assert "aggregate_score" in out
    assert out["redacted_text"] != text or out["aggregate_score"] == 0.0


def test_aadhaar_like_grouping():
    text = "Aadhaar 1234 5678 9012 (sample formatting)."
    m = detect_india_pii(text)
    assert any(x.entity_type == "IN_AADHAAR" for x in m)
