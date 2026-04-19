"""RAG-specific rails for faithfulness, citation, and grounding checks."""

from typing import Dict, Any, List, Optional
import logging
import re
from signals.embeddings.semantic_detector import SemanticDetector, truncate_text_for_embeddings
from signals.embeddings.qdrant_client import get_qdrant_client

logger = logging.getLogger(__name__)

class RAGRail:
    """Implements faithfulness and grounding checks for RAG pipelines."""
    
    def __init__(self, semantic_detector: Optional[SemanticDetector] = None):
        self.detector = semantic_detector or SemanticDetector()
        self.qdrant = get_qdrant_client()

    def check_faithfulness(
        self, 
        response: str, 
        retrieved_context: Optional[str] = None,
        threshold: float = 0.65
    ) -> Dict[str, Any]:
        """
        Check if the response is faithful to the retrieved context.
        
        Args:
            response: LLM generated response
            retrieved_context: Context provided to the LLM
            threshold: Minimum similarity score for faithfulness
            
        Returns:
            Dictionary with score and evaluation
        """
        if not retrieved_context:
            return {"score": 0.0, "status": "skipped", "reason": "no_context"}
            
        # 1. Lexical overlap as fast baseline (with strict entity penalty)
        score = self._lexical_overlap(response, retrieved_context)
        
        # 2. Semantic baseline only if no stark hallucinations were found lexically
        # If score is 0, it means a hallucinated entity was detected; don't fall back.
        if 0.0 < score < threshold:
            # Encode response and context
            resp_emb = self.detector._encode_text_safe(response)
            ctx_emb = self.detector._encode_text_safe(truncate_text_for_embeddings(retrieved_context))
            
            if resp_emb is not None and ctx_emb is not None:
                import numpy as np
                score = float(np.dot(resp_emb, ctx_emb))
        
        status = "faithful" if score >= threshold else "unfaithful"
        
        return {
            "score": score,
            "status": status,
            "method": "hybrid_semantic_lexical"
        }

    def check_citations(self, response: str) -> Dict[str, Any]:
        """Verify presence and format of citations (e.g., [1], [Source])."""
        citation_patterns = [
            r"\[\d+\]",       # [1], [2]
            r"\[Source:.*?\]", # [Source: File.pdf]
            r"\(Source:.*?\)", # (Source: Page 5)
            r"Source:.*",      # Source: ... at end of line
        ]
        
        found = []
        for pattern in citation_patterns:
            matches = re.findall(pattern, response)
            found.extend(matches)
            
        has_citations = len(found) > 0
        
        return {
            "has_citations": has_citations,
            "citation_count": len(found),
            "citations_found": list(set(found))[:5] # Limit to first 5
        }

    def verify_grounding_with_qdrant(
        self, 
        response: str, 
        collection_name: str = "kb_grounding"
    ) -> Dict[str, Any]:
        """Verify if response claims are grounded in a trusted Qdrant knowledge base."""
        if not self.qdrant.client:
            return {"grounded": True, "reason": "qdrant_disabled"}
            
        resp_emb = self.detector._encode_text_safe(response)
        if resp_emb is None:
            return {"grounded": True, "reason": "embedding_failure"}
            
        # Search for supporting evidence in Qdrant
        results = self.qdrant.search_similar_docs(
            collection_name=collection_name,
            vector=resp_emb.tolist(),
            limit=2
        )
        
        if not results:
            return {"grounded": False, "reason": "no_supporting_evidence_in_kb", "best_score": 0.0}
            
        best_score = results[0]["score"]
        # Standard threshold for grounding in KB
        grounded = best_score > 0.75
        
        return {
            "grounded": grounded,
            "best_score": best_score,
            "best_match_preview": results[0]["content"][:100] if grounded else None
        }

    def _lexical_overlap(self, a: str, b: str) -> float:
        """Entity-aware lexical overlap with stopword filtering."""
        STOPWORDS = {"accounting", "according", "context", "this", "that", "those", "these", "where", "there"}
        
        def get_tokens(s):
            # Extract words >= 3 chars, but also keep numbers and Capitalized words
            words = re.findall(r"\b[A-Z0-9]\w*\b|\b\w{3,}\b", s)
            return [w for w in words if w.lower() not in STOPWORDS]
            
        tokens_a = get_tokens(a)
        tokens_b = get_tokens(b)
        
        if not tokens_a:
            return 0.0
            
        # Proper Nouns / Numbers check (Entities)
        entities_a = {w for w in tokens_a if w[0].isupper() or any(c.isdigit() for c in w)}
        entities_b = {w for w in tokens_b if w[0].isupper() or any(c.isdigit() for c in w)}
        
        if entities_a:
            # Check for hallucinated entities (in A but not in B)
            # Use lowercase for comparison to be case-insensitive but still catch proper nouns
            ents_a_lower = {e.lower() for e in entities_a}
            ents_b_lower = {e.lower() for e in entities_b}
            hallucinated = ents_a_lower - ents_b_lower
            
            if hallucinated:
                # Direct failure if any entity is hallucinated
                return 0.0
                
            entity_overlap = len(ents_a_lower & ents_b_lower)
            entity_score = entity_overlap / len(ents_a_lower)
            if entity_score < 0.5:
                return 0.0
                
        # General token overlap
        set_a, set_b = set(tokens_a), set(tokens_b)
        intersection = len(set_a & set_b)
        coverage = intersection / len(set_a)
        
        return coverage
