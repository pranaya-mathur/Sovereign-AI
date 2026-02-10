"""Monitoring routes for system health and metrics."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.dependencies import get_control_tower
from enforcement.control_tower_v3 import ControlTowerV3
from persistence.database import get_db


router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


@router.get("/health")
async def health_check(
    control_tower: ControlTowerV3 = Depends(get_control_tower),
    db: Session = Depends(get_db),
):
    """Health check endpoint."""
    stats = control_tower.get_tier_stats()
    
    # Test database connection
    try:
        db.execute("SELECT 1")
        db_healthy = True
    except Exception:
        db_healthy = False
    
    is_healthy = stats["health"]["is_healthy"] and db_healthy
    
    return {
        "status": "healthy" if is_healthy else "degraded",
        "database": "connected" if db_healthy else "disconnected",
        "tier_health": stats["health"]["message"],
        "tier_distribution": stats["distribution"],
    }


@router.get("/tier_stats")
async def get_tier_stats(
    control_tower: ControlTowerV3 = Depends(get_control_tower),
):
    """Get tier distribution statistics."""
    stats = control_tower.get_tier_stats()
    
    return {
        "total_checks": stats["total"],
        "tier1_count": stats["tier1_count"],
        "tier2_count": stats["tier2_count"],
        "tier3_count": stats["tier3_count"],
        "distribution": stats["distribution"],
        "health": stats["health"],
    }


@router.get("/metrics")
async def get_metrics(
    control_tower: ControlTowerV3 = Depends(get_control_tower),
):
    """Get detailed metrics."""
    stats = control_tower.get_tier_stats()
    
    return {
        "total_detections": stats["total"],
        "tier_breakdown": {
            "tier1": {
                "count": stats["tier1_count"],
                "percentage": stats["distribution"]["tier1_pct"],
                "target": 95.0,
            },
            "tier2": {
                "count": stats["tier2_count"],
                "percentage": stats["distribution"]["tier2_pct"],
                "target": 4.0,
            },
            "tier3": {
                "count": stats["tier3_count"],
                "percentage": stats["distribution"]["tier3_pct"],
                "target": 1.0,
            },
        },
        "health": {
            "is_healthy": stats["health"]["is_healthy"],
            "message": stats["health"]["message"],
        },
    }


@router.get("/status")
async def get_status():
    """Get system status."""
    return {
        "service": "LLM Observability API",
        "version": "5.0.0",
        "status": "operational",
    }
