"""Detection API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from api.auth.models import User
from api.auth.dependencies import get_current_active_user
from api.middleware.rate_limiter import rate_limit_dependency
from enforcement.control_tower_v3 import ControlTowerV3

router = APIRouter()
control_tower = ControlTowerV3()


class DetectionRequest(BaseModel):
    """Detection request model."""
    text: str
    context: Optional[dict] = None


class DetectionResponse(BaseModel):
    """Detection response model."""
    text: str
    tier_used: int
    method: str
    confidence: float
    should_block: bool
    action: str
    severity: Optional[str]
    reason: Optional[str]
    processing_time_ms: float
    rate_limit: dict


class BatchDetectionRequest(BaseModel):
    """Batch detection request."""
    texts: List[str]
    context: Optional[dict] = None


@router.post("/detect", response_model=DetectionResponse)
async def detect(
    request: DetectionRequest,
    current_user: User = Depends(get_current_active_user),
    rate_info: dict = Depends(rate_limit_dependency)
):
    """Detect issues in LLM response.
    
    Uses 3-tier detection:
    - Tier 1: Fast regex (<1ms)
    - Tier 2: Semantic embeddings (5-10ms)
    - Tier 3: LLM agent reasoning (50-100ms)
    """
    result = control_tower.check_response(request.text, request.context)
    
    return DetectionResponse(
        text=request.text[:100] + "..." if len(request.text) > 100 else request.text,
        tier_used=result.get("tier_used", 1),
        method=result.get("method", "unknown"),
        confidence=result.get("confidence", 0.0),
        should_block=result.get("should_block", False),
        action=result.get("action", "allow"),
        severity=result.get("severity"),
        reason=result.get("reason"),
        processing_time_ms=result.get("processing_time_ms", 0.0),
        rate_limit=rate_info
    )


@router.post("/batch_detect")
async def batch_detect(
    request: BatchDetectionRequest,
    current_user: User = Depends(get_current_active_user),
    rate_info: dict = Depends(rate_limit_dependency)
):
    """Batch detection for multiple texts."""
    results = []
    
    for text in request.texts:
        result = control_tower.check_response(text, request.context)
        results.append({
            "text": text[:100] + "..." if len(text) > 100 else text,
            "tier_used": result.get("tier_used", 1),
            "should_block": result.get("should_block", False),
            "confidence": result.get("confidence", 0.0),
        })
    
    return {
        "results": results,
        "total": len(results),
        "blocked": sum(1 for r in results if r["should_block"]),
        "rate_limit": rate_info
    }