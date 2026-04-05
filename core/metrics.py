import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict
from opentelemetry import metrics
from core.otel import SovereignOTel

try:
    from enforcement.control_tower_v2 import DetectionTier

    TIER_ENUM_AVAILABLE = True
except ImportError:
    # Fallback if control_tower_v2 not available yet
    from enum import Enum

    class DetectionTier(Enum):
        REGEX = 1
        EMBEDDING = 2
        LLM_AGENT = 3

    TIER_ENUM_AVAILABLE = False


@dataclass
class TierStats:
    """Statistics for a single detection tier."""

    count: int = 0
    total_latency_ms: float = 0.0
    min_latency_ms: float = float("inf")
    max_latency_ms: float = 0.0
    threat_count: int = 0

    def record(self, latency_ms: float, is_threat: bool = False) -> None:
        """Record a detection event."""
        self.count += 1
        self.total_latency_ms += latency_ms
        self.min_latency_ms = min(self.min_latency_ms, latency_ms)
        self.max_latency_ms = max(self.max_latency_ms, latency_ms)
        if is_threat:
            self.threat_count += 1

    def avg_latency_ms(self) -> float:
        """Calculate average latency."""
        return self.total_latency_ms / self.count if self.count > 0 else 0.0

    def threat_rate(self) -> float:
        """Calculate threat detection rate."""
        return self.threat_count / self.count if self.count > 0 else 0.0


class TierMetrics:
    """Track metrics across all detection tiers."""

    def __init__(self):
        """Initialize metrics tracking with OTel support."""
        from collections import defaultdict
        self.stats: Dict[DetectionTier, TierStats] = defaultdict(TierStats)
        self.start_time = time.time()
        
        # OTel Metrics initialization
        self.otel_singleton = SovereignOTel()
        self.meter = self.otel_singleton.get_meter("sovereign-metrics")
        
        self.request_counter = self.meter.create_counter(
            "sovereign.requests.total",
            description="Total detection requests"
        )
        self.latency_histogram = self.meter.create_histogram(
            "sovereign.latency.ms",
            unit="ms",
            description="Detection latency per tier"
        )
        self.threat_counter = self.meter.create_counter(
            "sovereign.threats.total",
            description="Total threats detected per tier"
        )

    def record_detection(
        self, tier: DetectionTier, latency_ms: float, is_threat: bool = False,
        failure_class: Optional[str] = None
    ) -> None:
        """Record a detection event.

        Args:
            tier: Detection tier used
            latency_ms: Detection latency in milliseconds
            is_threat: Whether a threat was detected
            failure_class: Category of the threat detected
        """
        self.stats[tier].record(latency_ms, is_threat)
        
        # Record OTel Metrics
        labels = {"tier": tier.name}
        if failure_class:
            labels["failure_class"] = failure_class
            
        self.request_counter.add(1, labels)
        self.latency_histogram.record(latency_ms, labels)
        if is_threat:
            self.threat_counter.add(1, labels)

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all tier metrics."""
        total_count = sum(stats.count for stats in self.stats.values())
        uptime_seconds = time.time() - self.start_time

        summary = {
            "total_requests": total_count,
            "uptime_seconds": uptime_seconds,
            "requests_per_second": total_count / uptime_seconds if uptime_seconds > 0 else 0.0,
            "tiers": {},
        }

        for tier, stats in self.stats.items():
            if stats.count > 0:
                summary["tiers"][tier.name] = {
                    "count": stats.count,
                    "percentage": (stats.count / total_count * 100) if total_count > 0 else 0.0,
                    "avg_latency_ms": stats.avg_latency_ms(),
                    "min_latency_ms": stats.min_latency_ms,
                    "max_latency_ms": stats.max_latency_ms,
                    "threat_count": stats.threat_count,
                    "threat_rate": stats.threat_rate(),
                }

        return summary

    def reset(self) -> None:
        """Reset all metrics."""
        self.stats.clear()
        self.start_time = time.time()

    def get_tier_distribution(self) -> Dict[str, float]:
        """Get percentage distribution across tiers."""
        total = sum(stats.count for stats in self.stats.values())
        if total == 0:
            return {}

        return {
            tier.name: (stats.count / total * 100) for tier, stats in self.stats.items()
        }
