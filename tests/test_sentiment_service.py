import pytest
from sqlalchemy.exc import IntegrityError
from backend.app.services.sentiment_service import analyse_and_persist_sentiment, _validate_engine_output
from shared.models import Article, Company, SentimentAnalysis, ArticleEntity

class DummyEngine:
    def __init__(self, result):
        self.result = result
    def analyze(self, text):
        return self.result

def create_company_article(db, ticker="AAA", name="TestCo", article_title="Test Article", content="Some content"):
    company = Company(ticker=ticker, name=name, sector="Tech")
    article = Article(title=article_title, content=content)
    db.add_all([company, article])
    db.commit()
    db.refresh(company)
    db.refresh(article)
    db.add(ArticleEntity(article_id=article.id, company_id=company.id))
    db.commit()
    return company, article

def test_persist_valid_result(db):
    company, article = create_company_article(db)
    engine = DummyEngine({"label": "positive", "score": 0.8, "confidence": 0.9, "model_used": "mock-model"})
    sentiment = analyse_and_persist_sentiment(db, article.id, company.id, engine=engine)
    assert isinstance(sentiment, SentimentAnalysis)
    assert sentiment.label == "positive"
    assert sentiment.score == 0.8
    assert sentiment.confidence == 0.9
    assert sentiment.model_used == "mock-model"

def test_summary_is_used_when_article_content_is_missing(db):
    company = Company(ticker="SUM", name="Summary Co", sector="Tech")
    article = Article(
        title="Company announces quarterly results",
        content=None,
        summary="Revenue increased while operating costs declined.",
    )
    db.add_all([company, article])
    db.commit()
    db.refresh(company)
    db.refresh(article)
    db.add(ArticleEntity(article_id=article.id, company_id=company.id))
    db.commit()

    class CapturingEngine(DummyEngine):
        def analyze(self, text):
            self.received_text = text
            return self.result

    engine = CapturingEngine({
        "label": "positive",
        "score": 0.8,
        "confidence": 0.9,
        "model_used": "mock-model",
    })

    analyse_and_persist_sentiment(db, article.id, company.id, engine=engine)

    assert engine.received_text == (
        "Company announces quarterly results\n\n"
        "Revenue increased while operating costs declined."
    )


def test_idempotent_persistence(db):
    company, article = create_company_article(db)
    engine = DummyEngine({"label": "positive", "score": 0.8, "confidence": 0.9, "model_used": "mock-model"})
    first = analyse_and_persist_sentiment(db, article.id, company.id, engine=engine)
    second = analyse_and_persist_sentiment(db, article.id, company.id, engine=engine)
    assert first.id == second.id
    # Ensure only one row exists
    count = db.query(SentimentAnalysis).filter(SentimentAnalysis.article_id == article.id, SentimentAnalysis.company_id == company.id).count()
    assert count == 1

def test_missing_article_raises(db):
    company = Company(ticker="BBB", name="CompB", sector="Tech")
    db.add(company)
    db.commit()
    db.refresh(company)
    engine = DummyEngine({"label": "positive", "score": 0.5, "confidence": 0.6, "model_used": "mock"})
    with pytest.raises(ValueError, match="Article"):
        analyse_and_persist_sentiment(db, 9999, company.id, engine=engine)

def test_missing_company_raises(db):
    article = Article(title="Orphan", content="text")
    db.add(article)
    db.commit()
    db.refresh(article)
    engine = DummyEngine({"label": "positive", "score": 0.5, "confidence": 0.6, "model_used": "mock"})
    with pytest.raises(ValueError, match="Company"):
        analyse_and_persist_sentiment(db, article.id, 9999, engine=engine)

def test_article_not_associated_raises(db):
    company = Company(ticker="CCC", name="CompC", sector="Tech")
    article = Article(title="Unlinked", content="text")
    db.add_all([company, article])
    db.commit()
    db.refresh(company)
    db.refresh(article)
    engine = DummyEngine({"label": "positive", "score": 0.5, "confidence": 0.6, "model_used": "mock"})
    with pytest.raises(ValueError, match="associated"):
        analyse_and_persist_sentiment(db, article.id, company.id, engine=engine)

@pytest.mark.parametrize("result", [
    {"label": "unknown", "score": 0.5, "confidence": 0.5, "model_used": "mock"},
    {"label": "positive", "score": 2.0, "confidence": 0.5, "model_used": "mock"},
    {"label": "positive", "score": 0.5, "confidence": 1.5, "model_used": "mock"},
    {"label": "positive", "score": 0.5, "confidence": 0.5, "model_used": ""},
])
def test_invalid_engine_output_raises(db, result):
    company, article = create_company_article(db)
    engine = DummyEngine(result)
    with pytest.raises(ValueError):
        analyse_and_persist_sentiment(db, article.id, company.id, engine=engine)
    # Ensure no row was persisted
    row = db.query(SentimentAnalysis).filter(SentimentAnalysis.article_id == article.id, SentimentAnalysis.company_id == company.id).first()
    assert row is None

def test_engine_load_failure_raises(db, monkeypatch):
    company, article = create_company_article(db)
    def raise_err(*args, **kwargs):
        raise Exception("load fail")
    monkeypatch.setattr("nlp.pipeline.sentiment.SentimentEngine._load_pipeline", raise_err)
    # engine will attempt to load on first analyze call
    engine = DummyEngine({"label": "positive", "score": 0.5, "confidence": 0.5, "model_used": "mock"})
    # Replace engine with real class to trigger load logic
    from nlp.pipeline.sentiment import SentimentEngine
    real_engine = SentimentEngine()
    # monkeypatch its _load_pipeline to raise
    monkeypatch.setattr(real_engine, "_load_pipeline", raise_err)
    with pytest.raises(RuntimeError):
        analyse_and_persist_sentiment(db, article.id, company.id, engine=real_engine)
