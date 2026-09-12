"""
#############################################################################
### Upload images temporarily (multipart) for use in MIC / IDWM as upload:<id>
###
### @file upload_images.py
### @author Sebastian Russo
### @date 2025
#############################################################################

POST /upload/images: one or more files, returns upload_ids (array).
Client passes "upload:<uuid>" in images[], image, or mask to MIC/IDWM.
"""

# Third-party imports
from fastapi import APIRouter, Request, HTTPException, UploadFile, File

# Other files imports
from src.utils.custom_logger import log_handler
from src.utils.limiter import limiter as SlowLimiter
from src.utils.upload_store import register
from src.utils.validators import validate_request_size, validate_upload_file_bytes
from src.core_specs.configuration.config_loader import config_loader
from src.core_specs.data.data_loader import data_loader

"""VARIABLES-----------------------------------------------------------"""
FILE_UPLOAD_CFG = data_loader.get("file_upload", {})
UPLOAD_TTL = FILE_UPLOAD_CFG.get("upload_temp_ttl_seconds", 600)
MAX_FILES_PER_UPLOAD = FILE_UPLOAD_CFG.get("max_files_per_upload", 4)
MAX_UPLOAD_BYTES = FILE_UPLOAD_CFG.get("max_upload_bytes", 10485760)

"""API ROUTER-----------------------------------------------------------"""
router = APIRouter(
    prefix=config_loader["endpoints"]["upload_images_endpoint"]["endpoint_prefix"],
    tags=[config_loader["endpoints"]["upload_images_endpoint"]["endpoint_tag"]],
)


async def _process_file(file: UploadFile) -> str:
    """Validate and register one file; return upload_id."""
    body = await file.read()
    if not body:
        raise HTTPException(status_code=400, detail="Empty file not allowed.")
    content_type = validate_upload_file_bytes(body, file.content_type)
    return register(body, content_type)


"""ENDPOINTS-----------------------------------------------------------"""


@router.post(config_loader["endpoints"]["upload_images_endpoint"]["endpoint_route"])
@SlowLimiter.limit(
    f"{config_loader['endpoints']['upload_images_endpoint']['request_limit']}/"
    f"{config_loader['endpoints']['upload_images_endpoint']['unit_of_time_for_limit']}"
)
async def upload_images(
    request: Request,
    files: list[UploadFile] = File(..., description="One or more image files"),
):
    """
    Upload one or more images. Returns upload_ids to use in MIC/IDWM as "upload:<id>".
    Each file is validated (content-type, max size) and stored temporarily (one-time use).
    """
    if not files:
        raise HTTPException(status_code=400, detail="At least one file required.")
    if len(files) > MAX_FILES_PER_UPLOAD:
        raise HTTPException(
            status_code=400,
            detail=f"At most {MAX_FILES_PER_UPLOAD} files per upload request.",
        )

    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            parsed_length = int(content_length)
        except ValueError:
            parsed_length = None
        max_request_bytes = MAX_UPLOAD_BYTES * MAX_FILES_PER_UPLOAD
        validate_request_size(parsed_length, max_bytes=max_request_bytes)

    upload_ids = []
    for f in files:
        if not f.filename and not f.content_type:
            continue
        try:
            uid = await _process_file(f)
            upload_ids.append(uid)
        except HTTPException:
            raise
        except Exception as e:
            log_handler.error(f"[upload_images] Upload failed: {e}")
            raise HTTPException(status_code=500, detail="Upload failed.")
    log_handler.info(f"[upload_images] Uploaded {len(upload_ids)} image(s)")
    return {"upload_ids": upload_ids, "expires_in_seconds": UPLOAD_TTL}
