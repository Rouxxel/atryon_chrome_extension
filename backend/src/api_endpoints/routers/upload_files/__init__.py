"""
#############################################################################
### Upload files router
###
### @file __init__.py
### @author Sebastian Russo
### @date 2025
#############################################################################

Aggregates upload files endpoints.
"""

# Third-party imports
from fastapi import APIRouter

# Other files imports (local routers)
from .upload_images import router as upload_images_router

"""ROUTER AGGREGATION-----------------------------------------------------------"""
router = APIRouter()
router.include_router(upload_images_router)
