# Combined tests for sentiment analysis endpoints (T4, T5, T7)

import pytest
from fastapi.testclient import TestClient
from backend.app.core.database import get_db
from shared.models import Company, Article, ArticleEntity, SentimentAnalysis
from backend.app.tasks.sentiment_scheduler import _run_analysis_job
from backend.app.services.company_sentiment_service import analyse_pending_articles

# Fixtures from conftest provide 'client' and 'db'

def test_trigger_sentiment_analysis_401_without_token(client, db):
    """T4: Ensure authentication is required."""
    company = Company(ticker="TST", name="TestCo", sector="Tech")
    db.add(company)
    db.commit()
    db.refresh(company)
    response = client.post(f"/companies/{company.id}/sentiment/analyze")
    assert response.status_code == 401

def test_trigger_sentiment_analysis_200_with_token_and_mock_engine(client, db, monkeypatch):
    """T4: Successful analysis with mocked SentimentEngine."""
    # Register and login
    client.post("/auth/register", json={"email": "user@example.com", "password": "StrongPass1!"})
    login_resp = client.post("/auth/login", data={"username": "user@example.com", "password": "StrongPass1!"})
    token = login_resp.json()["access_token"]

    # Create company, article, association
    company = Company(ticker="TST", name="TestCo", sector="Tech")
    article = Article(title="Test Article", content="Some content")
    db.add_all([company, article])
    db.commit()
    db.refresh(company)
    db.refresh(article)
    db.add(ArticleEntity(article_id=article.id, company_id=company.id))
    db.commit()

    # Mock SentimentEngine used inside service
    class MockEngine:
        def __init__(self, model_name=None):
            pass
        def analyze(self, text):
            return {"label": "positive", "score": 0.9, "confidence": 0.95, "model_used": "mock-model"}
    monkeypatch.setattr("backend.app.services.sentiment_engine.SentimentEngine", MockEngine)

    response = client.post(
        f"/companies/{company.id}/sentiment/analyze",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["created"] == 1

    # Verify persisted row
    persisted = db.query(SentimentAnalysis).filter(SentimentAnalysis.company_id == company.id).first()
    assert persisted is not None
    assert persisted.label == "positive"
    assert persisted.model_used == "mock-model"

def test_run_analysis_job_commits_per_company(monkeypatch, db):
    """T5: Verify per‑company commit and rollback on failure."""
    # Create two companies with pending articles
    company1 = Company(ticker="C1", name="Comp1", sector="Tech")
    article1 = Article(title="A1", content="Content 1")
    db.add_all([company1, article1])
    db.commit()
    db.refresh(company1)
    db.refresh(article1)
    db.add(ArticleEntity(article_id=article1.id, company_id=company1.id))

    company2 = Company(ticker="C2", name="Comp2", sector="Tech")
    article2 = Article(title="A2", content="Content 2")
    db.add_all([company2, article2])
    db.commit()
    db.refresh(company2)
    db.refresh(article2)
    db.add(ArticleEntity(article_id=article2.id, company_id=company2.id))
    db.commit()

    # Mock SentimentEngine for real analyse function (engine is passed directly to job)
    class MockEngine:
        def analyze(self, text):
            return {"label": "positive", "score": 0.9, "confidence": 0.95, "model_used": "mock-model"}

    # Import the real analyse_pending_articles for success case
    from backend.app.services.company_sentiment_service import analyse_pending_articles as real_analyse

    # Fake analyse_pending_articles: succeed for first, raise for second; accept engine argument
    call_order = []
    def fake_analyse(db_arg, company_id, engine=None):
        call_order.append(company_id)
        if company_id == company1.id:
            return real_analyse(db_arg, company_id, engine=engine)
        raise Exception("simulated failure")
    monkeypatch.setattr("backend.app.tasks.sentiment_scheduler.analyse_pending_articles", fake_analyse)

    # Patch SessionLocal to return the test session (avoid closing)
    from tests.conftest import TestingSessionLocal
    monkeypatch.setattr("backend.app.tasks.sentiment_scheduler.SessionLocal", TestingSessionLocal)

    # Run the job with the mock engine injected
    _run_analysis_job(engine=MockEngine())

    # Use a fresh session to verify persistence
    from tests.conftest import TestingSessionLocal
    new_session = TestingSessionLocal()
    try:
        stmt1 = new_session.query(SentimentAnalysis).filter(SentimentAnalysis.company_id == company1.id).first()
        stmt2 = new_session.query(SentimentAnalysis).filter(SentimentAnalysis.company_id == company2.id).first()
    finally:
        new_session.close()

    assert stmt1 is not None
    assert stmt2 is None
    # Ensure both companies were processed
    assert call_order == [company1.id, company2.id]

    # Use a fresh session to verify persistence

    assert stmt1 is not None
    assert stmt2 is None
    # Ensure both companies were processed
    assert call_order == [company1.id, company2.id]

def test_cors_allowed_origin(client):
    """T7: Request with an allowed Origin receives CORS headers."""
    response = client.get("/", headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"

def test_cors_disallowed_origin(client):
    """T7: Request with a disallowed Origin does not receive CORS headers."""
    response = client.get("/", headers={"Origin": "http://evil.com"})
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers

def test_trigger_sentiment_analysis_503_engine_failure(client, db, monkeypatch):
    """T4: Engine fails to load, endpoint returns 5xx and does not create a row."""
    # Register and login
    client.post("/auth/register", json={"email": "user2@example.com", "password": "StrongPass1!"})
    login_resp = client.post("/auth/login", data={"username": "user2@example.com", "password": "StrongPass1!"})
    token = login_resp.json()["access_token"]

    # Create company and article
    company = Company(ticker="FAIL", name="FailCo", sector="Tech")
    article = Article(title="Bad Article", content="Bad content")
    db.add_all([company, article])
    db.commit()
    db.refresh(company)
    db.refresh(article)
    db.add(ArticleEntity(article_id=article.id, company_id=company.id))
    db.commit()

    # Patch SentimentEngine to raise ImportError
    def raise_import_error(*args, **kwargs):
        raise ImportError("Engine not available")
    monkeypatch.setattr("nlp.pipeline.sentiment.SentimentEngine", raise_import_error)

    response = client.post(
        f"/companies/{company.id}/sentiment/analyze",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 503
    # Verify no sentiment row was created
    persisted = db.query(SentimentAnalysis).filter(SentimentAnalysis.company_id == company.id).first()
    assert persisted is None
