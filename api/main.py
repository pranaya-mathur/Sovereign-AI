"""FastAPI application entry point."""

import os
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, List

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.models import (
    DetectionRequest,
    DetectionResponse,
    HealthResponse,
    StatsResponse,
)
from api.dependencies import get_control_tower
from api.middleware import MetricsMiddleware, RequestLoggingMiddleware
from enforcement.control_tower_v3 import ControlTowerV3

# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management for FastAPI app."""
    # Startup
    logger.info("🚀 Starting LLM Observability API...")
    yield
    # Shutdown
    logger.info("🛑 Shutting down LLM Observability API...")


app = FastAPI(
    title="LLM Observability API",
    description="Production-grade LLM observability with 3-tier detection",
    version="4.0.0",
    lifespan=lifespan,
)

# CORS configuration
CORS_ORIGINS_RAW = os.getenv("CORS_ORIGINS", "")
if CORS_ORIGINS_RAW:
    allow_origins = [origin.strip() for origin in CORS_ORIGINS_RAW.split(",") if origin.strip()]
else:
    # Default to development-friendly origins if not specified
    allow_origins = ["http://localhost:3000", "http://localhost:5173", "http://localhost:8000"]

# Safety check: If allow_credentials is True, origins cannot be ["*"]
# Here we enforce explicit origins for security.
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add custom middleware
app.add_middleware(MetricsMiddleware)
app.add_middleware(RequestLoggingMiddleware)


@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint."""
    return {
        "service": "LLM Observability API",
        "version": "4.0.0",
        "status": "operational",
    }


@app.get("/health", response_model=HealthResponse)
async def health_check(control_tower: ControlTowerV3 = Depends(get_control_tower)):
    """Health check endpoint with tier distribution."""
    stats = control_tower.get_tier_stats()
    
    return HealthResponse(
        status="healthy" if stats["health"]["is_healthy"] else "degraded",
        tier_distribution=stats["distribution"],
        health_message=stats["health"]["message"],
    )


@app.get("/metrics/stats", response_model=StatsResponse)
async def get_stats(control_tower: ControlTowerV3 = Depends(get_control_tower)):
    """Get detailed detection statistics."""
    stats = control_tower.get_tier_stats()
    
    return StatsResponse(
        total_detections=stats["total"],
        tier1_count=stats["tier1_count"],
        tier2_count=stats["tier2_count"],
        tier3_count=stats["tier3_count"],
        distribution=stats["distribution"],
        health=stats["health"],
    )


@app.post("/detect", response_model=DetectionResponse)
async def detect(
    request: DetectionRequest,
    control_tower: ControlTowerV3 = Depends(get_control_tower),
):
    """Detect issues in LLM response using 3-tier system."""
    try:
        result = control_tower.evaluate_response(
            llm_response=request.llm_response,
            context=request.context or {},
        )
        
        return DetectionResponse(
            action=result.action.value,
            tier_used=result.tier_used,
            method=result.method,
            confidence=result.confidence,
            processing_time_ms=result.processing_time_ms,
            failure_class=result.failure_class.value if result.failure_class else None,
            severity=result.severity.value if result.severity else None,
            explanation=result.explanation,
            blocked=result.action.value == "block",
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Detection failed: {str(e)}",
        )


@app.post("/detect/batch", response_model=Dict[str, Any])
async def detect_batch(
    requests: list[DetectionRequest],
    control_tower: ControlTowerV3 = Depends(get_control_tower),
):
    """Batch detection for multiple LLM responses."""
    if len(requests) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batch size exceeds maximum of 100",
        )
    
    results = []
    for req in requests:
        try:
            result = control_tower.evaluate_response(
                llm_response=req.llm_response,
                context=req.context or {},
            )
            results.append({
                "action": result.action.value,
                "tier_used": result.tier_used,
                "method": result.method,
                "confidence": result.confidence,
                "processing_time_ms": result.processing_time_ms,
                "blocked": result.action.value == "block",
            })
        except Exception as e:
            results.append({
                "error": str(e),
                "blocked": False,
            })
    
    return {
        "total": len(requests),
        "results": results,
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": str(exc),
        },
    )
