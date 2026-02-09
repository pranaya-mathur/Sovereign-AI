"""Control Tower V3 - Integrated 3-tier detection system.

Combines all detection methods:
- Tier 1: Fast regex patterns (95% of cases)
- Tier 2: Semantic embeddings (4% of cases)
- Tier 3: LLM agents (1% of cases)
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import time

from config.policy_loader import PolicyLoader
from contracts.severity_levels import SeverityLevel, EnforcementAction
from enforcement.tier_router import TierRouter, TierDecision
from signals.embeddings.semantic_detector import SemanticDetector
from agent.langgraph_agent import PromptInjectionAgent


@dataclass
class ControlTowerResult:
    """Result from Control Tower evaluation."""
    failure_class: Optional[str]
    severity: str
    action: str
    confidence: float
    reason: str
    should_block: bool
    tier_used: int
    tier_reason: str
    processing_time_ms: float
    method: str


class ControlTowerV3:
    """3-tier integrated detection and enforcement system."""
    
    def __init__(self, policy_path: str = "config/policy.yaml"):
        """
        Initialize Control Tower V3 with all detection tiers.
        
        Args:
            policy_path: Path to policy configuration file
        """
        self.policy = PolicyLoader(policy_path)
        self.tier_router = TierRouter()
        
        # Initialize Tier 2 (semantic detection)
        try:
            self.semantic_detector = SemanticDetector()
            self.tier2_available = True
        except Exception as e:
            print(f"Warning: Semantic detector unavailable: {e}")
            self.tier2_available = False
        
        # Initialize Tier 3 (LLM agents)
        try:
            self.llm_agent = PromptInjectionAgent()
            self.tier3_available = True
        except Exception as e:
            print(f"Warning: LLM agent unavailable: {e}")
            self.tier3_available = False
    
    def evaluate(
        self,
        prompt: str,
        response: str,
        metadata: Dict[str, Any],
        signal_result: Dict[str, Any]
    ) -> ControlTowerResult:
        """
        Evaluate response using 3-tier detection system.
        
        Args:
            prompt: User prompt
            response: LLM response
            metadata: Additional context
            signal_result: Initial signal detection result (Tier 1)
            
        Returns:
            ControlTowerResult with enforcement decision
        """
        start_time = time.time()
        
        # Step 1: Route to appropriate tier
        tier_decision = self.tier_router.route(signal_result)
        
        # Step 2: Execute detection based on tier
        if tier_decision.tier == 1:
            result = self._tier1_evaluation(signal_result, tier_decision)
        elif tier_decision.tier == 2:
            result = self._tier2_evaluation(prompt, response, metadata, signal_result, tier_decision)
        else:  # tier 3
            result = self._tier3_evaluation(prompt, response, metadata, signal_result, tier_decision)
        
        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000  # Convert to ms
        result.processing_time_ms = processing_time
        
        return result
    
    def _tier1_evaluation(
        self,
        signal_result: Dict[str, Any],
        tier_decision: TierDecision
    ) -> ControlTowerResult:
        """Tier 1: Fast deterministic regex-based evaluation."""
        failure_detected = signal_result.get("value", False)
        failure_class = signal_result.get("failure_class")
        confidence = signal_result.get("confidence", 0.0)
        
        if failure_detected and failure_class:
            # Apply policy
            policy_decision = self.policy.get_policy_decision(failure_class, confidence)
            
            return ControlTowerResult(
                failure_class=failure_class,
                severity=policy_decision.severity.value,
                action=policy_decision.action.value,
                confidence=policy_decision.confidence,
                reason=policy_decision.reason,
                should_block=(policy_decision.action == EnforcementAction.BLOCK),
                tier_used=1,
                tier_reason=tier_decision.reason,
                processing_time_ms=0.0,  # Will be set later
                method=signal_result.get("method", "regex")
            )
        else:
            # No failure detected
            return ControlTowerResult(
                failure_class=None,
                severity="none",
                action="allow",
                confidence=confidence,
                reason="No failure patterns detected",
                should_block=False,
                tier_used=1,
                tier_reason=tier_decision.reason,
                processing_time_ms=0.0,
                method=signal_result.get("method", "regex")
            )
    
    def _tier2_evaluation(
        self,
        prompt: str,
        response: str,
        metadata: Dict[str, Any],
        signal_result: Dict[str, Any],
        tier_decision: TierDecision
    ) -> ControlTowerResult:
        """Tier 2: Semantic embedding-based evaluation."""
        if not self.tier2_available:
            # Fallback to Tier 1 if Tier 2 unavailable
            return self._tier1_evaluation(signal_result, tier_decision)
        
        failure_class = signal_result.get("failure_class", "missing_grounding")
        
        # Run semantic detection
        semantic_result = self.semantic_detector.detect(
            response=response,
            failure_class=failure_class,
            threshold=0.75
        )
        
        if semantic_result["detected"]:
            # Apply policy
            policy_decision = self.policy.get_policy_decision(
                failure_class,
                semantic_result["confidence"]
            )
            
            return ControlTowerResult(
                failure_class=failure_class,
                severity=policy_decision.severity.value,
                action=policy_decision.action.value,
                confidence=semantic_result["confidence"],
                reason=f"Semantic detection: {policy_decision.reason}",
                should_block=(policy_decision.action == EnforcementAction.BLOCK),
                tier_used=2,
                tier_reason=tier_decision.reason,
                processing_time_ms=0.0,
                method="semantic"
            )
        else:
            # No failure detected
            return ControlTowerResult(
                failure_class=None,
                severity="none",
                action="allow",
                confidence=semantic_result["confidence"],
                reason="Semantic analysis passed",
                should_block=False,
                tier_used=2,
                tier_reason=tier_decision.reason,
                processing_time_ms=0.0,
                method="semantic"
            )
    
    def _tier3_evaluation(
        self,
        prompt: str,
        response: str,
        metadata: Dict[str, Any],
        signal_result: Dict[str, Any],
        tier_decision: TierDecision
    ) -> ControlTowerResult:
        """Tier 3: LLM agent-based evaluation with multi-step reasoning."""
        if not self.tier3_available:
            # Fallback to Tier 2 if Tier 3 unavailable
            return self._tier2_evaluation(prompt, response, metadata, signal_result, tier_decision)
        
        # Run LLM agent analysis
        agent_result = self.llm_agent.analyze(
            prompt=prompt,
            context={"response": response, "metadata": metadata}
        )
        
        decision = agent_result.get("decision", "ALLOW")
        confidence = agent_result.get("confidence", 0.5)
        reasoning = agent_result.get("reasoning", "LLM agent analysis")
        cached = agent_result.get("cached", False)
        
        if decision == "BLOCK":
            failure_class = "prompt_injection"  # Agent detects prompt injection
            policy_decision = self.policy.get_policy_decision(failure_class, confidence)
            
            return ControlTowerResult(
                failure_class=failure_class,
                severity=policy_decision.severity.value,
                action="block",
                confidence=confidence,
                reason=f"LLM Agent: {reasoning}" + (" [cached]" if cached else ""),
                should_block=True,
                tier_used=3,
                tier_reason=tier_decision.reason,
                processing_time_ms=0.0,
                method="llm_agent"
            )
        else:
            # No failure detected
            return ControlTowerResult(
                failure_class=None,
                severity="none",
                action="allow",
                confidence=confidence,
                reason=f"LLM Agent: {reasoning}" + (" [cached]" if cached else ""),
                should_block=False,
                tier_used=3,
                tier_reason=tier_decision.reason,
                processing_time_ms=0.0,
                method="llm_agent"
            )
    
    def get_tier_stats(self) -> Dict[str, Any]:
        """Get tier distribution statistics."""
        distribution = self.tier_router.get_distribution()
        health_ok, health_msg = self.tier_router.check_distribution_health()
        
        return {
            "distribution": distribution,
            "health": {
                "is_healthy": health_ok,
                "message": health_msg
            },
            "tier_availability": {
                "tier1": True,  # Always available
                "tier2": self.tier2_available,
                "tier3": self.tier3_available
            }
        }
    
    def reset_tier_stats(self):
        """Reset tier statistics."""
        self.tier_router.reset_stats()
