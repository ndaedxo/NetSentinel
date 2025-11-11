#!/usr/bin/env python3
"""
Refactored Event Processor for NetSentinel
Clean, maintainable implementation using the new architecture
"""

import asyncio
import logging
import os
import time
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from contextlib import asynccontextmanager

from ..core.base import BaseComponent, managed_component, get_resource_manager
from ..core.models import (
    StandardEvent,
    StandardAlert,
    ThreatLevel,
    create_event,
    create_alert,
)
from ..core.error_handler import handle_errors, create_error_context
from ..core.event_bus import get_event_bus, create_event as create_bus_event
from ..monitoring.metrics import get_metrics_collector
from .event_consumer import EventConsumer, ConsumerConfig
from .event_analyzer import EventAnalyzer, AnalysisResult
from .event_router import EventRouter
from .api_server import APIServer, create_api_server
from .threat_storage import ThreatStorage, create_threat_storage
from ..firewall_manager import FirewallManager
from ..alerts import get_alert_manager

logger = logging.getLogger(__name__)


@dataclass
class ProcessorConfig:
    """Event processor configuration"""

    kafka_servers: List[str]
    kafka_topic: str = "netsentinel-events"
    consumer_group: str = "netsentinel-processor"
    max_workers: int = 3
    queue_size: int = 1000
    ml_enabled: bool = True
    alerting_enabled: bool = True
    siem_enabled: bool = True
    firewall_enabled: bool = True
    api_enabled: bool = True
    api_host: str = "0.0.0.0"
    api_port: int = 8082
    threat_storage_enabled: bool = True
    threat_ttl: int = 3600
    correlation_ttl: int = 1800
    firewall_manager_enabled: bool = True
    websocket_enabled: bool = True
    alert_manager_enabled: bool = True


class RefactoredEventProcessor(BaseComponent):
    """
    Refactored event processor using clean architecture
    Composed of focused components: consumer, analyzer, router
    """

    def __init__(
        self, config: ProcessorConfig, logger: Optional[logging.Logger] = None
    ):
        super().__init__("refactored_event_processor", config.__dict__, logger)

        self.config = config
        self.resource_manager = get_resource_manager()

        # Component instances
        self.consumer: Optional[EventConsumer] = None
        self.analyzer: Optional[EventAnalyzer] = None
        self.router: Optional[EventRouter] = None
        self.api_server: Optional[APIServer] = None
        self.threat_storage: Optional[ThreatStorage] = None
        self.firewall_manager: Optional[FirewallManager] = None
        self.alert_manager = None
        self.websocket_manager = None  # Will be initialized if websocket_enabled

        # Processing metrics
        self.events_processed = 0
        self.events_failed = 0
        self.start_time = time.time()

        # Initialize metrics collector
        self.metrics_collector = get_metrics_collector("event_processor")

    async def _initialize(self):
        """Initialize all processor components"""
        try:
            # Initialize consumer
            consumer_config = ConsumerConfig(
                kafka_servers=self.config.kafka_servers,
                topic=self.config.kafka_topic,
                group_id=self.config.consumer_group,
            )
            self.consumer = EventConsumer(consumer_config, self.logger)

            # Initialize alert manager if enabled (before analyzer)
            if self.config.alert_manager_enabled:
                self.alert_manager = get_alert_manager()

            # Initialize analyzer
            analyzer_config = {
                "ml_enabled": self.config.ml_enabled,
                "max_workers": self.config.max_workers,
            }
            self.analyzer = EventAnalyzer(analyzer_config, self.logger, self.alert_manager)

            # Initialize router
            router_config = {
                "max_workers": self.config.max_workers,
                "queue_size": self.config.queue_size,
            }
            self.router = EventRouter(router_config, self.logger)

            # Initialize API server if enabled
            if self.config.api_enabled:
                self.api_server = create_api_server(
                    processor=self, host=self.config.api_host, port=self.config.api_port
                )

            # Initialize threat storage if enabled
            if self.config.threat_storage_enabled:
                self.threat_storage = create_threat_storage(
                    redis_host=os.getenv("NETSENTINEL_REDIS_HOST", "redis"),
                    redis_port=int(os.getenv("NETSENTINEL_REDIS_PORT", "6379")),
                    redis_password=os.getenv("NETSENTINEL_REDIS_PASSWORD", ""),
                    threat_ttl=self.config.threat_ttl,
                    correlation_ttl=self.config.correlation_ttl,
                )

            # Initialize WebSocket manager if enabled
            if self.config.websocket_enabled:
                from .websocket_manager import WebSocketManager
                self.websocket_manager = WebSocketManager()
                await self.websocket_manager.start()

            # Initialize firewall manager if enabled
            if self.config.firewall_manager_enabled:
                self.firewall_manager = FirewallManager()

            # Setup component dependencies
            self.analyzer.add_dependency(self.consumer)
            self.router.add_dependency(self.analyzer)
            if self.threat_storage:
                self.router.add_dependency(self.threat_storage)
            if self.api_server:
                self.api_server.add_dependency(self.router)
                if self.threat_storage:
                    self.api_server.add_dependency(self.threat_storage)

            # Register components with resource manager
            self.resource_manager.register_resource(
                "event_consumer",
                self.consumer,
                cleanup_handler=self.consumer.stop,
            )
            self.resource_manager.register_resource(
                "event_analyzer",
                self.analyzer,
                cleanup_handler=self.analyzer.stop,
            )
            self.resource_manager.register_resource(
                "event_router",
                self.router,
                cleanup_handler=self.router.stop,
            )
            if self.threat_storage:
                self.resource_manager.register_resource(
                    "threat_storage",
                    self.threat_storage,
                    cleanup_handler=self.threat_storage.stop,
                )
            if self.api_server:
                self.resource_manager.register_resource(
                    "api_server",
                    self.api_server,
                    cleanup_handler=self.api_server.stop,
                )

            # Setup event flow
            await self._setup_event_flow()

            self.logger.info("Refactored event processor initialized")

        except Exception as e:
            context = create_error_context(
                "initialize_processor", "refactored_event_processor"
            )
            handle_errors(e, context)
            raise

    async def _start_internal(self):
        """Start all processor components"""
        try:
            # Start components in dependency order
            if self.consumer:
                await self.consumer.start()
                self.logger.info("Event consumer started")

            if self.analyzer:
                await self.analyzer.start()
                self.logger.info("Event analyzer started")

            if self.threat_storage:
                await self.threat_storage.start()
                self.logger.info("Threat storage started")

            if self.alert_manager:
                await self.alert_manager.start()
                self.logger.info("Alert manager started")

            if self.router:
                await self.router.start()
                self.logger.info("Event router started")

            if self.api_server:
                await self.api_server.start()
                self.logger.info("API server started")

            # Start event bus processing
            event_bus = get_event_bus()
            event_bus.start()

            # Initialize resource manager
            await self.resource_manager.start()

            self.logger.info("Refactored event processor started successfully")

        except Exception as e:
            context = create_error_context(
                "start_processor", "refactored_event_processor"
            )
            handle_errors(e, context)
            raise

    async def _stop_internal(self):
        """Stop all processor components"""
        try:
            # Stop components in reverse order
            if self.api_server:
                await self.api_server.stop()
                self.logger.info("API server stopped")

            if self.router:
                await self.router.stop()
                self.logger.info("Event router stopped")

            if self.threat_storage:
                await self.threat_storage.stop()
                self.logger.info("Threat storage stopped")

            if self.alert_manager:
                await self.alert_manager.stop()
                self.logger.info("Alert manager stopped")

            if self.analyzer:
                await self.analyzer.stop()
                self.logger.info("Event analyzer stopped")

            if self.consumer:
                await self.consumer.stop()
                self.logger.info("Event consumer stopped")

            if self.websocket_manager:
                await self.websocket_manager.stop()
                self.logger.info("WebSocket manager stopped")

            # Stop resource manager
            await self.resource_manager.stop()

            self.logger.info("Refactored event processor stopped successfully")

        except Exception as e:
            context = create_error_context(
                "stop_processor", "refactored_event_processor"
            )
            handle_errors(e, context)

    async def _setup_event_flow(self):
        """Setup event flow between components"""
        if not all([self.consumer, self.analyzer, self.router]):
            return

        # Consumer -> Analyzer flow
        async def route_to_analyzer(event: StandardEvent):
            try:
                self.logger.info(f"Routing event {event.id} to analyzer (type: {event.event_type})")
                await self.analyzer.queue_item(event)
                self.events_processed += 1
                self.logger.info(f"Event {event.id} queued to analyzer successfully")

                # Track metrics
                self.metrics_collector.increment_counter(
                    "events_processed_total", labels={"event_type": event.event_type}
                )

            except Exception as e:
                self.events_failed += 1
                self.logger.error(f"Error routing to analyzer: {e}")

        self.consumer.add_event_handler(route_to_analyzer)

        # Analyzer -> Router flow
        async def route_analysis_result(result: AnalysisResult):
            try:
                self.logger.info(f"Routing analysis result for event {result.event.id} (score={result.threat_score}) to router")
                await self.router.queue_item(result)

                # Store threat data and perform correlation if threat storage is enabled
                if self.threat_storage and result.threat_score > 0:
                    await self.threat_storage.store_threat(
                        ip_address=result.event.source,
                        threat_score=result.threat_score,
                        threat_level=result.threat_level,
                        event=result.event,
                        indicators=result.indicators,
                    )

                    # Perform threat correlation analysis
                    await self._perform_threat_correlation(result)

                # Track threat analysis metrics
                self.metrics_collector.increment_counter(
                    "threats_analyzed_total",
                    labels={"threat_level": result.threat_level.value},
                )

                # Track threat score distribution
                self.metrics_collector.observe_histogram(
                    "threat_score_distribution",
                    result.threat_score,
                    labels={"threat_level": result.threat_level.value},
                )

                # Publish threat event to event bus for real-time broadcasting
                if result.threat_score > 5.0:
                    threat_data = {
                        "source_ip": result.event.source,
                        "threat_score": result.threat_score,
                        "threat_level": result.threat_level.value,
                        "event_type": result.event.event_type,
                        "timestamp": time.time(),
                        "indicators": result.indicators
                    }
                    threat_event = create_bus_event("threat.new", threat_data)
                    event_bus = get_event_bus()
                    await event_bus.publish(threat_event)

                # Track analysis time
                self.metrics_collector.observe_histogram(
                    "threat_analysis_duration_seconds", result.analysis_time
                )

            except Exception as e:
                self.logger.error(f"Error routing analysis result: {e}")

                # Track routing errors
                self.metrics_collector.increment_counter(
                    "analysis_routing_failed_total"
                )

        # Set analyzer result callback after function is defined
        self.analyzer.set_result_callback(route_analysis_result)

        # Register router handlers
        self.router.register_handler("alert_store", self._handle_alert)
        self.router.register_handler("firewall_manager", self._handle_firewall)
        self.router.register_handler("siem_forwarder", self._handle_siem)
        self.router.register_handler("event_logger", self._handle_logging)
        self.router.register_handler("metrics_collector", self._handle_metrics)

    async def _handle_alert(self, event_or_result):
        """Handle alert creation"""
        if not self.config.alerting_enabled:
            return

        try:
            if isinstance(event_or_result, AnalysisResult):
                result = event_or_result
                if result.threat_level.value in ["high", "critical"]:
                    alert = create_alert(
                        title=f"Threat Detected: {result.event.event_type}",
                        description=f"Threat score: {result.threat_score:.2f}",
                        severity=result.threat_level.value,
                        source="refactored_processor",
                        event_data=result.event.data,
                        tags=result.indicators,
                    )
                    self.logger.info(f"Created alert: {alert.id}")

                    # Track alert metrics
                    self.metrics_collector.increment_counter(
                        "alerts_created_total",
                        labels={"severity": result.threat_level.value},
                    )

                    # Publish alert event to event bus for real-time broadcasting
                    alert_data = {
                        "id": alert.id,
                        "severity": alert.severity,
                        "message": alert.title,
                        "description": alert.description,
                        "timestamp": alert.timestamp,
                        "source": alert.source,
                        "tags": alert.tags
                    }
                    alert_event = create_bus_event("alert.new", alert_data)
                    event_bus = get_event_bus()
                    await event_bus.publish(alert_event)

        except Exception as e:
            self.logger.error(f"Error handling alert: {e}")

    async def _handle_firewall(self, event_or_result):
        """Handle firewall actions"""
        if not self.config.firewall_enabled:
            return

        try:
            if isinstance(event_or_result, AnalysisResult):
                result = event_or_result
                if result.threat_level.value == "critical" and self.firewall_manager:
                    # Block IP for critical threats
                    ip_address = result.event.source
                    success = self.firewall_manager.block_ip(
                        ip_address,
                        reason=f"threat_score_{result.threat_score:.2f}_{result.event.event_type}",
                    )

                    if success:
                        self.logger.info(
                            f"Successfully blocked IP: {ip_address} "
                            f"(threat score: {result.threat_score:.2f})"
                        )

                        # Track successful firewall blocks
                        self.metrics_collector.increment_counter(
                            "firewall_blocks_successful_total",
                            labels={"threat_level": result.threat_level.value},
                        )
                    else:
                        self.logger.error(f"Failed to block IP: {ip_address}")

                        # Track failed firewall blocks
                        self.metrics_collector.increment_counter(
                            "firewall_blocks_failed_total",
                            labels={"threat_level": result.threat_level.value},
                        )
                elif (
                    result.threat_level.value == "critical"
                    and not self.firewall_manager
                ):
                    self.logger.warning(
                        "Firewall manager not available for IP blocking"
                    )

        except Exception as e:
            self.logger.error(f"Error handling firewall: {e}")

            # Track firewall errors
            self.metrics_collector.increment_counter("firewall_errors_total")

    async def _perform_threat_correlation(self, result: AnalysisResult):
        """Perform threat correlation analysis for pattern detection"""
        try:
            if not self.threat_storage:
                return

            ip_address = result.event.source

            # Get recent events for this IP
            correlations = await self.threat_storage.get_correlations(ip_address)

            if not correlations:
                # If no existing correlations, create initial correlation record
                recent_events = [result.event]  # Current event
                correlation_score = result.threat_score
                pattern = self._detect_initial_pattern(result)
            else:
                # Analyze existing correlation patterns
                recent_events = [result.event]
                correlation_score, pattern = self._analyze_correlation_patterns(
                    correlations, result
                )

            # Store correlation data if pattern detected
            if (
                correlation_score > result.threat_score * 1.5
            ):  # Significant correlation boost
                await self.threat_storage.store_correlation(
                    ip_address=ip_address,
                    events=recent_events,
                    correlation_score=correlation_score,
                    pattern=pattern,
                )

                # Update threat score if correlation indicates higher risk
                if correlation_score > 8.0 and result.threat_level.value != "critical":
                    result.threat_level = ThreatLevel.CRITICAL
                    result.indicators.append(f"correlation_pattern:{pattern}")

                    self.logger.warning(
                        f"Correlation analysis elevated threat level for {ip_address}: {pattern}"
                    )

                    # Track correlation discoveries
                    self.metrics_collector.increment_counter(
                        "threat_correlations_detected_total",
                        labels={"pattern": pattern or "unknown"},
                    )

        except Exception as e:
            self.logger.error(
                f"Error in threat correlation for {result.event.source}: {e}"
            )

    def _detect_initial_pattern(self, result: AnalysisResult) -> str:
        """Detect initial threat patterns"""
        event_type = result.event.event_type
        threat_score = result.threat_score

        if threat_score >= 8.0:
            if "ssh" in event_type:
                return "brute_force_ssh"
            elif "mysql" in event_type:
                return "database_attack"
            elif "http" in event_type:
                return "web_exploit"
            else:
                return "high_risk_activity"

        return "single_event"

    def _analyze_correlation_patterns(
        self, correlations, result: AnalysisResult
    ) -> Tuple[float, str]:
        """Analyze existing correlations to detect patterns"""
        correlation_score = result.threat_score
        detected_pattern = "unknown"

        # Analyze event frequency and types
        recent_correlations = correlations[-5:]  # Last 5 correlation records
        all_events = []
        for corr in recent_correlations:
            all_events.extend(corr.events)

        if len(all_events) >= 3:
            # Check for brute force patterns
            ssh_events = [e for e in all_events if "ssh" in e.get("event_type", "")]
            if len(ssh_events) >= 3:
                correlation_score *= (
                    2.0  # Double threat score for repeated SSH attempts
                )
                detected_pattern = "persistent_brute_force"
            elif len(all_events) >= 5:
                correlation_score *= 1.8  # Increase for high frequency
                detected_pattern = "high_frequency_attack"

        # Check for attack progression (different service types)
        service_types = set()
        for event in all_events[-10:]:  # Last 10 events
            event_type = event.get("event_type", "")
            if "ssh" in event_type:
                service_types.add("ssh")
            elif "mysql" in event_type:
                service_types.add("database")
            elif "http" in event_type:
                service_types.add("web")

        if len(service_types) >= 2:
            correlation_score *= 1.5  # Increase for multi-service attacks
            detected_pattern = "multi_service_attack"

        return correlation_score, detected_pattern

    async def _handle_siem(self, event_or_result):
        """Handle SIEM forwarding"""
        if not self.config.siem_enabled:
            return

        try:
            if isinstance(event_or_result, AnalysisResult):
                result = event_or_result

                # Initialize SIEM manager if not already done
                if not hasattr(self, "siem_manager"):
                    try:
                        from ..siem_integration import SiemManager, SiemEvent

                        self.siem_manager = SiemManager()
                        self.siem_event_class = SiemEvent
                    except ImportError:
                        self.logger.warning("SIEM integration not available")
                        return

                # Convert to SIEM event and forward
                siem_event = self.siem_event_class(
                    event_id=result.event.id,
                    timestamp=result.event.timestamp,
                    source_ip=result.event.source,
                    event_type=result.event.event_type,
                    severity=result.event.severity,
                    message=f"Threat detected: {result.event.event_type}",
                    raw_data=result.event.data,
                )

                # Send to all configured SIEM systems
                if (
                    hasattr(self.siem_manager, "connectors")
                    and self.siem_manager.connectors
                ):
                    for connector_name in self.siem_manager.connectors:
                        success = self.siem_manager.connectors[
                            connector_name
                        ].send_event(siem_event)
                        if success:
                            self.logger.info(
                                f"Forwarded to SIEM ({connector_name}): {result.event.id}"
                            )
                        else:
                            self.logger.warning(
                                f"Failed to forward to SIEM ({connector_name}): {result.event.id}"
                            )
                else:
                    self.logger.warning("No SIEM connectors available")

        except Exception as e:
            self.logger.error(f"Error handling SIEM: {e}")

    async def _handle_logging(self, event_or_result):
        """Handle event logging"""
        try:
            if isinstance(event_or_result, AnalysisResult):
                result = event_or_result
                self.logger.info(
                    f"Processed event {result.event.id}: "
                    f"score={result.threat_score:.2f}, "
                    f"level={result.threat_level.value}"
                )
            elif isinstance(event_or_result, StandardEvent):
                event = event_or_result
                self.logger.info(f"Received event {event.id}: {event.event_type}")

        except Exception as e:
            self.logger.error(f"Error handling logging: {e}")

    async def _handle_metrics(self, event_or_result):
        """Handle metrics collection"""
        try:
            # Update processing metrics
            self.metrics.operations_count += 1
            self.metrics.last_operation_time = time.time()

        except Exception as e:
            self.logger.error(f"Error handling metrics: {e}")

    async def get_processor_metrics(self) -> Dict[str, Any]:
        """Get comprehensive processor metrics"""
        base_metrics = self.get_metrics()

        # Component-specific metrics
        consumer_metrics = {}
        analyzer_metrics = {}
        router_metrics = {}

        if self.consumer:
            consumer_metrics = await self.consumer.get_consumer_metrics()

        if self.analyzer:
            analyzer_metrics = await self.analyzer.get_analysis_metrics()

        if self.router:
            router_metrics = await self.router.get_routing_metrics()

        # Resource manager metrics
        resource_metrics = self.resource_manager.get_resource_metrics()

        return {
            **base_metrics,
            "events_processed": self.events_processed,
            "events_failed": self.events_failed,
            "uptime": time.time() - self.start_time,
            "consumer_metrics": consumer_metrics,
            "analyzer_metrics": analyzer_metrics,
            "router_metrics": router_metrics,
            "resource_metrics": resource_metrics,
            "config": {
                "ml_enabled": self.config.ml_enabled,
                "alerting_enabled": self.config.alerting_enabled,
                "siem_enabled": self.config.siem_enabled,
                "firewall_enabled": self.config.firewall_enabled,
            },
        }

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        health = {"status": "healthy", "timestamp": time.time(), "components": {}}

        # Check component health
        components = {
            "consumer": self.consumer,
            "analyzer": self.analyzer,
            "router": self.router,
        }

        unhealthy_components = []

        for name, component in components.items():
            if component:
                is_healthy = component.is_healthy()
                health["components"][name] = {
                    "healthy": is_healthy,
                    "state": (
                        component.state.value
                        if hasattr(component, "state")
                        else "unknown"
                    ),
                }
                if not is_healthy:
                    unhealthy_components.append(name)
            else:
                health["components"][name] = {
                    "healthy": False,
                    "state": "not_initialized",
                }
                unhealthy_components.append(name)

        # Overall health status
        if unhealthy_components:
            health["status"] = "degraded"
            health["unhealthy_components"] = unhealthy_components

        return health

    async def _process_single_event(self, event) -> Dict[str, Any]:
        """Process a single event (for testing purposes)"""
        try:
            # Handle both StandardEvent objects and dictionaries
            if isinstance(event, dict):
                event_id = event.get("id", "unknown")
                # Convert dict to StandardEvent if needed
                from ..core.models import create_event

                event = create_event(
                    event_type=event.get("logtype", "unknown"),
                    source=event.get("src_host", "unknown"),
                    data=event.get("logdata", {}),
                    timestamp=event.get("timestamp", time.time()),
                )
            else:
                event_id = getattr(event, "id", "unknown")

            # Queue the event for processing
            if self.analyzer:
                await self.analyzer.queue_item(event)
                self.events_processed += 1
                return {"status": "processed", "event_id": event_id}
            else:
                return {"status": "no_analyzer", "event_id": event_id}
        except Exception as e:
            self.events_failed += 1
            self.logger.error(f"Error processing event {event_id}: {e}")
            return {"status": "error", "event_id": event_id, "error": str(e)}

    async def cleanup(self):
        """Cleanup processor resources"""
        try:
            await self.stop()
            self.logger.info("Processor cleanup completed")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")


# Factory function for creating processor
def create_refactored_processor(
    config: ProcessorConfig, logger: Optional[logging.Logger] = None
) -> RefactoredEventProcessor:
    """Create a refactored event processor"""
    return RefactoredEventProcessor(config, logger)


# Context manager for processor lifecycle
@asynccontextmanager
async def managed_processor(processor: RefactoredEventProcessor):
    """Context manager for processor lifecycle"""
    try:
        await processor.start()
        yield processor
    finally:
        await processor.stop()
