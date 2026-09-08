"""
Vision service (Phase 3 — Image Pipeline).

Wraps pretrained CLIP for two things (Architecture Sec. 4, SRS FR-04/FR-06):
  1. Zero-shot category classification against a controlled label set.
  2. Normalized image embedding generation for pgvector similarity search.

Also provides a lightweight, CLIP-independent dominant-color estimator
(K-means over downsampled pixels) so color suggestions work even in
environments where the heavier CLIP weights aren't available.

Design note — graceful degradation:
This module is imported at API-route load time, so it must never raise just
because `torch`/`open_clip` aren't installed or their weights can't be
downloaded (offline hackathon environments, CI, etc.). Every public function
here has a deterministic fallback path, and the fallback is always
*conservative* — it defaults to "Other" / 0.0 confidence rather than
fabricating a guess, consistent with FR-04.4.
"""
from __future__ import annotations

import functools
import io
import logging
from typing import Iterable

import numpy as np
from PIL import Image

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Controlled label set (PRD Sec. 6 / mirrors app/api/routes/ai.py). Kept
# here too so vision.py has no import-time dependency on the routes module.
CATEGORY_LABELS = [
    "Electronics", "Bags", "Wallets", "Documents", "Clothing", "Keys",
    "Books", "Accessories", "Bottles", "Watches", "Earbuds/Headphones", "Other",
]

IMAGE_EMBEDDING_DIM = 512  # ViT-B/32 — must match models/report.py

# A small, named palette for turning an average RGB pixel into a human
# label like "black" / "navy" rather than a raw hex value the user didn't
# type themselves — used only as a *suggestion*, always user-editable.
_NAMED_COLORS: dict[str, tuple[int, int, int]] = {
    "black": (20, 20, 20),
    "white": (245, 245, 245),
    "gray": (128, 128, 128),
    "silver": (192, 192, 192),
    "red": (200, 30, 30),
    "orange": (230, 126, 34),
    "yellow": (230, 210, 40),
    "green": (40, 140, 70),
    "blue": (40, 90, 200),
    "navy": (20, 30, 90),
    "purple": (120, 40, 150),
    "pink": (230, 130, 180),
    "brown": (110, 70, 40),
    "beige": (222, 202, 170),
    "gold": (200, 165, 60),
}


def decode_image_bytes(data: bytes) -> Image.Image:
    """Pillow preprocessing: verify + decode + normalize to RGB.

    Raises ValueError on anything that isn't a genuine, decodable image —
    callers should turn that into an HTTP 400 (SRS Sec. 8: "Unsupported
    image format -> Reject at upload with clear error message").
    """
    try:
        # verify() catches truncated/corrupt files but invalidates the
        # object afterward, so we re-open a fresh copy to actually use it.
        Image.open(io.BytesIO(data)).verify()
        image = Image.open(io.BytesIO(data))
        image = image.convert("RGB")
    except Exception as exc:  # noqa: BLE001 - any decode failure is a 400, not a 500
        raise ValueError(f"File is not a valid image: {exc}") from exc
    return image


@functools.lru_cache(maxsize=1)
def _try_load_clip():
    """Lazily loads the pretrained CLIP model + preprocessing transform.

    Returns (model, preprocess, tokenizer, device) on success, or None if
    open_clip/torch aren't installed, no weights can be fetched, or the
    feature flag is off. Cached so the (expensive) load only happens once
    per process.
    """
    if not settings.ENABLE_IMAGE_AI:
        logger.info("ENABLE_IMAGE_AI is False — vision pipeline running in fallback mode.")
        return None
    try:
        import open_clip
        import torch
    except ImportError:
        logger.warning(
            "open_clip/torch not installed — vision pipeline running in fallback "
            "mode (category='Other', zero-vector embeddings). Install via "
            "requirements.txt to enable real CLIP scoring."
        )
        return None

    try:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model, _, preprocess = open_clip.create_model_and_transforms(
            settings.CLIP_MODEL_NAME,
            pretrained=settings.CLIP_PRETRAINED,
            cache_dir=settings.MODEL_CACHE_DIR,
        )
        model.eval().to(device)
        tokenizer = open_clip.get_tokenizer(settings.CLIP_MODEL_NAME)
        return model, preprocess, tokenizer, device
    except Exception:  # noqa: BLE001 - e.g. no internet to fetch weights
        logger.exception("Failed to load CLIP model — falling back to non-ML heuristic.")
        return None


def classify_image(image: Image.Image) -> tuple[str, float]:
    """FR-04.1/04.4 — zero-shot category classification.

    Scores the image against `f"a photo of a {label}"` prompts for every
    entry in CATEGORY_LABELS and returns the top match with its softmax
    confidence. Below CATEGORY_CONFIDENCE_THRESHOLD (or if CLIP isn't
    available at all), defaults to ("Other", 0.0) rather than guessing.
    """
    loaded = _try_load_clip()
    if loaded is None:
        return "Other", 0.0

    model, preprocess, tokenizer, device = loaded
    import torch

    labels = [label for label in CATEGORY_LABELS if label != "Other"]
    prompts = [f"a photo of a {label.lower()}" for label in labels]

    with torch.no_grad():
        image_tensor = preprocess(image).unsqueeze(0).to(device)
        text_tokens = tokenizer(prompts).to(device)

        image_features = model.encode_image(image_tensor)
        text_features = model.encode_text(text_tokens)
        image_features /= image_features.norm(dim=-1, keepdim=True)
        text_features /= text_features.norm(dim=-1, keepdim=True)

        similarity = (100.0 * image_features @ text_features.T).softmax(dim=-1)
        confidence, index = similarity[0].max(dim=0)

    top_label = labels[int(index)]
    top_confidence = float(confidence)

    if top_confidence < settings.CATEGORY_CONFIDENCE_THRESHOLD:
        return "Other", top_confidence
    return top_label, top_confidence


def embed_image(image: Image.Image) -> list[float]:
    """FR-06.1 — normalized CLIP image embedding for pgvector storage.

    Falls back to a zero-vector of the correct dimensionality when CLIP
    isn't available, so `Report.image_embedding` always has a
    schema-consistent value (and cosine similarity against another
    zero-vector correctly contributes no signal rather than erroring).
    """
    loaded = _try_load_clip()
    if loaded is None:
        return [0.0] * IMAGE_EMBEDDING_DIM

    model, preprocess, _tokenizer, device = loaded
    import torch

    with torch.no_grad():
        image_tensor = preprocess(image).unsqueeze(0).to(device)
        features = model.encode_image(image_tensor)
        features /= features.norm(dim=-1, keepdim=True)

    return features[0].cpu().tolist()


def estimate_dominant_color(image: Image.Image, n_clusters: int = 3) -> str | None:
    """Best-effort dominant-color suggestion (FR-04.2), CLIP-independent.

    Downsamples the image, runs K-means over pixel RGB values, and maps
    the largest cluster's centroid to the nearest named color. Always a
    *suggestion* — the field stays user-editable (UIUX Sec. 7).
    """
    try:
        from sklearn.cluster import KMeans
    except ImportError:
        return None

    try:
        small = image.copy()
        small.thumbnail((64, 64))
        pixels = np.asarray(small).reshape(-1, 3).astype(float)
        if len(pixels) < n_clusters:
            return None

        kmeans = KMeans(n_clusters=n_clusters, n_init=3, random_state=0).fit(pixels)
        counts = np.bincount(kmeans.labels_)
        dominant_rgb = kmeans.cluster_centers_[int(np.argmax(counts))]

        best_name, best_distance = None, float("inf")
        for name, rgb in _NAMED_COLORS.items():
            distance = float(np.linalg.norm(dominant_rgb - np.array(rgb)))
            if distance < best_distance:
                best_name, best_distance = name, distance
        return best_name
    except Exception:  # noqa: BLE001 - color estimation is a nice-to-have, never fatal
        logger.exception("Dominant color estimation failed.")
        return None


def analyze_and_embed_image(image: Image.Image) -> dict:
    """Combined single-pass CLIP inference: classify + embed in one forward pass.

    Avoids the overhead of loading/running the model twice when both outputs
    are needed (e.g. on image upload). Returns a dict with keys:
      - category, confidence  (same as classify_image)
      - color                 (same as analyze_image_bytes)
      - embedding             (same as embed_image)
    """
    loaded = _try_load_clip()

    # Compute embedding regardless — even if CLIP is unavailable we return
    # a zero-vector so callers never have to handle the missing-key case.
    if loaded is None:
        color = estimate_dominant_color(image)
        return {
            "category": "Other",
            "confidence": 0.0,
            "color": color,
            "brand": None,
            "embedding": [0.0] * IMAGE_EMBEDDING_DIM,
            "dim": IMAGE_EMBEDDING_DIM,
        }

    model, preprocess, tokenizer, device = loaded
    import torch

    labels = [label for label in CATEGORY_LABELS if label != "Other"]
    prompts = [f"a photo of a {label.lower()}" for label in labels]

    with torch.no_grad():
        image_tensor = preprocess(image).unsqueeze(0).to(device)
        text_tokens = tokenizer(prompts).to(device)

        # Single encode_image call — reuse features for both tasks
        image_features = model.encode_image(image_tensor)
        text_features = model.encode_text(text_tokens)

        image_features_norm = image_features / image_features.norm(dim=-1, keepdim=True)
        text_features_norm = text_features / text_features.norm(dim=-1, keepdim=True)

        similarity = (100.0 * image_features_norm @ text_features_norm.T).softmax(dim=-1)
        confidence, index = similarity[0].max(dim=0)

    top_label = labels[int(index)]
    top_confidence = float(confidence)

    if top_confidence < settings.CATEGORY_CONFIDENCE_THRESHOLD:
        top_label = "Other"

    embedding = image_features_norm[0].cpu().tolist()
    color = estimate_dominant_color(image)

    return {
        "category": top_label,
        "confidence": round(top_confidence, 4),
        "color": color,
        "brand": None,
        "embedding": embedding,
        "dim": len(embedding),
    }


def analyze_image_bytes(data: bytes) -> dict:
    """Convenience wrapper used by the /ai/analyze-image route: preprocess
    once, then run classification + color estimation on the same decoded
    image (FR-04.1/04.2)."""
    image = decode_image_bytes(data)
    category, confidence = classify_image(image)
    color = estimate_dominant_color(image)
    return {
        "category": category,
        "confidence": round(confidence, 4),
        "color": color,
        "brand": None,  # Brand/logo detection is out of MVP scope (PRD Sec. 6/12); left None for user entry.
    }


def embed_image_bytes(data: bytes) -> list[float]:
    """Convenience wrapper used by the /ai/embed-image route."""
    image = decode_image_bytes(data)
    return embed_image(image)


def average_embeddings(embeddings: Iterable[list[float]]) -> list[float] | None:
    """FR-06.2 — when a report has multiple images, average their
    embeddings into a single vector stored on the report. Returns None for
    an empty input so callers can distinguish "no embeddings supplied"
    from "images with a real zero vector"."""
    vectors = [np.asarray(vec, dtype=float) for vec in embeddings if vec]
    if not vectors:
        return None

    dims = {len(vec) for vec in vectors}
    if len(dims) > 1:
        raise ValueError(f"Cannot average embeddings of mismatched dimensions: {dims}")

    averaged = np.mean(vectors, axis=0)
    norm = np.linalg.norm(averaged)
    if norm > 0:
        averaged = averaged / norm
    return averaged.tolist()
