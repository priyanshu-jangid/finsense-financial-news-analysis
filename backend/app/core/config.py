
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str

    # Gemini-powered ImpactLens explanations
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.8-flash"
    GEMINI_REQUEST_TIMEOUT_SECONDS: float = 20.0

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # News Provider & Ingestion Settings
    MARKETAUX_API_TOKEN: str = ""
    MARKETAUX_BASE_URL: str = "https://api.marketaux.com/v1"
    NEWS_REQUEST_TIMEOUT_SECONDS: float = 10.0
    NEWS_DEFAULT_LOOKBACK_HOURS: int = 24
    NEWS_CHECKPOINT_OVERLAP_MINUTES: int = 30
    INGESTION_INTERVAL_HOURS: int = 3

    # Scheduler controls
    ENABLE_SCHEDULER: bool = True
    # Canonical kill switch: defaults to False to protect API quota
    ENABLE_LIVE_NEWS: bool = False

    # NLP settings
    FINBERT_MODEL_NAME: str = "ProsusAI/finbert"

    # CORS settings
    CORS_ORIGINS: str = (
        "http://localhost:5173,"
        "http://127.0.0.1:5173,"
        "http://localhost:5174,"
        "http://127.0.0.1:5174"
    )
    # Comma-separated list of operator emails allowed to trigger manual ingestion
    INGESTION_OPERATOR_EMAILS: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
