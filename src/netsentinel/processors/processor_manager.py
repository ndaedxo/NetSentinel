#!/usr/bin/env python3
"""
Processor Manager for NetSentinel
Manages the complete event processing pipeline
"""

import asyncio
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

try:
    from ..core.base import BaseManager, BaseConfig
    from ..core.interfaces import Event, Alert
    from ..processors.event_consumer import EventConsumer, ConsumerConfig
    from ..processors.event_analyzer import EventAnalyzer, AnalyzerConfig
    from ..processors.event_router import EventRouter, RouterConfig

    # Import centralized utilities
    from ..utils.centralized import (
        create_logger,
        generate_id,
        hash_data,
        serialize_data,
        deserialize_data,
        retry_with_backoff,
        handle_errors_simple as handle_errors,
        create_error_context_simple as create_error_context,
        load_config,
        validate_config,
        create_connection_pool,
        measure_time,
        create_timer,
        create_cache,
    )
except ImportError:
    # Fallback for standalone usage
    from core.base import BaseManager, BaseConfig
    from core.interfaces import Event, Alert
    from .event_consumer import EventConsumer, ConsumerConfig
    from .event_analyzer import EventAnalyzer, AnalyzerConfig
    from .event_router import EventRouter, RouterConfig

    # Import centralized utilities
    from utils.centralized import (
        create_logger,
        generate_id,
        hash_data,
        serialize_data,
        deserialize_data,
        retry_with_backoff,
        handle_errors_simple as handle_errors,
        create_error_context_simple as create_error_context,
        load_config,
        validate_config,
        create_connection_pool,
        measure_time,
        create_timer,
        create_cache,
    )

logger = create_logger("processor_manager", level="INFO")


@dataclass
class ProcessorManagerConfig(BaseConfig):
    """Processor manager configuration"""

    consumer_enabled: bool = True
    analyzer_enabled: bool = True
    router_enabled: bool = True
    pipeline_timeout: float = 30.0
    max_concurrent_events: int = 100


class ProcessorManager(BaseManager):
    """
    Manages the complete event processing pipeline
    Coordinates consumer, analyzer, and router components
    """

    def __init__(self, config: ProcessorManagerConfig):
        super().__init__(config)
        self.config = config

        # Initialize components
        self.consumer = None
        self.analyzer = None
        self.router = None

        # Processing metrics
        self.events_processed = 0
        self.events_failed = 0
        self.processing_time = 0.0

        # Initialize components
        self._initialize_components()

    def _initialize_components(self) -> None:
        """Initialize processing components"""
        try:
            # Initialize consumer
            if self.config.consumer_enabled:
                consumer_config = ConsumerConfig(name="consumer")
                self.consumer = EventConsumer(consumer_config)
                self.consumer.add_message_handler(self._handle_event)

            # Initialize analyzer
            if self.config.analyzer_enabled:
                analyzer_config = AnalyzerConfig(name="analyzer")
                self.analyzer = EventAnalyzer(analyzer_config)

            # Initialize router
            if self.config.router_enabled:
                router_config = RouterConfig(name="router")
                self.router = EventRouter(router_config)
                self._setup_router_handlers()

            self.logger.info("Processor components initialized")

        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            raise

    def _setup_router_handlers(self) -> None:
        """Setup router handlers"""
        if not self.router:
            return

        # Add alert handler
        self.router.add_route_handler(
            self.router.RouteAction.ALERT, self._handle_alert_route
        )

        # Add block handler
        self.router.add_route_handler(
            self.router.RouteAction.BLOCK, self._handle_block_route
        )

        # Add log handler
        self.router.add_route_handler(
            self.router.RouteAction.LOG, self._handle_log_route
        )

    async def _start_internal(self) -> None:
        """Start all processing components"""
        try:
            # Start consumer
            if self.consumer:
                await self.consumer.start()
                self.logger.info("Event consumer started")

            # Start analyzer
            if self.analyzer:
                # Analyzer doesn't need explicit start
                self.logger.info("Event analyzer ready")

            # Start router
            if self.router:
                await self.router.start()
                self.logger.info("Event router started")

            self.logger.info("Processor manager started successfully")

        except Exception as e:
            self.logger.error(f"Failed to start processor manager: {e}")
            raise

    async def _stop_internal(self) -> None:
        """Stop all processing components"""
        try:
            # Stop consumer
            if self.consumer:
                await self.consumer.stop()
                self.logger.info("Event consumer stopped")

            # Stop router
            if self.router:
                await self.router.stop()
                self.logger.info("Event router stopped")

            self.logger.info("Processor manager stopped")

        except Exception as e:
            self.logger.error(f"Error stopping processor manager: {e}")

    async def _handle_event(self, event: Event) -> None:
        """Handle incoming event"""
        try:
            # Analyze event
            if self.analyzer:
                analysis_result = await self.analyzer.process(event)

                # Route event
                if self.router:
                    await self.router.route_event(analysis_result)

            self.events_processed += 1

        except Exception as e:
            self.events_failed += 1
            self.logger.error(f"Error processing event {event.id}: {e}")
            raise

    async def _handle_alert_route(self, rule, analysis_result) -> Dict[str, Any]:
        """Handle alert routing"""
        try:
            # Create alert from analysis result
            alert = Alert(
                id=f"alert_{analysis_result.event.id}",
                title=f"Security Alert: {analysis_result.event.event_type}",
                description=f"Threat detected with score {analysis_result.threat_score:.2f}",
                severity=analysis_result.threat_level.value,
                source=analysis_result.event.source,
                timestamp=analysis_result.event.timestamp,
                event_data=analysis_result.event.data,
                tags=analysis_result.event.tags,
            )

            # Send alert (placeholder - would integrate with alert manager)
            self.logger.info(f"Alert created: {alert.id}")

            return {"status": "success", "alert_id": alert.id}

        except Exception as e:
            self.logger.error(f"Error handling alert route: {e}")
            return {"status": "error", "error": str(e)}

    async def _handle_block_route(self, rule, analysis_result) -> Dict[str, Any]:
        """Handle block routing"""
        try:
            # Extract IP from event data
            ip = analysis_result.event.data.get("ip")
            if not ip:
                return {"status": "error", "error": "No IP found in event data"}

            # Block IP (placeholder - would integrate with firewall manager)
            self.logger.info(f"Blocking IP: {ip}")

            return {"status": "success", "blocked_ip": ip}

        except Exception as e:
            self.logger.error(f"Error handling block route: {e}")
            return {"status": "error", "error": str(e)}

    async def _handle_log_route(self, rule, analysis_result) -> Dict[str, Any]:
        """Handle log routing"""
        try:
            # Log event details
            self.logger.info(
                f"Event logged: {analysis_result.event.id} - {analysis_result.threat_level.value}"
            )

            return {"status": "success", "logged": True}

        except Exception as e:
            self.logger.error(f"Error handling log route: {e}")
            return {"status": "error", "error": str(e)}

    def get_processing_metrics(self) -> Dict[str, Any]:
        """Get processing metrics"""
        metrics = {
            "events_processed": self.events_processed,
            "events_failed": self.events_failed,
            "success_rate": (self.events_processed - self.events_failed)
            / max(self.events_processed, 1),
            "processing_time": self.processing_time,
        }

        # Add component metrics
        if self.consumer:
            metrics["consumer"] = self.consumer.get_consumer_metrics()

        if self.analyzer:
            metrics["analyzer"] = self.analyzer.get_analysis_metrics()

        if self.router:
            metrics["router"] = self.router.get_router_metrics()

        return metrics
