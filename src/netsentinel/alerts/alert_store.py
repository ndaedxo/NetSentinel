#!/usr/bin/env python3
"""
Alert Store for NetSentinel
Manages alert storage, retrieval, and persistence
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass

from ..core.base import BaseManager, BaseConfig
from ..core.interfaces import Alert
from ..core.error_handler import handle_errors
from ..core.retry_handler import retry_on_failure
from ..utils.validation import validate_alert_data as validate_alert

logger = logging.getLogger(__name__)


@dataclass
class StoreConfig(BaseConfig):
    """Alert store configuration"""

    max_alerts: int = 10000
    alert_ttl: int = 3600  # seconds
    cleanup_interval: int = 300  # seconds
    persistence_enabled: bool = True
    storage_backend: str = "memory"  # memory, redis, elasticsearch


class AlertStore(BaseManager):
    """
    Manages alert storage and retrieval
    Supports multiple storage backends and automatic cleanup
    """

    def __init__(self, config: StoreConfig):
        super().__init__(config)
        self.config = config
        self.alerts: Dict[str, Alert] = {}
        self.alert_index: Dict[str, Set[str]] = {
            "by_severity": {},
            "by_source": {},
            "by_status": {},
            "by_timestamp": {},
        }
        self.storage_backend = None
        self.cleanup_task = None

        # Initialize storage backend
        self._initialize_storage_backend()

    def _initialize_storage_backend(self) -> None:
        """Initialize storage backend"""
        try:
            if self.config.storage_backend == "redis":
                from ..utils.connections import ConnectionManager

                self.storage_backend = ConnectionManager()
            elif self.config.storage_backend == "elasticsearch":
                # Initialize Elasticsearch client
                pass

            self.logger.info(
                f"Storage backend initialized: {self.config.storage_backend}"
            )

        except Exception as e:
            self.logger.error(f"Failed to initialize storage backend: {e}")
            self.storage_backend = None

    async def _start_internal(self) -> None:
        """Start alert store"""
        # Start cleanup task
        if self.config.cleanup_interval > 0:
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())

        self.logger.info("Alert store started")

    async def _stop_internal(self) -> None:
        """Stop alert store"""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass

        self.logger.info("Alert store stopped")

    async def store_alert(self, alert: Alert) -> bool:
        """Store an alert"""
        try:
            # Validate alert
            validation_result = validate_alert(alert.__dict__)
            if not validation_result.is_valid:
                self.logger.error(f"Invalid alert data: {validation_result.errors}")
                return False

            # Store in memory
            self.alerts[alert.id] = alert

            # Update indexes
            self._update_indexes(alert)

            # Persist to backend
            if self.storage_backend and self.config.persistence_enabled:
                await self._persist_alert(alert)

            self.logger.debug(f"Alert stored: {alert.id}")
            return True

        except Exception as e:
            self.logger.error(f"Error storing alert: {e}")
            return False

    async def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Get alert by ID"""
        try:
            # Check memory first
            if alert_id in self.alerts:
                return self.alerts[alert_id]

            # Check persistent storage
            if self.storage_backend and self.config.persistence_enabled:
                return await self._load_alert(alert_id)

            return None

        except Exception as e:
            self.logger.error(f"Error getting alert {alert_id}: {e}")
            return None

    async def get_alerts(self, filters: Optional[Dict[str, Any]] = None) -> List[Alert]:
        """Get alerts with optional filters"""
        try:
            alerts = list(self.alerts.values())

            if not filters:
                return alerts

            # Apply filters
            filtered_alerts = []
            for alert in alerts:
                if self._matches_filters(alert, filters):
                    filtered_alerts.append(alert)

            return filtered_alerts

        except Exception as e:
            self.logger.error(f"Error getting alerts: {e}")
            return []

    async def update_alert(self, alert_id: str, updates: Dict[str, Any]) -> bool:
        """Update an alert"""
        try:
            if alert_id not in self.alerts:
                return False

            alert = self.alerts[alert_id]

            # Apply updates
            for key, value in updates.items():
                if hasattr(alert, key):
                    setattr(alert, key, value)

            # Update indexes
            self._update_indexes(alert)

            # Persist changes
            if self.storage_backend and self.config.persistence_enabled:
                await self._persist_alert(alert)

            self.logger.debug(f"Alert updated: {alert_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error updating alert {alert_id}: {e}")
            return False

    async def delete_alert(self, alert_id: str) -> bool:
        """Delete an alert"""
        try:
            if alert_id not in self.alerts:
                return False

            alert = self.alerts[alert_id]

            # Remove from indexes
            self._remove_from_indexes(alert)

            # Remove from memory
            del self.alerts[alert_id]

            # Remove from persistent storage
            if self.storage_backend and self.config.persistence_enabled:
                await self._delete_persistent_alert(alert_id)

            self.logger.debug(f"Alert deleted: {alert_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error deleting alert {alert_id}: {e}")
            return False

    def _update_indexes(self, alert: Alert) -> None:
        """Update alert indexes"""
        # Severity index
        if alert.severity not in self.alert_index["by_severity"]:
            self.alert_index["by_severity"][alert.severity] = set()
        self.alert_index["by_severity"][alert.severity].add(alert.id)

        # Source index
        if alert.source not in self.alert_index["by_source"]:
            self.alert_index["by_source"][alert.source] = set()
        self.alert_index["by_source"][alert.source].add(alert.id)

        # Status index
        status = "resolved" if alert.resolved else "active"
        if status not in self.alert_index["by_status"]:
            self.alert_index["by_status"][status] = set()
        self.alert_index["by_status"][status].add(alert.id)

    def _remove_from_indexes(self, alert: Alert) -> None:
        """Remove alert from indexes"""
        # Remove from all indexes
        for index_name, index in self.alert_index.items():
            for key, alert_set in index.items():
                alert_set.discard(alert.id)

    def _matches_filters(self, alert: Alert, filters: Dict[str, Any]) -> bool:
        """Check if alert matches filters"""
        for key, value in filters.items():
            if key == "severity" and alert.severity != value:
                return False
            elif key == "source" and alert.source != value:
                return False
            elif key == "resolved" and alert.resolved != value:
                return False
            elif key == "acknowledged" and alert.acknowledged != value:
                return False
            elif key == "start_time" and alert.timestamp < value:
                return False
            elif key == "end_time" and alert.timestamp > value:
                return False

        return True

    async def _cleanup_loop(self) -> None:
        """Cleanup expired alerts"""
        while True:
            try:
                await asyncio.sleep(self.config.cleanup_interval)
                await self._cleanup_expired_alerts()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")

    async def _cleanup_expired_alerts(self) -> None:
        """Remove expired alerts"""
        current_time = time.time()
        expired_alerts = []

        for alert_id, alert in self.alerts.items():
            if current_time - alert.timestamp > self.config.alert_ttl:
                expired_alerts.append(alert_id)

        for alert_id in expired_alerts:
            await self.delete_alert(alert_id)

        if expired_alerts:
            self.logger.info(f"Cleaned up {len(expired_alerts)} expired alerts")

    async def _persist_alert(self, alert: Alert) -> None:
        """Persist alert to storage backend"""
        try:
            if self.config.storage_backend == "redis":
                # Store in Redis
                pass
            elif self.config.storage_backend == "elasticsearch":
                # Store in Elasticsearch
                pass

        except Exception as e:
            self.logger.error(f"Error persisting alert: {e}")

    async def _load_alert(self, alert_id: str) -> Optional[Alert]:
        """Load alert from storage backend"""
        try:
            if self.config.storage_backend == "redis":
                # Load from Redis
                pass
            elif self.config.storage_backend == "elasticsearch":
                # Load from Elasticsearch
                pass

            return None

        except Exception as e:
            self.logger.error(f"Error loading alert: {e}")
            return None

    async def _delete_persistent_alert(self, alert_id: str) -> None:
        """Delete alert from storage backend"""
        try:
            if self.config.storage_backend == "redis":
                # Delete from Redis
                pass
            elif self.config.storage_backend == "elasticsearch":
                # Delete from Elasticsearch
                pass

        except Exception as e:
            self.logger.error(f"Error deleting persistent alert: {e}")

    def get_store_metrics(self) -> Dict[str, Any]:
        """Get store metrics"""
        return {
            "total_alerts": len(self.alerts),
            "max_alerts": self.config.max_alerts,
            "storage_backend": self.config.storage_backend,
            "persistence_enabled": self.config.persistence_enabled,
            "indexes": {
                "by_severity": len(self.alert_index["by_severity"]),
                "by_source": len(self.alert_index["by_source"]),
                "by_status": len(self.alert_index["by_status"]),
            },
        }
