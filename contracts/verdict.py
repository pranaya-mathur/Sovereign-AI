"""Verdict structure - Governance decisions for LLM outputs.

Verdict ≠ Signal (critical distinction)

Signals = Evidence (what was detected)
Verdicts = Decisions (what to do about it)

Verdicts are:
- Deterministic
- Explainable
- Audit-friendly
- Enforcement-ready
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from contracts.severity_levels import SeverityLevel, EnforcementAction
from contracts.failure_classes import FailureClass


@dataclass
class FiredSignal:
    """Record of a signal that fired (detected an issue)."""
    
    signal_name: str
    confidence: float
    explanation: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "signal_name": self.signal_name,
            "confidence": self.confidence,
            "explanation": self.explanation,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class Verdict:
    """Governance decision for an LLM response.
    
    A verdict is the final judgment that determines what happens
    to an LLM response based on detected signals and policy rules.
    
    Attributes:
        verdict_id: Unique identifier for audit trail
        severity: Overall severity level (CRITICAL → INFO)
        action: What to do (BLOCK, WARN, LOG, ALLOW)
        failure_class: Primary failure type detected
        fired_signals: List of signals that triggered
        reason: Human-readable explanation
        confidence: Overall confidence in decision (0.0-1.0)
        policy_version: Version of policy used
        timestamp: When verdict was made
    """
    
    # Core decision
    verdict_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    severity: SeverityLevel = SeverityLevel.INFO
    action: EnforcementAction = EnforcementAction.ALLOW
    
    # Failure context
    failure_class: Optional[FailureClass] = None
    fired_signals: List[FiredSignal] = field(default_factory=list)
    
    # Explanation
    reason: str = "No issues detected"
    confidence: float = 1.0
    
    # Audit metadata
    policy_version: str = "1.0.0"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Additional context
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate verdict after initialization."""
        assert 0.0 <= self.confidence <= 1.0, "Confidence must be 0.0-1.0"
        assert self.verdict_id, "Verdict must have ID"
    
    @property
    def should_block(self) -> bool:
        """Check if verdict requires blocking response."""
        return self.action == EnforcementAction.BLOCK
    
    @property
    def signal_count(self) -> int:
        """Number of signals that fired."""
        return len(self.fired_signals)
    
    @property
    def highest_signal_confidence(self) -> float:
        """Get highest confidence among fired signals."""
        if not self.fired_signals:
            return 0.0
        return max(s.confidence for s in self.fired_signals)
    
    def get_signals_by_name(self, signal_name: str) -> List[FiredSignal]:
        """Get all fired signals matching a name."""
        return [s for s in self.fired_signals if s.signal_name == signal_name]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert verdict to dictionary for serialization.
        
        Returns audit-friendly structure suitable for:
        - Database storage
        - JSON serialization
        - Dashboard display
        - Compliance reporting
        """
        return {
            "verdict_id": self.verdict_id,
            "severity": self.severity.value,
            "action": self.action.value,
            "failure_class": self.failure_class.value if self.failure_class else None,
            "fired_signals": [s.to_dict() for s in self.fired_signals],
            "reason": self.reason,
            "confidence": self.confidence,
            "should_block": self.should_block,
            "signal_count": self.signal_count,
            "policy_version": self.policy_version,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }
    
    def to_audit_log(self) -> str:
        """Generate human-readable audit log entry."""
        lines = [
            f"[VERDICT {self.verdict_id}]",
            f"Timestamp: {self.timestamp.isoformat()}",
            f"Severity: {self.severity.value.upper()}",
            f"Action: {self.action.value.upper()}",
            f"Reason: {self.reason}",
            f"Confidence: {self.confidence:.2f}",
            f"Signals Fired: {self.signal_count}",
        ]
        
        if self.fired_signals:
            lines.append("\nFired Signals:")
            for signal in self.fired_signals:
                lines.append(
                    f"  - {signal.signal_name} "
                    f"(confidence={signal.confidence:.2f}): "
                    f"{signal.explanation}"
                )
        
        return "\n".join(lines)
    
    @classmethod
    def create_allow(cls, reason: str = "No issues detected") -> "Verdict":
        """Create an ALLOW verdict (no issues found)."""
        return cls(
            severity=SeverityLevel.INFO,
            action=EnforcementAction.ALLOW,
            reason=reason,
            confidence=1.0,
        )
    
    @classmethod
    def create_from_signal(
        cls,
        signal_name: str,
        signal_confidence: float,
        signal_explanation: str,
        severity: SeverityLevel,
        action: EnforcementAction,
        failure_class: FailureClass,
        reason: str,
        policy_version: str = "1.0.0",
    ) -> "Verdict":
        """Create verdict from a single fired signal."""
        fired_signal = FiredSignal(
            signal_name=signal_name,
            confidence=signal_confidence,
            explanation=signal_explanation,
        )
        
        return cls(
            severity=severity,
            action=action,
            failure_class=failure_class,
            fired_signals=[fired_signal],
            reason=reason,
            confidence=signal_confidence,
            policy_version=policy_version,
        )


@dataclass
class VerdictSummary:
    """Summary of multiple verdicts for dashboard/reporting.
    
    Used for aggregating verdict statistics over time.
    """
    
    total_verdicts: int = 0
    blocked_count: int = 0
    warned_count: int = 0
    allowed_count: int = 0
    
    # By severity
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    
    # By failure class
    failure_class_counts: Dict[str, int] = field(default_factory=dict)
    
    # Signal statistics
    most_fired_signals: Dict[str, int] = field(default_factory=dict)
    
    def add_verdict(self, verdict: Verdict) -> None:
        """Add a verdict to the summary statistics."""
        self.total_verdicts += 1
        
        # Count by action
        if verdict.action == EnforcementAction.BLOCK:
            self.blocked_count += 1
        elif verdict.action == EnforcementAction.WARN:
            self.warned_count += 1
        elif verdict.action == EnforcementAction.ALLOW:
            self.allowed_count += 1
        
        # Count by severity
        if verdict.severity == SeverityLevel.CRITICAL:
            self.critical_count += 1
        elif verdict.severity == SeverityLevel.HIGH:
            self.high_count += 1
        elif verdict.severity == SeverityLevel.MEDIUM:
            self.medium_count += 1
        elif verdict.severity == SeverityLevel.LOW:
            self.low_count += 1
        
        # Count failure classes
        if verdict.failure_class:
            fc = verdict.failure_class.value
            self.failure_class_counts[fc] = self.failure_class_counts.get(fc, 0) + 1
        
        # Count signals
        for signal in verdict.fired_signals:
            name = signal.signal_name
            self.most_fired_signals[name] = self.most_fired_signals.get(name, 0) + 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert summary to dictionary."""
        return {
            "total_verdicts": self.total_verdicts,
            "actions": {
                "blocked": self.blocked_count,
                "warned": self.warned_count,
                "allowed": self.allowed_count,
            },
            "severities": {
                "critical": self.critical_count,
                "high": self.high_count,
                "medium": self.medium_count,
                "low": self.low_count,
            },
            "failure_classes": self.failure_class_counts,
            "most_fired_signals": self.most_fired_signals,
        }
