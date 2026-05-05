"""Enhanced FastAPI application with database integration."""

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
try:
    from slowapi.middleware import SlowAPIMiddleware
except Exception:  # pragma: no cover - optional dependency fallback
    SlowAPIMiddleware = None

from api.models import (
    HealthResponse,
    StatsResponse,
)
from api.dependencies import get_control_tower
from api.middleware import MetricsMiddleware, RequestLoggingMiddleware
from api.middleware.auth import APIKeyJWTAuthMiddleware, limiter
from api.metrics import router as metrics_router
from api.routes import admin as admin_routes
from api.routes import auth as auth_routes
from api.routes import detection as detection_routes
from api.routes import governance as governance_routes
from api.routes import monitoring as monitoring_routes
from enforcement.control_tower_v3 import ControlTowerV3
from persistence.database import get_db
from persistence.repository import DetectionRepository, MetricsRepository

logger = logging.getLogger(__name__)


def _is_production() -> bool:
    env = (os.getenv("ENV") or os.getenv("ENVIRONMENT") or "").lower()
    return env == "production"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management for FastAPI app."""
    if os.getenv("SEED_DEFAULT_USERS"):
        logger.warning(
            "SEED_DEFAULT_USERS is deprecated and ignored; runtime user seeding is disabled."
        )
    yield

    logger.info("Shutting down LLM Observability API...")


app = FastAPI(
    title="LLM Observability API",
    description="Production-grade LLM observability with 3-tier detection",
    version="4.1.0",
    lifespan=lifespan,
)

# CORS: explicit origins only (wildcard + credentials is invalid in browsers)
CORS_ORIGINS_RAW = os.getenv("CORS_ORIGINS", "")
if CORS_ORIGINS_RAW.strip():
    _cors_origins = [o.strip() for o in CORS_ORIGINS_RAW.split(",") if o.strip()]
else:
    _cors_origins = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://localhost:8501",  # Streamlit dashboards
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(MetricsMiddleware)
app.add_middleware(RequestLoggingMiddleware)
if SlowAPIMiddleware is not None:
    app.add_middleware(SlowAPIMiddleware)
app.add_middleware(APIKeyJWTAuthMiddleware)
app.state.limiter = limiter

# Include metrics router
app.include_router(metrics_router, tags=["metrics"])
app.include_router(auth_routes.router)
app.include_router(detection_routes.router)
app.include_router(monitoring_routes.router)
app.include_router(admin_routes.router)
app.include_router(governance_routes.router)


@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint."""
    return {
        "service": "LLM Observability API",
        "version": "4.1.0",
        "status": "operational",
        "docs": "/docs",
    }


@app.get("/health", response_model=HealthResponse)
async def health_check(
    control_tower: ControlTowerV3 = Depends(get_control_tower),
    db: Session = Depends(get_db),
):
    """Health check endpoint with tier distribution."""
    stats = control_tower.get_tier_stats()
    
    # Test database connection
    try:
        db.execute(text("SELECT 1"))
        db_healthy = True
    except Exception:
        db_healthy = False
    
    overall_status = "healthy" if (stats["health"]["is_healthy"] and db_healthy) else "degraded"
    
    return HealthResponse(
        status=overall_status,
        tier_distribution=stats["distribution"],
        health_message=stats["health"]["message"],
    )


@app.get("/metrics/stats", response_model=StatsResponse)
async def get_stats(
    control_tower: ControlTowerV3 = Depends(get_control_tower),
    db: Session = Depends(get_db),
):
    """Get detailed detection statistics."""
    stats = control_tower.get_tier_stats()
    
    # Optionally save metrics snapshot to database
    try:
        metrics_repo = MetricsRepository(db)
        metrics_repo.create_snapshot({
            "total_detections": stats["total"],
            "tier1_count": stats["tier1_count"],
            "tier2_count": stats["tier2_count"],
            "tier3_count": stats["tier3_count"],
            "tier1_pct": stats["distribution"]["tier1_pct"],
            "tier2_pct": stats["distribution"]["tier2_pct"],
            "tier3_pct": stats["distribution"]["tier3_pct"],
            "is_healthy": stats["health"]["is_healthy"],
            "health_message": stats["health"]["message"],
        })
    except Exception as e:
        logger.warning("Could not save metrics snapshot: %s", e)
    
    return StatsResponse(
        total_detections=stats["total"],
        tier1_count=stats["tier1_count"],
        tier2_count=stats["tier2_count"],
        tier3_count=stats["tier3_count"],
        distribution=stats["distribution"],
        health=stats["health"],
    )


@app.get("/logs/recent")
async def get_recent_logs(
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Get recent detection logs."""
    if limit > 500:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit exceeds maximum of 500",
        )
    
    detection_repo = DetectionRepository(db)
    logs = detection_repo.get_recent(limit=limit)
    
    return {
        "total": len(logs),
        "logs": [
            {
                "id": log.id,
                "tier_used": log.tier_used,
                "action": log.action,
                "blocked": log.blocked,
                "confidence": log.confidence,
                "processing_time_ms": log.processing_time_ms,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ],
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler (no sensitive detail in production)."""
    logger.exception("Unhandled exception: %s", exc)
    body: Dict[str, Any] = {"error": "Internal server error"}
    if not _is_production():
        body["detail"] = str(exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=body,
    )
