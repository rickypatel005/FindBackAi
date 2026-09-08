"""
Text embeddings service (Phase 4 — Text Pipeline).

Wraps pretrained Sentence Transformers for FR-05 (SRS): concatenates
title + description + features and encodes them into a normalized
embedding for pgvector similarity search against the opposite-type
candidate pool (FR-07, matching.py).

Design note — graceful degradation (mirrors app/services/vision.py):
This module is imported at API-route load time, so it must never raise
just because `sentence-transformers`/`torch` aren't installed or their
weights can't be downloaded (offline hackathon environments, CI, etc.).
`embed_text` always returns a schema-consistent zero-vector fallback in
that case rather than erroring, so report creation / editing still works
end-to-end (Architecture Sec. 13 risk table entries carry over).
"""
from __future__ import annotations

import functools
import logging
import re

import numpy as np

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

TEXT_EMBEDDING_DIM = 384  # all-MiniLM-L6-v2 — must match models/report.py


@functools.lru_cache(maxsize=1)
def _try_load_model():
    """Lazily loads the pretrained Sentence Transformers model.

    Returns the model instance on success, or None if
    `sentence-transformers` isn't installed, no weights can be fetched, or
    the feature flag is off. Cached so the (expensive) load only happens
    once per process — same pattern as vision._try_load_clip().
    """
    if not settings.ENABLE_TEXT_AI:
        logger.info("ENABLE_TEXT_AI is False — text pipeline running in fallback mode.")
        return None
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        logger.warning(
            "sentence-transformers not installed — text pipeline running in "
            "fallback mode (zero-vector embeddings). Install via "
            "requirements.txt to enable real text similarity scoring."
        )
        return None

    try:
        return SentenceTransformer(
            settings.SENTENCE_TRANSFORMER_MODEL,
            cache_folder=settings.MODEL_CACHE_DIR,
        )
    except Exception:  # noqa: BLE001 - e.g. no internet to fetch weights
        logger.exception("Failed to load Sentence Transformers model — falling back to zero-vector.")
        return None


def build_report_text(title: str | None, description: str | None, features: str | None = None) -> str:
    """FR-05.1 — Title + Description + Features are concatenated before
    encoding. Empty/None fields are skipped so a missing `features` value
    (it's optional per FR-02.1) doesn't pollute the string with 'None'."""
    parts = [p.strip() for p in (title, description, features) if p and p.strip()]
    return ". ".join(parts)


def embed_text(text: str) -> list[float]:
    """FR-05.1 — normalized Sentence Transformers embedding for pgvector
    storage. Falls back to a zero-vector of the correct dimensionality
    when the model isn't available, matching vision.embed_image's
    contract (cosine similarity against another zero-vector contributes
    no signal rather than erroring)."""
    model = _try_load_model()
    if model is None or not text.strip():
        return [0.0] * TEXT_EMBEDDING_DIM

    vector = model.encode(text, normalize_embeddings=True)
    return np.asarray(vector, dtype=float).tolist()


def embed_report_text(title: str | None, description: str | None, features: str | None = None) -> list[float]:
    """Convenience wrapper used by services/reports.py on report
    create/update (FR-05.1/05.2)."""
    text = build_report_text(title, description, features)
    return embed_text(text)


# --- Metadata normalization (FR-05 task: "location aliases, etc.") ---

# A small alias table so common location phrasings collapse to the same
# canonical string before comparison/embedding — e.g. a lost report logged
# at "Bldg 3" and a found report logged at "Building 3" should still score
# a location match without requiring GPS (PRD Sec. 12/13, Architecture
# Sec. 13: "Weak location semantics without GPS -> text similarity +
# normalized location aliases"). Deliberately small/generic for MVP; not
# meant to be exhaustive.
_LOCATION_ALIASES: dict[str, str] = {
    "bldg": "building",
    "blvd": "boulevard",
    "st": "street",
    "rd": "road",
    "ave": "avenue",
    "apt": "apartment",
    "fl": "floor",
    "flr": "floor",
    "lvl": "level",
    "ctr": "center",
    "univ": "university",
    "lib": "library",
    "caf": "cafe",
    "cafeteria": "cafe",
    "carpark": "parking lot",
    "car park": "parking lot",
    "parking garage": "parking lot",
}

_WHITESPACE_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[.,#\-_/]")


def normalize_location(value: str | None) -> str:
    """Lowercases, strips punctuation, and expands known abbreviations so
    metadata comparison (matching.py location_score) isn't defeated by
    superficial phrasing differences. Returns "" for empty input so
    callers can treat that as "no location signal" rather than a match."""
    if not value:
        return ""

    text = value.strip().lower()
    text = _PUNCT_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()

    tokens = [
        _LOCATION_ALIASES.get(token, token)
        for token in text.split(" ")
        if token
    ]
    # Multi-word aliases (e.g. "car park") are handled as a final pass over
    # the rejoined string, since they span more than one token.
    normalized = " ".join(tokens)
    for phrase, canonical in _LOCATION_ALIASES.items():
        if " " in phrase:
            normalized = normalized.replace(phrase, canonical)
    return normalized
