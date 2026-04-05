"""Environment-driven settings — add DATABASE_URL for DB connection."""

from __future__ import annotations

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
        """Guard against shipping a production deployment on SQLite by mistake."""

        if self.app_env.lower() == "production" and self.database_url.startswith("sqlite"):
            raise ValueError("DATABASE_URL must not use sqlite when APP_ENV=production")
        if self.app_env.lower() == "production" and self.auto_create_tables:
            raise ValueError("AUTO_CREATE_TABLES must be false when APP_ENV=production")

        if self.job_worker_count < 1:
            raise ValueError("JOB_WORKER_COUNT must be >= 1")
        if self.job_queue_capacity < 1:
            raise ValueError("JOB_QUEUE_CAPACITY must be >= 1")
        if self.max_concurrent_renders < 1:
            raise ValueError("MAX_CONCURRENT_RENDERS must be >= 1")
        if self.max_upload_mb < 1:
            raise ValueError("MAX_UPLOAD_MB must be >= 1")
        if self.max_input_chars < 1000:
            raise ValueError("MAX_INPUT_CHARS must be >= 1000")

        if self.app_env.lower() == "production":
            if not self.jwt_secret or self.jwt_secret == "change_me":
                raise ValueError("JWT_SECRET must be set to a strong value in production")
            if self.enable_auth and (
                self.auth_password in {"", "change_me"} or self.jwt_secret == "change_me"
            ):
                raise ValueError("AUTH_PASSWORD and JWT_SECRET must be changed when ENABLE_AUTH=true")
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