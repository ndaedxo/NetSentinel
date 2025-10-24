#!/usr/bin/env python3
"""
NetSentinel Utilities Package
Centralized utility functions and helpers
"""

# Import all utility modules
from .centralized import (
    create_logger,
    generate_id,
    hash_data,
    serialize_data,
    deserialize_data,
    retry_with_backoff,
    handle_errors_simple as handle_errors,
    create_error_context_simple as create_error_context,
    load_config,
    validate_config,
    create_connection_pool,
    measure_time,
    create_timer,
    create_cache,
    validate_event,
    validate_alert,
    validate_ip_address,
    deep_merge,
    generate_hmac,
    verify_hmac,
    encode_base64,
    decode_base64,
    run_async,
    create_async_pool,
    create_webhook_payload,
    validate_webhook_signature,
    create_mock_data,
    assert_equals,
)
from .consolidated_cleanup import ConsolidatedCleanupUtility
from .registry import UtilityRegistry, register_utility, UtilityCategory, get_registry

# Import specific utilities
try:
    from .constants import (
        DEFAULT_TIMEOUT,
        DEFAULT_RETRY_ATTEMPTS,
        MAX_CONNECTIONS,
        LOG_LEVELS,
        DEFAULT_CONFIG_FILE,
        DEFAULT_PORT,
    )
    from .validation import (
        validate_domain,
        validate_url,
        validate_port,
        validate_timeout,
        validate_config_value,
        ValidationResult,
    )
except ImportError as e:
    # Fallback for missing modules
    import logging

    logger = logging.getLogger(__name__)
    logger.warning(f"Failed to import some utility modules: {e}")
    pass

__all__ = [
    "ConsolidatedCleanupUtility",
    "UtilityRegistry",
    "register_utility",
    "UtilityCategory",
    "get_registry",
    "ValidationResult",
    "load_config",
    "validate_config",
    "create_connection_pool",
    "validate_ip_address",
    "validate_domain",
    "validate_url",
    "validate_port",
    "validate_timeout",
    "validate_config_value",
    "create_logger",
    "generate_id",
    "hash_data",
    "serialize_data",
    "deserialize_data",
    "retry_with_backoff",
    "handle_errors",
    "create_error_context",
    "measure_time",
    "create_timer",
    "create_cache",
    "validate_event",
    "validate_alert",
    "deep_merge",
    "generate_hmac",
    "verify_hmac",
    "encode_base64",
    "decode_base64",
    "run_async",
    "create_async_pool",
    "create_webhook_payload",
    "validate_webhook_signature",
    "create_mock_data",
    "assert_equals",
]
