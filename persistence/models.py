"""SQLAlchemy database models."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Detection(Base):
    """Detection log model."""
    __tablename__ = "detections"
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String, unique=True, index=True)
    llm_response = Column(Text, nullable=False)
    context = Column(JSON, nullable=True)
    action = Column(String, nullable=False)
    tier_used = Column(Integer, nullable=False)
    method = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    processing_time_ms = Column(Float, nullable=False)
    failure_class = Column(String, nullable=True)
    severity = Column(String, nullable=True)
    explanation = Column(Text, nullable=True)
    blocked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class MetricsSnapshot(Base):
    """Metrics snapshot model."""
    __tablename__ = "metrics_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    total_detections = Column(Integer, nullable=False)
    tier1_count = Column(Integer, nullable=False)
    tier2_count = Column(Integer, nullable=False)
    tier3_count = Column(Integer, nullable=False)
    tier1_pct = Column(Float, nullable=False)
    tier2_pct = Column(Float, nullable=False)
    tier3_pct = Column(Float, nullable=False)
    is_healthy = Column(Boolean, default=True)
    health_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class User(Base):
    """User model for authentication."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user")  # admin, user, viewer
    rate_limit_tier = Column(String, default="free")  # free, pro, enterprise
    disabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
