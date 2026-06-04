"""
#############################################################################
### Download generated image by URL (from polling result)
###
### @file download_requests.py
### @author Sebastian Russo
### @date 2025
#############################################################################

This module defines an endpoint to download the finished image using the signed
URL returned in result['sample'] from the polling endpoint. Returns the image
bytes (so the client can save the file). SSRF-protected via allowlist; async
fetch with max size limit.
"""

#Native imports
from urllib.parse import urlparse

#Third-party imports
import httpx
from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import Response

#Other files imports
from src.utils.custom_logger import log_handler
from src.utils.limiter import limiter as SlowLimiter
from src.utils.validators import is_url
from src.core_specs.configuration.config_loader import config_loader
from src.core_specs.data.data_loader import data_loader

"""VARIABLES-----------------------------------------------------------"""
BF_CFG = data_loader["image_ai_providers"]["black_forest"]
ALLOWED_HOSTS = set(BF_CFG.get("allowed_download_hosts", ["bfldeliveryprodeu4.blob.core.windows.net"]))
MAX_DOWNLOAD_BYTES = BF_CFG.get("max_download_bytes", 10 * 1024 * 1024)  # 10 MB default
DOWNLOAD_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}


def _url_allowed(url: str) -> tuple[bool, str]:
    """
    SSRF check: HTTPS only, host in allowlist.
    Returns (ok, error_message).
    """
    if not is_url(url):
        return False, "Invalid URL."
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return False, "Only HTTPS URLs are allowed."
    host = (parsed.hostname or "").lower()
    if not host or host not in ALLOWED_HOSTS:
        return False, "URL host not allowed for download."
    return True, ""


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

    The URL must be result['sample'] from the polling response (BFL blob).
    Returns the image bytes so the client can save the file. Only allowlisted
    hosts and HTTPS are accepted; response size is capped.
    """
    ok, err = _url_allowed(url)
    if not ok:
        log_handler.error(f"[download_requests] Url not ok: {url}")
        raise HTTPException(status_code=400, detail=err)

    log_handler.debug("[download_requests] Downloading image from provided URL")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("GET", url, headers=DOWNLOAD_HEADERS) as resp:
                if resp.status_code != 200:
                    log_handler.warning(f"[download_requests] Image URL returned {resp.status_code}")
                    detail = f"Image URL returned {resp.status_code}."
                    if resp.status_code == 403:
                        detail = (
                            "Image URL returned 403. Signed URLs expire after a short time (often 10–15 min). "
                            "Call this endpoint immediately after polling; do not reuse old result['sample'] URLs."
                        )
                    raise HTTPException(status_code=502, detail=detail)

                content_type = resp.headers.get("Content-Type", "image/jpeg")
                chunks: list[bytes] = []
                total = 0
                async for chunk in resp.aiter_bytes(chunk_size=65536):
                    total += len(chunk)
                    if total > MAX_DOWNLOAD_BYTES:
                        log_handler.warning(f"[download_requests] Download exceeded max size ({MAX_DOWNLOAD_BYTES})")
                        raise HTTPException(status_code=502, detail="Image exceeds maximum allowed size.")
                    chunks.append(chunk)
                body = b"".join(chunks)
    except httpx.RequestError as e:
        log_handler.error(f"[download_requests] Image download failed: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch image from URL.")

    log_handler.info(f"[download_requests] Image downloaded successfully")
    return Response(content=body, media_type=content_type)
