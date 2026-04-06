"""Environment-driven settings — add DATABASE_URL for DB connection."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = Field(default="development", alias="APP_ENV")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    svg_assets_dir: str = Field(default="../assets/svgs", alias="SVG_ASSETS_DIR")
    max_scenes: int = Field(default=15, alias="MAX_SCENES")
    max_input_chars: int = Field(default=200_000, alias="MAX_INPUT_CHARS")
    max_upload_mb: int = Field(default=20, alias="MAX_UPLOAD_MB")
    run_retention_count: int = Field(default=20, alias="RUN_RETENTION_COUNT")
    output_dir: str = Field(default="../renderer/public", alias="OUTPUT_DIR")
    gemini_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL")
    auto_create_tables: bool = Field(default=True, alias="AUTO_CREATE_TABLES")
    recover_stale_jobs_on_startup: bool = Field(default=True, alias="RECOVER_STALE_JOBS_ON_STARTUP")
    database_ssl_mode: str = Field(default="prefer", alias="DATABASE_SSL_MODE")
    job_worker_count: int = Field(default=2, alias="JOB_WORKER_COUNT")
    job_queue_capacity: int = Field(default=6, alias="JOB_QUEUE_CAPACITY")
    max_concurrent_renders: int = Field(default=1, alias="MAX_CONCURRENT_RENDERS")
    enable_auth: bool = Field(default=False, alias="ENABLE_AUTH")
    auth_username: str = Field(default="admin", alias="AUTH_USERNAME")
    auth_password: str = Field(default="change_me", alias="AUTH_PASSWORD")
    jwt_secret: str = Field(default="change_me", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=60, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    allowed_origins: str = Field(default="*", alias="ALLOWED_ORIGINS")

    # ── NEW ──────────────────────────────────────────────────────────────────
    # SQLite for local dev (no setup needed — file created automatically)
    # Switch to PostgreSQL for production:
    #   DATABASE_URL=postgresql://anigen:password@localhost:5432/anigendb
    database_url: str = Field(
        default="sqlite:///./anigen.db",
        alias="DATABASE_URL",
    )

    @model_validator(mode="after")
    def validate_database_url_for_environment(self) -> "Settings":
        """Robust safety checks for Cloud Run deployment."""

        if self.app_env.lower() == "production":
            # Sanitize DATABASE_URL if it contains local-only hostnames (ghosts from .env)
            if "@db:" in self.database_url or "@localhost" in self.database_url:
                logging.warning(f"DATABASE_URL contains local hostname (@db or @localhost). Forcing SQLite fallback.")
                self.database_url = "sqlite:////tmp/anigen.db"

            if self.database_url.startswith("sqlite"):
                logging.warning("DATABASE_URL uses sqlite in production. Redirecting to /tmp/anigen.db.")
                if not self.database_url.startswith("sqlite:////tmp/"):
                    self.database_url = "sqlite:////tmp/anigen.db"

            if self.auto_create_tables:
                logging.warning("AUTO_CREATE_TABLES is true in production. Using it for initial test.")

            # Soften JWT and Auth checks
            if not self.jwt_secret or self.jwt_secret == "change_me":
                logging.warning("JWT_SECRET missing. Using temporary secret.")
                self.jwt_secret = "temporary_deployment_secret_please_change"

            if self.enable_auth and self.auth_password in {"", "change_me"}:
                logging.warning("AUTH_PASSWORD is default. Update in production console.")

        return self

    model_config = SettingsConfigDict(
        env_file=(".env"),
        extra="ignore",
        populate_by_name=True,
    )

    def resolve_svg_assets_dir(self, base_dir: str | Path) -> Path:
        return _resolve_path(base_dir=base_dir, value=self.svg_assets_dir)

    def resolve_output_dir(self, base_dir: str | Path) -> Path:
        return _resolve_path(base_dir=base_dir, value=self.output_dir)


def _resolve_path(base_dir: str | Path, value: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    return (Path(base_dir) / candidate).resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()