
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
from backend.app.services.news_ingestion import NewsIngestionService, OverallIngestionResult

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None
_scheduler_lock = threading.Lock()
_job_lock = threading.Lock()

# Manual job state abstraction (thread‑safe)
from dataclasses import dataclass, field

@dataclass
class ManualJobState:
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    status: str = "idle"  # idle | queued | running | success | partial_failure | failure
    result: "OverallIngestionResult | None" = None

    def set(self, status: str, result=None):
        with self._lock:
            self.status = status
            self.result = result

    def get(self):
        with self._lock:
            return {"status": self.status, "result": self.result}

_manual_job_state = ManualJobState()

def is_ingestion_job_running() -> bool:
    """Return True if a ingestion job (scheduled or manual) is currently running."""
    return _job_lock.locked()

def get_manual_job_info() -> dict:
    """Return a dictionary with the current manual ingestion job status and results."""
    state = _manual_job_state.get()
    info = {
        "status": state["status"],
        "total_fetched": None,
        "total_persisted": None,
        "errors": None,
    }
    if state["result"] is not None:
        result = state["result"]
        info["total_fetched"] = result.total_fetched
        info["total_persisted"] = result.total_persisted
        info["errors"] = result.errors
    return info






def run_scheduled_ingestion() -> None:
    """Execute news ingestion in a dedicated background task with non-overlapping concurrency lock.
    Returns immediately if live news is disabled.
    """
    # Acquire lock non‑blocking; if another ingestion job is running, skip this scheduled run
    lock_acquired = _job_lock.acquire(blocking=False)
    if not lock_acquired:
        logger.warning("Scheduled news ingestion skipped because another ingestion job is running.")
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
        if lock_acquired and _job_lock.locked():
            _job_lock.release()

def run_manual_ingestion(lock_already_acquired: bool = False) -> None:
    """Execute news ingestion as a manual background job.
    Handles lock acquisition (or assumes it's already held), updates manual job state via the
    thread‑safe helper, and ensures DB session and lock cleanup.
    """
    # Determine whether we need to acquire the lock here
    lock_acquired_here = False
    if not lock_already_acquired:
        lock_acquired_here = _job_lock.acquire(blocking=False)
        if not lock_acquired_here:
            # Could not acquire; mark job as queued (will be handled by caller)
            _manual_job_state.set("queued")
            return
    # At this point we hold the lock (either from caller or just acquired)
    _manual_job_state.set("running")
    start_time = time.monotonic()
    db = SessionLocal()
    try:
        service = NewsIngestionService()
        result: OverallIngestionResult = service.ingest_all(db)
        # Update state with final status and result
        if result.errors:
            final_status = "partial_failure" if result.total_persisted > 0 else "failure"
        else:
            final_status = "success"
        _manual_job_state.set(final_status, result)
        duration = time.monotonic() - start_time
        logger.info(
            "Manual news ingestion completed in %.2fs: status=%s, fetched=%d, persisted=%d, errors=%d",
            duration,
            final_status,
            result.total_fetched,
            result.total_persisted,
            len(result.errors),
        )
    except Exception as exc:
        logger.exception("Unhandled exception in manual news ingestion")
        _manual_job_state.set("failure", None)
    finally:
        db.close()
        # Ensure the lock is released after the job finishes, even if it was acquired by the caller
        if _job_lock.locked():
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
