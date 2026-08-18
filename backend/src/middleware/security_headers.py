"""
#############################################################################
### Security headers middleware
###
### @file security_headers.py
### @author Sebastian Russo
### @date 2025
#############################################################################

This module provides an ASGI middleware that injects security response headers
on every HTTP response (including error responses), attaches a per-request
correlation identifier, and removes the ``Server`` header to prevent version
disclosure.

Non-HTTP scopes (websocket, lifespan) are passed through unmodified.
"""

# Native imports
import uuid

# Third-party imports
from starlette.datastructures import MutableHeaders

# Other files imports
from src.utils.custom_logger import log_handler

# Static security headers injected on every HTTP response.
# Requirements 1.1 - 1.5. These values overwrite any pre-existing values set
# by downstream handlers (Requirement 1.9).
SECURITY_HEADERS = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "strict-origin-when-cross-origin",
    "permissions-policy": "camera=(), microphone=(), geolocation=()",
    "cache-control": "no-store",
}


class SecurityHeadersMiddleware:
    """ASGI middleware that injects security headers on all HTTP responses.

    The middleware intercepts the ``http.response.start`` ASGI message and
    mutates its headers before the response is sent to the client. Each request
    is assigned a fresh UUID v4 exposed via the ``X-Request-ID`` header.
    """

    def __init__(self, app):
        """Store the wrapped ASGI application."""
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        """Intercept the response and inject security headers.

        Non-HTTP scopes (e.g. ``websocket``, ``lifespan``) are forwarded to the
        wrapped application without modification (Requirement 1.8).
        """
        # Pass through non-HTTP scopes unmodified (Requirement 1.8).
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Generate a distinct UUID v4 per request/response (Requirement 1.6).
        request_id = str(uuid.uuid4())

        async def send_with_security_headers(message) -> None:
            if message["type"] == "http.response.start":
                try:
                    headers = MutableHeaders(scope=message)

                    # Inject/overwrite static security headers
                    # (Requirements 1.1 - 1.5, 1.9).
                    for header_name, header_value in SECURITY_HEADERS.items():
                        headers[header_name] = header_value

                    # Inject the per-request correlation id (Requirement 1.6).
                    headers["x-request-id"] = request_id

                    # Remove the Server header to avoid version disclosure
                    # (Requirement 1.7).
                    if "server" in headers:
                        del headers["server"]
                except Exception as exc:  # noqa: BLE001
                    # If header injection fails, allow the response to proceed
                    # without the failed header and log the error
                    # (Requirement 1.10).
                    log_handler.error(
                        "[security_headers] Failed to inject security headers: %s",
                        type(exc).__name__,
                    )

            await send(message)

        await self.app(scope, receive, send_with_security_headers)
