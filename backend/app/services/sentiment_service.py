"""Sentiment analysis service layer.

Provides a function to analyse an article for a specific company using the existing
:class:`nlp.pipeline.sentiment.SentimentEngine`. The result is stored in the
``SentimentAnalysis`` table and returned to callers.
"""

from __future__ import annotations

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

# Import SentimentEngine lazily inside function to respect monkeypatches
from shared.models import Article, Company, SentimentAnalysis, ArticleEntity

_ALLOWED_LABELS = {"positive", "neutral", "negative"}

def _validate_engine_output(result: dict) -> None:
    """Validate keys and value ranges from ``SentimentEngine.analyze``.

    Raises ``ValueError`` if any data is outside expected domains.
    """
    label = result.get("label")
    score = result.get("score")
    confidence = result.get("confidence")
    model_used = result.get("model_used")

    if label not in _ALLOWED_LABELS:
        raise ValueError(f"Unexpected sentiment label: {label}")
    if not isinstance(score, (int, float)) or not -1.0 <= score <= 1.0:
        raise ValueError(f"Score out of bounds: {score}")
    if not isinstance(confidence, (int, float)) or not 0.0 <= confidence <= 1.0:
        raise ValueError(f"Confidence out of bounds: {confidence}")
    if not isinstance(model_used, str) or not model_used:
        raise ValueError("model_used must be a non-empty string")

def _article_company_association_exists(db: Session, article_id: int, company_id: int) -> bool:
    """Return True if the article is linked to the company via an ``ArticleEntity`` row."""
    stmt = (
        db.query(ArticleEntity)
        .filter(ArticleEntity.article_id == article_id, ArticleEntity.company_id == company_id)
        .exists()
    )
    return db.query(stmt).scalar()

def analyse_and_persist_sentiment(
    db: Session, article_id: int, company_id: int, *, engine: SentimentEngine | None = None
) -> SentimentAnalysis:
    """Analyse an article for a company and persist the result.

    Idempotent: returns existing ``SentimentAnalysis`` if one with the same article,
    company and model_used already exists.
    """
    article = db.get(Article, article_id)
    if article is None:
        raise ValueError(f"Article {article_id} not found")
    company = db.get(Company, company_id)
    if company is None:
        raise ValueError(f"Company {company_id} not found")
    if not _article_company_association_exists(db, article_id, company_id):
        raise ValueError(f"Company {company_id} is not associated with Article {article_id}")

    text_parts = [article.title]
    if article.content:
        text_parts.append(article.content)
    text = "\n\n".join(text_parts).strip()

    if engine is None:
        # Dynamically import SentimentEngine each call to honour monkeypatches
        try:
            import importlib
            sentiment_mod = importlib.import_module("nlp.pipeline.sentiment")
            EngineClass = getattr(sentiment_mod, "SentimentEngine")
            engine = EngineClass()
        except Exception as exc:
            # In production, fail fast if the engine cannot be loaded
            raise RuntimeError("Failed to load SentimentEngine") from exc

    # Run analysis; let any exception propagate to be handled by caller
    result = engine.analyze(text)
    _validate_engine_output(result)

    existing = (
        db.query(SentimentAnalysis)
        .filter(
            SentimentAnalysis.article_id == article_id,
            SentimentAnalysis.company_id == company_id,
            SentimentAnalysis.model_used == result["model_used"],
        )
        .first()
    )
    if existing:
        return existing

    sentiment = SentimentAnalysis(
        article_id=article_id,
        company_id=company_id,
        label=result["label"],
        score=result["score"],
        confidence=result["confidence"],
        model_used=result["model_used"],
    )
    try:
        # Use a savepoint to handle possible unique constraint violations
        with db.begin_nested():
            db.add(sentiment)
            db.flush()
            return sentiment
    except IntegrityError:
        # Roll back the savepoint and fetch the existing record
        db.rollback()
        existing = (
            db.query(SentimentAnalysis)
            .filter(
                SentimentAnalysis.article_id == article_id,
                SentimentAnalysis.company_id == company_id,
                SentimentAnalysis.model_used == result["model_used"],
            )
            .first()
        )
        return existing
