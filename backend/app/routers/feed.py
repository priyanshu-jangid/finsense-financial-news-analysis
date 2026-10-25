"""Personalized news feed router.

Exposes ``GET /users/{user_id}/feed`` — an auth-guarded, ownership-checked
endpoint that returns paginated articles linked (via ArticleEntity) to
companies on the authenticated user's watchlist.

Query parameters
----------------
page : int ≥ 1, default 1
page_size : int 1-100, default 20
company_id : int, optional — must be on the user's watchlist
sentiment : str, optional — "positive" | "neutral" | "negative"
start_date : ISO 8601 datetime, optional
end_date : ISO 8601 datetime, optional

Invalid date ranges (start_date > end_date) are rejected with 422.
A company_id not on the user's watchlist is rejected with 400.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.dependencies import get_current_user
from backend.app.schemas.feed import FeedFilters, PaginatedFeedResponse
from backend.app.services.personalized_feed_service import get_personalized_feed
from shared.models import User

router = APIRouter(
    prefix="/users/{user_id}/feed",
    tags=["Feed"],
)

_SENTIMENT_LABELS = {"positive", "neutral", "negative"}


@router.get(
    "",
    response_model=PaginatedFeedResponse,
    summary="Get personalized news feed",
)
def get_user_feed(
    user_id: int,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    company_id: int | None = Query(
        default=None,
        description="Filter to a specific company (must be on the user's watchlist)",
    ),
    sentiment: str | None = Query(
        default=None,
        description="Filter by sentiment label: positive | neutral | negative",
    ),
    start_date: datetime | None = Query(
        default=None,
        description="ISO 8601 datetime — include only articles published at or after this time",
    ),
    end_date: datetime | None = Query(
        default=None,
        description="ISO 8601 datetime — include only articles published at or before this time",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedFeedResponse:
    """Return a paginated personalized news feed for the authenticated user."""
    # Ownership check — matches the pattern used in watchlists.py.
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view another user's feed",
        )

    # Validate sentiment label value early so the error is a 422, not a 500.
    if sentiment is not None and sentiment not in _SENTIMENT_LABELS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid sentiment value '{sentiment}'. Must be one of: positive, neutral, negative",
        )

    filters = FeedFilters(
        company_id=company_id,
        sentiment_label=sentiment,
        start_date=start_date,
        end_date=end_date,
    )

    try:
        return get_personalized_feed(
            db=db,
            user_id=user_id,
            filters=filters,
            page=page,
            page_size=page_size,
        )
    except ValueError as exc:
        detail = str(exc)
        if "start_date" in detail:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=detail,
            )
        # company_id not on watchlist
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )
