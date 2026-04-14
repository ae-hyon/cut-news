"""Configuration settings for the crawler service."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    PROJECT_NAME: str = "Crawler Service"
    VERSION: str = "0.1.0"

    # Crawler-specific settings
    REQUEST_TIMEOUT: int = 30
    MAX_RETRIES: int = 3
    USER_AGENT: str = "CutNews-Crawler/0.1.0"


settings = Settings()
