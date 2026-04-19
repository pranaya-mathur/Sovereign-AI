"""Governance: PII redaction API and compliance JSONL export."""

import json
from collections import Counter
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from api.routes.auth import get_current_admin_user, get_current_user
from config.policy_loader import PolicyLoader
from enforcement.agentic_rails import agentic_preflight, goal_hijack_score
from persistence.compliance_jsonl import ComplianceJSONLLogger
from rules.pii_india import detect_india_pii, redact_india_pii

router = APIRouter(prefix="/api/governance", tags=["governance"])

# Synthetic lines for demo heatmap only (no real customer data).
_PII_HEATMAP_SAMPLES = [
    "KYC PAN ABCDE1234F submitted.",
    "GST 22AAAAA0000A1Z5 on the invoice.",
    "IFSC HDFC0000123 for NEFT.",
    "UPI: payments@okhdfcbank",
    "Call +91 9876543210 for support.",
    "Email billing@company.example for PAN updates.",
    "Vehicle KA 01 AB 1234 spotted.",
    "Aadhaar format 1234 5678 9012 (synthetic).",
    "PIN 560001 Bangalore.",
    "Card 4532 1488 0343 6467 test.",
    "Another PAN FGHIJ5678K in footer.",
    "Reach us at user.name+bank@mail.example.",
]


class RedactRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=100_000)


class AgenticCheckRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=50_000)
    tool_name: Optional[str] = None
    allowed_tools: Optional[List[str]] = None


@router.post("/redact")
async def redact_india_pii_endpoint(
    body: RedactRequest,
    current_user=Depends(get_current_user),
):
    """Return India-focused PII redaction and confidence-style aggregate score."""
    _ = current_user
    result = redact_india_pii(body.text)
    return {
        "redacted_text": result["redacted_text"],
        "matches": result["matches"],
        "entity_counts": result["entity_counts"],
        "aggregate_score": result["aggregate_score"],
    }


@router.get("/compliance/export")
async def export_compliance_jsonl(
    max_lines: int = Query(5000, ge=1, le=50_000),
    current_admin=Depends(get_current_admin_user),
):
    """Stream append-only audit JSONL (admin). Pro deployments can gate via SSO/RBAC."""
    _ = current_admin
    policy = PolicyLoader()
    path = policy.get_compliance_audit_config().get("jsonl_path", "data/compliance_audit.jsonl")
    store = ComplianceJSONLLogger(path)
    rows = store.read_last(max_lines)

    def gen():
        for row in rows:
            yield json.dumps(row, ensure_ascii=False, default=str) + "\n"

    return StreamingResponse(gen(), media_type="application/x-ndjson")


@router.get("/pii-heatmap-demo")
async def pii_heatmap_demo(current_user=Depends(get_current_user)):
    """Aggregate PII entity hits across synthetic demo strings (dashboard heatmap)."""
    _ = current_user
    counts: Counter = Counter()
    per_sample: List[Dict[str, object]] = []
    for line in _PII_HEATMAP_SAMPLES:
        matches = detect_india_pii(line)
        for m in matches:
            counts[m.entity_type] += 1
        per_sample.append(
            {
                "preview": line[:80],
                "entity_types": [m.entity_type for m in matches],
                "match_count": len(matches),
            }
        )
    return {
        "entity_counts": dict(counts),
        "samples_scanned": len(_PII_HEATMAP_SAMPLES),
        "per_sample": per_sample,
    }


@router.post("/agentic-check")
async def agentic_check_endpoint(
    body: AgenticCheckRequest,
    current_user=Depends(get_current_user),
):
    """OWASP Agentic-style probe: goal hijack score + optional tool whitelist (Tier 3 rails)."""
    _ = current_user
    ctx: dict = {}
    if body.tool_name:
        ctx["tool_name"] = body.tool_name
    if body.allowed_tools is not None:
        ctx["allowed_tools"] = body.allowed_tools
    gh = goal_hijack_score(body.text)
    rail = agentic_preflight(body.text, ctx)
    return {
        "goal_hijack_score": gh,
        "rail_triggered": rail is not None,
        "rail_result": rail,
    }


@router.get("/correction-history")
async def correction_history(
    limit: int = Query(100, ge=1, le=2000),
    current_user=Depends(get_current_user),
):
    """Rows where post-LLM output validation ran (Pro: richer UI in dashboard)."""
    _ = current_user
    policy = PolicyLoader()
    path = policy.get_compliance_audit_config().get("jsonl_path", "data/compliance_audit.jsonl")
    store = ComplianceJSONLLogger(path)
    rows = store.read_last(20_000)
    corrections = [
        r
        for r in rows
        if (r.get("output_validation_attempts") or 0) > 0 or r.get("output_self_corrected")
    ]
    tail = corrections[-limit:]
    return {"total_matched": len(corrections), "returned": len(tail), "items": tail}
