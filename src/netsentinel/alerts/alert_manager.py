#!/usr/bin/env python3
"""
Alert Manager for NetSentinel
Handles alert generation, notification, and escalation
"""

import asyncio
import time
import smtplib
import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

try:
    from ..core.base import BaseComponent
    from ..monitoring.logger import create_logger
    from .alert_store import get_alert_store, AlertSeverity
except ImportError:
    from core.base import BaseComponent
    from monitoring.logger import create_logger
    from alerts.alert_store import get_alert_store, AlertSeverity

logger = create_logger("alert_manager")


@dataclass
class NotificationChannel:
    """Notification channel configuration"""
    name: str
    type: str  # 'email', 'webhook', 'slack', etc.
    config: Dict[str, Any]
    enabled: bool = True


class AlertManager(BaseComponent):
    """
    Alert management and notification system
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("alert_manager", config or {})

        self.alert_store = get_alert_store()
        self.notification_channels: Dict[str, NotificationChannel] = {}
        self.escalation_rules: List[Dict[str, Any]] = []

        # Default escalation rules
        self._setup_default_escalation_rules()

    async def _initialize(self):
        """Initialize alert manager"""
        logger.info("Alert manager initialized")

    async def _start_internal(self):
        """Start alert manager operations"""
        logger.info("Alert manager started")

        # Start escalation monitoring
        asyncio.create_task(self._monitor_escalations())

    async def _stop_internal(self):
        """Stop alert manager operations"""
        logger.info("Alert manager stopped")

    async def generate_alert(
        self,
        title: str,
        description: str,
        severity: str,
        source: str,
        event_data: Dict[str, Any],
        tags: List[str] = None
    ) -> str:
        """Generate a new alert"""

        # Create alert in store
        alert_id = self.alert_store.create_alert(
            title=title,
            description=description,
            severity=severity,
            source=source,
            event_data=event_data,
            tags=tags or []
        )

        # Send notifications asynchronously
        asyncio.create_task(self._send_notifications(alert_id))

        # Check escalation rules asynchronously
        asyncio.create_task(self._check_escalation(alert_id))

        return alert_id

    def add_notification_channel(
        self,
        name: str,
        channel_type: str,
        config: Dict[str, Any]
    ) -> bool:
        """Add a notification channel"""

        if name in self.notification_channels:
            return False

        channel = NotificationChannel(
            name=name,
            type=channel_type,
            config=config,
            enabled=True
        )

        self.notification_channels[name] = channel
        logger.info(f"Added notification channel: {name} ({channel_type})")

        return True

    def remove_notification_channel(self, name: str) -> bool:
        """Remove a notification channel"""
        if name in self.notification_channels:
            del self.notification_channels[name]
            logger.info(f"Removed notification channel: {name}")
            return True
        return False

    def enable_channel(self, name: str) -> bool:
        """Enable a notification channel"""
        if name in self.notification_channels:
            self.notification_channels[name].enabled = True
            logger.info(f"Enabled notification channel: {name}")
            return True
        return False

    def disable_channel(self, name: str) -> bool:
        """Disable a notification channel"""
        if name in self.notification_channels:
            self.notification_channels[name].enabled = False
            logger.info(f"Disabled notification channel: {name}")
            return True
        return False

    def acknowledge_alert(self, alert_id: str, user: str = "system") -> bool:
        """Acknowledge an alert"""
        return self.alert_store.acknowledge_alert(alert_id, user)

    def resolve_alert(self, alert_id: str, user: str = "system") -> bool:
        """Resolve an alert"""
        return self.alert_store.resolve_alert(alert_id, user)

    def get_alerts(self, **filters) -> List[Any]:
        """Get alerts with filtering"""
        return self.alert_store.get_alerts(**filters)

    def get_statistics(self) -> Dict[str, Any]:
        """Get alert statistics"""
        stats = self.alert_store.get_statistics()
        stats['channels'] = len(self.notification_channels)
        stats['enabled_channels'] = len([c for c in self.notification_channels.values() if c.enabled])
        return stats

    async def _send_notifications(self, alert_id: str):
        """Send notifications for an alert"""

        alert = self.alert_store.get_alert(alert_id)
        if not alert:
            return

        # Send to all enabled channels
        for channel in self.notification_channels.values():
            if channel.enabled:
                try:
                    await self._send_to_channel(channel, alert)
                except Exception as e:
                    logger.error(f"Failed to send notification to {channel.name}: {e}")

    async def _send_to_channel(self, channel: NotificationChannel, alert):
        """Send notification to specific channel"""

        if channel.type == "email":
            await self._send_email(channel, alert)
        elif channel.type == "webhook":
            await self._send_webhook(channel, alert)
        elif channel.type == "slack":
            await self._send_slack(channel, alert)
        else:
            logger.warning(f"Unknown channel type: {channel.type}")

    async def _send_email(self, channel: NotificationChannel, alert):
        """Send email notification"""

        config = channel.config
        smtp_server = config.get('smtp_server', 'localhost')
        smtp_port = config.get('smtp_port', 587)
        smtp_user = config.get('smtp_user')
        smtp_password = config.get('smtp_password')
        from_addr = config.get('from_addr', 'alerts@netsentinel.local')
        to_addrs = config.get('to_addrs', [])

        if not to_addrs:
            return

        # Create message
        msg = MIMEMultipart()
        msg['From'] = from_addr
        msg['To'] = ', '.join(to_addrs)
        msg['Subject'] = f"NetSentinel Alert: {alert.title}"

        body = f"""
NetSentinel Security Alert

Title: {alert.title}
Severity: {alert.severity.value.upper()}
Source: {alert.source}
Created: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(alert.created_at))}

Description:
{alert.description}

Event Data:
{json.dumps(alert.event_data, indent=2)}

Tags: {', '.join(alert.tags) if alert.tags else 'None'}
        """

        msg.attach(MIMEText(body, 'plain'))

        # Send email
        try:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)
            server.sendmail(from_addr, to_addrs, msg.as_string())
            server.quit()
            logger.info(f"Email alert sent to {len(to_addrs)} recipients")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            raise

    async def _send_webhook(self, channel: NotificationChannel, alert):
        """Send webhook notification"""

        url = channel.config.get('url')
        if not url:
            return

        headers = channel.config.get('headers', {})
        headers.setdefault('Content-Type', 'application/json')

        payload = {
            'alert_id': alert.alert_id,
            'title': alert.title,
            'severity': alert.severity.value,
            'description': alert.description,
            'source': alert.source,
            'created_at': alert.created_at,
            'event_data': alert.event_data,
            'tags': alert.tags
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            logger.info(f"Webhook notification sent to {url}")
        except Exception as e:
            logger.error(f"Failed to send webhook to {url}: {e}")
            raise

    async def _send_slack(self, channel: NotificationChannel, alert):
        """Send Slack notification"""

        webhook_url = channel.config.get('webhook_url')
        if not webhook_url:
            return

        color_map = {
            'low': 'good',
            'medium': 'warning',
            'high': 'danger',
            'critical': 'danger'
        }

        payload = {
            'attachments': [{
                'color': color_map.get(alert.severity.value, 'warning'),
                'title': f"🚨 NetSentinel Alert: {alert.title}",
                'text': alert.description,
                'fields': [
                    {'title': 'Severity', 'value': alert.severity.value.upper(), 'short': True},
                    {'title': 'Source', 'value': alert.source, 'short': True},
                    {'title': 'Time', 'value': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(alert.created_at)), 'short': True}
                ],
                'footer': 'NetSentinel Security Platform'
            }]
        }

        try:
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info("Slack notification sent")
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            raise

    def _setup_default_escalation_rules(self):
        """Setup default escalation rules"""

        self.escalation_rules = [
            {
                'name': 'critical_escalation',
                'condition': lambda alert: alert.severity == AlertSeverity.CRITICAL,
                'delay_minutes': 5,
                'action': 'notify_all_channels'
            },
            {
                'name': 'high_priority_escalation',
                'condition': lambda alert: alert.severity == AlertSeverity.HIGH,
                'delay_minutes': 15,
                'action': 'notify_all_channels'
            },
            {
                'name': 'unacknowledged_alerts',
                'condition': lambda alert: alert.status.name == 'ACTIVE',
                'delay_minutes': 30,
                'action': 'escalate_priority'
            }
        ]

    async def _check_escalation(self, alert_id: str):
        """Check if alert needs escalation"""

        alert = self.alert_store.get_alert(alert_id)
        if not alert:
            return

        for rule in self.escalation_rules:
            if rule['condition'](alert):
                # Schedule escalation
                delay = rule['delay_minutes'] * 60  # Convert to seconds
                asyncio.create_task(self._schedule_escalation(alert_id, rule, delay))

    async def _schedule_escalation(self, alert_id: str, rule: Dict, delay: int):
        """Schedule alert escalation"""

        await asyncio.sleep(delay)

        alert = self.alert_store.get_alert(alert_id)
        if not alert or alert.status != alert.status.ACTIVE:  # Assuming AlertStatus.ACTIVE
            return

        logger.info(f"Escalating alert {alert_id} due to rule: {rule['name']}")

        # Perform escalation action
        if rule['action'] == 'notify_all_channels':
            await self._send_notifications(alert_id)
        elif rule['action'] == 'escalate_priority':
            # Could increase severity or send to additional channels
            pass

        alert.escalation_count += 1
        alert.last_escalation = time.time()

    async def _monitor_escalations(self):
        """Monitor and process escalations"""

        while self._running:
            try:
                # Check for alerts that need escalation
                current_time = time.time()

                for alert_id, alert in self.alert_store.alerts.items():
                    if alert.status.name == 'ACTIVE':  # Assuming AlertStatus.ACTIVE
                        # Check escalation rules
                        for rule in self.escalation_rules:
                            if rule['condition'](alert):
                                last_check = getattr(alert, 'last_escalation_check', 0)
                                if current_time - last_check > (rule['delay_minutes'] * 60):
                                    await self._schedule_escalation(alert_id, rule, 0)
                                    alert.last_escalation_check = current_time

                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Error in escalation monitoring: {e}")
                await asyncio.sleep(60)

# Global alert manager instance
_alert_manager = None

def get_alert_manager() -> AlertManager:
    """Get global alert manager instance"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager
