import argparse
import csv
import sys
from pathlib import Path

from sqlalchemy import func

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.core.database import SessionLocal
from shared.models import Company
CSV_PATH = ROOT / "data" / "reference" / "sp500_constituents.csv"


def load_constituents():
    if not CSV_PATH.is_file():
        raise FileNotFoundError(f"Constituent CSV not found: {CSV_PATH}")

    constituents = []
    seen = set()

    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        required = {"Symbol", "Name", "Sector"}

        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(
                f"CSV must contain columns {sorted(required)}; "
                f"found {reader.fieldnames}"
            )

        for line_number, row in enumerate(reader, start=2):
            ticker = (row.get("Symbol") or "").strip().upper()
            name = (row.get("Name") or "").strip()
            sector = (row.get("Sector") or "").strip() or None

            if not ticker or not name:
                raise ValueError(
                    f"Missing ticker or company name at CSV line {line_number}"
                )

            if len(ticker) > 20 or len(name) > 200:
                raise ValueError(
                    f"Ticker or company name exceeds database limits "
                    f"at CSV line {line_number}"
                )

            if sector and len(sector) > 100:
                raise ValueError(
                    f"Sector exceeds database limit at CSV line {line_number}"
                )

            if ticker in seen:
                raise ValueError(f"Duplicate ticker in CSV: {ticker}")

            seen.add(ticker)
            constituents.append({
                "ticker": ticker,
                "name": name,
                "sector": sector,
            })

    if len(constituents) < 500:
        raise ValueError(
            f"Expected at least 500 constituent rows; found {len(constituents)}"
        )

    return constituents


def seed(apply_changes: bool):
    constituents = load_constituents()
    db = SessionLocal()

    try:
        existing = {
            company.ticker.upper(): company
            for company in db.query(Company).all()
        }

        new_count = 0
        updated_count = 0
        membership_count = 0

        # Count membership changes before changing any rows.
        incoming_tickers = {item["ticker"] for item in constituents}
        membership_count = sum(
            1 for ticker, company in existing.items()
            if ticker in incoming_tickers and not company.is_sp500
        )

        for item in constituents:
            company = existing.get(item["ticker"])

            if company is None:
                company = Company(
                    ticker=item["ticker"],
                    name=item["name"],
                    sector=item["sector"],
                    is_sp500=True,
                )
                db.add(company)
                new_count += 1
            else:
                if (
                    company.name != item["name"]
                    or company.sector != item["sector"]
                    or not company.is_sp500
                ):
                    updated_count += 1

                company.name = item["name"]
                company.sector = item["sector"]
                company.is_sp500 = True

        # Clear membership from companies absent from this snapshot.
        # Company records and their related data are never deleted.
        stale_count = sum(
            1 for ticker, company in existing.items()
            if company.is_sp500 and ticker not in incoming_tickers
        )

        for ticker, company in existing.items():
            if ticker not in incoming_tickers:
                company.is_sp500 = False

        print(f"CSV constituents:       {len(constituents)}")
        print(f"New company records:    {new_count}")
        print(f"Existing records updated: {updated_count}")
        print(f"Previously nonmembers added to index: {membership_count}")
        print(f"Existing members removed from snapshot: {stale_count}")

        if not apply_changes:
            db.rollback()
            print("\nDRY RUN: no database changes committed.")
            print("Review the counts, then rerun with --apply to commit.")
            return

        db.commit()

        total_members = (
            db.query(func.count(Company.id))
            .filter(Company.is_sp500.is_(True))
            .scalar()
        )

        print("\nImport committed successfully.")
        print(f"Companies marked as S&P 500 members: {total_members}")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Import S&P 500 constituents into FinSense."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Commit changes. Without this flag, run a dry run.",
    )
    args = parser.parse_args()

    try:
        seed(apply_changes=args.apply)
    except Exception as exc:
        print(f"Import failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
