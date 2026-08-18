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
import re
import unicodedata
from urllib.parse import urlparse

# Other files imports
from src.utils.custom_logger import log_handler
from src.core_specs.configuration.config_loader import config_loader
from src.core_specs.data.data_loader import data_loader
from fastapi import HTTPException

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
    if (
        host.startswith("127.")
        or host.startswith("10.")
        or host.startswith("192.168.")
        or host.startswith("169.254.")
    ):
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


def validate_prompt_safe(prompt: str, max_length: int) -> str:
    """
    Sanitize and validate a user-submitted prompt.

    Steps:
      1. Remove null bytes and Unicode control characters (category C),
         preserving newline (U+000A), carriage return (U+000D),
         tab (U+0009), and space (U+0020).
      2. Collapse consecutive whitespace into a single space.
      3. Strip leading/trailing whitespace.
      4. Reject empty prompts with HTTP 400.
      5. Reject prompts exceeding max_length with HTTP 400.

    Args:
        prompt: The raw prompt string from the user.
        max_length: Maximum allowed character length after sanitization.

    Returns:
        The sanitized prompt string.

    Raises:
        HTTPException: 400 if prompt is empty or exceeds max length.
    """
    # Preserve these characters even though they are in Unicode category C
    ALLOWED_CONTROL = {"\n", "\r", "\t"}

    # Step 1: Remove null bytes and control characters (Unicode category C)
    sanitized = []
    for ch in prompt:
        if ch == " ":
            sanitized.append(ch)
        elif ch in ALLOWED_CONTROL:
            sanitized.append(ch)
        elif unicodedata.category(ch).startswith("C"):
            continue  # Remove control characters
        else:
            sanitized.append(ch)
    sanitized_str = "".join(sanitized)

    # Step 2: Collapse consecutive whitespace into a single space
    sanitized_str = re.sub(r"\s+", " ", sanitized_str)

    # Step 3: Strip leading and trailing whitespace
    sanitized_str = sanitized_str.strip()

    # Step 4: Reject empty prompts
    if not sanitized_str:
        log_handler.warning("[validators] Prompt rejected: empty after sanitization")
        raise HTTPException(status_code=400, detail="Prompt must not be empty.")

    # Step 5: Reject prompts exceeding configured max length
    if len(sanitized_str) > max_length:
        log_handler.warning(
            "[validators] Prompt rejected: exceeds maximum allowed length"
        )
        raise HTTPException(
            status_code=400, detail="Prompt exceeds the maximum allowed length."
        )

    # Step 6: Return sanitized string for downstream use
    return sanitized_str


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
