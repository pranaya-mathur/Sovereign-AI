"""Output validation and correction helpers."""

from __future__ import annotations

from typing import Any, Dict, Optional

from contracts.severity_levels import EnforcementAction
from enforcement.output_validator import run_output_validation


def apply_output_validation_and_correction(
    llm_response: str,
    context: Dict[str, Any],
    result: Any,
    policy: Any,
    llm_agent: Optional[Any],
    tier3_available: bool,
    span: Any,
) -> None:
    """Attach output validation metadata and optional corrected response."""
    ov_cfg = policy.get_output_validation_config()
    if (
        ov_cfg.get("enabled", False)
        and result.action != EnforcementAction.BLOCK
    ):
        agent = llm_agent if tier3_available else None
        ov = run_output_validation(
            llm_response,
            context or {},
            agent,
            threshold=float(ov_cfg.get("groundedness_threshold", 0.7)),
            max_retries=int(ov_cfg.get("max_retries", 1)),
        )
        result.metadata["output_validation"] = ov
        gs = ov.get("groundedness_score")
        if gs is not None:
            span.set_attribute("sovereign.groundedness_score", float(gs))
        if ov.get("corrected_response"):
            result.metadata["corrected_response"] = ov["corrected_response"]
            result.explanation = (
                result.explanation + " | Output self-corrected for grounding (Tier 3)."
            ).strip(" |")
