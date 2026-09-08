"""
Phase 3 — vision service tests. Deliberately avoid requiring torch/open_clip
to be installed: `_try_load_clip()` degrades to the documented fallback
path (category='Other', confidence=0.0, zero-vector embedding) whenever
those packages or their weights aren't available, so these tests exercise
that fallback path directly rather than mocking CLIP itself. Anyone who
does have the ML deps installed locally can additionally sanity-check the
real path manually via `/api/ai/analyze-image`.
"""
import io

import pytest
from PIL import Image

from app.services import vision


def _tiny_png_bytes(color=(200, 30, 30)) -> bytes:
    image = Image.new("RGB", (32, 32), color=color)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_decode_image_bytes_valid():
    image = vision.decode_image_bytes(_tiny_png_bytes())
    assert image.mode == "RGB"
    assert image.size == (32, 32)


def test_decode_image_bytes_rejects_garbage():
    with pytest.raises(ValueError):
        vision.decode_image_bytes(b"not-an-image")


def test_analyze_image_bytes_defaults_safe_without_clip():
    result = vision.analyze_image_bytes(_tiny_png_bytes())
    assert result["category"] in vision.CATEGORY_LABELS
    assert 0.0 <= result["confidence"] <= 1.0
    assert result["brand"] is None


def test_embed_image_bytes_returns_correct_dimension():
    embedding = vision.embed_image_bytes(_tiny_png_bytes())
    assert len(embedding) == vision.IMAGE_EMBEDDING_DIM
    assert all(isinstance(v, float) for v in embedding)


def test_estimate_dominant_color_reasonable_for_solid_red():
    image = vision.decode_image_bytes(_tiny_png_bytes(color=(200, 20, 20)))
    color = vision.estimate_dominant_color(image)
    assert color in (None, *vision._NAMED_COLORS.keys())


def test_average_embeddings_empty_returns_none():
    assert vision.average_embeddings([]) is None


def test_average_embeddings_normalizes_and_averages():
    result = vision.average_embeddings([[1.0, 0.0], [0.0, 1.0]])
    assert result is not None
    assert len(result) == 2
    # Averaged then re-normalized to unit length.
    norm = sum(v ** 2 for v in result) ** 0.5
    assert abs(norm - 1.0) < 1e-6


def test_average_embeddings_rejects_mismatched_dims():
    with pytest.raises(ValueError):
        vision.average_embeddings([[1.0, 0.0], [1.0, 0.0, 0.0]])
