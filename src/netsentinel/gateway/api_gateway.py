#!/usr/bin/env python3
"""
API Gateway for NetSentinel
Centralized routing, authentication, rate limiting, and load balancing
"""

import asyncio
import time
import uuid
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import json
import hashlib
import hmac
from datetime import datetime, timedelta

from flask import Flask, request, jsonify, g
from werkzeug.exceptions import TooManyRequests, Unauthorized, Forbidden
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..core.exceptions import NetSentinelException, ConfigurationError
from ..monitoring.logger import create_logger, get_structured_logger

logger = create_logger("api_gateway", level="INFO")
structured_logger = get_structured_logger("api_gateway")


class ServiceStatus(Enum):
    """Service status enumeration"""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class ServiceInstance:
    """Service instance information"""

    name: str
    url: str
    status: ServiceStatus
    last_health_check: float
    response_time: float
    error_count: int = 0
    success_count: int = 0

    @property
    def health_score(self) -> float:
        """Calculate health score (0-1)"""
        if self.error_count + self.success_count == 0:
            return 0.5

        success_rate = self.success_count / (self.error_count + self.success_count)
        response_score = max(
            0, 1 - (self.response_time / 1000)
        )  # Normalize response time
        return (success_rate + response_score) / 2


@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""

    requests_per_minute: int = 60
    burst_limit: int = 10
    window_size: int = 60  # seconds


class RateLimiter:
    """Token bucket rate limiter"""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.buckets: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed"""
        async with self._lock:
            now = time.time()
            bucket = self.buckets.get(
                client_id,
                {"tokens": self.config.requests_per_minute, "last_refill": now},
            )

            # Refill tokens
            time_passed = now - bucket["last_refill"]
            tokens_to_add = time_passed * (self.config.requests_per_minute / 60)
            bucket["tokens"] = min(
                self.config.requests_per_minute, bucket["tokens"] + tokens_to_add
            )
            bucket["last_refill"] = now

            # Check if request is allowed
            if bucket["tokens"] >= 1:
                bucket["tokens"] -= 1
                self.buckets[client_id] = bucket
                return True

            return False


class CircuitBreaker:
    """Circuit breaker for service protection"""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def can_execute(self) -> bool:
        """Check if circuit breaker allows execution"""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        else:  # HALF_OPEN
            return True

    def record_success(self):
        """Record successful execution"""
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self):
        """Record failed execution"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


class LoadBalancer:
    """Load balancer for service instances"""

    def __init__(self, strategy: str = "round_robin"):
        self.strategy = strategy
        self.instances: Dict[str, List[ServiceInstance]] = {}
        self.current_index: Dict[str, int] = {}

    def add_service_instances(
        self, service_name: str, instances: List[ServiceInstance]
    ):
        """Add service instances"""
        self.instances[service_name] = instances
        self.current_index[service_name] = 0

    def get_instance(self, service_name: str) -> Optional[ServiceInstance]:
        """Get next service instance"""
        if service_name not in self.instances or not self.instances[service_name]:
            return None

        instances = [
            inst
            for inst in self.instances[service_name]
            if inst.status == ServiceStatus.HEALTHY
        ]
        if not instances:
            return None

        if self.strategy == "round_robin":
            instance = instances[self.current_index[service_name] % len(instances)]
            self.current_index[service_name] = (
                self.current_index[service_name] + 1
            ) % len(instances)
            return instance

        elif self.strategy == "least_connections":
            return min(instances, key=lambda x: x.error_count)

        elif self.strategy == "health_score":
            return max(instances, key=lambda x: x.health_score)

        return instances[0]


class APIGateway:
    """Main API Gateway class"""

    def __init__(self):
        self.app = Flask(__name__)
        self.rate_limiter = RateLimiter(RateLimitConfig())
        self.load_balancer = LoadBalancer()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.service_registry: Dict[str, str] = {}
        self.request_count = 0
        self.error_count = 0

        # Setup routes
        self._setup_routes()

        # Setup middleware
        self._setup_middleware()

    def _setup_routes(self):
        """Setup API routes"""

        @self.app.route("/api/v1/events", methods=["POST"])
        def create_event():
            """Create new event"""
            return self._route_request_sync("event-service", "/events", request)

        @self.app.route("/api/v1/events/<event_id>", methods=["GET"])
        def get_event(event_id):
            """Get event by ID"""
            return self._route_request_sync(
                "event-service", f"/events/{event_id}", request
            )

        @self.app.route("/api/v1/alerts", methods=["GET"])
        def get_alerts():
            """Get alerts"""
            return self._route_request_sync("alert-service", "/alerts", request)

        @self.app.route("/api/v1/alerts/<alert_id>", methods=["GET"])
        def get_alert(alert_id):
            """Get alert by ID"""
            return self._route_request_sync(
                "alert-service", f"/alerts/{alert_id}", request
            )

        @self.app.route("/api/v1/metrics", methods=["GET"])
        def get_metrics():
            """Get system metrics"""
            return self._route_request_sync("monitoring-service", "/metrics", request)

        @self.app.route("/api/v1/health", methods=["GET"])
        def health_check():
            """Health check endpoint"""
            return jsonify(
                {
                    "status": "healthy",
                    "timestamp": time.time(),
                    "services": self._get_service_status(),
                }
            )

    def _setup_middleware(self):
        """Setup middleware"""

        @self.app.before_request
        def before_request():
            """Before request middleware"""
            g.start_time = time.time()
            g.request_id = str(uuid.uuid4())

            # Rate limiting
            client_id = self._get_client_id()
            # Use synchronous rate limiting check
            if not self._check_rate_limit_sync(client_id):
                raise TooManyRequests("Rate limit exceeded")

            # Authentication
            if not self._authenticate_request():
                raise Unauthorized("Authentication required")

            # Authorization
            if not self._authorize_request():
                raise Forbidden("Insufficient permissions")

        @self.app.after_request
        def after_request(response):
            """After request middleware"""
            # Log request
            duration = time.time() - g.start_time
            self._log_request(request, response, duration)

            # Update metrics
            self.request_count += 1
            if response.status_code >= 400:
                self.error_count += 1

            return response

    def _route_request_sync(
        self, service_name: str, path: str, original_request
    ) -> Dict[str, Any]:
        """Route request to appropriate service (synchronous version)"""
        # Get service instance
        instance = self.load_balancer.get_instance(service_name)
        if not instance:
            return jsonify({"error": "Service unavailable"}), 503

        # Check circuit breaker
        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = CircuitBreaker()

        circuit_breaker = self.circuit_breakers[service_name]
        if not circuit_breaker.can_execute():
            return jsonify({"error": "Service circuit breaker open"}), 503

        try:
            # Forward request
            url = f"{instance.url}{path}"
            response = self._forward_request_sync(url, original_request)

            # Record success
            circuit_breaker.record_success()
            instance.success_count += 1

            return response

        except Exception as e:
            # Record failure
            circuit_breaker.record_failure()
            instance.error_count += 1

            structured_logger.error(
                "Request forwarding failed",
                {
                    "service": service_name,
                    "path": path,
                    "error": str(e),
                    "request_id": g.request_id,
                },
            )

            return jsonify({"error": "Service unavailable"}), 503

    async def _route_request(
        self, service_name: str, path: str, original_request
    ) -> Dict[str, Any]:
        """Route request to appropriate service (async version)"""
        # Get service instance
        instance = self.load_balancer.get_instance(service_name)
        if not instance:
            return jsonify({"error": "Service unavailable"}), 503

        # Check circuit breaker
        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = CircuitBreaker()

        circuit_breaker = self.circuit_breakers[service_name]
        if not circuit_breaker.can_execute():
            return jsonify({"error": "Service circuit breaker open"}), 503

        try:
            # Forward request
            url = f"{instance.url}{path}"
            response = await self._forward_request(url, original_request)

            # Record success
            circuit_breaker.record_success()
            instance.success_count += 1

            return response

        except Exception as e:
            # Record failure
            circuit_breaker.record_failure()
            instance.error_count += 1

            structured_logger.error(
                "Request forwarding failed",
                {
                    "service": service_name,
                    "path": path,
                    "error": str(e),
                    "request_id": g.request_id,
                },
            )

            return jsonify({"error": "Service unavailable"}), 503

    def _forward_request_sync(self, url: str, original_request) -> Dict[str, Any]:
        """Forward request to service (synchronous version)"""
        # Prepare headers
        headers = dict(original_request.headers)
        headers["X-Request-ID"] = g.request_id
        headers["X-Forwarded-For"] = original_request.remote_addr

        # Forward request
        response = requests.request(
            method=original_request.method,
            url=url,
            headers=headers,
            data=original_request.get_data(),
            params=original_request.args,
            timeout=30,
        )

        return response.json(), response.status_code

    async def _forward_request(self, url: str, original_request) -> Dict[str, Any]:
        """Forward request to service (async version)"""
        # Prepare headers
        headers = dict(original_request.headers)
        headers["X-Request-ID"] = g.request_id
        headers["X-Forwarded-For"] = original_request.remote_addr

        # Forward request
        response = requests.request(
            method=original_request.method,
            url=url,
            headers=headers,
            data=original_request.get_data(),
            params=original_request.args,
            timeout=30,
        )

        return response.json(), response.status_code

    def _get_client_id(self) -> str:
        """Get client ID for rate limiting"""
        # Use IP address as client ID
        return request.remote_addr or "unknown"

    def _check_rate_limit_sync(self, client_id: str) -> bool:
        """Synchronous rate limiting check"""
        now = time.time()
        bucket = self.rate_limiter.buckets.get(
            client_id,
            {
                "tokens": self.rate_limiter.config.requests_per_minute,
                "last_refill": now,
            },
        )

        # Refill tokens
        time_passed = now - bucket["last_refill"]
        tokens_to_add = time_passed * (
            self.rate_limiter.config.requests_per_minute / 60
        )
        bucket["tokens"] = min(
            self.rate_limiter.config.requests_per_minute,
            bucket["tokens"] + tokens_to_add,
        )
        bucket["last_refill"] = now

        # Check if request is allowed
        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            self.rate_limiter.buckets[client_id] = bucket
            return True
        return False

    def _authenticate_request(self) -> bool:
        """Authenticate request"""
        # Simple JWT authentication
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return False

        token = auth_header[7:]  # Remove 'Bearer ' prefix
        return self._validate_jwt_token(token)

    def _validate_jwt_token(self, token: str) -> bool:
        """Validate JWT token"""
        # Simplified JWT validation
        try:
            # In production, use proper JWT library
            parts = token.split(".")
            if len(parts) != 3:
                return False

            # Basic validation (in production, verify signature)
            return True
        except (ValueError, TypeError, AttributeError) as e:
            logger.debug(f"Token validation failed: {e}")
            return False

    def _authorize_request(self) -> bool:
        """Authorize request"""
        # Simple authorization check
        # In production, implement proper RBAC
        return True

    def _log_request(self, request, response, duration: float):
        """Log request details"""
        structured_logger.info(
            "API Gateway Request",
            {
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "duration": duration,
                "client_ip": request.remote_addr,
                "request_id": g.request_id,
            },
        )

    def _get_service_status(self) -> Dict[str, Any]:
        """Get service status"""
        status = {}
        for service_name, instances in self.load_balancer.instances.items():
            healthy_instances = [
                inst for inst in instances if inst.status == ServiceStatus.HEALTHY
            ]
            status[service_name] = {
                "total_instances": len(instances),
                "healthy_instances": len(healthy_instances),
                "status": "healthy" if healthy_instances else "unhealthy",
            }
        return status

    def register_service(self, name: str, instances: List[ServiceInstance]):
        """Register service instances"""
        self.load_balancer.add_service_instances(name, instances)
        structured_logger.info(
            "Service registered",
            {"service_name": name, "instance_count": len(instances)},
        )

    def get_gateway_metrics(self) -> Dict[str, Any]:
        """Get gateway metrics"""
        return {
            "total_requests": self.request_count,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(1, self.request_count),
            "services": self._get_service_status(),
            "circuit_breakers": {
                name: {"state": cb.state, "failure_count": cb.failure_count}
                for name, cb in self.circuit_breakers.items()
            },
        }

    def run(self, host: str = "0.0.0.0", port: int = 8080, debug: bool = False):
        """Run the API Gateway"""
        structured_logger.info(
            "Starting API Gateway", {"host": host, "port": port, "debug": debug}
        )

        self.app.run(host=host, port=port, debug=debug)


# Global API Gateway instance
_gateway: Optional[APIGateway] = None


def get_api_gateway() -> APIGateway:
    """Get global API Gateway instance"""
    global _gateway
    if _gateway is None:
        _gateway = APIGateway()
    return _gateway


def create_service_instance(
    name: str, url: str, status: ServiceStatus = ServiceStatus.HEALTHY
) -> ServiceInstance:
    """Create service instance"""
    return ServiceInstance(
        name=name,
        url=url,
        status=status,
        last_health_check=time.time(),
        response_time=0.0,
    )
