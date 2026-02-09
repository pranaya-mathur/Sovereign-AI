"""Severity level definitions for LLM observability system.

Defines the impact classification for detected failures and determines
appropriate enforcement actions.
"""

from enum import Enum


class SeverityLevel(str, Enum):
    """Severity classification for detected failures.
    
    Determines the urgency and type of enforcement action required.
    Ordered from most to least severe.
    """
    
    CRITICAL = "critical"  # Immediate blocking required
    HIGH = "high"         # Strong warning or blocking
    MEDIUM = "medium"     # Warning with context
    LOW = "low"           # Log for monitoring
    INFO = "info"         # Informational only


class EnforcementAction(str, Enum):
    """Actions that can be taken in response to failures.
    
    Maps severity levels to concrete enforcement behaviors.
    """
    
    BLOCK = "block"       # Reject response entirely
    WARN = "warn"         # Return response with warning
    LOG = "log"           # Allow response, log for analysis
    ALLOW = "allow"       # No action needed


class SeverityConfig:
    """Maps severity levels to enforcement actions and behavior."""
    
    # Default severity-to-action mapping
    SEVERITY_TO_ACTION = {
        SeverityLevel.CRITICAL: EnforcementAction.BLOCK,
        SeverityLevel.HIGH: EnforcementAction.WARN,
        SeverityLevel.MEDIUM: EnforcementAction.WARN,
        SeverityLevel.LOW: EnforcementAction.LOG,
        SeverityLevel.INFO: EnforcementAction.ALLOW,
    }
    
    # User-facing messages for each severity
    SEVERITY_MESSAGES = {
        SeverityLevel.CRITICAL: "Response blocked due to critical safety issue.",
        SeverityLevel.HIGH: "Warning: Response may contain unreliable information.",
        SeverityLevel.MEDIUM: "Note: Response quality may be limited.",
        SeverityLevel.LOW: "Response logged for quality monitoring.",
        SeverityLevel.INFO: "",
    }
    
    @classmethod
    def get_action(cls, severity: SeverityLevel) -> EnforcementAction:
        """Get enforcement action for a given severity level."""
        return cls.SEVERITY_TO_ACTION.get(severity, EnforcementAction.LOG)
    
    @classmethod
    def get_message(cls, severity: SeverityLevel) -> str:
        """Get user-facing message for a given severity level."""
        return cls.SEVERITY_MESSAGES.get(severity, "")
    
    @classmethod
    def should_block(cls, severity: SeverityLevel) -> bool:
        """Determine if a severity level requires blocking."""
        return cls.get_action(severity) == EnforcementAction.BLOCK
