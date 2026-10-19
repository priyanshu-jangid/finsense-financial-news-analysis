"""Tests for news article retrieval, filtering, pagination, and ingestion API endpoints."""
from backend.app.core.config import settings
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest

from backend.app.core.security import create_access_token
from backend.app.services.news_provider import MarketauxClient
from shared.models import Article, ArticleEntity, Company, IngestionCheckpoint, Source, User


@pytest.fixture
def auth_headers(db):
    user = User(email="analyst@finsense.com", password_hash="hashed_pw")
    db.add(user)
    db.commit()
    token = create_access_token(str(user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def seeded_articles(db):
    source1 = Source(name="Reuters", domain="reuters.com", credibility_tier=1)
    source2 = Source(name="Bloomberg", domain="bloomberg.com", credibility_tier=1)
    apple = Company(ticker="AAPL", name="Apple Inc.", sector="Technology")
    tcs = Company(ticker="TCS", name="Tata Consultancy Services", sector="Technology")

    db.add_all([source1, source2, apple, tcs])
    db.commit()

    # Company article (Apple)
    art1 = Article(
        source_id=source1.id,
        title="Apple announces record quarterly profit",
        url="https://reuters.com/apple-profit",
        summary="Record quarterly profit driven by services.",
        published_at=datetime(2026, 10, 14, 10, 0, 0),
        fetched_at=datetime(2026, 10, 14, 10, 5, 0),
    )

    # Company article (TCS)
    art2 = Article(
        source_id=source2.id,
        title="TCS signs massive digital transformation deal",
        url="https://bloomberg.com/tcs-deal",
        summary="TCS expands presence in European enterprise banking.",
        published_at=datetime(2026, 10, 14, 9, 0, 0),
        fetched_at=datetime(2026, 10, 14, 9, 5, 0),
    )

    # Broad market news (no company linked)
    art3 = Article(
        source_id=source1.id,
        title="RBI keeps repo rate unchanged at 6.5 percent amid inflation moderation",
        url="https://reuters.com/rbi-monetary-policy-decision",
        summary="Reserve Bank of India Monetary Policy Committee maintains status quo.",
        published_at=datetime(2026, 10, 14, 8, 0, 0),
        fetched_at=datetime(2026, 10, 14, 8, 5, 0),
    )

    db.add_all([art1, art2, art3])
    db.commit()

    ent1 = ArticleEntity(article_id=art1.id, company_id=apple.id, relevance_score=0.92)
    ent2 = ArticleEntity(article_id=art2.id, company_id=tcs.id, relevance_score=0.88)
    db.add_all([ent1, ent2])
    db.commit()

    return {
        "source1": source1,
        "source2": source2,
        "apple": apple,
        "tcs": tcs,
        "art1": art1,
        "art2": art2,
        "art3": art3,
    }


def test_list_articles_pagination(client, seeded_articles):
    response = client.get("/articles?page=1&page_size=2")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert data["total_pages"] == 2
    assert len(data["items"]) == 2

    # Second page
    response2 = client.get("/articles?page=2&page_size=2")
    assert response2.status_code == 200
    data2 = response2.json()
    assert len(data2["items"]) == 1


def test_news_read_does_not_call_external_provider(client, seeded_articles):
    with patch("backend.app.services.news_provider.MarketauxClient.fetch_news") as mock_fetch:
        response = client.get("/articles")
        assert response.status_code == 200
        mock_fetch.assert_not_called()


def test_company_specific_news_endpoint(client, seeded_articles):
    apple = seeded_articles["apple"]
    response = client.get(f"/articles/company/{apple.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Apple announces record quarterly profit"
    assert data["items"][0]["entities"][0]["company_id"] == apple.id


def test_company_specific_news_not_found(client):
    response = client.get("/articles/company/999999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Company not found"


def test_market_feed_excludes_company_specific_articles(client, seeded_articles):
    response = client.get("/articles/market")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    item = data["items"][0]
    assert "RBI" in item["title"]
    assert len(item["entities"]) == 0


def test_invalid_pagination_parameters(client):
    response = client.get("/articles?page=0")
    assert response.status_code == 422

    response2 = client.get("/articles?page_size=101")
    assert response2.status_code == 422


def test_manual_ingestion_requires_authentication(client):
    response = client.post("/articles/ingest")
    assert response.status_code == 401


def test_manual_ingestion_authenticated_success(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        settings,
        "INGESTION_OPERATOR_EMAILS",
        "analyst@finsense.com",
    )
    mock_response = {
        "data": [
            {
                "uuid": "mock-ingest-uuid",
                "title": "SEBI releases new guidelines for algorithmic trading",
                "url": "https://reuters.com/markets/sebi-algo-rules",
                "published_at": "2026-10-14T11:00:00Z",
                "source": "reuters.com",
            }
        ]
    }

    with patch.object(MarketauxClient, "get_company_news", return_value={"data": []}), \
         patch.object(MarketauxClient, "get_broad_news", return_value=mock_response):
        response = client.post("/articles/ingest", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("success", "partial_failure")
        assert data["broad_feed"]["articles_persisted"] == 1

def test_manual_ingestion_forbidden_for_non_operator(
    client, auth_headers, monkeypatch
):
    monkeypatch.setattr(
        settings,
        "INGESTION_OPERATOR_EMAILS",
        "authorized@example.com",
    )

    response = client.post(
        "/articles/ingest",
        headers=auth_headers,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "User not authorized to trigger ingestion"
    )

def test_ingestion_status_endpoint(client, db):
    cp = IngestionCheckpoint(
        feed_type="company",
        status="success",
        articles_fetched=5,
        articles_persisted=4,
        last_successful_published_at=datetime(2026, 10, 14, 12, 0, 0),
    )
    db.add(cp)
    db.commit()

    response = client.get("/articles/ingestion-status")
    assert response.status_code == 200
    data = response.json()
    assert "is_scheduler_running" in data
    assert "checkpoints" in data
    assert any(c["feed_type"] == "company" for c in data["checkpoints"])
