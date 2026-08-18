"""
#############################################################################
### CORS Configuration
###
### @file cors_config.py
### @date 2025
#############################################################################

This module configures CORS middleware with a strict origin allowlist.
Only known extension and development origins are permitted.
"""

# Native imports
import os

# Third-party imports
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Other files imports
from src.utils.custom_logger import log_handler

# Default origins used when CORS_ORIGINS env var is empty or unset
_DEFAULT_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]


def _parse_origins() -> list[str]:
    """Parse the CORS_ORIGINS environment variable as a comma-separated list.

    Returns the configured origins or falls back to default development origins
    when the environment variable is empty or unset.
    """
    raw = os.environ.get("CORS_ORIGINS", "").strip()
    if not raw:
        return list(_DEFAULT_ORIGINS)

    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    if not origins:
        return list(_DEFAULT_ORIGINS)

    return origins


def configure_cors(app: FastAPI) -> None:
    """Apply CORSMiddleware with strict origin allowlist.

    Parses allowed origins from the CORS_ORIGINS environment variable,
    restricts methods to GET/POST/OPTIONS, limits headers to Content-Type
    and X-Request-ID, disables credentials, and sets preflight cache to 600s.
    """
    origins = _parse_origins()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-Request-ID"],
        allow_credentials=False,
        max_age=600,
    )

    log_handler.info(f"[cors_config] CORS configured with origins: {origins}")
