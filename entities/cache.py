"""In-memory cache for dashboard data with TTL support."""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Any, Generic, TypeVar
from dataclasses import dataclass
import structlog

logger = structlog.get_logger()

T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """Cache entry with value and metadata."""
    value: T
    cached_at: datetime
    expires_at: datetime


class EntityCache:
    """Thread-safe in-memory cache with TTL for entity dashboard data."""

    def __init__(self, ttl_seconds: int = 300):
        """Initialize cache with TTL (default 5 minutes)."""
        self._data: Optional[CacheEntry] = None
        self._lock = asyncio.Lock()
        self._ttl = timedelta(seconds=ttl_seconds)
        self._stale_threshold = timedelta(minutes=2)

    @property
    def is_valid(self) -> bool:
        """Check if cache has valid (non-expired) data."""
        if self._data is None:
            return False
        return datetime.utcnow() < self._data.expires_at

    @property
    def is_stale(self) -> bool:
        """Check if cache is older than 2 minutes (stale but valid)."""
        if self._data is None:
            return True
        age = datetime.utcnow() - self._data.cached_at
        return age > self._stale_threshold

    @property
    def cached_at(self) -> Optional[datetime]:
        """Get cache timestamp."""
        return self._data.cached_at if self._data else None

    @property
    def ttl_remaining(self) -> int:
        """Get remaining TTL in seconds."""
        if self._data is None:
            return 0
        remaining = self._data.expires_at - datetime.utcnow()
        return max(0, int(remaining.total_seconds()))

    async def get(self) -> Optional[Any]:
        """Get cached value if valid."""
        async with self._lock:
            if not self.is_valid:
                logger.debug("cache_miss")
                return None
            logger.debug("cache_hit", age_seconds=(datetime.utcnow() - self._data.cached_at).seconds)
            return self._data.value

    async def set(self, value: Any) -> None:
        """Set cache value with TTL."""
        async with self._lock:
            now = datetime.utcnow()
            self._data = CacheEntry(
                value=value,
                cached_at=now,
                expires_at=now + self._ttl
            )
            logger.info("cache_set", ttl_seconds=self._ttl.seconds)

    async def invalidate(self) -> None:
        """Clear cache."""
        async with self._lock:
            self._data = None
            logger.info("cache_invalidated")

    def get_metadata(self) -> dict:
        """Get cache metadata for response."""
        return {
            "cached_at": self._data.cached_at.isoformat() if self._data else None,
            "is_stale": self.is_stale,
            "ttl_remaining_seconds": self.ttl_remaining
        }


# Global singleton instance
_dashboard_cache: Optional[EntityCache] = None


def get_dashboard_cache() -> EntityCache:
    """Get or create dashboard cache singleton."""
    global _dashboard_cache
    if _dashboard_cache is None:
        _dashboard_cache = EntityCache(ttl_seconds=300)
    return _dashboard_cache

