#!/usr/bin/env python3
"""
Centralized Error Handler for NetSentinel
Provides standardized error handling across all components
"""

import asyncio
import logging
import time
import functools
import random
from typing import Any, Dict, List, Optional, Type, Callable, Union
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RetryStrategy(Enum):
    """Retry strategies"""

    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"


@dataclass
class RetryConfig:
    """Retry configuration"""

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    backoff_multiplier: float = 2.0
    jitter: bool = True
    exceptions: tuple = (Exception,)


@dataclass
class ErrorContext:
    """Error context information"""

    component: str
    operation: str
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    additional_data: Dict[str, Any] = None

    def __post_init__(self):
        if self.additional_data is None:
            self.additional_data = {}


@dataclass
class ErrorMetrics:
    """Error metrics tracking"""

    total_errors: int = 0
    errors_by_type: Dict[str, int] = None
    errors_by_severity: Dict[str, int] = None
    errors_by_component: Dict[str, int] = None
    last_error_time: Optional[float] = None

    def __post_init__(self):
        if self.errors_by_type is None:
            self.errors_by_type = {}
        if self.errors_by_severity is None:
            self.errors_by_severity = {}
        if self.errors_by_component is None:
            self.errors_by_component = {}


class NetSentinelErrorHandler:
    """
    Centralized error handler for NetSentinel
    Provides standardized error processing, logging, and recovery
    """

    def __init__(self):
        self.error_handlers: Dict[Type[Exception], Callable] = {}
        self.recovery_strategies: Dict[Type[Exception], Callable] = {}
        self.metrics = ErrorMetrics()
        self.logger = logging.getLogger(f"{__name__}.NetSentinelErrorHandler")

        # Setup default handlers
        self._setup_default_handlers()

    def _setup_default_handlers(self) -> None:
        """Setup default error handlers"""
        # Import here to avoid circular imports
        try:
            from .exceptions import ConnectionError

            # Connection errors
            self.register_handler(ConnectionError, self._handle_connection_error)
        except ImportError:
            # Fallback if exceptions module is not available
            pass

        # Generic exceptions - register last to catch all unhandled exceptions
        self.register_handler(Exception, self._handle_generic_error)

    def register_handler(
        self, exception_type: Type[Exception], handler: Callable
    ) -> None:
        """Register error handler for specific exception type"""
        self.error_handlers[exception_type] = handler
        self.logger.debug(f"Registered handler for {exception_type.__name__}")

    def register_recovery_strategy(
        self, exception_type: Type[Exception], strategy: Callable
    ) -> None:
        """Register recovery strategy for specific exception type"""
        self.recovery_strategies[exception_type] = strategy
        self.logger.debug(f"Registered recovery strategy for {exception_type.__name__}")

    async def handle_error(
        self, error: Exception, context: ErrorContext
    ) -> Dict[str, Any]:
        """Handle an error with context"""
        try:
            # Update metrics
            self._update_metrics(error, context)

            # Find appropriate handler
            handler = self._find_handler(error)
            if not handler:
                self.logger.error(f"No handler found for {type(error).__name__}")
                return {"status": "no_handler", "error": str(error)}

            # Execute handler
            if asyncio.iscoroutinefunction(handler):
                result = await handler(error, context)
            else:
                result = handler(error, context)

            # Try recovery if available
            recovery_result = await self._attempt_recovery(error, context)
            if recovery_result:
                result["recovery"] = recovery_result

            return result

        except Exception as e:
            self.logger.error(f"Error in error handler: {e}")
            return {"status": "handler_error", "error": str(e)}

    def _find_handler(self, error: Exception) -> Optional[Callable]:
        """Find appropriate handler for error"""
        # Try exact type match first
        if type(error) in self.error_handlers:
            return self.error_handlers[type(error)]

        # Try parent class matches
        for exception_type, handler in self.error_handlers.items():
            if isinstance(error, exception_type):
                return handler

        return None

    async def _attempt_recovery(
        self, error: Exception, context: ErrorContext
    ) -> Optional[Dict[str, Any]]:
        """Attempt error recovery"""
        try:
            # Find recovery strategy
            strategy = None
            for exception_type, recovery_strategy in self.recovery_strategies.items():
                if isinstance(error, exception_type):
                    strategy = recovery_strategy
                    break

            if not strategy:
                return None

            # Execute recovery strategy
            if asyncio.iscoroutinefunction(strategy):
                result = await strategy(error, context)
            else:
                result = strategy(error, context)

            return result

        except Exception as e:
            self.logger.error(f"Error in recovery strategy: {e}")
            return None

    def _update_metrics(self, error: Exception, context: ErrorContext) -> None:
        """Update error metrics"""
        self.metrics.total_errors += 1
        self.metrics.last_error_time = time.time()

        # Update by type
        error_type = type(error).__name__
        self.metrics.errors_by_type[error_type] = (
            self.metrics.errors_by_type.get(error_type, 0) + 1
        )

        # Update by component
        self.metrics.errors_by_component[context.component] = (
            self.metrics.errors_by_component.get(context.component, 0) + 1
        )

        # Update by severity
        severity = self._determine_error_severity(error)
        self.metrics.errors_by_severity[severity.value] = (
            self.metrics.errors_by_severity.get(severity.value, 0) + 1
        )

    def _determine_error_severity(self, error: Exception) -> ErrorSeverity:
        """Determine error severity"""
        # Import here to avoid circular imports
        try:
            from .exceptions import ConnectionError

            if isinstance(error, ConnectionError):
                return ErrorSeverity.MEDIUM
        except ImportError:
            pass

        if isinstance(error, (ValueError, TypeError)):
            return ErrorSeverity.LOW
        elif isinstance(error, (OSError, IOError)):
            return ErrorSeverity.HIGH
        else:
            return ErrorSeverity.MEDIUM

    async def _handle_connection_error(
        self, error: Exception, context: ErrorContext
    ) -> Dict[str, Any]:
        """Handle connection errors"""
        self.logger.error(f"Connection error in {context.component}: {error}")

        return {
            "status": "connection_error",
            "component": context.component,
            "message": str(error),
            "severity": "medium",
        }

    async def _handle_generic_error(
        self, error: Exception, context: ErrorContext
    ) -> Dict[str, Any]:
        """Handle generic errors"""
        self.logger.error(f"Generic error in {context.component}: {str(error)}")

        return {
            "status": "generic_error",
            "component": context.component,
            "error_type": type(error).__name__,
            "message": str(error),
            "severity": "low",
        }

    def get_error_metrics(self) -> Dict[str, Any]:
        """Get error metrics"""
        return {
            "total_errors": self.metrics.total_errors,
            "errors_by_type": self.metrics.errors_by_type,
            "errors_by_severity": self.metrics.errors_by_severity,
            "errors_by_component": self.metrics.errors_by_component,
            "last_error_time": self.metrics.last_error_time,
        }

    def retry_with_backoff(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        exceptions: tuple = (Exception,),
    ):
        """Decorator for retry with exponential backoff"""

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
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
                            # Use random jitter instead of hash-based jitter for better distribution
                            delay *= 0.5 + 0.5 * random.random()

                        await asyncio.sleep(delay)
                raise last_exception

            @functools.wraps(func)
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
                            # Use random jitter instead of hash-based jitter for better distribution
                            delay *= 0.5 + 0.5 * random.random()

                        time.sleep(delay)
                raise last_exception

            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

        return decorator

    def reset_metrics(self) -> None:
        """Reset error metrics"""
        self.metrics = ErrorMetrics()
        self.logger.info("Error metrics reset")


# Global error handler instance
_error_handler: Optional[NetSentinelErrorHandler] = None


def get_error_handler() -> NetSentinelErrorHandler:
    """Get the global error handler"""
    global _error_handler
    if _error_handler is None:
        _error_handler = NetSentinelErrorHandler()
    return _error_handler


# Convenience functions for backward compatibility
def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: tuple = (Exception,),
):
    """Convenience function for retry with backoff"""
    return get_error_handler().retry_with_backoff(
        max_attempts, base_delay, max_delay, exponential_base, jitter, exceptions
    )


def handle_errors(
    error: Exception,
    context: Union[str, ErrorContext] = "",
    log_level: str = "ERROR",
    return_value: Any = None,
) -> Any:
    """Convenience function for error handling"""
    try:
        # Handle both string and ErrorContext types
        if isinstance(context, ErrorContext):
            context_str = f"{context.component}:{context.operation}"
        else:
            context_str = str(context)

        # Log the error with context
        if log_level.upper() == "ERROR":
            logger.error(f"Error in {context_str}: {str(error)}", exc_info=True)
        elif log_level.upper() == "WARNING":
            logger.warning(f"Warning in {context_str}: {str(error)}")
        else:
            logger.info(f"Info in {context_str}: {str(error)}")
        return return_value
    except Exception as e:
        logger.error(f"Error in error handler: {e}")
        return return_value


def create_error_context(
    operation: str,
    module: str = "",
    user_id: str = "",
    request_id: str = "",
    additional_data: Dict[str, Any] = None,
) -> ErrorContext:
    """Convenience function for creating error context"""
    return ErrorContext(
        component=module,
        operation=operation,
        user_id=user_id,
        request_id=request_id,
        additional_data=additional_data or {},
    )
