import pytest
from sqlalchemy.exc import IntegrityError
from backend.app.services.sentiment_service import analyse_and_persist_sentiment
from shared.models import Article, Company, SentimentAnalysis, ArticleEntity

class DummyEngine:
    def __init__(self, label="positive", score=0.8, confidence=0.9, model_used="dummy-model"):
        self.result = {
            "label": label,
            "score": score,
            "confidence": confidence,
            "model_used": model_used,
        }
    def analyze(self, text: str):
        return self.result

@pytest.fixture
def dummy_engine():
    return DummyEngine()

def create_article_and_company(db):
    article = Article(title="Test Article", content="Test content")
    company = Company(ticker="TEST", name="Test Co")
    db.add_all([article, company])
    db.flush()
    assoc = ArticleEntity(article_id=article.id, company_id=company.id)
    db.add(assoc)
    db.flush()
    return article, company

def test_duplicate_triplet_raises_integrity_error(db, dummy_engine):
    article, company = create_article_and_company(db)
    analyse_and_persist_sentiment(db, article.id, company.id, engine=dummy_engine)
    db.commit()
    dup = SentimentAnalysis(
        article_id=article.id,
        company_id=company.id,
        label="positive",
        score=0.5,
        confidence=0.6,
        model_used="dummy-model",
    )
    db.add(dup)
    with pytest.raises(IntegrityError):
        db.flush()

def test_service_is_idempotent(db, dummy_engine):
    article, company = create_article_and_company(db)
    first = analyse_and_persist_sentiment(db, article.id, company.id, engine=dummy_engine)
    db.commit()
    second = analyse_and_persist_sentiment(db, article.id, company.id, engine=dummy_engine)
    db.commit()
    assert first.id == second.id
    count = db.query(SentimentAnalysis).filter(
        SentimentAnalysis.article_id == article.id,
        SentimentAnalysis.company_id == company.id,
        SentimentAnalysis.model_used == "dummy-model",
    ).count()
    assert count == 1

def test_savepoint_race_returns_existing(db, dummy_engine):
    article, company = create_article_and_company(db)
    existing = SentimentAnalysis(
        article_id=article.id,
        company_id=company.id,
        label="positive",
        score=0.7,
        confidence=0.8,
        model_used="dummy-model",
    )
    db.add(existing)
    db.flush()
    db.commit()
    result = analyse_and_persist_sentiment(db, article.id, company.id, engine=dummy_engine)
    db.commit()
    assert result.id == existing.id
