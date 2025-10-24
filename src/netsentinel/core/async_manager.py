#!/usr/bin/env python3
"""
Async Processing Manager for NetSentinel
Implements comprehensive async processing optimization with proper resource management
Designed for maintainability and preventing code debt
"""

import asyncio
import time
import threading
import weakref
from typing import Dict, List, Optional, Any, Union, Callable, Coroutine
from dataclasses import dataclass, field
from enum import Enum
import json
from collections import defaultdict, deque
import concurrent.futures
from contextlib import asynccontextmanager

from .exceptions import NetSentinelException, ProcessingError
from ..monitoring.logger import create_logger, get_structured_logger

logger = create_logger("async_manager", level="INFO")
structured_logger = get_structured_logger("async_manager")


class TaskPriority(Enum):
    """Task priority enumeration"""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class TaskStatus(Enum):
    """Task status enumeration"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskConfig:
    """Task configuration"""

    max_concurrent_tasks: int = 100
    max_queue_size: int = 1000
    task_timeout: int = 300  # 5 minutes
    retry_attempts: int = 3
    retry_delay: float = 1.0
    cleanup_interval: int = 60  # 1 minute


@dataclass
class AsyncTask:
    """Async task representation"""

    task_id: str
    coroutine: Coroutine
    priority: TaskPriority
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[Exception] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> float:
        """Get task duration"""
        if self.completed_at and self.started_at:
            return self.completed_at - self.started_at
        elif self.started_at:
            return time.time() - self.started_at
        return 0.0

    @property
    def is_completed(self) -> bool:
        """Check if task is completed"""
        return self.status in [
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        ]


class AsyncTaskManager:
    """Async task manager with priority queuing"""

    def __init__(self, config: TaskConfig):
        self.config = config
        self.task_queue: Dict[TaskPriority, deque] = {
            priority: deque(maxlen=1000) for priority in TaskPriority
        }
        self.running_tasks: Dict[str, AsyncTask] = {}
        self.completed_tasks: Dict[str, AsyncTask] = {}
        self._lock = threading.RLock()
        self._worker_tasks: List[asyncio.Task] = []
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

        # Statistics
        self.stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "cancelled_tasks": 0,
            "average_duration": 0.0,
            "queue_sizes": {priority.value: 0 for priority in TaskPriority},
        }

    async def submit_task(
        self,
        coroutine: Coroutine,
        priority: TaskPriority = TaskPriority.NORMAL,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Submit async task"""
        if task_id is None:
            task_id = f"task_{int(time.time() * 1000)}"

        # Check queue size
        total_queue_size = sum(len(queue) for queue in self.task_queue.values())
        if total_queue_size >= self.config.max_queue_size:
            raise ProcessingError("Task queue is full")

        # Create task
        task = AsyncTask(
            task_id=task_id,
            coroutine=coroutine,
            priority=priority,
            created_at=time.time(),
            metadata=metadata or {},
        )

        with self._lock:
            self.task_queue[priority].append(task)
            self.stats["total_tasks"] += 1
            self.stats["queue_sizes"][priority.value] = len(self.task_queue[priority])

        logger.info(f"Submitted task {task_id} with priority {priority.value}")
        return task_id

    async def get_task_result(self, task_id: str) -> Optional[Any]:
        """Get task result"""
        with self._lock:
            if task_id in self.completed_tasks:
                task = self.completed_tasks[task_id]
                if task.status == TaskStatus.COMPLETED:
                    return task.result
                elif task.status == TaskStatus.FAILED:
                    raise task.error
            return None

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel task"""
        with self._lock:
            # Check if task is in queue
            for priority, queue in self.task_queue.items():
                for i, task in enumerate(queue):
                    if task.task_id == task_id:
                        task.status = TaskStatus.CANCELLED
                        queue.remove(task)
                        self.stats["cancelled_tasks"] += 1
                        self.stats["queue_sizes"][priority.value] = len(queue)
                        return True

            # Check if task is running
            if task_id in self.running_tasks:
                task = self.running_tasks[task_id]
                task.status = TaskStatus.CANCELLED
                self.stats["cancelled_tasks"] += 1
                return True

            return False

    async def _process_task(self, task: AsyncTask) -> None:
        """Process single task"""
        try:
            task.status = TaskStatus.RUNNING
            task.started_at = time.time()

            # Run task with timeout
            result = await asyncio.wait_for(
                task.coroutine, timeout=self.config.task_timeout
            )

            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = time.time()

            # Update statistics
            self.stats["completed_tasks"] += 1
            self._update_average_duration(task.duration)

            logger.info(f"Task {task.task_id} completed in {task.duration:.3f}s")

        except asyncio.TimeoutError:
            task.status = TaskStatus.FAILED
            task.error = ProcessingError(f"Task {task.task_id} timed out")
            task.completed_at = time.time()
            self.stats["failed_tasks"] += 1

            logger.error(f"Task {task.task_id} timed out")

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = e
            task.completed_at = time.time()
            self.stats["failed_tasks"] += 1

            logger.error(f"Task {task.task_id} failed: {e}")

        finally:
            # Move to completed tasks
            with self._lock:
                if task.task_id in self.running_tasks:
                    del self.running_tasks[task.task_id]
                self.completed_tasks[task.task_id] = task

    async def _worker_loop(self) -> None:
        """Worker loop for processing tasks"""
        while self._running:
            try:
                # Get next task by priority
                task = None
                with self._lock:
                    for priority in sorted(
                        TaskPriority, key=lambda p: p.value, reverse=True
                    ):
                        if self.task_queue[priority]:
                            task = self.task_queue[priority].popleft()
                            self.stats["queue_sizes"][priority.value] = len(
                                self.task_queue[priority]
                            )
                            break

                if task is None:
                    await asyncio.sleep(0.1)
                    continue

                # Check if we can run more tasks
                if len(self.running_tasks) >= self.config.max_concurrent_tasks:
                    # Put task back in queue
                    with self._lock:
                        self.task_queue[task.priority].appendleft(task)
                        self.stats["queue_sizes"][task.priority.value] = len(
                            self.task_queue[task.priority]
                        )
                    await asyncio.sleep(0.1)
                    continue

                # Start task
                with self._lock:
                    self.running_tasks[task.task_id] = task

                # Process task
                await self._process_task(task)

            except Exception as e:
                logger.error(f"Worker loop error: {e}")
                await asyncio.sleep(1)

    async def _cleanup_loop(self) -> None:
        """Cleanup loop for old completed tasks"""
        while self._running:
            try:
                await asyncio.sleep(self.config.cleanup_interval)

                current_time = time.time()
                max_age = 3600  # 1 hour

                with self._lock:
                    to_remove = []
                    for task_id, task in self.completed_tasks.items():
                        if current_time - task.completed_at > max_age:
                            to_remove.append(task_id)

                    for task_id in to_remove:
                        del self.completed_tasks[task_id]

                if to_remove:
                    logger.info(f"Cleaned up {len(to_remove)} old tasks")

            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
                await asyncio.sleep(60)

    async def start(self, worker_count: int = 5) -> None:
        """Start async task manager"""
        if self._running:
            return

        self._running = True

        # Start worker tasks
        for i in range(worker_count):
            task = asyncio.create_task(self._worker_loop())
            self._worker_tasks.append(task)

        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        logger.info(f"Started async task manager with {worker_count} workers")

    async def stop(self) -> None:
        """Stop async task manager"""
        if not self._running:
            return

        self._running = False

        # Cancel worker tasks
        for task in self._worker_tasks:
            task.cancel()

        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        if self._cleanup_task:
            await asyncio.gather(self._cleanup_task, return_exceptions=True)

        self._worker_tasks.clear()
        self._cleanup_task = None

        logger.info("Stopped async task manager")

    def get_statistics(self) -> Dict[str, Any]:
        """Get task manager statistics"""
        with self._lock:
            return {
                "running": self._running,
                "worker_count": len(self._worker_tasks),
                "running_tasks": len(self.running_tasks),
                "completed_tasks": len(self.completed_tasks),
                "queue_sizes": self.stats["queue_sizes"].copy(),
                "statistics": self.stats.copy(),
            }

    def _update_average_duration(self, duration: float) -> None:
        """Update average duration"""
        total_completed = self.stats["completed_tasks"]
        if total_completed > 0:
            self.stats["average_duration"] = (
                self.stats["average_duration"] * (total_completed - 1) + duration
            ) / total_completed


class AsyncDatabaseManager:
    """Async database operations manager"""

    def __init__(self):
        self.connections: Dict[str, Any] = {}
        self._lock = threading.RLock()

    async def execute_query(
        self, database: str, query: str, params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Execute async database query"""
        try:
            connection = self.connections.get(database)
            if not connection:
                raise ConnectionError(f"Database connection '{database}' not found")

            # Execute query based on database type
            if database.startswith("elasticsearch"):
                return await self._execute_elasticsearch_query(
                    connection, query, params
                )
            elif database.startswith("influxdb"):
                return await self._execute_influxdb_query(connection, query, params)
            else:
                raise ValueError(f"Unsupported database type: {database}")

        except Exception as e:
            logger.error(f"Database query failed: {e}")
            raise

    async def _execute_elasticsearch_query(
        self, connection: Any, query: str, params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Execute Elasticsearch query"""
        try:
            # This would be implemented based on specific Elasticsearch client
            # For now, return mock result
            return {"hits": {"total": 0, "hits": []}}
        except Exception as e:
            logger.error(f"Elasticsearch query failed: {e}")
            raise

    async def _execute_influxdb_query(
        self, connection: Any, query: str, params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Execute InfluxDB query"""
        try:
            # This would be implemented based on specific InfluxDB client
            # For now, return mock result
            return {"results": []}
        except Exception as e:
            logger.error(f"InfluxDB query failed: {e}")
            raise

    def add_connection(self, name: str, connection: Any) -> None:
        """Add database connection"""
        with self._lock:
            self.connections[name] = connection
            logger.info(f"Added database connection: {name}")

    def remove_connection(self, name: str) -> None:
        """Remove database connection"""
        with self._lock:
            if name in self.connections:
                del self.connections[name]
                logger.info(f"Removed database connection: {name}")


class AsyncFileManager:
    """Async file operations manager"""

    def __init__(self):
        self.file_handles: Dict[str, Any] = {}
        self._lock = threading.RLock()

    async def read_file(self, file_path: str) -> str:
        """Read file asynchronously"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return content
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            raise

    async def write_file(self, file_path: str, content: str) -> None:
        """Write file asynchronously"""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            logger.error(f"Failed to write file {file_path}: {e}")
            raise

    async def append_file(self, file_path: str, content: str) -> None:
        """Append to file asynchronously"""
        try:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            logger.error(f"Failed to append to file {file_path}: {e}")
            raise


class AsyncNetworkManager:
    """Async network operations manager"""

    def __init__(self):
        self.sessions: Dict[str, Any] = {}
        self._lock = threading.RLock()

    async def make_request(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Any] = None,
        timeout: int = 30,
    ) -> Any:
        """Make async HTTP request"""
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=method, url=url, headers=headers, data=data, timeout=timeout
                ) as response:
                    return await response.json()

        except Exception as e:
            logger.error(f"Network request failed: {e}")
            raise

    async def download_file(self, url: str, file_path: str) -> None:
        """Download file asynchronously"""
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    with open(file_path, "wb") as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)

        except Exception as e:
            logger.error(f"File download failed: {e}")
            raise


class AsyncManager:
    """Main async processing manager"""

    def __init__(self, config: Optional[TaskConfig] = None):
        self.config = config or TaskConfig()
        self.task_manager = AsyncTaskManager(self.config)
        self.database_manager = AsyncDatabaseManager()
        self.file_manager = AsyncFileManager()
        self.network_manager = AsyncNetworkManager()
        self._running = False

    async def start(self, worker_count: int = 5) -> None:
        """Start async manager"""
        await self.task_manager.start(worker_count)
        self._running = True
        logger.info("Started async manager")

    async def stop(self) -> None:
        """Stop async manager"""
        await self.task_manager.stop()
        self._running = False
        logger.info("Stopped async manager")

    async def submit_task(
        self,
        coroutine: Coroutine,
        priority: TaskPriority = TaskPriority.NORMAL,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Submit async task"""
        return await self.task_manager.submit_task(
            coroutine, priority, task_id, metadata
        )

    async def get_task_result(self, task_id: str) -> Any:
        """Get task result"""
        return await self.task_manager.get_task_result(task_id)

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel task"""
        return await self.task_manager.cancel_task(task_id)

    def get_statistics(self) -> Dict[str, Any]:
        """Get async manager statistics"""
        return {
            "running": self._running,
            "task_manager": self.task_manager.get_statistics(),
            "database_connections": len(self.database_manager.connections),
            "file_handles": len(self.file_manager.file_handles),
            "network_sessions": len(self.network_manager.sessions),
        }


# Global async manager
_async_manager: Optional[AsyncManager] = None


def get_async_manager() -> AsyncManager:
    """Get global async manager"""
    global _async_manager
    if _async_manager is None:
        _async_manager = AsyncManager()
    return _async_manager


# Decorator for async functions
def async_task(priority: TaskPriority = TaskPriority.NORMAL):
    """Decorator for async task functions"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            manager = get_async_manager()
            task_id = await manager.submit_task(
                func(*args, **kwargs), priority=priority
            )
            return await manager.get_task_result(task_id)

        return wrapper

    return decorator
