"""Qdrant client integration for RAG-specific rails and grounding verification."""

from typing import List, Dict, Any, Optional
import os
import logging
from qdrant_client import QdrantClient
from qdrant_client.http import models

logger = logging.getLogger(__name__)

class SovereignQdrantClient:
    """Manages connection and operations for Qdrant Vector DB."""
    
    def __init__(self, url: Optional[str] = None, api_key: Optional[str] = None):
        url = url or os.getenv("QDRANT_URL", "http://localhost:6333")
        api_key = api_key or os.getenv("QDRANT_API_KEY")
        
        try:
            self.client = QdrantClient(url=url, api_key=api_key)
            logger.info(f"Connected to Qdrant at {url}")
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            self.client = None

    def search_similar_docs(
        self, 
        collection_name: str, 
        vector: List[float], 
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """Search for similar documents in Qdrant."""
        if not self.client:
            return []
            
        try:
            results = self.client.search(
                collection_name=collection_name,
                query_vector=vector,
                limit=limit
            )
            return [
                {
                    "content": hit.payload.get("content", ""),
                    "metadata": hit.payload.get("metadata", {}),
                    "score": hit.score
                }
                for hit in results
            ]
        except Exception as e:
            logger.error(f"Qdrant search failed: {e}")
            return []

    def ensure_collection(self, collection_name: str, vector_size: int = 384):
        """Ensure collection exists in Qdrant."""
        if not self.client:
            return
            
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == collection_name for c in collections)
            
            if not exists:
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=models.VectorParams(
                        size=vector_size, 
                        distance=models.Distance.COSINE
                    )
                )
                logger.info(f"Created collection '{collection_name}' in Qdrant")
        except Exception as e:
            logger.error(f"Failed to ensure Qdrant collection: {e}")

_instance = None

def get_qdrant_client() -> SovereignQdrantClient:
    """Singleton getter for Qdrant client."""
    global _instance
    if _instance is None:
        _instance = SovereignQdrantClient()
    return _instance
