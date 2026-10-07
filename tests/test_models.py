import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from shared.models import (
    Base,
    User,
    Company,
    Watchlist,
    Source,
    Article,
    ArticleEntity,
    SentimentAnalysis,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")

    Base.metadata.create_all(bind=engine)

    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_create_user_and_company(db_session):
    user = User(
        email="test@example.com",
        password_hash="hashed_password",
    )

    company = Company(
        ticker="AAPL",
        name="Apple Inc.",
        sector="Technology",
    )

    db_session.add_all([user, company])
    db_session.commit()

    assert user.id is not None
    assert company.id is not None
    assert company.ticker == "AAPL"


def test_user_can_add_company_to_watchlist(db_session):
    user = User(
        email="test@example.com",
        password_hash="hashed_password",
    )

    company = Company(
        ticker="AAPL",
        name="Apple Inc.",
        sector="Technology",
    )

    db_session.add_all([user, company])
    db_session.commit()

    watchlist = Watchlist(
        user_id=user.id,
        company_id=company.id,
    )

    db_session.add(watchlist)
    db_session.commit()

    assert watchlist.id is not None
    assert watchlist.user_id == user.id
    assert watchlist.company_id == company.id


def test_duplicate_watchlist_entry_is_rejected(db_session):
    user = User(
        email="test@example.com",
        password_hash="hashed_password",
    )

    company = Company(
        ticker="AAPL",
        name="Apple Inc.",
        sector="Technology",
    )

    db_session.add_all([user, company])
    db_session.commit()

    first = Watchlist(
        user_id=user.id,
        company_id=company.id,
    )

    db_session.add(first)
    db_session.commit()

    duplicate = Watchlist(
        user_id=user.id,
        company_id=company.id,
    )

    db_session.add(duplicate)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_article_can_have_multiple_companies_and_sentiments(db_session):
    apple = Company(
        ticker="AAPL",
        name="Apple Inc.",
        sector="Technology",
    )

    samsung = Company(
        ticker="005930.KS",
        name="Samsung Electronics",
        sector="Technology",
    )

    source = Source(
        name="Reuters",
        domain="reuters.com",
        credibility_tier=1,
    )

    db_session.add_all([apple, samsung, source])
    db_session.commit()

    article = Article(
        source_id=source.id,
        title="Apple reports strong revenue while Samsung faces declining sales",
        url="https://example.com/article-1",
        content="Example financial news article.",
        summary="Apple performs strongly while Samsung faces weaker sales.",
    )

    db_session.add(article)
    db_session.commit()

    apple_entity = ArticleEntity(
        article_id=article.id,
        company_id=apple.id,
    )

    samsung_entity = ArticleEntity(
        article_id=article.id,
        company_id=samsung.id,
    )

    apple_sentiment = SentimentAnalysis(
        article_id=article.id,
        company_id=apple.id,
        label="positive",
        score=0.82,
        confidence=0.94,
        model_used="finbert",
    )

    samsung_sentiment = SentimentAnalysis(
        article_id=article.id,
        company_id=samsung.id,
        label="negative",
        score=-0.71,
        confidence=0.91,
        model_used="finbert",
    )

    db_session.add_all(
        [
            apple_entity,
            samsung_entity,
            apple_sentiment,
            samsung_sentiment,
        ]
    )

    db_session.commit()

    assert len(article.entities) == 2
    assert len(article.sentiments) == 2

    assert apple_sentiment.label == "positive"
    assert samsung_sentiment.label == "negative"


def test_article_belongs_to_source(db_session):
    source = Source(
        name="Reuters",
        domain="reuters.com",
        credibility_tier=1,
    )

    db_session.add(source)
    db_session.commit()

    article = Article(
        source_id=source.id,
        title="Test financial article",
        url="https://example.com/article-2",
    )

    db_session.add(article)
    db_session.commit()

    assert article.source.name == "Reuters"
    assert article.source.domain == "reuters.com"
