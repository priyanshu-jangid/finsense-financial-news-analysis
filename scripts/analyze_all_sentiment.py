import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.core.database import SessionLocal
from backend.app.services.company_sentiment_service import (
    analyse_pending_articles,
)
from backend.app.services.sentiment_engine import get_sentiment_engine
from shared.models import Company


def main():
    db = SessionLocal()
    total_created = 0
    companies_processed = 0
    failures = []

    try:
        # Load the local FinBERT model once and reuse it.
        engine = get_sentiment_engine()

        companies = (
            db.query(Company)
            .order_by(Company.ticker)
            .all()
        )

        print(f"Companies found: {len(companies)}")
        print("Starting sentiment analysis...\n")

        for company in companies:
            try:
                created = analyse_pending_articles(
                    db,
                    company.id,
                    engine=engine,
                )
                db.commit()

                total_created += created
                companies_processed += 1

                if created:
                    print(
                        f"{company.ticker}: "
                        f"{created} new sentiment analyses"
                    )

            except Exception as exc:
                db.rollback()
                failures.append((company.ticker, str(exc)))
                print(f"FAILED {company.ticker}: {exc}")

        print("\n--- Sentiment Analysis Summary ---")
        print(f"Companies processed: {companies_processed}/{len(companies)}")
        print(f"New sentiment analyses: {total_created}")
        print(f"Companies with errors: {len(failures)}")

        if failures:
            print("\nFailures:")
            for ticker, error in failures:
                print(f"- {ticker}: {error}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
