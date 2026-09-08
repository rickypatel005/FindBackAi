"""
Image upload endpoint (Dev Plan Phase 3: "Image upload API + validation").

Split from the /ai/* routes on purpose: uploading a file and persisting it
is a storage concern, while /ai/analyze-image and /ai/embed-image are pure
inference over bytes the caller already has. The frontend flow (UIUX Sec.
4.1) calls this once per selected photo to get a durable URL for
`image_urls`, and (optionally) /ai/embed-image on the same file to collect
an embedding to send along at report-creation time.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.core.config import get_settings
from app.core.security import get_current_user
from app.models.user import User
from app.services import storage, vision

router = APIRouter(prefix="/uploads", tags=["uploads"])
settings = get_settings()


@router.post("/image", status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
):
    """SRS FR-02.3 — validates file type + size *before* any AI/storage
    work, then preprocesses (Pillow) and persists the image, returning a
    URL suitable for `Report.image_urls`."""
    if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image type '{file.content_type}'. "
            f"Allowed: {', '.join(settings.ALLOWED_IMAGE_TYPES)}.",
        )

    data = await file.read()
    max_bytes = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024
    if len(data) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image exceeds the {settings.MAX_IMAGE_SIZE_MB}MB limit.",
        )

    try:
        # Re-decodes with Pillow so a mislabeled/corrupt file (wrong
        # content-type header, truncated upload) is caught server-side
        # even if it slipped past client-side checks (SRS Sec. 8/9).
        image = vision.decode_image_bytes(data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    result = storage.save_report_image(current_user.id, image)
    return result
