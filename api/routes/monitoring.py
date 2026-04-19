"""Monitoring routes for system health and metrics."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.dependencies import get_control_tower
from config.policy_loader import PolicyLoader
from enforcement.control_tower_v3 import ControlTowerV3
from persistence.compliance_jsonl import ComplianceJSONLLogger
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


@router.get("/policy_effectiveness")
async def policy_effectiveness(
    control_tower: ControlTowerV3 = Depends(get_control_tower),
):
    """Routing mix as a lightweight policy routing heatmap (tiers vs volume)."""
    stats = control_tower.get_tier_stats()
    dist = stats.get("distribution", {})
    total = max(1, int(stats.get("total", 0)))
    return {
        "total_requests": total,
        "heatmap_rows": [
            {"tier": "tier1_regex", "count": stats.get("tier1_count", 0), "pct": dist.get("tier1_pct", 0)},
            {"tier": "tier2_semantic", "count": stats.get("tier2_count", 0), "pct": dist.get("tier2_pct", 0)},
            {"tier": "tier3_llm", "count": stats.get("tier3_count", 0), "pct": dist.get("tier3_pct", 0)},
        ],
        "health": stats.get("health"),
        "drift_note": "Configure embedding baselines in policy for full drift alerts.",
    }


@router.get("/drift_signals")
async def drift_signals(
    control_tower: ControlTowerV3 = Depends(get_control_tower),
    window: int = 200,
):
    """Lightweight drift-style signal from recent compliance rows (tier mix shift)."""
    policy = PolicyLoader()
    path = policy.get_compliance_audit_config().get("jsonl_path", "data/compliance_audit.jsonl")
    store = ComplianceJSONLLogger(path)
    rows = store.read_last(min(max(window, 10), 5000))
    tiers = [r.get("tier_used") for r in rows if isinstance(r.get("tier_used"), int)]
    t3_frac = sum(1 for t in tiers if t == 3) / max(1, len(tiers))
    stats = control_tower.get_tier_stats()
    return {
        "window_size": len(tiers),
        "tier3_fraction_recent_compliance_window": round(t3_frac, 4),
        "tier3_routing_pct_live": stats.get("distribution", {}).get("tier3_pct"),
        "drift_alert": t3_frac > 0.12 and len(tiers) >= 30,
        "note": "Heuristic only; pair with embedding baselines for production drift.",
    }
