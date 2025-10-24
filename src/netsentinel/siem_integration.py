#!/usr/bin/env python3
"""
SIEM Integration for NetSentinel
Connects NetSentinel to enterprise SIEM systems (Splunk, ELK, Syslog)
"""

import json
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
import requests
import socket
from urllib.parse import urljoin
import ssl

# Import centralized utilities
from .utils import (
    create_logger,
    generate_id,
    hash_data,
    serialize_data,
    deserialize_data,
    retry_with_backoff,
    handle_errors,
    create_error_context,
    load_config,
    validate_config,
    create_connection_pool,
    measure_time,
    create_timer,
    generate_hmac,
    verify_hmac,
)

logger = create_logger("siem_integration", level="INFO")


@dataclass
class SiemEvent:
    """SIEM-formatted security event"""

    timestamp: float
    source: str
    event_type: str
    severity: str
    message: str
    raw_data: Dict[str, Any]
    tags: List[str] = None
    host: Optional[str] = None
    source_ip: Optional[str] = None
    destination_ip: Optional[str] = None
    user: Optional[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

    def to_splunk(self) -> Dict[str, Any]:
        """Format for Splunk HEC"""
        event_data = {
            "message": self.message,
            "severity": self.severity,
            "event_type": self.event_type,
            "source_ip": self.source_ip,
            "destination_ip": self.destination_ip,
            "user": self.user,
            "tags": self.tags,
            "raw_data": self.raw_data,
        }

        # Include threat_score if present in raw_data
        if "threat_score" in self.raw_data:
            event_data["threat_score"] = self.raw_data["threat_score"]

        return {
            "time": self.timestamp,
            "host": self.host or "netsentinel",
            "source": self.source,
            "sourcetype": f"netsentinel:{self.event_type}",
            "event": event_data,
        }

    def to_syslog(self) -> str:
        """Format for syslog (RFC 5424)"""
        # Calculate priority (facility * 8 + severity)
        facility = 20  # security/authorization messages
        severity_map = {
            "emergency": 0,
            "alert": 1,
            "critical": 2,
            "error": 3,
            "warning": 4,
            "notice": 5,
            "info": 6,
            "debug": 7,
        }
        severity_num = severity_map.get(self.severity.lower(), 6)
        priority = facility * 8 + severity_num

        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(self.timestamp))

        # Structured data
        structured_data = f'[netsentinel@12345 event_type="{self.event_type}" severity="{self.severity}"]'

        # Message
        message = f"{self.source}: {self.message}"

        return (
            f"<{priority}>1 {timestamp} {self.host or 'netsentinel'} "
            f"netsentinel {self.event_type} - {structured_data} {message}"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "timestamp": self.timestamp,
            "source": self.source,
            "event_type": self.event_type,
            "severity": self.severity,
            "message": self.message,
            "raw_data": self.raw_data,
            "tags": self.tags,
            "host": self.host,
            "source_ip": self.source_ip,
            "destination_ip": self.destination_ip,
            "user": self.user,
        }

    def to_json(self) -> str:
        """Format as JSON for ELK/Logstash"""
        json_data = {
            "@timestamp": time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.timestamp)
            ),
            "host": self.host or "netsentinel",
            "source": self.source,
            "event_type": self.event_type,
            "severity": self.severity,
            "message": self.message,
            "source_ip": self.source_ip,
            "destination_ip": self.destination_ip,
            "user": self.user,
            "tags": self.tags,
            "raw_data": self.raw_data,
        }

        # Include threat_score if present in raw_data
        if "threat_score" in self.raw_data:
            json_data["threat_score"] = self.raw_data["threat_score"]

        return json.dumps(json_data)


class SplunkConnector:
    """Splunk HTTP Event Collector integration"""

    def __init__(
        self,
        endpoint: str,
        token: str,
        index: str = "netsentinel",
        source: str = "netsentinel",
        sourcetype: str = "netsentinel:events",
        batch_size: int = 10,
        flush_interval: int = 30,
    ):
        self.endpoint = endpoint.rstrip("/")
        self.token = token
        self.index = index
        self.source = source
        self.sourcetype = sourcetype
        self.batch_size = batch_size
        self.flush_interval = flush_interval

        self.event_buffer = []
        self.last_flush = time.time()

        # Headers for HEC
        self.headers = {
            "Authorization": f"Splunk {self.token}",
            "Content-Type": "application/json",
        }

    def send_event(self, event: SiemEvent) -> bool:
        """Send single event to Splunk"""
        try:
            splunk_event = event.to_splunk()
            splunk_event.update(
                {
                    "index": self.index,
                    "source": self.source,
                    "sourcetype": self.sourcetype,
                }
            )

            response = requests.post(
                f"{self.endpoint}/services/collector/event",
                json=splunk_event,
                headers=self.headers,
                timeout=10,
            )

            if response.status_code == 200:
                logger.debug(f"Splunk event sent: {event.event_type}")
                return True
            else:
                logger.error(f"Splunk error: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Failed to send event to Splunk: {e}")
            return False

    def buffer_event(self, event: SiemEvent):
        """Buffer event for batch sending"""
        self.event_buffer.append(event)

        # Flush if batch size reached or interval exceeded
        if (
            len(self.event_buffer) >= self.batch_size
            or time.time() - self.last_flush >= self.flush_interval
        ):
            self.flush_buffer()

    def flush_buffer(self):
        """Flush buffered events to Splunk"""
        if not self.event_buffer:
            return

        try:
            # Send events in batch
            events_data = []
            for event in self.event_buffer:
                splunk_event = event.to_splunk()
                splunk_event.update(
                    {
                        "index": self.index,
                        "source": self.source,
                        "sourcetype": self.sourcetype,
                    }
                )
                events_data.append(splunk_event)

            response = requests.post(
                f"{self.endpoint}/services/collector/event",
                json={"events": events_data},
                headers=self.headers,
                timeout=30,
            )

            if response.status_code == 200:
                logger.info(f"Flushed {len(self.event_buffer)} events to Splunk")
                self.event_buffer.clear()
                self.last_flush = time.time()
            else:
                logger.error(
                    f"Splunk batch error: {response.status_code} - {response.text}"
                )

        except Exception as e:
            logger.error(f"Failed to flush events to Splunk: {e}")


class ElkConnector:
    """ELK Stack (Elasticsearch + Logstash) integration"""

    def __init__(
        self,
        elasticsearch_url: str = "http://elasticsearch:9200",
        logstash_url: Optional[str] = None,
        index_prefix: str = "netsentinel",
        api_key: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.elasticsearch_url = elasticsearch_url.rstrip("/")
        self.logstash_url = logstash_url
        self.index_prefix = index_prefix

        # Authentication
        self.api_key = api_key
        self.auth = (username, password) if username and password else None

        # Session for connection reuse
        self.session = requests.Session()
        if self.auth:
            self.session.auth = self.auth
        if self.api_key:
            self.session.headers.update({"Authorization": f"ApiKey {self.api_key}"})

    def send_event(self, event: SiemEvent) -> bool:
        """Send event to Elasticsearch"""
        try:
            # Create index name with date
            date_suffix = time.strftime("%Y.%m.%d", time.gmtime(event.timestamp))
            index_name = f"{self.index_prefix}-{date_suffix}"

            # Index document
            url = f"{self.elasticsearch_url}/{index_name}/_doc"
            response = self.session.post(
                url, json=json.loads(event.to_json()), timeout=10
            )

            if response.status_code in [200, 201]:
                logger.debug(f"ELK event indexed: {event.event_type}")
                return True
            else:
                logger.error(
                    f"ELK indexing error: {response.status_code} - {response.text}"
                )
                return False

        except Exception as e:
            logger.error(f"Failed to send event to ELK: {e}")
            return False

    def send_to_logstash(self, event: SiemEvent) -> bool:
        """Send event to Logstash"""
        if not self.logstash_url:
            return False

        try:
            response = self.session.post(
                self.logstash_url,
                data=event.to_json(),
                headers={"Content-Type": "application/json"},
                timeout=10,
            )

            if response.status_code == 200:
                logger.debug(f"Logstash event sent: {event.event_type}")
                return True
            else:
                logger.error(f"Logstash error: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Failed to send event to Logstash: {e}")
            return False


class SyslogConnector:
    """Syslog integration (UDP/TCP)"""

    def __init__(
        self,
        host: str,
        port: int = 514,
        protocol: str = "udp",
        facility: int = 20,
        hostname: str = "netsentinel",
    ):
        self.host = host
        self.port = port
        self.protocol = protocol.lower()
        self.facility = facility
        self.hostname = hostname

        if self.protocol == "tcp":
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        else:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send_event(self, event: SiemEvent) -> bool:
        """Send event via syslog"""
        try:
            syslog_msg = event.to_syslog()
            data = syslog_msg.encode("utf-8")

            if self.protocol == "tcp":
                # For TCP, establish connection each time or reuse
                try:
                    self.sock.connect((self.host, self.port))
                    self.sock.send(data)
                    self.sock.close()
                except (ConnectionError, OSError, socket.error) as e:
                    logger.warning(f"Socket connection failed, retrying: {e}")
                    # Reconnect and retry
                    self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.sock.connect((self.host, self.port))
                    self.sock.send(data)
                    self.sock.close()
            else:
                # UDP
                self.sock.sendto(data, (self.host, self.port))

            logger.debug(f"Syslog event sent: {event.event_type}")
            return True

        except Exception as e:
            logger.error(f"Failed to send syslog event: {e}")
            return False

    def close(self):
        """Close syslog connection"""
        try:
            self.sock.close()
        except (OSError, socket.error):
            # Socket already closed or connection error - ignore
            pass


class WebhookSiemConnector:
    """Generic webhook-based SIEM integration"""

    def __init__(
        self,
        webhook_url: str,
        headers: Optional[Dict[str, str]] = None,
        method: str = "POST",
        timeout: int = 10,
    ):
        self.webhook_url = webhook_url
        self.method = method.upper()
        self.timeout = timeout

        self.session = requests.Session()
        if headers:
            self.session.headers.update(headers)

    def send_event(self, event: SiemEvent) -> bool:
        """Send event via webhook"""
        try:
            payload = {
                "netsentinel_event": event.to_dict(),
                "formatted_message": event.message,
                "timestamp": time.time(),
            }

            response = self.session.request(
                self.method, self.webhook_url, json=payload, timeout=self.timeout
            )

            if response.status_code in [200, 201, 202]:
                logger.debug(f"Webhook event sent: {event.event_type}")
                return True
            else:
                logger.error(f"Webhook error: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Failed to send webhook event: {e}")
            return False


class SiemManager:
    """
    Central SIEM integration manager for NetSentinel
    Supports multiple SIEM systems simultaneously
    """

    def __init__(self):
        # Load configuration using centralized utilities
        config = load_config(
            prefix="SIEM",
            required_keys=["max_queue_size"],
            default_values={
                "max_queue_size": 10000,
                "retry_attempts": 3,
                "timeout": 30,
            },
        )

        self.connectors = {}
        self.enabled_systems = set()
        self.event_filters = {}
        self.active_flows = set()  # Track active data flows
        self.running = False
        self.stats = {
            "events_sent": 0,
            "events_failed": 0,
            "connectors_active": 0,
            "last_event_time": None,
        }

    def add_splunk_connector(self, name: str, endpoint: str, token: str, **kwargs):
        """Add Splunk connector"""
        connector = SplunkConnector(endpoint, token, **kwargs)
        self.connectors[f"splunk_{name}"] = connector
        logger.info(f"Added Splunk connector: {name}")

    def add_elk_connector(self, name: str, elasticsearch_url: str, **kwargs):
        """Add ELK connector"""
        connector = ElkConnector(elasticsearch_url, **kwargs)
        self.connectors[f"elk_{name}"] = connector
        logger.info(f"Added ELK connector: {name}")

    def add_syslog_connector(self, name: str, host: str, port: int = 514, **kwargs):
        """Add Syslog connector"""
        connector = SyslogConnector(host, port, **kwargs)
        self.connectors[f"syslog_{name}"] = connector
        logger.info(f"Added Syslog connector: {name}")

    def add_webhook_connector(self, name: str, webhook_url: str, **kwargs):
        """Add webhook connector"""
        connector = WebhookSiemConnector(webhook_url, **kwargs)
        self.connectors[f"webhook_{name}"] = connector
        logger.info(f"Added Webhook connector: {name}")

    def enable_system(self, system_name: str):
        """Enable a SIEM system"""
        if system_name in self.connectors:
            self.enabled_systems.add(system_name)
            self.stats["connectors_active"] = len(self.enabled_systems)
            logger.info(f"Enabled SIEM system: {system_name}")

    def disable_system(self, system_name: str):
        """Disable a SIEM system"""
        if system_name in self.enabled_systems:
            self.enabled_systems.remove(system_name)
            self.stats["connectors_active"] = len(self.enabled_systems)
            logger.info(f"Disabled SIEM system: {system_name}")

    def set_event_filter(
        self,
        system_name: str,
        event_types: List[str],
        severities: List[str] = None,
        min_score: float = None,
    ):
        """Set filtering rules for a SIEM system"""
        self.event_filters[system_name] = {
            "event_types": event_types,
            "severities": severities or [],
            "min_score": min_score,
        }
        logger.info(f"Set event filter for {system_name}")

    def send_event(self, event_data: Dict[str, Any]) -> bool:
        """Send event to all enabled SIEM systems"""
        try:
            # Convert NetSentinel event to SIEM format
            siem_event = self._convert_to_siem_event(event_data)

            if not siem_event:
                return False

            success_count = 0

            for system_name in self.enabled_systems:
                if system_name in self.connectors:
                    # Check filters
                    if not self._passes_filter(system_name, siem_event):
                        continue

                    connector = self.connectors[system_name]

                    try:
                        if hasattr(connector, "buffer_event"):
                            # Buffered connector (like Splunk)
                            connector.buffer_event(siem_event)
                        else:
                            # Direct send connector
                            if connector.send_event(siem_event):
                                success_count += 1
                    except Exception as e:
                        logger.error(f"Failed to send event to {system_name}: {e}")

            if success_count > 0:
                self.stats["events_sent"] += 1
                self.stats["last_event_time"] = time.time()
                return True
            else:
                self.stats["events_failed"] += 1
                return False

        except Exception as e:
            logger.error(f"Error sending event to SIEM systems: {e}")
            self.stats["events_failed"] += 1
            return False

    def _convert_to_siem_event(self, event_data: Dict[str, Any]) -> Optional[SiemEvent]:
        """Convert NetSentinel event to SIEM format"""
        try:
            # Determine severity
            threat_score = event_data.get("threat_score", 0)
            if threat_score >= 8.0:
                severity = "critical"
            elif threat_score >= 6.0:
                severity = "high"
            elif threat_score >= 4.0:
                severity = "medium"
            elif threat_score >= 2.0:
                severity = "low"
            else:
                severity = "info"

            # Create message
            event_type = event_data.get("logtype", "unknown")
            src_ip = event_data.get("src_host", "unknown")
            message = (
                f"Security event: {event_type} from {src_ip} (score: {threat_score})"
            )

            return SiemEvent(
                timestamp=event_data.get("timestamp", time.time()),
                source="netsentinel",
                event_type=str(event_type),
                severity=severity,
                message=message,
                host="netsentinel-cluster",
                source_ip=src_ip,
                raw_data=event_data,
                tags=["netsentinel", f"type_{event_type}"],
            )

        except Exception as e:
            logger.error(f"Failed to convert event to SIEM format: {e}")
            return None

    def _passes_filter(self, system_name: str, event: SiemEvent) -> bool:
        """Check if event passes system filter"""
        if system_name not in self.event_filters:
            return True  # No filter means accept all

        filter_rules = self.event_filters[system_name]

        # Check event types
        if (
            filter_rules["event_types"]
            and event.event_type not in filter_rules["event_types"]
        ):
            return False

        # Check severities
        if (
            filter_rules["severities"]
            and event.severity not in filter_rules["severities"]
        ):
            return False

        # Check minimum score (if available in raw data)
        if filter_rules["min_score"] is not None:
            event_score = event.raw_data.get("threat_score", 0)
            if event_score < filter_rules["min_score"]:
                return False

        return True

    def flush_buffers(self):
        """Flush any buffered events"""
        for system_name, connector in self.connectors.items():
            if hasattr(connector, "flush_buffer"):
                try:
                    connector.flush_buffer()
                except Exception as e:
                    logger.error(f"Failed to flush buffer for {system_name}: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get SIEM integration statistics"""
        return {
            **self.stats,
            "enabled_systems": list(self.enabled_systems),
            "available_connectors": list(self.connectors.keys()),
            "active_filters": list(self.event_filters.keys()),
        }

    def shutdown(self):
        """Shutdown SIEM manager and close connections"""
        self.flush_buffers()

        for connector in self.connectors.values():
            if hasattr(connector, "close"):
                try:
                    connector.close()
                except Exception as e:
                    logger.warning(
                        f"Error closing connector {connector.__class__.__name__}: {e}"
                    )
                    pass

        logger.info("SIEM manager shutdown complete")


# Global SIEM manager instance
siem_manager = None


def get_siem_manager() -> SiemManager:
    """Get or create global SIEM manager instance"""
    global siem_manager
    if siem_manager is None:
        siem_manager = SiemManager()
    return siem_manager


def setup_default_siem():
    """Setup default SIEM integrations from environment variables"""
    manager = get_siem_manager()

    # Splunk integration
    splunk_url = os.getenv("SPLUNK_HEC_URL")
    splunk_token = os.getenv("SPLUNK_HEC_TOKEN")
    if splunk_url and splunk_token:
        manager.add_splunk_connector(
            "default",
            splunk_url,
            splunk_token,
            index=os.getenv("SPLUNK_INDEX", "netsentinel"),
        )
        manager.enable_system("splunk_default")

    # ELK integration
    elk_url = os.getenv("ELASTICSEARCH_URL")
    if elk_url:
        manager.add_elk_connector(
            "default",
            elk_url,
            api_key=os.getenv("ELASTICSEARCH_API_KEY"),
            username=os.getenv("ELASTICSEARCH_USERNAME"),
            password=os.getenv("ELASTICSEARCH_PASSWORD"),
        )
        manager.enable_system("elk_default")

    # Syslog integration
    syslog_host = os.getenv("SYSLOG_HOST")
    if syslog_host:
        syslog_port = int(os.getenv("SYSLOG_PORT", "514"))
        manager.add_syslog_connector(
            "default",
            syslog_host,
            syslog_port,
            protocol=os.getenv("SYSLOG_PROTOCOL", "udp"),
        )
        manager.enable_system("syslog_default")

    # Webhook integration
    webhook_url = os.getenv("SIEM_WEBHOOK_URL")
    if webhook_url:
        manager.add_webhook_connector(
            "default",
            webhook_url,
            headers=(
                {"Authorization": f"Bearer {os.getenv('SIEM_WEBHOOK_TOKEN', '')}"}
                if os.getenv("SIEM_WEBHOOK_TOKEN")
                else None
            ),
        )
        manager.enable_system("webhook_default")

    # Set up default filters
    for system in manager.enabled_systems:
        manager.set_event_filter(
            system,
            event_types=["4002", "4000", "2000", "9999"],  # SSH, FTP, packet anomalies
            severities=["high", "critical"],
            min_score=6.0,
        )

    logger.info("Default SIEM integrations configured")


def send_to_siem(event_data: Dict[str, Any]) -> bool:
    """Convenience function to send events to SIEM systems"""
    manager = get_siem_manager()
    return manager.send_event(event_data)
