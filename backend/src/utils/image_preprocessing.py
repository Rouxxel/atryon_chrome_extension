"""
#############################################################################
### Image preprocessing methods
###
### @file image_preprocessing.py
### @author Sebastian Russo
### @date 2025
#############################################################################

This module provides methods to preprocess images before sending them
to the Black Forest (BFL) API for multi-image composition. Images can be
public URLs (passed through) or base64-encoded strings (e.g. from local files).
"""

# Native imports
import base64
from pathlib import Path
from typing import List

# Other files imports
from src.utils.custom_logger import log_handler
from src.utils.validators import is_url, validate_image_url_safe
from src.utils.upload_store import (
    is_upload_reference,
    extract_upload_id,
    resolve as resolve_upload,
)
from src.core_specs.data.data_loader import data_loader
from fastapi import HTTPException

# Define a strictly controlled base directory for your images
IMAGE_SAFE_ZONE = Path("data/uploads").resolve()

def image_to_base64(image_path: str) -> str:
    """
    Convert a local image file to a base64-encoded string with path validation.
    """
    # Resolve to absolute path and handle symlinks/redundant separators
    requested_path = Path(image_path).resolve()

    # Check if the requested path is strictly within the safe directory
    if not requested_path.is_relative_to(IMAGE_SAFE_ZONE):
        log_handler.error(
            f"[image_preprocessing] Security Alert: Attempted access outside safe zone: {requested_path}"
        )
        raise HTTPException(
            status_code=403, detail="Access to the requested path is forbidden."
        )

    if not requested_path.is_file():
        raise FileNotFoundError(f"Image not found: {requested_path}")

    # Read and encode using pathlib for safer file handling
    encoded = base64.b64encode(requested_path.read_bytes()).decode("utf-8")

    log_handler.debug(
        f"[image_preprocessing] Encoded local image to base64: {requested_path}"
    )
    return encoded


def normalize_reference_images(images: List[str]) -> List[str]:
    """
    Normalize reference images into BFL-compatible identifiers.

    - URLs (http/https) are passed through unchanged.
    - Non-URL strings are treated as base64 image data and passed through.
    - Validates count against config (min_input_images, max_input_images).

    :param images: List of image URLs or base64-encoded image strings.
    :return: List of image identifiers (URLs or base64 strings).
    :raises HTTPException: If image count is out of range.
    """
    flux2 = (
        data_loader.get("image_ai_providers", {})
        .get("black_forest", {})
        .get("flux2", {})
    )
    min_n = flux2.get("min_input_images", 2)
    max_n = flux2.get("max_input_images", 4)

    if len(images) < min_n or len(images) > max_n:
        raise HTTPException(
            status_code=400,
            detail=f"Number of images must be between {min_n} and {max_n}, got {len(images)}.",
        )

    normalized: List[str] = []
    for i, img in enumerate(images):
        if is_url(img):
            validate_image_url_safe(img)
            normalized.append(img)
            log_handler.debug(
                f"[image_preprocessing] Reference image {i + 1}: using URL"
            )
        elif is_upload_reference(img):
            upload_id = extract_upload_id(img)
            b64 = resolve_upload(upload_id)
            normalized.append(b64)
            log_handler.debug(
                f"[image_preprocessing] Reference image {i + 1}: resolved upload to base64"
            )
        else:
            normalized.append(img)
            log_handler.debug(
                f"[image_preprocessing] Reference image {i + 1}: using base64 data"
            )
    return normalized
