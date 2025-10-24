"""
NetSentinel - Advanced Network Anomaly Detection and Threat Mitigation

A comprehensive cybersecurity platform for real-time network threat detection,
analysis, and automated response using machine learning and distributed systems.

Main Components:
- Event Processing: Real-time event ingestion and analysis from Kafka
- Threat Intelligence: ML-based anomaly detection and correlation
- Automated Response: Firewall blocking and SDN quarantine
- Monitoring: Prometheus metrics and Grafana dashboards
- API: REST endpoints for health checks and threat intelligence

Author: NetSentinel Development Team
Version: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "NetSentinel Development Team"

# Core imports for easy access
from .core.base import BaseComponent, managed_component
from .core.models import (
    StandardEvent,
    StandardAlert,
    ValidationResult,
    create_event,
    create_alert,
)
from .core.error_handler import handle_errors, create_error_context

__all__ = [
    "BaseComponent",
    "managed_component",
    "StandardEvent",
    "StandardAlert",
    "ValidationResult",
    "create_event",
    "create_alert",
    "handle_errors",
    "create_error_context",
    "__version__",
    "__author__",
]
