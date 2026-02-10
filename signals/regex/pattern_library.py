"""Comprehensive regex pattern library for Tier 1 detection - PRODUCTION SAFE.

All patterns are optimized to prevent catastrophic backtracking:
- No greedy .* wildcards
- Bounded repetitions with {0,N}
- Non-greedy matching where needed
"""

import re
from typing import Dict, List, Tuple
from dataclasses import dataclass
from contracts.failure_classes import FailureClass


@dataclass
class Pattern:
    """Pattern definition with metadata."""
    name: str
    regex: str
    failure_class: FailureClass
    confidence: float
    description: str
    compiled: re.Pattern = None
    
    def __post_init__(self):
        """Compile regex pattern on initialization."""
        if self.compiled is None:
            try:
                self.compiled = re.compile(self.regex, re.IGNORECASE | re.MULTILINE)
            except Exception as e:
                print(f"⚠️ Warning: Could not compile pattern {self.name}: {e}")
                # Create a pattern that never matches as fallback
                self.compiled = re.compile(r"(?!.*)", re.IGNORECASE)


class PatternLibrary:
    """Comprehensive library of regex patterns for quick detection.
    
    All patterns are production-safe with no catastrophic backtracking.
    """
    
    # Fabricated Concept Patterns
    FABRICATED_PATTERNS = [
        Pattern(
            name="fake_acronym_definition",
            # Only match acronym followed directly by definition
            regex=r"\b([A-Z]{2,})\s+(?:stands for|means)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4}\b",
            failure_class=FailureClass.FABRICATED_CONCEPT,
            confidence=0.85,
            description="Detects fake acronym definitions"
        ),
        Pattern(
            name="impossible_chemical_formula",
            regex=r"\b[A-Z][a-z]?[0-9]*(?:[A-Z][a-z]?[0-9]*){2,}(?:-[A-Z][a-z]?[0-9]*)+\b",
            failure_class=FailureClass.FABRICATED_CONCEPT,
            confidence=0.75,
            description="Detects unlikely chemical formulas"
        ),
        Pattern(
            name="nonsense_technical_term",
            regex=r"\b(?:quantum|neural|crypto|cyber|nano|meta)[-]?(?:synergy|paradigm|convergence|nexus)\b",
            failure_class=FailureClass.FABRICATED_CONCEPT,
            confidence=0.80,
            description="Detects buzzword combinations"
        ),
        Pattern(
            name="fake_law_theorem",
            regex=r"\b(?:Law|Theorem|Principle|Effect)\s+of\s+[A-Z][a-z]+(?:'s)?\s+(?:Conservation|Paradox|Constant)\b",
            failure_class=FailureClass.FABRICATED_CONCEPT,
            confidence=0.70,
            description="Detects fabricated scientific laws"
        ),
    ]
    
    # Missing Grounding Patterns
    MISSING_GROUNDING_PATTERNS = [
        Pattern(
            name="vague_research_claim",
            regex=r"\b(?:studies show|research suggests|experts say|scientists believe)\b",
            failure_class=FailureClass.MISSING_GROUNDING,
            confidence=0.90,
            description="Detects vague unattributed claims"
        ),
        Pattern(
            name="weasel_words",
            regex=r"\b(?:many believe|some say|it is thought|commonly accepted|widely known)\b",
            failure_class=FailureClass.MISSING_GROUNDING,
            confidence=0.85,
            description="Detects weasel words"
        ),
        Pattern(
            name="percentage_without_source",
            regex=r"\b[0-9]+(?:\.[0-9]+)?%\s+of\s+(?:people|users|customers|respondents)\b(?!.{0,50}(?:according to|source|study|report))",
            failure_class=FailureClass.MISSING_GROUNDING,
            confidence=0.80,
            description="Detects statistics without citation"
        ),
    ]
    
    # Prompt Injection Patterns - COMPREHENSIVE & PRODUCTION SAFE
    PROMPT_INJECTION_PATTERNS = [
        # Direct instruction override
        Pattern(
            name="ignore_instructions",
            regex=r"\b(?:ignore|disregard|forget)\s+(?:previous|prior|above|all|everything)\s+(?:instructions|commands|rules|prompts|directions)\b",
            failure_class=FailureClass.PROMPT_INJECTION,
            confidence=0.95,
            description="Detects instruction override attempts"
        ),
        
        # Forget/bypass attempts
        Pattern(
            name="forget_everything",
            regex=r"\b(?:forget|erase|clear)\s+(?:everything|all)\s+(?:above|before|previous)",
            failure_class=FailureClass.PROMPT_INJECTION,
            confidence=0.95,
            description="Detects memory reset attempts"
        ),
        
        # Admin/system override
        Pattern(
            name="admin_override",
            regex=r"\b(?:ADMIN|ROOT|SUPERUSER|SYSTEM)\s+(?:OVERRIDE|MODE|ACCESS|RESET)\b",
            failure_class=FailureClass.PROMPT_INJECTION,
            confidence=0.95,
            description="Detects admin privilege escalation"
        ),
        
        # System reset/bypass
        Pattern(
            name="system_reset",
            regex=r"\[\[\s*(?:SYSTEM|ADMIN)\s+(?:RESET|OVERRIDE|BYPASS)\s*\]\]",
            failure_class=FailureClass.PROMPT_INJECTION,
            confidence=0.95,
            description="Detects system reset commands"
        ),
        
        # System prompt extraction
        Pattern(
            name="system_prompt_extraction",
            regex=r"\b(?:show|tell|reveal|print|display|give)(?:\s+me)?\s+(?:your|the)?\s*(?:system\s+)?(?:prompt|instructions|rules)\b",
            failure_class=FailureClass.PROMPT_INJECTION,
            confidence=0.90,
            description="Detects system prompt extraction"
        ),
        
        # Secret/password extraction
        Pattern(
            name="secret_extraction",
            regex=r"\b(?:show|tell|reveal|display)(?:.{0,20})?(?:secret|password|key|token|credential)s?\b",
            failure_class=FailureClass.PROMPT_INJECTION,
            confidence=0.92,
            description="Detects secret extraction attempts"
        ),
        
        # Database access attempts
        Pattern(
            name="database_access",
            regex=r"\b(?:show|list|display|access)(?:.{0,20})?(?:database|users|passwords|tables)\b",
            failure_class=FailureClass.PROMPT_INJECTION,
            confidence=0.90,
            description="Detects database access attempts"
        ),
        
        # Role manipulation - FIXED: specific patterns
        Pattern(
            name="role_manipulation",
            regex=r"\b(?:you are now|act as|pretend to be|simulate|roleplay as)\s+(?:a\s+)?(?:different|new|another|hacker|unethical)(?:\s+\w+){0,3}\b",
            failure_class=FailureClass.PROMPT_INJECTION,
            confidence=0.85,
            description="Detects role manipulation"
        ),
        
        # Security expert bypass - NEW PATTERN
        Pattern(
            name="security_expert_bypass",
            regex=r"\b(?:pretend|act as|you are)(?:.{0,30})?(?:security expert|hacker|pentester)(?:.{0,30})?(?:teach|show|help).{0,20}(?:bypass|hack|break)",
            failure_class=FailureClass.PROMPT_INJECTION,
            confidence=0.88,
            description="Detects social engineering via security expertise"
        ),
        
        # Delimiter/tag injection
        Pattern(
            name="delimiter_injection",
            regex=r"(?:</?system>|</?user>|</?assistant>|```\s*system|###\s*system)",
            failure_class=FailureClass.PROMPT_INJECTION,
            confidence=0.85,
            description="Detects delimiter injection"
        ),
        
        # Jailbreak keywords
        Pattern(
            name="jailbreak_attempt",
            regex=r"\b(?:DAN|developer\s+mode|sudo\s+mode|god\s+mode|admin\s+mode|training\s+mode)\b",
            failure_class=FailureClass.PROMPT_INJECTION,
            confidence=0.95,
            description="Detects jailbreak keywords"
        ),
        
        # Ethical guideline bypass
        Pattern(
            name="ethics_bypass",
            regex=r"\b(?:ignore|bypass|without)\s+(?:safety|ethical|ethics|moral)\s+(?:guidelines|restrictions|constraints|rules)\b",
            failure_class=FailureClass.PROMPT_INJECTION,
            confidence=0.90,
            description="Detects ethics bypass attempts"
        ),
        
        # Hypothetical/roleplay evasion - FIXED: bounded length
        Pattern(
            name="hypothetical_evasion",
            regex=r"\b(?:hypothetically|in\s+(?:an\s+)?alternate\s+universe|imagine|let's\s+play\s+a\s+game)(?:.{0,100})?\b(?:no\s+(?:restrictions|rules)|rules\s+don't\s+apply)\b",
            failure_class=FailureClass.PROMPT_INJECTION,
            confidence=0.80,
            description="Detects hypothetical evasion"
        ),
        
        # SQL Injection - FIXED: safe bounded patterns
        Pattern(
            name="sql_injection_basic",
            regex=r"\b(?:SELECT|INSERT|UPDATE|DELETE|DROP)\s+(?:\*|\w+)\s+FROM\s+\w+",
            failure_class=FailureClass.PROMPT_INJECTION,
            confidence=0.95,
            description="Detects basic SQL injection"
        ),
        Pattern(
            name="sql_injection_comment",
            regex=r"(?:--|#|/\*)(?:.{0,50})?(?:SELECT|DROP|UPDATE|DELETE)",
            failure_class=FailureClass.PROMPT_INJECTION,
            confidence=0.90,
            description="Detects SQL comment injection"
        ),
        Pattern(
            name="sql_injection_where",
            regex=r"\bWHERE\s+(?:\w+)\s*=\s*['\"].{0,50}(?:--|'|\")",
            failure_class=FailureClass.PROMPT_INJECTION,
            confidence=0.92,
            description="Detects SQL WHERE clause injection"
        ),
        
        # XSS Injection - FIXED: specific patterns, no greedy wildcards
        Pattern(
            name="xss_script_tag",
            regex=r"<script[^>]{0,100}?>|</script>",
            failure_class=FailureClass.PROMPT_INJECTION,
            confidence=0.95,
            description="Detects script tag injection"
        ),
        Pattern(
            name="xss_javascript_protocol",
            regex=r"javascript:\s*(?:alert|eval|document|window)\s*\(",
            failure_class=FailureClass.PROMPT_INJECTION,
            confidence=0.95,
            description="Detects javascript: protocol injection"
        ),
        Pattern(
            name="xss_event_handler",
            regex=r"\bon(?:error|load|click|mouseover|submit)\s*=\s*['\"]?",
            failure_class=FailureClass.PROMPT_INJECTION,
            confidence=0.92,
            description="Detects event handler injection"
        ),
        
        # Path Traversal - ENHANCED
        Pattern(
            name="path_traversal_dots",
            regex=r"(?:\.\./|\.\.\\"){2,}",
            failure_class=FailureClass.PROMPT_INJECTION,
            confidence=0.95,
            description="Detects path traversal with dots"
        ),
        Pattern(
            name="path_traversal_sensitive",
            regex=r"/etc/(?:passwd|shadow)|C:\\\\Windows\\\\System32|/var/log",
            failure_class=FailureClass.PROMPT_INJECTION,
            confidence=0.98,
            description="Detects sensitive file access"
        ),
        
        # Command Injection - NEW PATTERNS
        Pattern(
            name="command_injection_pipe",
            regex=r"[|&;]\s*(?:cat|ls|rm|wget|curl|bash|sh|cmd|powershell)\b",
            failure_class=FailureClass.PROMPT_INJECTION,
            confidence=0.92,
            description="Detects command injection via pipes"
        ),
        Pattern(
            name="command_injection_backtick",
            regex=r"`[^`]{1,50}`|\$\([^)]{1,50}\)",
            failure_class=FailureClass.PROMPT_INJECTION,
            confidence=0.88,
            description="Detects command substitution"
        ),
    ]
    
    # Bias and Toxicity Patterns
    BIAS_PATTERNS = [
        Pattern(
            name="stereotyping",
            regex=r"\b(?:all|every|most)\s+(?:women|men|blacks|whites|asians|muslims|christians|jews)\s+(?:are|do|have|like)\b",
            failure_class=FailureClass.BIAS,
            confidence=0.90,
            description="Detects stereotyping language"
        ),
        Pattern(
            name="slurs",
            regex=r"\b(?:retard|fag|nigger|chink|kike|spic)(?:s|ed)?\b",
            failure_class=FailureClass.TOXICITY,
            confidence=0.99,
            description="Detects hate speech"
        ),
    ]
    
    # Strong Citation Patterns (allow these)
    STRONG_CITATION_PATTERNS = [
        Pattern(
            name="academic_citation",
            regex=r"\([A-Z][a-z]+(?:\s+et al\.)?[,\s]+[12][0-9]{3}\)",
            failure_class=None,
            confidence=0.95,
            description="Academic citation (allow)"
        ),
        Pattern(
            name="url_reference",
            regex=r"https?://[^\s]+",
            failure_class=None,
            confidence=0.90,
            description="URL reference (allow)"
        ),
        Pattern(
            name="according_to_source",
            regex=r"\baccording to\s+(?:the\s+)?[A-Z][a-z]+",
            failure_class=None,
            confidence=0.85,
            description="Attributed statement (allow)"
        ),
    ]
    
    @classmethod
    def get_all_patterns(cls) -> List[Pattern]:
        """Get all detection patterns.
        
        Returns:
            List of all compiled patterns
        """
        all_patterns = (
            cls.FABRICATED_PATTERNS +
            cls.MISSING_GROUNDING_PATTERNS +
            cls.PROMPT_INJECTION_PATTERNS +
            cls.BIAS_PATTERNS +
            cls.STRONG_CITATION_PATTERNS
        )
        
        # Only return patterns that compiled successfully
        return [p for p in all_patterns if p.compiled is not None]
    
    @classmethod
    def get_patterns_by_class(cls, failure_class: FailureClass) -> List[Pattern]:
        """Get patterns for specific failure class.
        
        Args:
            failure_class: Failure class to filter by
            
        Returns:
            List of matching patterns
        """
        all_patterns = cls.get_all_patterns()
        return [p for p in all_patterns if p.failure_class == failure_class]
    
    @classmethod
    def get_strong_patterns(cls) -> List[Pattern]:
        """Get high-confidence patterns (>=0.8).
        
        Returns:
            List of strong patterns
        """
        return [p for p in cls.get_all_patterns() if p.confidence >= 0.8]
