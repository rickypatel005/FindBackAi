"""Phase 3 — /ai/analyze-image and /ai/embed-image route tests."""
import io

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.services import embeddings, vision

client = TestClient(app)


def _tiny_png() -> bytes:
    image = Image.new("RGB", (16, 16), color=(30, 30, 30))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_analyze_image_returns_valid_category():
    res = client.post("/api/ai/analyze-image", files={"file": ("photo.png", _tiny_png(), "image/png")})
    assert res.status_code == 200
    body = res.json()
    assert body["category"] in vision.CATEGORY_LABELS
    assert "confidence" in body


def test_analyze_image_rejects_bad_type():
    res = client.post("/api/ai/analyze-image", files={"file": ("f.txt", b"hi", "text/plain")})
    assert res.status_code == 400


def test_embed_image_returns_vector_of_expected_length():
    res = client.post("/api/ai/embed-image", files={"file": ("photo.png", _tiny_png(), "image/png")})
    assert res.status_code == 200
    body = res.json()
    assert body["dim"] == vision.IMAGE_EMBEDDING_DIM
    assert len(body["embedding"]) == body["dim"]


def test_check_report_quality_unchanged():
    res = client.post("/api/ai/check-report-quality?description=short")
    assert res.status_code == 200
    assert res.json()["is_weak"] is True


def test_check_report_quality_accepts_optional_title():
    res = client.post("/api/ai/check-report-quality?description=short&title=item")
    assert res.status_code == 200
    body = res.json()
    assert body["is_weak"] is True
    assert len(body["suggestions"]) >= 2


def test_embed_text_returns_vector_of_expected_length():
    res = client.post("/api/ai/embed-text?text=A%20blue%20backpack%20with%20a%20torn%20strap")
    assert res.status_code == 200
    body = res.json()
    assert body["dim"] == embeddings.TEXT_EMBEDDING_DIM
    assert len(body["embedding"]) == body["dim"]


def test_embed_text_rejects_empty_text():
    res = client.post("/api/ai/embed-text?text=")
    assert res.status_code == 400
