"""News provider client for Marketaux API integration."""

from datetime import datetime, timezone
import logging
from typing import Any

try:
    import httpx2 as httpx
except ImportError:
    import httpx  # type: ignore

from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class NewsProviderError(Exception):
    """Base exception for news provider errors."""


class AuthenticationError(NewsProviderError):
    """Raised when provider authentication fails (e.g. invalid or missing API token)."""


class RateLimitError(NewsProviderError):
    """Raised when the provider's rate limit or free-tier quota is reached."""


class ProviderTimeoutError(NewsProviderError):
    """Raised when a request to the provider times out."""


class MarketauxClient:
    """HTTP client for interacting with the Marketaux Financial News API.

    Adheres to free-tier guidelines:
    - Default limit of 3 articles per request
    - Configurable timeouts
    - Secure token handling (tokens are kept in memory and never logged)
    """

    def __init__(
        self,
        api_token: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        client: httpx.Client | None = None,
    ):
        self.api_token = api_token if api_token is not None else settings.MARKETAUX_API_TOKEN
        self.base_url = (base_url or settings.MARKETAUX_BASE_URL).rstrip("/")
        self.timeout = timeout if timeout is not None else settings.NEWS_REQUEST_TIMEOUT_SECONDS
        self._client = client

    def _get_client(self) -> httpx.Client:
        if self._client is not None:
            return self._client
        return httpx.Client(timeout=self.timeout)

    def _sanitize_params_for_logging(self, params: dict[str, Any]) -> dict[str, Any]:
        """Return a copy of request params with secrets redacted for safe logging."""
        sanitized = dict(params)
        if "api_token" in sanitized:
            sanitized["api_token"] = "[REDACTED]"
        return sanitized



# Duplicate stub removed - live news guard now handled in main implementation
    def fetch_news(self, request_params: dict[str, Any]) -> dict[str, Any]:
        """Fetch news from Marketaux API with error handling.

        Parameters
        ----------
        request_params: dict[str, Any]
            Query parameters for the API request.

        Returns
        -------
        dict[str, Any]
            Parsed JSON response.

        Raises
        ------
        AuthenticationError
            If API token is missing.
        NewsProviderError
            If live news is disabled.
        RateLimitError, ProviderTimeoutError, etc.
        """
        # Ensure API token is configured
        if not self.api_token:
            raise AuthenticationError("API token not configured.")
        # Guard against real requests when live news disabled (unless a custom client is injected)
        if not settings.ENABLE_LIVE_NEWS and self._client is None:
            raise NewsProviderError("Live news fetching is disabled by configuration.")

        owns_client = self._client is None
        http_client = self._get_client()
        url = f"{self.base_url}/news"
        sanitized = self._sanitize_params_for_logging(request_params)
        logger.debug("Fetching Marketaux news with params: %s", sanitized)
        try:
            response = http_client.get(url, params=request_params)
        except (httpx.TimeoutException, TimeoutError) as exc:
            logger.warning("Marketaux request timed out after %.1f seconds", self.timeout)
            raise ProviderTimeoutError(
                f"Marketaux request timed out after {self.timeout}s"
            ) from exc
        except (httpx.RequestError, httpx.TransportError) as exc:
            logger.error("Marketaux network/transport error: %s", type(exc).__name__)
            raise NewsProviderError(f"Marketaux transport error: {type(exc).__name__}") from exc
        finally:
            if owns_client:
                http_client.close()
        if response.status_code in (401, 403):
            logger.error("Marketaux authentication error (status %d)", response.status_code)
            raise AuthenticationError(
                f"Marketaux authentication failed with status {response.status_code}."
            )
        if response.status_code == 429:
            logger.warning("Marketaux rate limit reached (HTTP 429)")
            raise RateLimitError("Marketaux rate limit / quota exceeded.")
        if response.status_code >= 400:
            logger.error("Marketaux returned HTTP error %d", response.status_code)
            raise NewsProviderError(
                f"Marketaux error response (HTTP {response.status_code}): {response.text[:200]}"
            )
        try:
            data = response.json()
        except Exception as exc:
            logger.error("Marketaux response could not be parsed as JSON")
            raise NewsProviderError("Failed to parse Marketaux JSON response") from exc
        if not isinstance(data, dict):
            raise NewsProviderError("Marketaux response root is not a JSON object")
        if "error" in data:
            error_info = data["error"]
            err_msg = error_info.get("message") if isinstance(error_info, dict) else str(error_info)
            logger.error("Marketaux returned logical error: %s", err_msg)
            raise NewsProviderError(f"Marketaux API error: {err_msg}")
        return data
        url = f"{self.base_url}/news"
        # Log sanitized params to avoid leaking secrets.
        sanitized = self._sanitize_params_for_logging(request_params)
        logger.debug("Fetching Marketaux news with params: %s", sanitized)
        try:
            response = http_client.get(url, params=request_params)
        except (httpx.TimeoutException, TimeoutError) as exc:
            logger.warning("Marketaux request timed out after %.1f seconds", self.timeout)
            raise ProviderTimeoutError(
                f"Marketaux request timed out after {self.timeout}s"
            ) from exc
        except (httpx.RequestError, httpx.TransportError) as exc:
            logger.error("Marketaux network/transport error: %s", type(exc).__name__)
            raise NewsProviderError(f"Marketaux transport error: {type(exc).__name__}") from exc
        finally:
            if owns_client:
                http_client.close()
        if response.status_code in (401, 403):
            logger.error("Marketaux authentication error (status %d)", response.status_code)
            raise AuthenticationError(
                f"Marketaux authentication failed with status {response.status_code}."
            )
        if response.status_code == 429:
            logger.warning("Marketaux rate limit reached (HTTP 429)")
            raise RateLimitError("Marketaux rate limit / quota exceeded.")
        if response.status_code >= 400:
            logger.error("Marketaux returned HTTP error %d", response.status_code)
            raise NewsProviderError(
                f"Marketaux error response (HTTP {response.status_code}): {response.text[:200]}"
            )
        try:
            data = response.json()
        except Exception as exc:
            logger.error("Marketaux response could not be parsed as JSON")
            raise NewsProviderError("Failed to parse Marketaux JSON response") from exc
        if not isinstance(data, dict):
            raise NewsProviderError("Marketaux response root is not a JSON object")
        if "error" in data:
            error_info = data["error"]
            err_msg = error_info.get("message") if isinstance(error_info, dict) else str(error_info)
            logger.error("Marketaux returned logical error: %s", err_msg)
            raise NewsProviderError(f"Marketaux API error: {err_msg}")
        return data

    def get_company_news(
        self,
        symbols: list[str],
        published_after: datetime | None = None,
        page: int = 1,
        limit: int = 3,
    ) -> dict[str, Any]:
        """Retrieve news filtered by entity symbols."""
        if not symbols:
            return {"meta": {"found": 0, "returned": 0, "page": page}, "data": []}

        # Marketaux supports comma-separated symbols up to batch limit
        clean_symbols = [s.strip().upper() for s in symbols if s and s.strip()]
        if not clean_symbols:
            return {"meta": {"found": 0, "returned": 0, "page": page}, "data": []}

        params: dict[str, Any] = {
            "symbols": ",".join(clean_symbols),
            "filter_entities": "true",
            "language": "en",
            "page": page,
            "limit": max(1, min(limit, 3)),  # Free tier caps at 3 articles
        }

        if published_after is not None:
            if published_after.tzinfo is None:
                published_after = published_after.replace(tzinfo=timezone.utc)
            params["published_after"] = published_after.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

        return self.fetch_news(params)

    def get_broad_news(
        self,
        search: str | None = None,
        countries: str = "in",
        published_after: datetime | None = None,
        page: int = 1,
        limit: int = 3,
    ) -> dict[str, Any]:
        """Retrieve broad financial and macroeconomic news."""
        params: dict[str, Any] = {
            "language": "en",
            "page": page,
            "limit": max(1, min(limit, 3)),
        }

        if countries:
            params["countries"] = countries.lower()

        if search:
            params["search"] = search

        if published_after is not None:
            if published_after.tzinfo is None:
                published_after = published_after.replace(tzinfo=timezone.utc)
            params["published_after"] = published_after.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

        return self.fetch_news(params)
