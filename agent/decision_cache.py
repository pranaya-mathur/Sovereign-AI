"""Hash-based LLM result caching for deterministic responses.

Caches LLM agent decisions to achieve 99% deterministic behavior.
Only 1% edge cases require actual LLM calls.
"""

import hashlib
import json
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path


class DecisionCache:
    """In-memory cache with hash-based lookups for LLM decisions."""

    def __init__(self, cache_dir: str = ".cache/decisions", ttl_hours: int = 168):
        """
        Initialize decision cache.

        Args:
            cache_dir: Directory for persistent cache storage
            ttl_hours: Cache entry time-to-live (default 7 days)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = timedelta(hours=ttl_hours)
        self.hits = 0
        self.misses = 0
        self._load_cache()

    def _compute_hash(self, prompt: str, context: Dict[str, Any]) -> str:
        """Generate deterministic hash from prompt and context."""
        # Sort context keys for consistent hashing
        context_str = json.dumps(context, sort_keys=True)
        combined = f"{prompt}||{context_str}"
        return hashlib.sha256(combined.encode()).hexdigest()

    def get(self, prompt: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Retrieve cached decision if available and not expired."""
        cache_key = self._compute_hash(prompt, context)

        if cache_key in self.cache:
            entry = self.cache[cache_key]
            cached_time = datetime.fromisoformat(entry["timestamp"])

            # Check if expired
            if datetime.now() - cached_time < self.ttl:
                entry["cache_hit"] = True
                self.hits += 1
                return entry
            else:
                # Remove expired entry
                del self.cache[cache_key]
                self._save_cache()

        self.misses += 1
        return None

    def set(
        self,
        prompt: str,
        context: Dict[str, Any],
        decision: str,
        confidence: float,
        reasoning: str,
    ) -> None:
        """Store LLM decision in cache."""
        cache_key = self._compute_hash(prompt, context)

        entry = {
            "decision": decision,
            "confidence": confidence,
            "reasoning": reasoning,
            "timestamp": datetime.now().isoformat(),
            "cache_hit": False,
        }

        self.cache[cache_key] = entry
        self._save_cache()

    def _load_cache(self) -> None:
        """Load cache from disk."""
        cache_file = self.cache_dir / "decisions.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r") as f:
                    self.cache = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.cache = {}

    def _save_cache(self) -> None:
        """Persist cache to disk."""
        cache_file = self.cache_dir / "decisions.json"
        try:
            with open(cache_file, "w") as f:
                json.dump(self.cache, f, indent=2)
        except IOError:
            pass  # Silent fail on write errors

    def clear_expired(self) -> int:
        """Remove all expired entries. Returns count of removed entries."""
        expired_keys = []
        now = datetime.now()

        for key, entry in self.cache.items():
            cached_time = datetime.fromisoformat(entry["timestamp"])
            if now - cached_time >= self.ttl:
                expired_keys.append(key)

        for key in expired_keys:
            del self.cache[key]

        if expired_keys:
            self._save_cache()

        return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0.0
        
        return {
            "size": len(self.cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "total_entries": len(self.cache),
            "cache_dir": str(self.cache_dir),
            "ttl_hours": self.ttl.total_seconds() / 3600,
        }
