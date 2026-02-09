"""Unit tests for tier router.

Tests:
- Tier 1 routing (strong patterns)
- Tier 2 routing (gray zone)
- Tier 3 routing (edge cases)
- Distribution tracking
- Health checks
"""

import unittest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from enforcement.tier_router import TierRouter, TierDecision


class TestTierRouter(unittest.TestCase):
    """Test cases for TierRouter."""

    def setUp(self):
        """Set up test fixtures."""
        self.router = TierRouter(
            tier1_strong_threshold=0.8,
            tier1_weak_threshold=0.3,
            tier2_threshold=0.75
        )

    def test_tier1_strong_pattern(self):
        """Test Tier 1 routing for strong regex patterns."""
        signal_result = {
            "confidence": 0.9,
            "method": "regex_strong",
            "value": False,
            "failure_class": None
        }
        
        decision = self.router.route(signal_result)
        
        self.assertEqual(decision.tier, 1)
        self.assertEqual(decision.method, "regex_strong")
        self.assertEqual(decision.confidence, 0.9)
        self.assertIn("High confidence", decision.reason)

    def test_tier1_anti_pattern(self):
        """Test Tier 1 routing for clear anti-patterns."""
        signal_result = {
            "confidence": 0.85,
            "method": "regex_anti",
            "value": True,
            "failure_class": "missing_grounding"
        }
        
        decision = self.router.route(signal_result)
        
        self.assertEqual(decision.tier, 1)
        self.assertEqual(decision.method, "regex_anti")
        self.assertIn("anti-pattern", decision.reason.lower())

    def test_tier2_gray_zone(self):
        """Test Tier 2 routing for gray zone cases."""
        signal_result = {
            "confidence": 0.5,
            "method": "regex_weak",
            "value": True,
            "failure_class": "missing_grounding"
        }
        
        decision = self.router.route(signal_result)
        
        self.assertEqual(decision.tier, 2)
        self.assertEqual(decision.method, "semantic")
        self.assertIn("Gray zone", decision.reason)

    def test_tier3_edge_case_low_confidence(self):
        """Test Tier 3 routing for low confidence edge cases."""
        signal_result = {
            "confidence": 0.2,
            "method": "regex_weak",
            "value": False,
            "failure_class": None
        }
        
        decision = self.router.route(signal_result)
        
        self.assertEqual(decision.tier, 3)
        self.assertEqual(decision.method, "llm_agent")
        self.assertIn("Edge case", decision.reason)

    def test_tier3_edge_case_high_confidence_non_standard(self):
        """Test Tier 3 routing for non-standard high confidence cases."""
        signal_result = {
            "confidence": 0.9,
            "method": "custom",  # Not regex_strong or regex_anti
            "value": True,
            "failure_class": "unknown"
        }
        
        decision = self.router.route(signal_result)
        
        self.assertEqual(decision.tier, 3)
        self.assertEqual(decision.method, "llm_agent")

    def test_distribution_tracking(self):
        """Test tier distribution tracking."""
        # Simulate 100 requests with 95/4/1 distribution
        
        # 95 Tier 1 cases
        for _ in range(95):
            signal = {"confidence": 0.9, "method": "regex_strong", "value": False}
            self.router.route(signal)
        
        # 4 Tier 2 cases
        for _ in range(4):
            signal = {"confidence": 0.5, "method": "regex_weak", "value": True}
            self.router.route(signal)
        
        # 1 Tier 3 case
        signal = {"confidence": 0.2, "method": "regex_weak", "value": False}
        self.router.route(signal)
        
        dist = self.router.get_distribution()
        
        self.assertEqual(dist["total_requests"], 100)
        self.assertEqual(dist["tier1_pct"], 95.0)
        self.assertEqual(dist["tier2_pct"], 4.0)
        self.assertEqual(dist["tier3_pct"], 1.0)

    def test_distribution_health_check_healthy(self):
        """Test health check with healthy distribution."""
        # Create healthy 95/4/1 distribution
        for _ in range(95):
            signal = {"confidence": 0.9, "method": "regex_strong", "value": False}
            self.router.route(signal)
        
        for _ in range(4):
            signal = {"confidence": 0.5, "method": "regex_weak", "value": True}
            self.router.route(signal)
        
        signal = {"confidence": 0.2, "method": "regex_weak", "value": False}
        self.router.route(signal)
        
        is_healthy, message = self.router.check_distribution_health()
        
        self.assertTrue(is_healthy)
        self.assertIn("Healthy", message)
        self.assertIn("✅", message)

    def test_distribution_health_check_unhealthy_tier1(self):
        """Test health check with unhealthy Tier 1 distribution."""
        # Create unhealthy distribution (Tier 1 too low)
        for _ in range(85):  # Only 85% Tier 1
            signal = {"confidence": 0.9, "method": "regex_strong", "value": False}
            self.router.route(signal)
        
        for _ in range(15):  # 15% Tier 2 (too high)
            signal = {"confidence": 0.5, "method": "regex_weak", "value": True}
            self.router.route(signal)
        
        is_healthy, message = self.router.check_distribution_health()
        
        self.assertFalse(is_healthy)
        self.assertIn("Tier1", message)
        self.assertIn("⚠️", message)

    def test_distribution_health_check_insufficient_data(self):
        """Test health check with insufficient data."""
        # Only 10 requests
        for _ in range(10):
            signal = {"confidence": 0.9, "method": "regex_strong", "value": False}
            self.router.route(signal)
        
        is_healthy, message = self.router.check_distribution_health()
        
        self.assertTrue(is_healthy)  # Returns True but with warning
        self.assertIn("Not enough data", message)

    def test_reset_stats(self):
        """Test statistics reset."""
        # Add some data
        for _ in range(50):
            signal = {"confidence": 0.9, "method": "regex_strong", "value": False}
            self.router.route(signal)
        
        self.assertEqual(self.router.tier_stats["total"], 50)
        
        # Reset
        self.router.reset_stats()
        
        self.assertEqual(self.router.tier_stats["total"], 0)
        self.assertEqual(self.router.tier_stats["tier1"], 0)
        self.assertEqual(self.router.tier_stats["tier2"], 0)
        self.assertEqual(self.router.tier_stats["tier3"], 0)

    def test_tier_decision_dataclass(self):
        """Test TierDecision dataclass properties."""
        decision = TierDecision(
            tier=1,
            method="regex_strong",
            reason="Test reason",
            confidence=0.9
        )
        
        self.assertEqual(decision.tier, 1)
        self.assertEqual(decision.method, "regex_strong")
        self.assertEqual(decision.reason, "Test reason")
        self.assertEqual(decision.confidence, 0.9)

    def test_boundary_conditions(self):
        """Test boundary conditions for tier thresholds."""
        # Exactly at tier1_strong threshold (0.8)
        signal = {"confidence": 0.8, "method": "regex_strong", "value": False}
        decision = self.router.route(signal)
        self.assertEqual(decision.tier, 1)
        
        # Just below tier1_strong threshold
        signal = {"confidence": 0.79, "method": "regex_strong", "value": False}
        decision = self.router.route(signal)
        self.assertEqual(decision.tier, 3)  # Falls through to Tier 3
        
        # Exactly at tier1_weak threshold (0.3)
        signal = {"confidence": 0.3, "method": "regex_weak", "value": True}
        decision = self.router.route(signal)
        self.assertEqual(decision.tier, 3)
        
        # Just above tier1_weak threshold
        signal = {"confidence": 0.31, "method": "regex_weak", "value": True}
        decision = self.router.route(signal)
        self.assertEqual(decision.tier, 2)

    def test_custom_thresholds(self):
        """Test router with custom thresholds."""
        custom_router = TierRouter(
            tier1_strong_threshold=0.9,
            tier1_weak_threshold=0.2,
            tier2_threshold=0.7
        )
        
        # Should go to Tier 3 (below new strong threshold)
        signal = {"confidence": 0.85, "method": "regex_strong", "value": False}
        decision = custom_router.route(signal)
        self.assertEqual(decision.tier, 3)
        
        # Should go to Tier 1 (above new strong threshold)
        signal = {"confidence": 0.95, "method": "regex_strong", "value": False}
        decision = custom_router.route(signal)
        self.assertEqual(decision.tier, 1)


if __name__ == "__main__":
    unittest.main()
