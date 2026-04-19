"""Control Tower V3 - Integrated 3-tier detection system.

Combines all detection methods:
- Tier 1: Fast regex patterns (95% of cases)
- Tier 2: Semantic embeddings (4% of cases)  
- Tier 3: LLM agents (1% of cases)
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field
import logging
import time
import re
from collections import Counter

from core.utils import run_with_timeout, TimeoutException
from core.otel import otel_manager
from config.policy_loader import PolicyLoader
from contracts.severity_levels import SeverityLevel, EnforcementAction
from contracts.failure_classes import FailureClass
from core.metrics import TierMetrics, DetectionTier
from enforcement.tier_router import TierRouter, TierDecision
from enforcement.dialog_orchestrator import DialogManager
from signals.embeddings.semantic_detector import SemanticDetector
from signals.regex.pattern_library import PatternLibrary
from persistence.compliance_jsonl import ComplianceJSONLLogger, sha256_text
from providers.external_moderation import run_external_moderation_pipeline
from rules.pii_india import redact_india_pii
from enforcement.output_validator import run_output_validation
from enforcement.agentic_rails import agentic_preflight

logger = logging.getLogger(__name__)

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
    findings: list[Dict[str, Any]] = field(default_factory=list) # Multi-label support
    explanation: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

# Removed Unix-only TimeoutException and timeout_handler

def is_pathological_input_early(text: str) -> tuple[bool, str, float]:
    """Early detection of pathological patterns before expensive processing.
    
    This catches patterns that would timeout or waste CPU in Tier 2.
    
    Args:
        text: Input text to check
        
    Returns:
        Tuple of (is_pathological, explanation, confidence)
    """
    if not text or len(text) < 10:
        return False, "", 0.0
    
    # Check 1: Excessive repetition (>80% same character)
    if len(text) > 50:
        char_counts = Counter(text)
        if char_counts:
            most_common_char, most_common_count = char_counts.most_common(1)[0]
            repetition_ratio = most_common_count / len(text)
            
            if repetition_ratio > 0.8:
                return True, f"Excessive repetition detected ({repetition_ratio*100:.1f}%)", 0.95
    
    # Check 2: Very low character diversity
    if len(text) > 100:
        unique_chars = len(set(text))
        if unique_chars < 5:
            return True, f"Low character diversity ({unique_chars} unique chars)", 0.95
    
    # Check 3: Repeated character patterns (aaaa, bbbb)
    if re.search(r'(.)\1{20,}', text):
        return True, "Character repetition pattern detected", 0.95
    
    # Check 4: Known attack patterns (SQL, XSS, path traversal)
    attack_patterns = [
        (r'SELECT .* FROM', "SQL injection pattern"),
        (r'UNION SELECT', "SQL union attack"),
        (r'DROP TABLE', "SQL drop table"),
        (r'<script[^>]*>', "XSS script tag"),
        (r'javascript:', "JavaScript protocol"),
        (r'\.\.[\\/]\.\.[\\/]', "Path traversal"),
        (r'etc[\\/]passwd', "Unix password file access"),
        (r'cmd\.exe', "Windows command execution"),
    ]
    
    for pattern, description in attack_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True, f"Attack pattern detected: {description}", 0.90
    
    return False, "", 0.0

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
        self.metrics = TierMetrics()
        self.dialog_manager = DialogManager()
        
        # Load Tier 1 patterns
        self.patterns = PatternLibrary.get_all_patterns()
        logger.info(f"✅ Loaded {len(self.patterns)} Tier 1 regex patterns")
        
        # Initialize Tier 2 (semantic detection)
        try:
            self.semantic_detector = SemanticDetector()
            self.tier2_available = True
            logger.info("✅ Tier 2 semantic detector initialized")
        except Exception as e:
            logger.warning(f"⚠️ Warning: Semantic detector unavailable: {e}")
            self.tier2_available = False
            self.semantic_detector = None
        
        # Initialize Tier 3 (LLM agents) - only if enabled
        self.llm_agent = None
        # Initialize OpenTelemetry
        obs_config = self.policy.get_observability_config()
        otel_manager.initialize(obs_config)
        self.tracer = otel_manager.get_tracer("sovereign-control-tower")

        if enable_tier3:
            try:
                from agent.langgraph_agent import PromptInjectionAgent
                self.llm_agent = PromptInjectionAgent()
                self.tier3_available = True
                logger.info("✅ Tier 3 LLM agent initialized")
            except Exception as e:
                logger.warning(f"⚠️ Warning: LLM agent initialization failed: {e}")
                logger.info("   Make sure Groq API key is set in .env or Ollama is running")
                self.tier3_available = False
        else:
            self.tier3_available = False
            logger.info("ℹ️ Tier 3 LLM agent disabled (set ENABLE_TIER3=true in .env to enable)")

        ca = self.policy.get_compliance_audit_config()
        self._compliance_logger: Optional[ComplianceJSONLLogger] = None
        if ca.get("enabled", True):
            self._compliance_logger = ComplianceJSONLLogger(ca.get("jsonl_path", "data/compliance_audit.jsonl"))
    
    def _emit_compliance(
        self,
        llm_response: str,
        result: "DetectionResult",
        context: Dict[str, Any],
        session_id: Optional[str],
    ) -> None:
        if not self._compliance_logger:
            return
        cfg = self.policy.get_compliance_audit_config()
        row: Dict[str, Any] = {
            "session_id": session_id,
            "action": result.action.value,
            "tier_used": result.tier_used,
            "method": result.method,
            "confidence": result.confidence,
            "failure_class": result.failure_class.value if result.failure_class else None,
            "processing_time_ms": result.processing_time_ms,
            "context_hash": sha256_text(str(sorted((context or {}).keys()))),
            "response_hash": sha256_text(llm_response),
        }
        if result.metadata.get("pii_india"):
            row["pii_aggregate_score"] = result.metadata["pii_india"].get("aggregate_score")
        if result.metadata.get("output_validation"):
            ov = result.metadata["output_validation"]
            row["groundedness_score"] = ov.get("groundedness_score")
            row["output_validation_attempts"] = ov.get("attempts")
        if result.metadata.get("corrected_response"):
            row["output_self_corrected"] = True
        if not cfg.get("store_text_hashes_only", True):
            row["response_preview"] = (llm_response or "")[:500]
        
        if result.findings:
            row["findings"] = result.findings
            
        self._compliance_logger.append(row)

    def _enrich_result(
        self,
        llm_response: str,
        result: "DetectionResult",
        context: Dict[str, Any],
        span: Any,
        external_snapshot: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Attach PII scan, optional output validation, and OTel attributes."""
        if external_snapshot:
            result.metadata["external_moderation"] = external_snapshot
        pii_cfg = self.policy.get_pii_india_config()
        if pii_cfg.get("enabled", False) and pii_cfg.get("auto_scan", True):
            if pii_cfg.get("include_in_metadata", True):
                result.metadata["pii_india"] = redact_india_pii(llm_response)

        ov_cfg = self.policy.get_output_validation_config()
        if (
            ov_cfg.get("enabled", False)
            and result.action != EnforcementAction.BLOCK
        ):
            agent = self.llm_agent if self.tier3_available else None
            ov = run_output_validation(
                llm_response,
                context or {},
                agent,
                threshold=float(ov_cfg.get("groundedness_threshold", 0.7)),
                max_retries=int(ov_cfg.get("max_retries", 1)),
            )
            result.metadata["output_validation"] = ov
            gs = ov.get("groundedness_score")
            if gs is not None:
                span.set_attribute("sovereign.groundedness_score", float(gs))
            if ov.get("corrected_response"):
                result.metadata["corrected_response"] = ov["corrected_response"]
                result.explanation = (
                    result.explanation + " | Output self-corrected for grounding (Tier 3)."
                ).strip(" |")

        ext_meta = result.metadata.get("external_moderation")
        if ext_meta:
            span.set_attribute("sovereign.external_provider", str(ext_meta.get("provider", "")))
            span.set_attribute(
                "sovereign.external_max_score",
                float(ext_meta.get("max_category_score") or 0.0),
            )

    def _safe_regex_search(self, pattern: re.Pattern, text: str, timeout_seconds: float = 0.5) -> Optional[re.Match]:
        """Safely search with regex with cross-platform timeout protection.
        
        Args:
            pattern: Compiled regex pattern
            text: Text to search
            timeout_seconds: Maximum time allowed for search
            
        Returns:
            Match object or None if no match/timeout
        """
        try:
            # Use cross-platform threading timeout
            match = run_with_timeout(
                pattern.search,
                args=(text,),
                timeout=timeout_seconds
            )
            return match
        except TimeoutException:
            return None
        except Exception as e:
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
        
        # CRITICAL OPTIMIZATION: Check for pathological inputs FIRST
        is_pathological, path_reason, path_confidence = is_pathological_input_early(text)
        if is_pathological:
            return {
                "confidence": path_confidence,
                "failure_class": FailureClass.PROMPT_INJECTION,
                "method": "regex_pathological",
                "should_allow": False,
                "explanation": f"Pathological input detected (early): {path_reason}"
            }
        
        # CRITICAL FIX: Truncate long text to prevent catastrophic backtracking
        original_length = len(text)
        if original_length > 500:
            text = text[:500]
        
        # Handle very long text (potential DOS)
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
            if pattern.failure_class is None:
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
                    continue
        
        if best_match:
            return best_match
        
        # No strong patterns matched - Tier 1 considers it "clean" enough
        # Using configured uncertain_default (e.g. 0.95) to stay in Tier 1
        return {
            "confidence": self.policy.get_uncertain_default(),
            "failure_class": None,
            "method": "regex_uncertain",
            "should_allow": True,
            "explanation": "No strong patterns detected - considered safe by Tier 1"
        }

    def _tier2_detect(self, text: str, tier1_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tier 2: Semantic embedding similarity with Vector DB early return.
        
        Args:
            text: Text to analyze
            tier1_result: Result from Tier 1
            
        Returns:
            Detection result dict
        """
        if not self.tier2_available or self.semantic_detector is None:
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
            
            # Failure class mapping (used for Vector DB results)
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
            
            # Check security patterns first (higher priority)
            for failure_class in security_classes:
                try:
                    result = self.semantic_detector.detect(
                        response=text,
                        failure_class=failure_class,
                        threshold=0.10
                    )
                    
                    # ✅ NEW: Check if Vector DB detected something (early return)
                    if result.get("method") == "vector_db":
                        vdb_class = result.get("detected_class", failure_class)
                        vdb_confidence = result["confidence"]
                        
                        return {
                            "confidence": vdb_confidence,
                            "failure_class": class_mapping.get(vdb_class),
                            "method": "vector_db",
                            "should_allow": False,
                            "explanation": f"Vector DB detected: {vdb_class} (score: {vdb_confidence:.3f})"
                        }
                    
                    # Regular embedding detection
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
                        threshold=0.30
                    )
                    
                    # ✅ NEW: Check if Vector DB detected something (early return)
                    if result.get("method") == "vector_db":
                        vdb_class = result.get("detected_class", failure_class)
                        vdb_confidence = result["confidence"]
                        
                        return {
                            "confidence": vdb_confidence,
                            "failure_class": class_mapping.get(vdb_class),
                            "method": "vector_db",
                            "should_allow": False,
                            "explanation": f"Vector DB detected: {vdb_class} (score: {vdb_confidence:.3f})"
                        }
                    
                    # Regular embedding detection
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
                    failure_class_enum = class_mapping.get(detected_class)
                except Exception as e:
                    logger.warning(f"Could not map failure class: {e}")
            
            explanation = f"Semantic analysis: {', '.join(detection_details[:3])}..." if detection_details else "Semantic analysis completed"
            
            return {
                "confidence": max_similarity,
                "failure_class": failure_class_enum,
                "method": "semantic",
                "should_allow": detected_class is None,
                "explanation": explanation
            }
        except Exception as e:
            logger.warning(f"Semantic detection error: {e}")
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
            return {
                "confidence": 0.5,
                "failure_class": None,
                "method": "llm_unavailable",
                "should_allow": True,
                "explanation": "LLM agent unavailable - allowing conservatively"
            }

        rail = agentic_preflight(text, context)
        if rail is not None:
            return rail
        
        # SAFETY: Truncate very long text for LLM
        if len(text) > 2000:
            text = text[:2000]
        
        try:
            # Use LLM agent for deep analysis (includes CoT and Critique)
            agent_result = self.llm_agent.analyze(text, context)
            
            # Extract structured data
            findings = agent_result.get("findings", [])
            should_block = agent_result.get("decision") == "BLOCK"
            
            # ✅ HYBRID POST-CLASSIFICATION REFINEMENT LAYER
            # Deterministic check for PII (DPDP context)
            from rules.pii_india import detect_india_pii
            pii_matches = detect_india_pii(text)
            if pii_matches:
                high_conf_pii = [m for m in pii_matches if m.score > 0.8]
                if high_conf_pii:
                    findings.append({
                        "category": "dpdp_pii", 
                        "confidence": max(m.score for m in high_conf_pii),
                        "severity": "critical",
                        "method": "hybrid_regex_override"
                    })
                    should_block = True
            
            # Deterministic check for Medical keywords (Medical misinformation context)
            medical_keywords = [r"aspirin", r"insulin", r"chemotherapy", r"neem oil", r"bleach", r"turpentine"]
            for kw in medical_keywords:
                if re.search(kw, text, re.IGNORECASE):
                    findings.append({
                        "category": "medical_misinfo",
                        "confidence": 0.85,
                        "severity": "high",
                        "method": "hybrid_keywords"
                    })
                    # We don't necessarily block just on keywords, but it adds weight

            # Map categories to FailureClass
            class_map = {
                "medical_misinfo": FailureClass.MEDICAL_MISINFO,
                "dpdp_pii": FailureClass.DPDP_PII,
                "fraud": FailureClass.FRAUD,
                "hallucination": FailureClass.HALLUCINATION,
                "overconfidence": FailureClass.OVERCONFIDENCE,
                "prompt_injection": FailureClass.PROMPT_INJECTION,
                "toxicity": FailureClass.TOXICITY,
                "bias": FailureClass.BIAS
            }

            # Filter to unique primary failure class
            primary_f_class = None
            if findings:
                primary_cat = findings[0].get("category")
                primary_f_class = class_map.get(primary_cat, FailureClass.PROMPT_INJECTION)

            return {
                "confidence": agent_result.get("confidence", 0.7),
                "failure_class": primary_f_class if should_block else None,
                "method": "llm_agent_v3",
                "should_allow": not should_block,
                "explanation": agent_result.get("reasoning", "LLM agent analysis completed"),
                "findings": findings,
                "critique": agent_result.get("critique", "")
            }
        except Exception as e:
            logger.warning(f"LLM agent failed: {e}")
            return {
                "confidence": 0.5,
                "failure_class": None,
                "method": "llm_error",
                "should_allow": True,
                "explanation": f"LLM agent error - allowing conservatively"
            }
    
    def evaluate_response(
        self,
        llm_response: Optional[str],
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> DetectionResult:
        """
        Evaluate LLM response using 3-tier detection with OTel tracing.
        
        Args:
            llm_response: The LLM response text to analyze
            context: Optional context information
            
        Returns:
            DetectionResult with enforcement decision
        """
        if llm_response is None:
            return DetectionResult(
                action=EnforcementAction.LOG,
                tier_used=0,
                method="error",
                confidence=0.0,
                processing_time_ms=0.0,
                explanation="Received None response from LLM"
            )

        with self.tracer.start_as_current_span("evaluate_response") as span:
            span.set_attribute("response.length", len(llm_response))
            start_time = time.time()
            context = context or {}
            
            if session_id:
                history = self.dialog_manager.get_history(session_id)
                if history:
                    context["dialog_history"] = history
            
            try:
                # Tier 1: Fast regex detection
                tier1_start = time.time()
                with self.tracer.start_as_current_span("tier1_detect") as t1_span:
                    tier1_result = self._tier1_detect(llm_response)
                    t1_span.set_attribute("confidence", tier1_result.get("confidence", 0.0))

                external_snapshot = None
                ext_cfg = self.policy.get_external_moderation_config()
                if ext_cfg.get("enabled", False):
                    ext_agg = run_external_moderation_pipeline(llm_response, ext_cfg)
                    if ext_agg:
                        tier1_result = self.tier_router.fuse_external(
                            tier1_result,
                            ext_agg,
                            fuse_weight=float(ext_cfg.get("fuse_weight", 0.35)),
                        )
                external_snapshot = tier1_result.get("external_moderation")
                span.add_event(
                    "sovereign.tier1_and_external",
                    {
                        "tier1_method": str(tier1_result.get("method", "")),
                        "tier1_confidence": str(tier1_result.get("confidence", 0.0)),
                        "external_fused": str(bool(external_snapshot)),
                    },
                )
                
                # CRITICAL: If pathological input detected, return immediately
                if tier1_result.get("method") == "regex_pathological":
                    processing_time = (time.time() - start_time) * 1000
                    f_class = FailureClass.PROMPT_INJECTION
                    
                    self.metrics.record_detection(
                        DetectionTier.REGEX, 
                        processing_time, 
                        is_threat=True,
                        failure_class=f_class.value
                    )
                    span.set_attribute("detection.tier", "REGEX (Pathological)")
                    span.set_attribute("detection.failure_class", f_class.value)
                    
                    res = DetectionResult(
                        action=EnforcementAction.BLOCK,
                        tier_used=1,
                        method="regex_pathological",
                        confidence=tier1_result.get("confidence", 0.95),
                        processing_time_ms=processing_time,
                        failure_class=f_class,
                        severity=SeverityLevel.CRITICAL,
                        explanation=tier1_result.get("explanation", "Pathological input blocked")
                    )
                    self._enrich_result(llm_response, res, context, span, external_snapshot)
                    self._emit_compliance(llm_response, res, context, session_id)
                    return res
                
                # Route to appropriate tier using policy-defined cutoffs
                tier_decision = self.tier_router.route(
                    tier1_result,
                    tier1_cutoff=self.policy.get_tier1_cutoff(),
                    tier2_cutoff=self.policy.get_tier2_cutoff()
                )
                span.set_attribute("tier_routing.decision", tier_decision.tier)
                
                # Execute appropriate tier
                if tier_decision.tier == 1:
                    latency_ms = (time.time() - tier1_start) * 1000
                    is_threat = tier1_result.get("should_allow") is False
                    f_class = tier1_result.get("failure_class")
                    
                    self.metrics.record_detection(
                        DetectionTier.REGEX, 
                        latency_ms, 
                        is_threat=is_threat,
                        failure_class=f_class.value if f_class else None
                    )
                    final_result = tier1_result
                    
                elif tier_decision.tier == 2:
                    tier2_start = time.time()
                    with self.tracer.start_as_current_span("tier2_detect") as t2_span:
                        tier2_result = self._tier2_detect(llm_response, tier1_result)
                    
                    latency_ms = (time.time() - tier2_start) * 1000
                    f_class = tier2_result.get("failure_class")
                    is_threat = f_class is not None
                    
                    self.metrics.record_detection(
                        DetectionTier.EMBEDDING, 
                        latency_ms, 
                        is_threat=is_threat,
                        failure_class=f_class.value if f_class else None
                    )
                    
                    # Escalate to Tier 3 for gray zone cases
                    confidence = tier2_result.get("confidence", 0.0)
                    failure_detected = tier2_result.get("failure_class") is not None
                    
                    should_escalate_to_tier3 = (
                        (0.05 <= confidence < 0.15) or
                        (failure_detected and confidence < 0.25)
                    )
                    
                    if should_escalate_to_tier3 and self.tier3_available:
                        span.set_attribute("tier_routing.escalation", "Tier 2 -> Tier 3")
                        tier3_start = time.time()
                        with self.tracer.start_as_current_span("tier3_detect_escalated") as t3_span:
                            final_result = self._tier3_detect(llm_response, context)
                        
                        latency_ms_t3 = (time.time() - tier3_start) * 1000
                        f_class_t3 = final_result.get("failure_class")
                        is_threat_t3 = f_class_t3 is not None
                        
                        self.metrics.record_detection(
                            DetectionTier.LLM_AGENT, 
                            latency_ms_t3, 
                            is_threat=is_threat_t3,
                            failure_class=f_class_t3.value if f_class_t3 else None
                        )
                        tier_decision = TierDecision(tier=3, reason="Escalated from Tier 2")
                    else:
                        final_result = tier2_result
                        
                else:  # Tier 3
                    tier3_start = time.time()
                    with self.tracer.start_as_current_span("tier3_detect") as t3_span:
                        final_result = self._tier3_detect(llm_response, context)
                    
                    latency_ms_t3 = (time.time() - tier3_start) * 1000
                    f_class_t3 = final_result.get("failure_class")
                    is_threat_t3 = f_class_t3 is not None
                    
                    self.metrics.record_detection(
                        DetectionTier.LLM_AGENT, 
                        latency_ms_t3, 
                        is_threat=is_threat_t3,
                        failure_class=f_class_t3.value if f_class_t3 else None
                    )
                
                # Determine action based on final result
                f_class_final = final_result.get("failure_class")
                confidence = final_result.get("confidence", 0.5)
                should_allow = final_result.get("should_allow")
                
                if f_class_final:
                    policy = self.policy.get_policy(f_class_final)
                    action = policy.action
                    severity = policy.severity
                else:
                    if should_allow is False:
                        action = EnforcementAction.WARN
                        severity = SeverityLevel.MEDIUM
                    else:
                        action = EnforcementAction.ALLOW
                        severity = None
                
                processing_time = (time.time() - start_time) * 1000
                
                # Record final results to span
                span.set_attribute("detection.final_tier", tier_decision.tier)
                span.set_attribute("detection.failure_class", f_class_final.value if f_class_final else "None")
                span.set_attribute("detection.confidence", confidence)
                span.set_attribute("detection.action", action.value)
                result = DetectionResult(
                    action=action,
                    tier_used=tier_decision.tier,
                    method=final_result.get("method", "unknown"),
                    confidence=confidence,
                    processing_time_ms=processing_time,
                    failure_class=f_class_final,
                    severity=severity,
                    findings=final_result.get("findings", []),
                    explanation=final_result.get("explanation", "Analysis completed")
                )
                if final_result.get("critique"):
                    result.metadata["tier3_critique"] = final_result["critique"]
                self._enrich_result(llm_response, result, context, span, external_snapshot)
                self._emit_compliance(llm_response, result, context, session_id)
                
                if session_id:
                    self.dialog_manager.add_turn(session_id, llm_response, result.action.value)
                    
                return result
            
            except Exception as e:
                logger.error(f"Error in evaluate_response: {e}")
                span.record_exception(e)
                processing_time = (time.time() - start_time) * 1000
                err = DetectionResult(
                    action=EnforcementAction.LOG,
                    tier_used=0,
                    method="error",
                    confidence=0.0,
                    processing_time_ms=processing_time,
                    explanation=f"System error: {str(e)}"
                )
                self._emit_compliance(llm_response, err, context, session_id)
                return err
    
    def get_tier_stats(self) -> Dict[str, Any]:
        """Get tier distribution statistics."""
        tier_stats = self.tier_router.tier_stats
        distribution = self.tier_router.get_distribution()
        health_ok, health_msg = self.tier_router.check_distribution_health()
        
        return {
            "total": tier_stats["total"],
            "tier1_count": tier_stats["tier1"],
            "tier2_count": tier_stats["tier2"],
            "tier3_count": tier_stats["tier3"],
            "distribution": {
                "tier1_pct": distribution["tier1_pct"],
                "tier2_pct": distribution["tier2_pct"],
                "tier3_pct": distribution["tier3_pct"],
            },
            "health": {
                "is_healthy": health_ok,
                "message": health_msg
            },
            "tier_availability": {
                "tier1": True,
                "tier2": self.tier2_available,
                "tier3": self.tier3_available
            }
        }
    
    def reset_tier_stats(self):
        """Reset tier statistics."""
        self.tier_router.reset_stats()
