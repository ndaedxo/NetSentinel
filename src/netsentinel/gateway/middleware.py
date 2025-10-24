#!/usr/bin/env python3
"""
Middleware for NetSentinel API Gateway
Authentication, rate limiting, and logging middleware
"""

import time
import jwt
import hashlib
import secrets
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque
from flask import request, g, jsonify
import logging

logger = logging.getLogger(__name__)


class AuthMiddleware:
    """Authentication middleware for API Gateway"""

    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.token_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 300  # 5 minutes
        self.logger = logging.getLogger(f"{__name__}.AuthMiddleware")

    def authenticate(self):
        """Authenticate incoming request"""
        try:
            # Skip authentication for health check
            if request.path == "/health":
                return None

            # Get token from header
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                return jsonify({"error": "Authorization header required"}), 401

            # Extract token
            if not auth_header.startswith("Bearer "):
                return jsonify({"error": "Invalid authorization format"}), 401

            token = auth_header[7:]  # Remove 'Bearer ' prefix

            # Verify token
            user_info = self._verify_token(token)
            if not user_info:
                return jsonify({"error": "Invalid or expired token"}), 401

            # Set user info in request context
            g.user_id = user_info.get("user_id")
            g.user_roles = user_info.get("roles", [])
            g.user_permissions = user_info.get("permissions", [])

            return None  # Continue processing

        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            return jsonify({"error": "Authentication failed"}), 401

    def _verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token"""
        try:
            # Check cache first
            if token in self.token_cache:
                cached_info = self.token_cache[token]
                if time.time() - cached_info["cached_at"] < self.cache_ttl:
                    return cached_info["user_info"]
                else:
                    del self.token_cache[token]

            # Verify token
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])

            # Check expiration
            if payload.get("exp", 0) < time.time():
                return None

            user_info = {
                "user_id": payload.get("user_id"),
                "roles": payload.get("roles", []),
                "permissions": payload.get("permissions", []),
            }

            # Cache token info
            self.token_cache[token] = {"user_info": user_info, "cached_at": time.time()}

            return user_info

        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
        except Exception as e:
            self.logger.error(f"Token verification error: {e}")
            return None

    def generate_token(
        self,
        user_id: str,
        roles: list = None,
        permissions: list = None,
        expires_in: int = 3600,
    ) -> str:
        """Generate JWT token"""
        payload = {
            "user_id": user_id,
            "roles": roles or [],
            "permissions": permissions or [],
            "exp": datetime.utcnow() + timedelta(seconds=expires_in),
            "iat": datetime.utcnow(),
        }

        return jwt.encode(payload, self.secret_key, algorithm="HS256")

    def clear_cache(self):
        """Clear token cache"""
        self.token_cache.clear()


class RateLimitMiddleware:
    """Rate limiting middleware for API Gateway"""

    def __init__(self):
        self.rate_limits: Dict[str, Dict[str, Any]] = {}
        self.client_requests: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.burst_limits: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(f"{__name__}.RateLimitMiddleware")

    def check_rate_limit(self):
        """Check rate limit for request"""
        try:
            # Skip rate limiting for health check
            if request.path == "/health":
                return None

            client_id = self._get_client_id()
            endpoint = request.path

            # Get rate limit config for endpoint
            rate_limit_config = self.rate_limits.get(endpoint, {})
            if not rate_limit_config:
                return None  # No rate limit configured

            # Check rate limit
            if not self._is_allowed(client_id, endpoint, rate_limit_config):
                return (
                    jsonify(
                        {
                            "error": "Rate limit exceeded",
                            "retry_after": rate_limit_config.get("window_size", 60),
                        }
                    ),
                    429,
                )

            return None  # Continue processing

        except Exception as e:
            self.logger.error(f"Rate limit check error: {e}")
            return None  # Allow request on error

    def _get_client_id(self) -> str:
        """Get client identifier"""
        # Use IP address as client ID
        client_ip = request.remote_addr

        # Add user ID if available
        user_id = getattr(g, "user_id", None)
        if user_id:
            return f"{client_ip}:{user_id}"

        return client_ip

    def _is_allowed(
        self, client_id: str, endpoint: str, config: Dict[str, Any]
    ) -> bool:
        """Check if request is allowed"""
        current_time = time.time()
        window_size = config.get("window_size", 60)
        requests_per_window = config.get("requests_per_window", 100)
        burst_limit = config.get("burst_limit", 20)

        # Get client request history
        client_key = f"{client_id}:{endpoint}"
        requests = self.client_requests[client_key]

        # Remove old requests outside window
        cutoff_time = current_time - window_size
        while requests and requests[0] < cutoff_time:
            requests.popleft()

        # Check burst limit (requests in last 10 seconds)
        recent_requests = [
            req_time for req_time in requests if req_time > current_time - 10
        ]
        if len(recent_requests) >= burst_limit:
            return False

        # Check window limit
        if len(requests) >= requests_per_window:
            return False

        # Add current request
        requests.append(current_time)

        return True

    def set_rate_limit(self, endpoint: str, config: Dict[str, Any]) -> None:
        """Set rate limit for endpoint"""
        self.rate_limits[endpoint] = {
            "requests_per_window": config.requests_per_minute,
            "window_size": config.window_size,
            "burst_limit": config.burst_limit,
        }
        self.logger.info(
            f"Set rate limit for {endpoint}: {config.requests_per_minute} req/min"
        )

    def get_rate_limit_status(self, client_id: str, endpoint: str) -> Dict[str, Any]:
        """Get rate limit status for client"""
        client_key = f"{client_id}:{endpoint}"
        requests = self.client_requests[client_key]
        current_time = time.time()

        # Count requests in different windows
        last_minute = len([req for req in requests if req > current_time - 60])
        last_10_seconds = len([req for req in requests if req > current_time - 10])

        return {
            "requests_last_minute": last_minute,
            "requests_last_10_seconds": last_10_seconds,
            "total_requests": len(requests),
        }


class LoggingMiddleware:
    """Logging middleware for API Gateway"""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.LoggingMiddleware")
        self.request_count = 0
        self.error_count = 0

    def log_request(self):
        """Log incoming request"""
        try:
            # Set request start time
            g.request_start_time = time.time()
            g.request_id = self._generate_request_id()

            # Log request
            self.logger.info(
                f"Request started: {request.method} {request.path} - "
                f"Client: {request.remote_addr} - "
                f"Request ID: {g.request_id}"
            )

            # Increment request count
            self.request_count += 1

        except Exception as e:
            self.logger.error(f"Request logging error: {e}")

    def log_response(self, response):
        """Log response"""
        try:
            # Calculate response time
            response_time = time.time() - getattr(g, "request_start_time", time.time())

            # Get response status
            status_code = response.status_code

            # Log response
            self.logger.info(
                f"Request completed: {request.method} {request.path} - "
                f"Status: {status_code} - "
                f"Response time: {response_time:.3f}s - "
                f"Request ID: {getattr(g, 'request_id', 'unknown')}"
            )

            # Count errors
            if status_code >= 400:
                self.error_count += 1

            # Add response headers
            response.headers["X-Response-Time"] = f"{response_time:.3f}"
            response.headers["X-Request-ID"] = getattr(g, "request_id", "unknown")

            return response

        except Exception as e:
            self.logger.error(f"Response logging error: {e}")
            return response

    def _generate_request_id(self) -> str:
        """Generate unique request ID"""
        timestamp = str(int(time.time() * 1000))
        random_part = secrets.token_hex(4)
        return f"{timestamp}-{random_part}"

    def get_logging_stats(self) -> Dict[str, Any]:
        """Get logging statistics"""
        return {
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "error_rate": self.error_count / max(self.request_count, 1),
        }


class SecurityMiddleware:
    """Security middleware for API Gateway"""

    def __init__(self):
        self.blocked_ips: set = set()
        self.suspicious_ips: Dict[str, int] = defaultdict(int)
        self.logger = logging.getLogger(f"{__name__}.SecurityMiddleware")

    def check_security(self):
        """Check security for request"""
        try:
            client_ip = request.remote_addr

            # Check if IP is blocked
            if client_ip in self.blocked_ips:
                self.logger.warning(f"Blocked IP attempted access: {client_ip}")
                return jsonify({"error": "Access denied"}), 403

            # Check for suspicious activity
            if self._is_suspicious_request():
                self.suspicious_ips[client_ip] += 1

                # Block IP if too many suspicious requests
                if self.suspicious_ips[client_ip] >= 10:
                    self.blocked_ips.add(client_ip)
                    self.logger.warning(
                        f"IP blocked due to suspicious activity: {client_ip}"
                    )
                    return jsonify({"error": "Access denied"}), 403

            return None  # Continue processing

        except Exception as e:
            self.logger.error(f"Security check error: {e}")
            return None  # Allow request on error

    def _is_suspicious_request(self) -> bool:
        """Check if request is suspicious"""
        # Check for common attack patterns
        suspicious_patterns = [
            "..",  # Directory traversal
            "<script",  # XSS
            "union select",  # SQL injection
            "exec(",  # Command injection
            "eval(",  # Code injection
        ]

        # Check URL path
        path = request.path.lower()
        for pattern in suspicious_patterns:
            if pattern in path:
                return True

        # Check query parameters
        for param, value in request.args.items():
            if isinstance(value, str):
                value_lower = value.lower()
                for pattern in suspicious_patterns:
                    if pattern in value_lower:
                        return True

        # Check request body for POST requests
        if request.method == "POST" and request.json:
            body_str = str(request.json).lower()
            for pattern in suspicious_patterns:
                if pattern in body_str:
                    return True

        return False

    def unblock_ip(self, ip: str) -> None:
        """Unblock IP address"""
        self.blocked_ips.discard(ip)
        self.suspicious_ips.pop(ip, None)
        self.logger.info(f"IP unblocked: {ip}")

    def get_security_stats(self) -> Dict[str, Any]:
        """Get security statistics"""
        return {
            "blocked_ips": len(self.blocked_ips),
            "suspicious_ips": len(self.suspicious_ips),
            "blocked_ip_list": list(self.blocked_ips),
            "suspicious_ip_list": dict(self.suspicious_ips),
        }
