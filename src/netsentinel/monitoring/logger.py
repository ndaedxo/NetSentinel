#!/usr/bin/env python3
"""
Centralized Logging System for NetSentinel
Consolidates functionality from utils/logging.py and core/logging_config.py to eliminate code debt
JSON-based structured logging with correlation IDs and context
"""

import json
import logging
import logging.handlers
import time
import uuid
import sys
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import threading
from contextvars import ContextVar
from pathlib import Path

# Import centralized utilities (using absolute imports to avoid circular dependencies)
try:
    from ..utils.centralized import (
        generate_id,
        hash_data,
        serialize_data,
        deserialize_data,
        create_error_context,
        handle_errors,
        load_config,
        validate_config,
    )
except ImportError:
    # Fallback for direct execution
    import uuid

    def generate_id(prefix: str = "") -> str:
        return f"{prefix}{uuid.uuid4().hex}" if prefix else str(uuid.uuid4())

    def hash_data(data, algorithm: str = "sha256") -> str:
        import hashlib

        if isinstance(data, str):
            data = data.encode("utf-8")
        return hashlib.sha256(data).hexdigest()

    def serialize_data(data) -> str:
        import json

        return json.dumps(data, default=str)

    def deserialize_data(json_str: str):
        import json

        return json.loads(json_str)

    # These functions are now imported from centralized utilities
    # to avoid duplication

    def load_config(
        prefix: str = "NETSENTINEL",
        required_keys: list = None,
        default_values: dict = None,
    ):
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

    def validate_config(config: dict, schema: dict) -> list:
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
        return errors


logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """Log level enumeration"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(Enum):
    """Log category enumeration"""

    SYSTEM = "system"
    SECURITY = "security"
    PERFORMANCE = "performance"
    AUDIT = "audit"
    ERROR = "error"
    BUSINESS = "business"


@dataclass
class LogContext:
    """Logging context for request correlation"""

    request_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    service_name: str = "netsentinel"
    version: str = "1.0.0"
    environment: str = "development"


# Context variables for request correlation
request_context: ContextVar[LogContext] = ContextVar("request_context")


class StructuredLogger:
    """
    Structured logger for NetSentinel
    Provides JSON-based logging with correlation IDs and context
    """

    def __init__(self, name: str = "netsentinel", service_name: str = "netsentinel"):
        self.name = name
        self.service_name = service_name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        # Add JSON formatter
        self._setup_json_handler()

        # Thread-local storage for context
        self._local = threading.local()

    def _setup_json_handler(self) -> None:
        """Setup JSON log handler"""
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        self.logger.addHandler(handler)

    def set_context(self, context: LogContext) -> None:
        """Set logging context"""
        request_context.set(context)
        self._local.context = context

    def get_context(self) -> Optional[LogContext]:
        """Get current logging context"""
        try:
            return request_context.get()
        except LookupError:
            return getattr(self._local, "context", None)

    def _create_log_entry(
        self,
        level: LogLevel,
        message: str,
        category: LogCategory = LogCategory.SYSTEM,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create structured log entry"""
        context = self.get_context()
        timestamp = datetime.now().isoformat()

        log_entry = {
            "timestamp": timestamp,
            "level": level.value,
            "category": category.value,
            "message": message,
            "service": self.service_name,
            "logger": self.name,
        }

        # Add context if available
        if context:
            log_entry.update(
                {
                    "request_id": context.request_id,
                    "user_id": context.user_id,
                    "session_id": context.session_id,
                    "trace_id": context.trace_id,
                    "span_id": context.span_id,
                    "service_name": context.service_name,
                    "version": context.version,
                    "environment": context.environment,
                }
            )

        # Add additional fields
        log_entry.update(kwargs)

        return log_entry

    def debug(
        self, message: str, category: LogCategory = LogCategory.SYSTEM, **kwargs
    ) -> None:
        """Log debug message"""
        log_entry = self._create_log_entry(LogLevel.DEBUG, message, category, **kwargs)
        self.logger.debug(json.dumps(log_entry))

    def info(
        self, message: str, category: LogCategory = LogCategory.SYSTEM, **kwargs
    ) -> None:
        """Log info message"""
        log_entry = self._create_log_entry(LogLevel.INFO, message, category, **kwargs)
        self.logger.info(json.dumps(log_entry))

    def warning(
        self, message: str, category: LogCategory = LogCategory.SYSTEM, **kwargs
    ) -> None:
        """Log warning message"""
        log_entry = self._create_log_entry(
            LogLevel.WARNING, message, category, **kwargs
        )
        self.logger.warning(json.dumps(log_entry))

    def error(
        self, message: str, category: LogCategory = LogCategory.ERROR, **kwargs
    ) -> None:
        """Log error message"""
        log_entry = self._create_log_entry(LogLevel.ERROR, message, category, **kwargs)
        self.logger.error(json.dumps(log_entry))

    def critical(
        self, message: str, category: LogCategory = LogCategory.ERROR, **kwargs
    ) -> None:
        """Log critical message"""
        log_entry = self._create_log_entry(
            LogLevel.CRITICAL, message, category, **kwargs
        )
        self.logger.critical(json.dumps(log_entry))

    # Specialized logging methods
    def log_security_event(self, event_type: str, message: str, **kwargs) -> None:
        """Log security event"""
        self.info(
            message, category=LogCategory.SECURITY, event_type=event_type, **kwargs
        )

    def log_performance_metric(
        self, metric_name: str, value: float, unit: str = None, **kwargs
    ) -> None:
        """Log performance metric"""
        self.info(
            f"Performance metric: {metric_name}",
            category=LogCategory.PERFORMANCE,
            metric_name=metric_name,
            metric_value=value,
            metric_unit=unit,
            **kwargs,
        )

    def log_audit_event(
        self, action: str, resource: str, result: str, **kwargs
    ) -> None:
        """Log audit event"""
        self.info(
            f"Audit: {action} on {resource} - {result}",
            category=LogCategory.AUDIT,
            audit_action=action,
            audit_resource=resource,
            audit_result=result,
            **kwargs,
        )

    def log_business_event(self, event_type: str, message: str, **kwargs) -> None:
        """Log business event"""
        self.info(
            message,
            category=LogCategory.BUSINESS,
            business_event_type=event_type,
            **kwargs,
        )

    def log_error_with_context(
        self, error: Exception, context: str = None, **kwargs
    ) -> None:
        """Log error with full context"""
        self.error(
            f"Error in {context or 'unknown context'}: {str(error)}",
            category=LogCategory.ERROR,
            error_type=type(error).__name__,
            error_message=str(error),
            error_context=context,
            **kwargs,
        )

    def log_request(
        self, method: str, path: str, status_code: int, response_time: float, **kwargs
    ) -> None:
        """Log HTTP request"""
        self.info(
            f"HTTP {method} {path} - {status_code}",
            category=LogCategory.SYSTEM,
            http_method=method,
            http_path=path,
            http_status_code=status_code,
            response_time_ms=response_time * 1000,
            **kwargs,
        )

    def log_database_operation(
        self, operation: str, table: str, duration: float, **kwargs
    ) -> None:
        """Log database operation"""
        self.info(
            f"Database {operation} on {table}",
            category=LogCategory.SYSTEM,
            db_operation=operation,
            db_table=table,
            db_duration_ms=duration * 1000,
            **kwargs,
        )

    def log_cache_operation(
        self, operation: str, key: str, hit: bool, **kwargs
    ) -> None:
        """Log cache operation"""
        self.info(
            f"Cache {operation} for {key} - {'HIT' if hit else 'MISS'}",
            category=LogCategory.SYSTEM,
            cache_operation=operation,
            cache_key=key,
            cache_hit=hit,
            **kwargs,
        )

    def log_threat_detection(
        self, threat_type: str, severity: str, source_ip: str, **kwargs
    ) -> None:
        """Log threat detection"""
        self.warning(
            f"Threat detected: {threat_type} from {source_ip}",
            category=LogCategory.SECURITY,
            threat_type=threat_type,
            threat_severity=severity,
            source_ip=source_ip,
            **kwargs,
        )

    def log_alert_created(
        self, alert_id: str, severity: str, source: str, **kwargs
    ) -> None:
        """Log alert creation"""
        self.info(
            f"Alert created: {alert_id}",
            category=LogCategory.SECURITY,
            alert_id=alert_id,
            alert_severity=severity,
            alert_source=source,
            **kwargs,
        )

    def log_firewall_action(
        self, action: str, ip_address: str, rule_id: str, **kwargs
    ) -> None:
        """Log firewall action"""
        self.info(
            f"Firewall {action}: {ip_address}",
            category=LogCategory.SECURITY,
            firewall_action=action,
            ip_address=ip_address,
            rule_id=rule_id,
            **kwargs,
        )


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        try:
            # Parse JSON message if it's already JSON
            if record.getMessage().startswith("{"):
                return record.getMessage()

            # Create structured log entry
            log_entry = {
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                "level": record.levelname,
                "message": record.getMessage(),
                "logger": record.name,
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
            }

            # Add exception info if present
            if record.exc_info:
                log_entry["exception"] = self.formatException(record.exc_info)

            # Add extra fields
            for key, value in record.__dict__.items():
                if key not in [
                    "name",
                    "msg",
                    "args",
                    "levelname",
                    "levelno",
                    "pathname",
                    "filename",
                    "module",
                    "exc_info",
                    "exc_text",
                    "stack_info",
                    "lineno",
                    "funcName",
                    "created",
                    "msecs",
                    "relativeCreated",
                    "thread",
                    "threadName",
                    "processName",
                    "process",
                    "getMessage",
                ]:
                    log_entry[key] = value

            return json.dumps(log_entry, default=str)

        except Exception as e:
            # Fallback to simple format
            return f"{record.levelname}: {record.getMessage()}"


class LogContextManager:
    """Context manager for logging context"""

    def __init__(
        self,
        logger: StructuredLogger,
        request_id: str = None,
        user_id: str = None,
        session_id: str = None,
        trace_id: str = None,
        span_id: str = None,
    ):
        self.logger = logger
        self.context = LogContext(
            request_id=request_id or str(uuid.uuid4()),
            user_id=user_id,
            session_id=session_id,
            trace_id=trace_id,
            span_id=span_id,
        )
        self.original_context = None

    def __enter__(self):
        self.original_context = self.logger.get_context()
        self.logger.set_context(self.context)
        return self.logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.original_context:
            self.logger.set_context(self.original_context)
        else:
            self.logger._local.context = None


# Global logger instance
_structured_logger: Optional[StructuredLogger] = None


def get_structured_logger(service_name: str = "netsentinel") -> StructuredLogger:
    """Get the global structured logger"""
    global _structured_logger
    if _structured_logger is None:
        _structured_logger = StructuredLogger(service_name=service_name)
    return _structured_logger


def create_log_context(
    request_id: str = None,
    user_id: str = None,
    session_id: str = None,
    trace_id: str = None,
    span_id: str = None,
) -> LogContextManager:
    """Create logging context manager"""
    logger = get_structured_logger()
    return LogContextManager(
        logger=logger,
        request_id=request_id,
        user_id=user_id,
        session_id=session_id,
        trace_id=trace_id,
        span_id=span_id,
    )


# Consolidated logging functionality from utils/logging.py
class NetSentinelLogger:
    """Enhanced logger for NetSentinel components (consolidated from utils/logging.py)"""

    def __init__(self, name: str, level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))

        # Prevent duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers()

    def _setup_handlers(self):
        """Setup log handlers"""
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        self.logger.addHandler(console_handler)

        # File handler (if log directory exists)
        log_dir = Path("logs")
        if log_dir.exists():
            file_handler = logging.handlers.RotatingFileHandler(
                log_dir / f"{self.logger.name}.log",
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
            )
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )
            self.logger.addHandler(file_handler)

    def info(self, message: str, **kwargs):
        """Log info message"""
        self.logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.logger.warning(message, extra=kwargs)

    def error(self, message: str, **kwargs):
        """Log error message"""
        self.logger.error(message, extra=kwargs)

    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self.logger.debug(message, extra=kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self.logger.critical(message, extra=kwargs)


def create_logger(name: str, level: str = "INFO") -> NetSentinelLogger:
    """Create a NetSentinel logger (consolidated from utils/logging.py)"""
    return NetSentinelLogger(name, level)
