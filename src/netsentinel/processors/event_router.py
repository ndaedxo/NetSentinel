#!/usr/bin/env python3
"""
Event Router for NetSentinel
Routes events to appropriate handlers based on rules and routing logic
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Callable, Set
from dataclasses import dataclass, field
from enum import Enum

try:
    from ..core.base import BaseProcessor
    from ..core.models import StandardEvent, StandardAlert
    from .event_analyzer import AnalysisResult
    from ..core.error_handler import handle_errors, create_error_context
except ImportError:
    # Fallback for standalone usage
    from core.base import BaseProcessor
    from core.models import StandardEvent, StandardAlert
    from .event_analyzer import AnalysisResult
    from core.error_handler import handle_errors, create_error_context

logger = logging.getLogger(__name__)


@dataclass
class RouterConfig:
    """Configuration for EventRouter"""

    name: str = "event_router"
    cache_ttl: int = 300
    max_routes_per_event: int = 10
    enable_caching: bool = True


class RoutePriority(Enum):
    """Route priority levels"""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class RouteRule:
    """Event routing rule"""

    name: str
    condition: Callable[[StandardEvent], bool]
    handlers: List[str]
    priority: RoutePriority = RoutePriority.NORMAL
    enabled: bool = True
    description: str = ""


@dataclass
class RouteResult:
    """Result of event routing"""

    event: StandardEvent
    routes: List[str]
    handlers_called: List[str]
    routing_time: float
    success: bool
    errors: List[str] = field(default_factory=list)


class EventRouter(BaseProcessor):
    """Routes events to appropriate handlers"""

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        logger: Optional[logging.Logger] = None,
    ):
        super().__init__("event_router", config, logger)

        # Routing configuration
        self.routing_rules: List[RouteRule] = []
        self.handlers: Dict[str, Callable] = {}
        self.route_cache: Dict[str, List[str]] = {}
        self.cache_ttl = self.config.get("cache_ttl", 300)  # 5 minutes
        self.cache_timestamps: Dict[str, float] = {}

        # Initialize default routing rules
        self._initialize_default_rules()

    def _initialize_default_rules(self):
        """Initialize default routing rules"""
        # High-priority threat events
        self.add_rule(
            RouteRule(
                name="critical_threats",
                condition=lambda event: (
                    event.severity == "critical"
                    or event.event_type in ["4002", "9999"]  # SSH login, packet anomaly
                ),
                handlers=["alert_store", "firewall_manager", "siem_forwarder"],
                priority=RoutePriority.CRITICAL,
                description="Route critical threats to all security handlers",
            )
        )

        # Authentication events
        self.add_rule(
            RouteRule(
                name="auth_events",
                condition=lambda event: (
                    event.event_type in ["4002", "2000", "6001", "8001"]
                    and "logdata" in event.data
                    and isinstance(event.data["logdata"], dict)
                    and "USERNAME" in event.data["logdata"]
                ),
                handlers=["alert_store", "threat_intel_checker"],
                priority=RoutePriority.HIGH,
                description="Route authentication events for analysis",
            )
        )

        # HTTP events
        self.add_rule(
            RouteRule(
                name="http_events",
                condition=lambda event: event.event_type == "3000",
                handlers=["web_analyzer", "siem_forwarder"],
                priority=RoutePriority.NORMAL,
                description="Route HTTP events for web analysis",
            )
        )

        # All events (catch-all)
        self.add_rule(
            RouteRule(
                name="all_events",
                condition=lambda event: True,
                handlers=["event_logger", "metrics_collector"],
                priority=RoutePriority.LOW,
                description="Log and collect metrics for all events",
            )
        )

    async def _initialize(self):
        """Initialize router"""
        self.logger.info("Event router initialized")

    async def _start_internal(self):
        """Start router"""
        self.logger.info("Event router started")

    async def _stop_internal(self):
        """Stop router"""
        self.logger.info("Event router stopped")

    async def _process_item(self, item: Any):
        """Process a single routing item"""
        if isinstance(item, StandardEvent):
            await self._route_event(item)
        elif isinstance(item, AnalysisResult):
            await self._route_analysis_result(item)
        else:
            self.logger.warning(f"Unknown item type for routing: {type(item)}")

    async def _route_event(self, event: StandardEvent):
        """Route a standard event"""
        try:
            start_time = time.time()

            # Get routes for this event
            routes = await self._get_routes_for_event(event)

            # Execute routes
            handlers_called = []
            errors = []

            for route in routes:
                try:
                    await self._execute_route(event, route)
                    handlers_called.append(route)
                except Exception as e:
                    error_msg = f"Error executing route {route}: {e}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)

            # Create routing result
            result = RouteResult(
                event=event,
                routes=routes,
                handlers_called=handlers_called,
                routing_time=time.time() - start_time,
                success=len(errors) == 0,
                errors=errors,
            )

            # Update metrics
            self.metrics.operations_count += 1
            self.metrics.last_operation_time = time.time()

            if errors:
                self.metrics.errors_count += len(errors)

            self.logger.debug(
                f"Routed event {event.id} to {len(handlers_called)} handlers"
            )

        except Exception as e:
            context = create_error_context(
                "route_event", "event_router", additional_data={"event_id": event.id}
            )
            handle_errors(e, context)

    async def _route_analysis_result(self, result: AnalysisResult):
        """Route an analysis result"""
        try:
            # Route based on threat level
            if result.threat_level.value in ["high", "critical"]:
                await self._route_high_threat(result)
            else:
                await self._route_normal_threat(result)

        except Exception as e:
            self.logger.error(f"Error routing analysis result: {e}")

    async def _get_routes_for_event(self, event: StandardEvent) -> List[str]:
        """Get routes for an event using caching"""
        # Create cache key
        cache_key = f"{event.event_type}_{event.severity}_{event.source}"

        # Check cache
        if (
            cache_key in self.route_cache
            and cache_key in self.cache_timestamps
            and time.time() - self.cache_timestamps[cache_key] < self.cache_ttl
        ):
            return self.route_cache[cache_key]

        # Calculate routes
        routes = []
        for rule in self.routing_rules:
            if not rule.enabled:
                continue

            try:
                if rule.condition(event):
                    routes.extend(rule.handlers)
            except Exception as e:
                self.logger.error(f"Error in routing rule {rule.name}: {e}")

        # Remove duplicates while preserving order
        unique_routes = []
        seen = set()
        for route in routes:
            if route not in seen:
                unique_routes.append(route)
                seen.add(route)

        # Cache result
        self.route_cache[cache_key] = unique_routes
        self.cache_timestamps[cache_key] = time.time()

        return unique_routes

    async def _execute_route(self, event: StandardEvent, handler_name: str):
        """Execute a specific route"""
        if handler_name not in self.handlers:
            self.logger.warning(f"Handler {handler_name} not registered")
            return

        handler = self.handlers[handler_name]

        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)
        except Exception as e:
            self.logger.error(f"Error in handler {handler_name}: {e}")
            raise

    async def _route_high_threat(self, result: AnalysisResult):
        """Route high-threat analysis results"""
        # Route to all security handlers
        security_handlers = [
            "alert_store",
            "firewall_manager",
            "siem_forwarder",
            "threat_intel_checker",
        ]

        for handler_name in security_handlers:
            if handler_name in self.handlers:
                try:
                    handler = self.handlers[handler_name]
                    if asyncio.iscoroutinefunction(handler):
                        await handler(result)
                    else:
                        handler(result)
                except Exception as e:
                    self.logger.error(f"Error in security handler {handler_name}: {e}")

    async def _route_normal_threat(self, result: AnalysisResult):
        """Route normal-threat analysis results"""
        # Route to standard handlers
        standard_handlers = ["alert_store", "event_logger"]

        for handler_name in standard_handlers:
            if handler_name in self.handlers:
                try:
                    handler = self.handlers[handler_name]
                    if asyncio.iscoroutinefunction(handler):
                        await handler(result)
                    else:
                        handler(result)
                except Exception as e:
                    self.logger.error(f"Error in standard handler {handler_name}: {e}")

    def add_rule(self, rule: RouteRule):
        """Add a routing rule"""
        self.routing_rules.append(rule)
        # Sort by priority
        self.routing_rules.sort(key=lambda r: r.priority.value, reverse=True)
        self.logger.info(f"Added routing rule: {rule.name}")

    def remove_rule(self, rule_name: str) -> bool:
        """Remove a routing rule"""
        for i, rule in enumerate(self.routing_rules):
            if rule.name == rule_name:
                del self.routing_rules[i]
                self.logger.info(f"Removed routing rule: {rule_name}")
                return True
        return False

    def register_handler(self, name: str, handler: Callable):
        """Register an event handler"""
        self.handlers[name] = handler
        self.logger.info(f"Registered handler: {name}")

    def unregister_handler(self, name: str) -> bool:
        """Unregister an event handler"""
        if name in self.handlers:
            del self.handlers[name]
            self.logger.info(f"Unregistered handler: {name}")
            return True
        return False

    def get_handler_names(self) -> List[str]:
        """Get list of registered handler names"""
        return list(self.handlers.keys())

    def get_rule_names(self) -> List[str]:
        """Get list of routing rule names"""
        return [rule.name for rule in self.routing_rules]

    async def clear_cache(self):
        """Clear routing cache"""
        self.route_cache.clear()
        self.cache_timestamps.clear()
        self.logger.info("Routing cache cleared")

    async def get_routing_metrics(self) -> Dict[str, Any]:
        """Get router-specific metrics"""
        base_metrics = self.get_metrics()

        router_metrics = {
            **base_metrics,
            "routing_rules_count": len(self.routing_rules),
            "registered_handlers_count": len(self.handlers),
            "cache_size": len(self.route_cache),
            "cache_hit_ratio": self._calculate_cache_hit_ratio(),
            "enabled_rules": len([r for r in self.routing_rules if r.enabled]),
        }

        return router_metrics

    def _calculate_cache_hit_ratio(self) -> float:
        """Calculate cache hit ratio"""
        if not self.cache_timestamps:
            return 0.0

        # Simple calculation - in production, you'd track hits/misses
        return 0.8  # Placeholder
