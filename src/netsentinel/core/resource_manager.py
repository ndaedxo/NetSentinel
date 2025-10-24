#!/usr/bin/env python3
"""
Resource Manager for NetSentinel
Provides centralized resource management and cleanup
"""

import asyncio
import logging
import threading
import time
import weakref
from typing import Any, Dict, List, Optional, Callable, Set
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from collections import defaultdict
import gc

logger = logging.getLogger(__name__)


@dataclass
class ResourceInfo:
    """Information about a managed resource"""

    name: str
    resource: Any
    resource_type: str
    created_at: float
    last_accessed: float
    access_count: int = 0
    cleanup_handler: Optional[Callable] = None
    max_age: Optional[float] = None
    max_access_count: Optional[int] = None
    is_weak_ref: bool = False


class ResourceManager:
    """Centralized resource management with automatic cleanup"""

    def __init__(self, max_resources: int = 1000, cleanup_interval: int = 300):
        self.max_resources = max_resources
        self.cleanup_interval = cleanup_interval
        self._resources: Dict[str, ResourceInfo] = {}
        self._weak_resources: Dict[str, weakref.ref] = {}
        self._cleanup_handlers: Dict[str, Callable] = {}
        self._lock = threading.RLock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

        # Resource type tracking
        self._resource_types: Dict[str, int] = defaultdict(int)
        self._access_patterns: Dict[str, List[float]] = defaultdict(list)

        # Memory monitoring
        self._memory_threshold = 0.8  # 80% memory usage threshold
        self._last_memory_check = 0
        self._memory_check_interval = 60  # Check every minute

    async def start(self):
        """Start resource manager"""
        if self._running:
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Resource manager started")

    async def stop(self):
        """Stop resource manager and cleanup all resources"""
        if not self._running:
            return

        self._running = False

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Cleanup all resources
        await self.cleanup_all()
        logger.info("Resource manager stopped")

    def register_resource(
        self,
        name: str,
        resource: Any,
        resource_type: str = "unknown",
        cleanup_handler: Optional[Callable] = None,
        max_age: Optional[float] = None,
        max_access_count: Optional[int] = None,
        use_weak_ref: bool = False,
    ) -> bool:
        """Register a resource for management"""
        with self._lock:
            if len(self._resources) >= self.max_resources:
                logger.warning(
                    f"Resource limit reached ({self.max_resources}), cannot register {name}"
                )
                return False

            current_time = time.time()

            if use_weak_ref:
                self._weak_resources[name] = weakref.ref(resource)
                logger.debug(f"Registered weak reference for resource: {name}")
            else:
                self._resources[name] = ResourceInfo(
                    name=name,
                    resource=resource,
                    resource_type=resource_type,
                    created_at=current_time,
                    last_accessed=current_time,
                    cleanup_handler=cleanup_handler,
                    max_age=max_age,
                    max_access_count=max_access_count,
                    is_weak_ref=False,
                )

                self._resource_types[resource_type] += 1
                logger.debug(f"Registered resource: {name} (type: {resource_type})")

            return True

    def get_resource(self, name: str) -> Optional[Any]:
        """Get a registered resource"""
        with self._lock:
            # Check regular resources first
            if name in self._resources:
                resource_info = self._resources[name]
                resource_info.last_accessed = time.time()
                resource_info.access_count += 1

                # Track access pattern
                self._access_patterns[name].append(time.time())

                return resource_info.resource

            # Check weak references
            if name in self._weak_resources:
                weak_ref = self._weak_resources[name]
                resource = weak_ref()
                if resource is None:
                    # Weak reference was garbage collected
                    del self._weak_resources[name]
                    logger.debug(f"Weak reference {name} was garbage collected")
                    return None

                # Track access for weak references too
                self._access_patterns[name].append(time.time())
                return resource

            return None

    def unregister_resource(self, name: str) -> bool:
        """Unregister a resource"""
        with self._lock:
            if name in self._resources:
                resource_info = self._resources[name]
                resource_type = resource_info.resource_type

                # Cleanup resource if handler exists
                if resource_info.cleanup_handler:
                    try:
                        if asyncio.iscoroutinefunction(resource_info.cleanup_handler):
                            asyncio.create_task(resource_info.cleanup_handler())
                        else:
                            resource_info.cleanup_handler()
                    except Exception as e:
                        logger.error(f"Error in cleanup handler for {name}: {e}")

                del self._resources[name]
                self._resource_types[resource_type] -= 1
                logger.debug(f"Unregistered resource: {name}")
                return True

            if name in self._weak_resources:
                del self._weak_resources[name]
                logger.debug(f"Unregistered weak reference: {name}")
                return True

            return False

    async def cleanup_expired(self) -> int:
        """Cleanup expired resources"""
        cleaned_count = 0
        current_time = time.time()

        with self._lock:
            expired_resources = []

            for name, resource_info in self._resources.items():
                should_cleanup = False

                # Check age limit
                if (
                    resource_info.max_age
                    and (current_time - resource_info.created_at)
                    > resource_info.max_age
                ):
                    should_cleanup = True
                    logger.debug(f"Resource {name} expired due to age")

                # Check access count limit
                if (
                    resource_info.max_access_count
                    and resource_info.access_count >= resource_info.max_access_count
                ):
                    should_cleanup = True
                    logger.debug(f"Resource {name} expired due to access count")

                # Check if resource hasn't been accessed recently
                if (current_time - resource_info.last_accessed) > 3600:  # 1 hour
                    should_cleanup = True
                    logger.debug(f"Resource {name} expired due to inactivity")

                if should_cleanup:
                    expired_resources.append(name)

            # Cleanup expired resources
            for name in expired_resources:
                if await self._cleanup_resource(name):
                    cleaned_count += 1

        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} expired resources")

        return cleaned_count

    async def cleanup_weak_references(self) -> int:
        """Cleanup garbage collected weak references"""
        cleaned_count = 0

        with self._lock:
            dead_refs = []

            for name, weak_ref in self._weak_resources.items():
                if weak_ref() is None:
                    dead_refs.append(name)

            for name in dead_refs:
                del self._weak_resources[name]
                cleaned_count += 1

        if cleaned_count > 0:
            logger.debug(f"Cleaned up {cleaned_count} dead weak references")

        return cleaned_count

    async def cleanup_all(self) -> int:
        """Cleanup all resources"""
        cleaned_count = 0

        with self._lock:
            # Cleanup regular resources
            for name in list(self._resources.keys()):
                if await self._cleanup_resource(name):
                    cleaned_count += 1

            # Cleanup weak references
            self._weak_resources.clear()

        logger.info(f"Cleaned up {cleaned_count} resources")
        return cleaned_count

    async def _cleanup_resource(self, name: str) -> bool:
        """Cleanup a specific resource"""
        try:
            if name in self._resources:
                resource_info = self._resources[name]

                # Call cleanup handler if exists
                if resource_info.cleanup_handler:
                    if asyncio.iscoroutinefunction(resource_info.cleanup_handler):
                        await resource_info.cleanup_handler()
                    else:
                        resource_info.cleanup_handler()

                # Remove from tracking
                resource_type = resource_info.resource_type
                del self._resources[name]
                self._resource_types[resource_type] -= 1

                logger.debug(f"Cleaned up resource: {name}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error cleaning up resource {name}: {e}")
            return False

    async def _cleanup_loop(self):
        """Main cleanup loop"""
        while self._running:
            try:
                # Cleanup expired resources
                await self.cleanup_expired()

                # Cleanup weak references
                await self.cleanup_weak_references()

                # Check memory usage
                await self._check_memory_usage()

                # Force garbage collection periodically
                if time.time() - self._last_memory_check > 300:  # Every 5 minutes
                    gc.collect()
                    self._last_memory_check = time.time()

                await asyncio.sleep(self.cleanup_interval)

            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    async def _check_memory_usage(self):
        """Check memory usage and cleanup if necessary"""
        try:
            import psutil

            process = psutil.Process()
            memory_percent = process.memory_percent() / 100

            if memory_percent > self._memory_threshold:
                logger.warning(f"High memory usage: {memory_percent:.1%}")

                # Cleanup oldest resources
                await self._emergency_cleanup()

        except ImportError:
            # psutil not available, skip memory checking
            pass
        except Exception as e:
            logger.error(f"Error checking memory usage: {e}")

    async def _emergency_cleanup(self):
        """Emergency cleanup when memory usage is high"""
        with self._lock:
            # Sort resources by last access time (oldest first)
            sorted_resources = sorted(
                self._resources.items(), key=lambda x: x[1].last_accessed
            )

            # Cleanup oldest 25% of resources
            cleanup_count = max(1, len(sorted_resources) // 4)

            for name, _ in sorted_resources[:cleanup_count]:
                await self._cleanup_resource(name)

            logger.info(f"Emergency cleanup: removed {cleanup_count} resources")

    def get_resource_info(self, name: str) -> Optional[ResourceInfo]:
        """Get information about a resource"""
        with self._lock:
            return self._resources.get(name)

    def list_resources(self) -> List[str]:
        """List all registered resource names"""
        with self._lock:
            return list(self._resources.keys()) + list(self._weak_resources.keys())

    def get_resource_metrics(self) -> Dict[str, Any]:
        """Get resource management metrics"""
        with self._lock:
            current_time = time.time()

            # Calculate average access patterns
            avg_access_intervals = {}
            for name, access_times in self._access_patterns.items():
                if len(access_times) > 1:
                    intervals = [
                        access_times[i] - access_times[i - 1]
                        for i in range(1, len(access_times))
                    ]
                    avg_access_intervals[name] = sum(intervals) / len(intervals)

            return {
                "total_resources": len(self._resources),
                "weak_references": len(self._weak_resources),
                "resource_types": dict(self._resource_types),
                "oldest_resource_age": (
                    min(
                        (current_time - info.created_at)
                        for info in self._resources.values()
                    )
                    if self._resources
                    else 0
                ),
                "newest_resource_age": (
                    max(
                        (current_time - info.created_at)
                        for info in self._resources.values()
                    )
                    if self._resources
                    else 0
                ),
                "total_access_count": sum(
                    info.access_count for info in self._resources.values()
                ),
                "avg_access_intervals": avg_access_intervals,
            }

    @asynccontextmanager
    async def managed_resource(self, name: str, resource: Any, **kwargs):
        """Context manager for automatic resource cleanup"""
        try:
            self.register_resource(name, resource, **kwargs)
            yield resource
        finally:
            await self._cleanup_resource(name)


# Global resource manager
_resource_manager: Optional[ResourceManager] = None


def get_resource_manager() -> ResourceManager:
    """Get the global resource manager"""
    global _resource_manager
    if _resource_manager is None:
        _resource_manager = ResourceManager()
    return _resource_manager


async def start_resource_manager():
    """Start the global resource manager"""
    manager = get_resource_manager()
    await manager.start()


async def stop_resource_manager():
    """Stop the global resource manager"""
    manager = get_resource_manager()
    await manager.stop()
