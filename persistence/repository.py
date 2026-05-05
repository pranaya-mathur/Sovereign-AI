"""Repository pattern for database operations."""

import os
from typing import List, Optional
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from persistence.models import Detection, MetricsSnapshot
from rules.pii_india import redact_india_pii


class DetectionRepository:
    """Repository for detection log operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, detection_data: dict) -> Detection:
        """Create a new detection log entry.
        
        Args:
            detection_data: Dictionary with detection information
            
        Returns:
            Created Detection instance
        """
        payload = dict(detection_data)
        raw_response = payload.get("llm_response", "") or ""
        redacted_bundle = redact_india_pii(raw_response)
        payload["redacted_llm_response"] = redacted_bundle.get("redacted_text", "")

        # Optional strict minimization mode: do not persist raw response text at rest.
        if os.getenv("STORE_RAW_LLM_RESPONSE", "false").lower() != "true":
            payload["llm_response"] = payload["redacted_llm_response"]

        log = Detection(**payload)
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log
    
    def get_by_id(self, log_id: int) -> Optional[Detection]:
        """Get detection log by ID."""
        return self.db.query(Detection).filter(Detection.id == log_id).first()
    
    def get_recent(self, limit: int = 100) -> List[Detection]:
        """Get recent detection logs."""
        return (
            self.db.query(Detection)
            .order_by(desc(Detection.created_at))
            .limit(limit)
            .all()
        )
    
    def get_by_tier(self, tier: int, limit: int = 100) -> List[Detection]:
        """Get detection logs filtered by tier."""
        return (
            self.db.query(Detection)
            .filter(Detection.tier_used == tier)
            .order_by(desc(Detection.created_at))
            .limit(limit)
            .all()
        )
    
    def get_blocked_count(self, hours: int = 24) -> int:
        """Get count of blocked detections in the last N hours."""
        since = datetime.utcnow() - timedelta(hours=hours)
        return (
            self.db.query(func.count(Detection.id))
            .filter(Detection.blocked == True)
            .filter(Detection.created_at >= since)
            .scalar()
        )
    
    def get_tier_distribution(self, hours: int = 24) -> dict:
        """Get tier distribution for the last N hours."""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        total = (
            self.db.query(func.count(Detection.id))
            .filter(Detection.created_at >= since)
            .scalar()
        )
        
        if total == 0:
            return {"tier1": 0, "tier2": 0, "tier3": 0, "total": 0}
        
        tier_counts = (
            self.db.query(
                Detection.tier_used,
                func.count(Detection.id).label("count")
            )
            .filter(Detection.created_at >= since)
            .group_by(Detection.tier_used)
            .all()
        )
        
        distribution = {f"tier{t}": c for t, c in tier_counts}
        distribution["total"] = total
        
        return distribution


class MetricsRepository:
    """Repository for system metrics operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_snapshot(self, metrics_data: dict) -> MetricsSnapshot:
        """Create a new metrics snapshot.
        
        Args:
            metrics_data: Dictionary with metrics information
            
        Returns:
            Created MetricsSnapshot instance
        """
        metrics = MetricsSnapshot(**metrics_data)
        self.db.add(metrics)
        self.db.commit()
        self.db.refresh(metrics)
        return metrics
    
    def get_latest(self) -> Optional[MetricsSnapshot]:
        """Get the most recent metrics snapshot."""
        return (
            self.db.query(MetricsSnapshot)
            .order_by(desc(MetricsSnapshot.created_at))
            .first()
        )
    
    def get_time_series(self, hours: int = 24) -> List[MetricsSnapshot]:
        """Get metrics time series for the last N hours."""
        since = datetime.utcnow() - timedelta(hours=hours)
        return (
            self.db.query(MetricsSnapshot)
            .filter(MetricsSnapshot.created_at >= since)
            .order_by(MetricsSnapshot.created_at)
            .all()
        )
