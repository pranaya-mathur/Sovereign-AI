"""Unit tests for semantic detector."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import unittest
from signals.embeddings.semantic_detector import SemanticDetector


class TestSemanticDetector(unittest.TestCase):
    """Test suite for SemanticDetector."""
    
    @classmethod
    def setUpClass(cls):
        """Initialize detector once for all tests."""
        cls.detector = SemanticDetector()
    
    def test_initialization(self):
        """Test detector initializes correctly."""
        self.assertIsNotNone(self.detector.model)
        self.assertGreater(len(self.detector.pattern_embeddings), 0)
        
        supported_classes = self.detector.get_supported_failure_classes()
        self.assertIn("fabricated_concept", supported_classes)
        self.assertIn("missing_grounding", supported_classes)
    
    def test_fabricated_concept_detection(self):
        """Test detection of fabricated concepts."""
        # Positive case
        response = "RAG stands for Ruthenium-Arsenic Growth, a chemical process."
        result = self.detector.detect(response, "fabricated_concept")
        
        self.assertTrue(result["detected"])
        self.assertGreater(result["confidence"], 0.7)
        self.assertEqual(result["method"], "embedding")
    
    def test_missing_grounding_detection(self):
        """Test detection of missing grounding."""
        # Positive case (missing grounding)
        response = "This is definitely true without any sources or citations."
        result = self.detector.detect(response, "missing_grounding")
        
        self.assertIn("confidence", result)
        self.assertIn("explanation", result)
    
    def test_short_response_handling(self):
        """Test handling of very short responses."""
        result = self.detector.detect("Hi", "missing_grounding")
        
        self.assertFalse(result["detected"])
        self.assertEqual(result["confidence"], 0.0)
        self.assertIn("too short", result["explanation"].lower())
    
    def test_determinism(self):
        """Test that same input produces same output."""
        response = "This is a test response for determinism."
        
        result1 = self.detector.detect(response, "missing_grounding")
        result2 = self.detector.detect(response, "missing_grounding")
        
        self.assertEqual(result1["confidence"], result2["confidence"])
        self.assertEqual(result1["detected"], result2["detected"])
    
    def test_caching(self):
        """Test that LRU cache is working."""
        response = "Cached test response"
        
        # First call
        self.detector.detect(response, "missing_grounding")
        
        # Second call should hit cache
        cache_info = self.detector.detect.cache_info()
        initial_hits = cache_info.hits
        
        self.detector.detect(response, "missing_grounding")
        
        cache_info = self.detector.detect.cache_info()
        self.assertGreater(cache_info.hits, initial_hits)
    
    def test_batch_detection(self):
        """Test batch detection functionality."""
        responses = [
            "First test response",
            "Second test response",
            "Third test response"
        ]
        
        results = self.detector.batch_detect(responses, "missing_grounding")
        
        self.assertEqual(len(results), len(responses))
        for result in results:
            self.assertIn("detected", result)
            self.assertIn("confidence", result)
    
    def test_unknown_failure_class(self):
        """Test handling of unknown failure class."""
        response = "Test response"
        result = self.detector.detect(response, "unknown_failure_type")
        
        # Should return low confidence, not crash
        self.assertIn("confidence", result)


if __name__ == "__main__":
    unittest.main()
