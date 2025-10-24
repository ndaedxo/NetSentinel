#!/usr/bin/env python3
"""
Advanced Connection Manager for NetSentinel
Implements connection pooling with proper resource management and cleanup
Designed for maintainability and preventing code debt
"""

import asyncio
import time
import threading
import weakref
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from contextlib import asynccontextmanager
import logging
from collections import defaultdict, deque
import json

from .exceptions import NetSentinelException, ConnectionError, ConfigurationError
from ..monitoring.logger import create_logger, get_structured_logger

logger = create_logger("connection_manager", level="INFO")
structured_logger = get_structured_logger("connection_manager")


class ConnectionState(Enum):
    """Connection state enumeration"""

    IDLE = "idle"
    ACTIVE = "active"
    CLOSING = "closing"
    CLOSED = "closed"
    ERROR = "error"


@dataclass
class ConnectionConfig:
    """Connection configuration"""

    max_connections: int = 10
    min_connections: int = 2
    max_idle_time: int = 300  # 5 minutes
    connection_timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0
    health_check_interval: int = 60
    cleanup_interval: int = 300  # 5 minutes


@dataclass
class ConnectionInfo:
    """Connection information"""

    connection_id: str
    connection: Any
    state: ConnectionState
    created_at: float
    last_used: float
    use_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None

    @property
    def is_healthy(self) -> bool:
        """Check if connection is healthy"""
        return (
            self.state == ConnectionState.ACTIVE
            and self.error_count < 3
            and time.time() - self.last_used < 3600  # 1 hour
        )

    @property
    def idle_time(self) -> float:
        """Get idle time in seconds"""
        return time.time() - self.last_used


class ConnectionPool:
    """Base connection pool implementation"""

    def __init__(
        self,
        name: str,
        config: ConnectionConfig,
        connection_factory: Callable,
        health_check: Optional[Callable] = None,
    ):
        self.name = name
        self.config = config
        self.connection_factory = connection_factory
        self.health_check = health_check

        # Connection management
        self.connections: Dict[str, ConnectionInfo] = {}
        self.idle_connections: deque = deque(maxlen=100)
        self.active_connections: Dict[str, ConnectionInfo] = {}

        # Statistics
        self.stats = {
            "total_created": 0,
            "total_closed": 0,
            "total_errors": 0,
            "active_count": 0,
            "idle_count": 0,
            "last_cleanup": time.time(),
        }

        # Thread safety
        self._lock = threading.RLock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._health_check_task: Optional[asyncio.Task] = None

        # Cleanup tracking
        self._cleanup_callbacks: List[Callable] = []

        logger.info(f"Connection pool '{name}' initialized with config: {config}")

    async def get_connection(self) -> Any:
        """Get connection from pool"""
        with self._lock:
            # Try to get idle connection
            if self.idle_connections:
                conn_info = self.idle_connections.popleft()
                if self._is_connection_healthy(conn_info):
                    conn_info.state = ConnectionState.ACTIVE
                    conn_info.last_used = time.time()
                    conn_info.use_count += 1
                    self.active_connections[conn_info.connection_id] = conn_info
                    self.stats["active_count"] = len(self.active_connections)
                    return conn_info.connection

            # Create new connection if under limit
            if len(self.connections) < self.config.max_connections:
                return await self._create_new_connection()

            # Wait for connection to become available
            return await self._wait_for_connection()

    async def return_connection(self, connection: Any) -> None:
        """Return connection to pool"""
        with self._lock:
            # Find connection info
            conn_info = None
            for info in self.active_connections.values():
                if info.connection == connection:
                    conn_info = info
                    break

            if not conn_info:
                logger.warning(
                    f"Connection not found in active connections: {connection}"
                )
                return

            # Remove from active
            del self.active_connections[conn_info.connection_id]
            self.stats["active_count"] = len(self.active_connections)

            # Check if connection is still healthy
            if self._is_connection_healthy(conn_info):
                conn_info.state = ConnectionState.IDLE
                conn_info.last_used = time.time()
                self.idle_connections.append(conn_info)
                self.stats["idle_count"] = len(self.idle_connections)
            else:
                # Close unhealthy connection
                await self._close_connection(conn_info)

    async def _create_new_connection(self) -> Any:
        """Create new connection"""
        try:
            connection = await self.connection_factory()
            conn_info = ConnectionInfo(
                connection_id=f"{self.name}_{int(time.time() * 1000)}",
                connection=connection,
                state=ConnectionState.ACTIVE,
                created_at=time.time(),
                last_used=time.time(),
            )

            self.connections[conn_info.connection_id] = conn_info
            self.active_connections[conn_info.connection_id] = conn_info
            self.stats["total_created"] += 1
            self.stats["active_count"] = len(self.active_connections)

            logger.info(f"Created new connection: {conn_info.connection_id}")
            return connection

        except Exception as e:
            self.stats["total_errors"] += 1
            logger.error(f"Failed to create connection: {e}")
            raise ConnectionError(f"Failed to create connection: {e}")

    async def _wait_for_connection(self) -> Any:
        """Wait for connection to become available"""
        # Implement proper queuing with timeout
        max_wait_time = self.config.connection_timeout
        start_time = time.time()

        while time.time() - start_time < max_wait_time:
            # Try to get a connection
            try:
                return await self.get_connection()
            except Exception:
                # Wait a bit before retrying
                await asyncio.sleep(0.1)

        # Timeout reached
        raise ConnectionError(f"Timeout waiting for connection after {max_wait_time}s")

    def _is_connection_healthy(self, conn_info: ConnectionInfo) -> bool:
        """Check if connection is healthy"""
        if not conn_info.is_healthy:
            return False

        # Perform health check if available
        if self.health_check:
            try:
                return self.health_check(conn_info.connection)
            except Exception as e:
                logger.warning(
                    f"Health check failed for {conn_info.connection_id}: {e}"
                )
                return False

        return True

    async def _close_connection(self, conn_info: ConnectionInfo) -> None:
        """Close connection"""
        try:
            if hasattr(conn_info.connection, "close"):
                if asyncio.iscoroutinefunction(conn_info.connection.close):
                    await conn_info.connection.close()
                else:
                    conn_info.connection.close()

            conn_info.state = ConnectionState.CLOSED
            del self.connections[conn_info.connection_id]
            self.stats["total_closed"] += 1

            logger.info(f"Closed connection: {conn_info.connection_id}")

        except Exception as e:
            logger.error(f"Error closing connection {conn_info.connection_id}: {e}")
            conn_info.state = ConnectionState.ERROR

    async def cleanup_idle_connections(self) -> None:
        """Cleanup idle connections"""
        with self._lock:
            current_time = time.time()
            to_remove = []

            for conn_info in list(self.idle_connections):
                if (
                    current_time - conn_info.last_used > self.config.max_idle_time
                    or not self._is_connection_healthy(conn_info)
                ):
                    to_remove.append(conn_info)

            for conn_info in to_remove:
                self.idle_connections.remove(conn_info)
                await self._close_connection(conn_info)
                self.stats["idle_count"] = len(self.idle_connections)

            self.stats["last_cleanup"] = current_time

            if to_remove:
                logger.info(f"Cleaned up {len(to_remove)} idle connections")

    async def health_check_connections(self) -> None:
        """Perform health check on all connections"""
        with self._lock:
            if not self.health_check:
                return

            for conn_info in list(self.connections.values()):
                try:
                    if not self.health_check(conn_info.connection):
                        conn_info.error_count += 1
                        conn_info.last_error = "Health check failed"

                        if conn_info.error_count >= 3:
                            await self._close_connection(conn_info)
                except Exception as e:
                    conn_info.error_count += 1
                    conn_info.last_error = str(e)
                    logger.warning(
                        f"Health check error for {conn_info.connection_id}: {e}"
                    )

    async def start_background_tasks(self) -> None:
        """Start background cleanup and health check tasks"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        if self._health_check_task is None:
            self._health_check_task = asyncio.create_task(self._health_check_loop())

        logger.info(f"Started background tasks for pool '{self.name}'")

    async def stop_background_tasks(self) -> None:
        """Stop background tasks"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None

        logger.info(f"Stopped background tasks for pool '{self.name}'")

    async def _cleanup_loop(self) -> None:
        """Cleanup loop"""
        while True:
            try:
                await asyncio.sleep(self.config.cleanup_interval)
                await self.cleanup_idle_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    async def _health_check_loop(self) -> None:
        """Health check loop"""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                await self.health_check_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    async def close_all_connections(self) -> None:
        """Close all connections"""
        with self._lock:
            # Stop background tasks
            await self.stop_background_tasks()

            # Close all connections
            for conn_info in list(self.connections.values()):
                await self._close_connection(conn_info)

            self.connections.clear()
            self.idle_connections.clear()
            self.active_connections.clear()

            # Call cleanup callbacks
            for callback in self._cleanup_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback()
                    else:
                        callback()
                except Exception as e:
                    logger.error(f"Cleanup callback error: {e}")

            logger.info(f"Closed all connections for pool '{self.name}'")

    def get_statistics(self) -> Dict[str, Any]:
        """Get pool statistics"""
        with self._lock:
            return {
                "name": self.name,
                "config": {
                    "max_connections": self.config.max_connections,
                    "min_connections": self.config.min_connections,
                    "max_idle_time": self.config.max_idle_time,
                    "connection_timeout": self.config.connection_timeout,
                },
                "current_state": {
                    "total_connections": len(self.connections),
                    "active_connections": len(self.active_connections),
                    "idle_connections": len(self.idle_connections),
                },
                "statistics": self.stats.copy(),
            }

    def add_cleanup_callback(self, callback: Callable) -> None:
        """Add cleanup callback"""
        self._cleanup_callbacks.append(callback)


class ConnectionManager:
    """Centralized connection manager"""

    def __init__(self):
        self.pools: Dict[str, ConnectionPool] = {}
        self._lock = threading.RLock()
        self._cleanup_registry = weakref.WeakSet()

    def create_pool(
        self,
        name: str,
        connection_factory: Callable,
        config: Optional[ConnectionConfig] = None,
        health_check: Optional[Callable] = None,
    ) -> ConnectionPool:
        """Create connection pool"""
        if config is None:
            config = ConnectionConfig()

        with self._lock:
            if name in self.pools:
                raise ValueError(f"Pool '{name}' already exists")

            pool = ConnectionPool(name, config, connection_factory, health_check)
            self.pools[name] = pool
            self._cleanup_registry.add(pool)

            logger.info(f"Created connection pool: {name}")
            return pool

    def get_pool(self, name: str) -> Optional[ConnectionPool]:
        """Get connection pool"""
        with self._lock:
            return self.pools.get(name)

    async def start_all_pools(self) -> None:
        """Start all connection pools"""
        with self._lock:
            for pool in self.pools.values():
                await pool.start_background_tasks()

        logger.info("Started all connection pools")

    async def stop_all_pools(self) -> None:
        """Stop all connection pools"""
        with self._lock:
            for pool in self.pools.values():
                await pool.stop_background_tasks()
                await pool.close_all_connections()

        logger.info("Stopped all connection pools")

    def get_all_statistics(self) -> Dict[str, Any]:
        """Get statistics for all pools"""
        with self._lock:
            return {name: pool.get_statistics() for name, pool in self.pools.items()}

    def cleanup_all_pools(self) -> None:
        """Cleanup all pools (for testing)"""
        with self._lock:
            for pool in self.pools.values():
                asyncio.create_task(pool.close_all_connections())


# Global connection manager
_connection_manager: Optional[ConnectionManager] = None


def get_connection_manager() -> ConnectionManager:
    """Get global connection manager"""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager


# Context manager for connection usage
@asynccontextmanager
async def get_connection(pool_name: str):
    """Context manager for connection usage"""
    manager = get_connection_manager()
    pool = manager.get_pool(pool_name)

    if not pool:
        raise ValueError(f"Pool '{pool_name}' not found")

    connection = None
    try:
        connection = await pool.get_connection()
        yield connection
    finally:
        if connection:
            await pool.return_connection(connection)
