"""Unit tests for the news ingestion scheduler."""

from unittest.mock import MagicMock, patch
import pytest

from apscheduler.triggers.interval import IntervalTrigger

from backend.app.core.config import settings
from backend.app.tasks.news_scheduler import (
    is_scheduler_running,
    run_scheduled_ingestion,
    shutdown_news_scheduler,
    start_news_scheduler,
)


@pytest.fixture(autouse=True)
def clean_scheduler():
    shutdown_news_scheduler()
    yield
    shutdown_news_scheduler()


def test_scheduler_lifecycle():
    assert is_scheduler_running() is False
    scheduler = start_news_scheduler()
    assert scheduler is not None
    assert is_scheduler_running() is True

    # Starting again should return existing running instance without errors
    scheduler2 = start_news_scheduler()
    assert scheduler2 is scheduler

    shutdown_news_scheduler()
    assert is_scheduler_running() is False


def test_scheduler_configured_interval():
    scheduler = start_news_scheduler()
    jobs = scheduler.get_jobs()
    ingest_job = next((j for j in jobs if j.id == "financial_news_ingestion"), None)
    assert ingest_job is not None

    trigger = ingest_job.trigger
    assert isinstance(trigger, IntervalTrigger)
    expected_interval = settings.INGESTION_INTERVAL_HOURS
    assert trigger.interval.total_seconds() == expected_interval * 3600


def test_scheduled_job_invokes_ingestion_service():
    with patch("backend.app.tasks.news_scheduler.NewsIngestionService") as mock_service_cls:
        mock_instance = MagicMock()
        mock_instance.ingest_all.return_value = MagicMock(
            status="success",
            total_fetched=3,
            total_persisted=2,
            errors=[],
        )
        mock_service_cls.return_value = mock_instance

        run_scheduled_ingestion()
        mock_instance.ingest_all.assert_called_once()


def test_scheduled_job_handles_errors_resiliently():
    with patch("backend.app.tasks.news_scheduler.NewsIngestionService") as mock_service_cls:
        mock_instance = MagicMock()
        mock_instance.ingest_all.side_effect = RuntimeError("Simulated network outage")
        mock_service_cls.return_value = mock_instance

        # Should log the exception without raising or crashing
        run_scheduled_ingestion()
        mock_instance.ingest_all.assert_called_once()


def test_overlapping_job_execution_prevention():
    from backend.app.tasks.news_scheduler import _job_lock

    with patch("backend.app.tasks.news_scheduler.NewsIngestionService") as mock_service_cls:
        mock_instance = MagicMock()
        mock_service_cls.return_value = mock_instance

        # Simulate job already running by acquiring lock
        acquired = _job_lock.acquire(blocking=False)
        assert acquired is True

        try:
            # Second execution attempt should be skipped immediately
            run_scheduled_ingestion()
            mock_instance.ingest_all.assert_not_called()
        finally:
            _job_lock.release()
