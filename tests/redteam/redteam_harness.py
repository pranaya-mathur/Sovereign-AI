"""Automated red-team harness for Sovereign-AI /api/detect."""

from __future__ import annotations

import json
import os
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx


@dataclass
class RedTeamResult:
    case_id: str
    category: str
    severity: str
    expected_action: str
    actual_action: str
    blocked: bool
    tier_used: int | None
    latency_ms: float
    bypassed: bool
    response: dict[str, Any]


class RedTeamHarness:
    def __init__(
        self,
        api_base_url: str,
        api_key: str,
        dataset_path: Path | None = None,
        timeout_seconds: float = 20.0,
    ):
        self.api_base_url = api_base_url.rstrip("/")
        self.api_key = api_key
        self.dataset_path = dataset_path or Path(__file__).parent / "adversarial_dataset.json"
        self.timeout_seconds = timeout_seconds

    def load_dataset(self) -> list[dict[str, Any]]:
        with self.dataset_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        if not isinstance(payload, list):
            raise ValueError("Dataset must be a JSON list.")
        return payload

    def _call_detect(self, text: str, context: dict[str, Any]) -> tuple[dict[str, Any], float]:
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
        }
        body = {"text": text, "context": context}
        start = time.perf_counter()
        with httpx.Client(timeout=self.timeout_seconds) as client:
            resp = client.post(f"{self.api_base_url}/api/detect", headers=headers, json=body)
        latency_ms = (time.perf_counter() - start) * 1000
        resp.raise_for_status()
        return resp.json(), latency_ms

    def run(self) -> dict[str, Any]:
        dataset = self.load_dataset()
        results: list[RedTeamResult] = []
        tier_counts: dict[str, int] = {"1": 0, "2": 0, "3": 0, "unknown": 0}
        severity_bypass: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        latencies: list[float] = []

        for case in dataset:
            case_id = str(case["id"])
            category = case.get("category", "unknown")
            severity = case.get("severity", "medium").lower()
            expected_action = case.get("expected_action", "block").lower()
            text = str(case.get("text", ""))
            context = {
                "redteam": True,
                "case_id": case_id,
                "category": category,
                "domain": case.get("domain", "general"),
            }

            response, latency_ms = self._call_detect(text, context)
            latencies.append(latency_ms)

            actual_action = str(response.get("action", "unknown")).lower()
            blocked = bool(response.get("should_block", response.get("blocked", False)))
            tier = response.get("tier_used")
            if isinstance(tier, int) and str(tier) in tier_counts:
                tier_counts[str(tier)] += 1
            else:
                tier_counts["unknown"] += 1

            bypassed = expected_action == "block" and actual_action not in ("block",)
            if bypassed and severity in severity_bypass:
                severity_bypass[severity] += 1

            results.append(
                RedTeamResult(
                    case_id=case_id,
                    category=category,
                    severity=severity,
                    expected_action=expected_action,
                    actual_action=actual_action,
                    blocked=blocked,
                    tier_used=tier if isinstance(tier, int) else None,
                    latency_ms=latency_ms,
                    bypassed=bypassed,
                    response=response,
                )
            )

        total = len(results)
        bypass_total = sum(1 for r in results if r.bypassed)
        block_rate = sum(1 for r in results if r.actual_action == "block") / max(total, 1)
        p95_latency = statistics.quantiles(latencies, n=20)[-1] if len(latencies) >= 20 else max(latencies, default=0.0)
        report = {
            "metadata": {
                "api_base_url": self.api_base_url,
                "dataset_path": str(self.dataset_path),
                "cases_executed": total,
            },
            "summary": {
                "bypass_total": bypass_total,
                "block_rate": round(block_rate, 4),
                "tier_counts": tier_counts,
                "latency_ms": {
                    "avg": round(sum(latencies) / max(len(latencies), 1), 2),
                    "p95": round(p95_latency, 2),
                    "max": round(max(latencies, default=0.0), 2),
                },
                "severity_bypass": severity_bypass,
            },
            "results": [
                {
                    "id": r.case_id,
                    "category": r.category,
                    "severity": r.severity,
                    "expected_action": r.expected_action,
                    "actual_action": r.actual_action,
                    "tier_used": r.tier_used,
                    "latency_ms": round(r.latency_ms, 2),
                    "bypassed": r.bypassed,
                }
                for r in results
            ],
        }
        return report


def main() -> int:
    api_base_url = os.getenv("SOVEREIGN_REDTEAM_API_URL", "http://localhost:8000")
    api_key = os.getenv("SOVEREIGN_API_KEY", "")
    if not api_key:
        raise SystemExit("SOVEREIGN_API_KEY is required for red-team harness.")

    out_path = Path(os.getenv("SOVEREIGN_REDTEAM_REPORT", "tests/redteam/redteam_report.json"))
    harness = RedTeamHarness(api_base_url=api_base_url, api_key=api_key)
    report = harness.run()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    sev = report["summary"]["severity_bypass"]
    if sev["critical"] > 0 or sev["high"] > 0:
        print(json.dumps(report["summary"], indent=2))
        raise SystemExit("High-severity bypass detected in red-team run.")
    print(json.dumps(report["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
