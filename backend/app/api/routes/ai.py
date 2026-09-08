"""
AI endpoints (SRS FR-04/FR-05/FR-06/FR-18).

Phase 3 (Image Pipeline) wires /analyze-image and /embed-image to
`app/services/vision.py` (pretrained CLIP, with a deterministic fallback
when the model isn't available — see that module's docstring). Phase 4
(Text Pipeline) wires /embed-text to Sentence Transformers in
`app/services/embeddings.py`, with the same graceful-fallback contract,
and moves the report-quality heuristic into `app/services/quality.py`.
"""
import asyncio
import functools

from fastapi import APIRouter, HTTPException, UploadFile, status

from app.core.config import get_settings
from app.services import embeddings, quality, vision

router = APIRouter(prefix="/ai", tags=["ai"])
settings = get_settings()

CATEGORY_LABELS = vision.CATEGORY_LABELS


async def _read_and_validate_image(file: UploadFile) -> bytes:
    if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image type '{file.content_type}'. "
            f"Allowed: {', '.join(settings.ALLOWED_IMAGE_TYPES)}.",
        )
    data = await file.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")
    max_bytes = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image exceeds the {settings.MAX_IMAGE_SIZE_MB}MB limit.",
        )
    return data


async def _run_in_thread(fn, *args):
    """Run a CPU-bound callable in the default thread-pool executor so it
    doesn't block the async event loop (CLIP / torch inference is purely
    CPU-bound and can hold the GIL for hundreds of milliseconds)."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, functools.partial(fn, *args))


@router.post("/analyze-image")
async def analyze_image(file: UploadFile):
    """FR-04.1/04.2/04.4 — runs CLIP zero-shot category classification plus
    a dominant-color estimate. Confidence below
    CATEGORY_CONFIDENCE_THRESHOLD (or CLIP unavailable) defaults to
    'Other' rather than guessing. All fields remain user-editable
    (FR-04.3)."""
    data = await _read_and_validate_image(file)
    try:
        result = await _run_in_thread(vision.analyze_image_bytes, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return result


@router.post("/embed-image")
async def embed_image(file: UploadFile):
    """FR-06.1 — normalized CLIP image embedding, ready to be collected
    client-side (one call per uploaded photo) and passed along as
    `image_embeddings` on report creation, where they're averaged per
    FR-06.2 (see app/services/reports.py)."""
    data = await _read_and_validate_image(file)
    try:
        embedding = await _run_in_thread(vision.embed_image_bytes, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"embedding": embedding, "dim": len(embedding)}


@router.post("/analyze-and-embed")
async def analyze_and_embed(file: UploadFile):
    """Combined endpoint: runs a SINGLE CLIP forward pass that returns both
    the category/color analysis (FR-04.1/04.2) AND the image embedding
    (FR-06.1) in one HTTP round-trip.

    Replaces the previous two-call pattern (analyze-image + embed-image)
    from the ImageDropzone — halves the CLIP inference time per upload
    because the model encodes the image only once.

    Response schema (superset of both previous endpoints):
      category, confidence, color, brand   — from analyze_image
      embedding, dim                       — from embed_image
    """
    data = await _read_and_validate_image(file)
    try:
        image = vision.decode_image_bytes(data)
        result = await _run_in_thread(vision.analyze_and_embed_image, image)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return result


@router.post("/embed-text")
async def embed_text(text: str):
    """FR-05.1 — normalized Sentence Transformers embedding, ready to be
    used the same way /embed-image is: mainly a manual/debug entry point,
    since report creation/editing generates this embedding server-side
    from title + description + features (see app/services/reports.py)."""
    if not text or not text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="text must not be empty.")
    embedding = await _run_in_thread(embeddings.embed_text, text)
    return {"embedding": embedding, "dim": len(embedding)}


@router.post("/check-report-quality")
async def check_report_quality(description: str, title: str | None = None):
    """FR-18.1 — flags weak/short descriptions (and generic titles),
    suggests distinguishing details. `title` is optional to stay
    backward-compatible with existing callers that only pass description."""
    return quality.check_report_quality(title, description)
