#!/usr/bin/env python3
"""
Advanced Cache Manager for NetSentinel
Implements multi-level caching with TTL, eviction policies, and memory management
Designed for maintainability and preventing code debt
"""

import asyncio
import time
import threading
import weakref
from typing import Dict, List, Optional, Any, Union, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import hashlib
from collections import OrderedDict, defaultdict
import gc

from .exceptions import NetSentinelException, ConfigurationError
from ..monitoring.logger import create_logger, get_structured_logger

logger = create_logger("cache_manager", level="INFO")
structured_logger = get_structured_logger("cache_manager")


class CacheLevel(Enum):
    """Cache level enumeration"""

    L1 = "l1"  # In-memory
    L2 = "l2"  # Redis
    L3 = "l3"  # Database


class EvictionPolicy(Enum):
    """Eviction policy enumeration"""

    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    SIZE = "size"  # Size-based


@dataclass
class CacheConfig:
    """Cache configuration"""

    max_size: int = 1000
    default_ttl: int = 3600  # 1 hour
    eviction_policy: EvictionPolicy = EvictionPolicy.LRU
    cleanup_interval: int = 300  # 5 minutes
    max_memory_mb: int = 100
    compression_enabled: bool = True
    serialization_enabled: bool = True


@dataclass
class CacheEntry:
    """Cache entry"""

    key: str
    value: Any
    created_at: float
    last_accessed: float
    access_count: int = 0
    ttl: Optional[int] = None
    size_bytes: int = 0

    @property
    def is_expired(self) -> bool:
        """Check if entry is expired"""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl

    @property
    def age(self) -> float:
        """Get entry age in seconds"""
        return time.time() - self.created_at

    def touch(self) -> None:
        """Update access information"""
        self.last_accessed = time.time()
        self.access_count += 1


class L1Cache:
    """Level 1 cache (in-memory)"""

    def __init__(self, config: CacheConfig):
        self.config = config
        self.entries: OrderedDict[str, CacheEntry] = OrderedDict()
        self.size_bytes = 0
        self._lock = threading.RLock()
        self._cleanup_task: Optional[asyncio.Task] = None

        # Statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "evictions": 0,
            "memory_usage_mb": 0,
        }

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self._lock:
            if key not in self.entries:
                self.stats["misses"] += 1
                return None

            entry = self.entries[key]

            # Check if expired
            if entry.is_expired:
                del self.entries[key]
                self.size_bytes -= entry.size_bytes
                self.stats["misses"] += 1
                return None

            # Update access info
            entry.touch()
            self.entries.move_to_end(key)  # Move to end (most recent)

            self.stats["hits"] += 1
            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache"""
        with self._lock:
            # Calculate size
            size_bytes = self._calculate_size(value)

            # Check memory limit
            if size_bytes > self.config.max_memory_mb * 1024 * 1024:
                logger.warning(f"Value too large for cache: {size_bytes} bytes")
                return

            # Create entry
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                last_accessed=time.time(),
                ttl=ttl or self.config.default_ttl,
                size_bytes=size_bytes,
            )

            # Remove existing entry if exists
            if key in self.entries:
                old_entry = self.entries[key]
                self.size_bytes -= old_entry.size_bytes
                del self.entries[key]

            # Add new entry
            self.entries[key] = entry
            self.size_bytes += size_bytes

            # Evict if necessary
            self._evict_if_necessary()

            self.stats["sets"] += 1
            self.stats["memory_usage_mb"] = self.size_bytes / (1024 * 1024)

    def delete(self, key: str) -> bool:
        """Delete value from cache"""
        with self._lock:
            if key not in self.entries:
                return False

            entry = self.entries[key]
            del self.entries[key]
            self.size_bytes -= entry.size_bytes

            self.stats["deletes"] += 1
            return True

    def clear(self) -> None:
        """Clear all entries"""
        with self._lock:
            self.entries.clear()
            self.size_bytes = 0
            self.stats["memory_usage_mb"] = 0

    def _calculate_size(self, value: Any) -> int:
        """Calculate size of value in bytes"""
        try:
            if self.config.serialization_enabled:
                serialized = json.dumps(value, default=str)
                return len(serialized.encode("utf-8"))
            else:
                return len(str(value).encode("utf-8"))
        except Exception:
            return 1024  # Default size

    def _evict_if_necessary(self) -> None:
        """Evict entries if necessary"""
        # Check size limit
        while (
            len(self.entries) > self.config.max_size
            or self.size_bytes > self.config.max_memory_mb * 1024 * 1024
        ):

            if not self.entries:
                break

            # Evict based on policy
            if self.config.eviction_policy == EvictionPolicy.LRU:
                # Remove least recently used
                key, entry = self.entries.popitem(last=False)
            elif self.config.eviction_policy == EvictionPolicy.LFU:
                # Remove least frequently used
                key = min(
                    self.entries.keys(), key=lambda k: self.entries[k].access_count
                )
                entry = self.entries.pop(key)
            elif self.config.eviction_policy == EvictionPolicy.TTL:
                # Remove oldest
                key, entry = self.entries.popitem(last=False)
            else:  # SIZE
                # Remove largest
                key = max(self.entries.keys(), key=lambda k: self.entries[k].size_bytes)
                entry = self.entries.pop(key)

            self.size_bytes -= entry.size_bytes
            self.stats["evictions"] += 1

    async def cleanup_expired(self) -> None:
        """Cleanup expired entries"""
        with self._lock:
            current_time = time.time()
            expired_keys = []

            for key, entry in self.entries.items():
                if entry.is_expired:
                    expired_keys.append(key)

            for key in expired_keys:
                entry = self.entries[key]
                del self.entries[key]
                self.size_bytes -= entry.size_bytes

            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired entries")

    async def start_cleanup_task(self) -> None:
        """Start cleanup task"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop_cleanup_task(self) -> None:
        """Stop cleanup task"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

    async def _cleanup_loop(self) -> None:
        """Cleanup loop"""
        while True:
            try:
                await asyncio.sleep(self.config.cleanup_interval)
                await self.cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
                await asyncio.sleep(60)

    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            hit_rate = 0
            if self.stats["hits"] + self.stats["misses"] > 0:
                hit_rate = self.stats["hits"] / (
                    self.stats["hits"] + self.stats["misses"]
                )

            return {
                "level": "L1",
                "entries": len(self.entries),
                "size_bytes": self.size_bytes,
                "max_size": self.config.max_size,
                "hit_rate": hit_rate,
                "statistics": self.stats.copy(),
            }


class L2Cache:
    """Level 2 cache (Redis)"""

    def __init__(self, config: CacheConfig, redis_client=None):
        self.config = config
        self.redis_client = redis_client
        self._lock = threading.RLock()

        # Statistics
        self.stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0, "errors": 0}

    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache"""
        if not self.redis_client:
            return None

        try:
            with self._lock:
                value = await self.redis_client.get(key)
                if value is None:
                    self.stats["misses"] += 1
                    return None

                # Deserialize if needed
                if self.config.serialization_enabled:
                    value = json.loads(value)

                self.stats["hits"] += 1
                return value

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"L2 cache get error: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in Redis cache"""
        if not self.redis_client:
            return

        try:
            with self._lock:
                # Serialize if needed
                if self.config.serialization_enabled:
                    value = json.dumps(value, default=str)

                ttl = ttl or self.config.default_ttl
                await self.redis_client.setex(key, ttl, value)
                self.stats["sets"] += 1

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"L2 cache set error: {e}")

    async def delete(self, key: str) -> bool:
        """Delete value from Redis cache"""
        if not self.redis_client:
            return False

        try:
            with self._lock:
                result = await self.redis_client.delete(key)
                self.stats["deletes"] += 1
                return result > 0

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"L2 cache delete error: {e}")
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            return {
                "level": "L2",
                "redis_connected": self.redis_client is not None,
                "statistics": self.stats.copy(),
            }


class L3Cache:
    """Level 3 cache (Database)"""

    def __init__(self, config: CacheConfig, db_client=None):
        self.config = config
        self.db_client = db_client
        self._lock = threading.RLock()

        # Statistics
        self.stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0, "errors": 0}

    async def get(self, key: str) -> Optional[Any]:
        """Get value from database cache"""
        if not self.db_client:
            return None

        try:
            with self._lock:
                # This would be implemented based on specific database
                # For now, return None
                self.stats["misses"] += 1
                return None

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"L3 cache get error: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in database cache"""
        if not self.db_client:
            return

        try:
            with self._lock:
                # This would be implemented based on specific database
                self.stats["sets"] += 1

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"L3 cache set error: {e}")

    async def delete(self, key: str) -> bool:
        """Delete value from database cache"""
        if not self.db_client:
            return False

        try:
            with self._lock:
                # This would be implemented based on specific database
                self.stats["deletes"] += 1
                return True

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"L3 cache delete error: {e}")
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            return {
                "level": "L3",
                "db_connected": self.db_client is not None,
                "statistics": self.stats.copy(),
            }


class MultiLevelCache:
    """Multi-level cache implementation"""

    def __init__(self, name: str, config: CacheConfig, l2_client=None, l3_client=None):
        self.name = name
        self.config = config

        # Initialize cache levels
        self.l1_cache = L1Cache(config)
        self.l2_cache = L2Cache(config, l2_client)
        self.l3_cache = L3Cache(config, l3_client)

        # Statistics
        self.stats = {
            "total_requests": 0,
            "l1_hits": 0,
            "l2_hits": 0,
            "l3_hits": 0,
            "misses": 0,
        }

    async def get(self, key: str) -> Optional[Any]:
        """Get value from multi-level cache"""
        self.stats["total_requests"] += 1

        # Try L1 cache
        value = self.l1_cache.get(key)
        if value is not None:
            self.stats["l1_hits"] += 1
            return value

        # Try L2 cache
        value = await self.l2_cache.get(key)
        if value is not None:
            self.stats["l2_hits"] += 1
            # Store in L1 for faster access
            self.l1_cache.set(key, value)
            return value

        # Try L3 cache
        value = await self.l3_cache.get(key)
        if value is not None:
            self.stats["l3_hits"] += 1
            # Store in L1 and L2 for faster access
            self.l1_cache.set(key, value)
            await self.l2_cache.set(key, value)
            return value

        self.stats["misses"] += 1
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in multi-level cache"""
        # Set in all levels
        self.l1_cache.set(key, value, ttl)
        await self.l2_cache.set(key, value, ttl)
        await self.l3_cache.set(key, value, ttl)

    async def delete(self, key: str) -> bool:
        """Delete value from multi-level cache"""
        l1_result = self.l1_cache.delete(key)
        l2_result = await self.l2_cache.delete(key)
        l3_result = await self.l3_cache.delete(key)

        return l1_result or l2_result or l3_result

    async def clear(self) -> None:
        """Clear all cache levels"""
        self.l1_cache.clear()
        # L2 and L3 clear would be implemented based on specific clients

    async def start_background_tasks(self) -> None:
        """Start background tasks"""
        await self.l1_cache.start_cleanup_task()

    async def stop_background_tasks(self) -> None:
        """Stop background tasks"""
        await self.l1_cache.stop_cleanup_task()

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        l1_stats = self.l1_cache.get_statistics()
        l2_stats = self.l2_cache.get_statistics()
        l3_stats = self.l3_cache.get_statistics()

        total_hits = (
            self.stats["l1_hits"] + self.stats["l2_hits"] + self.stats["l3_hits"]
        )
        hit_rate = total_hits / max(1, self.stats["total_requests"])

        return {
            "name": self.name,
            "config": {
                "max_size": self.config.max_size,
                "default_ttl": self.config.default_ttl,
                "eviction_policy": self.config.eviction_policy.value,
                "max_memory_mb": self.config.max_memory_mb,
            },
            "overall_statistics": {
                "total_requests": self.stats["total_requests"],
                "hit_rate": hit_rate,
                "l1_hits": self.stats["l1_hits"],
                "l2_hits": self.stats["l2_hits"],
                "l3_hits": self.stats["l3_hits"],
                "misses": self.stats["misses"],
            },
            "level_statistics": {"l1": l1_stats, "l2": l2_stats, "l3": l3_stats},
        }


class CacheManager:
    """Centralized cache manager"""

    def __init__(self):
        self.caches: Dict[str, MultiLevelCache] = {}
        self._lock = threading.RLock()

    def create_cache(
        self,
        name: str,
        config: Optional[CacheConfig] = None,
        l2_client=None,
        l3_client=None,
    ) -> MultiLevelCache:
        """Create multi-level cache"""
        if config is None:
            config = CacheConfig()

        with self._lock:
            if name in self.caches:
                raise ValueError(f"Cache '{name}' already exists")

            cache = MultiLevelCache(name, config, l2_client, l3_client)
            self.caches[name] = cache

            logger.info(f"Created cache: {name}")
            return cache

    def get_cache(self, name: str) -> Optional[MultiLevelCache]:
        """Get cache by name"""
        with self._lock:
            return self.caches.get(name)

    async def start_all_caches(self) -> None:
        """Start all caches"""
        with self._lock:
            for cache in self.caches.values():
                await cache.start_background_tasks()

        logger.info("Started all caches")

    async def stop_all_caches(self) -> None:
        """Stop all caches"""
        with self._lock:
            for cache in self.caches.values():
                await cache.stop_background_tasks()

        logger.info("Stopped all caches")

    def get_all_statistics(self) -> Dict[str, Any]:
        """Get statistics for all caches"""
        with self._lock:
            return {name: cache.get_statistics() for name, cache in self.caches.items()}


# Global cache manager
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get global cache manager"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager
