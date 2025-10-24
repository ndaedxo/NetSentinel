#!/usr/bin/env python3
"""
Custom exceptions for NetSentinel
Provides standardized error handling across the system
"""


class NetSentinelException(Exception):
    """Base exception for NetSentinel"""

    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class ConfigurationError(NetSentinelException):
    """Configuration-related errors"""

    def __init__(self, message: str, config_key: str = None, details: dict = None):
        super().__init__(message, "CONFIG_ERROR", details)
        self.config_key = config_key


class ConnectionError(NetSentinelException):
    """Connection-related errors"""

    def __init__(self, message: str, service: str = None, details: dict = None):
        super().__init__(message, "CONNECTION_ERROR", details)
        self.service = service


class ProcessingError(NetSentinelException):
    """Event processing errors"""

    def __init__(self, message: str, event_id: str = None, details: dict = None):
        super().__init__(message, "PROCESSING_ERROR", details)
        self.event_id = event_id


class ValidationError(NetSentinelException):
    """Data validation errors"""

    def __init__(
        self, message: str, field: str = None, value: str = None, details: dict = None
    ):
        super().__init__(message, "VALIDATION_ERROR", details)
        self.field = field
        self.value = value


# Removed unused exception classes - use standard Python exceptions instead
# AuthenticationError -> use PermissionError
# RateLimitError -> use ConnectionError with custom message
# TimeoutError -> use asyncio.TimeoutError
# ResourceError -> use ResourceWarning or custom NetSentinelException
