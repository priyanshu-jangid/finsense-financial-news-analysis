# FinSense: Automated Financial News Ingestion (Milestone 2)

FinSense is an intelligent financial news aggregation and sentiment analysis platform designed to help users track high-signal financial news, macroeconomic updates, and company-specific disclosures for companies in their watchlists.

This milestone implements **Automated Financial News Ingestion** (Milestone 2), integrating external market news feeds, multi-factor company matching, robust deduplication, incremental checkpointing, public article retrieval APIs, and a 3-hour automated scheduler.

---

## 1. Architecture Overview

```
                      +-----------------------------+
                      |   Marketaux Financial API   |
                      +--------------+--------------+
                                     |  (HTTP JSON, Max 3 articles/call)
                                     v
                 +---------------------------------------+
                 |    NewsIngestionService Orchestrator  |
                 +-------------------+-------------------+
                                     |
         +---------------------------+---------------------------+
         |                                                       |
         v                                                       v
+-------------------------------+               +-------------------------------+
| Company-Specific News Flow    |               | Broad Macroeconomic News Flow |
| - Query tracked tickers       |               | - RBI, SEBI, Inflation, Repo  |
| - Batch symbols (up to 5/req) |               | - Broad Indian market updates |
+---------------+---------------+               +---------------+---------------+
                |                                               |
                +-----------------------+-----------------------+
                                        |
                                        v
                 +---------------------------------------+
                 |      CompanyMatcher & Guardrails      |
                 | - Provider entity symbol matching     |
                 | - Headline & summary matching         |
                 | - Short-ticker cashtag ambiguity check|
                 +----------------------+----------------+
                                        |
                                        v
                 +---------------------------------------+
                 |    Deduplication & Canonicalization   |
                 | - URL tracking parameter stripping    |
                 | - Provider UUID indexing              |
                 | - Publisher Source deduplication      |
                 +----------------------+----------------+
                                        |
                                        v
                 +---------------------------------------+
                 |         PostgreSQL Database           |
                 | - articles                            |
                 | - article_entities (relevance_score)  |
                 | - sources                             |
                 | - ingestion_checkpoints               |
                 +----------------------+----------------+
                                        |
         +------------------------------+------------------------------+
         |                                                             |
         v                                                             v
+----------------------------------+         +----------------------------------+
|      FastAPI REST Router         |         |     APScheduler In-Process Job   |
| - GET /articles                  |         | - Runs every 3 hours             |
| - GET /articles/market           |         | - Non-overlapping concurrency    |
| - GET /articles/company/{id}     |         | - Clean startup & shutdown       |
| - POST /articles/ingest (Auth)   |         +----------------------------------+
| - GET /articles/ingestion-status |
+----------------------------------+
```

---

## 2. News Provider Evaluation: Marketaux

### Capabilities
- **Entity Identification:** Maps news stories to over 200,000 global financial entities (equities, ETFs, indices, currencies).
- **Sentiment & Entity Tags:** Provides structured entity arrays including symbol, match score, and sentiment highlights.
- **Geographic Filtering:** Supports ISO country codes (e.g. `countries=in` for India).
- **Date Range Retrieval:** Supports `published_after` and `published_before` in ISO 8601 UTC format.

### Free-Tier Limitations
- **Daily Quota:** 100 API requests per day.
- **Articles per Request:** Limited to **3 articles** per request on the free tier.
- **Rate Limits:** HTTP 429 is returned if the rate limit is exceeded.

### Indian Equity & NSE/BSE Coverage
- **Symbol Formats:** Indian equities generally adhere to `.NS` (National Stock Exchange) or `.BO` (Bombay Stock Exchange) suffixes (e.g. `CANBK.NS`, `RELIANCE.BO`).
- **Coverage Scope:** Large-cap Indian equities (Nifty 50 / Sensex 30) have good coverage. Mid-cap and small-cap disclosures are comparatively sparse.
- **System Resilience:**
  - `CompanyMatcher` strips exchange suffixes (e.g., matching `RELIANCE.NS` against local database ticker `RELIANCE`).
  - Broad macroeconomic news (`countries=in` with keyword filters for RBI, SEBI, and repo rate) captures systemic stories even when ticker-specific news is quiet.
  - Unsupported or unmapped tickers are safely logged without crashing the pipeline.

---

## 3. Environment Configuration

The application reads configuration from environment variables via Pydantic Settings (`.env` file).

### Required & Configurable Variables

| Variable | Description | Default |
| :--- | :--- | :--- |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+psycopg://...` |
| `JWT_SECRET_KEY` | Secret key for JWT signing | *(Required)* |
| `MARKETAUX_API_TOKEN` | API token from Marketaux | `""` (Empty triggers mock/error) |
| `MARKETAUX_BASE_URL` | Marketaux API endpoint | `https://api.marketaux.com/v1` |
| `NEWS_REQUEST_TIMEOUT_SECONDS`| Network request timeout | `10.0` |
| `NEWS_DEFAULT_LOOKBACK_HOURS` | Historical lookback for first ingestion run | `24` |
| `NEWS_CHECKPOINT_OVERLAP_MINUTES`| Overlap window to catch delayed articles | `30` |
| `INGESTION_INTERVAL_HOURS` | Frequency of scheduled background job | `3` |
| `ENABLE_SCHEDULER` | Flag to enable/disable automated scheduler | `true` |

> [!NOTE]
> See `.env.example` for a sample configuration template. Never commit your actual `.env` file or real API tokens.

---

## 4. Database Setup & Migrations

Database tables are managed with Alembic.

To apply all migrations to PostgreSQL:
```bash
./.venv/bin/alembic upgrade head
```

### Milestone 2 Schema Additions:
- `articles.provider_id` (VARCHAR 100, indexed)
- `articles.image_url` (VARCHAR 1000, nullable)
- `articles.author` (VARCHAR 255, nullable)
- `article_entities.relevance_score` (FLOAT, nullable)
- `ingestion_checkpoints` table (tracks `feed_type`, `last_successful_published_at`, `last_run_at`, `status`, `articles_fetched`, `articles_persisted`, `error_message`).

---

## 5. Starting the Backend

Start the FastAPI application with Uvicorn:
```bash
./.venv/bin/uvicorn backend.app.main:app --reload
```

Interactive API documentation (Swagger UI) is available at:
`http://127.0.0.1:8000/docs`

---

## 6. Ingestion Mechanics

### A. Company-Specific News
- Identifies distinct companies tracked in PostgreSQL.
- Queries Marketaux in batches of up to 5 symbols using the `symbols` parameter and `filter_entities=true`.
- Matches articles against tracked companies using provider entity symbols, headlines, and summaries.

### B. Broad Macroeconomic News
- Queries Marketaux with `countries=in` and curated topics (e.g. RBI monetary policy, SEBI regulations, inflation, repo rates, corporate earnings).
- Stores macroeconomic news independently of user watchlists.

### C. Deduplication & Idempotency
- **Canonical URL:** URLs are normalized by lowercasing scheme/host, removing trailing slashes, stripping tracking parameters (`utm_*`, `ref`, `fbclid`, `gclid`), and sorting remaining query params.
- **Provider UUID:** Unique identifier from Marketaux is indexed and checked before insertion.
- **Relationship Enrichment:** If an existing article is found, new company relationships (`ArticleEntity`) are attached without duplicating the article record.
- **Source Reuse:** Reuses existing `Source` records by normalized domain instead of creating duplicate publishers.

### D. Checkpoint Management
- Checkpoints are persisted in `ingestion_checkpoints` for both `company` and `broad` feeds.
- If a provider request fails, the checkpoint is **not** advanced.
- On partial failure, the checkpoint only advances to the newest publication timestamp among successfully persisted articles.
- The default lookback window (24 hours) prevents unbounded backfills on the initial run.

---

## 7. Automated 3-Hour Scheduler

- Configured using APScheduler `BackgroundScheduler` in `backend/app/tasks/news_scheduler.py`.
- **Interval:** Runs every 3 hours (`INGESTION_INTERVAL_HOURS=3`).
- **Non-Overlapping:** Uses a concurrency thread lock `_job_lock` and `max_instances=1` to guarantee jobs never run concurrently.
- **FastAPI Lifespan:** Scheduler is started on application startup and cleanly stopped on application shutdown via FastAPI's `lifespan` handler.
- **Production Note:** In a multi-worker deployment (e.g. multiple Gunicorn/Uvicorn workers), designate a single worker or dedicated process for the scheduler (`ENABLE_SCHEDULER=false` on web workers) to prevent duplicate cron jobs.

---

## 8. API Endpoints

### News Retrieval Endpoints (Public, reads from PostgreSQL)
1. **List Articles (Paginated):**
   ```http
   GET /articles?page=1&page_size=20&search=earnings
   ```
2. **Company-Specific News:**
   ```http
   GET /articles/company/{company_id}?page=1&page_size=20
   ```
3. **Broad Market Feed:**
   ```http
   GET /articles/market?page=1&page_size=20
   ```
4. **Ingestion Checkpoint & Scheduler Status:**
   ```http
   GET /articles/ingestion-status
   ```

### News Ingestion Trigger (Authenticated)
5. **Trigger Ingestion Run:**
   ```http
   POST /articles/ingest
   Authorization: Bearer <access_token>
   ```

---

## 9. Running Tests

Run the test suite using pytest:
```bash
./.venv/bin/pytest -v
```

### Test Coverage Highlights:
- **`tests/test_news_provider.py`:** Tests Marketaux HTTP client, authentication handling, 401 errors, 429 rate limits, network timeouts, malformed JSON, and secret redaction.
- **`tests/test_news_ingestion.py`:** Tests URL canonicalization, timestamp parsing, article persistence, provider ID and canonical URL deduplication, multi-company matching, short-ticker ambiguity guards, failed provider checkpoint handling, and idempotency.
- **`tests/test_articles_api.py`:** Tests pagination, read-path isolation from external provider, company news filtering, market news filtering, authentication enforcement on ingestion trigger, and status endpoint.
- **`tests/test_news_scheduler.py`:** Tests scheduler lifecycle, configured interval, background task execution, and non-overlapping execution lock.
- **Existing Tests:** All 33 pre-existing tests (`test_auth.py`, `test_companies.py`, `test_database.py`, `test_models.py`, `test_security.py`, `test_watchlists.py`) continue to pass.
