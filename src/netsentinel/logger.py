#!/usr/bin/env python3
"""
Logger module for NetSentinel - backwards compatibility with OpenCanary
"""

import logging
from typing import Any, Dict, Optional
from .monitoring.logger import NetSentinelLogger


class OpenCanaryLogger:
    """OpenCanary-compatible logger interface"""

    def __init__(self, config=None):
        self.config = config
        self._internal_logger = NetSentinelLogger("netsentinel")
        self._std_logger = logging.getLogger("netsentinel")

    def log(self, data: Dict[str, Any], retry: bool = True):
        """Log data in OpenCanary format"""
        try:
            # Extract logdata from the nested structure
            if "logdata" in data:
                logdata = data["logdata"]
                if isinstance(logdata, dict):
                    # Convert to structured log
                    level = logdata.get("level", "INFO").upper()
                    message = logdata.get("msg", str(logdata))

                    # Log with appropriate level
                    if level == "ERROR":
                        self._std_logger.error(message)
                    elif level == "WARNING":
                        self._std_logger.warning(message)
                    elif level == "DEBUG":
                        self._std_logger.debug(message)
                    else:
                        self._std_logger.info(message)
                else:
                    # Simple string message
                    self._std_logger.info(str(logdata))
            else:
                # Log the entire data structure
                self._internal_logger.log("INFO", "OpenCanary log", extra=data)
        except Exception as e:
            # Fallback to basic logging
            print(f"Logging error: {e}, data: {data}")


def getLogger(config=None) -> OpenCanaryLogger:
    """Factory function for OpenCanary-compatible logger"""
    return OpenCanaryLogger(config)


__all__ = ['getLogger', 'OpenCanaryLogger']
