import pytest
from backend.app.services.sentiment_engine import get_sentiment_engine, reset_sentiment_engine

def test_get_sentiment_engine_success(monkeypatch):
    """Engine should be instantiated when model is available."""
    class DummyEngine:
        def __init__(self, model_name=None):
            self.model_name = model_name
    monkeypatch.setattr('backend.app.services.sentiment_engine.SentimentEngine', DummyEngine)
    reset_sentiment_engine()
    engine = get_sentiment_engine()
    assert isinstance(engine, DummyEngine)
    # model_name may be None or the dummy value; ensure attribute exists
    assert hasattr(engine, 'model_name')

def test_get_sentiment_engine_failure(monkeypatch):
    """Engine creation should raise RuntimeError when underlying import fails."""
    def raise_err(*args, **kwargs):
        raise ImportError('Engine not available')
    monkeypatch.setattr('backend.app.services.sentiment_engine.SentimentEngine', raise_err)
    reset_sentiment_engine()
    with pytest.raises(RuntimeError):
        get_sentiment_engine()
