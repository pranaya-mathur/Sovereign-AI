"""Detection API endpoints."""

from fastapi import APIRouter, Depends
from typing import Optional

from api.models import DetectionRequest, DetectionResponse
from api.routes.auth import get_current_user
from api.dependencies import get_control_tower
from enforcement.control_tower_v3 import ControlTowerV3

router = APIRouter(prefix="/api", tags=["detection"])


@router.post("/detect", response_model=DetectionResponse)
async def detect(
    request: DetectionRequest,
    current_user: dict = Depends(get_current_user),
    control_tower: ControlTowerV3 = Depends(get_control_tower),
):
    """Detect issues in LLM response.
    
    Uses 3-tier detection:
    - Tier 1: Fast regex (<1ms)
    - Tier 2: Semantic embeddings (5-10ms)
    - Tier 3: LLM agent reasoning (50-100ms)
    """
    result = control_tower.evaluate_response(
        llm_response=request.llm_response,
        context=request.context or {},
    )
    
    # Mock rate limit info
    rate_limits = {
        "free": 100,
        "pro": 1000,
        "enterprise": 10000,
    }
    
    user_tier = current_user.get("rate_limit_tier", "free")
    limit = rate_limits.get(user_tier, 100)
    remaining = limit - 1  # Mock calculation
    
    return DetectionResponse(
        action=result.action.value,
        tier_used=result.tier_used,
        method=result.method,
        confidence=result.confidence,
        processing_time_ms=result.processing_time_ms,
        failure_class=result.failure_class.value if result.failure_class else None,
        severity=result.severity.value if result.severity else None,
        explanation=result.explanation,
        blocked=result.action.value == "block",
    )
