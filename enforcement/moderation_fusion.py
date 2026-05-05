"""External moderation fusion helpers for Control Tower."""

from __future__ import annotations

from typing import Any, Dict, Optional

from enforcement.tier_router import TierRouter
from providers.external_moderation import run_external_moderation_pipeline


def apply_external_moderation_fusion(
    llm_response: str,
    tier1_result: Dict[str, Any],
    ext_cfg: Dict[str, Any],
    tier_router: TierRouter,
) -> tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """Run external moderation and fuse into Tier-1 result."""
    external_snapshot = None
    if ext_cfg.get("enabled", False):
        ext_agg = run_external_moderation_pipeline(llm_response, ext_cfg)
        if ext_agg:
            tier1_result = tier_router.fuse_external(
                tier1_result,
                ext_agg,
                fuse_weight=float(ext_cfg.get("fuse_weight", 0.35)),
            )
    external_snapshot = tier1_result.get("external_moderation")
    return tier1_result, external_snapshot
