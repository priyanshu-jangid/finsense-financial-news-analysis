# FinSense — Financial News Aggregation & Sentiment Analysis Platform

FinSense is a financial news aggregation and sentiment analysis platform designed to help users understand market-related news, analyze company sentiment, and track changes in financial sentiment over time.

The platform collects financial news from an external news provider, identifies relevant companies, removes duplicate articles, analyzes sentiment using FinBERT, and presents the resulting insights through a web-based dashboard.

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Local Setup](#local-setup)
- [Environment Variables](#environment-variables)
- [Running the Application](#running-the-application)
- [Database Migrations](#database-migrations)
- [Running Tests](#running-tests)
- [API Documentation](#api-documentation)
- [Security Notes](#security-notes)
- [Troubleshooting](#troubleshooting)
- [Future Enhancements](#future-enhancements)

## Overview

Financial markets react to company announcements, earnings reports, geopolitical developments, macroeconomic indicators, and other news events. However, tracking news across multiple sources and understanding its potential relationship with market sentiment can be challenging.

FinSense addresses this problem by combining financial news ingestion, company matching, sentiment analysis, and historical sentiment tracking in a single application.

The platform is intended for financial news research and analytical exploration. Its sentiment classifications are informational signals, not guaranteed predictions of stock-price movements or investment recommendations.

## Key Features

### 1. Financial News Aggregation

- Integrates with the Marketaux financial news API.
- Retrieves financial news through a centralized ingestion service.
- Supports controlled live ingestion through configuration flags.
- Normalizes incoming articles before storing them.

### 2. Company Matching and Deduplication

- Identifies companies associated with incoming news.
- Applies company-matching guardrails to reduce irrelevant associations.
- Deduplicates articles to reduce repeated news entries.
- Maintains canonical article records in the database.

### 3. AI-Powered Sentiment Analysis

- Uses the FinBERT model for financial sentiment classification.
- Supports positive, negative, and neutral sentiment labels.
- Validates model outputs before persisting analysis results.
- Stores sentiment analyses for subsequent retrieval and aggregation.

### 4. Sentiment Dashboard and Analytics

- Presents financial news and sentiment information through a web interface.
- Provides company-level sentiment information and historical views.
- Supports exploration of sentiment changes over time.

### 5. User Accounts and Watchlists

- Provides user registration and authentication functionality.
- Supports company watchlists.
- Enforces ownership checks for user-specific watchlists.
- Supports a personalized news feed based on watchlist interests.

### 6. Sentiment Shift Analysis

- Helps users explore changes in company sentiment over time.
- Combines persisted sentiment information with historical analysis.
- Provides a foundation for investigating why a company's news sentiment may have changed.

### 7. Controlled Background Ingestion

- Supports scheduled news ingestion.
- Uses configuration flags to control scheduler startup and live API access.
- Keeps live news ingestion disabled by default for safer local development.

## System Architecture

```text
                 ┌────────────────────────┐
                 │   Marketaux News API   │
                 └────────────┬───────────┘
                              │
                              ▼
                 ┌────────────────────────┐
                 │  News Ingestion Service│
                 └────────────┬───────────┘
                              │
                              ▼
                 ┌────────────────────────┐
                 │ Normalization, Company │
                 │ Matching & Deduplication│
                 └────────────┬───────────┘
                              │
                              ▼
                 ┌────────────────────────┐
                 │    PostgreSQL DB       │
                 │ Articles & Companies   │
                 └────────────┬───────────┘
                              │
                              ▼
                 ┌────────────────────────┐
                 │   FinBERT Sentiment    │
                 │       Analysis         │
                 └────────────┬───────────┘
                              │
                              ▼
                 ┌────────────────────────┐
                 │ Persisted Sentiment &  │
                 │ Historical Analytics   │
                 └────────────┬───────────┘
                              │
                              ▼
                 ┌────────────────────────┐
                 │ FastAPI Backend & REST │
                 │          APIs          │
                 └────────────┬───────────┘
                              │
                              ▼
                 ┌────────────────────────┐
                 │ React + TypeScript UI  │
                 └────────────────────────┘
```

The backend exposes API endpoints consumed by the frontend. PostgreSQL stores application data, while FinBERT performs financial sentiment classification.

## Technology Stack

| Component | Technologies |
|---|---|
| Frontend | React, TypeScript, Vite |
| Routing and API integration | React Router, Axios |
| Backend | Python, FastAPI, Uvicorn |
| Database | PostgreSQL |
| ORM and migrations | SQLAlchemy, Alembic |
| Validation | Pydantic |
| Sentiment analysis | Hugging Face Transformers, PyTorch, ProsusAI/finbert |
| Financial news provider | Marketaux API |
| Background scheduling | APScheduler |
| Testing | pytest |
| Version control | Git, GitHub |

## Project Structure

The following is a high-level overview of the repository. Exact filenames may evolve as development continues.

```text
FinSense/
├── backend/
│   └── app/
│       ├── core/          # Configuration and security
│       ├── services/      # Business logic and data services
│       ├── tasks/         # Background tasks and scheduling
│       └── main.py        # FastAPI application entry point
├── frontend/
│   ├── src/
│   │   ├── components/    # Reusable UI components
│   │   ├── pages/         # Application pages
│   │   └── api/           # Frontend API utilities
│   ├── .env.example       # Frontend configuration template
│   └── package.json
├── nlp/
│   └── pipeline/
│       └── sentiment.py   # Sentiment engine
├── shared/                # Shared application contracts
├── tests/                 # Automated tests
├── .env.example           # Backend/root configuration template
└── README.md
```

## Prerequisites

Install the following before running the project:

- Python 3.11 or another Python version supported by the project's dependencies.
- Node.js and npm.
- PostgreSQL.
- Git.
- A Marketaux account and API token for live news ingestion.

The application can be developed locally without enabling live news ingestion. Database connectivity is still required for normal database-backed functionality.

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/priyanshu-jangid/finsense-financial-news-analysis.git
cd finsense-financial-news-analysis
```

### 2. Create a Python virtual environment

On Linux or macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install backend dependencies

From the project root, install the dependencies using the repository's requirements file:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If the requirements file is located in a subdirectory in your checkout, use its actual path instead.

### 4. Configure PostgreSQL

Create a PostgreSQL database and a dedicated application user. For example, run the following as a PostgreSQL administrator:

```sql
CREATE USER finsense_user WITH PASSWORD 'replace_with_a_local_password';
CREATE DATABASE finsense OWNER finsense_user;
```

Use your own local password. Do not commit it to Git.

### 5. Configure backend environment variables

Create a local environment file from the supplied template:

```bash
cp .env.example .env
```

Edit `.env` and configure the database connection, JWT secret, and other settings required for your environment.

Keep `.env` local and never commit it.

### 6. Configure frontend environment variables

Create the frontend environment file:

```bash
cp frontend/.env.example frontend/.env
```

The local frontend configuration should point to the FastAPI backend running at `http://localhost:8000`.

### 7. Apply database migrations

Activate the Python virtual environment and run the migration command from the project root:

```bash
python -m alembic upgrade head
```

This applies the database schema migrations managed by Alembic.

If your project configures Alembic to run from a different working directory, follow that configuration.

## Environment Variables

The following variables are defined in the project's environment templates. Use placeholders in documentation and real values only in your local environment.

| Variable | Purpose | Example or default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+psycopg://finsense_user:your_password@localhost:5432/finsense` |
| `JWT_SECRET_KEY` | Secret used for JWT-related security | `your_jwt_secret_key_change_me` |
| `MARKETAUX_API_TOKEN` | Authentication for Marketaux API requests | `your_marketaux_token_here` |
| `INGESTION_OPERATOR_EMAILS` | Email addresses permitted to trigger manual ingestion | `your-operator@example.com` |
| `INGESTION_INTERVAL_HOURS` | Configured ingestion interval in hours | `3` |
| `ENABLE_SCHEDULER` | Enables background scheduler startup when other required conditions are met | `false` |
| `ENABLE_LIVE_NEWS` | Controls live news access | `false` |
| `FINBERT_MODEL_NAME` | Hugging Face model used for sentiment classification | `ProsusAI/finbert` |
| `CORS_ORIGINS` | Allowed frontend origins for cross-origin requests | `http://localhost:5173` |
| `VITE_API_BASE_URL` | Backend API base URL used by the frontend | `http://localhost:8000` |

### Important configuration notes

- `ENABLE_LIVE_NEWS=false` keeps live news access disabled.
- `ENABLE_SCHEDULER=false` prevents scheduler startup.
- In the current application configuration, the scheduler starts only when both `ENABLE_SCHEDULER` and `ENABLE_LIVE_NEWS` are enabled.
- Live ingestion requires a valid Marketaux API token.
- Generate a strong, unique JWT secret for your local environment. Never use the example value in production.
- `INGESTION_OPERATOR_EMAILS` should contain the email addresses of authorized ingestion operators.
- If you change the backend port or frontend origin, update the corresponding configuration values.

## Running the Application

Run the backend and frontend in separate terminals.

### Terminal 1 — Start the backend

From the project root, with the Python virtual environment activated:

```bash
uvicorn backend.app.main:app --reload
```

The backend should be available at:

- API base URL: http://localhost:8000
- Interactive API documentation: http://localhost:8000/docs
- Alternative API documentation: http://localhost:8000/redoc

### Terminal 2 — Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open the frontend at:

http://localhost:5173

The frontend communicates with the backend through `VITE_API_BASE_URL`.

### First-time sentiment model initialization

FinBERT may download its model files from Hugging Face when first initialized. This can take time and require an internet connection. Subsequent runs may reuse the locally cached model files.

### Enabling live news ingestion

Only enable live ingestion after verifying your API token, database configuration, and operator authorization.

In your local `.env`, configure the appropriate values:

```dotenv
ENABLE_LIVE_NEWS=true
ENABLE_SCHEDULER=false
```

This allows live news functionality without automatically starting the scheduler, provided the relevant ingestion endpoints are used.

To enable scheduled ingestion as well, set:

```dotenv
ENABLE_LIVE_NEWS=true
ENABLE_SCHEDULER=true
```

Restart the backend after changing environment variables. Be mindful of API usage limits.

## Database Migrations

Apply pending migrations:

```bash
python -m alembic upgrade head
```

Check the current migration revision:

```bash
python -m alembic current
```

Inspect migration history:

```bash
python -m alembic history
```

These commands help verify that the local database schema is aligned with the application's migration history.

## Running Tests

From the project root, activate the virtual environment and run:

```bash
python -m pytest -q
```

For additional diagnostic output:

```bash
python -m pytest -v
```

Tests that require PostgreSQL or external services may need their corresponding local configuration. Keep live API access disabled unless a test explicitly requires it.

## API Documentation

Once the backend is running, FastAPI provides interactive API documentation at:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

Use these pages to explore available endpoints, inspect request and response schemas, and test supported API operations.

## Security Notes

Security is an important part of the development and deployment process.

- Never commit `.env` files or actual API tokens.
- Keep `.env.example` limited to dummy values and non-sensitive defaults.
- Rotate credentials immediately if they are accidentally exposed.
- Removing a secret from the latest file does not remove it from previous Git commits.
- Do not expose JWT secrets, database passwords, or provider tokens in logs, screenshots, issue reports, or public documentation.
- Restrict manual ingestion endpoints to authorized operators.
- Configure CORS origins explicitly for the environment in which the application runs.
- Keep live news ingestion and scheduled jobs disabled until they are intentionally configured.
- Review secret handling before deploying the application to a public server.

## Troubleshooting

### Backend cannot connect to PostgreSQL

- Confirm that PostgreSQL is running.
- Check the database name, username, password, host, and port in `DATABASE_URL`.
- Verify that the database and application user exist.
- Confirm that database migrations have been applied.

### Frontend cannot reach the backend

- Ensure the backend is running at `http://localhost:8000`.
- Check `VITE_API_BASE_URL` in `frontend/.env`.
- Verify that `CORS_ORIGINS` includes the frontend origin.
- Restart the Vite development server after changing environment variables.

### Live news returns no articles

- Check `ENABLE_LIVE_NEWS`.
- Verify that `MARKETAUX_API_TOKEN` contains a valid, active token.
- Check the backend logs for provider errors or API rate limits.
- Confirm that the configured ingestion operator is authorized where required.

### Sentiment analysis takes a long time on first run

- Allow time for the FinBERT model to initialize and download if necessary.
- Confirm that the machine has sufficient memory and an internet connection for initial model retrieval.
- Check the backend logs for model-loading or dependency errors.

### Database schema errors

Run:

```bash
python -m alembic current
python -m alembic history
```

If the database is behind the migration head, apply the pending migrations after confirming that the configured database is the intended local database.

## Future Enhancements

Potential areas for further development include:

- Event classification for financial news.
- News relevance and impact ranking.
- More detailed explanations of sentiment shifts.
- Personalized alerts for watched companies.
- Expanded historical analytics and visualization.
- Production deployment, monitoring, and operational hardening.

These are development directions rather than a guarantee that every feature is currently implemented.

## Disclaimer

FinSense is a software project for financial news analysis and research. Its sentiment outputs may be incomplete or inaccurate and should not be treated as financial advice, investment recommendations, or reliable predictions of market movements.

## License

Add a license file and specify the license here if you intend to distribute the project under an open-source license.
