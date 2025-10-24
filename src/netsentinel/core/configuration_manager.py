#!/usr/bin/env python3
"""
Centralized Configuration Manager for NetSentinel
Provides single source of truth for all configuration
Designed for maintainability and preventing code debt
"""

import os
import json
import yaml
import logging
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path
import threading

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Database configuration"""

    host: str = "localhost"
    port: int = 5432
    username: str = ""
    password: str = ""
    database: str = ""
    ssl_enabled: bool = False
    connection_pool_size: int = 10
    timeout: float = 30.0


@dataclass
class KafkaConfig:
    """Kafka configuration"""

    bootstrap_servers: List[str] = field(default_factory=lambda: ["localhost:9092"])
    topic_prefix: str = "netsentinel"
    group_id: str = "netsentinel-processor"
    auto_offset_reset: str = "latest"
    enable_auto_commit: bool = True
    session_timeout_ms: int = 30000
    heartbeat_interval_ms: int = 3000


@dataclass
class RedisConfig:
    """Redis/Valkey configuration"""

    host: str = "localhost"
    port: int = 6379
    password: str = ""
    db: int = 0
    max_connections: int = 100
    timeout: float = 30.0
    retry_on_timeout: bool = True


@dataclass
class SecurityConfig:
    """Security configuration"""

    encryption_enabled: bool = True
    encryption_algorithm: str = "AES-256-GCM"
    key_rotation_days: int = 90
    jwt_secret: str = ""
    jwt_expiry_hours: int = 24
    rate_limit_requests: int = 100
    rate_limit_window: int = 3600


@dataclass
class MonitoringConfig:
    """Monitoring configuration"""

    prometheus_enabled: bool = True
    prometheus_port: int = 9090
    grafana_enabled: bool = True
    grafana_port: int = 3000
    health_check_interval: int = 30
    metrics_retention_days: int = 30


@dataclass
class NetSentinelConfig:
    """Main NetSentinel configuration"""

    # Core settings
    debug: bool = False
    log_level: str = "INFO"
    max_workers: int = 4
    event_batch_size: int = 100
    event_timeout: float = 30.0

    # Component settings
    packet_analysis_enabled: bool = True
    threat_intel_enabled: bool = True
    ml_analysis_enabled: bool = True
    enterprise_db_enabled: bool = True

    # Database configurations
    kafka: KafkaConfig = field(default_factory=KafkaConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    elasticsearch: DatabaseConfig = field(default_factory=DatabaseConfig)
    influxdb: DatabaseConfig = field(default_factory=DatabaseConfig)

    # Security configuration
    security: SecurityConfig = field(default_factory=SecurityConfig)

    # Monitoring configuration
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)


class ConfigurationManager:
    """Centralized configuration manager"""

    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file
        self.config: NetSentinelConfig = NetSentinelConfig()
        self._lock = threading.RLock()
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from multiple sources"""
        with self._lock:
            # Load from file if provided
            if self.config_file and Path(self.config_file).exists():
                self._load_from_file(self.config_file)

            # Load from environment variables
            self._load_from_environment()

            # Validate configuration
            self._validate_config()

            logger.info("Configuration loaded successfully")

    def _load_from_file(self, config_file: str) -> None:
        """Load configuration from file"""
        try:
            with open(config_file, "r") as f:
                if config_file.endswith(".yaml") or config_file.endswith(".yml"):
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)

                self._merge_config(data)
                logger.info(f"Configuration loaded from {config_file}")

        except Exception as e:
            logger.error(f"Failed to load configuration from {config_file}: {e}")

    def _load_from_environment(self) -> None:
        """Load configuration from environment variables"""
        # Core settings
        self.config.debug = (
            os.getenv("NETSENTINEL_DEBUG", str(self.config.debug)).lower() == "true"
        )
        self.config.log_level = os.getenv(
            "NETSENTINEL_LOG_LEVEL", self.config.log_level
        ).upper()
        self.config.max_workers = int(
            os.getenv("NETSENTINEL_MAX_WORKERS", str(self.config.max_workers))
        )

        # Kafka configuration
        kafka_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.config.kafka.bootstrap_servers = kafka_servers.split(",")
        self.config.kafka.topic_prefix = os.getenv(
            "KAFKA_TOPIC_PREFIX", self.config.kafka.topic_prefix
        )
        self.config.kafka.group_id = os.getenv(
            "KAFKA_GROUP_ID", self.config.kafka.group_id
        )

        # Redis configuration
        self.config.redis.host = os.getenv("REDIS_HOST", self.config.redis.host)
        self.config.redis.port = int(
            os.getenv("REDIS_PORT", str(self.config.redis.port))
        )
        self.config.redis.password = os.getenv(
            "REDIS_PASSWORD", self.config.redis.password
        )
        self.config.redis.db = int(os.getenv("REDIS_DB", str(self.config.redis.db)))

        # Elasticsearch configuration
        self.config.elasticsearch.host = os.getenv(
            "ELASTICSEARCH_HOST", self.config.elasticsearch.host
        )
        self.config.elasticsearch.port = int(
            os.getenv("ELASTICSEARCH_PORT", str(self.config.elasticsearch.port))
        )
        self.config.elasticsearch.username = os.getenv(
            "ELASTICSEARCH_USERNAME", self.config.elasticsearch.username
        )
        self.config.elasticsearch.password = os.getenv(
            "ELASTICSEARCH_PASSWORD", self.config.elasticsearch.password
        )

        # InfluxDB configuration
        self.config.influxdb.host = os.getenv(
            "INFLUXDB_HOST", self.config.influxdb.host
        )
        self.config.influxdb.port = int(
            os.getenv("INFLUXDB_PORT", str(self.config.influxdb.port))
        )
        self.config.influxdb.username = os.getenv(
            "INFLUXDB_USERNAME", self.config.influxdb.username
        )
        self.config.influxdb.password = os.getenv(
            "INFLUXDB_PASSWORD", self.config.influxdb.password
        )

        # Security configuration
        self.config.security.encryption_enabled = (
            os.getenv(
                "ENCRYPTION_ENABLED", str(self.config.security.encryption_enabled)
            ).lower()
            == "true"
        )
        self.config.security.jwt_secret = os.getenv(
            "JWT_SECRET", self.config.security.jwt_secret
        )
        self.config.security.rate_limit_requests = int(
            os.getenv(
                "RATE_LIMIT_REQUESTS", str(self.config.security.rate_limit_requests)
            )
        )

        # Monitoring configuration
        self.config.monitoring.prometheus_enabled = (
            os.getenv(
                "PROMETHEUS_ENABLED", str(self.config.monitoring.prometheus_enabled)
            ).lower()
            == "true"
        )
        self.config.monitoring.prometheus_port = int(
            os.getenv("PROMETHEUS_PORT", str(self.config.monitoring.prometheus_port))
        )

        logger.info("Configuration loaded from environment variables")

    def _merge_config(self, data: Dict[str, Any]) -> None:
        """Merge configuration data"""

        # Implement deep merging of configuration data
        def deep_merge(target: Any, source: Any) -> Any:
            if isinstance(target, dict) and isinstance(source, dict):
                for key, value in source.items():
                    if (
                        key in target
                        and isinstance(target[key], dict)
                        and isinstance(value, dict)
                    ):
                        deep_merge(target[key], value)
                    else:
                        target[key] = value
                return target
            return source

        # Convert config to dict for merging
        config_dict = self._config_to_dict(self.config)
        merged_config = deep_merge(config_dict, data)

        # Update config attributes
        for key, value in merged_config.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

    def _validate_config(self) -> None:
        """Validate configuration"""
        # Validate required settings
        if not self.config.kafka.bootstrap_servers:
            raise ValueError("Kafka bootstrap servers must be configured")

        if not self.config.redis.host:
            raise ValueError("Redis host must be configured")

        # Validate security settings
        if (
            self.config.security.encryption_enabled
            and not self.config.security.jwt_secret
        ):
            logger.warning("Encryption enabled but JWT secret not configured")

        logger.info("Configuration validation completed")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key"""
        with self._lock:
            keys = key.split(".")
            value = self.config

            for k in keys:
                if hasattr(value, k):
                    value = getattr(value, k)
                else:
                    return default

            return value

    def set(self, key: str, value: Any) -> None:
        """Set configuration value by key"""
        with self._lock:
            keys = key.split(".")
            config = self.config

            for k in keys[:-1]:
                if hasattr(config, k):
                    config = getattr(config, k)
                else:
                    return

            setattr(config, keys[-1], value)
            logger.info(f"Configuration updated: {key} = {value}")

    def get_database_config(self, database_type: str) -> DatabaseConfig:
        """Get database configuration by type"""
        with self._lock:
            if database_type.lower() == "elasticsearch":
                return self.config.elasticsearch
            elif database_type.lower() == "influxdb":
                return self.config.influxdb
            else:
                raise ValueError(f"Unknown database type: {database_type}")

    def get_kafka_config(self) -> KafkaConfig:
        """Get Kafka configuration"""
        with self._lock:
            return self.config.kafka

    def get_redis_config(self) -> RedisConfig:
        """Get Redis configuration"""
        with self._lock:
            return self.config.redis

    def get_security_config(self) -> SecurityConfig:
        """Get security configuration"""
        with self._lock:
            return self.config.security

    def get_monitoring_config(self) -> MonitoringConfig:
        """Get monitoring configuration"""
        with self._lock:
            return self.config.monitoring

    def reload(self) -> None:
        """Reload configuration"""
        self._load_config()
        logger.info("Configuration reloaded")

    def export_config(self, file_path: str) -> None:
        """Export configuration to file"""
        with self._lock:
            config_dict = self._config_to_dict(self.config)

            with open(file_path, "w") as f:
                if file_path.endswith(".yaml") or file_path.endswith(".yml"):
                    yaml.dump(config_dict, f, default_flow_style=False)
                else:
                    json.dump(config_dict, f, indent=2)

            logger.info(f"Configuration exported to {file_path}")

    def _config_to_dict(self, config: Any) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        if hasattr(config, "__dict__"):
            result = {}
            for key, value in config.__dict__.items():
                if not key.startswith("_"):
                    result[key] = self._config_to_dict(value)
            return result
        else:
            return config


# Global configuration manager
_config_manager: Optional[ConfigurationManager] = None


def get_config_manager(config_file: Optional[str] = None) -> ConfigurationManager:
    """Get global configuration manager"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigurationManager(config_file)
    return _config_manager


def get_config(key: str, default: Any = None) -> Any:
    """Get configuration value"""
    return get_config_manager().get(key, default)


def set_config(key: str, value: Any) -> None:
    """Set configuration value"""
    get_config_manager().set(key, value)
