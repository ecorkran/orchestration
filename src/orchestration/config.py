"""Application configuration via Pydantic Settings."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file.

    All variables are prefixed with ``ORCH_`` (e.g. ``ORCH_LOG_LEVEL``).
    """

    model_config = SettingsConfigDict(
        env_prefix="ORCH_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Provider defaults
    default_provider: str = "anthropic"
    default_model: str = "claude-sonnet-4-20250514"

    # Anthropic credentials
    anthropic_api_key: str | None = None
    anthropic_credential_path: str | None = None

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # "json" or "text"

    # Server (used by later slices)
    host: str = "127.0.0.1"
    port: int = 8000
