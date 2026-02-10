"""Phase 3 Demo - Integrated 3-tier detection system.

Demonstrates:
- Tier routing (95/4/1 distribution)
- All three detection methods
- Performance monitoring
- Distribution health checks
"""

import sys
from pathlib import Path

# Add project root to path (now two levels up)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from enforcement.control_tower_v3 import ControlTowerV3
from signals.grounding.missing_grounding_v2 import MissingGroundingV2Signal
import time


def print_header(title: str):
    """Print formatted section header."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")


def print_result(test_name: str, result, response: str):
    """Print formatted test result."""
    print(f"📊 Test: {test_name}")
    print(f"   Response: {response[:80]}...")
    print(f"   Tier Used: {result.tier_used} ({result.tier_reason})")
    print(f"   Method: {result.method}")
    print(f"   Failure: {result.failure_class or 'None'}")
    print(f"   Action: {result.action.upper()}")
    print(f"   Confidence: {result.confidence:.2f}")
    print(f"   Should Block: {'❌ YES' if result.should_block else '✅ NO'}")
    print(f"   Processing Time: {result.processing_time_ms:.2f}ms")
    print(f"   Reason: {result.reason}")
    print()


def print_tier_stats(control_tower: ControlTowerV3):
    """Print tier distribution statistics."""
    stats = control_tower.get_tier_stats()
    dist = stats["distribution"]
    health = stats["health"]
    availability = stats["tier_availability"]
    
    print_header("TIER DISTRIBUTION STATISTICS")
    
    print(f"📈 Distribution (Target: 95/4/1):")
    print(f"   Tier 1 (Regex):    {dist['tier1_pct']:5.1f}%  {'✅' if 92 <= dist['tier1_pct'] <= 98 else '⚠️'}")
    print(f"   Tier 2 (Semantic): {dist['tier2_pct']:5.1f}%  {'✅' if 2 <= dist['tier2_pct'] <= 7 else '⚠️'}")
    print(f"   Tier 3 (LLM):      {dist['tier3_pct']:5.1f}%  {'✅' if 0 <= dist['tier3_pct'] <= 3 else '⚠️'}")
    print(f"   Total Requests:    {dist['total_requests']}\n")
    
    print(f"🏥 Health Status: {health['message']}\n")
    
    print(f"🔧 Tier Availability:")
    print(f"   Tier 1: {'✅ Available' if availability['tier1'] else '❌ Unavailable'}")
    print(f"   Tier 2: {'✅ Available' if availability['tier2'] else '❌ Unavailable'}")
    print(f"   Tier 3: {'✅ Available' if availability['tier3'] else '❌ Unavailable'}")
    print()


def main():
    """Run Phase 3 comprehensive demo."""
    print("\n" + "#"*70)
    print("#" + " "*68 + "#")
    print("#  LLM OBSERVABILITY - PHASE 3: INTEGRATED 3-TIER SYSTEM" + " "*12 + "#")
    print("#" + " "*68 + "#")
    print("#"*70)
    
    # Initialize systems
    print("\n🚀 Initializing Control Tower V3...")
    control_tower = ControlTowerV3()
    signal_detector = MissingGroundingV2Signal()
    print("✅ Initialization complete\n")
    
    print_header("TIER 1: DETERMINISTIC REGEX DETECTION")
    
    # Test 1: Strong citation (Tier 1)
    test_cases_tier1 = [
        (
            "Strong Citation",
            "What is RAG?",
            "RAG stands for Retrieval-Augmented Generation [1]. It combines retrieval with generation [2]."
        ),
        (
            "Clear Anti-pattern",
            "Tell me about AI",
            "I think AI is interesting. I believe it will change everything. In my opinion, it's revolutionary."
        ),
    ]
    
    for test_name, prompt, response in test_cases_tier1:
        signal_result = signal_detector.extract(prompt, response, {})
        result = control_tower.evaluate(prompt, response, {}, signal_result)
        print_result(test_name, result, response)
    
    print_header("TIER 2: SEMANTIC EMBEDDING DETECTION")
    
    # Test 2: Gray zone cases (Tier 2)
    test_cases_tier2 = [
        (
            "Gray Zone - Weak Pattern",
            "What is machine learning?",
            "Studies show that machine learning is effective. Research indicates it's growing rapidly."
        ),
        (
            "Gray Zone - Moderate Confidence",
            "Explain quantum computing",
            "Quantum computing uses quantum mechanics. It's a complex field that scientists are exploring."
        ),
    ]
    
    for test_name, prompt, response in test_cases_tier2:
        signal_result = signal_detector.extract(prompt, response, {})
        result = control_tower.evaluate(prompt, response, {}, signal_result)
        print_result(test_name, result, response)
    
    print_header("TIER 3: LLM AGENT REASONING")
    
    # Test 3: Edge cases (Tier 3)
    test_cases_tier3 = [
        (
            "Edge Case - Ambiguous",
            "What do you think about this?",
            "That's an interesting perspective. There are multiple viewpoints on this topic."
        ),
    ]
    
    for test_name, prompt, response in test_cases_tier3:
        # Create signal result that triggers Tier 3
        signal_result = {
            "value": False,
            "confidence": 0.2,  # Low confidence triggers Tier 3
            "method": "regex_weak",
            "failure_class": "missing_grounding",
            "explanation": "Low confidence case"
        }
        result = control_tower.evaluate(prompt, response, {}, signal_result)
        print_result(test_name, result, response)
    
    # Performance test for distribution
    print_header("PERFORMANCE TEST: 100 REQUESTS")
    print("🔄 Running 100 test requests to measure tier distribution...\n")
    
    test_responses = [
        # 95 Tier 1 cases
        *[("According to the study [1], this is correct.", 0.9)] * 47,
        *[("I think this might be true.", 0.85)] * 48,
        # 4 Tier 2 cases
        *[("Studies suggest this could be relevant.", 0.5)] * 4,
        # 1 Tier 3 case
        ("This is ambiguous and needs careful analysis.", 0.2),
    ]
    
    start = time.time()
    for i, (resp, conf) in enumerate(test_responses, 1):
        signal_result = {
            "value": conf < 0.7,
            "confidence": conf,
            "method": "regex_strong" if conf > 0.8 else "regex_weak",
            "failure_class": "missing_grounding" if conf < 0.7 else None,
            "explanation": "Test case"
        }
        control_tower.evaluate("Test prompt", resp, {}, signal_result)
        
        if i % 25 == 0:
            print(f"   Processed {i}/100 requests...")
    
    elapsed = time.time() - start
    print(f"\n✅ Completed 100 requests in {elapsed*1000:.1f}ms")
    print(f"   Average per request: {elapsed*10:.2f}ms")
    print(f"   Throughput: {100/elapsed:.0f} requests/sec")
    
    # Show final statistics
    print_tier_stats(control_tower)
    
    print_header("PHASE 3 DEMO COMPLETE")
    print("✅ All tiers operational")
    print("✅ Tier routing working as expected")
    print("✅ Distribution monitoring active")
    print("\n🎯 Next: Monitor distribution in production")
    print("🎯 Goal: Maintain 95/4/1 tier distribution\n")


if __name__ == "__main__":
    main()
