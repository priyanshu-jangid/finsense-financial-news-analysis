"""Tests for the personalized news feed endpoint (Stage 4a).

All tests run against an in-memory SQLite database via the shared conftest.py
fixtures (``client``, ``db``).  PostgreSQL-specific features are not assumed.

Coverage
--------
- Empty watchlist → empty feed
- Single watchlisted company → correct articles returned
- Company not in watchlist → 400
- company_id filter (valid + belonging to watchlist)
- company_id filter for company NOT on watchlist → 400
- sentiment filter
- start_date / end_date filters
- invalid date range (start > end) → 422
- invalid sentiment value → 422
- pagination (page, page_size, total_pages)
- no duplicate articles when article matches multiple watchlisted companies
- matched_companies populated correctly with latest sentiment
- deterministic sentiment selection (highest id wins)
- authentication required (401)
- ownership enforced (403)
- article order (published_at DESC NULLS LAST, then fetched_at DESC, then id DESC)
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.core.security import create_access_token
from shared.models import (
    Article,
    ArticleEntity,
    Company,
    SentimentAnalysis,
    Source,
    User,
    Watchlist,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def auth_header(user_id: int) -> dict:
    token = create_access_token(str(user_id))
    return {"Authorization": f"Bearer {token}"}


def make_user(db: Session, email: str = "feed@example.com") -> User:
    user = User(email=email, password_hash="hash")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def make_source(db: Session) -> Source:
    src = Source(name="Test Source", domain="testnews.com", credibility_tier=1)
    db.add(src)
    db.commit()
    db.refresh(src)
    return src


def make_company(db: Session, ticker: str, name: str = "Company") -> Company:
    company = Company(ticker=ticker, name=name, sector="Technology")
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def make_article(
    db: Session,
    source: Source,
    title: str = "Article",
    published_at: datetime | None = None,
    fetched_at: datetime | None = None,
) -> Article:
    article = Article(
        title=title,
        url=f"https://example.com/{title.replace(' ', '-').lower()}",
        source_id=source.id,
        published_at=published_at,
        fetched_at=fetched_at or datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    return article


def link_entity(db: Session, article: Article, company: Company, relevance: float = 0.9) -> ArticleEntity:
    entity = ArticleEntity(
        article_id=article.id, company_id=company.id, relevance_score=relevance
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity


def add_to_watchlist(db: Session, user: User, company: Company) -> Watchlist:
    entry = Watchlist(user_id=user.id, company_id=company.id)
    db.add(entry)
    db.commit()
    return entry


def add_sentiment(
    db: Session,
    article: Article,
    company: Company,
    label: str = "positive",
    score: float = 0.8,
    confidence: float = 0.9,
    model_used: str = "test-model",
) -> SentimentAnalysis:
    sa = SentimentAnalysis(
        article_id=article.id,
        company_id=company.id,
        label=label,
        score=score,
        confidence=confidence,
        model_used=model_used,
    )
    db.add(sa)
    db.commit()
    db.refresh(sa)
    return sa


# ---------------------------------------------------------------------------
# Tests — empty / baseline
# ---------------------------------------------------------------------------

def test_empty_watchlist_returns_empty_feed(client: TestClient, db: Session):
    user = make_user(db)
    resp = client.get(f"/users/{user.id}/feed", headers=auth_header(user.id))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_feed_returns_articles_for_watchlisted_company(client: TestClient, db: Session):
    user = make_user(db)
    src = make_source(db)
    company = make_company(db, "AAPL")
    add_to_watchlist(db, user, company)

    article = make_article(db, src, "Apple Earnings")
    link_entity(db, article, company)

    resp = client.get(f"/users/{user.id}/feed", headers=auth_header(user.id))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == article.id
    assert data["items"][0]["title"] == "Apple Earnings"


def test_feed_excludes_articles_not_linked_to_watchlisted_company(client: TestClient, db: Session):
    user = make_user(db)
    src = make_source(db)
    watched = make_company(db, "AAPL")
    other = make_company(db, "GOOG")
    add_to_watchlist(db, user, watched)

    watched_article = make_article(db, src, "Apple News")
    link_entity(db, watched_article, watched)

    other_article = make_article(db, src, "Google News")
    link_entity(db, other_article, other)

    resp = client.get(f"/users/{user.id}/feed", headers=auth_header(user.id))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == watched_article.id


# ---------------------------------------------------------------------------
# Tests — company_id filter
# ---------------------------------------------------------------------------

def test_company_id_filter_restricts_feed(client: TestClient, db: Session):
    user = make_user(db)
    src = make_source(db)
    c1 = make_company(db, "AAPL")
    c2 = make_company(db, "MSFT")
    add_to_watchlist(db, user, c1)
    add_to_watchlist(db, user, c2)

    a1 = make_article(db, src, "Apple article")
    link_entity(db, a1, c1)
    a2 = make_article(db, src, "Microsoft article")
    link_entity(db, a2, c2)

    resp = client.get(
        f"/users/{user.id}/feed",
        params={"company_id": c1.id},
        headers=auth_header(user.id),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == a1.id


def test_company_id_not_on_watchlist_returns_400(client: TestClient, db: Session):
    user = make_user(db)
    src = make_source(db)
    watched = make_company(db, "AAPL")
    unwatched = make_company(db, "GOOG")
    add_to_watchlist(db, user, watched)

    resp = client.get(
        f"/users/{user.id}/feed",
        params={"company_id": unwatched.id},
        headers=auth_header(user.id),
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Tests — sentiment filter
# ---------------------------------------------------------------------------

def test_sentiment_filter_positive(client: TestClient, db: Session):
    user = make_user(db)
    src = make_source(db)
    company = make_company(db, "AAPL")
    add_to_watchlist(db, user, company)

    pos_article = make_article(db, src, "Good news")
    link_entity(db, pos_article, company)
    add_sentiment(db, pos_article, company, label="positive")

    neg_article = make_article(db, src, "Bad news")
    link_entity(db, neg_article, company)
    add_sentiment(db, neg_article, company, label="negative")

    resp = client.get(
        f"/users/{user.id}/feed",
        params={"sentiment": "positive"},
        headers=auth_header(user.id),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == pos_article.id


def test_invalid_sentiment_value_returns_422(client: TestClient, db: Session):
    user = make_user(db)
    resp = client.get(
        f"/users/{user.id}/feed",
        params={"sentiment": "bullish"},
        headers=auth_header(user.id),
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Tests — date filters
# ---------------------------------------------------------------------------

def test_start_date_filter(client: TestClient, db: Session):
    user = make_user(db)
    src = make_source(db)
    company = make_company(db, "AAPL")
    add_to_watchlist(db, user, company)

    old = make_article(db, src, "Old article", published_at=datetime(2024, 1, 1, tzinfo=timezone.utc))
    link_entity(db, old, company)
    new = make_article(db, src, "New article", published_at=datetime(2024, 6, 1, tzinfo=timezone.utc))
    link_entity(db, new, company)

    resp = client.get(
        f"/users/{user.id}/feed",
        params={"start_date": "2024-03-01T00:00:00"},
        headers=auth_header(user.id),
    )
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()["items"]]
    assert new.id in ids
    assert old.id not in ids


def test_end_date_filter(client: TestClient, db: Session):
    user = make_user(db)
    src = make_source(db)
    company = make_company(db, "AAPL")
    add_to_watchlist(db, user, company)

    old = make_article(db, src, "Old article", published_at=datetime(2024, 1, 1, tzinfo=timezone.utc))
    link_entity(db, old, company)
    new = make_article(db, src, "New article", published_at=datetime(2024, 6, 1, tzinfo=timezone.utc))
    link_entity(db, new, company)

    resp = client.get(
        f"/users/{user.id}/feed",
        params={"end_date": "2024-03-01T00:00:00"},
        headers=auth_header(user.id),
    )
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()["items"]]
    assert old.id in ids
    assert new.id not in ids


def test_invalid_date_range_returns_422(client: TestClient, db: Session):
    user = make_user(db)
    resp = client.get(
        f"/users/{user.id}/feed",
        params={
            "start_date": "2024-06-01T00:00:00",
            "end_date": "2024-01-01T00:00:00",
        },
        headers=auth_header(user.id),
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Tests — pagination
# ---------------------------------------------------------------------------

def test_pagination_page_size(client: TestClient, db: Session):
    user = make_user(db)
    src = make_source(db)
    company = make_company(db, "AAPL")
    add_to_watchlist(db, user, company)

    for i in range(5):
        art = make_article(db, src, f"Article {i}", published_at=datetime(2024, 1, i + 1, tzinfo=timezone.utc))
        link_entity(db, art, company)

    resp = client.get(
        f"/users/{user.id}/feed",
        params={"page_size": 3, "page": 1},
        headers=auth_header(user.id),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert data["total_pages"] == 2
    assert len(data["items"]) == 3


def test_pagination_second_page(client: TestClient, db: Session):
    user = make_user(db)
    src = make_source(db)
    company = make_company(db, "AAPL")
    add_to_watchlist(db, user, company)

    for i in range(5):
        art = make_article(db, src, f"Article {i}", published_at=datetime(2024, 1, i + 1, tzinfo=timezone.utc))
        link_entity(db, art, company)

    resp = client.get(
        f"/users/{user.id}/feed",
        params={"page_size": 3, "page": 2},
        headers=auth_header(user.id),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2


# ---------------------------------------------------------------------------
# Tests — no duplicates when article matches multiple watchlisted companies
# ---------------------------------------------------------------------------

def test_no_duplicate_articles_multi_company(client: TestClient, db: Session):
    user = make_user(db)
    src = make_source(db)
    c1 = make_company(db, "AAPL")
    c2 = make_company(db, "MSFT")
    add_to_watchlist(db, user, c1)
    add_to_watchlist(db, user, c2)

    article = make_article(db, src, "Tech round-up")
    link_entity(db, article, c1)
    link_entity(db, article, c2)

    resp = client.get(f"/users/{user.id}/feed", headers=auth_header(user.id))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1


# ---------------------------------------------------------------------------
# Tests — matched_companies and deterministic sentiment
# ---------------------------------------------------------------------------

def test_matched_companies_populated(client: TestClient, db: Session):
    user = make_user(db)
    src = make_source(db)
    company = make_company(db, "AAPL", "Apple Inc.")
    add_to_watchlist(db, user, company)

    article = make_article(db, src, "Apple News")
    link_entity(db, article, company)
    add_sentiment(db, article, company, label="positive", score=0.75)

    resp = client.get(f"/users/{user.id}/feed", headers=auth_header(user.id))
    assert resp.status_code == 200
    item = resp.json()["items"][0]
    assert len(item["matched_companies"]) == 1
    mc = item["matched_companies"][0]
    assert mc["company_id"] == company.id
    assert mc["company_ticker"] == "AAPL"
    assert mc["label"] == "positive"
    assert mc["score"] == pytest.approx(0.75)


def test_deterministic_sentiment_latest_id_wins(client: TestClient, db: Session):
    """When multiple sentiment records exist for the same (article, company),
    the one with the highest id is returned."""
    user = make_user(db)
    src = make_source(db)
    company = make_company(db, "AAPL")
    add_to_watchlist(db, user, company)

    article = make_article(db, src, "Apple News")
    link_entity(db, article, company)

    # Insert two sentiment records — second (higher id) should win.
    add_sentiment(db, article, company, label="neutral", score=0.5, model_used="model-a")
    add_sentiment(db, article, company, label="positive", score=0.9, model_used="model-b")

    resp = client.get(f"/users/{user.id}/feed", headers=auth_header(user.id))
    assert resp.status_code == 200
    item = resp.json()["items"][0]
    assert len(item["matched_companies"]) == 1
    mc = item["matched_companies"][0]
    assert mc["label"] == "positive"
    assert mc["model_used"] == "model-b"


def test_article_without_sentiment_still_appears(client: TestClient, db: Session):
    user = make_user(db)
    src = make_source(db)
    company = make_company(db, "AAPL")
    add_to_watchlist(db, user, company)

    article = make_article(db, src, "Apple News (no sentiment)")
    link_entity(db, article, company)

    resp = client.get(f"/users/{user.id}/feed", headers=auth_header(user.id))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["matched_companies"] == []


# ---------------------------------------------------------------------------
# Tests — ordering
# ---------------------------------------------------------------------------

def test_feed_ordering_by_published_at_desc(client: TestClient, db: Session):
    user = make_user(db)
    src = make_source(db)
    company = make_company(db, "AAPL")
    add_to_watchlist(db, user, company)

    a1 = make_article(db, src, "Older", published_at=datetime(2024, 1, 1, tzinfo=timezone.utc))
    link_entity(db, a1, company)
    a2 = make_article(db, src, "Newer", published_at=datetime(2024, 6, 1, tzinfo=timezone.utc))
    link_entity(db, a2, company)

    resp = client.get(f"/users/{user.id}/feed", headers=auth_header(user.id))
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()["items"]]
    assert ids.index(a2.id) < ids.index(a1.id)


def test_feed_ordering_nulls_last(client: TestClient, db: Session):
    """Articles with null published_at appear after dated articles."""
    user = make_user(db)
    src = make_source(db)
    company = make_company(db, "AAPL")
    add_to_watchlist(db, user, company)

    dated = make_article(db, src, "Dated", published_at=datetime(2024, 1, 1, tzinfo=timezone.utc))
    link_entity(db, dated, company)
    undated = make_article(db, src, "Undated", published_at=None)
    link_entity(db, undated, company)

    resp = client.get(f"/users/{user.id}/feed", headers=auth_header(user.id))
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()["items"]]
    assert ids.index(dated.id) < ids.index(undated.id)


# ---------------------------------------------------------------------------
# Tests — authentication and ownership
# ---------------------------------------------------------------------------

def test_feed_requires_authentication(client: TestClient, db: Session):
    user = make_user(db)
    resp = client.get(f"/users/{user.id}/feed")
    assert resp.status_code == 401


def test_feed_ownership_enforced(client: TestClient, db: Session):
    owner = make_user(db, "owner@example.com")
    other = make_user(db, "other@example.com")

    resp = client.get(
        f"/users/{owner.id}/feed",
        headers=auth_header(other.id),
    )
    assert resp.status_code == 403
