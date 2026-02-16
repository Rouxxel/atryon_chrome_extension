"""
#############################################################################
### Submit Text-to-Image (TTI) request to Black Forest API
###
### @file submit_tti.py
### @author Sebastian Russo
### @date 2025
#############################################################################

This module exposes a POST endpoint to submit a FLUX.2 text-to-image generation
request to Black Forest Labs (BFL). It returns the polling_url for the client
to poll until the task is ready. Polling and download use the same endpoints
as multi-image composition (polling_requests, download_requests).
"""

#Native imports
import os
from typing import Optional

#Third-party imports
import requests
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field

#Other files imports
from src.utils.custom_logger import log_handler
from src.utils.limiter import limiter as SlowLimiter
from src.core_specs.configuration.config_loader import config_loader
from src.core_specs.data.data_loader import data_loader

"""VARIABLES-----------------------------------------------------------"""
#Black Forest provider data (model, dimensions, prompt prefix, etc.)
BF_CFG = data_loader["image_ai_providers"]["black_forest"]


def _get_bfl_headers() -> dict:
    """Build BFL API headers (x-key from environment)."""
    api_key = os.getenv(BF_CFG["api_key_env"])
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Black Forest API key not configured. Set the environment variable."
        )
    return {"x-key": api_key, "Content-Type": "application/json"}


def _build_full_prompt_tti(user_prompt: str) -> str:
    """Prepend default text-to-image prompt prefix from data config if set."""
    prefix = BF_CFG.get("flux2", {}).get("default_prompt_prefix_tti") or ""
    return f"{prefix}{user_prompt}".strip()


class SubmitTtiBody(BaseModel):
    """Request body: text prompt and optional dimensions."""

    prompt: str = Field(..., min_length=1, description="Text prompt describing the desired image (subject, scene, style)")
    width: Optional[int] = Field(None, description="Output width in pixels (default from config)")
    height: Optional[int] = Field(None, description="Output height in pixels (default from config)")


"""API ROUTER-----------------------------------------------------------"""
router = APIRouter(
    prefix=config_loader['endpoints']['tti_endpoint']['endpoint_prefix'],
    tags=[config_loader['endpoints']['tti_endpoint']['endpoint_tag']],
)

"""ENDPOINT-----------------------------------------------------------"""
# Submit text-to-image generation job to BFL FLUX.2
@router.post(config_loader['endpoints']['tti_endpoint']['endpoint_route'])
@SlowLimiter.limit(
    f"{config_loader['endpoints']['tti_endpoint']['request_limit']}/"
    f"{config_loader['endpoints']['tti_endpoint']['unit_of_time_for_limit']}"
)
async def submit_tti(request: Request, body: SubmitTtiBody):
    """
    Submit a text-to-image generation job to Black Forest FLUX.2.

    This endpoint sends the user prompt to the BFL API and returns a polling_url.
    The client should poll that URL until status is Ready (same polling endpoint
    as multi-image composition), then use result['sample'] as the signed image
    URL or call the download endpoint.

    Parameters:
        request (Request): The incoming HTTP request for limit event management.
        body (SubmitTtiBody): JSON body with 'prompt' (str) and optional 'width', 'height'.

    Returns:
        dict: Contains 'polling_url' (str) to poll for task status.

    Note:
        If the rate limit is exceeded, the rate_limit_handler() function handles the response.
    """
    log_handler.debug("Submit TTI request received")

    #Build full prompt with optional TTI prefix from data config
    full_prompt = _build_full_prompt_tti(body.prompt)

    #Build BFL request URL and payload (no input_image for text-to-image)
    flux2 = BF_CFG.get("flux2", {})
    base_url = os.getenv(BF_CFG["base_url_env"]) or BF_CFG["base_url_default"]
    model = flux2.get("default_model", "flux-2-klein-4b")
    url = f"{base_url.rstrip('/')}/{model}"
    width = body.width if body.width is not None else flux2.get("width", 1024)
    height = body.height if body.height is not None else flux2.get("height", 1024)
    payload = {
        "prompt": full_prompt,
        "width": width,
        "height": height,
    }

    #Submit request to BFL
    try:
        resp = requests.post(url, json=payload, headers=_get_bfl_headers(), timeout=60)
    except requests.RequestException as e:
        log_handler.error(f"BFL TTI submit request failed: {e}")
        raise HTTPException(status_code=502, detail="Failed to reach Black Forest API.")

    if resp.status_code != 200:
        log_handler.warning(f"BFL TTI submit returned {resp.status_code}: {resp.text}")
        raise HTTPException(status_code=502, detail=f"Black Forest API error: {resp.status_code} - {resp.text}")

    data = resp.json()
    polling_url = data.get("polling_url")
    if not polling_url:
        raise HTTPException(status_code=502, detail="Black Forest API did not return a polling_url.")

    log_handler.info("TTI task submitted successfully")
    return {"polling_url": polling_url}
