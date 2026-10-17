'''Background scheduler for pending sentiment analysis.

Runs a job that iterates over all companies and analyses any pending articles
that have not yet been processed for that company.
'''

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from backend.app.core.config import settings
from backend.app.services.company_service import get_companies
from backend.app.services.company_sentiment_service import analyse_pending_articles
# Import SentimentEngine lazily from the actual implementation module
# This avoids import errors during test collection when the engine class is defined elsewhere
# and allows monkeypatching in tests.
from nlp.pipeline.sentiment import SentimentEngine
from backend.app.core.database import SessionLocal

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _run_analysis_job(*, engine: SentimentEngine | None = None, session_factory: callable | None = None) -> None:
    """Execute sentiment analysis for all companies.

    This function is invoked by the APScheduler background job. It uses the
    provided ``session_factory`` (defaulting to ``SessionLocal``) to obtain a
    session, reads the list of company IDs, then creates a fresh session for each
    company. ``engine`` is passed through to ``analyse_pending_articles``.
    Errors are logged but do not stop the scheduler.
    """
    if session_factory is None:
        session_factory = SessionLocal
    # 1️⃣ Fetch company IDs using a temporary session
    try:
        with session_factory() as db:
            companies = get_companies(db)
            company_ids = [c.id for c in companies]
    except Exception as outer_exc:
        logger.error("Unexpected error fetching companies: %s", outer_exc)
        return

    total_created = 0
    # 2️⃣ Process each company in its own session
    for company_id in company_ids:
        # Create a brand‑new session for this company
        company_db = session_factory()
        try:
            created = analyse_pending_articles(company_db, company_id, engine=engine)
            company_db.commit()
            total_created += created
        except Exception as exc:
            logger.error("Error processing company %s", company_id, exc_info=True)
            company_db.rollback()
        finally:
            company_db.close()

    if total_created:
        logger.info("Sentiment analysis job created %d new rows", total_created)



def start_sentiment_scheduler() -> BackgroundScheduler | None:
    """
    Initialize and start the sentiment analysis scheduler.

    The interval can be configured via ``settings.INGESTION_INTERVAL_HOURS`` to
    run in sync with the news ingestion schedule.
    """
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        logger.debug("Sentiment scheduler already running")
        return _scheduler

    interval_hours = max(1, settings.INGESTION_INTERVAL_HOURS)
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        _run_analysis_job,
        trigger=IntervalTrigger(hours=interval_hours),
        id="sentiment_analysis",
        name="FinSense Sentiment Analysis Scheduler",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    logger.info("Sentiment analysis scheduler started (interval %d h)", interval_hours)
    return _scheduler


def shutdown_sentiment_scheduler() -> None:
    """Gracefully shut down the sentiment scheduler if it is running."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        logger.info("Shutting down sentiment analysis scheduler...")
        _scheduler.shutdown(wait=False)
    _scheduler = None
