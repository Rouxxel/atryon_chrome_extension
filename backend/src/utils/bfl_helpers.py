"""
Shared helpers for Black Forest Labs API requests and responses.
"""

# Third-party imports
import httpx
from fastapi import HTTPException

from src.utils.content_metrics import increment_content_metric

# Other files imports
from src.utils.custom_logger import log_handler

BFL_CLIENT_ERROR_DETAIL = "Request could not be completed."

_BFL_PENDING_STATUSES = {"pending", "processing"}
_BFL_FAILURE_STATUSES = {
    "error",
    "failed",
    "failure",
    "request moderated",
    "content moderated",
    "moderated",
    "cancelled",
    "canceled",
    "blocked",
}
_BFL_CONTENT_REJECTION_HINTS = (
    "moderat",
    "safety",
    "content policy",
    "nsfw",
    "inappropriate",
    "blocked",
    "not allowed",
)


def clamp_safety_tolerance(value: int, minimum: int = 0, maximum: int = 6) -> int:
    """Clamp safety_tolerance to the supported BFL range (typically 0–6)."""
    return max(minimum, min(maximum, int(value)))


def get_flux2_safety_tolerance(flux2_cfg: dict) -> int:
    """Read and clamp FLUX.2 safety_tolerance from provider config."""
    minimum = flux2_cfg.get("safety_tolerance_min", 0)
    maximum = flux2_cfg.get("safety_tolerance_max", 6)
    return clamp_safety_tolerance(
        flux2_cfg.get("safety_tolerance", 2), minimum, maximum
    )


def get_flux1_fill_safety_tolerance(flux1_cfg: dict) -> int:
    """Read and clamp FLUX.1 Fill safety_tolerance from provider config."""
    minimum = flux1_cfg.get("safety_tolerance_min", 0)
    maximum = flux1_cfg.get("safety_tolerance_max", 6)
    return clamp_safety_tolerance(
        flux1_cfg.get("safety_tolerance", 2), minimum, maximum
    )


def is_likely_bfl_content_rejection(status_code: int, body: str) -> bool:
    """Heuristic: BFL submit body/status suggests provider-side content moderation."""
    lowered = (body or "").lower()
    if status_code in (400, 403, 422):
        return True
    return any(hint in lowered for hint in _BFL_CONTENT_REJECTION_HINTS)


def parse_bfl_poll_response(resp: httpx.Response) -> dict | None:
    """
    Parse a BFL polling HTTP response into a task payload when possible.

    BFL sometimes returns non-200 (e.g. 422) with a JSON body that still contains
    task fields such as status=Error. Those should be handled as poll results,
    not as transport failures.
    """
    try:
        data = resp.json()
    except ValueError:
        return None
    if isinstance(data, dict) and data.get("status") is not None:
        return data
    return None


def is_bfl_task_failure(status: str | None) -> bool:
    """Return True when a polled BFL task reached a terminal failure state."""
    if not status:
        return False
    normalized = status.strip().lower()
    if normalized in _BFL_PENDING_STATUSES or normalized == "ready":
        return False
    if normalized in _BFL_FAILURE_STATUSES:
        return True
    return True


def handle_bfl_submit_response(endpoint: str, resp: httpx.Response) -> dict:
    """
    Parse a BFL submit response or raise a generic client error.

    Full provider response text is logged server-side only.
    """
    if resp.status_code != 200:
        body = resp.text
        is_content_rejection = is_likely_bfl_content_rejection(resp.status_code, body)
        reason = "bfl_content_policy" if is_content_rejection else "bfl_submit_error"
        log_handler.warning(
            "[bfl] reason=%s endpoint=%s status_code=%s body=%s",
            reason,
            endpoint,
            resp.status_code,
            body,
        )
        increment_content_metric(
            "bfl_submit_reject" if is_content_rejection else "bfl_submit_error"
        )
        raise HTTPException(status_code=502, detail=BFL_CLIENT_ERROR_DETAIL)

    data = resp.json()
    polling_url = data.get("polling_url")
    if not polling_url:
        log_handler.warning(
            "[bfl] reason=bfl_submit_no_polling_url endpoint=%s response_keys=%s",
            endpoint,
            list(data.keys()),
        )
        increment_content_metric("bfl_submit_error")
        raise HTTPException(status_code=502, detail=BFL_CLIENT_ERROR_DETAIL)

    increment_content_metric("bfl_submit_success")
    log_handler.warning("[bfl] endpoint=%s polling_url=%s", endpoint, polling_url)
    return data


def handle_bfl_poll_payload(polling_url: str, data: dict) -> dict:
    """
    Return poll payload when still in progress or ready; raise on terminal failure.

    Provider moderation failures are logged with polling_url and task id when present.
    """
    status = data.get("status")
    task_id = data.get("id") or data.get("task_id")
    details = data.get("details") or {}
    detail_error = details.get("error") if isinstance(details, dict) else None

    if is_bfl_task_failure(status):
        log_handler.warning(
            "[bfl] reason=bfl_poll_reject polling_url=%s task_id=%s status=%s detail=%s",
            polling_url,
            task_id,
            status,
            detail_error,
        )
        increment_content_metric("bfl_poll_reject")
        if detail_error and "image" in str(detail_error).lower():
            raise HTTPException(
                status_code=400,
                detail="Image could not be processed. Try another clothing or photo file.",
            )
        raise HTTPException(status_code=400, detail=BFL_CLIENT_ERROR_DETAIL)

    if status and status.strip().lower() == "ready":
        increment_content_metric("bfl_poll_success")

    return data
