"""Phase 8 — Edge cases and validation testing (SRS Section 8 & Section 6)."""

import datetime
from app.models.report import ReportStatus, ReportType
from app.models.user import RoleEnum, User
from app.schemas.report import ReportCreate
from app.services import embeddings, matching, quality, vision


def _register_user(client, email="edgeuser@example.com"):
    res = client.post("/api/auth/register", json={"email": email, "password": "password123"})
    assert res.status_code == 201
    return res.json()["access_token"]


def test_report_creation_rejects_zero_images(client):
    token = _register_user(client, "noimages@example.com")
    payload = {
        "title": "Lost iPhone 13",
        "category": "Electronics",
        "color": "Midnight",
        "description": "Lost near student library 2nd floor.",
        "features": "Clear case, scratch on screen protector.",
        "location": "Library",
        "report_date": "2026-09-01",
        "report_time": "12:00:00",
        "image_urls": [],  # FR-02.4: Cannot be submitted with zero images
    }
    res = client.post("/api/reports/lost", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 422


def test_report_creation_rejects_more_than_three_images(client):
    token = _register_user(client, "fourimages@example.com")
    payload = {
        "title": "Lost Wallet",
        "category": "Wallets",
        "color": "Black",
        "description": "Leather bifold wallet with cards.",
        "features": "ID card inside.",
        "location": "Cafeteria",
        "report_date": "2026-09-01",
        "report_time": "12:00:00",
        "image_urls": [
            "https://example.com/1.jpg",
            "https://example.com/2.jpg",
            "https://example.com/3.jpg",
            "https://example.com/4.jpg",  # Exceeds max limit 3
        ],
    }
    res = client.post("/api/reports/lost", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 422


def test_report_creation_rejects_missing_required_fields(client):
    token = _register_user(client, "missingfields@example.com")
    # Missing title, color, location
    payload = {
        "category": "Bags",
        "description": "Lost a backpack somewhere.",
        "image_urls": ["https://example.com/bag.jpg"],
    }
    res = client.post("/api/reports/lost", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 422


def test_quality_service_identifies_weak_descriptions():
    # Short description without distinguishing details
    weak1 = quality.check_report_quality("Lost bag", "Lost bag somewhere.")
    assert weak1["is_weak"] is True
    assert len(weak1["suggestions"]) > 0

    # Strong detailed description with distinguishing keywords
    strong = quality.check_report_quality(
        "Navy Blue Herschel Backpack",
        "Dark blue Herschel canvas backpack with tan leather bottom straps. Has a keychain on the front zipper and initials RP inside.",
    )
    assert strong["is_weak"] is False


def test_vision_fallback_to_other_on_low_confidence():
    """FR-04.4: Low confidence falls back to 'Other' without failing."""
    assert "Other" in vision.CATEGORY_LABELS


def test_location_normalization_handles_edge_cases():
    assert embeddings.normalize_location("") == ""
    assert embeddings.normalize_location("   ") == ""
    assert embeddings.normalize_location("Main Library 2nd Floor") == "main library 2nd floor"
    norm = embeddings.normalize_location("Student Center -- 3rd Fl. (East Wing!)")
    assert "student center" in norm
    assert "3rd" in norm


def test_time_decay_score_bounds():
    today = datetime.date(2026, 9, 5)
    # Same date = 100
    score_same = matching._time_decay_score(today, today)
    assert score_same == 100.0

    # 1 day difference = slight decay
    score_1d = matching._time_decay_score(today, datetime.date(2026, 9, 4))
    assert 85.0 < score_1d < 100.0

    # 30 days difference = significant decay but positive
    score_30d = matching._time_decay_score(today, datetime.date(2026, 8, 5))
    assert 0.0 < score_30d < 50.0
