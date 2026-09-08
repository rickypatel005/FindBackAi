def _register_and_get_token(client, email: str) -> str:
    res = client.post(
        "/api/auth/register",
        json={"email": email, "password": "correct-horse"},
    )
    return res.json()["access_token"]


def test_regular_user_cannot_access_admin_routes(client):
    token = _register_and_get_token(client, "regular@example.com")
    res = client.get("/api/admin/stats", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403


def test_admin_route_rejects_unauthenticated(client):
    res = client.get("/api/admin/stats")
    assert res.status_code == 401
