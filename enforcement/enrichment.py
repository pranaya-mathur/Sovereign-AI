"""Result enrichment and compliance emission helpers."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from contracts.severity_levels import EnforcementAction
from enforcement.output_correction import apply_output_validation_and_correction
from persistence.compliance_jsonl import sha256_text
from rules.pii_india import redact_india_pii

logger = logging.getLogger(__name__)


def emit_compliance_row(
    llm_response: str,
    result: Any,
    context: Dict[str, Any],
    session_id: Optional[str],
    policy: Any,
    compliance_logger: Optional[Any],
) -> None:
    """Append compliance event to JSONL when enabled."""
    if not compliance_logger:
        return
    cfg = policy.get_compliance_audit_config()
    row: Dict[str, Any] = {
        "session_id": session_id,
        "action": result.action.value,
        "tier_used": result.tier_used,
        "method": result.method,
        "confidence": result.confidence,
        "failure_class": result.failure_class.value if result.failure_class else None,
        "processing_time_ms": result.processing_time_ms,
        "context_hash": sha256_text(str(sorted((context or {}).keys()))),
        "response_hash": sha256_text(llm_response),
    }
    if result.metadata.get("pii_india"):
        row["pii_aggregate_score"] = result.metadata["pii_india"].get("aggregate_score")
    if result.metadata.get("output_validation"):
        ov = result.metadata["output_validation"]
        row["groundedness_score"] = ov.get("groundedness_score")
        row["output_validation_attempts"] = ov.get("attempts")
    if result.metadata.get("corrected_response"):
        row["output_self_corrected"] = True
    if not cfg.get("store_text_hashes_only", True):
        row["response_preview"] = (llm_response or "")[:500]
    if result.findings:
        row["findings"] = result.findings
    compliance_logger.append(row)


def enrich_result_metadata(
    llm_response: str,
    result: Any,
    context: Dict[str, Any],
    span: Any,
    policy: Any,
    semantic_detector: Optional[Any],
    llm_agent: Optional[Any],
    tier3_available: bool,
    external_snapshot: Optional[Dict[str, Any]] = None,
) -> None:
    """Attach PII scan, output validation, and optional RAG rails metadata."""
    if external_snapshot:
        result.metadata["external_moderation"] = external_snapshot

    pii_cfg = policy.get_pii_india_config()
    if pii_cfg.get("enabled", False) and pii_cfg.get("auto_scan", True):
        if pii_cfg.get("include_in_metadata", True):
            result.metadata["pii_india"] = redact_india_pii(llm_response)

    apply_output_validation_and_correction(
        llm_response=llm_response,
        context=context,
        result=result,
        policy=policy,
        llm_agent=llm_agent,
        tier3_available=tier3_available,
        span=span,
    )

    rag_cfg = policy.get_rag_config()
    if rag_cfg.get("enabled", False):
        try:
            from signals.rag_logic import RAGRail
            rag_rail = RAGRail(semantic_detector)

            retrieval_ctx = context.get("retrieval_context") or context.get("documents")
            faith = rag_rail.check_faithfulness(
                llm_response,
                retrieval_ctx,
                threshold=rag_cfg.get("faithfulness_threshold", 0.65),
            )
            result.metadata["rag_faithfulness"] = faith
            result.metadata["rag_citations"] = rag_rail.check_citations(llm_response)

            if rag_cfg.get("qdrant_grounding", False):
                result.metadata["rag_qdrant_grounding"] = rag_rail.verify_grounding_with_qdrant(llm_response)

            if faith.get("status") == "unfaithful":
                result.action = EnforcementAction.WARN
                result.explanation += " | Unfaithful to source context"
        except Exception as exc:
            logger.warning("RAG rails failed: %s", exc)

    ext_meta = result.metadata.get("external_moderation")
    if ext_meta:
        span.set_attribute("sovereign.external_provider", str(ext_meta.get("provider", "")))
        span.set_attribute(
            "sovereign.external_max_score",
            float(ext_meta.get("max_category_score") or 0.0),
        )
