"""Pydantic schemas for news articles and ingestion status."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class SourceResponse(BaseModel):
    id: int
    name: str
    domain: str
    credibility_tier: int

    model_config = ConfigDict(from_attributes=True)


class CompanyBriefResponse(BaseModel):
    id: int
    ticker: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class ArticleEntityResponse(BaseModel):
    id: int
    company_id: int
    relevance_score: float | None = None
    company: CompanyBriefResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class ArticleResponse(BaseModel):
    id: int
    title: str
    url: str
    summary: str | None = None
    published_at: datetime | None = None
    fetched_at: datetime
    provider_id: str | None = None
    image_url: str | None = None
    author: str | None = None
    source: SourceResponse
    entities: list[ArticleEntityResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class PaginatedArticlesResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: list[ArticleResponse]


class IngestionFeedResultResponse(BaseModel):
    feed_type: str
    articles_fetched: int
    articles_persisted: int
    articles_deduplicated: int
    status: str
    errors: list[str] = Field(default_factory=list)


class IngestionTriggerResponse(BaseModel):
    status: str
    total_fetched: int
    total_persisted: int
    company_feed: IngestionFeedResultResponse
    broad_feed: IngestionFeedResultResponse
    errors: list[str] = Field(default_factory=list)


class CheckpointStatusResponse(BaseModel):
    id: int
    feed_type: str
    last_successful_published_at: datetime | None
    last_run_at: datetime
    status: str
    articles_fetched: int
    articles_persisted: int
    error_message: str | None

    model_config = ConfigDict(from_attributes=True)


class IngestionStatusResponse(BaseModel):
    is_scheduler_running: bool
    interval_hours: int
    checkpoints: list[CheckpointStatusResponse]
    # Manual ingestion status (idle, queued, running, success, partial_failure, failure)
    manual_job_status: str
    manual_job_total_fetched: int | None = None
    manual_job_total_persisted: int | None = None
    manual_job_errors: list[str] | None = None
