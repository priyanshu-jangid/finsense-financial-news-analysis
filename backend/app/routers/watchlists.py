from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.schemas.watchlist import (
    WatchlistCreate,
    WatchlistResponse,
)
from backend.app.services.watchlist_service import (
    add_to_watchlist,
    get_user_watchlist,
    remove_from_watchlist,
)


router = APIRouter(
    prefix="/users/{user_id}/watchlist",
    tags=["Watchlist"],
)


@router.post(
    "",
    response_model=WatchlistResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_company_to_watchlist(
    user_id: int,
    watchlist_data: WatchlistCreate,
    db: Session = Depends(get_db),
):
    try:
        return add_to_watchlist(
            db,
            user_id,
            watchlist_data,
        )
    except ValueError as exc:
        detail = str(exc)

        if detail == "User not found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=detail,
            )

        if detail == "Company not found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=detail,
            )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )


@router.get(
    "",
    response_model=list[WatchlistResponse],
)
def list_user_watchlist(
    user_id: int,
    db: Session = Depends(get_db),
):
    try:
        return get_user_watchlist(db, user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.delete(
    "/{company_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_company_from_watchlist(
    user_id: int,
    company_id: int,
    db: Session = Depends(get_db),
):
    removed = remove_from_watchlist(
        db,
        user_id,
        company_id,
    )

    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company is not in the user's watchlist",
        )
