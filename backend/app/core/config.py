from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str

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
    ENABLE_SCHEDULER: bool = True
    # Canonical kill switch – defaults to False to protect quota
    ENABLE_LIVE_NEWS: bool = False
    FINBERT_MODEL_NAME: str = "ProsusAI/finbert"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
