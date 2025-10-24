#!/usr/bin/env python3
"""
Routing and Load Balancing for NetSentinel API Gateway
Service discovery, routing, and load balancing functionality
"""

import time
import random
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import requests
from collections import defaultdict

logger = logging.getLogger(__name__)


class LoadBalancingStrategy(Enum):
    """Load balancing strategies"""

    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    RANDOM = "random"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"


@dataclass
class ServiceInstance:
    """Service instance information"""

    url: str
    weight: int = 1
    health_check_url: str = None
    last_health_check: float = 0
    is_healthy: bool = True
    connection_count: int = 0
    response_time: float = 0.0
    error_count: int = 0


class ServiceRouter:
    """Service router for API Gateway"""

    def __init__(self):
        self.services: Dict[str, List[ServiceInstance]] = defaultdict(list)
        self.service_configs: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(f"{__name__}.ServiceRouter")

    def add_service(
        self,
        service_name: str,
        service_url: str,
        weight: int = 1,
        health_check_url: str = None,
    ) -> None:
        """Add service instance"""
        instance = ServiceInstance(
            url=service_url,
            weight=weight,
            health_check_url=health_check_url or f"{service_url}/health",
        )

        self.services[service_name].append(instance)
        self.logger.info(f"Added service instance: {service_name} -> {service_url}")

    def remove_service(self, service_name: str, service_url: str) -> None:
        """Remove service instance"""
        if service_name in self.services:
            self.services[service_name] = [
                instance
                for instance in self.services[service_name]
                if instance.url != service_url
            ]
            self.logger.info(
                f"Removed service instance: {service_name} -> {service_url}"
            )

    def get_service_instances(self, service_name: str) -> List[ServiceInstance]:
        """Get all instances for service"""
        return self.services.get(service_name, [])

    def get_healthy_instances(self, service_name: str) -> List[ServiceInstance]:
        """Get healthy instances for service"""
        instances = self.get_service_instances(service_name)
        return [instance for instance in instances if instance.is_healthy]

    def update_service_health(
        self, service_name: str, service_url: str, is_healthy: bool
    ) -> None:
        """Update service health status"""
        for instance in self.services.get(service_name, []):
            if instance.url == service_url:
                instance.is_healthy = is_healthy
                instance.last_health_check = time.time()
                break

    def get_service_stats(self, service_name: str) -> Dict[str, Any]:
        """Get service statistics"""
        instances = self.get_service_instances(service_name)
        healthy_instances = self.get_healthy_instances(service_name)

        return {
            "total_instances": len(instances),
            "healthy_instances": len(healthy_instances),
            "unhealthy_instances": len(instances) - len(healthy_instances),
            "instances": [
                {
                    "url": instance.url,
                    "is_healthy": instance.is_healthy,
                    "connection_count": instance.connection_count,
                    "response_time": instance.response_time,
                    "error_count": instance.error_count,
                }
                for instance in instances
            ],
        }


class LoadBalancer:
    """Load balancer for service instances"""

    def __init__(
        self, strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN
    ):
        self.strategy = strategy
        self.service_router = ServiceRouter()
        self.current_indices: Dict[str, int] = defaultdict(int)
        self.connection_counts: Dict[str, Dict[str, int]] = defaultdict(dict)
        self.logger = logging.getLogger(f"{__name__}.LoadBalancer")

    def add_instance(
        self,
        service_name: str,
        instance_url: str,
        weight: int = 1,
        health_check_url: str = None,
    ) -> None:
        """Add service instance"""
        self.service_router.add_service(
            service_name, instance_url, weight, health_check_url
        )
        self.connection_counts[service_name][instance_url] = 0

    def remove_instance(self, service_name: str, instance_url: str) -> None:
        """Remove service instance"""
        self.service_router.remove_service(service_name, instance_url)
        self.connection_counts[service_name].pop(instance_url, None)

    def get_instance(self, service_name: str) -> Optional[str]:
        """Get service instance using load balancing strategy"""
        try:
            healthy_instances = self.service_router.get_healthy_instances(service_name)
            if not healthy_instances:
                self.logger.warning(
                    f"No healthy instances available for {service_name}"
                )
                return None

            if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
                return self._round_robin_selection(service_name, healthy_instances)
            elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
                return self._least_connections_selection(
                    service_name, healthy_instances
                )
            elif self.strategy == LoadBalancingStrategy.RANDOM:
                return self._random_selection(healthy_instances)
            elif self.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
                return self._weighted_round_robin_selection(
                    service_name, healthy_instances
                )
            else:
                return healthy_instances[0].url

        except Exception as e:
            self.logger.error(f"Error selecting instance for {service_name}: {e}")
            return None

    def _round_robin_selection(
        self, service_name: str, instances: List[ServiceInstance]
    ) -> str:
        """Round robin selection"""
        if not instances:
            return None

        current_index = self.current_indices[service_name]
        selected_instance = instances[current_index % len(instances)]
        self.current_indices[service_name] = (current_index + 1) % len(instances)

        return selected_instance.url

    def _least_connections_selection(
        self, service_name: str, instances: List[ServiceInstance]
    ) -> str:
        """Least connections selection"""
        if not instances:
            return None

        # Find instance with least connections
        min_connections = min(instance.connection_count for instance in instances)
        least_connected_instances = [
            instance
            for instance in instances
            if instance.connection_count == min_connections
        ]

        # If multiple instances have same connection count, use round robin
        if len(least_connected_instances) > 1:
            current_index = self.current_indices[service_name]
            selected_instance = least_connected_instances[
                current_index % len(least_connected_instances)
            ]
            self.current_indices[service_name] = (current_index + 1) % len(
                least_connected_instances
            )
        else:
            selected_instance = least_connected_instances[0]

        return selected_instance.url

    def _random_selection(self, instances: List[ServiceInstance]) -> str:
        """Random selection"""
        if not instances:
            return None

        selected_instance = random.choice(instances)
        return selected_instance.url

    def _weighted_round_robin_selection(
        self, service_name: str, instances: List[ServiceInstance]
    ) -> str:
        """Weighted round robin selection"""
        if not instances:
            return None

        # Calculate total weight
        total_weight = sum(instance.weight for instance in instances)
        if total_weight == 0:
            return instances[0].url

        # Use weighted round robin algorithm
        current_weight = self.current_indices[service_name]
        selected_instance = None

        for instance in instances:
            current_weight -= instance.weight
            if current_weight <= 0:
                selected_instance = instance
                break

        # Update current weight
        self.current_indices[service_name] = (
            current_weight + total_weight
        ) % total_weight

        return selected_instance.url if selected_instance else instances[0].url

    def increment_connections(self, service_name: str, instance_url: str) -> None:
        """Increment connection count for instance"""
        if (
            service_name in self.connection_counts
            and instance_url in self.connection_counts[service_name]
        ):
            self.connection_counts[service_name][instance_url] += 1

    def decrement_connections(self, service_name: str, instance_url: str) -> None:
        """Decrement connection count for instance"""
        if (
            service_name in self.connection_counts
            and instance_url in self.connection_counts[service_name]
        ):
            self.connection_counts[service_name][instance_url] = max(
                0, self.connection_counts[service_name][instance_url] - 1
            )

    def get_load_balancer_stats(self) -> Dict[str, Any]:
        """Get load balancer statistics"""
        stats = {"strategy": self.strategy.value, "services": {}}

        for service_name in self.service_router.services:
            service_stats = self.service_router.get_service_stats(service_name)
            service_stats["connection_counts"] = self.connection_counts.get(
                service_name, {}
            )
            stats["services"][service_name] = service_stats

        return stats


class HealthChecker:
    """Health checker for service instances"""

    def __init__(self, check_interval: int = 30):
        self.check_interval = check_interval
        self.last_checks: Dict[str, float] = {}
        self.logger = logging.getLogger(f"{__name__}.HealthChecker")

    def should_check_health(self, service_name: str, instance_url: str) -> bool:
        """Check if health check should be performed"""
        key = f"{service_name}:{instance_url}"
        current_time = time.time()
        last_check = self.last_checks.get(key, 0)

        return current_time - last_check >= self.check_interval

    def check_instance_health(self, instance: ServiceInstance) -> bool:
        """Check health of service instance"""
        try:
            if not instance.health_check_url:
                return True  # Assume healthy if no health check URL

            start_time = time.time()
            response = requests.get(instance.health_check_url, timeout=5)
            response_time = time.time() - start_time

            # Update instance metrics
            instance.response_time = response_time
            instance.last_health_check = time.time()

            if response.status_code == 200:
                instance.error_count = 0
                return True
            else:
                instance.error_count += 1
                return False

        except Exception as e:
            self.logger.error(f"Health check failed for {instance.url}: {e}")
            instance.error_count += 1
            return False

    def check_service_health(
        self, service_name: str, service_router: ServiceRouter
    ) -> None:
        """Check health of all instances for a service"""
        instances = service_router.get_service_instances(service_name)

        for instance in instances:
            if self.should_check_health(service_name, instance.url):
                is_healthy = self.check_instance_health(instance)
                service_router.update_service_health(
                    service_name, instance.url, is_healthy
                )

                # Update last check time
                key = f"{service_name}:{instance.url}"
                self.last_checks[key] = time.time()

    def get_health_stats(self) -> Dict[str, Any]:
        """Get health check statistics"""
        return {
            "check_interval": self.check_interval,
            "last_checks": self.last_checks,
            "total_checks": len(self.last_checks),
        }


class CircuitBreaker:
    """Circuit breaker for service instances"""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.breaker_states: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "state": "closed",  # closed, open, half-open
                "failure_count": 0,
                "last_failure": 0,
                "success_count": 0,
            }
        )
        self.logger = logging.getLogger(f"{__name__}.CircuitBreaker")

    def is_request_allowed(self, service_name: str, instance_url: str) -> bool:
        """Check if request is allowed through circuit breaker"""
        key = f"{service_name}:{instance_url}"
        breaker_state = self.breaker_states[key]

        if breaker_state["state"] == "closed":
            return True
        elif breaker_state["state"] == "open":
            # Check if recovery timeout has passed
            if time.time() - breaker_state["last_failure"] > self.recovery_timeout:
                breaker_state["state"] = "half-open"
                return True
            return False
        elif breaker_state["state"] == "half-open":
            return True

        return False

    def record_success(self, service_name: str, instance_url: str) -> None:
        """Record successful request"""
        key = f"{service_name}:{instance_url}"
        breaker_state = self.breaker_states[key]

        if breaker_state["state"] == "half-open":
            breaker_state["success_count"] += 1
            if breaker_state["success_count"] >= 3:  # Require 3 successes to close
                breaker_state["state"] = "closed"
                breaker_state["failure_count"] = 0
                breaker_state["success_count"] = 0
        elif breaker_state["state"] == "closed":
            breaker_state["failure_count"] = 0

    def record_failure(self, service_name: str, instance_url: str) -> None:
        """Record failed request"""
        key = f"{service_name}:{instance_url}"
        breaker_state = self.breaker_states[key]

        breaker_state["failure_count"] += 1
        breaker_state["last_failure"] = time.time()

        if breaker_state["failure_count"] >= self.failure_threshold:
            breaker_state["state"] = "open"
            self.logger.warning(
                f"Circuit breaker opened for {service_name}:{instance_url}"
            )

    def get_circuit_breaker_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics"""
        stats = {
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "breakers": {},
        }

        for key, state in self.breaker_states.items():
            stats["breakers"][key] = {
                "state": state["state"],
                "failure_count": state["failure_count"],
                "success_count": state["success_count"],
                "last_failure": state["last_failure"],
            }

        return stats
