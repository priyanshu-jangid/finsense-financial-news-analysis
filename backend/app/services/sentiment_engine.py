from backend.app.core.config import settings

# Guarded import of the real SentimentEngine; fallback to None if import fails.
try:
    from nlp.pipeline.sentiment import SentimentEngine as SentimentEngine
except Exception:  # pragma: no cover
    SentimentEngine = None

# Lazy singleton for SentimentEngine instance
_engine = None

def get_sentiment_engine():
    """Return a cached SentimentEngine instance.

    The engine is instantiated once using the model name from settings.
    If the engine is unavailable, a RuntimeError is raised.
    """
    global _engine, SentimentEngine
    if _engine is None:
        if SentimentEngine is None:
            raise RuntimeError("Sentiment engine unavailable")
        try:
            _engine = SentimentEngine(model_name=settings.FINBERT_MODEL_NAME)
        except Exception as exc:
            raise RuntimeError("Sentiment engine unavailable") from exc
    return _engine

def reset_sentiment_engine():
    """Clear the cached SentimentEngine.

    Useful for tests to ensure a fresh engine per test.
    """
    global _engine
    _engine = None
