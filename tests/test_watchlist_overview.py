from datetime import UTC, datetime, timedelta
from itertools import count

import pytest
from sqlalchemy import event

from backend.app.core.security import create_access_token
from backend.app.services.watchlist_overview_service import get_watchlist_overview
from shared.models import (
    Article,
    ArticleEntity,
    Company,
    SentimentAnalysis,
    User,
    Watchlist,
)

AS_OF = datetime(2026, 10, 23, 12, 0, 0)
_url_counter = count(1)


# --------------------------------------------------------------------------
# Helpers (local, following the convention in tests/test_watchlists.py)
# --------------------------------------------------------------------------


def auth_header(user_id: int) -> dict:
    token = create_access_token(str(user_id))
    return {"Authorization": f"Bearer {token}"}


def create_user(db, email="overview@example.com") -> int:
    user = User(email=email, password_hash="test_hash")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user.id


def create_company(db, ticker, name=None, sector="Technology") -> int:
    company = Company(ticker=ticker, name=name or f"{ticker} Corp", sector=sector)
    db.add(company)
    db.commit()
    db.refresh(company)
    return company.id


def watch(db, user_id, *company_ids) -> None:
    for company_id in company_ids:
        db.add(Watchlist(user_id=user_id, company_id=company_id))
    db.commit()


def add_article(db, *, published_at, company_ids=()) -> int:
    article = Article(
        title="Test article",
        url=f"https://example.com/article-{next(_url_counter)}",
        published_at=published_at,
    )
    db.add(article)
    db.flush()
    for company_id in company_ids:
        db.add(ArticleEntity(article_id=article.id, company_id=company_id))
    db.commit()
    return article.id


def _label_for(score: float) -> str:
    if score > 0:
        return "positive"
    if score < 0:
        return "negative"
    return "neutral"


def add_sentiment(
    db, article_id, company_id, score, *, model="finbert-a", created_at=None
) -> int:
    kwargs = {}
    if created_at is not None:
        kwargs["created_at"] = created_at
    record = SentimentAnalysis(
        article_id=article_id,
        company_id=company_id,
        label=_label_for(score),
        score=score,
        confidence=abs(score),
        model_used=model,
        **kwargs,
    )
    db.add(record)
    db.commit()
    return record.id


def seed_scored(db, company_id, *, count_, days_ago, score, as_of=AS_OF):
    ids = []
    for _ in range(count_):
        article_id = add_article(
            db,
            published_at=as_of - timedelta(days=days_ago),
            company_ids=[company_id],
        )
        add_sentiment(db, article_id, company_id, score)
        ids.append(article_id)
    return ids


def overview_for(db, user_id, company_id):
    result = get_watchlist_overview(db, user_id, as_of=AS_OF)
    return next(c for c in result.companies if c.company_id == company_id)


# --------------------------------------------------------------------------
# Authentication and ownership (HTTP)
# --------------------------------------------------------------------------


def test_overview_requires_authentication(client, db):
    user_id = create_user(db)
    response = client.get(f"/users/{user_id}/watchlist/overview")
    assert response.status_code == 401


def test_overview_rejects_invalid_token(client, db):
    user_id = create_user(db)
    response = client.get(
        f"/users/{user_id}/watchlist/overview",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert response.status_code == 401


def test_overview_denies_access_to_another_users_overview(client, db):
    owner_id = create_user(db, "owner@example.com")
    other_id = create_user(db, "other@example.com")
    company_id = create_company(db, "AAPL")
    watch(db, owner_id, company_id)

    response = client.get(
        f"/users/{owner_id}/watchlist/overview", headers=auth_header(other_id)
    )
    assert response.status_code == 403


def test_overview_endpoint_empty_watchlist(client, db):
    user_id = create_user(db)
    response = client.get(
        f"/users/{user_id}/watchlist/overview", headers=auth_header(user_id)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == user_id
    assert body["companies"] == []
    assert body["totals"] == {
        "companies_tracked": 0,
        "companies_with_sentiment_shift": 0,
        "negative_article_count": 0,
    }
    assert body["window_days"] == 7
    assert body["min_articles_per_window"] == 5
    assert body["shift_threshold"] == 0.25


def test_overview_endpoint_returns_measured_values(client, db):
    user_id = create_user(db)
    company_id = create_company(db, "AAPL", "Apple Inc.")
    watch(db, user_id, company_id)
    now = datetime.now(UTC).replace(tzinfo=None)
    seed_scored(db, company_id, count_=5, days_ago=3, score=0.6, as_of=now)
    seed_scored(db, company_id, count_=5, days_ago=10, score=0.0, as_of=now)

    response = client.get(
        f"/users/{user_id}/watchlist/overview", headers=auth_header(user_id)
    )
    assert response.status_code == 200
    body = response.json()
    company = body["companies"][0]
    assert company["ticker"] == "AAPL"
    assert company["shift_status"] == "improving"
    assert company["score_delta"] == pytest.approx(0.6)
    assert company["current_window"]["article_count"] == 5
    assert company["previous_window"]["article_count"] == 5
    assert body["totals"]["companies_with_sentiment_shift"] == 1
    assert "alert" not in response.text.lower()


def test_overview_is_scoped_to_the_requesting_users_watchlist(db):
    user_id = create_user(db, "a@example.com")
    other_id = create_user(db, "b@example.com")
    mine = create_company(db, "AAPL")
    theirs = create_company(db, "MSFT")
    watch(db, user_id, mine)
    watch(db, other_id, theirs)
    seed_scored(db, theirs, count_=5, days_ago=3, score=0.9)

    result = get_watchlist_overview(db, user_id, as_of=AS_OF)
    assert [c.company_id for c in result.companies] == [mine]


# --------------------------------------------------------------------------
# Service behaviour
# --------------------------------------------------------------------------


def test_service_empty_watchlist(db):
    user_id = create_user(db)
    result = get_watchlist_overview(db, user_id, as_of=AS_OF)
    assert result.companies == []
    assert result.totals.companies_tracked == 0
    assert result.as_of == AS_OF


def test_single_company_window_counts_averages_and_labels(db):
    user_id = create_user(db)
    company_id = create_company(db, "AAPL", "Apple Inc.", sector="Technology")
    watch(db, user_id, company_id)
    seed_scored(db, company_id, count_=5, days_ago=10, score=0.0)
    for score in (0.5, 0.3, 0.0, -0.4, -0.4, -0.2):
        article_id = add_article(
            db, published_at=AS_OF - timedelta(days=2), company_ids=[company_id]
        )
        add_sentiment(db, article_id, company_id, score)

    company = overview_for(db, user_id, company_id)
    assert (company.ticker, company.name, company.sector) == (
        "AAPL",
        "Apple Inc.",
        "Technology",
    )
    assert company.current_window.article_count == 6
    assert company.current_window.average_score == pytest.approx(-0.2 / 6)
    assert company.current_window.start == AS_OF - timedelta(days=7)
    assert company.current_window.end == AS_OF
    assert company.previous_window.article_count == 5
    assert company.previous_window.average_score == pytest.approx(0.0)
    assert company.previous_window.start == AS_OF - timedelta(days=14)
    assert company.previous_window.end == AS_OF - timedelta(days=7)
    labels = company.current_label_counts
    assert (labels.positive, labels.neutral, labels.negative) == (2, 1, 3)
    assert company.negative_article_count == 3
    assert company.score_delta == pytest.approx(-0.2 / 6)
    assert company.shift_status == "stable"


def test_multiple_companies_ordering_statuses_and_totals(db):
    user_id = create_user(db)
    msft = create_company(db, "MSFT")
    aapl = create_company(db, "AAPL")
    tsla = create_company(db, "TSLA")
    watch(db, user_id, msft, aapl, tsla)

    seed_scored(db, aapl, count_=5, days_ago=10, score=0.4)
    seed_scored(db, aapl, count_=5, days_ago=3, score=-0.4)  # deteriorating
    seed_scored(db, msft, count_=5, days_ago=10, score=0.1)
    seed_scored(db, msft, count_=5, days_ago=3, score=0.15)  # stable
    seed_scored(db, tsla, count_=2, days_ago=3, score=-0.8)  # insufficient

    result = get_watchlist_overview(db, user_id, as_of=AS_OF)
    assert [c.ticker for c in result.companies] == ["AAPL", "MSFT", "TSLA"]
    by_ticker = {c.ticker: c for c in result.companies}
    assert by_ticker["AAPL"].shift_status == "deteriorating"
    assert by_ticker["AAPL"].score_delta == pytest.approx(-0.8)
    assert by_ticker["MSFT"].shift_status == "stable"
    assert by_ticker["TSLA"].shift_status == "insufficient_data"
    assert by_ticker["TSLA"].score_delta is None
    assert by_ticker["TSLA"].current_window.average_score == pytest.approx(-0.8)

    assert result.totals.companies_tracked == 3
    assert result.totals.companies_with_sentiment_shift == 1
    assert result.totals.negative_article_count == 5 + 0 + 2


def test_company_without_any_articles_is_reported_with_empty_values(db):
    user_id = create_user(db)
    company_id = create_company(db, "AAPL")
    watch(db, user_id, company_id)

    company = overview_for(db, user_id, company_id)
    assert company.shift_status == "insufficient_data"
    assert company.current_window.article_count == 0
    assert company.current_window.average_score is None
    assert company.score_delta is None
    assert company.negative_article_count == 0
    assert company.latest_article_published_at is None


def test_window_boundaries_are_half_open_and_use_published_at(db):
    user_id = create_user(db)
    company_id = create_company(db, "AAPL")
    watch(db, user_id, company_id)

    boundary_times = {
        "current_start": AS_OF - timedelta(days=7),  # current window
        "previous_start": AS_OF - timedelta(days=14),  # previous window
        "just_before_previous": AS_OF - timedelta(days=14, seconds=1),  # neither
        "exactly_as_of": AS_OF,  # eligible, but in neither window
    }
    for published_at in boundary_times.values():
        article_id = add_article(db, published_at=published_at, company_ids=[company_id])
        add_sentiment(db, article_id, company_id, 0.5)

    company = overview_for(db, user_id, company_id)
    assert company.current_window.article_count == 1
    assert company.previous_window.article_count == 1


def test_sentiment_creation_time_does_not_affect_windows(db):
    user_id = create_user(db)
    company_id = create_company(db, "AAPL")
    watch(db, user_id, company_id)
    old_article = add_article(
        db, published_at=AS_OF - timedelta(days=30), company_ids=[company_id]
    )
    add_sentiment(db, old_article, company_id, 0.9, created_at=AS_OF)
    recent_article = add_article(
        db, published_at=AS_OF - timedelta(days=1), company_ids=[company_id]
    )
    add_sentiment(
        db, recent_article, company_id, 0.9, created_at=AS_OF - timedelta(days=30)
    )

    company = overview_for(db, user_id, company_id)
    assert company.current_window.article_count == 1
    assert company.previous_window.article_count == 0


def test_articles_without_sentiment_are_not_counted_but_set_latest_time(db):
    user_id = create_user(db)
    company_id = create_company(db, "AAPL")
    watch(db, user_id, company_id)
    seed_scored(db, company_id, count_=2, days_ago=3, score=0.5)
    unscored_time = AS_OF - timedelta(hours=5)
    add_article(db, published_at=unscored_time, company_ids=[company_id])

    company = overview_for(db, user_id, company_id)
    assert company.current_window.article_count == 2
    assert company.latest_article_published_at == unscored_time


def test_null_and_future_publication_times_are_excluded(db):
    user_id = create_user(db)
    company_id = create_company(db, "AAPL")
    watch(db, user_id, company_id)
    valid_time = AS_OF - timedelta(days=2)
    valid = add_article(db, published_at=valid_time, company_ids=[company_id])
    add_sentiment(db, valid, company_id, 0.5)
    null_time = add_article(db, published_at=None, company_ids=[company_id])
    add_sentiment(db, null_time, company_id, 0.5)
    future = add_article(
        db, published_at=AS_OF + timedelta(days=1), company_ids=[company_id]
    )
    add_sentiment(db, future, company_id, 0.5)

    company = overview_for(db, user_id, company_id)
    assert company.current_window.article_count == 1
    assert company.previous_window.article_count == 0
    assert company.latest_article_published_at == valid_time


def test_articles_older_than_both_windows_are_excluded(db):
    user_id = create_user(db)
    company_id = create_company(db, "AAPL")
    watch(db, user_id, company_id)
    seed_scored(db, company_id, count_=3, days_ago=40, score=0.5)

    company = overview_for(db, user_id, company_id)
    assert company.current_window.article_count == 0
    assert company.previous_window.article_count == 0


def test_latest_sentiment_record_wins_per_article_company_pair(db):
    user_id = create_user(db)
    company_id = create_company(db, "AAPL")
    watch(db, user_id, company_id)
    article_id = add_article(
        db, published_at=AS_OF - timedelta(days=2), company_ids=[company_id]
    )
    add_sentiment(
        db, article_id, company_id, -0.9, model="old-model",
        created_at=AS_OF - timedelta(days=3),
    )
    add_sentiment(
        db, article_id, company_id, 0.8, model="new-model",
        created_at=AS_OF - timedelta(days=1),
    )

    company = overview_for(db, user_id, company_id)
    assert company.current_window.article_count == 1
    assert company.current_window.average_score == pytest.approx(0.8)
    assert company.current_label_counts.positive == 1
    assert company.current_label_counts.negative == 0


def test_equal_creation_times_fall_back_to_highest_record_id(db):
    user_id = create_user(db)
    company_id = create_company(db, "AAPL")
    watch(db, user_id, company_id)
    article_id = add_article(
        db, published_at=AS_OF - timedelta(days=2), company_ids=[company_id]
    )
    created = AS_OF - timedelta(days=1)
    add_sentiment(db, article_id, company_id, 0.1, model="model-a", created_at=created)
    add_sentiment(db, article_id, company_id, -0.7, model="model-b", created_at=created)

    company = overview_for(db, user_id, company_id)
    assert company.current_window.article_count == 1
    assert company.current_window.average_score == pytest.approx(-0.7)


def test_pairs_are_counted_once_even_with_many_records_and_shared_articles(db):
    user_id = create_user(db)
    first = create_company(db, "AAPL")
    second = create_company(db, "MSFT")
    watch(db, user_id, first, second)
    # One article linked to both companies, with three records for AAPL.
    article_id = add_article(
        db, published_at=AS_OF - timedelta(days=2), company_ids=[first, second]
    )
    for index, model in enumerate(("m1", "m2", "m3")):
        add_sentiment(
            db, article_id, first, 0.2 + index * 0.1, model=model,
            created_at=AS_OF - timedelta(days=3 - index),
        )
    add_sentiment(db, article_id, second, -0.5)

    result = get_watchlist_overview(db, user_id, as_of=AS_OF)
    by_ticker = {c.ticker: c for c in result.companies}
    assert by_ticker["AAPL"].current_window.article_count == 1
    assert by_ticker["AAPL"].current_window.average_score == pytest.approx(0.4)
    assert by_ticker["MSFT"].current_window.article_count == 1
    assert result.totals.negative_article_count == 1


def test_sentiment_without_article_entity_link_is_ignored(db):
    user_id = create_user(db)
    company_id = create_company(db, "AAPL")
    watch(db, user_id, company_id)
    # No ArticleEntity row, and the legacy Article.company_id is set. Neither
    # may make the article count for the company.
    article = Article(
        title="Unlinked",
        url="https://example.com/unlinked",
        published_at=AS_OF - timedelta(days=2),
        company_id=company_id,
    )
    db.add(article)
    db.commit()
    add_sentiment(db, article.id, company_id, 0.9)

    company = overview_for(db, user_id, company_id)
    assert company.current_window.article_count == 0
    assert company.latest_article_published_at is None


def test_sentiment_for_non_watchlisted_companies_is_ignored(db):
    user_id = create_user(db)
    watched = create_company(db, "AAPL")
    unwatched = create_company(db, "MSFT")
    watch(db, user_id, watched)
    seed_scored(db, unwatched, count_=5, days_ago=3, score=0.9)

    result = get_watchlist_overview(db, user_id, as_of=AS_OF)
    assert [c.company_id for c in result.companies] == [watched]
    assert result.companies[0].current_window.article_count == 0


# --------------------------------------------------------------------------
# Query count (no N+1)
# --------------------------------------------------------------------------


def _count_selects(db, func):
    statements = []

    def record(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    engine = db.get_bind()
    event.listen(engine, "before_cursor_execute", record)
    try:
        func()
    finally:
        event.remove(engine, "before_cursor_execute", record)
    return len(statements)


def test_query_count_is_constant_regardless_of_watchlist_size(db):
    user_id = create_user(db)
    first = create_company(db, "AAA")
    watch(db, user_id, first)
    seed_scored(db, first, count_=5, days_ago=3, score=0.5)
    seed_scored(db, first, count_=5, days_ago=10, score=0.0)

    one_company = _count_selects(
        db, lambda: get_watchlist_overview(db, user_id, as_of=AS_OF)
    )

    for index in range(7):
        company_id = create_company(db, f"CO{index}")
        watch(db, user_id, company_id)
        seed_scored(db, company_id, count_=5, days_ago=3, score=-0.5)
        seed_scored(db, company_id, count_=5, days_ago=10, score=0.2)

    result_holder = {}
    eight_companies = _count_selects(
        db,
        lambda: result_holder.setdefault(
            "result", get_watchlist_overview(db, user_id, as_of=AS_OF)
        ),
    )

    assert len(result_holder["result"].companies) == 8
    assert one_company == eight_companies
    assert eight_companies <= 3