"""Personalized news feed service.

Retrieves articles linked (via ``ArticleEntity``) to companies on the
requesting user's watchlist.  The implementation uses three queries
regardless of watchlist size:

1. Fetch the set of watchlisted company IDs for the user.
2. Count distinct articles that match all active filters.
3. Fetch one page of those articles (with source / entity eager-loads).

A fourth lightweight query fetches the latest sentiment per
article-company pair for the page articles only, keyed on the highest
``SentimentAnalysis.id`` per ``(article_id, company_id)``.

``Article.company_id`` is never read; all company associations go through
``ArticleEntity``.

PostgreSQL compatibility note
------------------------------
Tests run against SQLite (in-memory).  The queries use only standard
SQL constructs (subqueries, GROUP BY, correlated IN) that work on both
engines.  The ``NULLS LAST`` ordering is emulated via
``Article.published_at.desc().nullslast()`` which SQLAlchemy renders
correctly for both dialects.
"""

from __future__ import annotations

import math
from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, joinedload

from backend.app.schemas.article import ArticleEntityResponse, ArticleResponse, SourceResponse
from backend.app.schemas.feed import FeedArticleResponse, FeedFilters, FeedSentimentResult, PaginatedFeedResponse
from shared.models import Article, ArticleEntity, SentimentAnalysis, Watchlist


def _get_watchlisted_company_ids(db: Session, user_id: int) -> list[int]:
    """Return the list of company IDs on the user's watchlist."""
    rows = db.execute(
        select(Watchlist.company_id).where(Watchlist.user_id == user_id)
    ).scalars().all()
    return list(rows)


def get_personalized_feed(
    db: Session,
    user_id: int,
    filters: FeedFilters,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedFeedResponse:
    """Return a paginated personalized feed for *user_id*.

    Raises
    ------
    ValueError
        If *filters.company_id* is set but that company is not on the
        user's watchlist, or if *start_date* > *end_date*.
    """
    page = max(1, page)
    page_size = max(1, min(page_size, 100))

    # ------------------------------------------------------------------
    # 1. Validate date range
    # ------------------------------------------------------------------
    if (
        filters.start_date is not None
        and filters.end_date is not None
        and filters.start_date > filters.end_date
    ):
        raise ValueError("start_date must not be after end_date")

    # ------------------------------------------------------------------
    # 2. Resolve watchlisted company IDs
    # ------------------------------------------------------------------
    watchlisted_ids = _get_watchlisted_company_ids(db, user_id)

    if filters.company_id is not None:
        if filters.company_id not in watchlisted_ids:
            raise ValueError(
                f"Company {filters.company_id} is not on the user's watchlist"
            )
        effective_company_ids = [filters.company_id]
    else:
        effective_company_ids = watchlisted_ids

    # Empty watchlist → return empty feed immediately.
    if not effective_company_ids:
        return PaginatedFeedResponse(
            total=0,
            page=page,
            page_size=page_size,
            total_pages=0,
            items=[],
        )

    # ------------------------------------------------------------------
    # 3. Build the shared WHERE clause across count + fetch queries.
    #    We join Article → ArticleEntity to filter by company membership.
    #    A DISTINCT on Article.id is enforced via subquery to prevent
    #    duplicate rows when an article matches multiple watchlisted companies.
    # ------------------------------------------------------------------
    # Sub-select: distinct article IDs that satisfy all filters.
    entity_join_cond = ArticleEntity.article_id == Article.id

    conditions = [ArticleEntity.company_id.in_(effective_company_ids)]

    if filters.sentiment_label is not None:
        # Filter articles that have at least one SentimentAnalysis with the
        # requested label for any of the watchlisted companies.
        sentiment_subq = (
            select(SentimentAnalysis.article_id)
            .where(
                and_(
                    SentimentAnalysis.company_id.in_(effective_company_ids),
                    SentimentAnalysis.label == filters.sentiment_label,
                )
            )
            .scalar_subquery()
        )
        conditions.append(Article.id.in_(sentiment_subq))

    if filters.start_date is not None:
        conditions.append(Article.published_at >= filters.start_date)

    if filters.end_date is not None:
        conditions.append(Article.published_at <= filters.end_date)

    # Sub-select of matching article IDs (distinct to avoid fan-out).
    matching_ids_subq = (
        select(Article.id)
        .join(ArticleEntity, entity_join_cond)
        .where(and_(*conditions))
        .distinct()
        .scalar_subquery()
    )

    # ------------------------------------------------------------------
    # 4. Count query
    # ------------------------------------------------------------------
    total_count: int = (
        db.execute(
            select(func.count()).select_from(
                select(Article.id).where(Article.id.in_(matching_ids_subq)).subquery()
            )
        ).scalar()
        or 0
    )
    total_pages = math.ceil(total_count / page_size) if total_count > 0 else 0

    # ------------------------------------------------------------------
    # 5. Fetch one page of articles (eager-load source + entities)
    # ------------------------------------------------------------------
    order_criteria = (
        Article.published_at.desc().nullslast(),
        Article.fetched_at.desc(),
        Article.id.desc(),
    )

    articles = (
        db.execute(
            select(Article)
            .where(Article.id.in_(matching_ids_subq))
            .options(
                joinedload(Article.source),
                joinedload(Article.entities).joinedload(ArticleEntity.company),
            )
            .order_by(*order_criteria)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .unique()
        .scalars()
        .all()
    )

    if not articles:
        return PaginatedFeedResponse(
            total=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            items=[],
        )

    # ------------------------------------------------------------------
    # 6. Fetch latest sentiment per (article_id, company_id) for this page.
    #    "Latest" = highest SentimentAnalysis.id among records with the
    #    same (article_id, company_id) pair.  This is deterministic and
    #    engine-agnostic.
    # ------------------------------------------------------------------
    page_article_ids = [a.id for a in articles]

    # Sub-select: max id per (article_id, company_id) pair.
    max_id_subq = (
        select(
            func.max(SentimentAnalysis.id).label("max_id"),
        )
        .where(
            and_(
                SentimentAnalysis.article_id.in_(page_article_ids),
                SentimentAnalysis.company_id.in_(effective_company_ids),
            )
        )
        .group_by(SentimentAnalysis.article_id, SentimentAnalysis.company_id)
        .scalar_subquery()
    )

    sentiment_rows = (
        db.execute(
            select(SentimentAnalysis)
            .where(SentimentAnalysis.id.in_(max_id_subq))
            .options(joinedload(SentimentAnalysis.company))
        )
        .unique()
        .scalars()
        .all()
    )

    # Index by article_id for O(1) lookup.
    sentiment_by_article: dict[int, list[FeedSentimentResult]] = {}
    for sa in sentiment_rows:
        result = FeedSentimentResult(
            company_id=sa.company_id,
            company_ticker=sa.company.ticker,
            company_name=sa.company.name,
            label=sa.label,
            score=sa.score,
            confidence=sa.confidence,
            model_used=sa.model_used,
        )
        sentiment_by_article.setdefault(sa.article_id, []).append(result)

    # ------------------------------------------------------------------
    # 7. Assemble response items.
    # ------------------------------------------------------------------
    items: list[FeedArticleResponse] = []
    for article in articles:
        # Reuse existing schema machinery for source / entities.
        article_schema = ArticleResponse.model_validate(article)
        items.append(
            FeedArticleResponse(
                id=article_schema.id,
                title=article_schema.title,
                url=article_schema.url,
                summary=article_schema.summary,
                published_at=article_schema.published_at,
                fetched_at=article_schema.fetched_at,
                provider_id=article_schema.provider_id,
                image_url=article_schema.image_url,
                author=article_schema.author,
                source=article_schema.source.model_dump(),
                entities=[e.model_dump() for e in article_schema.entities],
                matched_companies=sentiment_by_article.get(article.id, []),
            )
        )

    return PaginatedFeedResponse(
        total=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=items,
    )
