"""Monitoring API endpoints."""

from fastapi import APIRouter, Depends
from api.routes.auth import get_current_user
from api.dependencies import get_control_tower
from enforcement.control_tower_v3 import ControlTowerV3

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


@router.get("/tier_stats")
async def get_tier_stats(
    current_user: dict = Depends(get_current_user),
    control_tower: ControlTowerV3 = Depends(get_control_tower),
):
    """Get tier distribution statistics."""
    stats = control_tower.get_tier_stats()
    
    return {
        "distribution": stats["distribution"],
        "health": stats["health"],
        "total_checks": stats.get("total", 0),
        "tier1_count": stats.get("tier1_count", 0),
        "tier2_count": stats.get("tier2_count", 0),
        "tier3_count": stats.get("tier3_count", 0),
    }


@router.get("/health")
async def get_health_status(
    current_user: dict = Depends(get_current_user),
    control_tower: ControlTowerV3 = Depends(get_control_tower),
):
    """Get detailed health status."""
    stats = control_tower.get_tier_stats()
    
    return {
        "status": "healthy" if stats["health"]["is_healthy"] else "degraded",
        "tier_distribution": stats["distribution"],
        "health_message": stats["health"]["message"],
        "total_checks": stats.get("total", 0),
        "is_healthy": stats["health"]["is_healthy"],
    }


@router.get("/performance")
async def get_performance_metrics(
    current_user: dict = Depends(get_current_user),
    control_tower: ControlTowerV3 = Depends(get_control_tower),
):
    """Get performance metrics."""
    stats = control_tower.get_tier_stats()
    
    # Calculate average processing times (mock data for now)
    return {
        "tier1_avg_ms": 0.5,
        "tier2_avg_ms": 6.0,
        "tier3_avg_ms": 60.0,
        "overall_avg_ms": 2.0,
        "total_processed": stats.get("total", 0),
        "cache_hit_rate": 0.993,  # 99.3% from requirements
    }
