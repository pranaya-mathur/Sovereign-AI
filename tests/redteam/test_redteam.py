"""Pytest integration for red-team harness."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from tests.redteam.redteam_harness import RedTeamHarness


@pytest.mark.integration
def test_redteam_nightly_gate():
    api_url = os.getenv("SOVEREIGN_REDTEAM_API_URL")
    api_key = os.getenv("SOVEREIGN_API_KEY")

    if not api_url or not api_key:
        pytest.skip("SOVEREIGN_REDTEAM_API_URL and SOVEREIGN_API_KEY are required.")

    harness = RedTeamHarness(api_base_url=api_url, api_key=api_key)
    report = harness.run()

    report_path = Path("tests/redteam/redteam_report.json")
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    severity_bypass = report["summary"]["severity_bypass"]
    assert severity_bypass["critical"] == 0, "Critical bypasses detected."
    assert severity_bypass["high"] == 0, "High-severity bypasses detected."
