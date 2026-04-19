"""Rate limiting middleware."""

from datetime import datetime, timedelta
from typing import Dict
from sqlalchemy.orm import Session


# In-memory rate limit store (replace with Redis in production)
rate_limit_store: Dict[str, Dict] = {}

# Rate limits per tier (requests per hour)
RATE_LIMITS = {
    "free": 100,
    "pro": 1000,
    "enterprise": 10000,
}


def get_rate_limit(tier: str) -> int:
    """Get rate limit for tier."""
    return RATE_LIMITS.get(tier, 100)

import redis
import os
import json

# Redis connection for production
redis_url = os.getenv("REDIS_URL")
redis_client = None
if redis_url:
    try:
        redis_client = redis.from_url(redis_url)
        logger.info(f"Connected to Redis for rate limiting at {redis_url}")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}")

async def check_rate_limit(user, db: Session) -> dict:
    """Check if user has exceeded rate limit (Redis-backed if available)."""
    username = user.username
    tier = user.rate_limit_tier
    limit = get_rate_limit(tier)
    
    if redis_client:
        try:
            key = f"rate_limit:{username}"
            count = redis_client.incr(key)
            if count == 1:
                redis_client.expire(key, 3600) # 1 hour window
            
            remaining = max(0, limit - count)
            allowed = count <= limit
            
            return {
                "allowed": allowed,
                "limit": limit,
                "remaining": remaining,
                "reset_at": (datetime.utcnow() + timedelta(hours=1)).isoformat()
            }
        except Exception as e:
            logger.warning(f"Redis rate limit failed: {e}")
            # Fallback to in-memory below
    
    # In-memory fallback (existing logic)
    now = datetime.utcnow()
    if username not in rate_limit_store:
        rate_limit_store[username] = {
            "count": 0,
            "reset_at": now + timedelta(hours=1),
        }
    
    user_data = rate_limit_store[username]
    if now >= user_data["reset_at"]:
        user_data["count"] = 0
        user_data["reset_at"] = now + timedelta(hours=1)
    
    user_data["count"] += 1
    allowed = user_data["count"] <= limit
    
    return {
        "allowed": allowed,
        "limit": limit,
        "remaining": max(0, limit - user_data["count"]),
        "reset_at": user_data["reset_at"].isoformat(),
    }


def reset_rate_limit(username: str):
    """Reset rate limit for user (admin function)."""
    if username in rate_limit_store:
        del rate_limit_store[username]


def get_rate_limit_info(username: str, tier: str) -> dict:
    """Get current rate limit info for user."""
    limit = get_rate_limit(tier)
    
    if username not in rate_limit_store:
        return {
            "limit": limit,
            "remaining": limit,
            "reset_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
        }
    
    user_data = rate_limit_store[username]
    remaining = max(0, limit - user_data["count"])
    
    return {
        "limit": limit,
        "remaining": remaining,
        "reset_at": user_data["reset_at"].isoformat(),
    }
