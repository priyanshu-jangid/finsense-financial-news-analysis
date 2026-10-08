from fastapi.testclient import TestClient

from backend.app.main import app
from shared.models import Company, User, Watchlist
from tests.test_companies import TestingSessionLocal


client = TestClient(app)


def create_user():
    db = TestingSessionLocal()

    user = User(
        email="test@example.com",
        password_hash="test_hash",
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    db.close()

    return user.id


def create_company(
    ticker: str,
    name: str,
):
    db = TestingSessionLocal()

    company = Company(
        ticker=ticker,
        name=name,
        sector="Technology",
    )

    db.add(company)
    db.commit()
    db.refresh(company)

    db.close()

    return company.id


def setup_function():
    db = TestingSessionLocal()

    db.query(Watchlist).delete()
    db.query(Company).delete()
    db.query(User).delete()

    db.commit()
    db.close()


def test_add_company_to_watchlist():

    user_id = create_user()
    company_id = create_company(
        "AAPL",
        "Apple Inc.",
    )

    response = client.post(
        f"/users/{user_id}/watchlist",
        json={
            "company_id": company_id,
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["user_id"] == user_id
    assert data["company_id"] == company_id
    assert data["id"] is not None


def test_list_user_watchlist():

    user_id = create_user()

    apple_id = create_company(
        "AAPL",
        "Apple Inc.",
    )

    microsoft_id = create_company(
        "MSFT",
        "Microsoft Corporation",
    )

    client.post(
        f"/users/{user_id}/watchlist",
        json={"company_id": apple_id},
    )

    client.post(
        f"/users/{user_id}/watchlist",
        json={"company_id": microsoft_id},
    )

    response = client.get(
        f"/users/{user_id}/watchlist"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2
    assert data[0]["company_id"] == apple_id
    assert data[1]["company_id"] == microsoft_id


def test_duplicate_company_is_rejected():

    user_id = create_user()

    company_id = create_company(
        "AAPL",
        "Apple Inc.",
    )

    first_response = client.post(
        f"/users/{user_id}/watchlist",
        json={"company_id": company_id},
    )

    second_response = client.post(
        f"/users/{user_id}/watchlist",
        json={"company_id": company_id},
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_nonexistent_user_is_rejected():

    company_id = create_company(
        "AAPL",
        "Apple Inc.",
    )

    response = client.post(
        "/users/9999/watchlist",
        json={"company_id": company_id},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_nonexistent_company_is_rejected():

    user_id = create_user()

    response = client.post(
        f"/users/{user_id}/watchlist",
        json={"company_id": 9999},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Company not found"


def test_remove_company_from_watchlist():

    user_id = create_user()

    company_id = create_company(
        "AAPL",
        "Apple Inc.",
    )

    client.post(
        f"/users/{user_id}/watchlist",
        json={"company_id": company_id},
    )

    response = client.delete(
        f"/users/{user_id}/watchlist/{company_id}"
    )

    assert response.status_code == 204

    list_response = client.get(
        f"/users/{user_id}/watchlist"
    )

    assert list_response.status_code == 200
    assert list_response.json() == []


def test_remove_nonexistent_watchlist_entry():

    user_id = create_user()

    company_id = create_company(
        "AAPL",
        "Apple Inc.",
    )

    response = client.delete(
        f"/users/{user_id}/watchlist/{company_id}"
    )

    assert response.status_code == 404

