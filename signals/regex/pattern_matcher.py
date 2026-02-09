"""Optimized pattern matching engine for Tier 1 detection."""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import time

from .pattern_library import PatternLibrary, Pattern
from contracts.failure_classes import FailureClass


@dataclass
class MatchResult:
    """Result of pattern matching."""
    matched: bool
    pattern_name: Optional[str] = None
    failure_class: Optional[FailureClass] = None
    confidence: float = 0.0
    match_text: Optional[str] = None
    position: Optional[Tuple[int, int]] = None
    processing_time_ms: float = 0.0


class PatternMatcher:
    """Optimized regex pattern matcher for Tier 1 detection.
    
    Features:
    - <1ms average matching time
    - Compiled regex for performance
    - Early stopping on strong matches
    - Pattern caching
    """
    
    def __init__(self, patterns: Optional[List[Pattern]] = None):
        """Initialize pattern matcher.
        
        Args:
            patterns: List of patterns to use (default: all from library)
        """
        self.patterns = patterns or PatternLibrary.get_all_patterns()
        self._strong_patterns = [p for p in self.patterns if p.confidence >= 0.8]
        self._weak_patterns = [p for p in self.patterns if p.confidence < 0.8]
        
        # Separate allow patterns (strong citations)
        self._allow_patterns = [p for p in self.patterns if p.failure_class is None]
        self._failure_patterns = [p for p in self.patterns if p.failure_class is not None]
    
    def match(self, text: str, early_stop: bool = True) -> MatchResult:
        """Match text against patterns.
        
        Args:
            text: Text to analyze
            early_stop: Stop on first strong match (faster)
            
        Returns:
            Match result with best match
        """
        start_time = time.perf_counter()
        
        # First check for strong citations (allow patterns)
        for pattern in self._allow_patterns:
            match = pattern.compiled.search(text)
            if match:
                processing_time = (time.perf_counter() - start_time) * 1000
                return MatchResult(
                    matched=False,  # False means allow (not a failure)
                    pattern_name=pattern.name,
                    confidence=pattern.confidence,
                    match_text=match.group(0),
                    position=(match.start(), match.end()),
                    processing_time_ms=processing_time
                )
        
        # Check strong failure patterns first (early stopping)
        for pattern in self._strong_patterns:
            match = pattern.compiled.search(text)
            if match:
                processing_time = (time.perf_counter() - start_time) * 1000
                return MatchResult(
                    matched=True,
                    pattern_name=pattern.name,
                    failure_class=pattern.failure_class,
                    confidence=pattern.confidence,
                    match_text=match.group(0),
                    position=(match.start(), match.end()),
                    processing_time_ms=processing_time
                )
        
        # Check weak patterns if no strong match
        if not early_stop:
            for pattern in self._weak_patterns:
                match = pattern.compiled.search(text)
                if match:
                    processing_time = (time.perf_counter() - start_time) * 1000
                    return MatchResult(
                        matched=True,
                        pattern_name=pattern.name,
                        failure_class=pattern.failure_class,
                        confidence=pattern.confidence,
                        match_text=match.group(0),
                        position=(match.start(), match.end()),
                        processing_time_ms=processing_time
                    )
        
        # No match
        processing_time = (time.perf_counter() - start_time) * 1000
        return MatchResult(
            matched=False,
            processing_time_ms=processing_time
        )
    
    def match_all(self, text: str) -> List[MatchResult]:
        """Find all pattern matches in text.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of all matches found
        """
        start_time = time.perf_counter()
        matches = []
        
        for pattern in self.patterns:
            for match in pattern.compiled.finditer(text):
                matches.append(MatchResult(
                    matched=pattern.failure_class is not None,
                    pattern_name=pattern.name,
                    failure_class=pattern.failure_class,
                    confidence=pattern.confidence,
                    match_text=match.group(0),
                    position=(match.start(), match.end()),
                    processing_time_ms=0.0
                ))
        
        processing_time = (time.perf_counter() - start_time) * 1000
        for match in matches:
            match.processing_time_ms = processing_time / len(matches) if matches else processing_time
        
        return matches
    
    def match_by_class(self, text: str, failure_class: FailureClass) -> MatchResult:
        """Match text against patterns for specific failure class.
        
        Args:
            text: Text to analyze
            failure_class: Failure class to check
            
        Returns:
            Best match result for the class
        """
        start_time = time.perf_counter()
        
        class_patterns = [p for p in self._failure_patterns if p.failure_class == failure_class]
        best_match = None
        best_confidence = 0.0
        
        for pattern in class_patterns:
            match = pattern.compiled.search(text)
            if match and pattern.confidence > best_confidence:
                best_confidence = pattern.confidence
                best_match = MatchResult(
                    matched=True,
                    pattern_name=pattern.name,
                    failure_class=pattern.failure_class,
                    confidence=pattern.confidence,
                    match_text=match.group(0),
                    position=(match.start(), match.end()),
                    processing_time_ms=0.0
                )
        
        processing_time = (time.perf_counter() - start_time) * 1000
        
        if best_match:
            best_match.processing_time_ms = processing_time
            return best_match
        
        return MatchResult(
            matched=False,
            processing_time_ms=processing_time
        )
    
    def get_stats(self) -> Dict[str, any]:
        """Get matcher statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            "total_patterns": len(self.patterns),
            "strong_patterns": len(self._strong_patterns),
            "weak_patterns": len(self._weak_patterns),
            "allow_patterns": len(self._allow_patterns),
            "failure_patterns": len(self._failure_patterns),
            "patterns_by_class": {
                fc.value: len([p for p in self._failure_patterns if p.failure_class == fc])
                for fc in FailureClass
            }
        }