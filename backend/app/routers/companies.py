from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import date

from backend.app.core.database import get_db
from backend.app.schemas.company import CompanyCreate, CompanyResponse
from backend.app.services.company_service import (
    create_company,
    get_companies,
    get_company,
)
from backend.app.schemas.company_sentiment import CompanySentimentSummaryResponse
from backend.app.services.company_sentiment_service import aggregate_company_sentiment, analyse_pending_articles
from backend.app.dependencies import get_current_user
from shared.models import User

router = APIRouter(
    prefix="/companies",
    tags=["Companies"],
)

@router.post(
    "",
    response_model=CompanyResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_company_endpoint(
    company_data: CompanyCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_company(db, company_data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

@router.get(
    "",
    response_model=list[CompanyResponse],
)
def list_companies(
    db: Session = Depends(get_db),
):
    return get_companies(db)

@router.get(
    "/{company_id}",
    response_model=CompanyResponse,
)
def get_company_endpoint(
    company_id: int,
    db: Session = Depends(get_db),
):
    company = get_company(db, company_id)
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )
    return company

@router.get(
    "/{company_id}/sentiment",
    response_model=CompanySentimentSummaryResponse,
    summary="Aggregate sentiment for a company",
)
def get_company_sentiment(
    company_id: int,
    start_date: date | None = Query(default=None, description="Inclusive start date (YYYY-MM-DD)"),
    end_date: date | None = Query(default=None, description="Inclusive end date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
):
    """Aggregate sentiment analyses for a company over an optional date range."""
    company = get_company(db, company_id)
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )
    summary = aggregate_company_sentiment(db, company_id, start_date, end_date)
    return summary

@router.post(
    "/{company_id}/sentiment/analyze",
    response_model=dict,
    status_code=status.HTTP_200_OK,
)
def trigger_sentiment_analysis(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run sentiment analysis on all pending articles for a company.

    Returns the number of newly created SentimentAnalysis rows.
    """
    # Verify company exists
    company = get_company(db, company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    try:
        created = analyse_pending_articles(db, company_id)
        db.commit()
    except RuntimeError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="Sentiment engine unavailable") from exc
    return {"created": created}
