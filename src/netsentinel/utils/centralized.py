#!/usr/bin/env python3
"""
NetSentinel Centralized Utilities
Consolidated utility functions for all NetSentinel components
"""

import asyncio
import json
import time
import uuid
import hashlib
import hmac
import base64
import threading
import random
from typing import Any, Dict, List, Optional, Union, Callable, TypeVar
from dataclasses import dataclass, field
from functools import wraps
import logging

# Avoid circular imports by using local implementations
# This eliminates the circular dependency issue


# Local implementations to avoid circular imports
def handle_errors_simple(
    error: Exception, context: str = "", log_level: str = "ERROR"
) -> None:
    """Simple error handling without circular dependencies"""
    logger.error(f"Error in {context}: {str(error)}")


def create_error_context_simple(operation: str, module: str = "") -> str:
    """Simple error context creation"""
    return f"{module}:{operation}"


def create_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Create a logger instance"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    return logger


# Local utility registry to avoid circular imports
class UtilityCategory:
    CONNECTION = "connection"
    ERROR_HANDLING = "error_handling"
    CONFIGURATION = "configuration"
    LOGGING = "logging"
    VALIDATION = "validation"
    DATA_PROCESSING = "data_processing"
    SECURITY = "security"
    PERFORMANCE = "performance"
    CACHING = "caching"
    ASYNC = "async"
    INTEGRATION = "integration"
    TESTING = "testing"


_utility_registry = {}


def register_utility(name: str, category: str, description: str = ""):
    """Register a utility function"""

    def decorator(func):
        _utility_registry[name] = {
            "function": func,
            "category": category,
            "description": description,
        }
        return func

    return decorator


def get_registry():
    """Get the utility registry"""
    return _utility_registry


logger = logging.getLogger(__name__)

# Type variables for generic utilities
T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")

# ============================================================================
# CONNECTION UTILITIES
# ============================================================================


@register_utility(
    name="create_connection_pool",
    category=UtilityCategory.CONNECTION,
    description="Create a connection pool with specified configuration",
)
def create_connection_pool(
    host: str,
    port: int,
    max_connections: int = 10,
    timeout: float = 30.0,
    retry_attempts: int = 3,
) -> Dict[str, Any]:
    """Create a connection pool configuration"""
    return {
        "host": host,
        "port": port,
        "max_connections": max_connections,
        "timeout": timeout,
        "retry_attempts": retry_attempts,
        "created_at": time.time(),
        "active_connections": 0,
    }


@register_utility(
    name="validate_connection",
    category=UtilityCategory.CONNECTION,
    description="Validate a connection configuration",
)
def validate_connection(config: Dict[str, Any]) -> bool:
    """Validate connection configuration"""
    required_fields = ["host", "port"]
    return all(field in config for field in required_fields)


@register_utility(
    name="get_connection_string",
    category=UtilityCategory.CONNECTION,
    description="Generate connection string from configuration",
)
def get_connection_string(config: Dict[str, Any], protocol: str = "tcp") -> str:
    """Generate connection string from configuration"""
    return f"{protocol}://{config['host']}:{config['port']}"


# ============================================================================
# ERROR HANDLING UTILITIES
# ============================================================================


@register_utility(
    name="retry_with_backoff",
    category=UtilityCategory.ERROR_HANDLING,
    description="Retry function with exponential backoff",
)
def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: tuple = (Exception,),
):
    """Decorator for retry with exponential backoff"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        raise e

                    delay = min(base_delay * (exponential_base**attempt), max_delay)
                    if jitter:
                        delay *= 0.5 + 0.5 * random.random()

                    await asyncio.sleep(delay)
            raise last_exception

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        raise e

                    delay = min(base_delay * (exponential_base**attempt), max_delay)
                    if jitter:
                        delay *= 0.5 + 0.5 * random.random()

                    time.sleep(delay)
            raise last_exception

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


@register_utility(
    name="handle_errors_simple",
    category=UtilityCategory.ERROR_HANDLING,
    description="Handle errors with context - simple version",
)
def handle_errors_simple(
    error: Exception,
    context: str = "",
    log_level: str = "ERROR",
    return_value: Any = None,
) -> Any:
    """Handle errors with context - simple version"""
    error_msg = f"Error in {context}: {str(error)}" if context else str(error)
    if log_level.upper() == "ERROR":
        logger.error(error_msg, exc_info=True)
    elif log_level.upper() == "WARNING":
        logger.warning(error_msg)
    else:
        logger.info(error_msg)
    return return_value


@register_utility(
    name="create_error_context_simple",
    category=UtilityCategory.ERROR_HANDLING,
    description="Create error context - simple version",
)
def create_error_context_simple(
    operation: str,
    module: str = "",
    user_id: str = "",
    request_id: str = "",
    additional_data: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """Create error context - simple version"""
    return {
        "operation": operation,
        "module": module,
        "user_id": user_id,
        "request_id": request_id or str(uuid.uuid4()),
        "timestamp": time.time(),
        "additional_data": additional_data or {},
    }


# ============================================================================
# CONFIGURATION UTILITIES
# ============================================================================


@register_utility(
    name="load_config",
    category=UtilityCategory.CONFIGURATION,
    description="Load configuration from environment variables",
)
def load_config(
    prefix: str = "NETSENTINEL",
    required_keys: List[str] = None,
    default_values: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """Load configuration from environment variables"""
    import os

    config = {}
    required_keys = required_keys or []
    default_values = default_values or {}

    for key in required_keys:
        env_key = f"{prefix}_{key.upper()}"
        value = os.getenv(env_key)
        if value is None and key not in default_values:
            raise ValueError(f"Required configuration key {env_key} not found")
        config[key] = value or default_values.get(key)

    return config


@register_utility(
    name="validate_config",
    category=UtilityCategory.CONFIGURATION,
    description="Validate configuration values",
)
def validate_config(config: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    """Validate configuration against schema"""
    errors = []

    for key, rules in schema.items():
        if key not in config:
            if rules.get("required", False):
                errors.append(f"Required key '{key}' not found")
            continue

        value = config[key]
        value_type = rules.get("type")

        if value_type and not isinstance(value, value_type):
            errors.append(f"Key '{key}' must be of type {value_type.__name__}")

        if "min" in rules and value < rules["min"]:
            errors.append(f"Key '{key}' must be >= {rules['min']}")

        if "max" in rules and value > rules["max"]:
            errors.append(f"Key '{key}' must be <= {rules['max']}")

    return errors


@register_utility(
    name="merge_configs",
    category=UtilityCategory.CONFIGURATION,
    description="Merge multiple configuration dictionaries",
)
def merge_configs(*configs: Dict[str, Any]) -> Dict[str, Any]:
    """Merge multiple configuration dictionaries"""
    result = {}
    for config in configs:
        result.update(config)
    return result


# ============================================================================
# LOGGING UTILITIES
# ============================================================================


@register_utility(
    name="create_logger",
    category=UtilityCategory.LOGGING,
    description="Create a logger instance",
)
def create_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Create a logger instance"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Prevent duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


@register_utility(
    name="get_structured_logger",
    category=UtilityCategory.LOGGING,
    description="Get structured logger",
)
def get_structured_logger(service_name: str = "netsentinel") -> logging.Logger:
    """Get structured logger"""
    return create_logger(service_name)


# ============================================================================
# VALIDATION UTILITIES
# ============================================================================


@register_utility(
    name="validate_event",
    category=UtilityCategory.VALIDATION,
    description="Validate event data structure",
)
def validate_event(event: Dict[str, Any]) -> List[str]:
    """Validate event data structure"""
    errors = []
    required_fields = ["id", "timestamp", "type", "data"]

    for field in required_fields:
        if field not in event:
            errors.append(f"Missing required field: {field}")

    if "timestamp" in event and not isinstance(event["timestamp"], (int, float)):
        errors.append("Timestamp must be numeric")

    if "data" in event and not isinstance(event["data"], dict):
        errors.append("Data must be a dictionary")

    return errors


@register_utility(
    name="validate_alert",
    category=UtilityCategory.VALIDATION,
    description="Validate alert data structure",
)
def validate_alert(alert: Dict[str, Any]) -> List[str]:
    """Validate alert data structure"""
    errors = []
    required_fields = ["id", "title", "severity", "timestamp"]

    for field in required_fields:
        if field not in alert:
            errors.append(f"Missing required field: {field}")

    if "severity" in alert and alert["severity"] not in [
        "low",
        "medium",
        "high",
        "critical",
    ]:
        errors.append("Severity must be one of: low, medium, high, critical")

    return errors


@register_utility(
    name="validate_ip_address",
    category=UtilityCategory.VALIDATION,
    description="Validate IP address format",
)
def validate_ip_address(ip: str) -> bool:
    """Validate IP address format"""
    import ipaddress

    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


# Validation functions moved to utils/consolidated_validation.py to avoid duplication


# ============================================================================
# DATA PROCESSING UTILITIES
# ============================================================================


@register_utility(
    name="generate_id",
    category=UtilityCategory.DATA_PROCESSING,
    description="Generate unique identifier",
)
def generate_id(prefix: str = "") -> str:
    """Generate unique identifier"""
    return f"{prefix}{uuid.uuid4().hex}" if prefix else str(uuid.uuid4())


@register_utility(
    name="hash_data",
    category=UtilityCategory.DATA_PROCESSING,
    description="Hash data using specified algorithm",
)
def hash_data(data: Union[str, bytes], algorithm: str = "sha256") -> str:
    """Hash data using specified algorithm"""
    if isinstance(data, str):
        data = data.encode("utf-8")

    if algorithm == "sha256":
        return hashlib.sha256(data).hexdigest()
    elif algorithm == "md5":
        return hashlib.md5(data).hexdigest()
    elif algorithm == "sha1":
        return hashlib.sha1(data).hexdigest()
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")


@register_utility(
    name="serialize_data",
    category=UtilityCategory.DATA_PROCESSING,
    description="Serialize data to JSON string",
)
def serialize_data(data: Any) -> str:
    """Serialize data to JSON string"""
    return json.dumps(data, default=str)


@register_utility(
    name="deserialize_data",
    category=UtilityCategory.DATA_PROCESSING,
    description="Deserialize JSON string to data",
)
def deserialize_data(json_str: str) -> Any:
    """Deserialize JSON string to data"""
    return json.loads(json_str)


@register_utility(
    name="deep_merge",
    category=UtilityCategory.DATA_PROCESSING,
    description="Deep merge two dictionaries",
)
def deep_merge(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries"""
    result = dict1.copy()

    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result


# ============================================================================
# SECURITY UTILITIES
# ============================================================================


@register_utility(
    name="generate_hmac",
    category=UtilityCategory.SECURITY,
    description="Generate HMAC signature",
)
def generate_hmac(data: str, secret: str, algorithm: str = "sha256") -> str:
    """Generate HMAC signature"""
    if algorithm == "sha256":
        return hmac.new(secret.encode(), data.encode(), hashlib.sha256).hexdigest()
    elif algorithm == "sha1":
        return hmac.new(secret.encode(), data.encode(), hashlib.sha1).hexdigest()
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")


@register_utility(
    name="verify_hmac",
    category=UtilityCategory.SECURITY,
    description="Verify HMAC signature",
)
def verify_hmac(
    data: str, signature: str, secret: str, algorithm: str = "sha256"
) -> bool:
    """Verify HMAC signature"""
    expected_signature = generate_hmac(data, secret, algorithm)
    return hmac.compare_digest(signature, expected_signature)


@register_utility(
    name="encode_base64",
    category=UtilityCategory.SECURITY,
    description="Encode data to base64",
)
def encode_base64(data: Union[str, bytes]) -> str:
    """Encode data to base64"""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return base64.b64encode(data).decode("utf-8")


@register_utility(
    name="decode_base64",
    category=UtilityCategory.SECURITY,
    description="Decode base64 data",
)
def decode_base64(data: str) -> str:
    """Decode base64 data"""
    return base64.b64decode(data).decode("utf-8")


# ============================================================================
# PERFORMANCE UTILITIES
# ============================================================================


@register_utility(
    name="measure_time",
    category=UtilityCategory.PERFORMANCE,
    description="Measure execution time of function",
)
def measure_time(func: Callable) -> Callable:
    """Decorator to measure execution time"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logger.info(
            f"Function {func.__name__} took {end_time - start_time:.4f} seconds"
        )
        return result

    return wrapper


@register_utility(
    name="create_timer",
    category=UtilityCategory.PERFORMANCE,
    description="Create a timer context manager",
)
def create_timer(name: str = "operation") -> "Timer":
    """Create a timer context manager"""
    return Timer(name)


class Timer:
    """Timer context manager"""

    def __init__(self, name: str = "operation"):
        self.name = name
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        logger.info(f"Timer '{self.name}': {duration:.4f} seconds")

    @property
    def duration(self) -> float:
        """Get timer duration"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0


# ============================================================================
# CACHING UTILITIES
# ============================================================================


@register_utility(
    name="create_cache",
    category=UtilityCategory.CACHING,
    description="Create a simple in-memory cache",
)
def create_cache(max_size: int = 1000, ttl: float = 3600.0) -> "SimpleCache":
    """Create a simple in-memory cache"""
    return SimpleCache(max_size, ttl)


class SimpleCache:
    """Simple in-memory cache with TTL"""

    def __init__(self, max_size: int = 1000, ttl: float = 3600.0):
        self.max_size = max_size
        self.ttl = ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> Any:
        """Get value from cache"""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if time.time() - entry["timestamp"] < self.ttl:
                    return entry["value"]
                else:
                    del self._cache[key]
            return None

    def set(self, key: str, value: Any) -> None:
        """Set value in cache"""
        with self._lock:
            if len(self._cache) >= self.max_size:
                # Remove oldest entry
                oldest_key = min(
                    self._cache.keys(), key=lambda k: self._cache[k]["timestamp"]
                )
                del self._cache[oldest_key]

            self._cache[key] = {"value": value, "timestamp": time.time()}

    def delete(self, key: str) -> None:
        """Delete value from cache"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]

    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        """Get cache size"""
        with self._lock:
            return len(self._cache)


# ============================================================================
# ASYNC UTILITIES
# ============================================================================


@register_utility(
    name="run_async",
    category=UtilityCategory.ASYNC,
    description="Run async function in sync context",
)
def run_async(func: Callable, *args, **kwargs) -> Any:
    """Run async function in sync context"""
    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(func(*args, **kwargs))
    except RuntimeError:
        return asyncio.run(func(*args, **kwargs))


@register_utility(
    name="create_async_pool",
    category=UtilityCategory.ASYNC,
    description="Create async task pool",
)
def create_async_pool(max_workers: int = 10) -> "AsyncPool":
    """Create async task pool"""
    return AsyncPool(max_workers)


class AsyncPool:
    """Async task pool"""

    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self._semaphore = asyncio.Semaphore(max_workers)

    async def submit(self, func: Callable, *args, **kwargs) -> Any:
        """Submit task to pool"""
        async with self._semaphore:
            return await func(*args, **kwargs)

    async def map(self, func: Callable, iterable: List[Any]) -> List[Any]:
        """Map function over iterable"""
        tasks = [self.submit(func, item) for item in iterable]
        return await asyncio.gather(*tasks)


# ============================================================================
# INTEGRATION UTILITIES
# ============================================================================


@register_utility(
    name="create_webhook_payload",
    category=UtilityCategory.INTEGRATION,
    description="Create webhook payload",
)
def create_webhook_payload(
    event_type: str, data: Dict[str, Any], timestamp: float = None
) -> Dict[str, Any]:
    """Create webhook payload"""
    return {
        "event_type": event_type,
        "data": data,
        "timestamp": timestamp or time.time(),
        "id": generate_id("webhook_"),
    }


@register_utility(
    name="validate_webhook_signature",
    category=UtilityCategory.INTEGRATION,
    description="Validate webhook signature",
)
def validate_webhook_signature(payload: str, signature: str, secret: str) -> bool:
    """Validate webhook signature"""
    return verify_hmac(payload, signature, secret)


# ============================================================================
# TESTING UTILITIES
# ============================================================================


@register_utility(
    name="create_mock_data",
    category=UtilityCategory.TESTING,
    description="Create mock data for testing",
)
def create_mock_data(
    data_type: str, count: int = 1
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """Create mock data for testing"""
    if data_type == "event":
        events = []
        for i in range(count):
            events.append(
                {
                    "id": generate_id("event_"),
                    "timestamp": time.time() - i * 60,
                    "type": "test_event",
                    "data": {"test": True, "index": i},
                }
            )
        return events[0] if count == 1 else events

    elif data_type == "alert":
        alerts = []
        for i in range(count):
            alerts.append(
                {
                    "id": generate_id("alert_"),
                    "title": f"Test Alert {i}",
                    "severity": "medium",
                    "timestamp": time.time() - i * 60,
                    "data": {"test": True, "index": i},
                }
            )
        return alerts[0] if count == 1 else alerts

    else:
        raise ValueError(f"Unsupported data type: {data_type}")


@register_utility(
    name="assert_equals",
    category=UtilityCategory.TESTING,
    description="Assert two values are equal",
)
def assert_equals(actual: Any, expected: Any, message: str = "") -> bool:
    """Assert two values are equal"""
    if actual != expected:
        error_msg = f"Assertion failed: {actual} != {expected}"
        if message:
            error_msg += f" - {message}"
        raise AssertionError(error_msg)
    return True


# ============================================================================
# UTILITY REGISTRY INITIALIZATION
# ============================================================================


def initialize_utilities():
    """Initialize all utilities in the registry"""
    registry = get_registry()

    # Register all utilities from this module
    # (This happens automatically when the module is imported)

    logger.info(f"Initialized {len(registry)} utilities")
    return registry


# Initialize utilities when module is imported
initialize_utilities()
