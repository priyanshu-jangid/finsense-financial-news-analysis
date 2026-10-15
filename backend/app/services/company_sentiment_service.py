"""Company sentiment aggregation service.

Provides functionality to aggregate persisted SentimentAnalysis records for a given
company over an optional date range.
"""

from datetime import datetime, date, UTC
from fastapi import HTTPException
from typing import List, Optional

from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from shared.models import Company, SentimentAnalysis


class DailyTrendPoint(BaseModel):
    date: date
    count: int
    average_score: Optional[float] = None

    class Config:
        from_attributes = True


class CompanySentimentSummary(BaseModel):
    company_id: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    total_analyses: int
    positive_count: int
    neutral_count: int
    negative_count: int
    average_score: Optional[float] = None
    daily_trend: List[DailyTrendPoint] = []

    class Config:
        from_attributes = True


def _validate_date_range(start: Optional[date], end: Optional[date]) -> None:
    """Validate that start is not after end.
    Raises ValueError if the range is invalid.
    """
    if start and end and start > end:
        raise ValueError("start_date must be before or equal to end_date")


def _company_exists(db: Session, company_id: int) -> bool:
    return db.query(Company.id).filter(Company.id == company_id).scalar() is not None


def aggregate_company_sentiment(
    db: Session,
    company_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> CompanySentimentSummary:
    """Aggregate sentiment analyses for a company.

    Args:
        db: SQLAlchemy session.
        company_id: Target company primary key.
        start_date: Inclusive start date (UTC) for the analysis creation timestamp.
        end_date: Inclusive end date (UTC).

    Returns:
        CompanySentimentSummary containing counts, average signed score, and a daily trend.
    """
    if not _company_exists(db, company_id):
        raise HTTPException(status_code=404, detail="Company not found")

    try:
        _validate_date_range(start_date, end_date)
    except ValueError as ve:
        raise HTTPException(status_code=500, detail=str(ve))

    # Base query for SentimentAnalysis filtered by company and optional dates.
    stmt = select(SentimentAnalysis).where(SentimentAnalysis.company_id == company_id)
    if start_date:
        stmt = stmt.where(
            SentimentAnalysis.created_at >= datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)
        )
    if end_date:
        # end of day inclusive
        stmt = stmt.where(
            SentimentAnalysis.created_at <= datetime.combine(end_date, datetime.max.time(), tzinfo=UTC)
        )

    analyses: List[SentimentAnalysis] = db.execute(stmt).scalars().all()

    total = len(analyses)
    positive = sum(1 for a in analyses if a.label == "positive")
    neutral = sum(1 for a in analyses if a.label == "neutral")
    negative = sum(1 for a in analyses if a.label == "negative")
    average_score = None
    if total:
        average_score = sum(a.score for a in analyses) / total

    # Build daily trend – group by UTC calendar day of created_at.
    daily: dict[date, List[float]] = {}
    for a in analyses:
        d = a.created_at.date()
        daily.setdefault(d, []).append(a.score)
    daily_trend: List[DailyTrendPoint] = []
    for d in sorted(daily):
        scores = daily[d]
        daily_trend.append(
            DailyTrendPoint(date=d, count=len(scores), average_score=(sum(scores) / len(scores) if scores else None))
        )

    return CompanySentimentSummary(
        company_id=company_id,
        start_date=start_date,
        end_date=end_date,
        total_analyses=total,
        positive_count=positive,
        neutral_count=neutral,
        negative_count=negative,
        average_score=average_score,
        daily_trend=daily_trend,
    )
