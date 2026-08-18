"""
#############################################################################
### Submit Image Edit with Mask (IDWM) – FLUX.1 Fill [pro] – to Black Forest API
###
### @file submit_idwm.py
### @author Sebastian Russo
### @date 2025
#############################################################################

This module exposes a POST endpoint to submit an inpainting request to
FLUX.1 Fill [pro] (flux-pro-1.0-fill). Supports two modes: (A) with a separate
mask (black=preserve, white=inpaint), or (B) without mask using base image
alpha channel (transparent=inpaint, opaque=preserved). Returns the polling_url;
polling and download use the same endpoints as MIC and TTI.
"""

#Native imports
import os
from typing import Optional

#Third-party imports
import httpx
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field

#Other files imports
from src.utils.custom_logger import log_handler
from src.utils.limiter import limiter as SlowLimiter
from src.utils.validators import is_url, validate_image_url_safe, validate_prompt_safe
from src.utils.upload_store import is_upload_reference, extract_upload_id, resolve as resolve_upload
from src.core_specs.configuration.config_loader import config_loader
from src.core_specs.data.data_loader import data_loader

"""VARIABLES-----------------------------------------------------------"""
#Black Forest provider data (base URL, API key; flux1_fill has its own model and params)
BF_CFG = data_loader["image_ai_providers"]["black_forest"]
FLUX1_FILL_CFG = BF_CFG.get("flux1_fill", {})
MIN_DIMENSION = 512
MAX_DIMENSION = 2048


def _get_bfl_headers() -> dict:
    """Build BFL API headers (x-key from environment)."""
    api_key = os.getenv(BF_CFG["api_key_env"])
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Black Forest API key not configured. Set the environment variable."
        )
    return {"x-key": api_key, "Content-Type": "application/json"}


def _build_full_prompt_fill(user_prompt: str) -> str:
    """Prepend default inpainting prompt prefix from data config if set."""
    prefix = FLUX1_FILL_CFG.get("default_prompt_prefix_idwm") or ""
    return f"{prefix}{user_prompt}".strip()


class SubmitIdwmBody(BaseModel):
    """Request body: prompt, base image, optional mask, optional dimensions."""

    prompt: str = Field(..., min_length=1, description="What to add or change in the editable area")
    image: str = Field(..., min_length=1, description="Base image: URL or base64-encoded data")
    mask: Optional[str] = Field(None, description="Optional mask: URL or base64. Black=preserve, white=inpaint. Omit for alpha-channel mode.")
    width: Optional[int] = Field(None, ge=MIN_DIMENSION, le=MAX_DIMENSION, description="Output width 512–2048")
    height: Optional[int] = Field(None, ge=MIN_DIMENSION, le=MAX_DIMENSION, description="Output height 512–2048")


"""API ROUTER-----------------------------------------------------------"""
router = APIRouter(
    prefix=config_loader['endpoints']['idwm_endpoint']['endpoint_prefix'],
    tags=[config_loader['endpoints']['idwm_endpoint']['endpoint_tag']],
)

"""ENDPOINT-----------------------------------------------------------"""
# Submit FLUX.1 Fill [pro] inpainting job (image edit with or without mask)
@router.post(config_loader['endpoints']['idwm_endpoint']['endpoint_route'])
@SlowLimiter.limit(
    f"{config_loader['endpoints']['idwm_endpoint']['request_limit']}/"
    f"{config_loader['endpoints']['idwm_endpoint']['unit_of_time_for_limit']}"
)
async def submit_idwm(request: Request, body: SubmitIdwmBody):
    """
    Submit an inpainting (image edit) job to FLUX.1 Fill [pro].

    This endpoint sends the base image, prompt, and optional mask to the BFL API
    and returns a polling_url. With mask: black=preserved, white=inpainted.
    Without mask: base image should have alpha channel (transparent=inpainted).
    The client should poll until status is Ready, then use result['sample'] or
    the download endpoint.

    Parameters:
        request (Request): The incoming HTTP request for limit event management.
        body (SubmitIdwmBody): JSON body with 'prompt', 'image' (URL or base64), optional 'mask'.

    Returns:
        dict: Contains 'polling_url' (str) to poll for task status.

    Note:
        If the rate limit is exceeded, the rate_limit_handler() function handles the response.
    """
    log_handler.debug("[submit_idwm] Submit IDWM (FLUX.1 Fill) request received")

    #Resolve upload:<id> to base64; validate URLs (SSRF)
    image_value = body.image
    if is_upload_reference(image_value):
        image_value = resolve_upload(extract_upload_id(image_value))
    elif is_url(image_value):
        validate_image_url_safe(image_value)

    mask_value = body.mask
    if body.mask and body.mask.strip():
        if is_upload_reference(body.mask):
            mask_value = resolve_upload(extract_upload_id(body.mask))
        elif is_url(body.mask):
            validate_image_url_safe(body.mask)
    else:
        mask_value = None

    #Sanitize prompt (strip control chars, enforce max length)
    sanitized_prompt = validate_prompt_safe(body.prompt, BF_CFG.get("max_prompt_length", 400))

    #Build full prompt with optional inpainting prefix from data config
    full_prompt = _build_full_prompt_fill(sanitized_prompt)

    #Build BFL request URL (FLUX.1 Fill model, not FLUX.2)
    base_url = os.getenv(BF_CFG["base_url_env"]) or BF_CFG["base_url_default"]
    model_name = FLUX1_FILL_CFG.get("default_model", "flux-pro-1.0-fill")
    url = f"{base_url.rstrip('/')}/{model_name}"

    payload = {
        "image": image_value,
        "prompt": full_prompt,
        "steps": FLUX1_FILL_CFG.get("steps", 50),
        "guidance": FLUX1_FILL_CFG.get("guidance", 60),
        "output_format": FLUX1_FILL_CFG.get("output_format", "jpeg"),
        "safety_tolerance": FLUX1_FILL_CFG.get("safety_tolerance", 2),
    }
    if mask_value is not None:
        payload["mask"] = mask_value
    if body.width is not None:
        payload["width"] = body.width
    if body.height is not None:
        payload["height"] = body.height

    #Submit request to BFL (async)
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload, headers=_get_bfl_headers())
    except httpx.RequestError as e:
        log_handler.error(f"[submit_idwm] BFL IDWM submit request failed: {e}")
        raise HTTPException(status_code=502, detail="Failed to reach Black Forest API.")

    if resp.status_code != 200:
        log_handler.warning(f"[submit_idwm] BFL IDWM submit returned {resp.status_code}: {resp.text}")
        raise HTTPException(status_code=502, detail=f"Black Forest API error: {resp.status_code} - {resp.text}")

    data = resp.json()
    polling_url = data.get("polling_url")
    if not polling_url:
        raise HTTPException(status_code=502, detail="Black Forest API did not return a polling_url.")

    log_handler.info("[submit_idwm] IDWM (FLUX.1 Fill) task submitted successfully")
    log_handler.warning(f"[submit_idwm] polling_url={polling_url}")
    return {"polling_url": polling_url}
