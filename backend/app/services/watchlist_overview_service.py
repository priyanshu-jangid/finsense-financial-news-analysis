"""Watchlist overview: per-company sentiment windows and shift status.

Runs a constant number of database queries regardless of watchlist size:

1. the user's watchlisted companies,
2. sentiment records (joined to their article's ``published_at``) for those
   companies within the two comparison windows,
3. the latest publication time per company.

Companies are linked to articles through ``ArticleEntity`` only; the legacy
``Article.company_id`` column is never read. Window assignment, latest-record
collapsing and shift detection are delegated to ``sentiment_shift_service``.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from backend.app.schemas.watchlist_overview import (
    OverviewLabelCounts,
    OverviewWindow,
    WatchlistCompanyOverview,
    WatchlistOverviewResponse,
    WatchlistOverviewTotals,
)
from backend.app.services.sentiment_shift_service import (
    DEFAULT_SHIFT_RULES,
    SentimentObservation,
    SentimentShiftResult,
    ShiftRules,
    ShiftStatus,
    WindowStats,
    compute_windows,
    detect_shifts,
)
from shared.models import (
    Article,
    ArticleEntity,
    Company,
    SentimentAnalysis,
    Watchlist,
)


def _utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _to_window(stats: WindowStats) -> OverviewWindow:
    return OverviewWindow(
        start=stats.start,
        end=stats.end,
        article_count=stats.article_count,
        average_score=stats.mean_score,
    )


def _to_company_overview(
    company_row,
    result: SentimentShiftResult,
    latest_published_at: datetime | None,
) -> WatchlistCompanyOverview:
    return WatchlistCompanyOverview(
        company_id=company_row.id,
        ticker=company_row.ticker,
        name=company_row.name,
        sector=company_row.sector,
        current_window=_to_window(result.current),
        previous_window=_to_window(result.previous),
        score_delta=result.delta,
        shift_status=result.status.value,
        current_label_counts=OverviewLabelCounts(
            positive=result.current.positive_count,
            neutral=result.current.neutral_count,
            negative=result.current.negative_count,
        ),
        negative_article_count=result.current.negative_count,
        latest_article_published_at=latest_published_at,
    )


def get_watchlist_overview(
    db: Session,
    user_id: int,
    *,
    as_of: datetime | None = None,
    rules: ShiftRules = DEFAULT_SHIFT_RULES,
) -> WatchlistOverviewResponse:
    """Build the overview for ``user_id`` as of ``as_of`` (naive UTC by default)."""
    windows = compute_windows(
        as_of if as_of is not None else _utc_now_naive(), rules
    )

    company_rows = db.execute(
        select(Company.id, Company.ticker, Company.name, Company.sector)
        .join(Watchlist, Watchlist.company_id == Company.id)
        .where(Watchlist.user_id == user_id)
        .order_by(Company.ticker, Company.id)
    ).all()

    if not company_rows:
        return WatchlistOverviewResponse(
            user_id=user_id,
            as_of=windows.as_of,
            window_days=rules.window_days,
            min_articles_per_window=rules.min_articles_per_window,
            shift_threshold=rules.shift_threshold,
            companies=[],
            totals=WatchlistOverviewTotals(
                companies_tracked=0,
                companies_with_sentiment_shift=0,
                negative_article_count=0,
            ),
        )

    company_ids = [row.id for row in company_rows]

    # Sentiment records for watchlisted companies whose article was published
    # within [previous_start, as_of]. Null publication times never match the
    # range. Joining ArticleEntity on both keys enforces a valid company
    # association (it is unique per article/company, so it cannot fan out).
    sentiment_rows = db.execute(
        select(
            SentimentAnalysis.id,
            SentimentAnalysis.article_id,
            SentimentAnalysis.company_id,
            SentimentAnalysis.label,
            SentimentAnalysis.score,
            SentimentAnalysis.created_at,
            Article.published_at,
        )
        .join(Article, Article.id == SentimentAnalysis.article_id)
        .join(
            ArticleEntity,
            and_(
                ArticleEntity.article_id == SentimentAnalysis.article_id,
                ArticleEntity.company_id == SentimentAnalysis.company_id,
            ),
        )
        .where(
            SentimentAnalysis.company_id.in_(company_ids),
            Article.published_at.is_not(None),
            Article.published_at >= windows.previous_start,
            Article.published_at <= windows.as_of,
        )
    ).all()

    observations = [
        SentimentObservation(
            article_id=row.article_id,
            company_id=row.company_id,
            published_at=row.published_at,
            label=row.label,
            score=row.score,
            analysis_created_at=row.created_at,
            analysis_id=row.id,
        )
        for row in sentiment_rows
    ]

    latest_rows = db.execute(
        select(ArticleEntity.company_id, func.max(Article.published_at))
        .join(Article, Article.id == ArticleEntity.article_id)
        .where(
            ArticleEntity.company_id.in_(company_ids),
            Article.published_at.is_not(None),
            Article.published_at <= windows.as_of,
        )
        .group_by(ArticleEntity.company_id)
    ).all()
    latest_by_company = {company_id: latest for company_id, latest in latest_rows}

    results = detect_shifts(company_ids, observations, as_of=windows.as_of, rules=rules)

    companies = [
        _to_company_overview(
            row, results[row.id], latest_by_company.get(row.id)
        )
        for row in company_rows
    ]

    return WatchlistOverviewResponse(
        user_id=user_id,
        as_of=windows.as_of,
        window_days=rules.window_days,
        min_articles_per_window=rules.min_articles_per_window,
        shift_threshold=rules.shift_threshold,
        companies=companies,
        totals=WatchlistOverviewTotals(
            companies_tracked=len(companies),
            companies_with_sentiment_shift=sum(
                1
                for result in results.values()
                if result.status
                in (ShiftStatus.IMPROVING, ShiftStatus.DETERIORATING)
            ),
            negative_article_count=sum(
                company.negative_article_count for company in companies
            ),
        ),
    )