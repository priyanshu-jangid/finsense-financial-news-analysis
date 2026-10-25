"""Pydantic schemas for the personalized news feed endpoint."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FeedSentimentResult(BaseModel):
    """The latest (highest-id) sentiment record for one article-company pair."""

    company_id: int
    company_ticker: str
    company_name: str
    label: str
    score: float
    confidence: float
    model_used: str

    model_config = ConfigDict(from_attributes=True)


class FeedArticleResponse(BaseModel):
    """An article from the personalized feed.

    Identical to the public ``ArticleResponse`` contract plus a
    ``matched_companies`` list that shows which watchlisted companies are
    linked to this article and their latest sentiment record.
    """

    id: int
    title: str
    url: str
    summary: str | None = None
    published_at: datetime | None = None
    fetched_at: datetime
    provider_id: str | None = None
    image_url: str | None = None
    author: str | None = None
    source: dict
    entities: list[dict] = []
    matched_companies: list[FeedSentimentResult] = []

    model_config = ConfigDict(from_attributes=False)


class PaginatedFeedResponse(BaseModel):
    """Paginated response for the personalized feed."""

    total: int
    page: int
    page_size: int
    total_pages: int
    items: list[FeedArticleResponse]


# ---------------------------------------------------------------------------
# Internal dataclass — not serialised; used only by the service layer.
# ---------------------------------------------------------------------------


@dataclass
class FeedFilters:
    """Optional filters applied to the personalized feed query."""

    company_id: int | None = None
    sentiment_label: str | None = None  # "positive" | "neutral" | "negative"
    start_date: datetime | None = None
    end_date: datetime | None = None
