"""
Configuration module for the Fleek Media Service.
Handles environment variables and application settings.
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Database Configuration
    database_url: str = Field(
        default="postgresql+asyncpg://fleek:fleek123@localhost:5432/fleek_media",
        description="Async database URL for SQLAlchemy",
    )
    database_url_sync: str = Field(
        default="postgresql://fleek:fleek123@localhost:5432/fleek_media",
        description="Sync database URL for Alembic migrations",
    )

    # Redis Configuration
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis URL for caching and session storage",
    )

    # Celery Configuration
    celery_broker_url: str = Field(
        default="redis://localhost:6379/0", description="Celery broker URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/0", description="Celery result backend URL"
    )

    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host address")
    api_port: int = Field(default=8000, description="API port number")
    api_debug: bool = Field(default=False, description="Enable debug mode")

    # File Storage Configuration
    storage_path: str = Field(
        default="./storage/media", description="Local file storage path"
    )
    storage_base_url: str = Field(
        default="http://localhost:8000/media",
        description="Base URL for accessing stored files",
    )

    # Replicate API Mock Configuration
    replicate_api_token: str = Field(
        default="mock_token_for_demo", description="Replicate API token (mock for demo)"
    )
    replicate_mock_delay_min: int = Field(
        default=2, description="Minimum delay for mock API responses (seconds)"
    )
    replicate_mock_delay_max: int = Field(
        default=10, description="Maximum delay for mock API responses (seconds)"
    )
    replicate_mock_failure_rate: float = Field(
        default=0.1, description="Mock API failure rate (0.0 to 1.0)"
    )

    # Job Configuration
    max_retry_attempts: int = Field(
        default=3, description="Maximum number of retry attempts for failed jobs"
    )
    retry_backoff_factor: int = Field(
        default=2, description="Exponential backoff factor for retries"
    )

    # Logging Configuration
    log_level: str = Field(default="INFO", description="Logging level")

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
