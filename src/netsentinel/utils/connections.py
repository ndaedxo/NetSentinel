#!/usr/bin/env python3
"""
Connection utilities for NetSentinel
"""

import asyncio
import time
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass
from contextlib import asynccontextmanager
import logging

from .constants import DEFAULT_TIMEOUT, DEFAULT_RETRY_ATTEMPTS, MAX_CONNECTIONS

logger = logging.getLogger(__name__)


@dataclass
class ConnectionConfig:
    """Configuration for connection pools"""

    host: str
    port: int
    max_connections: int = MAX_CONNECTIONS
    timeout: float = DEFAULT_TIMEOUT
    retry_attempts: int = DEFAULT_RETRY_ATTEMPTS
    keepalive: bool = True
    ssl_enabled: bool = False
    ssl_verify: bool = True


@dataclass
class ConnectionStats:
    """Connection pool statistics"""

    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    failed_connections: int = 0
    last_used: Optional[float] = None
    created_at: float = 0.0

    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()


class ConnectionPool:
    """Generic connection pool implementation"""

    def __init__(self, config: ConnectionConfig):
        self.config = config
        self.stats = ConnectionStats()
        self._connections: List[Any] = []
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(config.max_connections)

    async def acquire(self) -> Any:
        """Acquire a connection from the pool"""
        async with self._semaphore:
            async with self._lock:
                if self._connections:
                    connection = self._connections.pop()
                    self.stats.active_connections += 1
                    self.stats.idle_connections -= 1
                    self.stats.last_used = time.time()
                    return connection
                else:
                    # Create new connection
                    connection = await self._create_connection()
                    self.stats.active_connections += 1
                    self.stats.total_connections += 1
                    return connection

    async def release(self, connection: Any):
        """Release a connection back to the pool"""
        async with self._lock:
            if (
                self._connections
                and len(self._connections) < self.config.max_connections
            ):
                self._connections.append(connection)
                self.stats.active_connections -= 1
                self.stats.idle_connections += 1
            else:
                # Close connection if pool is full
                await self._close_connection(connection)
                self.stats.active_connections -= 1

    async def _create_connection(self) -> Any:
        """Create a new connection (to be implemented by subclasses)"""
        raise NotImplementedError("Subclasses must implement _create_connection")

    async def _close_connection(self, connection: Any):
        """Close a connection (to be implemented by subclasses)"""
        raise NotImplementedError("Subclasses must implement _close_connection")

    async def close_all(self):
        """Close all connections in the pool"""
        async with self._lock:
            for connection in self._connections:
                await self._close_connection(connection)
            self._connections.clear()
            self.stats.idle_connections = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        return {
            "total_connections": self.stats.total_connections,
            "active_connections": self.stats.active_connections,
            "idle_connections": self.stats.idle_connections,
            "failed_connections": self.stats.failed_connections,
            "last_used": self.stats.last_used,
            "uptime": time.time() - self.stats.created_at,
            "max_connections": self.config.max_connections,
            "utilization": (
                self.stats.active_connections / self.config.max_connections * 100
                if self.config.max_connections > 0
                else 0
            ),
        }


def create_connection_pool(
    host: str,
    port: int,
    max_connections: int = MAX_CONNECTIONS,
    timeout: float = DEFAULT_TIMEOUT,
    retry_attempts: int = DEFAULT_RETRY_ATTEMPTS,
    **kwargs,
) -> ConnectionConfig:
    """Create a connection pool configuration"""
    return ConnectionConfig(
        host=host,
        port=port,
        max_connections=max_connections,
        timeout=timeout,
        retry_attempts=retry_attempts,
        **kwargs,
    )


@asynccontextmanager
async def connection_context(pool: ConnectionPool):
    """Context manager for connection pool usage"""
    connection = None
    try:
        connection = await pool.acquire()
        yield connection
    except Exception as e:
        logger.error(f"Error in connection context: {e}")
        raise
    finally:
        if connection:
            await pool.release(connection)


async def with_retry(
    func: Callable,
    max_attempts: int = DEFAULT_RETRY_ATTEMPTS,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
) -> Any:
    """Execute function with retry logic"""
    last_exception = None

    for attempt in range(max_attempts):
        try:
            return await func() if asyncio.iscoroutinefunction(func) else func()
        except exceptions as e:
            last_exception = e
            if attempt == max_attempts - 1:
                break

            wait_time = delay * (backoff**attempt)
            logger.warning(
                f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s..."
            )
            await asyncio.sleep(wait_time)

    if last_exception:
        raise last_exception


def validate_connection_config(config: Dict[str, Any]) -> bool:
    """Validate connection configuration"""
    required_fields = ["host", "port"]

    for field in required_fields:
        if field not in config:
            logger.error(f"Missing required field: {field}")
            return False

    try:
        port = int(config["port"])
        if not 1 <= port <= 65535:
            logger.error(f"Invalid port number: {port}")
            return False
    except (ValueError, TypeError):
        logger.error(f"Invalid port value: {config['port']}")
        return False

    if "timeout" in config:
        try:
            timeout = float(config["timeout"])
            if timeout <= 0:
                logger.error(f"Invalid timeout value: {timeout}")
                return False
        except (ValueError, TypeError):
            logger.error(f"Invalid timeout value: {config['timeout']}")
            return False

    return True


class ConnectionManager:
    """Manages multiple connection pools"""

    def __init__(self):
        self._pools: Dict[str, ConnectionPool] = {}
        self._lock = asyncio.Lock()

    async def register_pool(self, name: str, pool: ConnectionPool):
        """Register a connection pool"""
        async with self._lock:
            self._pools[name] = pool
            logger.info(f"Registered connection pool: {name}")

    async def get_pool(self, name: str) -> Optional[ConnectionPool]:
        """Get a connection pool by name"""
        async with self._lock:
            return self._pools.get(name)

    async def remove_pool(self, name: str):
        """Remove a connection pool"""
        async with self._lock:
            if name in self._pools:
                pool = self._pools.pop(name)
                await pool.close_all()
                logger.info(f"Removed connection pool: {name}")

    async def close_all(self):
        """Close all connection pools"""
        async with self._lock:
            for name, pool in self._pools.items():
                await pool.close_all()
                logger.info(f"Closed connection pool: {name}")
            self._pools.clear()

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all connection pools"""
        return {name: pool.get_stats() for name, pool in self._pools.items()}


# Global connection manager instance
_connection_manager: Optional[ConnectionManager] = None


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager"""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager
