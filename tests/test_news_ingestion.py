"""Unit and integration tests for news ingestion, normalization, matching, deduplication, and checkpoints."""

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
import pytest
from sqlalchemy import select

from backend.app.services.company_matcher import match_companies_for_article
from backend.app.services.news_ingestion import (
    NewsIngestionService,
    canonicalize_url,
    get_checkpoint,
    parse_provider_datetime,
)
from backend.app.services.news_provider import (
    MarketauxClient,
    NewsProviderError,
    RateLimitError,
)
from shared.models import Article, ArticleEntity, Company, IngestionCheckpoint, Source


@pytest.fixture
def sample_companies(db):
    apple = Company(ticker="AAPL", name="Apple Inc.", sector="Technology")
    reliance = Company(ticker="RELIANCE", name="Reliance Industries", sector="Energy")
    infosys = Company(ticker="INFY", name="Infosys Limited", sector="Technology")
    canara = Company(ticker="CAN", name="Canara Bank", sector="Financial")
    db.add_all([apple, reliance, infosys, canara])
    db.commit()
    return {"AAPL": apple, "RELIANCE": reliance, "INFY": infosys, "CAN": canara}


def test_url_canonicalization():
    raw_url = "https://WWW.Reuters.COM/business/article-1/?utm_source=twitter&utm_medium=social&ref=123"
    canonical = canonicalize_url(raw_url)
    assert canonical == "https://reuters.com/business/article-1"

    trailing_slash = "https://bloomberg.com/news/story-a/"
    no_slash = "https://bloomberg.com/news/story-a"
    assert canonicalize_url(trailing_slash) == canonicalize_url(no_slash)


def test_parse_provider_datetime():
    dt_str = "2026-10-14T10:30:00.000000Z"
    dt = parse_provider_datetime(dt_str)
    assert dt is not None
    assert dt.year == 2026
    assert dt.month == 10
    assert dt.day == 14
    assert dt.hour == 10
    assert dt.minute == 30

    assert parse_provider_datetime(None) is None
    assert parse_provider_datetime("invalid-date") is None


def test_valid_article_normalized_and_persisted(db, sample_companies):
    service = NewsIngestionService()
    companies = list(sample_companies.values())

    raw_article = {
        "uuid": "art-001",
        "title": "Apple unveils new M4 chip powered hardware",
        "description": "Apple Inc. launched new MacBooks featuring state of the art silicon.",
        "url": "https://www.theverge.com/tech/apple-m4-launch",
        "published_at": "2026-10-14T12:00:00Z",
        "image_url": "https://theverge.com/img.jpg",
        "source": "theverge.com",
        "entities": [
            {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "match_score": 90.0,
            }
        ],
    }

    article, created = service.persist_raw_article(db, raw_article, companies)
    db.commit()

    assert created is True
    assert article is not None
    assert article.id is not None
    assert article.title == "Apple unveils new M4 chip powered hardware"
    assert article.provider_id == "art-001"
    assert article.source.domain == "theverge.com"
    assert len(article.entities) == 1
    assert article.entities[0].company.ticker == "AAPL"
    assert article.entities[0].relevance_score >= 0.8


def test_duplicate_provider_id_deduplication(db, sample_companies):
    service = NewsIngestionService()
    companies = list(sample_companies.values())

    raw_article_1 = {
        "uuid": "unique-uuid-999",
        "title": "Infosys reports quarterly revenue surge",
        "url": "https://economictimes.indiatimes.com/infosys-q2-earnings",
        "source": "economictimes.indiatimes.com",
        "entities": [{"symbol": "INFY", "name": "Infosys Limited"}],
    }

    raw_article_2 = {
        "uuid": "unique-uuid-999",  # Same provider ID
        "title": "Infosys reports quarterly revenue surge (Updated)",
        "url": "https://economictimes.indiatimes.com/infosys-q2-earnings-updated",
        "source": "economictimes.indiatimes.com",
        "entities": [{"symbol": "INFY", "name": "Infosys Limited"}],
    }

    art1, created1 = service.persist_raw_article(db, raw_article_1, companies)
    db.commit()
    assert created1 is True

    art2, created2 = service.persist_raw_article(db, raw_article_2, companies)
    db.commit()
    assert created2 is False
    assert art1.id == art2.id

    count = db.execute(select(Article).where(Article.provider_id == "unique-uuid-999")).scalars().all()
    assert len(count) == 1


def test_duplicate_canonical_url_deduplication(db, sample_companies):
    service = NewsIngestionService()
    companies = list(sample_companies.values())

    raw_article_1 = {
        "uuid": "uuid-a",
        "title": "Reliance expanding oil refining capacity",
        "url": "https://reuters.com/business/energy/reliance-oil/?utm_source=rss",
        "source": "reuters.com",
    }

    raw_article_2 = {
        "uuid": "uuid-b",  # Different UUID but same canonical URL
        "title": "Reliance expanding oil refining capacity",
        "url": "https://reuters.com/business/energy/reliance-oil/?utm_medium=email",
        "source": "reuters.com",
    }

    art1, created1 = service.persist_raw_article(db, raw_article_1, companies)
    db.commit()
    assert created1 is True

    art2, created2 = service.persist_raw_article(db, raw_article_2, companies)
    db.commit()
    assert created2 is False
    assert art1.id == art2.id


def test_one_article_linked_to_multiple_companies(db, sample_companies):
    service = NewsIngestionService()
    companies = list(sample_companies.values())

    raw_article = {
        "uuid": "joint-tech-1",
        "title": "Apple partners with Infosys on AI enterprise solutions",
        "description": "Tech giant Apple Inc. and Indian IT firm Infosys announce cloud partnership.",
        "url": "https://bloomberg.com/news/apple-infosys-partnership",
        "source": "bloomberg.com",
        "entities": [
            {"symbol": "AAPL", "name": "Apple Inc."},
            {"symbol": "INFY", "name": "Infosys Limited"},
        ],
    }

    article, created = service.persist_raw_article(db, raw_article, companies)
    db.commit()

    assert created is True
    matched_tickers = {e.company.ticker for e in article.entities}
    assert "AAPL" in matched_tickers
    assert "INFY" in matched_tickers
    assert len(article.entities) == 2


def test_unrelated_article_not_linked(db, sample_companies):
    service = NewsIngestionService()
    companies = list(sample_companies.values())

    raw_article = {
        "uuid": "general-sports-news",
        "title": "India wins cricket championship in dramatic final",
        "description": "A thrilling sports victory celebrates team spirit and international competition.",
        "url": "https://espn.com/cricket/india-win",
        "source": "espn.com",
    }

    article, created = service.persist_raw_article(db, raw_article, companies)
    db.commit()

    assert created is True
    assert len(article.entities) == 0


def test_short_ticker_ambiguity_guard(db, sample_companies):
    # CAN is a short ticker and a common English word ("can").
    # An article with "You can invest now" should NOT match Canara Bank (CAN).
    companies = list(sample_companies.values())

    raw_article = {
        "title": "Why anyone can invest in index funds today",
        "description": "A guide on how beginner investors can build long-term wealth safely.",
        "url": "https://example.com/can-invest",
    }

    matches = match_companies_for_article(raw_article, companies)
    matched_tickers = [m.company.ticker for m in matches]
    assert "CAN" not in matched_tickers

    # However, if title has cashtag $CAN or exchange prefix "NSE: CAN", it SHOULD match
    raw_article_with_cashtag = {
        "title": "Bullish outlook for $CAN banking earnings",
        "url": "https://example.com/can-earnings",
    }
    matches2 = match_companies_for_article(raw_article_with_cashtag, companies)
    matched_tickers2 = [m.company.ticker for m in matches2]
    assert "CAN" in matched_tickers2


def test_failed_provider_does_not_advance_checkpoint(db, sample_companies):
    mock_provider = MagicMock(spec=MarketauxClient)
    mock_provider.get_company_news.side_effect = NewsProviderError("Marketaux connection failed")

    service = NewsIngestionService(provider_client=mock_provider)
    result = service.ingest_company_news(db)

    checkpoint = get_checkpoint(db, "company")
    assert result.status == "failure"
    assert checkpoint.status == "failure"
    assert checkpoint.last_successful_published_at is None
    assert checkpoint.error_message is not None
    assert "Marketaux connection failed" in checkpoint.error_message


def test_partial_failure_reporting_and_checkpoint_advancement(db, sample_companies):
    mock_provider = MagicMock(spec=MarketauxClient)

    # First batch succeeds, second batch fails
    success_batch = {
        "data": [
            {
                "uuid": "success-uuid-1",
                "title": "Apple reports strong iPhone sales",
                "url": "https://example.com/apple-success",
                "published_at": "2026-10-14T08:00:00Z",
                "entities": [{"symbol": "AAPL", "name": "Apple Inc."}],
            }
        ]
    }
    mock_provider.get_company_news.side_effect = [
        success_batch,
        RateLimitError("Quota exceeded on second batch"),
    ]

    service = NewsIngestionService(provider_client=mock_provider)
    # Using max_symbols_per_batch=2 splits 4 companies into 2 batches
    result = service.ingest_company_news(db, max_symbols_per_batch=2)

    assert result.status == "partial_failure"
    assert result.articles_persisted == 1

    checkpoint = get_checkpoint(db, "company")
    assert checkpoint.status == "partial_failure"
    assert checkpoint.articles_persisted == 1
    # Checkpoint advances to the successfully persisted article's timestamp
    assert checkpoint.last_successful_published_at == datetime(2026, 10, 14, 8, 0, 0)
    assert "Quota exceeded" in checkpoint.error_message


def test_repeated_runs_are_idempotent(db, sample_companies):
    mock_provider = MagicMock(spec=MarketauxClient)
    mock_data = {
        "data": [
            {
                "uuid": "idempotent-art-1",
                "title": "Reliance Q2 Results Exceed Estimates",
                "url": "https://reuters.com/reliance-q2-estimates",
                "published_at": "2026-10-14T09:00:00Z",
                "entities": [{"symbol": "RELIANCE", "name": "Reliance Industries"}],
            }
        ]
    }
    mock_provider.get_company_news.return_value = mock_data

    service = NewsIngestionService(provider_client=mock_provider)

    # Run 1
    res1 = service.ingest_company_news(db)
    assert res1.articles_persisted == 1
    assert res1.articles_deduplicated == 0

    # Run 2 with same response
    res2 = service.ingest_company_news(db)
    assert res2.articles_persisted == 0
    assert res2.articles_deduplicated == 1

    articles = db.execute(select(Article)).scalars().all()
    assert len(articles) == 1
