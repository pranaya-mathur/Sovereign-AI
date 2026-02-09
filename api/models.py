"""Pydantic models for API request/response."""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class DetectionRequest(BaseModel):
    """Request model for LLM response detection."""
    
    llm_response: str = Field(
        ...,
        description="The LLM response text to analyze",
        min_length=1,
        max_length=50000,
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional context information (e.g., query, metadata)",
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "llm_response": "According to a study from Harvard, this approach is effective.",
                "context": {"query": "What's the best approach?"},
            }
        }


class DetectionResponse(BaseModel):
    """Response model for detection results."""
    
    action: str = Field(..., description="Action to take: allow, warn, block, log")
    tier_used: int = Field(..., description="Which tier was used (1, 2, or 3)")
    method: str = Field(..., description="Detection method used")
    confidence: float = Field(..., description="Confidence score (0.0 - 1.0)")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    failure_class: Optional[str] = Field(None, description="Type of failure detected")
    severity: Optional[str] = Field(None, description="Severity level")
    explanation: str = Field(..., description="Human-readable explanation")
    blocked: bool = Field(..., description="Whether response was blocked")
    
    class Config:
        json_schema_extra = {
            "example": {
                "action": "allow",
                "tier_used": 1,
                "method": "regex_strong",
                "confidence": 0.95,
                "processing_time_ms": 0.8,
                "failure_class": None,
                "severity": None,
                "explanation": "Strong citation pattern detected - legitimate source",
                "blocked": False,
            }
        }


class HealthResponse(BaseModel):
    """Response model for health check."""
    
    status: str = Field(..., description="Health status: healthy, degraded, unhealthy")
    tier_distribution: Dict[str, float] = Field(..., description="Current tier distribution percentages")
    health_message: str = Field(..., description="Health status message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "tier_distribution": {
                    "tier1_pct": 95.2,
                    "tier2_pct": 3.8,
                    "tier3_pct": 1.0,
                },
                "health_message": "✅ Healthy distribution",
            }
        }


class StatsResponse(BaseModel):
    """Response model for detection statistics."""
    
    total_detections: int = Field(..., description="Total number of detections")
    tier1_count: int = Field(..., description="Tier 1 detection count")
    tier2_count: int = Field(..., description="Tier 2 detection count")
    tier3_count: int = Field(..., description="Tier 3 detection count")
    distribution: Dict[str, float] = Field(..., description="Tier distribution percentages")
    health: Dict[str, Any] = Field(..., description="Health status information")


# Authentication Models

class LoginRequest(BaseModel):
    """Request model for user login."""
    
    username: str = Field(..., description="Username", min_length=3, max_length=50)
    password: str = Field(..., description="Password", min_length=6, max_length=100)
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "admin",
                "password": "admin123",
            }
        }


class LoginResponse(BaseModel):
    """Response model for successful login."""
    
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    username: str = Field(..., description="Username")
    role: str = Field(..., description="User role")
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "username": "admin",
                "role": "admin",
            }
        }


class UserResponse(BaseModel):
    """Response model for user information."""
    
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    role: str = Field(..., description="User role (admin, user, viewer)")
    rate_limit_tier: str = Field(..., description="Rate limit tier (free, pro, enterprise)")
    disabled: bool = Field(default=False, description="Whether user is disabled")
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "admin",
                "email": "admin@llm-obs.local",
                "role": "admin",
                "rate_limit_tier": "enterprise",
                "disabled": False,
            }
        }


class UserCreateRequest(BaseModel):
    """Request model for creating a new user."""
    
    username: str = Field(..., description="Username", min_length=3, max_length=50)
    password: str = Field(..., description="Password", min_length=6, max_length=100)
    email: Optional[str] = Field(None, description="Email address")
    role: str = Field(default="user", description="User role")
    rate_limit_tier: str = Field(default="free", description="Rate limit tier")
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "newuser",
                "password": "securepass123",
                "email": "newuser@example.com",
                "role": "user",
                "rate_limit_tier": "free",
            }
        }
