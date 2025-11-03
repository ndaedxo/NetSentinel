import os
import sys
import json
import itertools
import string
import re
from os.path import expanduser
from typing import Any, List, Dict, Optional
from pathlib import Path
import importlib.resources


def resource_filename(package: str, resource: str) -> str:
    """Get resource filename using importlib.resources (modern approach)"""
    return str(importlib.resources.files(package) / resource)


SAMPLE_SETTINGS = resource_filename("netsentinel", "data/settings.json")
SETTINGS = "netsentinel.conf"


def expand_vars(var: Any) -> Any:
    """Recursively replace environment variables in a dictionary, list or string with their respective values."""
    if isinstance(var, dict):
        for key, value in var.items():
            var[key] = expand_vars(value)
        return var
    if isinstance(var, (list, set, tuple)):
        return [expand_vars(v) for v in var]
    if isinstance(var, (str, bytes)):
        return os.path.expandvars(var)
    return var


def is_docker() -> bool:
    """Check if running inside a Docker container."""
    cgroup = Path("/proc/self/cgroup")
    return (
        Path("/.dockerenv").is_file()
        or cgroup.is_file()
        and "docker" in cgroup.read_text()
    )


SERVICE_REGEXES = {
    "ssh.version": (
        r"(SSH-(2.0|1.5|1.99|1.0)-([!-,\-./0-~]+(:?$|\s))(?:[ -~]*)){1,253}$"
    ),
}


class Config:
    """Configuration manager for NetSentinel."""

    def __init__(self, configfile: str = SETTINGS) -> None:
        self.__config: Optional[Dict[str, Any]] = None
        self.__configfile = configfile
        self._logger = None

        files = [
            f"/etc/netsentinel/{configfile}",
            f"{expanduser('~')}/.{configfile}",
            configfile,
        ]

        self._load_config_from_files(files)

    def _load_config_from_files(self, files: List[str]) -> None:
        """Load configuration from files with proper error handling"""
        import logging

        if self._logger is None:
            self._logger = logging.getLogger(__name__)

        self._logger.info(
            "Welcome to NetSentinel - AI-Powered Network Security Monitoring System"
        )

        for fname in files:
            try:
                with open(fname, "r", encoding="utf-8") as f:
                    self._logger.info(f"Using config file: {fname}")
                    self.__config = json.load(f)
                    self.__config = expand_vars(self.__config)

                if fname == self.__configfile:
                    self._logger.warning(
                        "Warning, making use of the configuration file in the immediate "
                        f"directory is not recommended! Suggested locations: {', '.join(files[:2])}"
                    )
                return

            except IOError as e:
                self._logger.error(f"Failed to open {fname} for reading ({e})")
            except ValueError as e:
                self._logger.error(f"Failed to decode json from {fname} ({e})")
            except Exception as e:
                self._logger.error(f"An error occurred loading {fname} ({e})")

        if self.__config is None:
            self._logger.error(
                'No config file found. Please create one with "netsentinel --copyconfig"'
            )
            self._load_default_config()

    def _load_default_config(self) -> None:
        """Load minimal default configuration for testing/development"""
        self.__config = {
            "device": {"name": "netsentinel", "desc": "NetSentinel System"},
            "ssh": {"enabled": True, "port": 2222},
            "http": {"enabled": True, "port": 8080},
            "https": {"enabled": True, "port": 8443},
        }
        if self._logger:
            self._logger.warning("Using minimal default configuration")

    def moduleEnabled(self, module_name: str) -> bool:
        """Check if a module is enabled."""
        if self.__config is None:
            return False

        k = f"{module_name.lower()}.enabled"
        return bool(self.__config.get(k, False))

    def getVal(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        if self.__config is None:
            return default

        try:
            return self.__config[key]
        except KeyError:
            if default is not None:
                return default
            raise KeyError(f"Configuration key '{key}' not found")

    def checkValues(self) -> List["ConfigException"]:
        """Validate all configuration values and return a list of errors for invalid ones"""
        if self.__config is None:
            return []

        errors = []

        # Test options independently for validity
        for key, value in self.__config.items():
            try:
                self.is_valid(key, value)
            except ConfigException as e:
                errors.append(e)

        # Test that no ports overlap
        port_conflicts = self._check_port_conflicts()
        errors.extend(port_conflicts)

        return errors

    def _check_port_conflicts(self) -> List["ConfigException"]:
        """Check for port conflicts between services"""
        if self.__config is None:
            return []

        errors = []
        ports = {}

        for key, value in self.__config.items():
            if key.endswith(".port") and isinstance(value, (int, str)):
                try:
                    port = int(value)
                    if port in ports:
                        services = [ports[port], key.split(".")[0]]
                        errmsg = f"More than one service uses port {port} ({', '.join(services)})"
                        errors.append(ConfigException(key, errmsg))
                    else:
                        ports[port] = key.split(".")[0]
                except ValueError:
                    errors.append(ConfigException(key, f"Invalid port number: {value}"))

        return errors

    def is_valid(self, key: str, val: Any) -> bool:
        """
        Test the validity of an individual setting
        Raise config error message on failure.
        Delegates module-specific validation to appropriate modules.
        """
        # Validate boolean settings
        if key.endswith(".enabled"):
            self._validate_boolean_setting(key, val)

        # Validate port settings
        if key.endswith(".port"):
            self._validate_port_setting(key, val)

        # Validate SSH version
        if key == "ssh.version":
            self._validate_ssh_version(key, val)

        # Validate device settings
        if key == "device.name":
            self._validate_device_name(key, val)

        if key == "device.desc":
            self._validate_device_description(key, val)

        # Validate service regexes
        if key in SERVICE_REGEXES.keys():
            self._validate_service_regex(key, val)

        # Delegate module-specific validation
        self._validate_module_specific(key, val)

        return True

    def _validate_boolean_setting(self, key: str, val: Any) -> None:
        """Validate boolean settings"""
        if not ((val is True) or (val is False)):
            raise ConfigException(
                key, "Boolean setting is not True or False (%s)" % val
            )

    def _validate_port_setting(self, key: str, val: Any) -> None:
        """Validate port settings"""
        if not isinstance(val, int):
            raise ConfigException(
                key, "Invalid port number (%s). Must be an integer." % val
            )
        if val < 1 or val > 65535:
            raise ConfigException(
                key, "Invalid port number (%s). Must be between 1 and 65535." % val
            )

    def _validate_ssh_version(self, key: str, val: Any) -> None:
        """Validate SSH version string"""
        # Max length of SSH version string is 255 chars including trailing CR and LF
        # https://tools.ietf.org/html/rfc4253
        if len(val) > 253:
            raise ConfigException(key, "SSH version string too long (%s..)" % val[:5])

    def _validate_device_name(self, key: str, val: Any) -> None:
        """Validate device name"""
        allowed_chars = string.ascii_letters + string.digits + "+-#_"

        if len(val) > 100:
            raise ConfigException(key, "Name cannot be longer than 100 characters")
        elif len(val) < 1:
            raise ConfigException(key, "Name ought to be at least one character")
        elif any(map(lambda x: x not in allowed_chars, val)):
            raise ConfigException(
                key,
                "Please use only characters, digits, any of the following: + - # _",
            )

    def _validate_device_description(self, key: str, val: Any) -> None:
        """Validate device description"""
        allowed_chars = string.ascii_letters + string.digits + "+-#_ "
        if len(val) > 100:
            raise ConfigException(key, "Name cannot be longer than 100 characters")
        elif len(val) < 1:
            raise ConfigException(key, "Name ought to be at least one character")
        elif any(map(lambda x: x not in allowed_chars, val)):
            raise ConfigException(
                key,
                "Please use only characters, digits, spaces and any of the following: + - # _",
            )

    def _validate_service_regex(self, key: str, val: Any) -> None:
        """Validate service regex patterns"""
        if not re.match(SERVICE_REGEXES[key], val):
            raise ConfigException(key, f"{val} is not valid.")

    def _validate_module_specific(self, key: str, val: Any) -> None:
        """
        Delegate module-specific validation to appropriate modules.
        This allows each module to define its own validation rules.
        """
        try:
            # Extract module name from key (e.g., "ssh.port" -> "ssh")
            if "." in key:
                module_name = key.split(".")[0]

                # Import and validate using module-specific validation if available
                if module_name in [
                    "ssh",
                    "http",
                    "https",
                    "ftp",
                    "mysql",
                    "telnet",
                    "rdp",
                    "vnc",
                    "redis",
                    "git",
                ]:
                    # Module-specific validation can be added here
                    # For now, we'll use the existing validation logic
                    pass

        except Exception as e:
            # If module-specific validation fails, log the error for debugging
            # but don't raise to ensure backward compatibility
            import logging

            logger = logging.getLogger(__name__)
            logger.debug(f"Module-specific validation failed for {key}: {e}")
            pass

    def __repr__(self) -> str:
        return self.__config.__repr__()

    def __str__(self) -> str:
        return self.__config.__str__()

    def toDict(self) -> Dict[str, Any]:
        """Return all settings as a dict"""
        return self.__config.copy()

    def toJSON(self) -> str:
        """
        JSON representation of config
        """
        return json.dumps(
            self.__config, sort_keys=True, indent=4, separators=(",", ": ")
        )


class ConfigException(Exception):
    """Exception raised on invalid config value"""

    def __init__(self, key: str, msg: str) -> None:
        self.key = key
        self.msg = msg

    def __str__(self) -> str:
        return "%s: %s" % (self.key, self.msg)

    def __repr__(self) -> str:
        return "<%s %s (%s)>" % (self.__class__.__name__, self.key, self.msg)


# Global config instance - lazy initialization
_config_instance: Optional[Config] = None


def get_config() -> Config:
    """Get the global config instance with lazy initialization"""
    global _config_instance
    if _config_instance is None:
        try:
            _config_instance = Config()
            errors = _config_instance.checkValues()
            if errors:
                import logging

                logger = logging.getLogger(__name__)
                for error in errors:
                    logger.error(str(error))
                # Use standard exception to avoid circular imports
                raise ValueError(
                    f"Configuration validation failed: {len(errors)} errors"
                )
        except Exception as e:
            # If config loading fails, create a minimal config for testing
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Config loading failed: {e}. Using minimal config.")
            _config_instance = Config.__new__(Config)
            _config_instance.__config = {
                "device": {"name": "netsentinel", "desc": "NetSentinel System"},
                "ssh": {"enabled": True, "port": 2222},
            }
    return _config_instance


def _is_test_mode() -> bool:
    """Check if running in test mode"""
    return any("pytest" in arg for arg in sys.argv) or any(
        "test" in arg for arg in sys.argv
    )


# Initialize config only if not in test mode
config: Optional[Config] = None

if not _is_test_mode():
    try:
        config = get_config()
    except Exception:
        # If initialization fails, leave config as None
        config = None
