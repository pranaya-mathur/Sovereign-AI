"""Tier routing logic for 3-tier detection system.

Routes requests to appropriate detection tier based on confidence:
- Tier 1: High confidence regex matches (>80%)
- Tier 2: Medium confidence semantic analysis (15-80%)
- Tier 3: Low/uncertain confidence LLM reasoning (<15% or gray zone)
"""

import logging
from dataclasses import dataclass
from typing import Dict, Any, Tuple, Optional, List

from providers.external_moderation import fuse_external_with_tier1

logger = logging.getLogger(__name__)


@dataclass
class TierDecision:
    """Decision about which tier to use."""
    tier: int  # 1, 2, or 3
    reason: str  # Why this tier was chosen
    method: str = "unknown"
    confidence: float = 0.0


class TierRouter:
    """Routes detection requests to appropriate tier based on confidence."""
    
    def __init__(
        self, 
        tier1_strong_threshold: float = 0.80, 
        tier1_weak_threshold: float = 0.15,
        tier2_threshold: float = 0.70  # Note: mapping test's expectations
    ):
        """Initialize tier router with threshold defaults and stats tracking.
        
        Args:
            tier1_strong_threshold: Default cutoff for Tier 1
            tier1_weak_threshold: Default cutoff for Tier 2/3 boundary
            tier2_threshold: Reserved for backward compatibility
        """
        self.tier1_strong_threshold = tier1_strong_threshold
        self.tier1_weak_threshold = tier1_weak_threshold
        self.tier2_threshold = tier2_threshold
        
        self.tier_stats = {
            "total": 0,
            "tier1": 0,
            "tier2": 0,
            "tier3": 0
        }
    
    def route(
        self, 
        tier1_result: Dict[str, Any], 
        tier1_cutoff: Optional[float] = None, 
        tier2_cutoff: Optional[float] = None,
        history: Optional[List[Dict[str, Any]]] = None
    ) -> TierDecision:
        """Route to appropriate tier based on Tier 1 confidence and optional session history.
        
        Priority:
        1. Explicit cutoffs passed to this method
        2. Thresholds provided during initialization
        3. History-based adjustments (e.g. repeated warnings escalate to Tier 3)
        
        Args:
            tier1_result: Result dictionary from Tier 1 detection
            tier1_cutoff: Optional override for Tier 1 finality cutoff
            tier2_cutoff: Optional override for Tier 2 semantic cutoff
            history: Optional list of previous turns in this session
            
        Returns:
            TierDecision indicating which tier to use
        """
        self.tier_stats["total"] += 1
        
        # Determine active cutoffs
        t1_cutoff = tier1_cutoff if tier1_cutoff is not None else self.tier1_strong_threshold
        t2_cutoff = tier2_cutoff if tier2_cutoff is not None else self.tier1_weak_threshold
        
        confidence = tier1_result.get("confidence", 0.5)
        method = tier1_result.get("method", "unknown")
        
        # ✅ MULTI-TURN ESCALATION: If history shows multiple warnings, be more suspicious
        if history:
            warning_count = sum(1 for turn in history if turn.get("status") in ["warn", "warned"])
            if warning_count >= 2:
                # Force escalation to at least Tier 2, if not Tier 3
                if confidence > t2_cutoff:
                    t1_cutoff = 0.99 # Force Tier 2/3 unless extremely high confidence
                else:
                    t2_cutoff = 0.5 # Lower Tier 3 threshold
                
                logger.info(f"Escalating due to session history ({warning_count} previous warnings)")

        # Tier 1: High confidence match (>= cutoff) from TRUSTED regex methods
        is_trusted_method = method in ["regex_strong", "regex_anti", "regex_pathological", "regex_length_check", "regex_uncertain"]
        
        if confidence >= t1_cutoff:
            if is_trusted_method:
                self.tier_stats["tier1"] += 1
                return TierDecision(
                    tier=1, 
                    method=method,
                    reason=f"High confidence regex match ({confidence:.0%})",
                    confidence=confidence
                )
            else:
                # Untrusted high-confidence signal: send to Tier 3 for verification
                self.tier_stats["tier3"] += 1
                return TierDecision(
                    tier=3,
                    method="llm_agent",
                    reason=f"Untrusted high-confidence method ({method}) - needs verification",
                    confidence=confidence
                )
        
        # Tier 3: Gray zone (5% to t2_cutoff)
        elif 0.05 <= confidence < t2_cutoff:
            self.tier_stats["tier3"] += 1
            return TierDecision(
                tier=3,
                method="llm_agent",
                reason=f"Gray zone confidence ({confidence:.0%}) - needs LLM reasoning",
                confidence=confidence
            )
        
        # Tier 2: Medium confidence (>= t2_cutoff and < t1_cutoff)
        elif confidence >= t2_cutoff:
            self.tier_stats["tier2"] += 1
            return TierDecision(
                tier=2,
                method="semantic",
                reason=f"Medium confidence ({confidence:.0%}) - semantic analysis",
                confidence=confidence
            )
        
        # Tier 3: Very low confidence (< 5%)
        else:
            self.tier_stats["tier3"] += 1
            return TierDecision(
                tier=3,
                method="llm_agent",
                reason=f"Very low confidence ({confidence:.0%}) - needs deep analysis",
                confidence=confidence
            )
    
    def get_distribution(self) -> Dict[str, float]:
        """Get percentage distribution across tiers.
        
        Returns:
            Dictionary with tier percentages
        """
        total = self.tier_stats["total"]
        if total == 0:
            return {
                "tier1_pct": 0.0,
                "tier2_pct": 0.0,
                "tier3_pct": 0.0
            }
        
        return {
            "total_requests": total,  # Restored key
            "tier1_pct": (self.tier_stats["tier1"] / total) * 100,
            "tier2_pct": (self.tier_stats["tier2"] / total) * 100,
            "tier3_pct": (self.tier_stats["tier3"] / total) * 100
        }
    
    def check_distribution_health(self) -> Tuple[bool, str]:
        """Check if tier distribution is healthy (close to 95/4/1 target).
        
        Returns:
            Tuple of (is_healthy, message)
        """
        if self.tier_stats["total"] < 100:
            return True, "Not enough data for healthy distribution check (< 100 requests)"
            
        dist = self.get_distribution()
        
        # Target: 95% Tier 1, 4% Tier 2, 1% Tier 3
        # Allow some variance: Tier 1 (90-98%), Tier 2 (2-8%), Tier 3 (0-5%)
        tier1_ok = 90 <= dist["tier1_pct"] <= 98
        tier2_ok = 2 <= dist["tier2_pct"] <= 8
        tier3_ok = 0 <= dist["tier3_pct"] <= 5
        
        if tier1_ok and tier2_ok and tier3_ok:
            return True, "Distribution healthy (close to 95/4/1 target)"
        
        # Generate helpful message
        issues = []
        if not tier1_ok:
            issues.append(f"Tier1: {dist['tier1_pct']:.1f}%")  # Restored "Tier1" (no space)
        if not tier2_ok:
            issues.append(f"Tier2: {dist['tier2_pct']:.1f}%")
        if not tier3_ok:
            issues.append(f"Tier3: {dist['tier3_pct']:.1f}%")
        
        return False, f"Distribution issues: {', '.join(issues)}"
    
    def reset_stats(self):
        """Reset tier statistics."""
        self.tier_stats = {
            "total": 0,
            "tier1": 0,
            "tier2": 0,
            "tier3": 0
        }

    @staticmethod
    def fuse_external(
        tier1_result: Dict[str, Any],
        external: Optional[Dict[str, Any]],
        fuse_weight: float = 0.35,
    ) -> Dict[str, Any]:
        """Fuse external moderation scores into Tier-1 regex output before routing."""
        return fuse_external_with_tier1(tier1_result, external, fuse_weight)
