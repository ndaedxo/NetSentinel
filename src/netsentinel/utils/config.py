#!/usr/bin/env python3
"""
Configuration utilities for NetSentinel
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, asdict
import logging

from .constants import DEFAULT_CONFIG_FILE, DEFAULT_TIMEOUT, DEFAULT_RETRY_ATTEMPTS

logger = logging.getLogger(__name__)


@dataclass
class ConfigSchema:
    """Configuration schema definition"""

    required_fields: List[str]
    optional_fields: Dict[str, Any]
    validators: Dict[str, callable]


class ConfigManager:
    """Centralized configuration management"""

    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or DEFAULT_CONFIG_FILE
        self.config: Dict[str, Any] = {}
        self.schema: Optional[ConfigSchema] = None
        self._loaded = False

    def load_config(self, config_file: Optional[str] = None) -> Dict[str, Any]:
        """Load configuration from file"""
        config_file = config_file or self.config_file

        # Try multiple locations for config file
        config_paths = [
            config_file,
            os.path.join("/etc/netsentinel", config_file),
            os.path.join(os.path.expanduser("~"), f".{config_file}"),
            os.path.join(os.getcwd(), config_file),
        ]

        for path in config_paths:
            if os.path.exists(path):
                try:
                    with open(path, "r") as f:
                        self.config = json.load(f)
                    self._loaded = True
                    logger.info(f"Loaded configuration from: {path}")
                    return self.config
                except (json.JSONDecodeError, IOError) as e:
                    logger.error(f"Failed to load config from {path}: {e}")
                    continue

        # If no config file found, use defaults
        logger.warning("No configuration file found, using defaults")
        self.config = self._get_default_config()
        self._loaded = True
        return self.config

    def save_config(self, config_file: Optional[str] = None) -> bool:
        """Save configuration to file"""
        config_file = config_file or self.config_file

        try:
            # Create directory if it doesn't exist
            config_dir = os.path.dirname(config_file)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)

            with open(config_file, "w") as f:
                json.dump(self.config, f, indent=2, sort_keys=True)

            logger.info(f"Saved configuration to: {config_file}")
            return True
        except IOError as e:
            logger.error(f"Failed to save config to {config_file}: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key"""
        keys = key.split(".")
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> bool:
        """Set configuration value by key"""
        keys = key.split(".")
        config = self.config

        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        # Set the value
        config[keys[-1]] = value
        return True

    def validate_config(self) -> List[str]:
        """Validate configuration against schema"""
        errors = []

        if not self.schema:
            return errors

        # Check required fields
        for field in self.schema.required_fields:
            if not self._has_key(field):
                errors.append(f"Missing required field: {field}")

        # Validate optional fields
        for field, validator in self.schema.validators.items():
            if self._has_key(field):
                value = self.get(field)
                if not validator(value):
                    errors.append(f"Invalid value for field {field}: {value}")

        return errors

    def _has_key(self, key: str) -> bool:
        """Check if configuration key exists"""
        keys = key.split(".")
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return False

        return True

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "server": {
                "host": "0.0.0.0",
                "port": 8080,
                "timeout": DEFAULT_TIMEOUT,
                "retry_attempts": DEFAULT_RETRY_ATTEMPTS,
            },
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "netsentinel",
                "timeout": DEFAULT_TIMEOUT,
            },
            "logging": {
                "level": "INFO",
                "file": "netsentinel.log",
                "max_size": 10485760,  # 10MB
                "backup_count": 5,
            },
            "security": {
                "encryption_key": "",
                "jwt_secret": "",
                "session_timeout": 3600,
            },
            "monitoring": {
                "enabled": True,
                "metrics_interval": 60,
                "health_check_interval": 30,
            },
        }

    def set_schema(self, schema: ConfigSchema):
        """Set configuration schema"""
        self.schema = schema

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return self.config.copy()

    def update(self, config: Dict[str, Any]):
        """Update configuration with new values"""
        self.config.update(config)


def load_config(config_file: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from file"""
    manager = ConfigManager(config_file)
    return manager.load_config()


def validate_config(
    config: Dict[str, Any], schema: Optional[ConfigSchema] = None
) -> List[str]:
    """Validate configuration"""
    manager = ConfigManager()
    manager.config = config
    if schema:
        manager.set_schema(schema)
    return manager.validate_config()


def create_config_schema() -> ConfigSchema:
    """Create default configuration schema"""
    return ConfigSchema(
        required_fields=[
            "server.host",
            "server.port",
            "database.host",
            "database.port",
            "database.name",
        ],
        optional_fields={
            "server.timeout": DEFAULT_TIMEOUT,
            "server.retry_attempts": DEFAULT_RETRY_ATTEMPTS,
            "logging.level": "INFO",
            "security.encryption_key": "",
            "monitoring.enabled": True,
        },
        validators={
            "server.port": lambda x: isinstance(x, int) and 1 <= x <= 65535,
            "server.timeout": lambda x: isinstance(x, (int, float)) and x > 0,
            "server.retry_attempts": lambda x: isinstance(x, int) and 0 <= x <= 10,
            "logging.level": lambda x: x
            in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            "monitoring.enabled": lambda x: isinstance(x, bool),
        },
    )


def merge_configs(
    base_config: Dict[str, Any], override_config: Dict[str, Any]
) -> Dict[str, Any]:
    """Merge two configurations, with override_config taking precedence"""
    merged = base_config.copy()

    for key, value in override_config.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = merge_configs(merged[key], value)
        else:
            merged[key] = value

    return merged


def expand_env_vars(config: Dict[str, Any]) -> Dict[str, Any]:
    """Expand environment variables in configuration"""
    expanded = {}

    for key, value in config.items():
        if isinstance(value, dict):
            expanded[key] = expand_env_vars(value)
        elif isinstance(value, str):
            expanded[key] = os.path.expandvars(value)
        else:
            expanded[key] = value

    return expanded


def get_config_value(config: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Get configuration value by dotted key"""
    keys = key.split(".")
    value = config

    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default

    return value


def set_config_value(config: Dict[str, Any], key: str, value: Any) -> bool:
    """Set configuration value by dotted key"""
    keys = key.split(".")
    current = config

    # Navigate to the parent of the target key
    for k in keys[:-1]:
        if k not in current:
            current[k] = {}
        current = current[k]

    # Set the value
    current[keys[-1]] = value
    return True


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get the global configuration manager"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
        _config_manager.load_config()
    return _config_manager
