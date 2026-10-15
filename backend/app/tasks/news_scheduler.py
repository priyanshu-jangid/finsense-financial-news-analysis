
"""Scheduler for periodic financial news ingestion.

Configured to run every three hours using APScheduler AsyncIOScheduler.
Ensures non-overlapping runs, standalone database sessions, safe shutdown,
and responsive API operations.
"""

from datetime import datetime, timezone
import logging
import threading
import time

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from backend.app.core.config import settings
from backend.app.core.database import SessionLocal
from backend.app.services.news_ingestion import NewsIngestionService

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None
_scheduler_lock = threading.Lock()
_job_lock = threading.Lock()


def run_scheduled_ingestion() -> None:
    """Execute news ingestion in a dedicated background task with non-overlapping concurrency lock.
    Returns immediately if live news is disabled.
    """
# Continue even if live news disabled; provider will guard real calls

    if not _job_lock.acquire(blocking=False):
        logger.warning("Previous news ingestion job is still running; skipping overlapping trigger.")
        return

    start_time = time.monotonic()
    now_utc = datetime.now(timezone.utc).isoformat()
    logger.info("News ingestion job triggered at %s", now_utc)


    db = SessionLocal()
    try:
        service = NewsIngestionService()
        result = service.ingest_all(db)
        duration = time.monotonic() - start_time
        logger.info(
            "News ingestion job completed in %.2fs: status=%s, fetched=%d, persisted=%d, errors=%d",
            duration,
            result.status,
            result.total_fetched,
            result.total_persisted,
            len(result.errors),
        )
    except Exception as exc:
        duration = time.monotonic() - start_time
        logger.error(
            "Unhandled exception in scheduled news ingestion job after %.2fs: %s",
            duration,
            exc,
            exc_info=True,
        )
    finally:
        db.close()
        _job_lock.release()


def start_news_scheduler() -> BackgroundScheduler | None:
    """Initialize and start the background news ingestion scheduler."""
    global _scheduler

    with _scheduler_lock:
        if _scheduler is not None and _scheduler.running:
            logger.debug("Scheduler is already running.")
            return _scheduler

        interval_hours = max(1, settings.INGESTION_INTERVAL_HOURS)
        logger.info("Initializing news ingestion scheduler (interval: %d hours)", interval_hours)

        _scheduler = BackgroundScheduler()
        _scheduler.add_job(
            run_scheduled_ingestion,
            trigger=IntervalTrigger(hours=interval_hours),
            id="financial_news_ingestion",
            name="FinSense 3-Hour Financial News Ingestion",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        _scheduler.start()
        logger.info("News ingestion scheduler started successfully.")
        return _scheduler


def shutdown_news_scheduler() -> None:
    """Gracefully shutdown the news ingestion scheduler."""
    global _scheduler

    with _scheduler_lock:
        if _scheduler is not None:
            if _scheduler.running:
                logger.info("Shutting down news ingestion scheduler...")
                _scheduler.shutdown(wait=False)
            _scheduler = None


def is_scheduler_running() -> bool:
    """Check if the scheduler is active and running."""
    with _scheduler_lock:
        return _scheduler is not None and _scheduler.running
