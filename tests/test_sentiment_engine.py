import pytest
from nlp.pipeline.sentiment import SentimentEngine

class DummyPipeline:
    def __init__(self, outputs):
        self.outputs = outputs
    def __call__(self, text):
        return self.outputs

def test_positive_score_mapping():
    engine = SentimentEngine()
    engine._set_pipeline(DummyPipeline([{"label": "POSITIVE", "score": 0.7}]))
    result = engine.analyze("some text")
    assert result["label"] == "positive"
    assert result["score"] == pytest.approx(0.7)
    assert result["confidence"] == pytest.approx(0.7)

def test_negative_score_mapping():
    engine = SentimentEngine()
    engine._set_pipeline(DummyPipeline([{"label": "NEGATIVE", "score": 0.8}]))
    result = engine.analyze("some text")
    assert result["label"] == "negative"
    assert result["score"] == pytest.approx(-0.8)
    assert result["confidence"] == pytest.approx(0.8)

def test_neutral_score_mapping():
    engine = SentimentEngine()
    engine._set_pipeline(DummyPipeline([{"label": "NEUTRAL", "score": 0.5}]))
    result = engine.analyze("some text")
    assert result["label"] == "neutral"
    assert result["score"] == 0.0
    assert result["confidence"] == pytest.approx(0.5)

def test_empty_input_neutral():
    engine = SentimentEngine()
    result = engine.analyze("")
    assert result["label"] == "neutral"
    assert result["score"] == 0.0
    assert result["confidence"] == 0.0

def test_whitespace_input_neutral():
    engine = SentimentEngine()
    result = engine.analyze("   \n \t")
    assert result["label"] == "neutral"
    assert result["score"] == 0.0
    assert result["confidence"] == 0.0

def test_malformed_output_unknown_label():
    engine = SentimentEngine()
    engine._set_pipeline(DummyPipeline([{"label": "UNKNOWN", "score": 0.6}]))
    with pytest.raises(ValueError):
        engine.analyze("text")

def test_malformed_output_out_of_range_score():
    engine = SentimentEngine()
    engine._set_pipeline(DummyPipeline([{"label": "POSITIVE", "score": 2.0}]))
    with pytest.raises(ValueError):
        engine.analyze("text")

def test_malformed_output_out_of_range_confidence():
    engine = SentimentEngine()
    engine._set_pipeline(DummyPipeline([{"label": "POSITIVE", "score": 0.5, "confidence": 1.5}]))
    with pytest.raises(ValueError):
        engine.analyze("text")

def test_load_failure_raises_runtime_error(monkeypatch):
    def raise_err(*args, **kwargs):
        raise Exception("load fail")
    monkeypatch.setattr(SentimentEngine, "_load_pipeline", raise_err)
    engine = SentimentEngine()
    with pytest.raises(RuntimeError):
        engine.analyze("text")
