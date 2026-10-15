from contextlib import asynccontextmanager
from fastapi import FastAPI

from backend.app.core.config import settings
from backend.app.routers.articles import router as articles_router
from backend.app.routers.auth import router as auth_router
from backend.app.routers.companies import router as companies_router
from backend.app.routers.watchlists import router as watchlists_router
from backend.app.tasks.news_scheduler import shutdown_news_scheduler, start_news_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.ENABLE_SCHEDULER and settings.ENABLE_LIVE_NEWS:
        start_news_scheduler()
    yield
    shutdown_news_scheduler()


app = FastAPI(
    title="FinSense API",
    description="Financial News Aggregation and Sentiment Analysis Platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(auth_router)
app.include_router(companies_router)
app.include_router(watchlists_router)
app.include_router(articles_router)


@app.get("/")
def root():
    return {
        "message": "Welcome to FinSense API",
        "status": "running",
        "version": "0.1.0",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
