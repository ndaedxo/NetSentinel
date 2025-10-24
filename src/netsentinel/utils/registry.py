#!/usr/bin/env python3
"""
NetSentinel Centralized Utility Registry
Provides a unified interface for all utility functions and classes
"""

import asyncio
import inspect
import threading
from typing import Any, Callable, Dict, List, Optional, Type, Union
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class UtilityCategory(Enum):
    """Categories for utility functions"""

    CONNECTION = "connection"
    ERROR_HANDLING = "error_handling"
    CONFIGURATION = "configuration"
    LOGGING = "logging"
    VALIDATION = "validation"
    DATA_PROCESSING = "data_processing"
    SECURITY = "security"
    PERFORMANCE = "performance"
    INTEGRATION = "integration"
    CACHING = "caching"
    SERIALIZATION = "serialization"
    ASYNC = "async"
    TESTING = "testing"


@dataclass
class UtilityMetadata:
    """Metadata for registered utilities"""

    name: str
    category: UtilityCategory
    function: Callable
    description: str
    version: str = "1.0.0"
    dependencies: List[str] = field(default_factory=list)
    is_async: bool = False
    is_deprecated: bool = False
    replacement: Optional[str] = None


class UtilityRegistry:
    """
    Centralized registry for all NetSentinel utilities
    Provides auto-discovery, dependency management, and unified access
    """

    def __init__(self):
        self._utilities: Dict[str, UtilityMetadata] = {}
        self._categories: Dict[UtilityCategory, List[str]] = {
            cat: [] for cat in UtilityCategory
        }
        self._dependencies: Dict[str, List[str]] = {}
        self._lock = threading.RLock()
        self._initialized = False

    def register(
        self,
        name: str,
        category: UtilityCategory,
        description: str = "",
        version: str = "1.0.0",
        dependencies: List[str] = None,
        is_deprecated: bool = False,
        replacement: str = None,
    ):
        """Decorator to register utility functions"""

        def decorator(func: Callable) -> Callable:
            with self._lock:
                # Check if function is async
                is_async = inspect.iscoroutinefunction(func)

                # Create metadata
                metadata = UtilityMetadata(
                    name=name,
                    category=category,
                    function=func,
                    description=description,
                    version=version,
                    dependencies=dependencies or [],
                    is_async=is_async,
                    is_deprecated=is_deprecated,
                    replacement=replacement,
                )

                # Register utility
                self._utilities[name] = metadata
                self._categories[category].append(name)

                # Track dependencies
                if dependencies:
                    self._dependencies[name] = dependencies

                logger.debug(f"Registered utility: {name} in category {category.value}")
                return func

        return decorator

    def get_utility(self, name: str) -> Optional[Callable]:
        """Get a utility function by name"""
        with self._lock:
            if name in self._utilities:
                metadata = self._utilities[name]
                if metadata.is_deprecated and metadata.replacement:
                    logger.warning(
                        f"Utility '{name}' is deprecated. Use '{metadata.replacement}' instead."
                    )
                return metadata.function
            return None

    def get_utilities_by_category(self, category: UtilityCategory) -> List[str]:
        """Get all utilities in a category"""
        with self._lock:
            return self._categories[category].copy()

    def get_all_utilities(self) -> Dict[str, UtilityMetadata]:
        """Get all registered utilities"""
        with self._lock:
            return self._utilities.copy()

    def get_dependencies(self, name: str) -> List[str]:
        """Get dependencies for a utility"""
        with self._lock:
            return self._dependencies.get(name, [])

    def validate_dependencies(self) -> List[str]:
        """Validate that all dependencies are satisfied"""
        missing = []
        with self._lock:
            for name, deps in self._dependencies.items():
                for dep in deps:
                    if dep not in self._utilities:
                        missing.append(f"{name} -> {dep}")
        return missing

    def get_utility_info(self, name: str) -> Optional[UtilityMetadata]:
        """Get metadata for a utility"""
        with self._lock:
            return self._utilities.get(name)

    def list_deprecated(self) -> List[str]:
        """List all deprecated utilities"""
        with self._lock:
            return [
                name for name, meta in self._utilities.items() if meta.is_deprecated
            ]

    def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics"""
        with self._lock:
            stats = {
                "total_utilities": len(self._utilities),
                "categories": {
                    cat.value: len(utilities)
                    for cat, utilities in self._categories.items()
                },
                "deprecated": len(self.list_deprecated()),
                "async_utilities": len(
                    [name for name, meta in self._utilities.items() if meta.is_async]
                ),
                "dependencies": len(self._dependencies),
            }
            return stats


# Global registry instance
_registry = UtilityRegistry()


def get_registry() -> UtilityRegistry:
    """Get the global utility registry"""
    return _registry


def register_utility(
    name: str,
    category: UtilityCategory,
    description: str = "",
    version: str = "1.0.0",
    dependencies: List[str] = None,
    is_deprecated: bool = False,
    replacement: str = None,
):
    """Register a utility function"""
    return _registry.register(
        name, category, description, version, dependencies, is_deprecated, replacement
    )


def get_utility(name: str) -> Optional[Callable]:
    """Get a utility function"""
    return _registry.get_utility(name)


def get_utilities_by_category(category: UtilityCategory) -> List[str]:
    """Get utilities by category"""
    return _registry.get_utilities_by_category(category)


def get_all_utilities() -> Dict[str, UtilityMetadata]:
    """Get all utilities"""
    return _registry.get_all_utilities()


def get_utility_info(name: str) -> Optional[UtilityMetadata]:
    """Get utility information"""
    return _registry.get_utility_info(name)


def get_registry_statistics() -> Dict[str, Any]:
    """Get registry statistics"""
    return _registry.get_statistics()


# Convenience functions for common operations
def list_connection_utilities() -> List[str]:
    """List all connection utilities"""
    return get_utilities_by_category(UtilityCategory.CONNECTION)


def list_error_handling_utilities() -> List[str]:
    """List all error handling utilities"""
    return get_utilities_by_category(UtilityCategory.ERROR_HANDLING)


def list_configuration_utilities() -> List[str]:
    """List all configuration utilities"""
    return get_utilities_by_category(UtilityCategory.CONFIGURATION)


def list_logging_utilities() -> List[str]:
    """List all logging utilities"""
    return get_utilities_by_category(UtilityCategory.LOGGING)


def list_validation_utilities() -> List[str]:
    """List all validation utilities"""
    return get_utilities_by_category(UtilityCategory.VALIDATION)


def list_data_processing_utilities() -> List[str]:
    """List all data processing utilities"""
    return get_utilities_by_category(UtilityCategory.DATA_PROCESSING)


def list_security_utilities() -> List[str]:
    """List all security utilities"""
    return get_utilities_by_category(UtilityCategory.SECURITY)


def list_performance_utilities() -> List[str]:
    """List all performance utilities"""
    return get_utilities_by_category(UtilityCategory.PERFORMANCE)


def list_integration_utilities() -> List[str]:
    """List all integration utilities"""
    return get_utilities_by_category(UtilityCategory.INTEGRATION)


def list_caching_utilities() -> List[str]:
    """List all caching utilities"""
    return get_utilities_by_category(UtilityCategory.CACHING)


def list_async_utilities() -> List[str]:
    """List all async utilities"""
    return get_utilities_by_category(UtilityCategory.ASYNC)


def list_testing_utilities() -> List[str]:
    """List all testing utilities"""
    return get_utilities_by_category(UtilityCategory.TESTING)
