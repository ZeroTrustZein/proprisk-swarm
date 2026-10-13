"""High-performance in-memory LRU cache with TTL expiration for MCP queries and embeddings."""

from __future__ import annotations

import functools
import hashlib
import time
from collections import OrderedDict
from typing import Any, Callable, Dict, Optional


class CacheEntry:
    """Cache entry payload containing value and expiration timestamp."""

    __slots__ = ("value", "expires_at")

    def __init__(self, value: Any, expires_at: Optional[float]) -> None:
        self.value = value
        self.expires_at = expires_at

    def is_expired(self, current_time: float) -> bool:
        return self.expires_at is not None and current_time >= self.expires_at


class SubsystemCache:
    """Thread-safe LRU cache with per-item TTL expiration and telemetry."""

    def __init__(self, max_size: int = 1000, default_ttl_seconds: Optional[float] = None) -> None:
        self.max_size = max(1, max_size)
        self.default_ttl = default_ttl_seconds
        self._store: OrderedDict[str, CacheEntry] = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve value by key, checking TTL expiration and updating LRU order."""
        entry = self._store.get(key)
        now = time.time()

        if entry is None:
            self._misses += 1
            return default

        if entry.is_expired(now):
            self._store.pop(key, None)
            self._misses += 1
            return default

        # Move to end for LRU refresh
        self._store.move_to_end(key)
        self._hits += 1
        return entry.value

    def set(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> None:
        """Store value with optional item-specific TTL."""
        now = time.time()
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        expires_at = (now + ttl) if ttl is not None else None

        if key in self._store:
            self._store.pop(key)
        elif len(self._store) >= self.max_size:
            # Evict oldest
            self._store.popitem(last=False)
            self._evictions += 1

        self._store[key] = CacheEntry(value=value, expires_at=expires_at)

    def has(self, key: str) -> bool:
        """Check if active unexpired key exists in cache."""
        entry = self._store.get(key)
        if entry is None:
            return False
        if entry.is_expired(time.time()):
            self._store.pop(key, None)
            return False
        return True

    def delete(self, key: str) -> bool:
        """Explicitly remove a key."""
        return self._store.pop(key, None) is not None

    def clear(self) -> None:
        """Flush cache."""
        self._store.clear()

    def cleanup_expired(self) -> int:
        """Prune all expired entries from cache."""
        now = time.time()
        expired_keys = [k for k, entry in self._store.items() if entry.is_expired(now)]
        for k in expired_keys:
            self._store.pop(k, None)
        return len(expired_keys)

    def stats(self) -> Dict[str, Any]:
        """Return cache health and telemetry."""
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests) if total_requests > 0 else 0.0
        return {
            "size": len(self._store),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
            "hit_rate": round(hit_rate, 4),
        }


def cached(
    cache: SubsystemCache,
    ttl_seconds: Optional[float] = None,
    key_prefix: str = "",
) -> Callable:
    """Decorator to cache function execution results."""

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Build cache key
            raw_key = f"{key_prefix}:{fn.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            hashed_key = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

            cached_val = cache.get(hashed_key)
            if cached_val is not None:
                return cached_val

            result = fn(*args, **kwargs)
            cache.set(hashed_key, result, ttl_seconds=ttl_seconds)
            return result

        return wrapper

    return decorator

