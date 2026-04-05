"""Policy configuration loader.

Loads and validates policy configuration from YAML file.
Provides type-safe access to policy rules.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

from contracts.failure_classes import FailureClass
from contracts.severity_levels import SeverityLevel, EnforcementAction


@dataclass
class Policy:
    """Policy for a failure class."""
    action: EnforcementAction
    severity: SeverityLevel
    reason: str


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
    
    def get_policy(self, failure_class: FailureClass) -> Policy:
        """Get complete policy for a failure class.
        
        Args:
            failure_class: FailureClass enum value
            
        Returns:
            Policy object with action, severity, and reason
        """
        # Convert enum to string for lookup
        failure_class_str = failure_class.value if isinstance(failure_class, FailureClass) else str(failure_class)
        
        return Policy(
            action=self.get_action(failure_class_str),
            severity=self.get_severity(failure_class_str),
            reason=self.get_reason(failure_class_str)
        )
    
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
    
    def get_tier1_cutoff(self) -> float:
        """Get the Tier 1 confidence cutoff."""
        thresholds = self._policy.get("thresholds", {})
        return thresholds.get("tier1_cutoff", 0.80)
    
    def get_tier2_cutoff(self) -> float:
        """Get the Tier 2 confidence cutoff."""
        thresholds = self._policy.get("thresholds", {})
        return thresholds.get("tier2_cutoff", 0.15)
    
    def get_uncertain_default(self) -> float:
        """Get the default confidence for uncertain (clean) requests."""
        thresholds = self._policy.get("thresholds", {})
        return thresholds.get("uncertain_default", 0.95)
    
    def get_observability_config(self) -> Dict[str, Any]:
        """Get OpenTelemetry observability configuration."""
        obs = self._policy.get("observability", {})
        return {
            "enabled": obs.get("enabled", False),
            "service_name": obs.get("service_name", "sovereign-ai-guard"),
            "otlp_endpoint": obs.get("otlp_endpoint", "http://localhost:4317"),
            "sampling_rate": obs.get("sampling_rate", 1.0),
            "export_timeout_seconds": obs.get("export_timeout_seconds", 10),
        }
    
    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM provider configuration."""
        providers = self._policy.get("llm_providers", {})
        return {
            "groq_model": providers.get("groq_model", "llama-3.3-70b-versatile"),
            "ollama_model": providers.get("ollama_model", "llama3.2"),
            "ollama_base_url": providers.get("ollama_base_url", "http://localhost:11434"),
        }
    
    def get_hardware_config(self) -> Dict[str, Any]:
        """Get hardware acceleration configuration."""
        hw = self._policy.get("hardware", {})
        return {
            "accelerator": hw.get("accelerator", "auto"),
            "precision": hw.get("precision", "fp16")
        }
    
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
