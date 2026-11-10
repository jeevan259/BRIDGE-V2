"""Application configuration and startup validation."""
from __future__ import annotations

import logging
import os
import sys
from functools import lru_cache
from typing import List

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("bridge.config")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql+asyncpg://bridge:bridge@localhost:5432/bridge"
    database_sync_url: str = "postgresql://bridge:bridge@localhost:5432/bridge"

    # Auth
    jwt_secret_key: str = "change-me-in-production-use-32-random-bytes"
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "bridge-auth"
    jwt_audience: str = "bridge-clients"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # AI Provider
    ai_provider: str = "mock"  # gemini | mock | adversarial
    gemini_api_key: str = ""

    # App
    environment: str = "development"
    cors_origins: str = "http://localhost:3000"
    upload_dir: str = "/tmp/bridge_uploads"

    # Derived status
    ai_status: str = "AI: offline mode"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str) -> str:
        return v

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_development(self) -> bool:
        return self.environment.lower() in ("development", "dev", "test")

    @model_validator(mode="after")
    def validate_and_compute_statuses(self) -> Settings:
        """Validate critical configuration with actionable error messages."""
        # 1. Database URL check
        if not self.database_url or "://" not in self.database_url:
            raise ValueError(
                "DATABASE_URL is not set or invalid. "
                "Expected format: postgresql+asyncpg://user:pass@host:5432/dbname"
            )

        # 2. Production secret key validation
        if not self.is_development and self.jwt_secret_key == "change-me-in-production-use-32-random-bytes":
            raise ValueError(
                "CRITICAL: Default JWT_SECRET_KEY cannot be used in production. "
                "Please generate a secure 32+ byte key via: python -c 'import secrets; print(secrets.token_hex(32))'"
            )

        # 3. Gemini API Key check (P0 rule: missing key MUST NOT crash, only produce visible 'AI: offline mode')
        if self.ai_provider == "gemini" and not self.gemini_api_key.strip():
            object.__setattr__(self, "ai_provider", "mock")
            object.__setattr__(self, "ai_status", "AI: offline mode (Gemini key not configured)")
            logger.warning(
                "AI: offline mode — GEMINI_API_KEY is not set. "
                "Operating with deterministic mock engine. System remains fully operational."
            )
        elif self.ai_provider == "gemini":
            object.__setattr__(self, "ai_status", "AI: online (Gemini 1.5)")
        else:
            object.__setattr__(self, "ai_status", "AI: offline mode (Deterministic Mock)")

        return self


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()
    except Exception as exc:
        sys.stderr.write(f"\n[FATAL STARTUP CONFIGURATION ERROR]\n{exc}\n\n")
        raise


settings = get_settings()

