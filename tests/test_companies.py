from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.database import get_db
from backend.app.main import app
from shared.models import Base


TEST_DATABASE_URL = "sqlite://"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_create_company():
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


def test_ticker_is_normalized_to_uppercase():
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


def test_list_companies():
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


def test_get_company():
    create_response = client.post(
        "/companies",
        json={
            "ticker": "NVDA",
            "name": "NVIDIA Corporation",
            "sector": "Technology",
        },
    )

    company_id = create_response.json()["id"]

    response = client.get(f"/companies/{company_id}")

    assert response.status_code == 200
    assert response.json()["ticker"] == "NVDA"


def test_get_nonexistent_company():
    response = client.get("/companies/9999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Company not found"


def test_duplicate_ticker_is_rejected():
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
