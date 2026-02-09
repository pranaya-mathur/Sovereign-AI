"""Storage backend for rate limiting."""

from typing import Dict, Optional
from datetime import datetime, timedelta
import time
from threading import Lock


class RateLimitStore:
    """In-memory rate limit storage with automatic expiration.
    
    In production, use Redis for distributed rate limiting.
    """
    
    def __init__(self, window_seconds: int = 3600):
        """Initialize rate limit store.
        
        Args:
            window_seconds: Time window for rate limiting (default: 1 hour)
        """
        self.window_seconds = window_seconds
        self._store: Dict[str, Dict[str, any]] = {}
        self._lock = Lock()
    
    def increment(self, key: str) -> int:
        """Increment counter for key.
        
        Args:
            key: Rate limit key
            
        Returns:
            New count value
        """
        with self._lock:
            now = time.time()
            
            # Initialize or reset if expired
            if key not in self._store:
                self._store[key] = {
                    "count": 0,
                    "start_time": now,
                    "expires_at": now + self.window_seconds
                }
            elif now >= self._store[key]["expires_at"]:
                # Window expired, reset
                self._store[key] = {
                    "count": 0,
                    "start_time": now,
                    "expires_at": now + self.window_seconds
                }
            
            # Increment
            self._store[key]["count"] += 1
            return self._store[key]["count"]
    
    def get_count(self, key: str) -> int:
        """Get current count for key.
        
        Args:
            key: Rate limit key
            
        Returns:
            Current count
        """
        with self._lock:
            if key not in self._store:
                return 0
            
            now = time.time()
            if now >= self._store[key]["expires_at"]:
                return 0
            
            return self._store[key]["count"]
    
    def get_ttl(self, key: str) -> int:
        """Get time-to-live for key in seconds.
        
        Args:
            key: Rate limit key
            
        Returns:
            Seconds until reset
        """
        with self._lock:
            if key not in self._store:
                return self.window_seconds
            
            now = time.time()
            ttl = int(self._store[key]["expires_at"] - now)
            return max(0, ttl)
    
    def reset(self, key: str) -> None:
        """Reset counter for key.
        
        Args:
            key: Rate limit key
        """
        with self._lock:
            if key in self._store:
                del self._store[key]
    
    def cleanup_expired(self) -> int:
        """Remove expired entries.
        
        Returns:
            Number of entries removed
        """
        with self._lock:
            now = time.time()
            expired_keys = [
                key for key, data in self._store.items()
                if now >= data["expires_at"]
            ]
            
            for key in expired_keys:
                del self._store[key]
            
            return len(expired_keys)
    
    def get_all_stats(self) -> Dict[str, Dict[str, any]]:
        """Get statistics for all keys.
        
        Returns:
            Dictionary of all rate limit stats
        """
        with self._lock:
            now = time.time()
            return {
                key: {
                    "count": data["count"],
                    "ttl": int(data["expires_at"] - now),
                    "expired": now >= data["expires_at"]
                }
                for key, data in self._store.items()
            }


class RedisRateLimitStore(RateLimitStore):
    """Redis-backed rate limit storage for production use.
    
    Requires redis-py package.
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379", window_seconds: int = 3600):
        """Initialize Redis rate limit store.
        
        Args:
            redis_url: Redis connection URL
            window_seconds: Time window for rate limiting
        """
        try:
            import redis
            self.redis_client = redis.from_url(redis_url)
            self.window_seconds = window_seconds
        except ImportError:
            raise ImportError("redis package required for RedisRateLimitStore. Install with: pip install redis")
    
    def increment(self, key: str) -> int:
        """Increment counter in Redis."""
        pipe = self.redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, self.window_seconds)
        results = pipe.execute()
        return results[0]
    
    def get_count(self, key: str) -> int:
        """Get current count from Redis."""
        count = self.redis_client.get(key)
        return int(count) if count else 0
    
    def get_ttl(self, key: str) -> int:
        """Get TTL from Redis."""
        ttl = self.redis_client.ttl(key)
        return max(0, ttl) if ttl > 0 else self.window_seconds
    
    def reset(self, key: str) -> None:
        """Delete key from Redis."""
        self.redis_client.delete(key)