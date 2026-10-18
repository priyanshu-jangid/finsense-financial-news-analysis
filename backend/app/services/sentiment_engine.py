from backend.app.core.config import settings

# Placeholder for SentimentEngine; will be set on first use or patched in tests.
SentimentEngine = None

# Lazy singleton for SentimentEngine instance
_engine = None

def get_sentiment_engine():
    """Return a cached SentimentEngine instance.

    The engine is instantiated once using the model name from settings.
    If the model cannot be loaded, a RuntimeError is raised.
    """
    global _engine, SentimentEngine
    if _engine is None:
        if SentimentEngine is None:
            from nlp.pipeline.sentiment import SentimentEngine as RealEngine
            SentimentEngine = RealEngine
        try:
            _engine = SentimentEngine(model_name=settings.FINBERT_MODEL_NAME)
        except Exception as exc:
            raise RuntimeError("Sentiment engine unavailable") from exc
    return _engine

def reset_sentiment_engine():
    """Clear the cached SentimentEngine.

    Useful for tests to ensure a fresh engine per test.
    """
    global _engine, SentimentEngine
    _engine = None
    SentimentEngine = None
