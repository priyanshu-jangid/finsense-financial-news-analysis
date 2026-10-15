"""Pydantic schemas for company sentiment aggregation responses.
"""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DailyTrendPointResponse(BaseModel):
    date: date
    count: int
    average_score: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class CompanySentimentSummaryResponse(BaseModel):
    company_id: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    total_analyses: int
    positive_count: int
    neutral_count: int
    negative_count: int
    average_score: Optional[float] = None
    daily_trend: List[DailyTrendPointResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

