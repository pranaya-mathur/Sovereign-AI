"""Detection routes with authentication and rate limiting."""

import uuid
import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, validator

from api.routes.auth import get_current_user
from api.dependencies import get_control_tower
from api.middleware.rate_limiter import check_rate_limit
from enforcement.control_tower_v3 import ControlTowerV3
from persistence.database import get_db
from persistence.repository import DetectionRepository


router = APIRouter(prefix="/api", tags=["detection"])


class DetectionRequest(BaseModel):
    """Detection request model."""
    text: str
    context: Optional[dict] = None
    
    @validator('text')
    def validate_text(cls, v):
        """Validate text input."""
        if v is None:
            return ""
        
        # Limit text length to prevent DOS
        max_length = 50000  # 50k chars max
        if len(v) > max_length:
            raise ValueError(f"Text too long: {len(v)} chars (max: {max_length})")
        
        return v


class DetectionResponse(BaseModel):
    """Detection response model."""
    action: str
    tier_used: int
    method: str
    confidence: float
    processing_time_ms: float
    should_block: bool
    reason: Optional[str] = None
    rate_limit: dict


@router.post("/detect", response_model=DetectionResponse)
async def detect(
    request: DetectionRequest,
    http_request: Request,
    control_tower: ControlTowerV3 = Depends(get_control_tower),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Detect issues in text using 3-tier system with timeout protection."""
    # Check rate limit
    rate_limit_info = await check_rate_limit(
        user=current_user,
        db=db,
    )
    
    if not rate_limit_info["allowed"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"X-RateLimit-Remaining": "0"},
        )
    
    request_id = str(uuid.uuid4())
    
    try:
        # Run detection with timeout (5 seconds max)
        detection_task = asyncio.create_task(
            asyncio.to_thread(
                control_tower.evaluate_response,
                llm_response=request.text,
                context=request.context or {},
            )
        )
        
        try:
            result = await asyncio.wait_for(detection_task, timeout=5.0)
        except asyncio.TimeoutError:
            # Detection took too long - block as suspicious
            return DetectionResponse(
                action="block",
                tier_used=1,
                method="timeout_protection",
                confidence=0.75,
                processing_time_ms=5000.0,
                should_block=True,
                reason="Request processing timeout - potential attack pattern detected",
                rate_limit={
                    "limit": rate_limit_info["limit"],
                    "remaining": rate_limit_info["remaining"],
                    "reset_at": rate_limit_info["reset_at"],
                },
            )
        
        # Save to database
        try:
            detection_repo = DetectionRepository(db)
            detection_repo.create({
                "llm_response": request.text[:1000],  # Truncate for storage
                "context": request.context,
                "action": result.action.value,
                "tier_used": result.tier_used,
                "method": result.method,
                "confidence": result.confidence,
                "processing_time_ms": result.processing_time_ms,
                "failure_class": result.failure_class.value if result.failure_class else None,
                "severity": result.severity.value if result.severity else None,
                "explanation": result.explanation,
                "blocked": result.action.value == "block",
                "request_id": request_id,
            })
        except Exception as e:
            print(f"Warning: Could not save detection log: {e}")
        
        return DetectionResponse(
            action=result.action.value,
            tier_used=result.tier_used,
            method=result.method,
            confidence=result.confidence,
            processing_time_ms=result.processing_time_ms,
            should_block=result.action.value == "block",
            reason=result.explanation,
            rate_limit={
                "limit": rate_limit_info["limit"],
                "remaining": rate_limit_info["remaining"],
                "reset_at": rate_limit_info["reset_at"],
            },
        )
    
    except ValueError as e:
        # Input validation error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        # Unexpected error - log and return safe response
        print(f"Detection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Detection failed: {str(e)[:100]}",
        )
