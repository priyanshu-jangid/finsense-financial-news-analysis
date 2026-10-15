"""API endpoints for news articles and ingestion management."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.dependencies import get_current_user
from backend.app.schemas.article import (
    ArticleResponse,
    CheckpointStatusResponse,
    IngestionStatusResponse,
    IngestionTriggerResponse,
    PaginatedArticlesResponse,
)
from backend.app.services.article_service import (
    get_checkpoints_status,
    get_company_articles,
    get_market_articles,
    get_paginated_articles,
)
from backend.app.services.company_service import get_company
from backend.app.services.news_ingestion import NewsIngestionService
from backend.app.tasks.news_scheduler import is_scheduler_running
from shared.models import User

router = APIRouter(
    prefix="/articles",
    tags=["Articles"],
)


@router.get(
    "",
    response_model=PaginatedArticlesResponse,
    summary="List stored news articles",
)
def list_articles(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    search: str | None = Query(default=None, max_length=100, description="Search keyword"),
    db: Session = Depends(get_db),
):
    """Retrieve stored financial news articles from the database with pagination."""
    articles, total, total_pages = get_paginated_articles(
        db, page=page, page_size=page_size, search=search
    )
    return PaginatedArticlesResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=[ArticleResponse.model_validate(art) for art in articles],
    )


@router.get(
    "/market",
    response_model=PaginatedArticlesResponse,
    summary="Get broad market news feed",
)
def get_market_news(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
):
    """Retrieve broad macroeconomic and market-wide news feed."""
    articles, total, total_pages = get_market_articles(
        db, page=page, page_size=page_size
    )
    return PaginatedArticlesResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=[ArticleResponse.model_validate(art) for art in articles],
    )


@router.get(
    "/company/{company_id}",
    response_model=PaginatedArticlesResponse,
    summary="Get news for a specific company",
)
def get_company_news(
    company_id: int,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
):
    """Retrieve news articles associated with a specific company."""
    company = get_company(db, company_id)
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    articles, total, total_pages = get_company_articles(
        db, company_id=company_id, page=page, page_size=page_size
    )
    return PaginatedArticlesResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=[ArticleResponse.model_validate(art) for art in articles],
    )


@router.post(
    "/ingest",
    response_model=IngestionTriggerResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger automated news ingestion",
)
def trigger_news_ingestion(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Authenticated endpoint to trigger financial news ingestion across company and broad feeds.
    Returns 503 Service Unavailable when live news ingestion is disabled.
    """

    service = NewsIngestionService()
    result = service.ingest_all(db)

    return IngestionTriggerResponse(
        status=result.status,
        total_fetched=result.total_fetched,
        total_persisted=result.total_persisted,
        company_feed={
            "feed_type": result.company_feed.feed_type,
            "articles_fetched": result.company_feed.articles_fetched,
            "articles_persisted": result.company_feed.articles_persisted,
            "articles_deduplicated": result.company_feed.articles_deduplicated,
            "status": result.company_feed.status,
            "errors": result.company_feed.errors,
        },
        broad_feed={
            "feed_type": result.broad_feed.feed_type,
            "articles_fetched": result.broad_feed.articles_fetched,
            "articles_persisted": result.broad_feed.articles_persisted,
            "articles_deduplicated": result.broad_feed.articles_deduplicated,
            "status": result.broad_feed.status,
            "errors": result.broad_feed.errors,
        },
        errors=result.errors,
    )


@router.get(
    "/ingestion-status",
    response_model=IngestionStatusResponse,
    summary="Get ingestion checkpoints and scheduler status",
)
def get_ingestion_status(
    db: Session = Depends(get_db),
):
    """Retrieve the status of news ingestion checkpoints and the scheduler."""
    checkpoints = get_checkpoints_status(db)
    return IngestionStatusResponse(
        is_scheduler_running=is_scheduler_running(),
        interval_hours=settings.INGESTION_INTERVAL_HOURS,
        checkpoints=[
            CheckpointStatusResponse.model_validate(cp) for cp in checkpoints
        ],
    )
