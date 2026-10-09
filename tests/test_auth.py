
def test_register_user(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "StrongPassword123!",
        },
    )

    assert response.status_code == 201
    assert response.json()["email"] == "test@example.com"
    assert "password_hash" not in response.json()
    assert "password" not in response.json()


def test_register_duplicate_email(client):
    payload = {
        "email": "test@example.com",
        "password": "StrongPassword123!",
    }

    first = client.post("/auth/register", json=payload)
    second = client.post("/auth/register", json=payload)

    assert first.status_code == 201
    assert second.status_code == 409


def test_register_email_is_case_insensitive(client):
    password = "StrongPassword123!"

    first = client.post(
        "/auth/register",
        json={"email": "Test@example.com", "password": password},
    )
    second = client.post(
        "/auth/register",
        json={"email": "test@example.com", "password": password},
    )

    assert first.status_code == 201
    assert second.status_code == 409


def test_register_rejects_short_password(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "short",
        },
    )

    assert response.status_code == 422

def test_login_success(client):
    client.post(
        "/auth/register",
        json={
            "email": "login@example.com",
            "password": "StrongPassword123!",
        },
    )

    response = client.post(
        "/auth/login",
        data={
            "username": "login@example.com",
            "password": "StrongPassword123!",
        },
    )

    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


def test_login_accepts_email_case_insensitively(client):
    client.post(
        "/auth/register",
        json={
            "email": "login@example.com",
            "password": "StrongPassword123!",
        },
    )

    response = client.post(
        "/auth/login",
        data={
            "username": "LOGIN@example.com",
            "password": "StrongPassword123!",
        },
    )

    assert response.status_code == 200


def test_login_rejects_wrong_password(client):
    client.post(
        "/auth/register",
        json={
            "email": "login@example.com",
            "password": "StrongPassword123!",
        },
    )

    response = client.post(
        "/auth/login",
        data={
            "username": "login@example.com",
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401


def test_login_rejects_unknown_email(client):
    response = client.post(
        "/auth/login",
        data={
            "username": "unknown@example.com",
            "password": "StrongPassword123!",
        },
    )

    assert response.status_code == 401


def test_auth_me_returns_current_user(client):
    client.post(
        "/auth/register",
        json={
            "email": "me@example.com",
            "password": "StrongPassword123!",
        },
    )

    login_response = client.post(
        "/auth/login",
        data={
            "username": "me@example.com",
            "password": "StrongPassword123!",
        },
    )

    token = login_response.json()["access_token"]

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"
    assert "password_hash" not in response.json()


def test_auth_me_rejects_missing_token(client):
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_auth_me_rejects_invalid_token(client):
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid.token.value"},
    )

    assert response.status_code == 401
