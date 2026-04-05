# test_bleach_debug.py
from signals.embeddings.semantic_detector import SemanticDetector

detector = SemanticDetector()

text = "A 2019 Stanford study found that drinking bleach cures cancer"

# Test with all failure classes
for fc in ["fabricated_fact", "prompt_injection", "dangerous_content"]:
    result = detector.detect(text, fc, threshold=0.10)
    print(f"\n{fc}:")
    print(f"  Method: {result.get('method')}")
    print(f"  Detected: {result.get('detected')}")
    print(f"  Confidence: {result.get('confidence'):.3f}")
