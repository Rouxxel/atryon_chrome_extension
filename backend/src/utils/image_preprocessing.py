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
import os
from typing import List

# Other files imports
from src.utils.custom_logger import log_handler
from src.utils.validators import is_url
from src.core_specs.data.data_loader import data_loader
from fastapi import HTTPException


def image_to_base64(image_path: str) -> str:
    """
    Convert a local image file to a base64-encoded string.

    :param image_path: Path to the image file.
    :return: Base64-encoded string (UTF-8 decoded).
    :raises FileNotFoundError: If the file does not exist.
    """
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    log_handler.debug(f"Encoded local image to base64: {image_path}")
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
    bf = data_loader.get("image_ai_providers", {}).get("black_forest", {})
    min_n = bf.get("min_input_images", 2)
    max_n = bf.get("max_input_images", 4)

    if len(images) < min_n or len(images) > max_n:
        raise HTTPException(
            status_code=400,
            detail=f"Number of images must be between {min_n} and {max_n}, got {len(images)}."
        )

    normalized: List[str] = []
    for i, img in enumerate(images):
        if is_url(img):
            normalized.append(img)
            log_handler.debug(f"Reference image {i + 1}: using URL")
        else:
            normalized.append(img)
            log_handler.debug(f"Reference image {i + 1}: using base64 data")
    return normalized
