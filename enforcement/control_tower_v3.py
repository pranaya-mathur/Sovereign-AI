"""Control Tower V3 - Integrated 3-tier detection system.

Combines all detection methods:
- Tier 1: Fast regex patterns (95% of cases)
- Tier 2: Semantic embeddings (4% of cases)  
- Tier 3: LLM agents (1% of cases)
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
import time
import re
import signal

from config.policy_loader import PolicyLoader
from contracts.severity_levels import SeverityLevel, EnforcementAction
from contracts.failure_classes import FailureClass
from enforcement.tier_router import TierRouter, TierDecision
from signals.embeddings.semantic_detector import SemanticDetector
from signals.regex.pattern_library import PatternLibrary


@dataclass
class DetectionResult:
    """Result from detection evaluation."""
    action: EnforcementAction
    tier_used: int
    method: str
    confidence: float
    processing_time_ms: float
    failure_class: Optional[FailureClass] = None
    severity: Optional[SeverityLevel] = None
    explanation: str = ""


class TimeoutException(Exception):
    """Exception raised when regex takes too long."""
    pass


def timeout_handler(signum, frame):
    """Signal handler for regex timeout."""
    raise TimeoutException("Regex timeout")


class ControlTowerV3:
    """3-tier integrated detection and enforcement system."""
    
    def __init__(self, policy_path: str = "config/policy.yaml", enable_tier3: bool = False):
        """
        Initialize Control Tower V3 with all detection tiers.
        
        Args:
            policy_path: Path to policy configuration file
            enable_tier3: Enable Tier 3 LLM agent (default: False, as it's expensive)
        """
        self.policy = PolicyLoader(policy_path)
        self.tier_router = TierRouter()
        
        # Load Tier 1 patterns
        self.patterns = PatternLibrary.get_all_patterns()
        print(f"✅ Loaded {len(self.patterns)} Tier 1 regex patterns")
        
        # Initialize Tier 2 (semantic detection)
        try:
            self.semantic_detector = SemanticDetector()
            self.tier2_available = True
            print("✅ Tier 2 semantic detector initialized")
        except Exception as e:
            print(f"⚠️ Warning: Semantic detector unavailable: {e}")
            self.tier2_available = False
            self.semantic_detector = None
        
        # Initialize Tier 3 (LLM agents) - only if enabled
        self.llm_agent = None
        if enable_tier3:
            try:
                from agent.langgraph_agent import PromptInjectionAgent
                self.llm_agent = PromptInjectionAgent()
                self.tier3_available = True
                print("✅ Tier 3 LLM agent initialized")
            except Exception as e:
                print(f"⚠️ Warning: LLM agent initialization failed: {e}")
                print("   Make sure Groq API key is set in .env or Ollama is running")
                self.tier3_available = False
        else:
            self.tier3_available = False
            print("ℹ️ Tier 3 LLM agent disabled (set enable_tier3=True in dependencies.py to enable)")
    
    def _safe_regex_search(self, pattern: re.Pattern, text: str, timeout_seconds: float = 0.5) -> Optional[re.Match]:
        """Safely search with regex with timeout protection.
        
        Args:
            pattern: Compiled regex pattern
            text: Text to search
            timeout_seconds: Maximum time allowed for search
            
        Returns:
            Match object or None if no match/timeout
        """
        try:
            # Set alarm for timeout (Unix only)
            if hasattr(signal, 'SIGALRM'):
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.setitimer(signal.ITIMER_REAL, timeout_seconds)
            
            match = pattern.search(text)
            
            # Cancel alarm
            if hasattr(signal, 'SIGALRM'):
                signal.setitimer(signal.ITIMER_REAL, 0)
            
            return match
        except TimeoutException:
            # Regex took too long - return None
            return None
        except Exception as e:
            # Any other error - return None
            return None
    
    def _tier1_detect(self, text: str) -> Dict[str, Any]:
        """
        Tier 1: Fast regex pattern matching with safety checks.
        
        Args:
            text: Text to analyze
            
        Returns:
            Detection result dict with confidence, failure_class, method
        """
        # Handle empty or very short text
        if not text or len(text.strip()) < 3:
            return {
                "confidence": 0.5,
                "failure_class": None,
                "method": "regex_skipped",
                "should_allow": True,
                "explanation": "Text too short for analysis"
            }
        
        # CRITICAL FIX: Truncate long text to prevent catastrophic backtracking
        # Regex on 500+ chars with .* can cause exponential time
        original_length = len(text)
        if original_length > 500:
            text = text[:500]
            print(f"⚠️ Warning: Truncated text from {original_length} to 500 chars for regex safety")
        
        # Handle very long text (potential DOS) - now 1000 char limit
        if original_length > 10000:
            return {
                "confidence": 0.7,
                "failure_class": FailureClass.PROMPT_INJECTION,
                "method": "regex_length_check",
                "should_allow": False,
                "explanation": f"Text too long ({original_length} chars) - potential DOS attack"
            }
        
        # Check for strong anti-patterns (allow patterns)
        for pattern in self.patterns:
            if pattern.failure_class is None:  # Allow patterns
                try:
                    match = self._safe_regex_search(pattern.compiled, text)
                    if match:
                        return {
                            "confidence": pattern.confidence,
                            "failure_class": None,
                            "method": "regex_anti",
                            "pattern_name": pattern.name,
                            "should_allow": True,
                            "explanation": f"Strong indicator detected: {pattern.description}"
                        }
                except Exception as e:
                    # Skip patterns that cause errors
                    continue
        
        # Check for failure patterns (block patterns)
        best_match = None
        for pattern in self.patterns:
            if pattern.failure_class is not None:
                try:
                    match = self._safe_regex_search(pattern.compiled, text)
                    if match:
                        if best_match is None or pattern.confidence > best_match["confidence"]:
                            best_match = {
                                "confidence": pattern.confidence,
                                "failure_class": pattern.failure_class,
                                "method": "regex_strong",
                                "pattern_name": pattern.name,
                                "should_allow": False,
                                "match_text": match.group(0)[:100],
                                "explanation": f"{pattern.failure_class.value}: {pattern.description}"
                            }
                except Exception as e:
                    # Skip patterns that cause errors
                    continue
        
        if best_match:
            return best_match
        
        # No strong patterns matched - gray zone
        return {
            "confidence": 0.5,
            "failure_class": None,
            "method": "regex_uncertain",
            "should_allow": None,  # Uncertain
            "explanation": "No strong patterns detected - needs semantic analysis"
        }
    
    def _tier2_detect(self, text: str, tier1_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tier 2: Semantic embedding similarity.
        
        Args:
            text: Text to analyze
            tier1_result: Result from Tier 1
            
        Returns:
            Detection result dict
        """
        if not self.tier2_available or self.semantic_detector is None:
            # Fallback - allow but with low confidence
            return {
                "confidence": 0.5,
                "failure_class": None,
                "method": "semantic_unavailable",
                "should_allow": True,
                "explanation": "Semantic detector unavailable - allowing conservatively"
            }
        
        # SAFETY: Truncate very long text for semantic analysis
        if len(text) > 1000:
            text = text[:1000]
        
        try:
            # Check against ALL failure classes for comprehensive detection
            max_similarity = 0.0
            detected_class = None
            detection_details = []
            
            # Security patterns get lower threshold (more sensitive)
            security_classes = ["prompt_injection", "bias", "toxicity"]
            general_classes = ["fabricated_concept", "missing_grounding", "overconfidence", 
                             "domain_mismatch", "fabricated_fact"]
            
            # Check security patterns first (higher priority)
            for failure_class in security_classes:
                try:
                    result = self.semantic_detector.detect(
                        response=text,
                        failure_class=failure_class,
                        threshold=0.65  # Lower threshold for security = more sensitive
                    )
                    confidence = result["confidence"]
                    detection_details.append(f"{failure_class}:{confidence:.2f}")
                    
                    if confidence > max_similarity:
                        max_similarity = confidence
                        if result["detected"]:
                            detected_class = failure_class
                except Exception as e:
                    continue
            
            # Then check general failure patterns
            for failure_class in general_classes:
                try:
                    result = self.semantic_detector.detect(
                        response=text,
                        failure_class=failure_class,
                        threshold=0.70
                    )
                    confidence = result["confidence"]
                    detection_details.append(f"{failure_class}:{confidence:.2f}")
                    
                    if confidence > max_similarity:
                        max_similarity = confidence
                        if result["detected"]:
                            detected_class = failure_class
                except Exception as e:
                    continue
            
            # Convert string to FailureClass enum
            failure_class_enum = None
            if detected_class:
                try:
                    # Map semantic class names to FailureClass enum
                    class_mapping = {
                        "prompt_injection": FailureClass.PROMPT_INJECTION,
                        "bias": FailureClass.BIAS,
                        "toxicity": FailureClass.TOXICITY,
                        "fabricated_concept": FailureClass.FABRICATED_CONCEPT,
                        "missing_grounding": FailureClass.MISSING_GROUNDING,
                        "overconfidence": FailureClass.OVERCONFIDENCE,
                        "domain_mismatch": FailureClass.DOMAIN_MISMATCH,
                        "fabricated_fact": FailureClass.FABRICATED_FACT,
                    }
                    failure_class_enum = class_mapping.get(detected_class)
                except Exception as e:
                    print(f"Warning: Could not map failure class: {e}")
            
            explanation = f"Semantic analysis: {', '.join(detection_details[:3])}" if detection_details else "Semantic analysis completed"
            
            return {
                "confidence": max_similarity,
                "failure_class": failure_class_enum,
                "method": "semantic",
                "should_allow": detected_class is None,
                "explanation": explanation
            }
        except Exception as e:
            print(f"Warning: Semantic detection error: {e}")
            return {
                "confidence": 0.5,
                "failure_class": None,
                "method": "semantic_error",
                "should_allow": True,
                "explanation": f"Semantic detection failed - allowing conservatively"
            }
    
    def _tier3_detect(self, text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tier 3: LLM agent reasoning.
        
        Args:
            text: Text to analyze
            context: Context information
            
        Returns:
            Detection result dict
        """
        if not self.tier3_available or self.llm_agent is None:
            # Conservative fallback - allow but log
            return {
                "confidence": 0.5,
                "failure_class": None,
                "method": "llm_unavailable",
                "should_allow": True,
                "explanation": "LLM agent unavailable - allowing conservatively"
            }
        
        # SAFETY: Truncate very long text for LLM
        if len(text) > 2000:
            text = text[:2000]
        
        try:
            # Use LLM agent for deep analysis
            agent_result = self.llm_agent.analyze(text, context)
            
            # Convert decision to boolean
            should_block = agent_result.get("decision") == "BLOCK"
            
            return {
                "confidence": agent_result.get("confidence", 0.7),
                "failure_class": FailureClass.PROMPT_INJECTION if should_block else None,
                "method": "llm_agent",
                "should_allow": not should_block,
                "explanation": agent_result.get("reasoning", "LLM agent analysis completed")
            }
        except Exception as e:
            print(f"Warning: LLM agent failed: {e}")
            return {
                "confidence": 0.5,
                "failure_class": None,
                "method": "llm_error",
                "should_allow": True,
                "explanation": f"LLM agent error - allowing conservatively"
            }
    
    def evaluate_response(
        self,
        llm_response: str,
        context: Dict[str, Any] = None
    ) -> DetectionResult:
        """
        Evaluate LLM response using 3-tier detection.
        
        Args:
            llm_response: The LLM response text to analyze
            context: Optional context information
            
        Returns:
            DetectionResult with enforcement decision
        """
        start_time = time.time()
        context = context or {}
        
        try:
            # Tier 1: Fast regex detection
            tier1_result = self._tier1_detect(llm_response)
            
            # Route to appropriate tier based on confidence
            tier_decision = self.tier_router.route(tier1_result)
            
            # Execute appropriate tier
            if tier_decision.tier == 1:
                final_result = tier1_result
            elif tier_decision.tier == 2:
                final_result = self._tier2_detect(llm_response, tier1_result)
            else:  # Tier 3
                final_result = self._tier3_detect(llm_response, context)
            
            # Determine action based on result
            failure_class = final_result.get("failure_class")
            confidence = final_result.get("confidence", 0.5)
            should_allow = final_result.get("should_allow")
            
            # Get policy for failure class
            if failure_class:
                policy = self.policy.get_policy(failure_class)
                action = policy.action
                severity = policy.severity
            else:
                # No failure detected - determine based on confidence
                if should_allow is False:
                    action = EnforcementAction.WARN
                    severity = SeverityLevel.MEDIUM
                else:
                    action = EnforcementAction.ALLOW
                    severity = None
            
            processing_time = (time.time() - start_time) * 1000
            
            return DetectionResult(
                action=action,
                tier_used=tier_decision.tier,
                method=final_result.get("method", "unknown"),
                confidence=confidence,
                processing_time_ms=processing_time,
                failure_class=failure_class,
                severity=severity,
                explanation=final_result.get("explanation", "Analysis completed")
            )
        
        except Exception as e:
            # Fallback for any unexpected errors
            print(f"Error in evaluate_response: {e}")
            processing_time = (time.time() - start_time) * 1000
            return DetectionResult(
                action=EnforcementAction.ALLOW,
                tier_used=1,
                method="error_fallback",
                confidence=0.5,
                processing_time_ms=processing_time,
                failure_class=None,
                severity=None,
                explanation=f"Detection error - allowing conservatively: {str(e)[:100]}"
            )
    
    def get_tier_stats(self) -> Dict[str, Any]:
        """
        Get tier distribution statistics.
        
        Returns:
            Dict with complete statistics including:
            - total: Total number of detections
            - tier1_count, tier2_count, tier3_count: Counts per tier
            - distribution: Percentage distribution
            - health: Health status
        """
        # Get raw stats from tier router
        tier_stats = self.tier_router.tier_stats
        distribution = self.tier_router.get_distribution()
        health_ok, health_msg = self.tier_router.check_distribution_health()
        
        return {
            # Total and counts
            "total": tier_stats["total"],
            "tier1_count": tier_stats["tier1"],
            "tier2_count": tier_stats["tier2"],
            "tier3_count": tier_stats["tier3"],
            
            # Distribution percentages
            "distribution": {
                "tier1_pct": distribution["tier1_pct"],
                "tier2_pct": distribution["tier2_pct"],
                "tier3_pct": distribution["tier3_pct"],
            },
            
            # Health status
            "health": {
                "is_healthy": health_ok,
                "message": health_msg
            },
            
            # Tier availability
            "tier_availability": {
                "tier1": True,
                "tier2": self.tier2_available,
                "tier3": self.tier3_available
            }
        }
    
    def reset_tier_stats(self):
        """Reset tier statistics."""
        self.tier_router.reset_stats()
