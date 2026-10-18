import pytest
from datetime import datetime, date, timezone, timedelta
from fastapi.testclient import TestClient
from shared.models import Company, Article, SentimentAnalysis

# Helper to create a company

def create_company(db, ticker: str, name: str, sector: str = None):
    company = Company(ticker=ticker.upper(), name=name, sector=sector)
    db.add(company)
    db.flush()  # assign id
    return company

# Helper to create an article linked to a company

def create_article(db, company_id: int, title: str = "Test", content: str = "content"):
    article = Article(title=title, content=content, company_id=company_id)
    db.add(article)
    db.flush()
    return article

import itertools
_model_counter = itertools.count(1)

# Helper to create a SentimentAnalysis record

def create_sentiment(db, article_id: int, company_id: int, label: str, score: float, created_at: datetime):
    sentiment = SentimentAnalysis(
        article_id=article_id,
        company_id=company_id,
        label=label,
        score=score,
        confidence=0.99,
        model_used=f"mock-model-{next(_model_counter)}",
        created_at=created_at,
    )
    db.add(sentiment)
    db.flush()
    return sentiment

def test_sentiment_aggregation_counts_and_average(client: TestClient, db):
    # Setup data
    comp = create_company(db, "AAA", "Alpha Co")
    art1 = create_article(db, comp.id)
    art2 = create_article(db, comp.id)
    now = datetime.now(timezone.utc)
    create_sentiment(db, art1.id, comp.id, "positive", 0.8, now - timedelta(days=1))
    create_sentiment(db, art1.id, comp.id, "neutral", 0.0, now - timedelta(days=1))
    create_sentiment(db, art2.id, comp.id, "negative", -0.6, now)
    db.commit()

    response = client.get(f"/companies/{comp.id}/sentiment")
    assert response.status_code == 200
    data = response.json()
    assert data["company_id"] == comp.id
    assert data["total_analyses"] == 3
    assert data["positive_count"] == 1
    assert data["neutral_count"] == 1
    assert data["negative_count"] == 1
    # average signed score
    expected_avg = (0.8 + 0.0 - 0.6) / 3
    assert pytest.approx(data["average_score"], rel=1e-5) == expected_avg

def test_sentiment_aggregation_daily_trend_ordering(client: TestClient, db):
    comp = create_company(db, "BBB", "Beta Co")
    art = create_article(db, comp.id)
    base_date = date(2023, 1, 1)
    # create three days of sentiments
    for i, (lbl, scr) in enumerate([
        ("positive", 0.5),
        ("negative", -0.4),
        ("positive", 0.9),
    ]):
        dt = datetime.combine(base_date + timedelta(days=i), datetime.min.time(), tzinfo=timezone.utc)
        create_sentiment(db, art.id, comp.id, lbl, scr, dt)
    db.commit()

    response = client.get(f"/companies/{comp.id}/sentiment")
    assert response.status_code == 200
    data = response.json()
    trend = data["daily_trend"]
    # Should have three entries, ordered chronologically
    assert len(trend) == 3
    dates = [d["date"] for d in trend]
    assert dates == ["2023-01-01", "2023-01-02", "2023-01-03"]
    # Verify counts and averages per day
    expected = {
        "2023-01-01": (1, 0.5),
        "2023-01-02": (1, -0.4),
        "2023-01-03": (1, 0.9),
    }
    for point in trend:
        exp_count, exp_avg = expected[point["date"]]
        assert point["count"] == exp_count
        assert pytest.approx(point["average_score"], rel=1e-5) == exp_avg

def test_sentiment_aggregation_empty_result(client: TestClient, db):
    comp = create_company(db, "CCC", "Gamma Co")
    db.commit()
    response = client.get(f"/companies/{comp.id}/sentiment")
    assert response.status_code == 200
    data = response.json()
    assert data["total_analyses"] == 0
    assert data["positive_count"] == 0
    assert data["neutral_count"] == 0
    assert data["negative_count"] == 0
    assert data["average_score"] is None
    assert data["daily_trend"] == []

def test_sentiment_aggregation_unknown_company_returns_404(client: TestClient, db):
    response = client.get("/companies/9999/sentiment")
    assert response.status_code == 404
    assert response.json()["detail"] == "Company not found"

def test_sentiment_aggregation_invalid_date_range_returns_422(client: TestClient, db):
    comp = create_company(db, "DDD", "Delta Co")
    db.commit()
    # start > end should trigger ValueError -> 422 response
    response = client.get(
        f"/companies/{comp.id}/sentiment?start_date=2023-01-10&end_date=2023-01-01"
    )
    assert response.status_code == 422

def test_get_company_endpoint_still_works(client: TestClient, db):
    comp = create_company(db, "EEE", "Epsilon Co")
    db.commit()
    resp = client.get(f"/companies/{comp.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ticker"] == "EEE"
    assert data["name"] == "Epsilon Co"
