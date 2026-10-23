from datetime import datetime
from typing import Literal

from pydantic import BaseModel

ShiftStatusLiteral = Literal[
    "insufficient_data",
    "stable",
    "improving",
    "deteriorating",
]


class OverviewWindow(BaseModel):
    """Measured values for one comparison window.

    ``start`` is inclusive and ``end`` is exclusive. Datetimes are UTC
    (stored without a timezone, like the rest of the API).
    """

    start: datetime
    end: datetime
    article_count: int
    average_score: float | None


class OverviewLabelCounts(BaseModel):
    positive: int
    neutral: int
    negative: int


class WatchlistCompanyOverview(BaseModel):
    company_id: int
    ticker: str
    name: str
    sector: str | None
    current_window: OverviewWindow
    previous_window: OverviewWindow
    # current average minus previous average; null when either window has
    # fewer articles than ``min_articles_per_window``.
    score_delta: float | None
    # A measured difference in average sentiment, not a claim about causes.
    shift_status: ShiftStatusLiteral
    current_label_counts: OverviewLabelCounts
    # Negative-labelled eligible articles in the current window.
    negative_article_count: int
    # Most recent non-null publication time (not after ``as_of``) among all
    # articles linked to the company, whether or not they have sentiment.
    latest_article_published_at: datetime | None


class WatchlistOverviewTotals(BaseModel):
    companies_tracked: int
    # Companies whose status is "improving" or "deteriorating".
    companies_with_sentiment_shift: int
    # Sum of negative_article_count across companies.
    negative_article_count: int


class WatchlistOverviewResponse(BaseModel):
    user_id: int
    as_of: datetime
    window_days: int
    min_articles_per_window: int
    shift_threshold: float
    companies: list[WatchlistCompanyOverview]
    totals: WatchlistOverviewTotals