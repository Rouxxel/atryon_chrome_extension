"""
#############################################################################
### Download generated image by URL (from polling result)
###
### @file download_requests.py
### @author Sebastian Russo
### @date 2025
#############################################################################

This module defines an endpoint to download the finished image using the signed
URL returned in result['sample'] from the polling endpoint.
"""

#Third-party imports
import requests
from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import Response

#Other files imports
from src.utils.custom_logger import log_handler
from src.utils.limiter import limiter as SlowLimiter
from src.utils.validators import is_url
from src.core_specs.configuration.config_loader import config_loader

"""API ROUTER-----------------------------------------------------------"""
router = APIRouter(
    prefix=config_loader['endpoints']['download_requests_endpoint']['endpoint_prefix'],
    tags=[config_loader['endpoints']['download_requests_endpoint']['endpoint_tag']],
)

"""ENDPOINT-----------------------------------------------------------"""
# Download image from signed URL (result['sample'] from polling)
@router.get(config_loader['endpoints']['download_requests_endpoint']['endpoint_route'])
@SlowLimiter.limit(
    f"{config_loader['endpoints']['download_requests_endpoint']['request_limit']}/"
    f"{config_loader['endpoints']['download_requests_endpoint']['unit_of_time_for_limit']}"
)
async def download_requests(
    request: Request,
    url: str = Query(..., description="Signed image URL from polling result (result['sample'])"),
):
    """
    Download the generated image from the given signed URL.

    The URL should be the signed URL obtained from the polling response
    (result['sample']). Returns the image bytes with appropriate Content-Type
    for display or save.

    Parameters:
        request (Request): The incoming HTTP request for limit event management.
        url (str): The signed image URL from the BFL polling result.

    Returns:
        Response: Image bytes with Content-Type set (e.g. image/jpeg).

    Note:
        If the rate limit is exceeded, the rate_limit_handler() function handles the response.
    """
    #Validate image URL
    if not is_url(url):
        raise HTTPException(status_code=400, detail="Invalid image URL.")

    log_handler.debug("Downloading image from provided URL")

    #Download image from signed URL
    try:
        resp = requests.get(url, timeout=60, stream=True)
    except requests.RequestException as e:
        log_handler.error(f"Image download failed: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch image from URL.")

    if resp.status_code != 200:
        log_handler.warning(f"Image URL returned {resp.status_code}")
        raise HTTPException(status_code=502, detail=f"Image URL returned {resp.status_code}.")

    content_type = resp.headers.get("Content-Type", "image/jpeg")
    log_handler.info("Image downloaded successfully")
    return Response(content=resp.content, media_type=content_type)
