"""
#############################################################################
### Root endpoint file
###
### @file root_endpoint.py
### @Sebastian Russo
### @date: 2025
#############################################################################

This module contains an endpoint that simply returns a dictionary confirming
the backend is up and running correctly. It serves as a health check and
does not perform any other operation.
"""

#Third-party imports
from fastapi import APIRouter, Request

#Other files imports
from src.utils.custom_logger import log_handler
from src.utils.limiter import limiter as SlowLimiter
from src.core_specs.configuration.config_loader import config_loader

"""API ROUTER-----------------------------------------------------------"""
# Get API router
router = APIRouter(
    prefix=config_loader['endpoints']['root_directory_endpoint']['endpoint_prefix'],
    tags=[config_loader['endpoints']['root_directory_endpoint']['endpoint_tag']],
)

"""ENDPOINT-----------------------------------------------------------"""
# Check if app works
@router.get(config_loader['endpoints']['root_directory_endpoint']['endpoint_route'])
@SlowLimiter.limit(
    f"{config_loader['endpoints']['root_directory_endpoint']['request_limit']}/"
    f"{config_loader['endpoints']['root_directory_endpoint']['unit_of_time_for_limit']}"
)  # Root endpoint rate limit
async def root_endpoint(request: Request):
    """
    Root endpoint to verify that the API is operational.

    This endpoint serves as a basic health check and confirms that the application
    is running correctly. It is rate-limited according to the configuration.

    Parameters:
        request (Request): The incoming HTTP request for limit event management.

    Returns:
        dict: A JSON response indicating that the API is running.
    
    Note:
        If the rate limit is exceeded, the rate_limit_handler() function handles the response.
    """
    log_handler.debug("Backend running successfully")
    return {"message": "Backend running successfully, ready to use other endpoints"}
