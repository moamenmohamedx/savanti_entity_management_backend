"""Application configuration."""

from functools import lru_cache
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Server
    environment: str = "development"
    debug: bool = True

    # Taskade
    taskade_api_token: SecretStr
    taskade_workspace_id: str
    entity_project_id: str
    taskade_base_url: str = "https://www.taskade.com/api/v1"

    # OpenRouter
    openrouter_api_key: SecretStr
    default_model: str = "openai/gpt-4o"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

