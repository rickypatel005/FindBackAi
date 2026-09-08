def test_register_returns_token_and_user(client):
    res = client.post(
        "/api/auth/register",
        json={"email": "jane@example.com", "password": "correct-horse", "name": "Jane"},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["user"]["email"] == "jane@example.com"
    assert body["user"]["role"] == "User"
    assert body["access_token"]


def test_register_duplicate_email_rejected(client):
    payload = {"email": "dupe@example.com", "password": "correct-horse"}
    first = client.post("/api/auth/register", json=payload)
    assert first.status_code == 201

    second = client.post("/api/auth/register", json=payload)
    assert second.status_code == 400


def test_login_with_correct_credentials(client):
    client.post(
        "/api/auth/register",
        json={"email": "login@example.com", "password": "correct-horse"},
    )
    res = client.post(
        "/api/auth/login",
        json={"email": "login@example.com", "password": "correct-horse"},
    )
    assert res.status_code == 200
    assert res.json()["user"]["email"] == "login@example.com"


def test_login_with_wrong_password_rejected(client):
    client.post(
        "/api/auth/register",
        json={"email": "wrongpw@example.com", "password": "correct-horse"},
    )
    res = client.post(
        "/api/auth/login",
        json={"email": "wrongpw@example.com", "password": "not-the-password"},
    )
    assert res.status_code == 401


def test_me_requires_valid_token(client):
    register_res = client.post(
        "/api/auth/register",
        json={"email": "me@example.com", "password": "correct-horse", "name": "Me"},
    )
    token = register_res.json()["access_token"]

    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["email"] == "me@example.com"


def test_me_rejects_missing_token(client):
    res = client.get("/api/auth/me")
    assert res.status_code == 401


def test_me_rejects_garbage_token(client):
    res = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert res.status_code == 401
