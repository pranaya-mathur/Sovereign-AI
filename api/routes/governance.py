"""Governance: PII redaction API and compliance JSONL export."""

import json

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from api.routes.auth import get_current_admin_user, get_current_user
from config.policy_loader import PolicyLoader
from persistence.compliance_jsonl import ComplianceJSONLLogger
from rules.pii_india import redact_india_pii

router = APIRouter(prefix="/api/governance", tags=["governance"])


class RedactRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=100_000)


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
