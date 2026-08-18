"""
#############################################################################
### Startup configuration validator
###
### @file startup_validator.py
### @date 2025
#############################################################################

This module performs fail-fast configuration validation at server boot.
It checks that all critical security configuration is present and valid
before the server begins serving traffic.
"""

# Native imports
import os

# Other files imports
from src.utils.custom_logger import log_handler
from src.core_specs.configuration.config_loader import config_loader
from src.core_specs.data.data_loader import data_loader


def validate_startup_config() -> None:
    """
    Validate critical startup configuration.

    Checks:
        - BFL_API_KEY environment variable is set and non-empty
        - allowed_polling_hosts list is non-empty in data config
        - allowed_download_hosts list is non-empty in data config
        - All endpoint rate limits are positive integers

    Collects all errors and logs each at CRITICAL level before raising
    SystemExit if any errors are found. Returns normally if all checks pass.
    """
    errors: list[str] = []

    # Check BFL_API_KEY environment variable
    api_key_env_name = data_loader["image_ai_providers"]["black_forest"]["api_key_env"]
    api_key_value = os.environ.get(api_key_env_name, "")
    if not api_key_value or not api_key_value.strip():
        errors.append(
            f"Environment variable '{api_key_env_name}' is not set or is empty"
        )

    # Check allowed_polling_hosts
    bfl_config = data_loader["image_ai_providers"]["black_forest"]
    polling_hosts = bfl_config.get("allowed_polling_hosts", [])
    if not polling_hosts:
        errors.append(
            "Configuration 'allowed_polling_hosts' is empty or not defined"
        )

    # Check allowed_download_hosts
    download_hosts = bfl_config.get("allowed_download_hosts", [])
    if not download_hosts:
        errors.append(
            "Configuration 'allowed_download_hosts' is empty or not defined"
        )

    # Check all endpoint rate limits are positive integers
    endpoints = config_loader.get("endpoints", {})
    for endpoint_name, endpoint_config in endpoints.items():
        rate_limit = endpoint_config.get("request_limit")
        if not isinstance(rate_limit, int) or rate_limit <= 0:
            errors.append(
                f"Endpoint '{endpoint_name}' has invalid rate limit: "
                f"{rate_limit!r} (must be a positive integer)"
            )

    # If errors found, log each at CRITICAL and raise SystemExit
    if errors:
        for error in errors:
            log_handler.critical("[startup_validator] %s", error)
        raise SystemExit(
            f"Startup validation failed with {len(errors)} error(s)"
        )
