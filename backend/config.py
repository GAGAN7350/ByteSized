"""
Centralised configuration for the ByteSized backend.

All settings are read from environment variables.  Copy `.env.example` to
`.env` and fill in values before running locally.  In production, inject
variables via your container runtime / secrets manager — never commit `.env`.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Runtime ──────────────────────────────────────────────────────────────
    environment: str = Field("development", description="development | staging | production")
    log_level: str = Field("info", description="Python log level (debug/info/warning/error)")

    # ── CORS ─────────────────────────────────────────────────────────────────
    # Comma-separated origins, e.g. "http://localhost:3000,https://app.example.com"
    # Set to "*" only in development; production should list explicit origins.
    cors_origins: str = Field(
        "http://localhost:3000,http://localhost:8000,vscode-webview://*",
        description="Allowed CORS origins (comma-separated).",
    )

    # ── API Keys ──────────────────────────────────────────────────────────────
    gemini_api_key: str = Field("", description="Google Gemini API key (optional).")

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = Field(
        "redis://localhost:6379/0",
        description="Redis connection URL for WebSocket fan-out.",
    )
    redis_password: str = Field("", description="Redis AUTH password (if set).")

    # ── Rate limiting ─────────────────────────────────────────────────────────
    rate_limit_per_minute: int = Field(
        60,
        ge=1,
        description="Max requests per IP per minute for analysis endpoints.",
    )

    # ── Derived helpers ───────────────────────────────────────────────────────
    @property
    def cors_origins_list(self) -> List[str]:
        """Return CORS origins as a list, stripping whitespace."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @field_validator("log_level")
    @classmethod
    def _normalise_log_level(cls, v: str) -> str:
        allowed = {"debug", "info", "warning", "error", "critical"}
        v = v.lower()
        if v not in allowed:
            raise ValueError(f"log_level must be one of {allowed}, got {v!r}")
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings singleton (one parse per process)."""
    return Settings()
