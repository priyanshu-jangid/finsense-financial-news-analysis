import sys
from pathlib import Path
import argparse

# Ensure the project root is in sys.path for imports
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.core.database import SessionLocal
from backend.app.services.company_sentiment_service import analyse_pending_articles
from backend.app.services.sentiment_engine import get_sentiment_engine
from shared.models import Company, ArticleEntity, SentimentAnalysis
from sqlalchemy import select, func

def count_pending_for_company(db, company_id):
    """Return the number of article‑company pairs that lack a sentiment analysis.

    Mirrors the logic in ``analyse_pending_articles`` but only counts rows.
    """
    linked_article_ids = (
        select(ArticleEntity.article_id)
        .where(ArticleEntity.company_id == company_id)
    )
    existing_article_ids = (
        select(SentimentAnalysis.article_id)
        .where(
            SentimentAnalysis.article_id.in_(linked_article_ids),
            SentimentAnalysis.company_id == company_id,
        )
    )
    pending_count = (
        db.query(func.count(ArticleEntity.article_id))
        .filter(ArticleEntity.company_id == company_id)
        .filter(~ArticleEntity.article_id.in_(existing_article_ids))
        .scalar()
    )
    return pending_count or 0

def main():
    parser = argparse.ArgumentParser(
        description="Analyze all stored articles lacking sentiment for their associated company."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be processed without writing any results.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process at most N pending article‑company pairs (useful for testing).",
    )
    args = parser.parse_args()

    db = SessionLocal()
    total_processed = 0
    total_skipped = 0
    total_created = 0
    failures = []
    engine = None

    try:
        if not args.dry_run:
            engine = get_sentiment_engine()

        companies_query = db.query(Company).order_by(Company.ticker)
        for company in companies_query:
            if args.limit is not None and total_processed >= args.limit:
                break

            pending = count_pending_for_company(db, company.id)
            if pending == 0:
                total_skipped += 1
                continue

            to_process = pending
            if args.limit is not None:
                remaining = args.limit - total_processed
                if remaining <= 0:
                    break
                to_process = min(pending, remaining)

            if args.dry_run:
                print(f"[DRY RUN] Company {company.ticker}: {to_process} pending analyses would be created.")
                total_processed += to_process
                continue

            try:
                created = analyse_pending_articles(db, company.id, engine=engine)
                if args.limit is not None:
                    created = min(created, to_process)
                db.commit()
                total_created += created
                total_processed += created
            except Exception as exc:
                db.rollback()
                failures.append((company.ticker, str(exc)))
                print(f"FAILED {company.ticker}: {exc}")

        print("\n--- Sentiment Analysis Batch Summary ---")
        print(f"Processed pairs: {total_processed}")
        print(f"Skipped (no pending): {total_skipped}")
        print(f"New sentiment analyses: {total_created}")
        print(f"Failures: {len(failures)}")
        if failures:
            print("\nFailure details:")
            for ticker, err in failures:
                print(f"- {ticker}: {err}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
