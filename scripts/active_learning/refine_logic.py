"""Active Learning Loop: Auto-refine embeddings and regex patterns from human feedback."""

import json
import os
import logging
from typing import List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

FEEDBACK_FILE = "data/active_learning_feedback.jsonl"
HARM_DB_FILE = "signals/embeddings/harm_vector_db.json"
REGEX_PATTERNS_FILE = "signals/regex/custom_patterns.json"

def process_feedback_loop():
    """Read feedback and suggest/apply refinements."""
    if not os.path.exists(FEEDBACK_FILE):
        print("No feedback found to process.")
        return

    misclassified = []
    with open(FEEDBACK_FILE, "r") as f:
        for line in f:
            data = json.loads(line)
            if not data.get("is_correct", True):
                misclassified.append(data)

    if not misclassified:
        print("All detections were marked as correct. No refinement needed.")
        return

    print(f"Processing {len(misclassified)} misclassified samples...")
    
    # 1. Update Semantic Embeddings
    refine_embeddings(misclassified)
    
    # 2. Update Regex Patterns
    refine_regex(misclassified)

def refine_embeddings(samples: List[Dict[str, Any]]):
    """Add difficult samples to the harm vector DB."""
    if not os.path.exists(HARM_DB_FILE):
        return
        
    with open(HARM_DB_FILE, "r") as f:
        db = json.load(f)
    
    added_count = 0
    for s in samples:
        label = s.get("actual_label")
        text = s.get("text")
        
        if label and label != "safe" and text:
            # Check if text already in examples
            if label not in db:
                db[label] = []
            
            if text not in db[label]:
                db[label].append(text)
                added_count += 1
                
    if added_count > 0:
        with open(HARM_DB_FILE, "w") as f:
            json.dump(db, f, indent=2)
        print(f"✅ Added {added_count} new examples to {HARM_DB_FILE}")

def refine_regex(samples: List[Dict[str, Any]]):
    """Suggest new regex patterns based on misclassified text."""
    # This is more complex, for now we just log suggestions
    suggestions = []
    for s in samples:
        if s.get("actual_label") != "safe":
            # Simple keyword extraction could happen here
            suggestions.append(f"Suggested pattern for {s['actual_label']}: {s['text'][:50]}...")

    if suggestions:
        print("Suggested Regex Refinements:")
        for sug in suggestions:
            print(f"  - {sug}")

if __name__ == "__main__":
    process_feedback_loop()
