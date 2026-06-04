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
signed URL for the generated image. SSRF-protected via allowlist; async.
"""

#Native imports
import os
import asyncio

#Third-party imports
import httpx
from fastapi import APIRouter, Request, HTTPException, Query

#Other files imports
from src.utils.custom_logger import log_handler
from src.utils.limiter import limiter as SlowLimiter
from src.utils.validators import validate_polling_url_allowed
from src.core_specs.configuration.config_loader import config_loader
from src.core_specs.data.data_loader import data_loader

"""VARIABLES-----------------------------------------------------------"""
#Black Forest provider data (for API key env key)
BF_CFG = data_loader["image_ai_providers"]["black_forest"]
ALLOWED_POLLING_HOSTS = set(data_loader["image_ai_providers"]["black_forest"]["allowed_polling_hosts"])
POLLING_RETRY_ATTEMPTS = BF_CFG.get("polling_retry_attempts", 3)
POLLING_RETRY_DELAY_SEC = BF_CFG.get("polling_retry_delay_sec", 1.0)

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
    the generated image (string or list of URLs). Only allowlisted BFL API hosts
    are accepted (SSRF protection).
    """
    validate_polling_url_allowed(polling_url, ALLOWED_POLLING_HOSTS)

    log_handler.debug("[polling_requests] Polling BFL task")

    last_exception = None
    last_resp = None

    for attempt in range(1, POLLING_RETRY_ATTEMPTS + 1):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(polling_url, headers=_get_bfl_headers())
        except httpx.RequestError as e:
            last_exception = e
            log_handler.error(
                "[polling_requests] BFL poll request failed (full error): polling_url=%s attempt=%s error_type=%s error=%s",
                polling_url, attempt, type(e).__name__, repr(e), exc_info=True
            )
            if attempt < POLLING_RETRY_ATTEMPTS:
                log_handler.warning("[polling_requests] Retrying BFL poll in %.1fs (attempt %s/%s)", POLLING_RETRY_DELAY_SEC, attempt + 1, POLLING_RETRY_ATTEMPTS)
                await asyncio.sleep(POLLING_RETRY_DELAY_SEC)
                continue
            raise HTTPException(status_code=502, detail="Failed to reach Black Forest API.")

        if resp.status_code != 200:
            last_resp = resp
            log_handler.error(
                "[polling_requests] BFL poll returned non-200 (full response): polling_url=%s attempt=%s status_code=%s body=%s",
                polling_url, attempt, resp.status_code, resp.text
            )
            if attempt < POLLING_RETRY_ATTEMPTS:
                log_handler.warning("[polling_requests] Retrying BFL poll in %.1fs (attempt %s/%s)", POLLING_RETRY_DELAY_SEC, attempt + 1, POLLING_RETRY_ATTEMPTS)
                await asyncio.sleep(POLLING_RETRY_DELAY_SEC)
                continue
            raise HTTPException(status_code=502, detail=f"Black Forest API error: {resp.status_code} - {resp.text}")

        data = resp.json()
        log_handler.debug("[polling_requests] Poll result status: %s", data.get("status"))
        return data

    raise HTTPException(status_code=502, detail="Polling failed after retries.")
