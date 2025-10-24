#!/usr/bin/env python3
"""
Comprehensive Health Check System for NetSentinel
Monitors system, database, application, and component health
"""

import asyncio
import time
import psutil
import threading
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import requests
from datetime import datetime, timedelta

from ..core.exceptions import NetSentinelException, ConnectionError
from ..monitoring.logger import create_logger, get_structured_logger

logger = create_logger("health_checker", level="INFO")
structured_logger = get_structured_logger("health_checker")


class HealthStatus(Enum):
    """Health status enumeration"""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Health check result"""

    name: str
    status: HealthStatus
    message: str
    timestamp: float
    response_time: float
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "timestamp": self.timestamp,
            "response_time": self.response_time,
            "details": self.details,
        }


@dataclass
class SystemHealth:
    """System health metrics"""

    cpu_percent: float
    memory_percent: float
    disk_percent: float
    load_average: List[float]
    uptime: float
    process_count: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "disk_percent": self.disk_percent,
            "load_average": self.load_average,
            "uptime": self.uptime,
            "process_count": self.process_count,
        }


class DatabaseHealthCheck:
    """Database health check"""

    def __init__(self, connection_string: str, timeout: int = 5):
        self.connection_string = connection_string
        self.timeout = timeout

    async def check(self) -> HealthCheckResult:
        """Check database health"""
        start_time = time.time()

        try:
            # Test database connection
            if "redis" in self.connection_string.lower():
                result = await self._check_redis()
            elif "elasticsearch" in self.connection_string.lower():
                result = await self._check_elasticsearch()
            elif "influxdb" in self.connection_string.lower():
                result = await self._check_influxdb()
            else:
                result = await self._check_generic_database()

            response_time = time.time() - start_time

            return HealthCheckResult(
                name="database",
                status=HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY,
                message=(
                    "Database connection successful"
                    if result
                    else "Database connection failed"
                ),
                timestamp=time.time(),
                response_time=response_time,
                details={"connection_string": self.connection_string},
            )

        except Exception as e:
            response_time = time.time() - start_time
            return HealthCheckResult(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database check failed: {str(e)}",
                timestamp=time.time(),
                response_time=response_time,
                details={"error": str(e)},
            )

    async def _check_redis(self) -> bool:
        """Check Redis connection"""
        try:
            import redis

            client = redis.from_url(self.connection_string, socket_timeout=self.timeout)
            client.ping()
            return True
        except Exception:
            return False

    async def _check_elasticsearch(self) -> bool:
        """Check Elasticsearch connection"""
        try:
            response = requests.get(
                f"{self.connection_string}/_cluster/health", timeout=self.timeout
            )
            return response.status_code == 200
        except Exception:
            return False

    async def _check_influxdb(self) -> bool:
        """Check InfluxDB connection"""
        try:
            response = requests.get(
                f"{self.connection_string}/ping", timeout=self.timeout
            )
            return response.status_code == 200
        except Exception:
            return False

    async def _check_generic_database(self) -> bool:
        """Check generic database connection"""
        try:
            # This would be implemented based on specific database
            return True
        except Exception:
            return False


class ServiceHealthCheck:
    """Service health check"""

    def __init__(self, name: str, url: str, timeout: int = 5):
        self.name = name
        self.url = url
        self.timeout = timeout

    async def check(self) -> HealthCheckResult:
        """Check service health"""
        start_time = time.time()

        try:
            response = requests.get(f"{self.url}/health", timeout=self.timeout)
            response_time = time.time() - start_time

            if response.status_code == 200:
                status = HealthStatus.HEALTHY
                message = "Service is healthy"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Service returned status {response.status_code}"

            return HealthCheckResult(
                name=self.name,
                status=status,
                message=message,
                timestamp=time.time(),
                response_time=response_time,
                details={
                    "url": self.url,
                    "status_code": response.status_code,
                    "response": response.text[:500] if response.text else "",
                },
            )

        except Exception as e:
            response_time = time.time() - start_time
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Service check failed: {str(e)}",
                timestamp=time.time(),
                response_time=response_time,
                details={"error": str(e), "url": self.url},
            )


class ComponentHealthCheck:
    """Component health check"""

    def __init__(self, name: str, check_function: Callable[[], bool], timeout: int = 5):
        self.name = name
        self.check_function = check_function
        self.timeout = timeout

    async def check(self) -> HealthCheckResult:
        """Check component health"""
        start_time = time.time()

        try:
            # Run check function with timeout
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(None, self.check_function),
                timeout=self.timeout,
            )

            response_time = time.time() - start_time

            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY,
                message="Component is healthy" if result else "Component check failed",
                timestamp=time.time(),
                response_time=response_time,
                details={"check_function": self.check_function.__name__},
            )

        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message="Component check timed out",
                timestamp=time.time(),
                response_time=response_time,
                details={"timeout": self.timeout},
            )

        except Exception as e:
            response_time = time.time() - start_time
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Component check failed: {str(e)}",
                timestamp=time.time(),
                response_time=response_time,
                details={"error": str(e)},
            )


class HealthChecker:
    """Main health checker"""

    def __init__(self, check_interval: int = 30):
        self.check_interval = check_interval
        self.checks: Dict[
            str, Union[DatabaseHealthCheck, ServiceHealthCheck, ComponentHealthCheck]
        ] = {}
        self.results: Dict[str, HealthCheckResult] = {}
        self.system_health: Optional[SystemHealth] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()

    def add_database_check(
        self, name: str, connection_string: str, timeout: int = 5
    ) -> None:
        """Add database health check"""
        self.checks[name] = DatabaseHealthCheck(connection_string, timeout)
        logger.info(f"Added database health check: {name}")

    def add_service_check(self, name: str, url: str, timeout: int = 5) -> None:
        """Add service health check"""
        self.checks[name] = ServiceHealthCheck(name, url, timeout)
        logger.info(f"Added service health check: {name}")

    def add_component_check(
        self, name: str, check_function: Callable[[], bool], timeout: int = 5
    ) -> None:
        """Add component health check"""
        self.checks[name] = ComponentHealthCheck(name, check_function, timeout)
        logger.info(f"Added component health check: {name}")

    async def check_system_health(self) -> SystemHealth:
        """Check system health metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            load_avg = (
                psutil.getloadavg() if hasattr(psutil, "getloadavg") else [0, 0, 0]
            )
            uptime = time.time() - psutil.boot_time()
            process_count = len(psutil.pids())

            self.system_health = SystemHealth(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_percent=disk.percent,
                load_average=list(load_avg),
                uptime=uptime,
                process_count=process_count,
            )

            return self.system_health

        except Exception as e:
            logger.error(f"Failed to check system health: {e}")
            return SystemHealth(0, 0, 0, [0, 0, 0], 0, 0)

    async def run_health_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all health checks"""
        results = {}

        # Check system health
        system_health = await self.check_system_health()

        # Run component checks
        for name, check in self.checks.items():
            try:
                result = await check.check()
                results[name] = result

                # Log result
                if result.status == HealthStatus.HEALTHY:
                    logger.info(f"Health check passed: {name}")
                else:
                    logger.warning(f"Health check failed: {name} - {result.message}")

            except Exception as e:
                logger.error(f"Health check error for {name}: {e}")
                results[name] = HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check error: {str(e)}",
                    timestamp=time.time(),
                    response_time=0.0,
                    details={"error": str(e)},
                )

        # Update results
        with self._lock:
            self.results = results

        return results

    def get_overall_health(self) -> HealthStatus:
        """Get overall health status"""
        with self._lock:
            if not self.results:
                return HealthStatus.UNKNOWN

            unhealthy_count = sum(
                1
                for result in self.results.values()
                if result.status == HealthStatus.UNHEALTHY
            )
            degraded_count = sum(
                1
                for result in self.results.values()
                if result.status == HealthStatus.DEGRADED
            )
            total_count = len(self.results)

            if unhealthy_count > total_count * 0.5:  # More than 50% unhealthy
                return HealthStatus.UNHEALTHY
            elif unhealthy_count > 0 or degraded_count > 0:
                return HealthStatus.DEGRADED
            else:
                return HealthStatus.HEALTHY

    def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary"""
        with self._lock:
            overall_status = self.get_overall_health()

            return {
                "overall_status": overall_status.value,
                "timestamp": time.time(),
                "system_health": (
                    self.system_health.to_dict() if self.system_health else None
                ),
                "checks": {
                    name: result.to_dict() for name, result in self.results.items()
                },
                "statistics": {
                    "total_checks": len(self.results),
                    "healthy_checks": sum(
                        1
                        for r in self.results.values()
                        if r.status == HealthStatus.HEALTHY
                    ),
                    "unhealthy_checks": sum(
                        1
                        for r in self.results.values()
                        if r.status == HealthStatus.UNHEALTHY
                    ),
                    "degraded_checks": sum(
                        1
                        for r in self.results.values()
                        if r.status == HealthStatus.DEGRADED
                    ),
                },
            }

    def start_monitoring(self) -> None:
        """Start health monitoring"""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._thread.start()
        logger.info("Health monitoring started")

    def stop_monitoring(self) -> None:
        """Stop health monitoring"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Health monitoring stopped")

    def _monitoring_loop(self) -> None:
        """Health monitoring loop"""
        while self._running:
            try:
                # Run health checks
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.run_health_checks())
                loop.close()

                # Wait for next check
                time.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                time.sleep(self.check_interval)

    def get_critical_components(self) -> List[str]:
        """Get list of critical components"""
        return [
            "database",
            "kafka",
            "redis",
            "elasticsearch",
            "influxdb",
            "ml_model",
            "threat_intelligence",
        ]

    def is_critical_component_healthy(self) -> bool:
        """Check if all critical components are healthy"""
        critical_components = self.get_critical_components()

        with self._lock:
            for component in critical_components:
                if component in self.results:
                    if self.results[component].status != HealthStatus.HEALTHY:
                        return False
                else:
                    # Component not checked, assume unhealthy
                    return False

        return True


# Global health checker
_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get global health checker"""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker


def setup_health_checks() -> HealthChecker:
    """Setup default health checks"""
    checker = get_health_checker()

    # Add database checks
    checker.add_database_check("redis", "redis://localhost:6379")
    checker.add_database_check("elasticsearch", "http://localhost:9200")
    checker.add_database_check("influxdb", "http://localhost:8086")

    # Add service checks
    checker.add_service_check("kafka", "http://localhost:9092")
    checker.add_service_check("api_gateway", "http://localhost:8080")

    # Add component checks
    checker.add_component_check("ml_model", lambda: True)  # Placeholder
    checker.add_component_check("threat_intelligence", lambda: True)  # Placeholder

    return checker
