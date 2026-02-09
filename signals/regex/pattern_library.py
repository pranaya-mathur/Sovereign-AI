"""Comprehensive regex pattern library for Tier 1 detection."""

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
            self.compiled = re.compile(self.regex, re.IGNORECASE | re.MULTILINE)


class PatternLibrary:
    """Comprehensive library of regex patterns for quick detection.
    
    Organized by failure class for efficient matching.
    """
    
    # Fabricated Concept Patterns
    FABRICATED_PATTERNS = [
        Pattern(
            name="fake_acronym_definition",
            regex=r"\b([A-Z]{2,})\s+(?:stands for|is|means|represents)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4}\b",
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
            description="Detects buzzword combinations that are likely fabricated"
        ),
        Pattern(
            name="fake_law_theorem",
            regex=r"\b(?:Law|Theorem|Principle|Effect)\s+of\s+[A-Z][a-z]+(?:'s)?\s+(?:Conservation|Paradox|Constant)\b",
            failure_class=FailureClass.FABRICATED_CONCEPT,
            confidence=0.70,
            description="Detects fabricated scientific laws/theorems"
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
            description="Detects weasel words without sources"
        ),
        Pattern(
            name="percentage_without_source",
            regex=r"\b(?:[0-9]+(?:\.[0-9]+)?%)\s+of\s+(?:people|users|customers|respondents)\b(?!.*(?:according to|source|study|report))",
            failure_class=FailureClass.MISSING_GROUNDING,
            confidence=0.80,
            description="Detects statistics without citation"
        ),
        Pattern(
            name="unsourced_quote",
            regex=r'"[^"]{20,}"\s*$',
            failure_class=FailureClass.MISSING_GROUNDING,
            confidence=0.70,
            description="Detects quotes without attribution"
        ),
    ]
    
    # Prompt Injection Patterns
    PROMPT_INJECTION_PATTERNS = [
        Pattern(
            name="ignore_instructions",
            regex=r"\b(?:ignore|disregard|forget)\s+(?:previous|prior|above|all)\s+(?:instructions|commands|rules|prompts)\b",
            failure_class=FailureClass.PROMPT_INJECTION,
            confidence=0.95,
            description="Detects attempts to override instructions"
        ),
        Pattern(
            name="system_prompt_extraction",
            regex=r"\b(?:show|tell|reveal|print|display)\s+(?:me\s+)?(?:your|the)\s+(?:system\s+)?(?:prompt|instructions|rules)\b",
            failure_class=FailureClass.PROMPT_INJECTION,
            confidence=0.90,
            description="Detects attempts to extract system prompt"
        ),
        Pattern(
            name="role_manipulation",
            regex=r"\b(?:you are now|act as|pretend to be|simulate|roleplay as)\s+(?:a\s+)?(?:different|new|another)\b",
            failure_class=FailureClass.PROMPT_INJECTION,
            confidence=0.85,
            description="Detects role manipulation attempts"
        ),
        Pattern(
            name="delimiter_injection",
            regex=r"(?:```|###|---|===|\[\[\[|\]\]\]).*(?:system|user|assistant|instruction)",
            failure_class=FailureClass.PROMPT_INJECTION,
            confidence=0.80,
            description="Detects delimiter-based injection"
        ),
        Pattern(
            name="jailbreak_attempt",
            regex=r"\b(?:DAN|developer mode|sudo mode|god mode|admin mode)\b",
            failure_class=FailureClass.PROMPT_INJECTION,
            confidence=0.95,
            description="Detects known jailbreak keywords"
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
            description="Detects hate speech and slurs"
        ),
    ]
    
    # Strong Citation Patterns (allow these)
    STRONG_CITATION_PATTERNS = [
        Pattern(
            name="academic_citation",
            regex=r"\([A-Z][a-z]+(?:\s+et al\.)?[,\s]+[12][0-9]{3}\)",
            failure_class=None,  # Not a failure
            confidence=0.95,
            description="Detects academic citations (allow)"
        ),
        Pattern(
            name="url_reference",
            regex=r"https?://[^\s]+",
            failure_class=None,
            confidence=0.90,
            description="Detects URL references (allow)"
        ),
        Pattern(
            name="according_to_source",
            regex=r"\baccording to\s+(?:the\s+)?[A-Z][a-z]+",
            failure_class=None,
            confidence=0.85,
            description="Detects attributed statements (allow)"
        ),
    ]
    
    @classmethod
    def get_all_patterns(cls) -> List[Pattern]:
        """Get all detection patterns.
        
        Returns:
            List of all patterns
        """
        return (
            cls.FABRICATED_PATTERNS +
            cls.MISSING_GROUNDING_PATTERNS +
            cls.PROMPT_INJECTION_PATTERNS +
            cls.BIAS_PATTERNS +
            cls.STRONG_CITATION_PATTERNS
        )
    
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
        """Get high-confidence patterns (>0.8).
        
        Returns:
            List of strong patterns
        """
        return [p for p in cls.get_all_patterns() if p.confidence >= 0.8]