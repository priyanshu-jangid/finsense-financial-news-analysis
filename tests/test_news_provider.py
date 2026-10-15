"""Unit tests for the news provider client (MarketauxClient)."""

from unittest.mock import MagicMock, patch
import pytest

try:
    import httpx2 as httpx
except ImportError:
    import httpx

from backend.app.services.news_provider import (
    AuthenticationError,
    MarketauxClient,
    NewsProviderError,
    ProviderTimeoutError,
    RateLimitError,
)


@pytest.fixture
def sample_marketaux_response():
    return {
        "meta": {"found": 1, "returned": 1, "limit": 3, "page": 1},
        "data": [
            {
                "uuid": "test-uuid-1234",
                "title": "Reliance Industries expands green energy investments",
                "description": "Reliance announces major renewable energy facility in Gujarat.",
                "keywords": "energy, reliance, markets",
                "snippet": "Reliance announces major renewable energy facility...",
                "url": "https://www.reuters.com/business/reliance-green-energy",
                "image_url": "https://images.reuters.com/photo.jpg",
                "language": "en",
                "published_at": "2026-10-14T10:30:00.000000Z",
                "source": "reuters.com",
                "entities": [
                    {
                        "symbol": "RELIANCE.NS",
                        "name": "Reliance Industries Limited",
                        "exchange": "NSE",
                        "country": "in",
                        "type": "equity",
                        "match_score": 85.5,
                    }
                ],
            }
        ],
    }


def test_provider_successful_response(sample_marketaux_response):
    mock_http = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = sample_marketaux_response
    mock_http.get.return_value = mock_resp

    client = MarketauxClient(api_token="valid_token", client=mock_http)
    data = client.get_company_news(symbols=["RELIANCE.NS"])

    assert "data" in data
    assert len(data["data"]) == 1
    assert data["data"][0]["uuid"] == "test-uuid-1234"
    assert data["data"][0]["title"].startswith("Reliance")


def test_provider_empty_result():
    mock_http = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"meta": {"found": 0, "returned": 0, "limit": 3, "page": 1}, "data": []}
    mock_http.get.return_value = mock_resp

    client = MarketauxClient(api_token="valid_token", client=mock_http)
    data = client.get_company_news(symbols=["NONEXISTENT"])

    assert data["data"] == []
    assert data["meta"]["found"] == 0


def test_provider_missing_token_raises_auth_error():
    client = MarketauxClient(api_token="")
    with pytest.raises(AuthenticationError, match="not configured"):
        client.fetch_news({"symbols": "AAPL"})


def test_provider_http_401_authentication_failure():
    mock_http = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_http.get.return_value = mock_resp

    client = MarketauxClient(api_token="invalid_token", client=mock_http)
    with pytest.raises(AuthenticationError, match="status 401"):
        client.fetch_news({"symbols": "AAPL"})


def test_provider_http_429_rate_limiting():
    mock_http = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_http.get.return_value = mock_resp

    client = MarketauxClient(api_token="test_token", client=mock_http)
    with pytest.raises(RateLimitError, match="rate limit"):
        client.fetch_news({"symbols": "AAPL"})


def test_provider_timeout_handling():
    mock_http = MagicMock()
    mock_http.get.side_effect = httpx.ReadTimeout("Connection timed out")

    client = MarketauxClient(api_token="test_token", client=mock_http, timeout=5.0)
    with pytest.raises(ProviderTimeoutError, match="timed out"):
        client.fetch_news({"symbols": "AAPL"})


def test_provider_http_500_failure():
    mock_http = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error"
    mock_http.get.return_value = mock_resp

    client = MarketauxClient(api_token="test_token", client=mock_http)
    with pytest.raises(NewsProviderError, match="HTTP 500"):
        client.fetch_news({"symbols": "AAPL"})


def test_provider_malformed_json_response():
    mock_http = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.side_effect = ValueError("Invalid JSON string")
    mock_http.get.return_value = mock_resp

    client = MarketauxClient(api_token="test_token", client=mock_http)
    with pytest.raises(NewsProviderError, match="Failed to parse"):
        client.fetch_news({"symbols": "AAPL"})


def test_provider_missing_optional_fields():
    minimal_response = {
        "meta": {"found": 1, "returned": 1},
        "data": [
            {
                "title": "Minimal News",
                "url": "https://example.com/minimal",
                # uuid, description, image_url, source, entities are omitted
            }
        ],
    }
    mock_http = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = minimal_response
    mock_http.get.return_value = mock_resp

    client = MarketauxClient(api_token="test_token", client=mock_http)
    res = client.fetch_news({"symbols": "AAPL"})
    assert len(res["data"]) == 1
    assert res["data"][0]["title"] == "Minimal News"


def test_provider_secrets_redacted_in_logging():
    client = MarketauxClient(api_token="super_secret_12345")
    sanitized = client._sanitize_params_for_logging({"api_token": "super_secret_12345", "symbols": "AAPL"})
    assert sanitized["api_token"] == "[REDACTED]"
    assert "super_secret_12345" not in str(sanitized)
