"""Phase 8 — Authentication & Authorization Boundary Tests (SRS Section 2 & Section 7)."""

import uuid
from app.models.report import Report, ReportStatus, ReportType
from app.models.user import RoleEnum, User


def _register_and_get_token(client, email: str, role: RoleEnum = RoleEnum.USER) -> tuple[str, str]:
    res = client.post("/api/auth/register", json={"email": email, "password": "password123"})
    assert res.status_code == 201
    token = res.json()["access_token"]
    user_id = res.json()["user"]["id"]
    return token, user_id


def test_guest_blocked_from_protected_endpoints(client):
    # Reports
    assert client.get("/api/reports/mine").status_code == 401
    assert client.post("/api/reports/lost", json={}).status_code == 401
    assert client.post("/api/reports/found", json={}).status_code == 401
    assert client.get("/api/reports/search").status_code == 401
    # Notifications
    assert client.get("/api/notifications").status_code == 401
    # Admin
    assert client.get("/api/admin/stats").status_code == 401
    assert client.get("/api/admin/reports").status_code == 401
    assert client.get("/api/admin/duplicates").status_code == 401


def test_regular_user_blocked_from_admin_endpoints(client):
    token, _ = _register_and_get_token(client, "regular_user@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/api/admin/stats", headers=headers).status_code == 403
    assert client.get("/api/admin/reports", headers=headers).status_code == 403
    assert client.get("/api/admin/duplicates", headers=headers).status_code == 403
    assert client.patch(f"/api/admin/matches/{uuid.uuid4()}/resolve", headers=headers).status_code == 403
    assert client.patch(f"/api/admin/reports/{uuid.uuid4()}?action=close", headers=headers).status_code == 403


def test_malformed_or_invalid_jwt_rejected(client):
    headers = {"Authorization": "Bearer invalid.jwt.token.string"}
    assert client.get("/api/auth/me", headers=headers).status_code == 401
    assert client.get("/api/reports/mine", headers=headers).status_code == 401


import pytest
from fastapi import HTTPException
from app.services.reports import assert_owner_or_admin


def test_cross_user_report_modification_forbidden():
    class _MockReport:
        def __init__(self, user_id):
            self.user_id = user_id

    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()
    report = _MockReport(user_a_id)

    # User B attempting to modify User A's report raises 403 Forbidden
    with pytest.raises(HTTPException) as exc_info:
        assert_owner_or_admin(report, user_b_id, is_admin=False)
    assert exc_info.value.status_code == 403

    # Admin modifying User A's report is allowed
    assert_owner_or_admin(report, user_b_id, is_admin=True)

    # Owner modifying own report is allowed
    assert_owner_or_admin(report, user_a_id, is_admin=False)
