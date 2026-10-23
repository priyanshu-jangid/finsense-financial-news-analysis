"""API endpoints for news articles and ingestion management."""

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.dependencies import get_current_user
from backend.app.schemas.article import (
    ArticleResponse,
    CheckpointStatusResponse,
    IngestionStatusResponse,
    IngestionTriggerResponse,
    IngestionFeedResultResponse,
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
from backend.app.tasks.news_scheduler import is_scheduler_running, run_manual_ingestion, _manual_job_state
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
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger manual news ingestion",
)
async def trigger_news_ingestion(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Authenticated endpoint to trigger news ingestion asynchronously.
    Returns 202 when the job is queued, 409 if another ingestion job is already in progress.
    """
    # Operator allowlist enforcement
    from backend.app.core.config import settings
    allowed_emails = [e.strip().lower() for e in settings.INGESTION_OPERATOR_EMAILS.split(',') if e.strip()]
    if not allowed_emails or current_user.email.lower() not in allowed_emails:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not authorized to trigger ingestion")

    # Queue background task; it will manage lock acquisition and job state
    _manual_job_state.set("queued")
    try:
        background_tasks.add_task(run_manual_ingestion, lock_already_acquired=False)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to schedule ingestion job")

    # Immediate queued response
    return IngestionTriggerResponse(
        status="queued",
        total_fetched=0,
        total_persisted=0,
        company_feed=IngestionFeedResultResponse(
            feed_type="company",
            articles_fetched=0,
            articles_persisted=0,
            articles_deduplicated=0,
            status="queued",
            errors=[],
        ),
        broad_feed=IngestionFeedResultResponse(
            feed_type="broad",
            articles_fetched=0,
            articles_persisted=0,
            articles_deduplicated=0,
            status="queued",
            errors=[],
        ),
        errors=[],
    )



@router.get(
    "/ingestion-status",
    response_model=IngestionStatusResponse,
    summary="Get ingestion checkpoints and scheduler status",
)
def get_ingestion_status(
    db: Session = Depends(get_db),
):
    """Retrieve the status of news ingestion checkpoints, scheduler, and manual job info."""
    checkpoints = get_checkpoints_status(db)
    from backend.app.tasks.news_scheduler import get_manual_job_info
    manual_info = get_manual_job_info()
    return IngestionStatusResponse(
        is_scheduler_running=is_scheduler_running(),
        interval_hours=settings.INGESTION_INTERVAL_HOURS,
        checkpoints=[
            CheckpointStatusResponse.model_validate(cp) for cp in checkpoints
        ],
        manual_job_status=manual_info.get("status", "idle"),
        manual_job_total_fetched=manual_info.get("total_fetched"),
        manual_job_total_persisted=manual_info.get("total_persisted"),
        manual_job_errors=manual_info.get("errors"),
    )
