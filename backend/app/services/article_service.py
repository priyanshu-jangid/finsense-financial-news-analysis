"""Article retrieval service for fetching stored articles from PostgreSQL."""

import math
from sqlalchemy import func, select, or_
from sqlalchemy.orm import Session, joinedload

from shared.models import Article, ArticleEntity, Company, IngestionCheckpoint


def get_paginated_articles(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
) -> tuple[list[Article], int, int]:
    """Retrieve all stored articles with pagination.

    Returns (articles, total_count, total_pages).
    """
    page = max(1, page)
    page_size = max(1, min(page_size, 100))

    base_query = select(Article).options(
        joinedload(Article.source),
        joinedload(Article.entities).joinedload(ArticleEntity.company),
    )

    count_query = select(func.count(Article.id))

    if search:
        search_filter = or_(
            Article.title.ilike(f"%{search}%"),
            Article.summary.ilike(f"%{search}%"),
        )
        base_query = base_query.where(search_filter)
        count_query = count_query.where(search_filter)

    total_count = db.execute(count_query).scalar() or 0
    total_pages = math.ceil(total_count / page_size) if total_count > 0 else 0

    order_criteria = (
        Article.published_at.desc().nullslast(),
        Article.fetched_at.desc(),
        Article.id.desc(),
    )

    articles = (
        db.execute(
            base_query.order_by(*order_criteria)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .unique()
        .scalars()
        .all()
    )

    return list(articles), total_count, total_pages


def get_company_articles(
    db: Session,
    company_id: int,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Article], int, int]:
    """Retrieve stored articles associated with a specific company."""
    page = max(1, page)
    page_size = max(1, min(page_size, 100))

    base_query = (
        select(Article)
        .join(ArticleEntity, ArticleEntity.article_id == Article.id)
        .where(ArticleEntity.company_id == company_id)
        .options(
            joinedload(Article.source),
            joinedload(Article.entities).joinedload(ArticleEntity.company),
        )
    )

    count_query = (
        select(func.count(Article.id))
        .join(ArticleEntity, ArticleEntity.article_id == Article.id)
        .where(ArticleEntity.company_id == company_id)
    )

    total_count = db.execute(count_query).scalar() or 0
    total_pages = math.ceil(total_count / page_size) if total_count > 0 else 0

    order_criteria = (
        Article.published_at.desc().nullslast(),
        Article.fetched_at.desc(),
        Article.id.desc(),
    )

    articles = (
        db.execute(
            base_query.order_by(*order_criteria)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .unique()
        .scalars()
        .all()
    )

    return list(articles), total_count, total_pages


def get_market_articles(
    db: Session,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Article], int, int]:
    """Retrieve broad market and macroeconomic news articles.

    Broad market news includes articles that are macroeconomic / economy-wide,
    specifically articles not constrained to a single company, or articles where
    entities are empty or broad market keywords appear.
    """
    page = max(1, page)
    page_size = max(1, min(page_size, 100))

    # Identify articles that are unlinked to individual companies OR broad macroeconomic topics
    base_query = (
        select(Article)
        .outerjoin(ArticleEntity, ArticleEntity.article_id == Article.id)
        .options(
            joinedload(Article.source),
            joinedload(Article.entities).joinedload(ArticleEntity.company),
        )
        .where(ArticleEntity.id.is_(None))
    )

    count_query = (
        select(func.count(Article.id))
        .outerjoin(ArticleEntity, ArticleEntity.article_id == Article.id)
        .where(ArticleEntity.id.is_(None))
    )

    total_count = db.execute(count_query).scalar() or 0
    total_pages = math.ceil(total_count / page_size) if total_count > 0 else 0

    order_criteria = (
        Article.published_at.desc().nullslast(),
        Article.fetched_at.desc(),
        Article.id.desc(),
    )

    articles = (
        db.execute(
            base_query.order_by(*order_criteria)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .unique()
        .scalars()
        .all()
    )

    return list(articles), total_count, total_pages


def get_checkpoints_status(db: Session) -> list[IngestionCheckpoint]:
    """Retrieve all ingestion checkpoints."""
    return list(
        db.execute(
            select(IngestionCheckpoint).order_by(IngestionCheckpoint.feed_type)
        )
        .scalars()
        .all()
    )
