from fastapi import FastAPI

app = FastAPI(
    title="FinSense API",
    description="Financial News Aggregation and Sentiment Analysis Platform",
    version="0.1.0",
)


@app.get("/")
def root():
    return {
        "message": "Welcome to FinSense API",
        "status": "running",
        "version": "0.1.0",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }