"""
NetSentinel Core Infrastructure
Base classes, interfaces, and common utilities for the NetSentinel system
"""

from .base import BaseManager, BaseProcessor, BaseNotifier, BaseConfig
from .interfaces import (
    IEventProcessor,
    IAlertManager,
    IFirewallManager,
    IThreatIntelligence,
)
from .exceptions import (
    NetSentinelException,
    ConfigurationError,
    ConnectionError,
    ProcessingError,
)
from .container import ServiceContainer

__all__ = [
    "BaseManager",
    "BaseProcessor",
    "BaseNotifier",
    "BaseConfig",
    "IEventProcessor",
    "IAlertManager",
    "IFirewallManager",
    "IThreatIntelligence",
    "NetSentinelException",
    "ConfigurationError",
    "ConnectionError",
    "ProcessingError",
    "ServiceContainer",
]
