"""
#############################################################################
### Main backend file
###
### @file main.py
### @author Sebastian Russo
### @date 2025
#############################################################################

This module initializes the FastAPI backend locally for development.
It sets up routers, custom logger, rate limiter, and loads environment variables.
"""

# Native imports
from contextlib import asynccontextmanager

# Third-party imports
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

load_dotenv()

# Other files imports
from src.api_endpoints.root_endpoint import router as root_router  # noqa: E402
from src.api_endpoints.routers.black_forest_api import router as black_forest_router  # noqa: E402
from src.api_endpoints.routers.upload_files import router as upload_files_router  # noqa: E402
from src.core_specs.configuration.config_loader import config_loader  # noqa: E402
from src.core_specs.data.data_loader import data_loader  # noqa: E402
from src.middleware.cors_config import configure_cors  # noqa: E402
from src.middleware.security_headers import SecurityHeadersMiddleware  # noqa: E402
from src.utils.custom_logger import log_handler  # noqa: E402
from src.utils.limiter import limiter  # noqa: E402
from src.utils.request_limiter import rate_limit_handler  # noqa: E402
from src.utils.startup_validator import validate_startup_config  # noqa: E402
from src.utils.upload_store import cleanup_expired  # noqa: E402

"""API APP-----------------------------------------------------------"""
# Lifespan event manager (startup and shutdown)
@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_startup_config()
    port = config_loader["network"]["server_port"]
    log_handler.info(f"[main] Atryon server starting on port {port}")
    removed = cleanup_expired()
    if removed:
        log_handler.info(f"[main] Cleaned up {removed} expired upload(s) on startup")
    yield
    log_handler.info("[main] Atryon server shutting down")

# Create FastAPI app
app = FastAPI(
    lifespan=lifespan,
    title=config_loader["defaults"]["api_title"],
    version=config_loader["defaults"]["api_version"],
    description=config_loader["defaults"]["api_description"],
)

"""VARIOUS-----------------------------------------------------------"""
# Setup rate limiter
app.state.limiter = limiter

# Add global exception handler for rate limits
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# Add global exception handler for unhandled exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions and return a generic 500 response.
    Logs exception details server-side without leaking internals to clients."""
    log_handler.error(
        f"[main] Unhandled exception on {request.method} {request.url.path}: "
        f"{type(exc).__name__}: {exc}"
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# CORS middleware (added before security headers so it is inner in the stack)
configure_cors(app)

# Security headers middleware (added last so it executes first — outermost in the stack)
app.add_middleware(SecurityHeadersMiddleware)

"""Routers-----------------------------------------------------------"""
# Root
app.include_router(root_router)
# Upload files (reusable for MIC, IDWM, etc.)
app.include_router(upload_files_router)
# Black Forest API (multi-image composition)
app.include_router(black_forest_router)

# Others

"""Start server-----------------------------------------------------------"""
if __name__ == "__main__":
    port = config_loader["network"]["server_port"]
    uvicorn.run(
        config_loader["network"]["uvicorn_app_reference"],
        host=config_loader["network"]["host"],
        port=config_loader["network"]["server_port"],
        reload=config_loader["network"]["reload"],
        workers=config_loader["network"]["workers"],
        proxy_headers=config_loader["network"]["proxy_headers"],
    )

    log_handler.info(f"[main] Loaded configuration: \n {config_loader['defaults']}")
    log_handler.info(f"[main] Loaded data: \n {data_loader['metadata']}")
    # available at: http://127.0.0.1:8000/docs
