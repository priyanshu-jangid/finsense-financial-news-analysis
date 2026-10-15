"""Financial news ingestion service.

Handles:
- Normalization and validation of raw provider articles
- Canonical URL deduplication and provider ID deduplication
- Company entity linking via CompanyMatcher
- Incremental retrieval using database-persisted checkpoints
- Separate company-specific and broad-market ingestion flows
- Transaction-safe database persistence
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
import logging
from typing import Any
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.services.company_matcher import match_companies_for_article
from backend.app.services.news_provider import (
    MarketauxClient,
    NewsProviderError,
    RateLimitError,
    AuthenticationError,
)
from shared.models import Article, ArticleEntity, Company, IngestionCheckpoint, Source

logger = logging.getLogger(__name__)

# Query parameters commonly used for tracking that should be stripped for canonicalization
TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "ref", "fbclid", "gclid", "_ga", "ncid", "guccounter", "guce_referrer",
}


@dataclass
class FeedIngestionResult:
    feed_type: str
    articles_fetched: int = 0
    articles_persisted: int = 0
    articles_deduplicated: int = 0
    status: str = "success"  # success, partial_failure, failure
    errors: list[str] = field(default_factory=list)


@dataclass
class OverallIngestionResult:
    status: str
    company_feed: FeedIngestionResult
    broad_feed: FeedIngestionResult
    total_fetched: int = 0
    total_persisted: int = 0
    errors: list[str] = field(default_factory=list)


def canonicalize_url(raw_url: str) -> str:
    """Normalize article URLs to safely detect duplicate links."""
    if not raw_url or not isinstance(raw_url, str):
        return ""

    try:
        parsed = urlparse(raw_url.strip())
        scheme = (parsed.scheme or "https").lower()
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]

        path = parsed.path.rstrip("/") if parsed.path != "/" else "/"

        # Filter out tracking query parameters and sort remainder
        query_items = [
            (k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
            if k.lower() not in TRACKING_PARAMS
        ]
        query_items.sort()
        clean_query = urlencode(query_items)

        # Drop fragments/anchors
        return urlunparse((scheme, netloc, path, "", clean_query, ""))
    except Exception:
        return raw_url.strip()


def parse_provider_datetime(dt_str: Any) -> datetime | None:
    """Safely parse provider ISO datetime string to timezone-naive or UTC datetime."""
    if not dt_str or not isinstance(dt_str, str):
        return None

    clean_str = dt_str.strip()
    try:
        # Replace trailing Z with +00:00 for fromisoformat compatibility
        if clean_str.endswith("Z"):
            clean_str = clean_str[:-1] + "+00:00"
        dt = datetime.fromisoformat(clean_str)
        # Ensure UTC timezone
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    except Exception:
        logger.debug("Could not parse datetime string: %s", dt_str)
        return None


def get_or_create_source(db: Session, source_name: str | None, article_url: str) -> Source:
    """Retrieve existing source by domain or create a new one."""
    domain = ""
    if article_url:
        try:
            parsed = urlparse(article_url)
            domain = parsed.netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
        except Exception:
            domain = ""

    if not domain and source_name:
        domain = source_name.lower().strip()
        if domain.startswith("www."):
            domain = domain[4:]

    if not domain:
        domain = "unknown.com"

    # Check for existing source
    source = db.execute(select(Source).where(Source.domain == domain)).scalar_one_or_none()
    if source:
        return source

    display_name = source_name.strip() if source_name else domain.capitalize()
    if len(display_name) > 200:
        display_name = display_name[:200]

    source = Source(
        name=display_name,
        domain=domain[:255],
        credibility_tier=1,
    )
    db.add(source)
    db.flush()
    return source


def get_checkpoint(db: Session, feed_type: str) -> IngestionCheckpoint:
    """Get or create ingestion checkpoint for the given feed type."""
    checkpoint = db.execute(
        select(IngestionCheckpoint).where(IngestionCheckpoint.feed_type == feed_type)
    ).scalar_one_or_none()

    if checkpoint is None:
        checkpoint = IngestionCheckpoint(
            feed_type=feed_type,
            status="idle",
            articles_fetched=0,
            articles_persisted=0,
        )
        db.add(checkpoint)
        db.flush()

    return checkpoint


class NewsIngestionService:
    """Orchestrates news retrieval, validation, company linking, and persistence."""

    def __init__(self, provider_client: MarketauxClient | None = None):
        self.provider = provider_client or MarketauxClient()

    def persist_raw_article(
        self,
        db: Session,
        raw_article: dict[str, Any],
        companies: list[Company],
    ) -> tuple[Article | None, bool]:
        """Normalize, match companies, and persist an article idempotently.

        Returns (article, was_created).
        """
        raw_url = raw_article.get("url")
        if not raw_url or not isinstance(raw_url, str):
            logger.debug("Skipping article without URL")
            return None, False

        canonical_url = canonicalize_url(raw_url)
        if not canonical_url:
            return None, False

        provider_id = raw_article.get("uuid")
        if provider_id and isinstance(provider_id, str):
            provider_id = provider_id.strip()[:100]
        else:
            provider_id = None

        # 1. Deduplication check: lookup by provider_id OR canonical url
        existing_article: Article | None = None
        if provider_id:
            existing_article = db.execute(
                select(Article).where(Article.provider_id == provider_id)
            ).scalar_one_or_none()

        if existing_article is None:
            existing_article = db.execute(
                select(Article).where(Article.url == canonical_url)
            ).scalar_one_or_none()

        matches = match_companies_for_article(raw_article, companies)

        if existing_article is not None:
            # Reuse existing article. Add any newly identified company entities.
            was_updated = False
            for match in matches:
                entity_exists = db.execute(
                    select(ArticleEntity).where(
                        ArticleEntity.article_id == existing_article.id,
                        ArticleEntity.company_id == match.company.id,
                    )
                ).scalar_one_or_none()

                if entity_exists is None:
                    new_entity = ArticleEntity(
                        article_id=existing_article.id,
                        company_id=match.company.id,
                        relevance_score=match.relevance_score,
                    )
                    db.add(new_entity)
                    was_updated = True

            # Safely enrich empty fields if provider has non-empty data
            if not existing_article.provider_id and provider_id:
                existing_article.provider_id = provider_id
                was_updated = True
            if not existing_article.image_url and raw_article.get("image_url"):
                existing_article.image_url = str(raw_article["image_url"])[:1000]
                was_updated = True
            if not existing_article.summary and raw_article.get("description"):
                existing_article.summary = str(raw_article["description"])
                was_updated = True

            if was_updated:
                db.flush()
            return existing_article, False

        # 2. Insert new article
        title = (raw_article.get("title") or "Untitled Article").strip()[:500]
        summary = raw_article.get("description") or raw_article.get("snippet") or None
        published_at = parse_provider_datetime(raw_article.get("published_at"))
        raw_source = raw_article.get("source")
        source_name = str(raw_source) if raw_source else None
        source = get_or_create_source(db, source_name, canonical_url)

        image_url = raw_article.get("image_url")
        if image_url and isinstance(image_url, str):
            image_url = image_url[:1000]
        else:
            image_url = None

        author = raw_article.get("author")
        if author and isinstance(author, str):
            author = author[:255]
        else:
            author = None

        article = Article(
            source_id=source.id,
            title=title,
            url=canonical_url[:2000],
            content=None,  # Do not store full copyrighted body text
            summary=summary,
            published_at=published_at,
            fetched_at=datetime.now(timezone.utc).replace(tzinfo=None),
            provider_id=provider_id,
            image_url=image_url,
            author=author,
        )
        db.add(article)
        db.flush()

        # Link companies
        for match in matches:
            entity = ArticleEntity(
                article_id=article.id,
                company_id=match.company.id,
                relevance_score=match.relevance_score,
            )
            db.add(entity)

        db.flush()
        return article, True

    def ingest_company_news(
        self,
        db: Session,
        lookback_hours: int | None = None,
        max_symbols_per_batch: int = 5,
    ) -> FeedIngestionResult:
        """Ingest company-specific financial news for distinct tracked companies."""
        result = FeedIngestionResult(feed_type="company")
        checkpoint = get_checkpoint(db, "company")
        checkpoint.last_run_at = datetime.now(timezone.utc).replace(tzinfo=None)

        all_companies = db.execute(select(Company)).scalars().all()
        if not all_companies:
            logger.info("No companies found in database; skipping company news ingestion.")
            checkpoint.status = "success"
            checkpoint.error_message = None
            db.commit()
            return result

        # Calculate incremental retrieval since_time
        if checkpoint.last_successful_published_at is not None:
            overlap = timedelta(minutes=settings.NEWS_CHECKPOINT_OVERLAP_MINUTES)
            since_time = checkpoint.last_successful_published_at - overlap
        else:
            lookback = lookback_hours or settings.NEWS_DEFAULT_LOOKBACK_HOURS
            since_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=lookback)

        symbols = [c.ticker.strip().upper() for c in all_companies if c.ticker and c.ticker.strip()]
        logger.info(
            "Starting company news ingestion for %d companies since %s",
            len(symbols),
            since_time.isoformat(),
        )

        max_published_seen: datetime | None = None
        has_partial_error = False

        # Query provider in batches of supported symbols
        for i in range(0, len(symbols), max_symbols_per_batch):
            batch = symbols[i : i + max_symbols_per_batch]
            try:
                response = self.provider.get_company_news(
                    symbols=batch,
                    published_after=since_time,
                    limit=3,
                )
            except (RateLimitError, AuthenticationError) as exc:
                err_msg = f"Provider error on batch {batch}: {type(exc).__name__} - {exc}"
                logger.error(err_msg)
                result.errors.append(err_msg)
                has_partial_error = True
                break
            except NewsProviderError as exc:
                err_msg = f"News provider failure on batch {batch}: {exc}"
                logger.error(err_msg)
                result.errors.append(err_msg)
                has_partial_error = True
                continue

            raw_articles = response.get("data") or []
            result.articles_fetched += len(raw_articles)

            for raw_art in raw_articles:
                try:
                    article, was_created = self.persist_raw_article(db, raw_art, all_companies)
                    if was_created:
                        result.articles_persisted += 1
                    else:
                        result.articles_deduplicated += 1

                    if article and article.published_at:
                        if max_published_seen is None or article.published_at > max_published_seen:
                            max_published_seen = article.published_at
                except Exception as exc:
                    db.rollback()
                    logger.error("Failed to persist article: %s", exc)
                    result.errors.append(f"Persistence error: {exc}")
                    has_partial_error = True

        try:
            checkpoint.articles_fetched = result.articles_fetched
            checkpoint.articles_persisted = result.articles_persisted

            if result.errors:
                if result.articles_persisted > 0:
                    checkpoint.status = "partial_failure"
                    result.status = "partial_failure"
                    if max_published_seen is not None:
                        checkpoint.last_successful_published_at = max_published_seen
                else:
                    checkpoint.status = "failure"
                    result.status = "failure"
                checkpoint.error_message = "; ".join(result.errors)[:500]
            else:
                checkpoint.status = "success"
                result.status = "success"
                checkpoint.error_message = None
                if max_published_seen is not None:
                    checkpoint.last_successful_published_at = max_published_seen
                elif checkpoint.last_successful_published_at is None:
                    checkpoint.last_successful_published_at = datetime.now(timezone.utc).replace(tzinfo=None)

            db.commit()
        except Exception as exc:
            db.rollback()
            logger.error("Failed to commit company news transaction: %s", exc)
            result.status = "failure"
            result.errors.append(f"DB commit error: {exc}")

        return result

    def ingest_broad_news(
        self,
        db: Session,
        lookback_hours: int | None = None,
    ) -> FeedIngestionResult:
        """Ingest broad macroeconomic and market-wide financial news."""
        result = FeedIngestionResult(feed_type="broad")
        checkpoint = get_checkpoint(db, "broad")
        checkpoint.last_run_at = datetime.now(timezone.utc).replace(tzinfo=None)

        all_companies = db.execute(select(Company)).scalars().all()

        if checkpoint.last_successful_published_at is not None:
            overlap = timedelta(minutes=settings.NEWS_CHECKPOINT_OVERLAP_MINUTES)
            since_time = checkpoint.last_successful_published_at - overlap
        else:
            lookback = lookback_hours or settings.NEWS_DEFAULT_LOOKBACK_HOURS
            since_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=lookback)

        logger.info("Starting broad market news ingestion since %s", since_time.isoformat())

        # Curated topics covering Indian macroeconomic and financial markets
        broad_search = 'RBI OR "monetary policy" OR inflation OR SEBI OR "Reserve Bank" OR earnings OR "Sensex" OR "Nifty"'

        max_published_seen: datetime | None = None
        try:
            response = self.provider.get_broad_news(
                search=broad_search,
                countries="in",
                published_after=since_time,
                limit=3,
            )
        except NewsProviderError as exc:
            err_msg = f"Broad news provider failure: {exc}"
            logger.error(err_msg)
            result.status = "failure"
            result.errors.append(err_msg)
            checkpoint.status = "failure"
            checkpoint.error_message = err_msg[:500]
            db.commit()
            return result

        raw_articles = response.get("data") or []
        result.articles_fetched = len(raw_articles)

        for raw_art in raw_articles:
            try:
                article, was_created = self.persist_raw_article(db, raw_art, all_companies)
                if was_created:
                    result.articles_persisted += 1
                else:
                    result.articles_deduplicated += 1

                if article and article.published_at:
                    if max_published_seen is None or article.published_at > max_published_seen:
                        max_published_seen = article.published_at
            except Exception as exc:
                db.rollback()
                logger.error("Failed to persist broad article: %s", exc)
                result.errors.append(f"Persistence error: {exc}")

        try:
            checkpoint.articles_fetched = result.articles_fetched
            checkpoint.articles_persisted = result.articles_persisted

            if result.errors:
                if result.articles_persisted > 0:
                    checkpoint.status = "partial_failure"
                    result.status = "partial_failure"
                    if max_published_seen is not None:
                        checkpoint.last_successful_published_at = max_published_seen
                else:
                    checkpoint.status = "failure"
                    result.status = "failure"
                checkpoint.error_message = "; ".join(result.errors)[:500]
            else:
                checkpoint.status = "success"
                result.status = "success"
                checkpoint.error_message = None
                if max_published_seen is not None:
                    checkpoint.last_successful_published_at = max_published_seen
                elif checkpoint.last_successful_published_at is None:
                    checkpoint.last_successful_published_at = datetime.now(timezone.utc).replace(tzinfo=None)

            db.commit()
        except Exception as exc:
            db.rollback()
            logger.error("Failed to commit broad news transaction: %s", exc)
            result.status = "failure"
            result.errors.append(f"DB commit error: {exc}")

        return result

    def ingest_all(self, db: Session) -> OverallIngestionResult:
        """Run both company-specific and broad financial news ingestion."""
        logger.info("Executing comprehensive financial news ingestion run...")
        company_res = self.ingest_company_news(db)
        broad_res = self.ingest_broad_news(db)

        all_errors = list(company_res.errors) + list(broad_res.errors)

        if company_res.status == "success" and broad_res.status == "success":
            overall_status = "success"
        elif company_res.status == "failure" and broad_res.status == "failure":
            overall_status = "failure"
        else:
            overall_status = "partial_failure"

        return OverallIngestionResult(
            status=overall_status,
            company_feed=company_res,
            broad_feed=broad_res,
            total_fetched=company_res.articles_fetched + broad_res.articles_fetched,
            total_persisted=company_res.articles_persisted + broad_res.articles_persisted,
            errors=all_errors,
        )
