from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# The canonical .env lives at the repo root (see README.md / .env.example), one
# level above backend/. Resolve it from this file's location rather than the
# process's CWD, so `.env` is found the same way whether the app is started
# from the repo root, from backend/, or by a tool (alembic, a script) that
# changes directory first. Real environment variables (e.g. those injected by
# docker-compose) still take precedence over this file's contents.
_REPO_ROOT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    """Central application configuration, loaded from environment variables / .env."""

    model_config = SettingsConfigDict(
        env_file=(str(_REPO_ROOT_ENV_FILE), ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    # App
    app_name: str = "project-monitoring-ai"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    debug: bool = True

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/project_monitoring"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Vector DB (introduced in later phases, kept here so config loads end-to-end)
    vector_db_url: str = "http://localhost:6333"

    # Object storage (MinIO/S3-compatible, introduced in later phases)
    object_storage_endpoint: str = "http://localhost:9000"
    object_storage_access_key: str = "minioadmin"
    object_storage_secret_key: str = "minioadmin"
    object_storage_bucket: str = "project-monitoring"

    # Security
    secret_key: str = "change-me-in-env"
    access_token_expire_minutes: int = 60

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Logging
    log_level: str = "INFO"
    log_json: bool = True

    # LLM (Gemini) - Phase 6 Project History Agent narrative synthesis only.
    # Never used for facts, trends, or predictions - those stay deterministic.
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.6-flash"

    # Web search (Tavily) - Phase 8 Web Intelligence Agent. Leave blank to
    # disable - the agent then reports web evidence as unavailable rather
    # than fabricating results (PRD section 65, graceful degradation).
    tavily_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
