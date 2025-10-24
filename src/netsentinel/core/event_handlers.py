#!/usr/bin/env python3
"""
Event Handlers for NetSentinel
Handles domain events and triggers appropriate actions
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .event_store import DomainEvent, EventType, get_event_store, create_domain_event
from ..core.interfaces import Alert, Event
from ..processors.event_analyzer import AnalysisResult, ThreatLevel

logger = logging.getLogger(__name__)


class ThreatDetectionHandler:
    """Handles threat detection events"""

    def __init__(self, alert_manager=None, firewall_manager=None):
        self.alert_manager = alert_manager
        self.firewall_manager = firewall_manager
        self.event_store = get_event_store()
        self.logger = logging.getLogger(f"{__name__}.ThreatDetectionHandler")

    async def handle_threat_detected(self, event: DomainEvent) -> None:
        """Handle threat detection event"""
        try:
            threat_data = event.data
            analysis_result = AnalysisResult(
                event=Event(
                    id=threat_data.get("event_id"),
                    timestamp=threat_data.get("timestamp"),
                    source=threat_data.get("source"),
                    event_type=threat_data.get("event_type"),
                    data=threat_data.get("data", {}),
                    severity=threat_data.get("severity", "medium"),
                    tags=threat_data.get("tags", []),
                ),
                threat_score=threat_data.get("threat_score", 0.0),
                threat_level=ThreatLevel(threat_data.get("threat_level", "low")),
                confidence=threat_data.get("confidence", 0.0),
                indicators=threat_data.get("indicators", []),
            )

            # Create alert if threat level is high enough
            if analysis_result.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
                await self._create_alert(analysis_result, event)

            # Block IP if threat is critical
            if analysis_result.threat_level == ThreatLevel.CRITICAL:
                await self._block_threat_ip(analysis_result, event)

            self.logger.info(
                f"Processed threat detection: {analysis_result.threat_level.value}"
            )

        except Exception as e:
            self.logger.error(f"Error handling threat detection: {e}")

    async def _create_alert(
        self, analysis_result: AnalysisResult, original_event: DomainEvent
    ) -> None:
        """Create alert for high-threat event"""
        try:
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

            # Store alert
            if self.alert_manager:
                await self.alert_manager.create_alert(alert)

            # Create alert created event
            alert_event = create_domain_event(
                event_type=EventType.ALERT_CREATED,
                aggregate_id=alert.id,
                aggregate_type="Alert",
                data={
                    "alert_id": alert.id,
                    "threat_score": analysis_result.threat_score,
                    "threat_level": analysis_result.threat_level.value,
                    "indicators": analysis_result.indicators,
                },
                metadata={
                    "original_event_id": original_event.id,
                    "correlation_id": original_event.correlation_id,
                },
                correlation_id=original_event.correlation_id,
                causation_id=original_event.id,
            )

            await self.event_store.append_event(alert_event)

        except Exception as e:
            self.logger.error(f"Error creating alert: {e}")

    async def _block_threat_ip(
        self, analysis_result: AnalysisResult, original_event: DomainEvent
    ) -> None:
        """Block threat IP for critical threats"""
        try:
            ip_address = analysis_result.event.data.get("ip")
            if not ip_address:
                self.logger.warning("No IP address found for blocking")
                return

            # Block IP using firewall manager
            if self.firewall_manager:
                success = await self.firewall_manager.block_ip(
                    ip_address, duration=3600
                )
                if success:
                    # Create IP blocked event
                    block_event = create_domain_event(
                        event_type=EventType.IP_BLOCKED,
                        aggregate_id=ip_address,
                        aggregate_type="IPAddress",
                        data={
                            "ip_address": ip_address,
                            "threat_score": analysis_result.threat_score,
                            "block_duration": 3600,
                            "reason": "Critical threat detected",
                        },
                        metadata={
                            "original_event_id": original_event.id,
                            "threat_level": analysis_result.threat_level.value,
                        },
                        correlation_id=original_event.correlation_id,
                        causation_id=original_event.id,
                    )

                    await self.event_store.append_event(block_event)
                    self.logger.info(f"Blocked IP {ip_address} due to critical threat")

        except Exception as e:
            self.logger.error(f"Error blocking threat IP: {e}")


class AlertManagementHandler:
    """Handles alert management events"""

    def __init__(self, alert_manager=None):
        self.alert_manager = alert_manager
        self.event_store = get_event_store()
        self.logger = logging.getLogger(f"{__name__}.AlertManagementHandler")

    async def handle_alert_acknowledged(self, event: DomainEvent) -> None:
        """Handle alert acknowledgment"""
        try:
            alert_id = event.data.get("alert_id")
            user_id = event.data.get("user_id")

            if self.alert_manager and alert_id:
                success = await self.alert_manager.acknowledge_alert(alert_id)
                if success:
                    self.logger.info(f"Alert {alert_id} acknowledged by {user_id}")
                else:
                    self.logger.warning(f"Failed to acknowledge alert {alert_id}")

        except Exception as e:
            self.logger.error(f"Error handling alert acknowledgment: {e}")

    async def handle_alert_resolved(self, event: DomainEvent) -> None:
        """Handle alert resolution"""
        try:
            alert_id = event.data.get("alert_id")
            user_id = event.data.get("user_id")
            resolution_notes = event.data.get("resolution_notes", "")

            if self.alert_manager and alert_id:
                success = await self.alert_manager.resolve_alert(alert_id)
                if success:
                    self.logger.info(
                        f"Alert {alert_id} resolved by {user_id}: {resolution_notes}"
                    )
                else:
                    self.logger.warning(f"Failed to resolve alert {alert_id}")

        except Exception as e:
            self.logger.error(f"Error handling alert resolution: {e}")


class SystemEventHandler:
    """Handles system events"""

    def __init__(self):
        self.event_store = get_event_store()
        self.logger = logging.getLogger(f"{__name__}.SystemEventHandler")

    async def handle_system_started(self, event: DomainEvent) -> None:
        """Handle system startup event"""
        try:
            component = event.data.get("component", "unknown")
            self.logger.info(f"System component {component} started")

            # Log system startup metrics
            startup_data = {
                "component": component,
                "startup_time": event.timestamp.isoformat(),
                "version": event.data.get("version", "unknown"),
            }

            self.logger.info(f"System startup: {startup_data}")

        except Exception as e:
            self.logger.error(f"Error handling system started event: {e}")

    async def handle_system_stopped(self, event: DomainEvent) -> None:
        """Handle system shutdown event"""
        try:
            component = event.data.get("component", "unknown")
            self.logger.info(f"System component {component} stopped")

            # Log system shutdown metrics
            shutdown_data = {
                "component": component,
                "shutdown_time": event.timestamp.isoformat(),
                "uptime": event.data.get("uptime", 0),
            }

            self.logger.info(f"System shutdown: {shutdown_data}")

        except Exception as e:
            self.logger.error(f"Error handling system stopped event: {e}")

    async def handle_configuration_changed(self, event: DomainEvent) -> None:
        """Handle configuration change event"""
        try:
            config_key = event.data.get("config_key")
            old_value = event.data.get("old_value")
            new_value = event.data.get("new_value")
            user_id = event.data.get("user_id", "system")

            self.logger.info(f"Configuration changed: {config_key} by {user_id}")
            self.logger.debug(f"  Old value: {old_value}")
            self.logger.debug(f"  New value: {new_value}")

            # Audit log configuration changes
            audit_data = {
                "config_key": config_key,
                "old_value": str(old_value),
                "new_value": str(new_value),
                "user_id": user_id,
                "timestamp": event.timestamp.isoformat(),
            }

            self.logger.info(f"Configuration audit: {audit_data}")

        except Exception as e:
            self.logger.error(f"Error handling configuration change: {e}")


class EventHandlerRegistry:
    """Registry for event handlers"""

    def __init__(self):
        self.handlers = {}
        self.event_store = get_event_store()
        self.logger = logging.getLogger(f"{__name__}.EventHandlerRegistry")

    def register_handler(self, event_type: EventType, handler: Any) -> None:
        """Register event handler"""
        self.handlers[event_type] = handler
        self.event_store.subscribe(event_type, handler)
        self.logger.debug(f"Registered handler for {event_type.value}")

    def register_all_handlers(self, alert_manager=None, firewall_manager=None) -> None:
        """Register all default event handlers"""
        # Threat detection handler
        threat_handler = ThreatDetectionHandler(alert_manager, firewall_manager)
        self.register_handler(
            EventType.THREAT_DETECTED, threat_handler.handle_threat_detected
        )

        # Alert management handler
        alert_handler = AlertManagementHandler(alert_manager)
        self.register_handler(
            EventType.ALERT_ACKNOWLEDGED, alert_handler.handle_alert_acknowledged
        )
        self.register_handler(
            EventType.ALERT_RESOLVED, alert_handler.handle_alert_resolved
        )

        # System event handler
        system_handler = SystemEventHandler()
        self.register_handler(
            EventType.SYSTEM_STARTED, system_handler.handle_system_started
        )
        self.register_handler(
            EventType.SYSTEM_STOPPED, system_handler.handle_system_stopped
        )
        self.register_handler(
            EventType.CONFIGURATION_CHANGED, system_handler.handle_configuration_changed
        )

        self.logger.info("All event handlers registered")

    def get_handler(self, event_type: EventType) -> Optional[Any]:
        """Get handler for event type"""
        return self.handlers.get(event_type)

    def get_all_handlers(self) -> Dict[EventType, Any]:
        """Get all registered handlers"""
        return self.handlers.copy()
