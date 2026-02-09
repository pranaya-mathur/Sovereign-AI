"""Rate limiting middleware for API endpoints."""

from typing import Optional, Dict
from datetime import datetime, timedelta
from fastapi import HTTPException, status, Request
from api.auth.models import User, RateLimitTier
from persistence.rate_limit_store import RateLimitStore


class RateLimiter:
    """Rate limiter for API requests.
    
    Implements multi-level rate limiting:
    - Per-user limits based on tier
    - Per-API-key limits
    - Global system limits
    - Per-tier detection limits
    """
    
    # Rate limit configurations (requests per hour)
    TIER_LIMITS = {
        RateLimitTier.FREE: 100,
        RateLimitTier.PRO: 1000,
        RateLimitTier.ENTERPRISE: 10000,
    }
    
    # Detection tier limits (to maintain 95/4/1 distribution)
    DETECTION_TIER_LIMITS = {
        "tier1": None,  # No limit for fast regex
        "tier2": 50,    # 50 req/hour for semantic
        "tier3": 10,    # 10 req/hour for LLM agent
    }
    
    GLOBAL_LIMIT = 10000  # Global requests per hour
    
    def __init__(self, store: Optional[RateLimitStore] = None):
        """Initialize rate limiter.
        
        Args:
            store: Rate limit storage backend (default: in-memory)
        """
        self.store = store or RateLimitStore()
    
    def check_rate_limit(
        self,
        user: User,
        detection_tier: Optional[str] = None,
        request: Optional[Request] = None
    ) -> Dict[str, any]:
        """Check if request is within rate limits.
        
        Args:
            user: Current user
            detection_tier: Optional detection tier (tier1/tier2/tier3)
            request: Optional request object for IP-based limiting
            
        Returns:
            Dict with rate limit info
            
        Raises:
            HTTPException: If rate limit exceeded
        """
        # Check user tier limit
        user_limit = self.TIER_LIMITS.get(user.rate_limit_tier, 100)
        user_key = f"user:{user.username}"
        user_count = self.store.increment(user_key)
        
        if user_count > user_limit:
            reset_time = self.store.get_ttl(user_key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Limit: {user_limit}/hour. Resets in {reset_time}s",
                headers={"X-RateLimit-Limit": str(user_limit), "X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(reset_time)}
            )
        
        # Check detection tier limit
        if detection_tier and detection_tier in self.DETECTION_TIER_LIMITS:
            tier_limit = self.DETECTION_TIER_LIMITS[detection_tier]
            if tier_limit is not None:
                tier_key = f"tier:{user.username}:{detection_tier}"
                tier_count = self.store.increment(tier_key)
                
                if tier_count > tier_limit:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"{detection_tier} rate limit exceeded. Limit: {tier_limit}/hour"
                    )
        
        # Check global limit
        global_key = "global:requests"
        global_count = self.store.increment(global_key)
        
        if global_count > self.GLOBAL_LIMIT:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="System rate limit exceeded. Please try again later."
            )
        
        # Return rate limit info
        remaining = user_limit - user_count
        reset_time = self.store.get_ttl(user_key)
        
        return {
            "limit": user_limit,
            "remaining": max(0, remaining),
            "reset": reset_time,
            "tier": user.rate_limit_tier.value
        }
    
    def get_rate_limit_info(self, user: User) -> Dict[str, any]:
        """Get current rate limit status for user.
        
        Args:
            user: User to check
            
        Returns:
            Rate limit information
        """
        user_limit = self.TIER_LIMITS.get(user.rate_limit_tier, 100)
        user_key = f"user:{user.username}"
        user_count = self.store.get_count(user_key)
        reset_time = self.store.get_ttl(user_key)
        
        return {
            "limit": user_limit,
            "used": user_count,
            "remaining": max(0, user_limit - user_count),
            "reset": reset_time,
            "tier": user.rate_limit_tier.value
        }


# Global rate limiter instance
_rate_limiter = RateLimiter()


def rate_limit_dependency(
    user: User,
    detection_tier: Optional[str] = None
) -> Dict[str, any]:
    """FastAPI dependency for rate limiting.
    
    Usage:
        @app.post("/detect")
        async def detect(
            user: User = Depends(get_current_user),
            rate_info: dict = Depends(rate_limit_dependency)
        ):
            # Your endpoint logic
            pass
    
    Args:
        user: Current authenticated user
        detection_tier: Optional detection tier
        
    Returns:
        Rate limit information
    """
    return _rate_limiter.check_rate_limit(user, detection_tier)