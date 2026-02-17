"""
#############################################################################
### Submit Multi-Image Composition (MIC) request to Black Forest API
###
### @file submit_mic.py
### @author Sebastian Russo
### @date 2025
#############################################################################

This module exposes a POST endpoint to submit a FLUX.2 multi-image composition
request to Black Forest Labs (BFL). It returns the polling_url for the client
to poll until the task is ready.
"""

#Native imports
import os

#Third-party imports
import httpx
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field

#Other files imports
from src.utils.custom_logger import log_handler
from src.utils.limiter import limiter as SlowLimiter
from src.utils.image_preprocessing import normalize_reference_images
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


def _build_full_prompt(user_prompt: str) -> str:
    """Prepend default prompt prefix from data config if set."""
    prefix = BF_CFG.get("flux2", {}).get("default_prompt_prefix_mic") or ""
    return f"{prefix}{user_prompt}".strip()


class SubmitMicBody(BaseModel):
    """Request body: user prompt and list of image URLs or base64 strings."""

    prompt: str = Field(..., min_length=1, description="User prompt for multi-image composition")
    images: list[str] = Field(..., min_length=2, description="List of image URLs or base64-encoded image data")


"""API ROUTER-----------------------------------------------------------"""
router = APIRouter(
    prefix=config_loader['endpoints']['mic_endpoint']['endpoint_prefix'],
    tags=[config_loader['endpoints']['mic_endpoint']['endpoint_tag']],
)

"""ENDPOINT-----------------------------------------------------------"""
# Submit multi-image composition job to BFL FLUX.2
@router.post(config_loader['endpoints']['mic_endpoint']['endpoint_route'])
@SlowLimiter.limit(
    f"{config_loader['endpoints']['mic_endpoint']['request_limit']}/"
    f"{config_loader['endpoints']['mic_endpoint']['unit_of_time_for_limit']}"
)
async def submit_mic(request: Request, body: SubmitMicBody):
    """
    Submit a multi-image composition job to Black Forest FLUX.2.

    This endpoint sends the user prompt and reference images to the BFL API and
    returns a polling_url. The client should poll that URL until status is Ready,
    then use result['sample'] as the signed image URL or call the download endpoint.

    Parameters:
        request (Request): The incoming HTTP request for limit event management.
        body (SubmitMicBody): JSON body with 'prompt' (str) and 'images' (list of URLs or base64).

    Returns:
        dict: Contains 'polling_url' (str) to poll for task status.

    Note:
        If the rate limit is exceeded, the rate_limit_handler() function handles the response.
    """
    log_handler.debug("Submit MIC request received")

    #Normalize reference images (URLs passed through, base64 accepted)
    normalized = normalize_reference_images(body.images)

    #Build full prompt with optional prefix from data config
    full_prompt = _build_full_prompt(body.prompt)

    #Build BFL request URL and payload
    flux2 = BF_CFG.get("flux2", {})
    base_url = os.getenv(BF_CFG["base_url_env"]) or BF_CFG["base_url_default"]
    model = flux2.get("default_model", "flux-2-klein-4b")
    url = f"{base_url.rstrip('/')}/{model}"
    payload = {
        "prompt": full_prompt,
        "input_image": normalized[0] if len(normalized) > 0 else None,
        "input_image_2": normalized[1] if len(normalized) > 1 else None,
        "input_image_3": normalized[2] if len(normalized) > 2 else None,
        "input_image_4": normalized[3] if len(normalized) > 3 else None,
        "width": flux2.get("width", 1024),
        "height": flux2.get("height", 1024),
        "safety_tolerance": flux2.get("safety_tolerance", 2),
        "output_format": flux2.get("output_format", "jpeg"),
    }

    #Submit request to BFL (async)
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload, headers=_get_bfl_headers())
    except httpx.RequestError as e:
        log_handler.error(f"BFL MIC submit request failed: {e}")
        raise HTTPException(status_code=502, detail="Failed to reach Black Forest API.")

    if resp.status_code != 200:
        log_handler.warning(f"BFL submit returned {resp.status_code}: {resp.text}")
        raise HTTPException(status_code=502, detail=f"Black Forest API error: {resp.status_code} - {resp.text}")

    data = resp.json()
    polling_url = data.get("polling_url")
    if not polling_url:
        raise HTTPException(status_code=502, detail="Black Forest API did not return a polling_url.")

    log_handler.info("MIC task submitted successfully")
    return {"polling_url": polling_url}
