"""Monitoring API endpoints."""

from fastapi import APIRouter, Depends
from api.auth.models import User
from api.auth.dependencies import get_current_active_user
from api.middleware.rate_limiter import RateLimiter
from enforcement.control_tower_v3 import ControlTowerV3

router = APIRouter()
rate_limiter = RateLimiter()
control_tower = ControlTowerV3()


@router.get("/tier_stats")
async def get_tier_stats(current_user: User = Depends(get_current_active_user)):
    """Get tier distribution statistics."""
    return control_tower.get_tier_stats()


@router.get("/rate_limit")
async def get_rate_limit_info(current_user: User = Depends(get_current_active_user)):
    """Get current rate limit status."""
    return rate_limiter.get_rate_limit_info(current_user)


@router.get("/health")
async def get_health_status(current_user: User = Depends(get_current_active_user)):
    """Get detailed health status."""
    tier_stats = control_tower.get_tier_stats()
    
    return {
        "status": "healthy" if tier_stats["health"]["is_healthy"] else "degraded",
        "tier_distribution": tier_stats["distribution"],
        "health_message": tier_stats["health"]["message"],
        "total_checks": tier_stats["total_checks"]
    }