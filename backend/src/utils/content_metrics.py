"""
Lightweight in-process counters for content-policy and BFL outcome monitoring.

Counts are logged on each increment for log aggregation (e.g. by day in hosted logs).
"""

from threading import Lock

from src.utils.custom_logger import log_handler

_lock = Lock()
_counts: dict[str, int] = {
    "content_policy_keyword": 0,
    "bfl_submit_reject": 0,
    "bfl_submit_error": 0,
    "bfl_submit_success": 0,
    "bfl_poll_reject": 0,
    "bfl_poll_success": 0,
}


def increment_content_metric(name: str) -> None:
    """Increment a named counter and log running totals."""
    with _lock:
        _counts[name] = _counts.get(name, 0) + 1
        log_handler.info(
            "[content_metrics] event=%s totals=%s",
            name,
            dict(_counts),
        )


def get_content_metric_totals() -> dict[str, int]:
    """Return a snapshot of current counter values."""
    with _lock:
        return dict(_counts)
