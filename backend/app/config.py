from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://neomint:neomint@localhost:5432/neomint"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60

    starting_cash: float = 100_000.0
    quote_cache_seconds: int = 15

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5-5"

    cors_origins: str = "http://localhost:3000"
    enable_scheduler: bool = True
    nightly_hour_utc: int = 18  # 23:30 IST
    nightly_minute_utc: int = 0

    admin_email: str = "admin@neomint.dev"
    admin_password: str = "ChangeMe123!"


@lru_cache
def get_settings() -> Settings:
    return Settings()
