"""
Application configuration.

Loads settings from environment variables with safe defaults.
All configurable values live here — nothing is hardcoded elsewhere.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_env: str = "development"
    database_url: str = "sqlite:///./tickets.db"
    log_level: str = "INFO"

    # Classification
    confidence_default: float = 0.82
    confidence_threshold_auto_route: float = 0.70

    # Routing fallback
    default_channel: str = "#support-general"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
