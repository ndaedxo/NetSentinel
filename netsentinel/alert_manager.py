#!/usr/bin/env python3
"""
Alert Manager for NetSentinel
Comprehensive alerting system with email, Slack, webhooks, and escalation
"""

import json
import time
import threading
import smtplib
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

@dataclass
class Alert:
    """Alert data structure"""
    id: str
    title: str
    description: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    source: str
    timestamp: float
    event_data: Dict[str, Any]
    tags: List[str] = None
    acknowledged: bool = False
    resolved: bool = False
    escalation_level: int = 0
    last_notification: Optional[float] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

    def to_dict(self) -> Dict:
        return asdict(self)

    def is_expired(self, ttl_seconds: int = 3600) -> bool:
        """Check if alert has expired"""
        return time.time() - self.timestamp > ttl_seconds

    def should_escalate(self, escalation_delays: List[int]) -> bool:
        """Check if alert should be escalated"""
        if self.escalation_level >= len(escalation_delays):
            return False

        delay = escalation_delays[self.escalation_level]
        if not self.last_notification:
            return True

        return time.time() - self.last_notification > delay

@dataclass
class AlertRule:
    """Alert rule configuration"""
    name: str
    condition: Dict[str, Any]  # Conditions to trigger alert
    template: str  # Alert template name
    channels: List[str]  # Notification channels
    severity: str
    enabled: bool = True
    throttle_seconds: int = 300  # Minimum time between alerts
    escalation_delays: List[int] = None  # Escalation delays in seconds

    def __post_init__(self):
        if self.escalation_delays is None:
            self.escalation_delays = [300, 900, 3600]  # 5min, 15min, 1hour

class AlertTemplate:
    """Alert message template"""

    def __init__(self, name: str, subject_template: str, body_template: str,
                 html_template: Optional[str] = None):
        self.name = name
        self.subject_template = subject_template
        self.body_template = body_template
        self.html_template = html_template or body_template

    def format_subject(self, alert: Alert) -> str:
        """Format alert subject"""
        return self.subject_template.format(
            title=alert.title,
            severity=alert.severity.upper(),
            source=alert.source,
            timestamp=datetime.fromtimestamp(alert.timestamp).strftime('%Y-%m-%d %H:%M:%S')
        )

    def format_body(self, alert: Alert) -> str:
        """Format alert body"""
        return self.body_template.format(
            title=alert.title,
            description=alert.description,
            severity=alert.severity.upper(),
            source=alert.source,
            timestamp=datetime.fromtimestamp(alert.timestamp).strftime('%Y-%m-%d %H:%M:%S'),
            event_data=json.dumps(alert.event_data, indent=2),
            tags=', '.join(alert.tags)
        )

class EmailNotifier:
    """Email notification handler"""

    def __init__(self, smtp_server: str, smtp_port: int = 587,
                 username: Optional[str] = None, password: Optional[str] = None,
                 use_tls: bool = True, from_address: str = "alerts@netsentinel.local"):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.from_address = from_address

    def send_alert(self, alert: Alert, template: AlertTemplate,
                   recipients: List[str]) -> bool:
        """Send alert via email"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = template.format_subject(alert)
            msg['From'] = self.from_address
            msg['To'] = ', '.join(recipients)

            # Add timestamp and alert ID to headers
            msg['X-Alert-ID'] = alert.id
            msg['X-Alert-Timestamp'] = str(int(alert.timestamp))
            msg['X-Alert-Severity'] = alert.severity

            # Plain text body
            text_part = MIMEText(template.format_body(alert), 'plain')
            msg.attach(text_part)

            # HTML body if available
            if template.html_template != template.body_template:
                html_part = MIMEText(template.format_body(alert), 'html')
                msg.attach(html_part)

            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            if self.use_tls:
                server.starttls()

            if self.username and self.password:
                server.login(self.username, self.password)

            server.sendmail(self.from_address, recipients, msg.as_string())
            server.quit()

            logger.info(f"Email alert sent to {len(recipients)} recipients: {alert.title}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False

class SlackNotifier:
    """Slack notification handler"""

    def __init__(self, webhook_url: str, channel: Optional[str] = None,
                 username: str = "NetSentinel", icon_emoji: str = ":shield:"):
        self.webhook_url = webhook_url
        self.channel = channel
        self.username = username
        self.icon_emoji = icon_emoji

    def send_alert(self, alert: Alert, template: AlertTemplate) -> bool:
        """Send alert to Slack"""
        try:
            # Create Slack message
            message = {
                "username": self.username,
                "icon_emoji": self.icon_emoji,
                "attachments": [{
                    "title": template.format_subject(alert),
                    "text": template.format_body(alert),
                    "color": self._get_severity_color(alert.severity),
                    "fields": [
                        {
                            "title": "Severity",
                            "value": alert.severity.upper(),
                            "short": True
                        },
                        {
                            "title": "Source",
                            "value": alert.source,
                            "short": True
                        },
                        {
                            "title": "Time",
                            "value": datetime.fromtimestamp(alert.timestamp).strftime('%Y-%m-%d %H:%M:%S'),
                            "short": True
                        }
                    ],
                    "footer": "NetSentinel Alert System",
                    "ts": alert.timestamp
                }]
            }

            if self.channel:
                message["channel"] = self.channel

            # Send to Slack
            response = requests.post(self.webhook_url, json=message, timeout=10)

            if response.status_code == 200:
                logger.info(f"Slack alert sent: {alert.title}")
                return True
            else:
                logger.error(f"Slack webhook failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False

    def _get_severity_color(self, severity: str) -> str:
        """Get color for severity level"""
        colors = {
            'low': 'good',      # green
            'medium': 'warning', # yellow/orange
            'high': 'danger',   # red
            'critical': '#FF0000'  # bright red
        }
        return colors.get(severity.lower(), 'warning')

class WebhookNotifier:
    """Generic webhook notification handler"""

    def __init__(self, webhook_url: str, headers: Optional[Dict[str, str]] = None,
                 timeout: int = 10):
        self.webhook_url = webhook_url
        self.headers = headers or {}
        self.timeout = timeout

        # Set default content type if not specified
        if 'Content-Type' not in self.headers:
            self.headers['Content-Type'] = 'application/json'

    def send_alert(self, alert: Alert, template: AlertTemplate) -> bool:
        """Send alert via webhook"""
        try:
            payload = {
                "alert": alert.to_dict(),
                "formatted": {
                    "subject": template.format_subject(alert),
                    "body": template.format_body(alert)
                },
                "timestamp": time.time()
            }

            response = requests.post(
                self.webhook_url,
                json=payload,
                headers=self.headers,
                timeout=self.timeout
            )

            if response.status_code in [200, 201, 202]:
                logger.info(f"Webhook alert sent to {self.webhook_url}: {alert.title}")
                return True
            else:
                logger.error(f"Webhook failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
            return False

class AlertManager:
    """
    Comprehensive alert management system for NetSentinel
    Handles alert generation, routing, escalation, and notifications
    """

    def __init__(self, max_alerts: int = 1000, alert_ttl: int = 3600):
        self.max_alerts = max_alerts
        self.alert_ttl = alert_ttl

        # Alert storage
        self.alerts = {}  # alert_id -> Alert
        self.active_alerts = {}  # alert_key -> Alert (for deduplication)

        # Alert rules and templates
        self.rules = {}
        self.templates = {}
        self.notifiers = {}

        # Threading
        self.running = False
        self.alert_thread = None
        self.cleanup_thread = None

        # Default templates
        self._setup_default_templates()

        logger.info("Initialized alert manager")

    def _setup_default_templates(self):
        """Setup default alert templates"""
        self.templates['security_alert'] = AlertTemplate(
            name='security_alert',
            subject_template='🚨 NetSentinel {severity} Alert: {title}',
            body_template='''
NetSentinel Security Alert
========================

Title: {title}
Severity: {severity}
Source: {source}
Time: {timestamp}

Description:
{description}

Event Data:
{event_data}

Tags: {tags}

This alert was automatically generated by NetSentinel.
'''
        )

        self.templates['threat_detected'] = AlertTemplate(
            name='threat_detected',
            subject_template='🔴 THREAT DETECTED: {title}',
            body_template='''
CRITICAL SECURITY ALERT
======================

A high-threat activity has been detected:

Title: {title}
Severity: {severity}
Source: {source}
Time: {timestamp}

Description:
{description}

Event Details:
{event_data}

Immediate investigation recommended.

Tags: {tags}
'''
        )

    def add_rule(self, rule: AlertRule):
        """Add an alert rule"""
        self.rules[rule.name] = rule
        logger.info(f"Added alert rule: {rule.name}")

    def add_template(self, template: AlertTemplate):
        """Add an alert template"""
        self.templates[template.name] = template
        logger.info(f"Added alert template: {template.name}")

    def add_email_notifier(self, name: str, config: Dict[str, Any]):
        """Add email notifier"""
        notifier = EmailNotifier(**config)
        self.notifiers[f"email_{name}"] = notifier
        logger.info(f"Added email notifier: {name}")

    def add_slack_notifier(self, name: str, webhook_url: str, **kwargs):
        """Add Slack notifier"""
        notifier = SlackNotifier(webhook_url, **kwargs)
        self.notifiers[f"slack_{name}"] = notifier
        logger.info(f"Added Slack notifier: {name}")

    def add_webhook_notifier(self, name: str, webhook_url: str, **kwargs):
        """Add webhook notifier"""
        notifier = WebhookNotifier(webhook_url, **kwargs)
        self.notifiers[f"webhook_{name}"] = notifier
        logger.info(f"Added webhook notifier: {name}")

    def start(self):
        """Start alert manager"""
        if self.running:
            return

        self.running = True

        # Start alert processing thread
        self.alert_thread = threading.Thread(target=self._process_alerts, daemon=True)
        self.alert_thread.start()

        # Start cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_expired_alerts, daemon=True)
        self.cleanup_thread.start()

        logger.info("Alert manager started")

    def stop(self):
        """Stop alert manager"""
        self.running = False

        if self.alert_thread and self.alert_thread.is_alive():
            self.alert_thread.join(timeout=5)

        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=5)

        logger.info("Alert manager stopped")

    def generate_alert(self, title: str, description: str, severity: str,
                      source: str, event_data: Dict[str, Any],
                      tags: Optional[List[str]] = None) -> Optional[str]:
        """Generate a new alert"""
        try:
            alert_id = f"{int(time.time() * 1000)}_{hash(title + description) % 10000}"

            # Check for duplicates (same title/source in last throttle period)
            alert_key = f"{title}_{source}"
            if alert_key in self.active_alerts:
                existing = self.active_alerts[alert_key]
                if time.time() - existing.timestamp < 300:  # 5 minute throttle
                    logger.debug(f"Alert throttled (duplicate): {title}")
                    return None

            alert = Alert(
                id=alert_id,
                title=title,
                description=description,
                severity=severity.lower(),
                source=source,
                timestamp=time.time(),
                event_data=event_data,
                tags=tags or []
            )

            # Store alert
            self.alerts[alert_id] = alert
            self.active_alerts[alert_key] = alert

            # Enforce max alerts limit
            if len(self.alerts) > self.max_alerts:
                oldest_id = min(self.alerts.keys(), key=lambda x: self.alerts[x].timestamp)
                del self.alerts[oldest_id]

            logger.info(f"Alert generated: {title} (severity: {severity})")
            return alert_id

        except Exception as e:
            logger.error(f"Failed to generate alert: {e}")
            return None

    def check_event_against_rules(self, event_data: Dict[str, Any]) -> List[str]:
        """Check event against alert rules and generate alerts"""
        alert_ids = []

        for rule_name, rule in self.rules.items():
            if not rule.enabled:
                continue

            if self._matches_rule(event_data, rule.condition):
                alert_id = self.generate_alert(
                    title=f"Rule Alert: {rule_name}",
                    description=f"Alert triggered by rule: {rule_name}",
                    severity=rule.severity,
                    source="alert_rule",
                    event_data=event_data,
                    tags=["rule_based", rule_name]
                )

                if alert_id:
                    alert_ids.append(alert_id)

        return alert_ids

    def _matches_rule(self, event_data: Dict[str, Any], condition: Dict[str, Any]) -> bool:
        """Check if event matches rule condition"""
        try:
            for key, value in condition.items():
                if key not in event_data:
                    return False

                event_value = event_data[key]

                if isinstance(value, dict):
                    # Range conditions
                    if 'min' in value and event_value < value['min']:
                        return False
                    if 'max' in value and event_value > value['max']:
                        return False
                    if 'equals' in value and event_value != value['equals']:
                        return False
                    if 'contains' in value and value['contains'] not in str(event_value):
                        return False
                else:
                    # Direct equality
                    if event_value != value:
                        return False

            return True

        except Exception as e:
            logger.error(f"Error matching rule condition: {e}")
            return False

    def _process_alerts(self):
        """Process alerts and send notifications"""
        while self.running:
            try:
                current_time = time.time()

                for alert in self.alerts.values():
                    if alert.acknowledged or alert.resolved:
                        continue

                    # Check if alert should be escalated/notified
                    rule_name = None
                    for r_name, rule in self.rules.items():
                        if rule.name in alert.tags:
                            rule_name = r_name
                            break

                    rule = self.rules.get(rule_name) if rule_name else None

                    if self._should_notify_alert(alert, rule):
                        self._send_alert_notifications(alert, rule)

                time.sleep(10)  # Check every 10 seconds

            except Exception as e:
                logger.error(f"Error in alert processing: {e}")
                time.sleep(10)

    def _should_notify_alert(self, alert: Alert, rule: Optional[AlertRule]) -> bool:
        """Determine if alert should be notified"""
        if not rule:
            # Default behavior for alerts without rules
            return not alert.last_notification or time.time() - alert.last_notification > 300

        # Check escalation
        return alert.should_escalate(rule.escalation_delays)

    def _send_alert_notifications(self, alert: Alert, rule: Optional[AlertRule]):
        """Send alert notifications via configured channels"""
        try:
            template_name = rule.template if rule else 'security_alert'
            template = self.templates.get(template_name, self.templates['security_alert'])

            channels = rule.channels if rule else ['email_default']

            success_count = 0

            for channel in channels:
                if channel in self.notifiers:
                    notifier = self.notifiers[channel]
                    if hasattr(notifier, 'send_alert'):
                        if notifier.send_alert(alert, template):
                            success_count += 1

            if success_count > 0:
                alert.last_notification = time.time()
                if rule:
                    alert.escalation_level += 1

                logger.info(f"Alert notifications sent: {alert.title} ({success_count} channels)")

        except Exception as e:
            logger.error(f"Error sending alert notifications: {e}")

    def _cleanup_expired_alerts(self):
        """Clean up expired alerts"""
        while self.running:
            try:
                current_time = time.time()
                expired_ids = []

                for alert_id, alert in self.alerts.items():
                    if alert.is_expired(self.alert_ttl):
                        expired_ids.append(alert_id)

                for alert_id in expired_ids:
                    alert = self.alerts[alert_id]
                    alert_key = f"{alert.title}_{alert.source}"
                    if alert_key in self.active_alerts:
                        del self.active_alerts[alert_key]
                    del self.alerts[alert_id]

                if expired_ids:
                    logger.info(f"Cleaned up {len(expired_ids)} expired alerts")

                time.sleep(300)  # Clean up every 5 minutes

            except Exception as e:
                logger.error(f"Error in alert cleanup: {e}")
                time.sleep(300)

    def get_alerts(self, limit: int = 100, severity: Optional[str] = None,
                   acknowledged: Optional[bool] = None) -> List[Dict]:
        """Get alerts with optional filtering"""
        alerts = list(self.alerts.values())

        # Apply filters
        if severity:
            alerts = [a for a in alerts if a.severity == severity.lower()]

        if acknowledged is not None:
            alerts = [a for a in alerts if a.acknowledged == acknowledged]

        # Sort by timestamp (newest first)
        alerts.sort(key=lambda x: x.timestamp, reverse=True)

        return [alert.to_dict() for alert in alerts[:limit]]

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        if alert_id in self.alerts:
            self.alerts[alert_id].acknowledged = True
            logger.info(f"Alert acknowledged: {alert_id}")
            return True
        return False

    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        if alert_id in self.alerts:
            self.alerts[alert_id].resolved = True
            logger.info(f"Alert resolved: {alert_id}")
            return True
        return False

    def get_statistics(self) -> Dict:
        """Get alert statistics"""
        total_alerts = len(self.alerts)
        active_alerts = len([a for a in self.alerts.values()
                           if not a.acknowledged and not a.resolved])

        severity_counts = {}
        for alert in self.alerts.values():
            severity_counts[alert.severity] = severity_counts.get(alert.severity, 0) + 1

        return {
            'total_alerts': total_alerts,
            'active_alerts': active_alerts,
            'severity_breakdown': severity_counts,
            'rules_count': len(self.rules),
            'templates_count': len(self.templates),
            'notifiers_count': len(self.notifiers)
        }

# Global alert manager instance
alert_manager = None

def get_alert_manager() -> AlertManager:
    """Get or create global alert manager instance"""
    global alert_manager
    if alert_manager is None:
        alert_manager = AlertManager()
    return alert_manager

def create_security_alert(event_data: Dict[str, Any]) -> Optional[str]:
    """Convenience function to create security alerts from events"""
    manager = get_alert_manager()

    # Determine severity based on threat score
    threat_score = event_data.get('threat_score', 0)
    if threat_score >= 8.0:
        severity = 'critical'
    elif threat_score >= 6.0:
        severity = 'high'
    elif threat_score >= 4.0:
        severity = 'medium'
    else:
        severity = 'low'

    # Create descriptive title
    event_type = event_data.get('logtype', 'unknown')
    src_ip = event_data.get('src_host', 'unknown')

    title = f"Security Event: {event_type} from {src_ip}"
    description = f"Threat score: {threat_score}. Event type: {event_type}"

    return manager.generate_alert(
        title=title,
        description=description,
        severity=severity,
        source="netsentinel",
        event_data=event_data,
        tags=["security", f"type_{event_type}"]
    )

def setup_default_alerting():
    """Setup default alerting configuration"""
    manager = get_alert_manager()

    # Add default email notifier (if SMTP configured)
    smtp_server = os.getenv('SMTP_SERVER')
    if smtp_server:
        manager.add_email_notifier('default', {
            'smtp_server': smtp_server,
            'smtp_port': int(os.getenv('SMTP_PORT', 587)),
            'username': os.getenv('SMTP_USERNAME'),
            'password': os.getenv('SMTP_PASSWORD'),
            'from_address': os.getenv('ALERT_FROM_EMAIL', 'alerts@netsentinel.local')
        })

    # Add Slack notifier (if webhook configured)
    slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
    if slack_webhook:
        manager.add_slack_notifier('default', slack_webhook)

    # Add webhook notifier (if URL configured)
    webhook_url = os.getenv('ALERT_WEBHOOK_URL')
    if webhook_url:
        manager.add_webhook_notifier('default', webhook_url)

    # Add default alert rules
    high_threat_rule = AlertRule(
        name='high_threat_detection',
        condition={'threat_score': {'min': 7.0}},
        template='threat_detected',
        channels=['email_default', 'slack_default'] if smtp_server and slack_webhook else ['email_default'] if smtp_server else [],
        severity='high',
        throttle_seconds=300
    )

    manager.add_rule(high_threat_rule)

    # Start the alert manager
    manager.start()

    logger.info("Default alerting configuration applied")
