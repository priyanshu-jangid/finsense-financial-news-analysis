def test_create_company(client):
    response = client.post(
        "/companies",
        json={
            "ticker": "AAPL",
            "name": "Apple Inc.",
            "sector": "Technology",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["ticker"] == "AAPL"
    assert data["name"] == "Apple Inc."
    assert data["sector"] == "Technology"
    assert data["id"] is not None


def test_ticker_is_normalized_to_uppercase(client):
    response = client.post(
        "/companies",
        json={
            "ticker": "msft",
            "name": "Microsoft Corporation",
            "sector": "Technology",
        },
    )

    assert response.status_code == 201
    assert response.json()["ticker"] == "MSFT"


def test_list_companies(client):
    client.post(
        "/companies",
        json={
            "ticker": "AAPL",
            "name": "Apple Inc.",
            "sector": "Technology",
        },
    )

    client.post(
        "/companies",
        json={
            "ticker": "MSFT",
            "name": "Microsoft Corporation",
            "sector": "Technology",
        },
    )

    response = client.get("/companies")

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2
    assert data[0]["ticker"] == "AAPL"
    assert data[1]["ticker"] == "MSFT"


def test_get_company(client):
    create_response = client.post(
        "/companies",
        json={
            "ticker": "NVDA",
            "name": "NVIDIA Corporation",
            "sector": "Technology",
        },
    )

    assert create_response.status_code == 201

    company_id = create_response.json()["id"]

    response = client.get(f"/companies/{company_id}")

    assert response.status_code == 200
    assert response.json()["ticker"] == "NVDA"


def test_get_nonexistent_company(client):
    response = client.get("/companies/9999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Company not found"


def test_duplicate_ticker_is_rejected(client):
    company = {
        "ticker": "AAPL",
        "name": "Apple Inc.",
        "sector": "Technology",
    }

    first_response = client.post(
        "/companies",
        json=company,
    )

    second_response = client.post(
        "/companies",
        json=company,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409

    assert (
        second_response.json()["detail"]
        == "A company with this ticker already exists"
    )
