"""
#############################################################################
### Temporary upload store for image uploads (one-time use, resolve to base64)
###
### @file upload_store.py
### @author Sebastian Russo
### @date 2025
#############################################################################

Stores uploaded image files temporarily. Register returns an upload_id; resolve
reads the file to base64 and deletes it (one-time use). Used by MIC and IDWM
when client sends "upload:<id>" or a bare UUID from /upload/images.
"""

# Native imports
import base64
import os
import re
import time
import uuid
from pathlib import Path

from fastapi import HTTPException

from src.core_specs.data.data_loader import data_loader

# Other files imports
from src.utils.custom_logger import log_handler

UPLOAD_PREFIX = "upload:"
_UPLOAD_ID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


# Config from general_data (file_upload)
def _upload_config():
    return data_loader.get("file_upload", {})


def _temp_dir() -> Path:
    """Dedicated temp subdirectory for uploads."""
    base = os.environ.get("UPLOAD_TEMP_DIR") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads_temp"
    )
    path = Path(base)
    path.mkdir(parents=True, exist_ok=True)
    return path


# In-memory: upload_id -> (file_path, created_at)
_store: dict[str, tuple[str, float]] = {}


def _max_bytes() -> int:
    return _upload_config().get("max_upload_bytes", 10 * 1024 * 1024)


def _allowed_content_types() -> set:
    types = _upload_config().get(
        "allowed_upload_content_types", ["image/jpeg", "image/png", "image/webp"]
    )
    return set(types)


def _ttl_seconds() -> int:
    return _upload_config().get("upload_temp_ttl_seconds", 600)


def _upload_path(upload_id: str) -> Path:
    return _temp_dir() / f"{upload_id}.bin"


def _recover_upload_from_disk(upload_id: str) -> bool:
    """
    Rebuild an in-memory entry when the temp file still exists (e.g. after reload).
    """
    if not is_bare_upload_id(upload_id):
        return False
    path = _upload_path(upload_id)
    if not path.is_file():
        return False
    _store[upload_id] = (str(path), path.stat().st_mtime)
    log_handler.debug(f"[upload_store] Recovered upload {upload_id} from disk")
    return True


def rehydrate_store_from_disk() -> int:
    """
    Scan uploads_temp and rebuild the in-memory index from surviving .bin files.
    """
    restored = 0
    for path in _temp_dir().glob("*.bin"):
        upload_id = path.stem
        if upload_id in _store or not is_bare_upload_id(upload_id):
            continue
        _store[upload_id] = (str(path), path.stat().st_mtime)
        restored += 1
    if restored:
        log_handler.info(f"[upload_store] Rehydrated {restored} upload(s) from disk")
    return restored


def register(file_bytes: bytes, content_type: str | None) -> str:
    """
    Save file bytes to temp directory and store mapping. Enforces max size and
    allowed content-type.

    :param file_bytes: Raw image bytes.
    :param content_type: e.g. image/jpeg, image/png.
    :return: upload_id (UUID string).
    :raises HTTPException: If size or content-type invalid.
    """
    max_b = _max_bytes()
    if len(file_bytes) > max_b:
        raise HTTPException(
            status_code=400, detail=f"File exceeds maximum size ({max_b} bytes)."
        )
    allowed = _allowed_content_types()
    ct = (content_type or "").strip().lower()
    if ct and ct not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Content-Type not allowed. Allowed: {list(allowed)}.",
        )
    upload_id = str(uuid.uuid4())
    temp_path = _upload_path(upload_id)
    temp_path.write_bytes(file_bytes)
    _store[upload_id] = (str(temp_path), time.time())
    log_handler.debug(f"[upload_store] Registered upload {upload_id}")
    return upload_id


def resolve(upload_id: str) -> str:
    """
    Read file for upload_id, return base64 string, then delete file and remove
    from store (one-time use). If not found or expired, raise.

    :param upload_id: UUID string (without "upload:" prefix).
    :return: Base64-encoded image string (raw, no data URI prefix).
    :raises HTTPException: If upload_id unknown or expired.
    """
    if upload_id not in _store and not _recover_upload_from_disk(upload_id):
        log_handler.warning(
            "[upload_store] Upload resolve failed: id=%s (not registered or already consumed)",
            upload_id,
        )
        raise HTTPException(
            status_code=400,
            detail=(
                "Upload not found or already used. Upload images again; "
                "each upload ID works only once per MIC/IDWM request."
            ),
        )
    path_str, created = _store[upload_id]
    path = Path(path_str)
    ttl = _ttl_seconds()
    if (time.time() - created) > ttl:
        if path.exists():
            try:
                path.unlink()
            except OSError:
                pass
        del _store[upload_id]
        raise HTTPException(status_code=400, detail="Upload expired.")
    if not path.exists():
        del _store[upload_id]
        raise HTTPException(status_code=400, detail="Upload not found or already used.")
    try:
        b64 = base64.b64encode(path.read_bytes()).decode("utf-8")
    finally:
        try:
            path.unlink()
        except OSError:
            log_handler.warning(f"[upload_store] Could not delete upload file: {path}")
        del _store[upload_id]
    log_handler.debug(f"[upload_store] Resolved and consumed upload {upload_id}")
    return b64


def is_bare_upload_id(value: str) -> bool:
    """True if value is a bare UUID returned by POST /upload/images."""
    return isinstance(value, str) and bool(_UPLOAD_ID_RE.match(value.strip()))


def is_upload_reference(value: str) -> bool:
    """True if value is upload:<uuid> or a bare upload UUID."""
    if not isinstance(value, str):
        return False
    stripped = value.strip()
    if stripped.startswith(UPLOAD_PREFIX) and len(stripped) > len(UPLOAD_PREFIX):
        return True
    return is_bare_upload_id(stripped)


def extract_upload_id(value: str) -> str:
    """Return the UUID from upload:<uuid> or a bare upload UUID."""
    if not isinstance(value, str):
        raise TypeError(f"Not an upload reference: {value!r}")
    stripped = value.strip()
    if stripped.startswith(UPLOAD_PREFIX):
        return stripped[len(UPLOAD_PREFIX) :].strip()
    if is_bare_upload_id(stripped):
        return stripped
    raise ValueError(f"Not an upload reference: {value!r}")


def cleanup_expired() -> int:
    """
    Remove orphaned files older than TTL (e.g. client never called MIC/IDWM).
    :return: Number of entries removed.
    """
    now = time.time()
    ttl = _ttl_seconds()
    removed = 0
    to_remove = [uid for uid, (_, created) in _store.items() if (now - created) > ttl]
    for uid in to_remove:
        path_str, _ = _store.get(uid, (None, 0))
        if path_str and Path(path_str).exists():
            try:
                Path(path_str).unlink()
            except OSError:
                pass
        if uid in _store:
            del _store[uid]
            removed += 1
    if removed:
        log_handler.debug(
            f"[upload_store] Cleanup: removed {removed} expired upload(s)"
        )
    return removed
