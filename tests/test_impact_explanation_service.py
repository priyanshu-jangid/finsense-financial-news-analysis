import json
import pytest
import importlib
from unittest.mock import MagicMock

from backend.app.services.impact_explanation_service import (
    explain_impact,
    ImpactEvidencePayload,
    ArticleEvidence,
    ImpactExplanationResponse,
)
from backend.app.core.config import settings

# Helper to build a minimal valid evidence payload
def build_evidence(override_articles=None):
    article = ArticleEvidence(
        id=1,
        title="Test Article",
        summary="Summary",
        published_at=None,
        sentiment_label="positive",
        sentiment_score=0.8,
    )
    articles = [article] if override_articles is None else override_articles
    payload = ImpactEvidencePayload(
        company_id=123,
        company_name="TestCo",
        period_start=None,
        period_end=None,
        articles=articles,
    )
    return payload.model_dump()

# ---------------------------------------------------------------------------
# Mock client helpers
# ---------------------------------------------------------------------------
class MockResponse:
    def __init__(self, text: str):
        self.text = text

class MockClient:
    def __init__(self, response_text: str | None = None, raise_exc: Exception | None = None):
        self.models = MagicMock()
        if raise_exc is not None:
            self.models.generate_content.side_effect = raise_exc
        else:
            self.models.generate_content.return_value = MockResponse(response_text)

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_successful_explanation(monkeypatch):
    response = {
        "headline": "Sentiment shift detected",
        "observed_facts": "Positive sentiment increased",
        "plausible_explanations": ["New product launch"],
        "supporting_article_ids": [1, 2],
        "contradictory_evidence": [],
        "uncertainty": "Limited data",
    }
    mock_client = MockClient(response_text=json.dumps(response))
    mod = importlib.import_module("backend.app.services.impact_explanation_service")
    monkeypatch.setattr(mod, "_init_gemini_client", lambda: mock_client)
    evidence = build_evidence()
    explanation = explain_impact(evidence)
    assert isinstance(explanation, ImpactExplanationResponse)
    assert explanation.headline == response["headline"]
    # Only article ID 1 exists in evidence; ID 2 should be filtered out
    assert explanation.supporting_article_ids == [1]

def test_missing_api_key(monkeypatch):
    original_key = settings.GEMINI_API_KEY
    settings.GEMINI_API_KEY = ""
    evidence = build_evidence()
    with pytest.raises(RuntimeError, match="Gemini API key is missing"):
        explain_impact(evidence)
    settings.GEMINI_API_KEY = original_key

def test_malformed_json(monkeypatch):
    mock_client = MockClient(response_text="not a json")
    mod = importlib.import_module("backend.app.services.impact_explanation_service")
    monkeypatch.setattr(mod, "_init_gemini_client", lambda: mock_client)
    evidence = build_evidence()
    with pytest.raises(RuntimeError, match="malformed JSON"):
        explain_impact(evidence)

def test_invalid_schema(monkeypatch):
    bad_response = {
        "observed_facts": "...",
        "plausible_explanations": [],
        "supporting_article_ids": [],
        "contradictory_evidence": [],
        "uncertainty": "...",
    }
    mock_client = MockClient(response_text=json.dumps(bad_response))
    mod = importlib.import_module("backend.app.services.impact_explanation_service")
    monkeypatch.setattr(mod, "_init_gemini_client", lambda: mock_client)
    evidence = build_evidence()
    with pytest.raises(RuntimeError, match="response validation failed"):
        explain_impact(evidence)

def test_provider_failure(monkeypatch):
    mock_client = MockClient(raise_exc=Exception("provider error"))
    mod = importlib.import_module("backend.app.services.impact_explanation_service")
    monkeypatch.setattr(mod, "_init_gemini_client", lambda: mock_client)
    evidence = build_evidence()
    with pytest.raises(RuntimeError, match="Gemini request failed"):
        explain_impact(evidence)

def test_empty_articles_validation(monkeypatch):
    # Empty articles list should cause payload validation error before any API call
    evidence = ImpactEvidencePayload(
        company_id=1,
        company_name="Co",
        period_start=None,
        period_end=None,
        articles=[],
    ).model_dump()
    with pytest.raises(ValueError, match="Invalid impact evidence payload"):
        explain_impact(evidence)
