#!/usr/bin/env python3
"""
Service Container for Dependency Injection
Manages component lifecycle and dependencies
"""

import asyncio
import logging
from typing import Any, Dict, Type, TypeVar, Optional, Callable
from abc import ABC, abstractmethod

T = TypeVar("T")

logger = logging.getLogger(__name__)


class ServiceContainer:
    """
    Dependency injection container for NetSentinel
    Manages component registration, instantiation, and lifecycle
    """

    def __init__(self):
        self.services: Dict[str, Any] = {}
        self.factories: Dict[str, Callable] = {}
        self.singletons: Dict[str, Any] = {}
        self.running = False
        self.logger = logging.getLogger(f"{__name__}.ServiceContainer")

    def register_singleton(self, name: str, instance: Any) -> None:
        """Register a singleton instance"""
        self.singletons[name] = instance
        self.logger.debug(f"Registered singleton: {name}")

    def register_factory(self, name: str, factory: Callable) -> None:
        """Register a factory function"""
        self.factories[name] = factory
        self.logger.debug(f"Registered factory: {name}")

    def register_class(self, name: str, cls: Type[T], *args, **kwargs) -> None:
        """Register a class with constructor arguments"""

        def factory():
            return cls(*args, **kwargs)

        self.register_factory(name, factory)

    def get(self, name: str) -> Any:
        """Get a service by name"""
        # Check singletons first
        if name in self.singletons:
            return self.singletons[name]

        # Check factories
        if name in self.factories:
            instance = self.factories[name]()
            self.singletons[name] = instance  # Cache as singleton
            return instance

        raise ValueError(f"Service '{name}' not found")

    def get_typed(self, name: str, expected_type: Type[T]) -> T:
        """Get a service with type checking"""
        service = self.get(name)
        if not isinstance(service, expected_type):
            raise TypeError(f"Service '{name}' is not of type {expected_type.__name__}")
        return service

    def has(self, name: str) -> bool:
        """Check if service is registered"""
        return name in self.singletons or name in self.factories

    def remove(self, name: str) -> None:
        """Remove a service"""
        self.singletons.pop(name, None)
        self.factories.pop(name, None)
        self.logger.debug(f"Removed service: {name}")

    async def start_all(self) -> None:
        """Start all registered services"""
        if self.running:
            return

        self.logger.info("Starting all services...")

        for name, service in self.singletons.items():
            if hasattr(service, "start"):
                try:
                    if asyncio.iscoroutinefunction(service.start):
                        await service.start()
                    else:
                        service.start()
                    self.logger.debug(f"Started service: {name}")
                except Exception as e:
                    self.logger.error(f"Failed to start service {name}: {e}")

        self.running = True
        self.logger.info("All services started")

    async def stop_all(self) -> None:
        """Stop all registered services"""
        if not self.running:
            return

        self.logger.info("Stopping all services...")

        for name, service in self.singletons.items():
            if hasattr(service, "stop"):
                try:
                    if asyncio.iscoroutinefunction(service.stop):
                        await service.stop()
                    else:
                        service.stop()
                    self.logger.debug(f"Stopped service: {name}")
                except Exception as e:
                    self.logger.error(f"Failed to stop service {name}: {e}")

        self.running = False
        self.logger.info("All services stopped")

    def get_all_services(self) -> Dict[str, Any]:
        """Get all registered services"""
        return {**self.singletons, **{name: self.get(name) for name in self.factories}}

    def get_service_metrics(self) -> Dict[str, Any]:
        """Get metrics for all services"""
        metrics = {}
        for name, service in self.singletons.items():
            if hasattr(service, "get_metrics"):
                try:
                    metrics[name] = service.get_metrics()
                except Exception as e:
                    self.logger.error(f"Failed to get metrics for service {name}: {e}")
        return metrics


# Global service container instance
_container: Optional[ServiceContainer] = None


def get_container() -> ServiceContainer:
    """Get the global service container"""
    global _container
    if _container is None:
        _container = ServiceContainer()
    return _container


def register_service(name: str, service: Any) -> None:
    """Register a service in the global container"""
    get_container().register_singleton(name, service)


def get_service(name: str) -> Any:
    """Get a service from the global container"""
    return get_container().get(name)


def get_typed_service(name: str, expected_type: Type[T]) -> T:
    """Get a typed service from the global container"""
    return get_container().get_typed(name, expected_type)
