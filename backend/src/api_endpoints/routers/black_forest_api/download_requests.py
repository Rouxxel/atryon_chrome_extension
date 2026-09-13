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

# Native imports
import re
from urllib.parse import quote, unquote, urlparse, urlsplit, urlunsplit

# Third-party imports
import httpx
from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

# Other files imports
from src.utils.custom_logger import log_handler
from src.utils.limiter import limiter as SlowLimiter
from src.utils.validators import validate_download_url_allowed
from src.core_specs.configuration.config_loader import config_loader
from src.core_specs.data.data_loader import data_loader

"""VARIABLES-----------------------------------------------------------"""
BF_CFG = data_loader["image_ai_providers"]["black_forest"]
MAX_DOWNLOAD_BYTES = BF_CFG.get("max_download_bytes", 10 * 1024 * 1024)  # 10 MB default
DOWNLOAD_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
TRUNCATED_URL_DETAIL = (
    "Download URL appears incomplete (missing signature query parameters). "
    "Signed URLs contain '&' characters; for GET you must URL-encode the entire "
    "result['sample'] value, or use POST /bf_fl/download_requests with "
    '{"url": "<full sample URL>"}.'
)


class DownloadBody(BaseModel):
    """POST body for download when the signed URL is easier to send as JSON."""

    url: str = Field(
        ...,
        description="Full signed image URL from polling result (result['sample'])",
    )


"""API ROUTER-----------------------------------------------------------"""
router = APIRouter(
    prefix=config_loader["endpoints"]["download_requests_endpoint"]["endpoint_prefix"],
    tags=[config_loader["endpoints"]["download_requests_endpoint"]["endpoint_tag"]],
)


def _has_signature_query(url: str) -> bool:
    """True when the URL query string includes a SAS sig parameter."""
    query = urlsplit(url).query
    return bool(re.search(r"(?:^|&)sig=", query, flags=re.IGNORECASE))


def _encode_url_for_fetch(url: str) -> str:
    """
    Re-encode query values for HTTP fetch.

    After a signed URL is passed through a GET query parameter, '+' in the SAS
    signature is often decoded into the URL string. Many HTTP clients then send
    '+' as a space, which invalidates the signature and causes 403 from BFL.
    """
    parts = urlsplit(url.strip())
    if not parts.query:
        return url.strip()

    encoded_pairs: list[str] = []
    for pair in parts.query.split("&"):
        if not pair:
            continue
        if "=" not in pair:
            encoded_pairs.append(pair)
            continue
        key, value = pair.split("=", 1)
        encoded_pairs.append(f"{key}={quote(unquote(value), safe='')}")

    query = "&".join(encoded_pairs)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))


def _prepare_download_url(url: str) -> str:
    cleaned = url.strip()
    parsed = urlparse(cleaned)
    host = (parsed.hostname or "").lower()
    path = (parsed.path or "").lower()

    if "polling_requests" in path or "get_result" in path:
        raise HTTPException(
            status_code=400,
            detail=(
                "You passed a task polling URL, not the image download URL. "
                "Copy result.sample from the polling response "
                "(https://delivery.*.bfl.ai/.../sample.jpeg?...)."
            ),
        )
    if host.startswith("api.") and host.endswith(".bfl.ai"):
        raise HTTPException(
            status_code=400,
            detail=(
                "You passed a BFL API polling URL (api.*.bfl.ai). "
                "Use result.sample from polling instead."
            ),
        )

    validate_download_url_allowed(cleaned)
    if not _has_signature_query(cleaned):
        raise HTTPException(status_code=400, detail=TRUNCATED_URL_DETAIL)
    return cleaned


async def _fetch_download_image(url: str) -> Response:
    fetch_url = _encode_url_for_fetch(url)
    log_handler.debug("[download_requests] Downloading image from provided URL")

    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            async with client.stream(
                "GET", fetch_url, headers=DOWNLOAD_HEADERS
            ) as resp:
                if resp.status_code != 200:
                    log_handler.warning(
                        "[download_requests] Image URL returned %s (has_sig=%s)",
                        resp.status_code,
                        _has_signature_query(url),
                    )
                    detail = f"Image URL returned {resp.status_code}."
                    if resp.status_code == 403:
                        detail = (
                            "Image URL returned 403. The signed URL may have expired "
                            "(poll again for a fresh result['sample']), or the URL was altered. "
                            "For Postman, prefer POST /bf_fl/download_requests with the sample URL in JSON."
                        )
                    raise HTTPException(status_code=502, detail=detail)

                content_type = resp.headers.get("Content-Type", "image/jpeg")
                chunks: list[bytes] = []
                total = 0
                async for chunk in resp.aiter_bytes(chunk_size=65536):
                    total += len(chunk)
                    if total > MAX_DOWNLOAD_BYTES:
                        log_handler.warning(
                            f"[download_requests] Download exceeded max size ({MAX_DOWNLOAD_BYTES})"
                        )
                        raise HTTPException(
                            status_code=502,
                            detail="Image exceeds maximum allowed size.",
                        )
                    chunks.append(chunk)
                body = b"".join(chunks)
    except httpx.RequestError as e:
        log_handler.error(f"[download_requests] Image download failed: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch image from URL.")

    log_handler.info("[download_requests] Image downloaded successfully")
    return Response(content=body, media_type=content_type)


"""ENDPOINT-----------------------------------------------------------"""


# Download image from signed URL (result['sample'] from polling)
@router.get(config_loader["endpoints"]["download_requests_endpoint"]["endpoint_route"])
@SlowLimiter.limit(
    f"{config_loader['endpoints']['download_requests_endpoint']['request_limit']}/"
    f"{config_loader['endpoints']['download_requests_endpoint']['unit_of_time_for_limit']}"
)
async def download_requests(
    request: Request,
    url: str = Query(
        ...,
        description="Signed image URL from polling result (result['sample']). Must be URL-encoded.",
    ),
):
    """
    Download the generated image from the given signed URL.

    The URL must be result['sample'] from the polling response (BFL blob).
    Returns the image bytes so the client can save the file. Only allowlisted
    hosts and HTTPS are accepted; response size is capped.

    Note: the signed URL contains '&' query parameters. When calling via GET,
    encode the entire URL as the single `url` query value, or use POST instead.
    """
    return await _fetch_download_image(_prepare_download_url(url))


@router.post(config_loader["endpoints"]["download_requests_endpoint"]["endpoint_route"])
@SlowLimiter.limit(
    f"{config_loader['endpoints']['download_requests_endpoint']['request_limit']}/"
    f"{config_loader['endpoints']['download_requests_endpoint']['unit_of_time_for_limit']}"
)
async def download_requests_post(request: Request, body: DownloadBody):
    """
    Download the generated image from a signed URL sent in the JSON body.

    Prefer this in Postman/Swagger when the signed URL is hard to pass as a GET query param.
    """
    return await _fetch_download_image(_prepare_download_url(body.url))
