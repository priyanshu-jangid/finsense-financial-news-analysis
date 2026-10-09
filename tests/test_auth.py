
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
