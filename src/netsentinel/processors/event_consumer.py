#!/usr/bin/env python3
"""
Event Consumer for NetSentinel
Handles Kafka message consumption and basic event processing
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass

try:
    from ..core.base import BaseProcessor
    from ..core.models import StandardEvent, create_event
    from ..core.error_handler import handle_errors, create_error_context
except ImportError:
    # Fallback for standalone usage
    from core.base import BaseProcessor
    from core.models import StandardEvent, create_event
    from core.error_handler import handle_errors, create_error_context

logger = logging.getLogger(__name__)


@dataclass
class ConsumerConfig:
    """Event consumer configuration"""

    kafka_servers: List[str]
    topic: str = "netsentinel-events"
    group_id: str = "netsentinel-consumer"
    max_poll_records: int = 100
    poll_timeout_ms: int = 1000
    auto_offset_reset: str = "latest"
    enable_auto_commit: bool = True
    session_timeout_ms: int = 30000
    heartbeat_interval_ms: int = 10000


class EventConsumer(BaseProcessor):
    """Consumes events from Kafka and queues them for processing"""

    def __init__(self, config: ConsumerConfig, logger: Optional[logging.Logger] = None):
        super().__init__("event_consumer", config.__dict__, logger)
        self.consumer_config = config
        self.kafka_consumer = None
        self._event_handlers: List[Callable[[StandardEvent], None]] = []
        self._running = False

    async def _initialize(self):
        """Initialize Kafka consumer"""
        try:
            import kafka

            self.kafka_consumer = kafka.KafkaConsumer(
                self.consumer_config.topic,
                bootstrap_servers=self.consumer_config.kafka_servers,
                group_id=self.consumer_config.group_id,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                max_poll_records=self.consumer_config.max_poll_records,
                auto_offset_reset=self.consumer_config.auto_offset_reset,
                enable_auto_commit=self.consumer_config.enable_auto_commit,
                session_timeout_ms=self.consumer_config.session_timeout_ms,
                heartbeat_interval_ms=self.consumer_config.heartbeat_interval_ms,
            )

            self.logger.info(
                f"Initialized Kafka consumer for topic: {self.consumer_config.topic}"
            )

        except ImportError:
            self.logger.error("Kafka library not available")
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize Kafka consumer: {e}")
            raise

    async def _start_internal(self):
        """Start consuming events"""
        if not self.kafka_consumer:
            raise RuntimeError("Kafka consumer not initialized")

        self._running = True
        self.logger.info("Started event consumption")

        # Start the consumer loop as an async task
        self._consumer_task = asyncio.create_task(self._consumer_loop())

    async def _stop_internal(self):
        """Stop consuming events"""
        self._running = False
        if hasattr(self, "_consumer_task"):
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass
        if self.kafka_consumer:
            self.kafka_consumer.close()
            self.logger.info("Stopped event consumption")

    async def _process_item(self, item: Any):
        """Process a single event item"""
        # This method is called by the base processor for queued items
        # The actual processing happens in the consumer loop
        pass

    def add_event_handler(self, handler: Callable[[StandardEvent], None]):
        """Add an event handler"""
        self._event_handlers.append(handler)
        self.logger.debug(f"Added event handler: {handler.__name__}")

    async def _consumer_loop(self):
        """Main consumer loop"""
        while self._running and self.state.value == "running":
            try:
                # Poll for messages
                message_batch = self.kafka_consumer.poll(
                    timeout_ms=self.consumer_config.poll_timeout_ms
                )

                if not message_batch:
                    await asyncio.sleep(0.1)
                    continue

                # Process messages
                for topic_partition, messages in message_batch.items():
                    for message in messages:
                        try:
                            await self._process_message(message.value)
                        except Exception as e:
                            context = create_error_context(
                                "process_message",
                                "event_consumer",
                                additional_data={"message": message.value},
                            )
                            handle_errors(e, context)
                            # Continue processing other messages even if one fails
                            continue

            except Exception as e:
                self.logger.error(f"Error in consumer loop: {e}")
                await self._handle_error(e)
                await asyncio.sleep(1)

    async def _process_message(self, message_data: Dict[str, Any]):
        """Process a single Kafka message"""
        try:
            # Convert to standard event
            event = self._convert_to_standard_event(message_data)

            # Validate event
            validation_result = event.validate()
            if not validation_result.valid:
                self.logger.warning(
                    f"Invalid event received: {validation_result.errors}"
                )
                return

            # Queue for processing
            await self.queue_item(event)

            # Call event handlers
            for handler in self._event_handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    self.logger.error(f"Error in event handler {handler.__name__}: {e}")

            self.metrics.operations_count += 1
            self.metrics.last_operation_time = time.time()

        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            raise

    def _convert_to_standard_event(self, message_data: Dict[str, Any]) -> StandardEvent:
        """Convert Kafka message to standard event"""
        # Extract basic information
        event_type = str(message_data.get("logtype", "unknown"))
        source = message_data.get("src_host", "unknown")
        timestamp = message_data.get("timestamp", time.time())

        # Create event data
        event_data = {
            "logtype": message_data.get("logtype"),
            "src_host": message_data.get("src_host"),
            "dst_host": message_data.get("dst_host"),
            "dst_port": message_data.get("dst_port"),
            "logdata": message_data.get("logdata", {}),
            "raw_message": message_data,
        }

        # Determine severity based on event type
        severity_map = {
            "4002": "high",  # SSH login
            "4000": "medium",  # SSH connection
            "3000": "low",  # HTTP request
            "2000": "medium",  # FTP login
            "6001": "medium",  # Telnet login
            "8001": "high",  # MySQL login
            "9999": "high",  # Packet anomaly
        }
        severity = severity_map.get(event_type, "medium")

        # Create tags
        tags = [f"type_{event_type}", f"source_{source}"]
        if "logdata" in message_data:
            logdata = message_data["logdata"]
            if isinstance(logdata, dict):
                if "USERNAME" in logdata:
                    tags.append("auth_attempt")
                if "PASSWORD" in logdata:
                    tags.append("credential_attempt")

        return create_event(
            event_type=event_type,
            source=source,
            data=event_data,
            severity=severity,
            timestamp=timestamp,
            tags=tags,
        )

    async def get_consumer_metrics(self) -> Dict[str, Any]:
        """Get consumer-specific metrics"""
        base_metrics = self.get_metrics()

        consumer_metrics = {
            **base_metrics,
            "topic": self.consumer_config.topic,
            "group_id": self.consumer_config.group_id,
            "event_handlers_count": len(self._event_handlers),
            "queue_size": self._processing_queue.qsize(),
            "max_queue_size": self._processing_queue.maxsize,
        }

        return consumer_metrics
