"""
Storage service (Phase 3 — Image upload API).

Persists validated/preprocessed image bytes and returns a URL the frontend
can store in `Report.image_urls` (Architecture Sec. 8). Uses Supabase
Storage when credentials are configured; otherwise falls back to writing
under LOCAL_STORAGE_DIR and serving via the static mount added in
`app/main.py` — so the upload flow works end-to-end in local dev / a
hackathon demo without a Supabase project provisioned yet.

Path convention (Architecture Sec. 8): `reports/{user_id}/{image_id}.jpg`.
The `{report_id}` segment from the doc is intentionally omitted here
because images are uploaded *before* the report exists (the report is
created with the resulting URLs already in hand, per FR-02.1) — noted as a
deliberate, documented deviation rather than an oversight.
"""
from __future__ import annotations

import io
import logging
import uuid

from PIL import Image

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

MAX_DIMENSION = 1600  # long-edge cap; keeps storage + embedding costs down


def preprocess_for_storage(image: Image.Image) -> bytes:
    """Pillow preprocessing (Dev Plan Phase 3): downscale oversized photos
    and re-encode as a consistent JPEG before persisting."""
    resized = image.copy()
    resized.thumbnail((MAX_DIMENSION, MAX_DIMENSION))
    buffer = io.BytesIO()
    resized.save(buffer, format="JPEG", quality=85, optimize=True)
    return buffer.getvalue()


def _build_path(user_id: uuid.UUID, image_id: uuid.UUID) -> str:
    return f"{user_id}/{image_id}.jpg"


def _save_local(path: str, data: bytes) -> str:
    from pathlib import Path

    root = Path(settings.LOCAL_STORAGE_DIR) / settings.STORAGE_BUCKET
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return f"{settings.BACKEND_BASE_URL.rstrip('/')}/media/{settings.STORAGE_BUCKET}/{path}"


def _save_supabase(path: str, data: bytes) -> str:
    from app.core.supabase_client import get_supabase_admin

    client = get_supabase_admin()
    bucket = client.storage.from_(settings.STORAGE_BUCKET)
    bucket.upload(
        path,
        data,
        file_options={"content-type": "image/jpeg", "upsert": "true"},
    )
    return bucket.get_public_url(path)


def save_report_image(user_id: uuid.UUID, image: Image.Image) -> dict:
    """Preprocesses and persists one image, returning its stored URL,
    storage path, and generated image_id (SRS FR-02.3 validation happens
    upstream in the route before this is called)."""
    image_id = uuid.uuid4()
    path = _build_path(user_id, image_id)
    data = preprocess_for_storage(image)

    use_supabase = bool(settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY)
    try:
        url = _save_supabase(path, data) if use_supabase else _save_local(path, data)
    except Exception:
        if use_supabase:
            logger.exception("Supabase Storage upload failed — falling back to local disk.")
            url = _save_local(path, data)
        else:
            raise

    return {"image_id": str(image_id), "path": path, "url": url}
