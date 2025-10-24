#!/usr/bin/env python3
"""
Retry Handler for NetSentinel
Implements comprehensive retry logic with exponential backoff
Designed for maintainability and preventing code debt
"""

import asyncio
import time
import random
import functools
from typing import Any, Callable, Optional, Type, Union, List
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """Retry strategy enumeration"""

    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    RANDOM = "random"


@dataclass
class RetryConfig:
    """Retry configuration"""

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    jitter: bool = True
    backoff_multiplier: float = 2.0
    retryable_exceptions: List[Type[Exception]] = None

    def __post_init__(self):
        if self.retryable_exceptions is None:
            self.retryable_exceptions = [Exception]


class RetryHandler:
    """Comprehensive retry handler with multiple strategies"""

    def __init__(self, config: RetryConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.RetryHandler")

    def retry(self, func: Callable) -> Callable:
        """Decorator for retry logic"""

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return self._execute_with_retry(func, *args, **kwargs)

        return wrapper

    async def async_retry(self, func: Callable) -> Callable:
        """Async decorator for retry logic"""

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await self._execute_async_retry(func, *args, **kwargs)

        return wrapper

    def _execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic"""
        last_exception = None

        for attempt in range(self.config.max_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                # Check if exception is retryable
                if not self._is_retryable_exception(e):
                    raise e

                # Check if we should retry
                if attempt == self.config.max_attempts - 1:
                    self.logger.error(
                        f"Max retry attempts reached for {func.__name__}: {e}"
                    )
                    raise e

                # Calculate delay
                delay = self._calculate_delay(attempt)
                self.logger.warning(
                    f"Retry {attempt + 1}/{self.config.max_attempts} for {func.__name__} after {delay:.2f}s: {e}"
                )

                time.sleep(delay)

        # This should never be reached, but just in case
        raise last_exception

    async def _execute_async_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function with retry logic"""
        last_exception = None

        for attempt in range(self.config.max_attempts):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                # Check if exception is retryable
                if not self._is_retryable_exception(e):
                    raise e

                # Check if we should retry
                if attempt == self.config.max_attempts - 1:
                    self.logger.error(
                        f"Max retry attempts reached for {func.__name__}: {e}"
                    )
                    raise e

                # Calculate delay
                delay = self._calculate_delay(attempt)
                self.logger.warning(
                    f"Retry {attempt + 1}/{self.config.max_attempts} for {func.__name__} after {delay:.2f}s: {e}"
                )

                await asyncio.sleep(delay)

        # This should never be reached, but just in case
        raise last_exception

    def _is_retryable_exception(self, exception: Exception) -> bool:
        """Check if exception is retryable"""
        return any(
            isinstance(exception, exc_type)
            for exc_type in self.config.retryable_exceptions
        )

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt"""
        if self.config.strategy == RetryStrategy.FIXED:
            delay = self.config.base_delay
        elif self.config.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.config.base_delay * (self.config.backoff_multiplier**attempt)
        elif self.config.strategy == RetryStrategy.LINEAR:
            delay = self.config.base_delay * (attempt + 1)
        elif self.config.strategy == RetryStrategy.RANDOM:
            delay = random.uniform(self.config.base_delay, self.config.base_delay * 2)
        else:
            delay = self.config.base_delay

        # Apply max delay limit
        delay = min(delay, self.config.max_delay)

        # Apply jitter if enabled
        if self.config.jitter:
            jitter = random.uniform(0.1, 0.3) * delay
            delay += jitter

        return delay


# Convenience functions
def retry_on_failure(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    retryable_exceptions: List[Type[Exception]] = None,
):
    """Decorator for retry logic with custom configuration"""
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        strategy=strategy,
        retryable_exceptions=retryable_exceptions or [Exception],
    )

    handler = RetryHandler(config)
    return handler.retry


def async_retry_on_failure(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    retryable_exceptions: List[Type[Exception]] = None,
):
    """Async decorator for retry logic with custom configuration"""
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        strategy=strategy,
        retryable_exceptions=retryable_exceptions or [Exception],
    )

    handler = RetryHandler(config)
    return handler.async_retry


# Global retry handler instances
_retry_handlers = {}


def get_retry_handler(
    name: str = "default", config: Optional[RetryConfig] = None
) -> RetryHandler:
    """Get or create retry handler"""
    if name not in _retry_handlers:
        _retry_handlers[name] = RetryHandler(config or RetryConfig())
    return _retry_handlers[name]


# Default retry decorators
retry = retry_on_failure()
async_retry = async_retry_on_failure()
