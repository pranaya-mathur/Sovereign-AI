"""Policy configuration loader.

Loads and validates policy configuration from YAML file.
Provides type-safe access to policy rules.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional

from contracts.failure_classes import FailureClass
from contracts.severity_levels import SeverityLevel, EnforcementAction


class PolicyLoader:
    """Loads and provides access to policy configuration."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize policy loader.
        
        Args:
            config_path: Path to policy.yaml file. 
                        If None, uses default location.
        """
        if config_path is None:
            # Default to config/policy.yaml relative to this file
            config_dir = Path(__file__).parent
            config_path = config_dir / "policy.yaml"
        
        self.config_path = Path(config_path)
        self._policy: Dict[str, Any] = {}
        self._load_policy()
    
    def _load_policy(self) -> None:
        """Load policy configuration from YAML file."""
        try:
            # Use UTF-8 encoding explicitly to handle emojis and special chars
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._policy = yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Policy file not found: {self.config_path}"
            )
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in policy file: {e}")
    
    def get_severity(self, failure_class: str) -> SeverityLevel:
        """Get severity level for a failure class.
        
        Args:
            failure_class: Name of the failure class
            
        Returns:
            SeverityLevel enum value
        """
        policies = self._policy.get("failure_policies", {})
        policy = policies.get(failure_class, {})
        severity_str = policy.get("severity", "low")
        
        try:
            return SeverityLevel(severity_str)
        except ValueError:
            return SeverityLevel.LOW
    
    def get_action(self, failure_class: str) -> EnforcementAction:
        """Get enforcement action for a failure class.
        
        Args:
            failure_class: Name of the failure class
            
        Returns:
            EnforcementAction enum value
        """
        policies = self._policy.get("failure_policies", {})
        policy = policies.get(failure_class, {})
        action_str = policy.get("action", "log")
        
        try:
            return EnforcementAction(action_str)
        except ValueError:
            return EnforcementAction.LOG
    
    def get_reason(self, failure_class: str) -> str:
        """Get human-readable reason for a failure class policy.
        
        Args:
            failure_class: Name of the failure class
            
        Returns:
            Reason string from policy
        """
        policies = self._policy.get("failure_policies", {})
        policy = policies.get(failure_class, {})
        return policy.get("reason", "Policy violation detected")
    
    def get_threshold(self, severity: SeverityLevel) -> float:
        """Get confidence threshold for a severity level.
        
        Args:
            severity: Severity level
            
        Returns:
            Confidence threshold (0.0 to 1.0)
        """
        thresholds = self._policy.get("thresholds", {})
        return thresholds.get(severity.value, 0.5)
    
    def should_enforce(
        self, 
        failure_class: str, 
        confidence: float
    ) -> bool:
        """Determine if enforcement should be applied based on confidence.
        
        Args:
            failure_class: Name of the failure class
            confidence: Confidence score (0.0 to 1.0)
            
        Returns:
            True if confidence exceeds threshold for this failure class
        """
        severity = self.get_severity(failure_class)
        threshold = self.get_threshold(severity)
        return confidence >= threshold
    
    def get_message_template(self, action: EnforcementAction) -> str:
        """Get user-facing message template for an action.
        
        Args:
            action: Enforcement action
            
        Returns:
            Message template string
        """
        messages = self._policy.get("messages", {})
        return messages.get(action.value, "Action: {reason}")
    
    @property
    def version(self) -> str:
        """Get policy configuration version."""
        return self._policy.get("version", "unknown")
    
    @property
    def strict_mode(self) -> bool:
        """Check if strict mode is enabled."""
        global_config = self._policy.get("global", {})
        return global_config.get("strict_mode", False)


# Global policy loader instance
_policy_loader: Optional[PolicyLoader] = None


def get_policy_loader() -> PolicyLoader:
    """Get or create global policy loader instance.
    
    Returns:
        Singleton PolicyLoader instance
    """
    global _policy_loader
    if _policy_loader is None:
        _policy_loader = PolicyLoader()
    return _policy_loader
