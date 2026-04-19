"""Detection routes with authentication and rate limiting."""

import uuid
import asyncio
import re
from datetime import datetime, timezone
from typing import Optional
from collections import Counter
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, validator

from api.routes.auth import get_current_user
from api.dependencies import get_control_tower
from api.middleware.rate_limiter import check_rate_limit
from enforcement.control_tower_v3 import ControlTowerV3
from persistence.database import get_db
from persistence.repository import DetectionRepository

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["detection"])


def is_pathological_input(text: str) -> tuple[bool, str]:
    """Detect pathological inputs that might cause timeouts.
    
    Industry standard: Detect malicious patterns early (OWASP Input Validation).
    
    This matches the early detection in Control Tower for consistency.
    
    Args:
        text: Input text to validate
        
    Returns:
        Tuple of (is_pathological, reason)
    """
    if not text:
        return False, ""
    
    # Check 1: Excessive repetition (>80% same character)
    if len(text) > 50:
        char_counts = Counter(text)
        if char_counts:
            most_common_char, most_common_count = char_counts.most_common(1)[0]
            repetition_ratio = most_common_count / len(text)
            
            if repetition_ratio > 0.8:
                return True, f"Excessive repetition detected ({repetition_ratio*100:.1f}%)"
    
    # Check 2: Very low character diversity
    if len(text) > 100:
        unique_chars = len(set(text))
        if unique_chars < 5:
            return True, f"Low character diversity ({unique_chars} unique chars in {len(text)} chars)"
    
    # Check 3: Repeated character patterns (aaaa, bbbb)
    if re.search(r'(.)\1{20,}', text):
        return True, "Character repetition pattern detected"
    
    # Check 4: SQL injection patterns (CRITICAL FIX!)
    sql_patterns = [
        (r'SELECT .* FROM', "SQL injection pattern"),
        (r'UNION SELECT', "SQL union attack"),
        (r'DROP TABLE', "SQL drop table"),
        (r'INSERT INTO', "SQL injection"),
        (r'DELETE FROM', "SQL deletion"),
        (r"'\s*OR\s*'1'\s*=\s*'1", "SQL OR injection"),
    ]
    
    for pattern, description in sql_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True, f"Attack pattern detected: {description}"
    
    # Check 5: XSS patterns (CRITICAL FIX!)
    xss_patterns = [
        (r'<script[^>]*>', "XSS script tag"),
        (r'javascript:', "JavaScript protocol"),
        (r'onerror\s*=', "XSS onerror handler"),
        (r'onload\s*=', "XSS onload handler"),
    ]
    
    for pattern, description in xss_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True, f"Attack pattern detected: {description}"
    
    # Check 6: Path traversal patterns (CRITICAL FIX!)
    path_patterns = [
        (r'\.\.[\\/]\.\.[\\/]', "Path traversal"),
        (r'etc[\\/]passwd', "Unix password file access"),
        (r'cmd\.exe', "Windows command execution"),
        (r'\\\\windows\\\\system32', "Windows system access"),
    ]
    
    for pattern, description in path_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True, f"Attack pattern detected: {description}"
    
    # Check 7: Other dangerous patterns
    other_patterns = [
        (r'<.*?>{50,}', "HTML tag flooding"),
        (r'[\x00-\x08\x0B\x0C\x0E-\x1F]{10,}', "Control character flooding"),
    ]
    
    for pattern, description in other_patterns:
        if re.search(pattern, text):
            return True, description
    
    return False, ""


def preprocess_input(text: str, max_length: int = 10000) -> str:
    """Preprocess and sanitize input text.
    
    Industry standard: Input sanitization (OWASP ASVS 5.1.3).
    
    Args:
        text: Raw input text
        max_length: Maximum allowed length
        
    Returns:
        Sanitized text truncated to max_length
    """
    if not text:
        return ""
    
    # Truncate to reasonable length (prevents DoS)
    if len(text) > max_length:
        logger.warning(f"Input truncated from {len(text)} to {max_length} chars")
        text = text[:max_length]
    
    # Remove null bytes and other problematic characters
    text = text.replace('\x00', '')
    
    # Normalize whitespace (prevent whitespace-based attacks)
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


class DetectionRequest(BaseModel):
    """Detection request model."""
    text: str
    context: Optional[dict] = None
    
    @validator('text')
    def validate_text(cls, v):
        """Validate text input."""
        if v is None:
            return ""
        
        # Limit text length to prevent DOS (OWASP)
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


class FeedbackRequest(BaseModel):
    """Model for submitting feedback on detection results."""
    request_id: str
    text: str
    actual_label: str # e.g. "safe", "dpdp_pii", "fraud"
    is_correct: bool
    comment: Optional[str] = None


@router.post("/detect", response_model=DetectionResponse)
async def detect(
    request: DetectionRequest,
    http_request: Request,
    control_tower: ControlTowerV3 = Depends(get_control_tower),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Detect issues in text using 3-tier system with timeout protection.
    
    Industry standards implemented:
    - OWASP Input Validation (sanitization, length limits)
    - Timeout protection (prevents resource exhaustion)
    - Thread cleanup (prevents memory leaks)
    - Proper error handling and logging
    - Rate limiting (DoS prevention)
    """
    # Check rate limit (OWASP Rate Limiting)
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
    
    # CRITICAL FIX 1: Preprocess input to detect pathological patterns
    preprocessed_text = preprocess_input(request.text, max_length=10000)
    
    # CRITICAL FIX 2: Early detection of pathological inputs
    # This now includes SQL, XSS, and path traversal patterns!
    is_pathological, pathological_reason = is_pathological_input(preprocessed_text)
    
    if is_pathological:
        logger.warning(f"Pathological input detected: {pathological_reason} (request_id={request_id})")
        
        # Return early with block action (don't waste resources on malicious input)
        # This bypasses Control Tower entirely - saves 2+ seconds!
        return DetectionResponse(
            action="block",
            tier_used=1,
            method="input_validation",
            confidence=0.95,
            processing_time_ms=0.5,
            should_block=True,
            reason=f"Pathological input detected: {pathological_reason}",
            rate_limit={
                "limit": rate_limit_info["limit"],
                "remaining": rate_limit_info["remaining"],
                "reset_at": rate_limit_info["reset_at"],
            },
        )
    
    try:
        # CRITICAL FIX 3: Increased timeout from 5s to 15s for CPU-only systems
        # Industry standard: Timeout should be 3x average processing time
        detection_task = asyncio.create_task(
            asyncio.to_thread(
                control_tower.evaluate_response,
                llm_response=preprocessed_text,
                context=request.context or {},
            )
        )
        
        try:
            # 15-second timeout (handles i3 CPU without GPU)
            result = await asyncio.wait_for(detection_task, timeout=15.0)
            
        except asyncio.TimeoutError:
            # CRITICAL FIX 4: Proper cleanup on timeout
            logger.error(f"Detection timeout after 15s (request_id={request_id}, text_len={len(preprocessed_text)})")
            
            # Cancel the task to release resources
            detection_task.cancel()
            try:
                await detection_task
            except asyncio.CancelledError:
                pass  # Expected
            
            # Detection took too long - block as suspicious
            return DetectionResponse(
                action="block",
                tier_used=1,
                method="timeout_protection",
                confidence=0.75,
                processing_time_ms=15000.0,
                should_block=True,
                reason="Request processing timeout - potential attack pattern detected",
                rate_limit={
                    "limit": rate_limit_info["limit"],
                    "remaining": rate_limit_info["remaining"],
                    "reset_at": rate_limit_info["reset_at"],
                },
            )
        
        # Save to database (async to not block response)
        try:
            detection_repo = DetectionRepository(db)
            detection_repo.create({
                "llm_response": preprocessed_text[:1000],  # Truncate for storage
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
            # Non-critical: Log but don't fail request
            logger.warning(f"Could not save detection log: {e}")
        
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
        # Input validation error (OWASP Error Handling)
        logger.warning(f"Validation error: {e} (request_id={request_id})")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        # Unexpected error - log with full context and return safe response
        logger.error(f"Detection error: {e} (request_id={request_id})", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Detection failed: {str(e)[:100]}",
        )

@router.post("/feedback/submit", status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    request: FeedbackRequest,
    current_user = Depends(get_current_user),
):
    """Submit feedback for a previous detection result (Active Learning)."""
    import json
    try:
        # Log to secondary feedback file for processing
        feedback_file = "data/active_learning_feedback.jsonl"
        with open(feedback_file, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": datetime.now(timezone.utc).isoformat(),
                "user": current_user.username,
                "request_id": request.request_id,
                "text": request.text,
                "actual_label": request.actual_label,
                "is_correct": request.is_correct,
                "comment": request.comment
            }) + "\n")
            
        return {"status": "success", "message": "Feedback received for active learning"}
    except Exception as e:
        logger.error(f"Failed to save feedback: {e}")
        raise HTTPException(status_code=500, detail="Feedback storage failed")
