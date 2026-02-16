"""
#############################################################################
### Poll Black Forest task status (multi-image composition)
###
### @file polling_requests.py
### @author Sebastian Russo
### @date 2025
#############################################################################

This module defines an endpoint to poll a Black Forest Labs (BFL) task by its
polling_url. A successful response is the full JSON; result['sample'] is the
signed URL for the generated image.
"""

#Native imports
import os

#Third-party imports
import requests
from fastapi import APIRouter, Request, HTTPException, Query

#Other files imports
from src.utils.custom_logger import log_handler
from src.utils.limiter import limiter as SlowLimiter
from src.utils.validators import is_url
from src.core_specs.configuration.config_loader import config_loader
from src.core_specs.data.data_loader import data_loader

"""VARIABLES-----------------------------------------------------------"""
#Black Forest provider data (for API key env key)
BF_CFG = data_loader["image_ai_providers"]["black_forest"]


def _get_bfl_headers() -> dict:
    """Build BFL API headers (x-key from environment)."""
    api_key = os.getenv(BF_CFG["api_key_env"])
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Black Forest API key not configured."
        )
    return {"x-key": api_key}


"""API ROUTER-----------------------------------------------------------"""
router = APIRouter(
    prefix=config_loader['endpoints']['polling_requests_endpoint']['endpoint_prefix'],
    tags=[config_loader['endpoints']['polling_requests_endpoint']['endpoint_tag']],
)

"""ENDPOINT-----------------------------------------------------------"""
# Poll BFL task status by polling_url
@router.get(config_loader['endpoints']['polling_requests_endpoint']['endpoint_route'])
@SlowLimiter.limit(
    f"{config_loader['endpoints']['polling_requests_endpoint']['request_limit']}/"
    f"{config_loader['endpoints']['polling_requests_endpoint']['unit_of_time_for_limit']}"
)
async def polling_requests(
    request: Request,
    polling_url: str = Query(..., description="Polling URL returned from the submit MIC endpoint"),
):
    """
    Poll the Black Forest task status.

    This endpoint calls the BFL polling URL and returns the full JSON response.
    When status is Ready, result['sample'] contains the signed URL to retrieve
    the generated image (string or list of URLs).

    Parameters:
        request (Request): The incoming HTTP request for limit event management.
        polling_url (str): The polling URL returned from the submit MIC endpoint.

    Returns:
        dict: Full BFL task response (status, result with 'sample' when Ready).

    Note:
        If the rate limit is exceeded, the rate_limit_handler() function handles the response.
    """
    #Validate polling URL
    if not is_url(polling_url):
        raise HTTPException(status_code=400, detail="Invalid polling URL.")

    log_handler.debug("Polling BFL task")

    #Poll BFL task status
    try:
        resp = requests.get(polling_url, headers=_get_bfl_headers(), timeout=30)
    except requests.RequestException as e:
        log_handler.error(f"BFL poll request failed: {e}")
        raise HTTPException(status_code=502, detail="Failed to reach Black Forest API.")

    if resp.status_code != 200:
        log_handler.warning(f"BFL poll returned {resp.status_code}: {resp.text}")
        raise HTTPException(status_code=502, detail=f"Black Forest API error: {resp.status_code}")

    data = resp.json()
    log_handler.debug(f"Poll result status: {data.get('status')}")
    return data
