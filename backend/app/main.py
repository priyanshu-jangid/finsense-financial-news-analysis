from fastapi import FastAPI

from backend.app.routers.auth import router as auth_router
from backend.app.routers.companies import router as companies_router
from backend.app.routers.watchlists import router as watchlists_router


app = FastAPI(
    title="FinSense API",
    description="Financial News Aggregation and Sentiment Analysis Platform",
    version="0.1.0",
)

app.include_router(auth_router)
app.include_router(companies_router)
app.include_router(watchlists_router)


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
