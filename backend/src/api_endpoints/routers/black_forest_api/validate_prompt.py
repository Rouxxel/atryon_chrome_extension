"""
#############################################################################
### Validate user prompt for content policy (no BFL call)
###
### @file validate_prompt.py
### @author Sebastian Russo
### @date 2025
#############################################################################

Lightweight endpoint for clients to check try-on instructions before upload/MIC.
Reuses the same sanitization and keyword policy as submit_mic.
"""

# Third-party imports
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from src.core_specs.configuration.config_loader import config_loader
from src.core_specs.data.data_loader import data_loader

# Other files imports
from src.utils.custom_logger import log_handler
from src.utils.limiter import limiter as SlowLimiter
from src.utils.validators import validate_prompt_safe_for_mic

"""VARIABLES-----------------------------------------------------------"""
BF_CFG = data_loader["image_ai_providers"]["black_forest"]

"""API ROUTER-----------------------------------------------------------"""
router = APIRouter(
    prefix=config_loader["endpoints"]["validate_prompt_endpoint"]["endpoint_prefix"],
    tags=[config_loader["endpoints"]["validate_prompt_endpoint"]["endpoint_tag"]],
)

"""ENDPOINT-----------------------------------------------------------"""


class ValidatePromptBody(BaseModel):
    """Request body: user prompt to validate for MIC / try-on."""

    prompt: str = Field(
        default="",
        max_length=BF_CFG.get("max_prompt_length", 400) + 64,
        description="Try-on instructions to validate (empty is allowed)",
    )


@router.post(config_loader["endpoints"]["validate_prompt_endpoint"]["endpoint_route"])
@SlowLimiter.limit(
    f"{config_loader['endpoints']['validate_prompt_endpoint']['request_limit']}/"
    f"{config_loader['endpoints']['validate_prompt_endpoint']['unit_of_time_for_limit']}"
)
async def validate_prompt(request: Request, body: ValidatePromptBody):
    """
    Validate user prompt against sanitization and content policy.

    Does not call Black Forest Labs. Whitespace-only prompts are allowed for try-on.
    """
    log_handler.debug("[validate_prompt] Validate prompt request received")
    validate_prompt_safe_for_mic(
        body.prompt, BF_CFG.get("max_prompt_length", 400), endpoint="VALIDATE"
    )
    return {"ok": True}
