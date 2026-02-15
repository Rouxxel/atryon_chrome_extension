"""
#############################################################################
### Request limiter file
###
### @file request_limiter.py
### @Sebastian Russo
### @date: 2025
#############################################################################

This module contains a method to handle when a user exceeds the x number of 
allowed requests per x minutes/seconds
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from src.utils.custom_logger import log_handler

async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """
    Handles requests that exceed the allowed rate limit.

    This function is triggered when a client sends too many requests within a given 
    time frame, as defined by the rate limiting middleware. Usually is X requests 
    per minute.

    Parameters:
    request (Request): The incoming HTTP request that triggered the exception.
    exc (RateLimitExceeded): The exception instance containing rate limit details.

    Returns:
    JSONResponse: A 429 Too Many Requests response with a message explaining the rate limit.
    """
    log_handler.warning(f"Rate limit exceeded for IP: {request.client.host}")
    return JSONResponse(
        status_code=429,
        content={"detail": "Request rate limit exceeded. Please try again later."},
    )
