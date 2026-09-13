"""
#############################################################################
### Validator methods file
###
### @file validators.py
### @Sebastian Russo
### @date: 2025
#############################################################################

This module defines several methods to validate several things.
"""

# Native imports
import base64
import binascii
import hashlib
import re
import struct
import unicodedata
from urllib.parse import urlparse

from fastapi import HTTPException

from src.core_specs.configuration.config_loader import config_loader
from src.core_specs.data.data_loader import data_loader
from src.utils.content_metrics import increment_content_metric

# Other files imports
from src.utils.custom_logger import log_handler


def validate_email_format(email: str) -> bool:
    """
    Validate an email address.

    local_part@subdomain.domain.tld or example@provider.tld

    Checks if:
    - There is exactly one '@' symbol.
    - The local part is non-empty, contains no '@' and only allowed characters.
    - The domain contains exactly 1 '.' separating provider and TLD.
    - The provider and TLD are in allowed lists from config.

    Args:
        email (str): The email string to validate.

    Returns:
        Nothing, it allows execution and not raise an exception
    """

    message = ""

    # Check exactly one '@' in the email
    if email.count("@") != 1:
        message = f"Invalid email '{email}': must contain exactly one '@'"
        log_handler.warning(message)
        raise HTTPException(status_code=400, detail=message)
    local_part, domain_part = email.rsplit("@", 1)

    # Check local part is not empty and contains only allowed characters
    if not local_part or not re.match(r"^[\w\.-]+$", local_part):
        message = f"Invalid email '{email}': local part is invalid"
        log_handler.warning(message)
        raise HTTPException(status_code=400, detail=message)

    # Domain must contain exactly one '.'
    if domain_part.count(".") != 1:
        message = f"Invalid email '{email}': domain part must contain exactly one '.'"
        log_handler.warning(message)
        raise HTTPException(status_code=400, detail=message)
    provider, tld = domain_part.rsplit(".", 1)

    # Check if provider and tld are allowed
    if provider not in config_loader["email_validation"]["allowed_providers"]:
        message = f"Invalid email '{email}': provider '{provider}' not allowed"
        log_handler.warning(message)
        raise HTTPException(status_code=400, detail=message)
    if tld not in config_loader["email_validation"]["allowed_tlds"]:
        message = f"Invalid email '{email}': TLD '{tld}' not allowed"
        log_handler.warning(message)
        raise HTTPException(status_code=400, detail=message)

    log_handler.debug(f"[validators] Email '{email}' is valid, proceeding")


def validate_password_format(password: str):
    """
    Validate a password.

    Checks if:
    - At least 8 characters long
    - Contains at least one lowercase letter
    - Contains at least one uppercase letter
    - Contains at least one digit
    - Contains at least one special symbol (non-alphanumeric)

    Args:
        password (str): The password string to validate.

    Returns:
        bool: Nothing, the method does not raise exceptions and allows
        to continue execution
    """

    message = ""

    if len(password) < 8:
        message = "Password length is too short."
        log_handler.warning(message)
        raise HTTPException(status_code=400, detail=message)

    if not re.search(r"[a-z]", password):
        message = "Password validation failed: no lowercase letter found"
        log_handler.warning(message)
        raise HTTPException(status_code=400, detail=message)

    if not re.search(r"[A-Z]", password):
        message = "Password validation failed: no uppercase letter found"
        log_handler.warning(message)
        raise HTTPException(status_code=400, detail=message)

    if not re.search(r"\d", password):
        message = "Password validation failed: no digit found"
        log_handler.warning(message)
        raise HTTPException(status_code=400, detail=message)

    if not re.search(r"[^\w\s]", password):
        message = "Password validation failed: no special symbol found"
        log_handler.warning(message)
        raise HTTPException(status_code=400, detail=message)

    log_handler.info("[validators] Password is valid")


def validate_access_token_format(token: str):
    jwt_regex = r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$"
    if not re.fullmatch(jwt_regex, token):
        raise HTTPException(status_code=400, detail="Access token format is invalid.")


def validate_refresh_token_format(token: str):
    if not token.isalnum() or len(token) < 10:
        raise HTTPException(status_code=400, detail="Refresh token format is invalid.")


def validate_uuid_format(uuid_str: str):
    uuid_regex = (
        r"^[a-f0-9]{8}-[a-f0-9]{4}-[1-5][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$"
    )
    if not re.fullmatch(uuid_regex, uuid_str.lower()):  # RFC 4122 standard
        raise HTTPException(status_code=400, detail="User ID format is invalid.")


def is_url(value: str) -> bool:
    return value.startswith(("http://", "https://"))


def _is_private_host(host: str) -> bool:
    """True if host is localhost or a private IP (SSRF risk)."""
    if not host:
        return True
    host = host.lower().strip()
    if host in ("localhost", "::1", "0.0.0.0"):
        return True
    try:
        import ipaddress

        ip = ipaddress.ip_address(host)
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
    except ValueError:
        pass
    if host.startswith(("127.", "10.", "192.168.", "169.254.")):
        return True
    if host.startswith("172."):
        parts = host.split(".")
        if len(parts) == 4 and parts[1].isdigit() and 16 <= int(parts[1]) <= 31:
            return True
    return False


def validate_polling_url_allowed(url: str, allowed_hosts: set) -> None:
    """
    SSRF check for polling URL: HTTPS only, host in allowlist.
    Raises HTTPException if invalid.
    """
    if not is_url(url):
        raise HTTPException(status_code=400, detail="Invalid polling URL.")
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise HTTPException(status_code=400, detail="Polling URL must be HTTPS.")
    host = (parsed.hostname or "").lower()
    if not host or host not in allowed_hosts:
        raise HTTPException(status_code=400, detail="Polling URL host not allowed.")


def validate_image_url_safe(url: str) -> None:
    """
    SSRF check for image/mask URLs sent to BFL: HTTPS only, no private hosts.
    Raises HTTPException if invalid.
    """
    if not is_url(url):
        raise HTTPException(status_code=400, detail="Invalid image URL.")
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise HTTPException(status_code=400, detail="Image URL must be HTTPS.")
    host = (parsed.hostname or "").lower()
    if _is_private_host(host):
        raise HTTPException(
            status_code=400, detail="Image URL must not point to private or localhost."
        )


def validate_request_size(
    content_length: int | None, max_bytes: int | None = None
) -> None:
    """
    Validate that a request body does not exceed the configured maximum size.

    Checks Content-Length header against the configured maximum upload size.
    If Content-Length is provided and exceeds the limit, rejects with HTTP 400
    before reading the body. If max_bytes is not provided, reads the limit from
    data config (file_upload.max_upload_bytes), defaulting to 10 MB.

    Args:
        content_length: The value of the Content-Length header, or None if absent.
        max_bytes: Optional override for the maximum allowed size in bytes.

    Raises:
        HTTPException: 400 if the request body exceeds the allowed size limit.
        SystemExit: If the configured max size is not a positive integer.
    """
    # Resolve max_bytes from config if not explicitly provided
    if max_bytes is None:
        max_bytes = data_loader.get("file_upload", {}).get("max_upload_bytes", 10485760)

    # Requirement 5.4: refuse to operate if configured value is invalid
    if not isinstance(max_bytes, int) or max_bytes <= 0:
        log_handler.critical(
            "[validators] Invalid max upload size configuration: "
            "value must be a positive integer"
        )
        raise SystemExit(
            "Invalid max upload size configuration: value must be a positive integer"
        )

    # Requirement 5.1: reject if Content-Length exceeds configured max
    if content_length is not None:
        if not isinstance(content_length, int) or content_length < 0:
            raise HTTPException(
                status_code=400, detail="Request body exceeds the allowed size limit."
            )
        if content_length > max_bytes:
            log_handler.warning(
                "[validators] Request rejected: Content-Length exceeds allowed size"
            )
            raise HTTPException(
                status_code=400, detail="Request body exceeds the allowed size limit."
            )

    log_handler.debug("[validators] Request size validation passed")


# Magic bytes signatures for supported image content types
MAGIC_BYTES: dict[str, dict] = {
    "image/jpeg": {
        "header": bytes([0xFF, 0xD8, 0xFF]),
        "offset": 0,
    },
    "image/png": {
        "header": bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]),
        "offset": 0,
    },
    "image/webp": {
        "header": bytes([0x52, 0x49, 0x46, 0x46]),
        "offset": 0,
        "secondary_header": bytes([0x57, 0x45, 0x42, 0x50]),
        "secondary_offset": 8,
    },
}


def validate_file_magic_bytes(file_bytes: bytes, claimed_content_type: str) -> None:
    """
    Validate that a file's leading bytes match the expected magic bytes
    for the claimed content-type.

    Raises HTTPException(400) if:
    - The content-type is not supported
    - The file is empty (0 bytes)
    - The file is shorter than the required signature length
    - The magic bytes do not match the claimed content-type

    Error messages are generic and do not reveal internal details.

    Args:
        file_bytes: The raw bytes of the uploaded file.
        claimed_content_type: The MIME type claimed by the upload.

    Returns:
        None. Raises HTTPException on failure.
    """
    # Reject unsupported content-types
    if claimed_content_type not in MAGIC_BYTES:
        log_handler.warning(
            "[validators] Unsupported content-type for magic byte validation"
        )
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type.",
        )

    # Reject empty files
    if len(file_bytes) == 0:
        log_handler.warning("[validators] Empty file uploaded")
        raise HTTPException(
            status_code=400,
            detail="File is empty.",
        )

    signature = MAGIC_BYTES[claimed_content_type]
    header = signature["header"]
    offset = signature["offset"]

    # Calculate minimum required length
    min_length = offset + len(header)
    if "secondary_header" in signature:
        secondary_end = signature["secondary_offset"] + len(
            signature["secondary_header"]
        )
        min_length = max(min_length, secondary_end)

    # Reject files shorter than the signature length
    if len(file_bytes) < min_length:
        log_handler.warning("[validators] File too short for magic byte validation")
        raise HTTPException(
            status_code=400,
            detail="File is too small to be a valid image.",
        )

    # Verify primary header bytes
    actual_header = file_bytes[offset : offset + len(header)]
    if actual_header != header:
        log_handler.warning("[validators] Magic byte mismatch for claimed content-type")
        raise HTTPException(
            status_code=400,
            detail="File content does not match the declared file type.",
        )

    # Verify secondary header (for WebP)
    if "secondary_header" in signature:
        sec_header = signature["secondary_header"]
        sec_offset = signature["secondary_offset"]
        actual_secondary = file_bytes[sec_offset : sec_offset + len(sec_header)]
        if actual_secondary != sec_header:
            log_handler.warning(
                "[validators] Secondary magic byte mismatch for claimed content-type"
            )
            raise HTTPException(
                status_code=400,
                detail="File content does not match the declared file type.",
            )


def detect_image_content_type(file_bytes: bytes) -> str | None:
    """Detect supported image MIME type from magic bytes, or None if unsupported."""
    for content_type in MAGIC_BYTES:
        try:
            validate_file_magic_bytes(file_bytes, content_type)
            return content_type
        except HTTPException:
            continue
    return None


def normalize_and_validate_base64_image(value: str) -> str:
    """
    Validate a raw or data-URI base64 image string for BFL payloads.

    Rejects file paths and other non-base64 strings that were previously
    passed through and rejected later by BFL as corrupted image input.
    """
    raw = value.strip()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty image data.")

    if raw.startswith("data:") and "," in raw:
        raw = raw.split(",", 1)[1].strip()

    lowered = raw.lower()
    if (
        "/" in raw
        or "\\" in raw
        or lowered.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif"))
    ):
        raise HTTPException(
            status_code=400,
            detail="Image reference must be a URL, upload:id, or base64-encoded image data.",
        )

    try:
        decoded = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(
            status_code=400,
            detail="Image reference must be a URL, upload:id, or valid base64-encoded image data.",
        )

    if detect_image_content_type(decoded) is None:
        raise HTTPException(
            status_code=400,
            detail="Image could not be processed. Try another clothing or photo file.",
        )

    return raw


def _read_png_dimensions(file_bytes: bytes) -> tuple[int, int]:
    if len(file_bytes) < 24:
        raise ValueError("PNG too short")
    return struct.unpack(">II", file_bytes[16:24])


def _read_jpeg_dimensions(file_bytes: bytes) -> tuple[int, int]:
    index = 2
    while index < len(file_bytes) - 8:
        if file_bytes[index] != 0xFF:
            index += 1
            continue
        marker = file_bytes[index + 1]
        if marker in (
            0xC0,
            0xC1,
            0xC2,
            0xC3,
            0xC5,
            0xC6,
            0xC7,
            0xC9,
            0xCA,
            0xCB,
            0xCD,
            0xCE,
            0xCF,
        ):
            height = struct.unpack(">H", file_bytes[index + 5 : index + 7])[0]
            width = struct.unpack(">H", file_bytes[index + 7 : index + 9])[0]
            return width, height
        if marker in (0xD0, 0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0x01):
            index += 2
            continue
        segment_length = struct.unpack(">H", file_bytes[index + 2 : index + 4])[0]
        index += 2 + segment_length
    raise ValueError("JPEG SOF not found")


def _read_webp_dimensions(file_bytes: bytes) -> tuple[int, int]:
    if len(file_bytes) < 30:
        raise ValueError("WebP too short")
    if file_bytes[12:16] == b"VP8 ":
        width = struct.unpack("<H", file_bytes[26:28])[0] & 0x3FFF
        height = struct.unpack("<H", file_bytes[28:30])[0] & 0x3FFF
        return width, height
    if file_bytes[12:16] == b"VP8L" and len(file_bytes) >= 25:
        bits = struct.unpack("<I", file_bytes[21:25])[0]
        width = (bits & 0x3FFF) + 1
        height = ((bits >> 14) & 0x3FFF) + 1
        return width, height
    raise ValueError("Unsupported WebP format")


def validate_upload_image_dimensions(file_bytes: bytes, content_type: str) -> None:
    """
    Reject images outside configured min/max width and height (per side).

    Uses lightweight header parsing only (no Pillow dependency).
    """
    upload_cfg = data_loader.get("file_upload", {})
    min_dim = upload_cfg.get("min_image_dimension", 64)
    max_dim = upload_cfg.get("max_image_dimension", 4096)

    try:
        if content_type == "image/png":
            width, height = _read_png_dimensions(file_bytes)
        elif content_type == "image/jpeg":
            width, height = _read_jpeg_dimensions(file_bytes)
        elif content_type == "image/webp":
            width, height = _read_webp_dimensions(file_bytes)
        else:
            return
    except ValueError:
        log_handler.warning(
            "[validators] reason=upload_invalid_dimensions content_type=%s",
            content_type,
        )
        raise HTTPException(
            status_code=400,
            detail="Image dimensions could not be validated.",
        )

    if width < min_dim or height < min_dim or width > max_dim or height > max_dim:
        log_handler.warning(
            "[validators] reason=upload_dimension_out_of_range width=%s height=%s "
            "min=%s max=%s",
            width,
            height,
            min_dim,
            max_dim,
        )
        raise HTTPException(
            status_code=400,
            detail="Image dimensions are outside the allowed range.",
        )


def validate_upload_file_bytes(file_bytes: bytes, content_type: str | None) -> str:
    """
    Validate upload bytes (size floor, magic bytes, dimensions) and return resolved MIME type.
    """
    upload_cfg = data_loader.get("file_upload", {})
    min_bytes = upload_cfg.get("min_upload_bytes", 100)
    if len(file_bytes) < min_bytes:
        log_handler.warning(
            "[validators] reason=upload_too_small size=%s", len(file_bytes)
        )
        raise HTTPException(
            status_code=400, detail="File is too small to be a valid image."
        )

    resolved_type = (content_type or "").strip().lower()
    if not resolved_type or resolved_type not in MAGIC_BYTES:
        resolved_type = detect_image_content_type(file_bytes)
    if not resolved_type:
        raise HTTPException(status_code=400, detail="Unsupported file type.")

    validate_file_magic_bytes(file_bytes, resolved_type)
    validate_upload_image_dimensions(file_bytes, resolved_type)
    return resolved_type


# Content-policy blocklists live in general_data.json only (banned_keywords and optional
# banned_keywords_hate / banned_keywords_explicit). Update lists there; do not echo
# terms in logs, README examples, or commit messages.
_BF_CFG = data_loader["image_ai_providers"]["black_forest"]
_ALLOWED_PROMPT_CONTROL = {"\n", "\r", "\t"}
_CONTENT_POLICY_REJECT_DETAIL = "Prompt not allowed."
_PROMPT_EMPTY_DETAIL = "Prompt must not be empty."
_PROMPT_LENGTH_DETAIL = "Prompt exceeds the maximum allowed length."
_LEETSPEAK_MAP = str.maketrans(
    {
        "0": "o",
        "1": "i",
        "3": "e",
        "4": "a",
        "5": "s",
        "7": "t",
        "@": "a",
        "$": "s",
    }
)


def _sanitize_prompt_text(prompt: str) -> str:
    """Strip control chars and normalize whitespace; may return an empty string."""
    sanitized = []
    for ch in prompt:
        if ch == " " or ch in _ALLOWED_PROMPT_CONTROL:
            sanitized.append(ch)
        elif unicodedata.category(ch).startswith("C"):
            continue
        else:
            sanitized.append(ch)
    sanitized_str = re.sub(r"\s+", " ", "".join(sanitized)).strip()
    return sanitized_str


def _normalize_prompt_for_policy_check(text: str) -> str:
    """Normalize prompt text for content-policy keyword matching."""
    nfkd = unicodedata.normalize("NFKD", text)
    without_marks = "".join(c for c in nfkd if not unicodedata.combining(c))
    normalized = without_marks.translate(_LEETSPEAK_MAP).lower()
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return _apply_evasion_normalization(normalized)


def _apply_evasion_normalization(text: str) -> str:
    """
    Harden matching against common evasion tactics.

    - Remove punctuation between letters (e.g. n.a.z.i -> nazi)
    - Collapse runs of 3+ repeated characters to a single character
    """
    without_punctuation = re.sub(r"[^\w\s]", "", text)
    collapsed = re.sub(r"(.)\1{2,}", r"\1", without_punctuation)
    return re.sub(r"\s+", " ", collapsed).strip()


def _hash_normalized_prompt_for_log(normalized_text: str) -> str:
    """Return a SHA-256 hex digest for audit logs without storing raw prompt text."""
    return hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()


def _get_merged_banned_keywords() -> list[str]:
    """
    Merge banned keyword lists from config.

    Supports a single `banned_keywords` list plus optional split lists
    (`banned_keywords_hate`, `banned_keywords_explicit`). Duplicates are removed
    while preserving order. Maintain lists only in general_data.json.
    """
    merged: list[str] = []
    seen: set[str] = set()
    for key in ("banned_keywords", "banned_keywords_hate", "banned_keywords_explicit"):
        for term in _BF_CFG.get(key) or []:
            if not term or not str(term).strip():
                continue
            normalized_term = str(term).strip().lower()
            if normalized_term in seen:
                continue
            seen.add(normalized_term)
            merged.append(str(term).strip())
    return merged


def check_banned_keywords(normalized_text: str, banned_list: list[str]) -> bool:
    """
    Return True if normalized_text matches any banned keyword or phrase.

    Single-word terms use word-boundary matching. Multi-word phrases use
    substring matching after normalization.
    """
    if not normalized_text or not banned_list:
        return False

    for term in banned_list:
        if not term or not str(term).strip():
            continue
        term_norm = _normalize_prompt_for_policy_check(str(term))
        if not term_norm:
            continue
        if " " in term_norm:
            if term_norm in normalized_text:
                return True
        elif re.search(rf"\b{re.escape(term_norm)}\b", normalized_text):
            return True
    return False


def _enforce_content_policy(sanitized_str: str, endpoint: str | None = None) -> None:
    """Raise HTTP 400 when content policy is enabled and a banned keyword matches."""
    if not sanitized_str:
        return

    policy_enabled = _BF_CFG.get("content_policy_enabled", False)
    banned_keywords = _get_merged_banned_keywords()
    if not policy_enabled or not banned_keywords:
        return

    normalized = _normalize_prompt_for_policy_check(sanitized_str)
    if check_banned_keywords(normalized, banned_keywords):
        log_handler.warning(
            "[validators] reason=content_policy_keyword endpoint=%s prompt_hash=%s",
            endpoint or "unknown",
            _hash_normalized_prompt_for_log(normalized),
        )
        increment_content_metric("content_policy_keyword")
        raise HTTPException(status_code=400, detail=_CONTENT_POLICY_REJECT_DETAIL)


def validate_prompt_safe(
    prompt: str,
    max_length: int,
    allow_empty: bool = False,
    endpoint: str | None = None,
) -> str:
    """
    Sanitize and validate a user-submitted prompt.

    Steps:
      1. Remove null bytes and Unicode control characters (category C),
         preserving newline (U+000A), carriage return (U+000D),
         tab (U+0009), and space (U+0020).
      2. Collapse consecutive whitespace into a single space.
      3. Strip leading/trailing whitespace.
      4. Reject empty prompts with HTTP 400 (unless allow_empty is True).
      5. Reject banned keywords when content policy is enabled.
      6. Reject prompts exceeding max_length with HTTP 400.

    Args:
        prompt: The raw prompt string from the user.
        max_length: Maximum allowed character length after sanitization.
        allow_empty: When True, whitespace-only prompts return "" without error.

    Returns:
        The sanitized prompt string.

    Raises:
        HTTPException: 400 if prompt is empty, blocked, or exceeds max length.
    """
    sanitized_str = _sanitize_prompt_text(prompt)

    if not sanitized_str:
        if allow_empty:
            return ""
        log_handler.warning(
            "[validators] reason=prompt_empty endpoint=%s",
            endpoint or "unknown",
        )
        raise HTTPException(status_code=400, detail=_PROMPT_EMPTY_DETAIL)

    _enforce_content_policy(sanitized_str, endpoint=endpoint)

    if len(sanitized_str) > max_length:
        log_handler.warning(
            "[validators] reason=prompt_too_long endpoint=%s length=%s max_length=%s",
            endpoint or "unknown",
            len(sanitized_str),
            max_length,
        )
        raise HTTPException(status_code=400, detail=_PROMPT_LENGTH_DETAIL)

    return sanitized_str


def validate_prompt_safe_for_mic(
    prompt: str, max_length: int, endpoint: str | None = "MIC"
) -> str:
    """Validate MIC user instructions; optional whitespace-only prompts are allowed."""
    return validate_prompt_safe(prompt, max_length, allow_empty=True, endpoint=endpoint)


def validate_download_url_allowed(url: str) -> None:
    """
    SSRF check for download URLs: HTTPS only, host in allowlist, no private IPs.

    Validates that:
      1. URL is parseable (has scheme and host)
      2. Scheme is HTTPS
      3. Host is in the configured allowed_download_hosts
      4. Host is not a private/loopback/link-local/reserved address

    Raises HTTPException(400) with a generic message on any failure.

    Args:
        url: The download URL to validate.

    Returns:
        None. Raises HTTPException on failure.
    """
    allowed_download_hosts = set(
        data_loader.get("image_ai_providers", {})
        .get("black_forest", {})
        .get("allowed_download_hosts", [])
    )

    # 1. Check URL is parseable (has scheme and host)
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.hostname:
        log_handler.warning("[validators] Download URL rejected: not parseable")
        raise HTTPException(status_code=400, detail="Invalid download URL.")

    # 2. Check scheme is HTTPS
    if parsed.scheme != "https":
        log_handler.warning("[validators] Download URL rejected: scheme is not HTTPS")
        raise HTTPException(status_code=400, detail="Download URL must be HTTPS.")

    host = (parsed.hostname or "").lower()

    # 3. Check host is in allowed_download_hosts
    if not host or host not in allowed_download_hosts:
        log_handler.warning("[validators] Download URL rejected: host not in allowlist")
        raise HTTPException(status_code=400, detail="Download URL host not allowed.")

    # 4. Check host is not private using _is_private_host()
    if _is_private_host(host):
        log_handler.warning(
            "[validators] Download URL rejected: host is private/reserved"
        )
        raise HTTPException(
            status_code=400,
            detail="Download URL must not point to private or localhost.",
        )
