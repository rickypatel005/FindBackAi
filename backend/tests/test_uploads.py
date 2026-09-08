"""Phase 3 — image upload endpoint tests (SRS FR-02.3, Sec. 8/9)."""
import io
import shutil

import pytest
from PIL import Image

from app.core.config import get_settings

settings = get_settings()


def _tiny_png() -> bytes:
    image = Image.new("RGB", (16, 16), color=(10, 120, 200))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _register_and_get_token(client, email="uploader@example.com") -> str:
    res = client.post("/api/auth/register", json={"email": email, "password": "correct-horse"})
    return res.json()["access_token"]


@pytest.fixture(autouse=True)
def _cleanup_local_storage():
    yield
    shutil.rmtree(settings.LOCAL_STORAGE_DIR, ignore_errors=True)


def test_upload_requires_auth(client):
    res = client.post(
        "/api/uploads/image",
        files={"file": ("photo.png", _tiny_png(), "image/png")},
    )
    assert res.status_code == 401


def test_upload_rejects_bad_content_type(client):
    token = _register_and_get_token(client)
    res = client.post(
        "/api/uploads/image",
        files={"file": ("notes.txt", b"hello", "text/plain")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400


def test_upload_rejects_empty_file(client):
    token = _register_and_get_token(client, "empty@example.com")
    res = client.post(
        "/api/uploads/image",
        files={"file": ("photo.png", b"", "image/png")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400


def test_upload_rejects_corrupt_image_despite_correct_content_type(client):
    token = _register_and_get_token(client, "corrupt@example.com")
    res = client.post(
        "/api/uploads/image",
        files={"file": ("photo.png", b"not-really-a-png", "image/png")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400


def test_upload_success_returns_url(client):
    token = _register_and_get_token(client, "success@example.com")
    res = client.post(
        "/api/uploads/image",
        files={"file": ("photo.png", _tiny_png(), "image/png")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["url"].startswith("http")
    assert body["image_id"]
    assert body["path"]
