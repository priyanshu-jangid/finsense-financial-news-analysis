from shared.models import Company, User, Watchlist


def create_user(db):
    user = User(
        email="test@example.com",
        password_hash="test_hash",
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user.id


def create_company(db, ticker, name):
    company = Company(
        ticker=ticker,
        name=name,
        sector="Technology",
    )

    db.add(company)
    db.commit()
    db.refresh(company)

    return company.id


def test_add_company_to_watchlist(client, db):
    user_id = create_user(db)
    company_id = create_company(
        db,
        "AAPL",
        "Apple Inc.",
    )

    response = client.post(
        f"/users/{user_id}/watchlist",
        json={"company_id": company_id},
    )

    assert response.status_code == 201

    data = response.json()

    assert data["user_id"] == user_id
    assert data["company_id"] == company_id
    assert data["id"] is not None


def test_list_user_watchlist(client, db):
    user_id = create_user(db)

    apple_id = create_company(
        db,
        "AAPL",
        "Apple Inc.",
    )

    microsoft_id = create_company(
        db,
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


def test_duplicate_company_is_rejected(client, db):
    user_id = create_user(db)

    company_id = create_company(
        db,
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


def test_nonexistent_user_is_rejected(client, db):
    company_id = create_company(
        db,
        "AAPL",
        "Apple Inc.",
    )

    response = client.post(
        "/users/9999/watchlist",
        json={"company_id": company_id},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_nonexistent_company_is_rejected(client, db):
    user_id = create_user(db)

    response = client.post(
        f"/users/{user_id}/watchlist",
        json={"company_id": 9999},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Company not found"


def test_remove_company_from_watchlist(client, db):
    user_id = create_user(db)

    company_id = create_company(
        db,
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


def test_remove_nonexistent_watchlist_entry(client, db):
    user_id = create_user(db)

    company_id = create_company(
        db,
        "AAPL",
        "Apple Inc.",
    )

    response = client.delete(
        f"/users/{user_id}/watchlist/{company_id}"
    )

    assert response.status_code == 404
