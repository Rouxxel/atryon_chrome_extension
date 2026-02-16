"""
#############################################################################
### Black Forest API router (multi-image composition)
###
### @file __init__.py
### @author Sebastian Russo
### @date 2025
#############################################################################

Aggregates submit MIC, polling, and download endpoints for BFL FLUX.2.
"""

#Third-party imports
from fastapi import APIRouter

#Other files imports (local routers)
from .submit_mic import router as submit_mic_router
from .polling_requests import router as polling_router
from .download_requests import router as download_router

"""ROUTER AGGREGATION-----------------------------------------------------------"""
router = APIRouter()
router.include_router(submit_mic_router)
router.include_router(polling_router)
router.include_router(download_router)
