#!/usr/bin/env python3
"""
Alert Store for NetSentinel
Manages alert storage, retrieval, and lifecycle
"""

import asyncio
import time
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import json

try:
    from ..core.base import BaseComponent
    from ..monitoring.logger import create_logger
except ImportError:
    from core.base import BaseComponent
    from monitoring.logger import create_logger

logger = create_logger("alert_store")


class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    EXPIRED = "expired"


@dataclass
class Alert:
    """Alert data structure"""
    alert_id: str
    title: str
    description: str
    severity: AlertSeverity
    status: AlertStatus
    source: str
    event_data: Dict[str, Any]
    tags: List[str]
    created_at: float
    updated_at: float
    acknowledged_at: Optional[float] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[float] = None
    resolved_by: Optional[str] = None
    escalation_count: int = 0
    last_escalation: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['severity'] = self.severity.value
        data['status'] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Alert':
        """Create from dictionary"""
        data_copy = data.copy()
        data_copy['severity'] = AlertSeverity(data['severity'])
        data_copy['status'] = AlertStatus(data['status'])
        return cls(**data_copy)


class AlertStore(BaseComponent):
    """
    Alert storage and management system
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("alert_store", config or {})

        # In-memory storage (for demo - in production use database)
        self.alerts: Dict[str, Alert] = {}
        self._max_alerts = 1000  # Limit stored alerts

        # Statistics
        self.stats = {
            'total_alerts': 0,
            'active_alerts': 0,
            'acknowledged_alerts': 0,
            'resolved_alerts': 0,
            'critical_alerts': 0
        }

    async def _initialize(self):
        """Initialize alert store"""
        logger.info("Alert store initialized")

    async def _start_internal(self):
        """Start alert store operations"""
        logger.info("Alert store started")

    async def _stop_internal(self):
        """Stop alert store operations"""
        logger.info("Alert store stopped")

    def create_alert(
        self,
        title: str,
        description: str,
        severity: str,
        source: str,
        event_data: Dict[str, Any],
        tags: List[str] = None
    ) -> str:
        """Create a new alert"""

        alert_id = str(uuid.uuid4())
        now = time.time()

        alert = Alert(
            alert_id=alert_id,
            title=title,
            description=description,
            severity=AlertSeverity(severity.lower()),
            status=AlertStatus.ACTIVE,
            source=source,
            event_data=event_data,
            tags=tags or [],
            created_at=now,
            updated_at=now
        )

        # Store alert
        self.alerts[alert_id] = alert

        # Update statistics
        self.stats['total_alerts'] += 1
        self.stats['active_alerts'] += 1
        if severity.lower() == 'critical':
            self.stats['critical_alerts'] += 1

        # Cleanup old alerts if needed
        if len(self.alerts) > self._max_alerts:
            self._cleanup_old_alerts()

        logger.info(f"Created alert {alert_id}: {title} ({severity})")

        return alert_id

    def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Get alert by ID"""
        return self.alerts.get(alert_id)

    def get_alerts(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 100
    ) -> List[Alert]:
        """Get alerts with filtering"""

        alerts = list(self.alerts.values())

        # Apply filters
        if status:
            alerts = [a for a in alerts if a.status.value == status]

        if severity:
            alerts = [a for a in alerts if a.severity.value == severity]

        if source:
            alerts = [a for a in alerts if a.source == source]

        # Sort by creation time (newest first)
        alerts.sort(key=lambda x: x.created_at, reverse=True)

        return alerts[:limit]

    def acknowledge_alert(self, alert_id: str, user: str = "system") -> bool:
        """Acknowledge an alert"""

        alert = self.alerts.get(alert_id)
        if not alert:
            return False

        if alert.status != AlertStatus.ACTIVE:
            return False

        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = time.time()
        alert.acknowledged_by = user
        alert.updated_at = time.time()

        # Update statistics
        self.stats['active_alerts'] -= 1
        self.stats['acknowledged_alerts'] += 1

        logger.info(f"Alert {alert_id} acknowledged by {user}")

        return True

    def resolve_alert(self, alert_id: str, user: str = "system") -> bool:
        """Resolve an alert"""

        alert = self.alerts.get(alert_id)
        if not alert:
            return False

        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = time.time()
        alert.resolved_by = user
        alert.updated_at = time.time()

        # Update statistics
        if alert.status == AlertStatus.ACTIVE:
            self.stats['active_alerts'] -= 1
        elif alert.status == AlertStatus.ACKNOWLEDGED:
            self.stats['acknowledged_alerts'] -= 1

        self.stats['resolved_alerts'] += 1

        logger.info(f"Alert {alert_id} resolved by {user}")

        return True

    def get_statistics(self) -> Dict[str, Any]:
        """Get alert statistics"""
        return self.stats.copy()

    def _cleanup_old_alerts(self):
        """Clean up old resolved alerts to prevent memory issues"""

        # Keep only the most recent 500 alerts, remove older resolved ones
        resolved_alerts = [(aid, alert) for aid, alert in self.alerts.items()
                          if alert.status in [AlertStatus.RESOLVED, AlertStatus.EXPIRED]]

        if len(resolved_alerts) > 500:
            # Sort by creation time and keep newest 500
            resolved_alerts.sort(key=lambda x: x[1].created_at, reverse=True)
            keep_alerts = resolved_alerts[:500]
            keep_ids = {aid for aid, _ in keep_alerts}

            # Remove old alerts
            to_remove = [aid for aid in self.alerts.keys()
                        if aid not in keep_ids and self.alerts[aid].status in
                        [AlertStatus.RESOLVED, AlertStatus.EXPIRED]]

            for aid in to_remove:
                del self.alerts[aid]

            logger.info(f"Cleaned up {len(to_remove)} old alerts")

# Global alert store instance
_alert_store = None

def get_alert_store() -> AlertStore:
    """Get global alert store instance"""
    global _alert_store
    if _alert_store is None:
        _alert_store = AlertStore()
    return _alert_store