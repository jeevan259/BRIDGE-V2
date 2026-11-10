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
        env_file=("../.env", ".env"),
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

    # Cookie settings (fully environment-driven)
    cookie_secure: bool | None = None
    cookie_samesite: str = "lax"  # lax | strict | none
    cookie_domain: str | None = None

    # AI Provider
    ai_provider: str = "mock"  # gemini | mock | adversarial
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"
    gemini_embedding_model: str = "text-embedding-004"
    gemini_embedding_dimensions: int = 768

    # App
    environment: str = "development"
    cors_origins: str = "http://localhost:3000"
    upload_dir: str = "/tmp/bridge_uploads"
    demo_mode: bool = False
    demo_password: str = "password123"

    # Derived status
    ai_status: str = "AI: offline mode"

    @property
    def is_cookie_secure(self) -> bool:
        if self.cookie_secure is not None:
            return self.cookie_secure
        if self.cookie_samesite.lower() == "none":
            return True
        return not self.is_development

    @property
    def resolved_cookie_samesite(self) -> str:
        val = self.cookie_samesite.lower()
        if val in ("lax", "strict", "none"):
            return val
        return "lax"

    @field_validator("database_url", mode="before")
    @classmethod
    def clean_asyncpg_database_url(cls, v: str) -> str:
        """Sanitize Postgres URL for SQLAlchemy asyncpg driver.
        asyncpg does not accept sslmode or channel_binding as query parameters;
        it requires ssl=require instead of sslmode=require.
        Also ensures postgresql+asyncpg:// scheme is present.
        """
        if not v:
            return v
        if not v.startswith("postgresql+asyncpg://") and v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        import urllib.parse
        parsed = urllib.parse.urlparse(v)
        if parsed.query:
            q_dict = urllib.parse.parse_qs(parsed.query)
            q_dict.pop("channel_binding", None)
            ssl_val = q_dict.pop("sslmode", None)
            if ssl_val and "ssl" not in q_dict:
                q_dict["ssl"] = ssl_val
            new_query = urllib.parse.urlencode(q_dict, doseq=True)
            v = urllib.parse.urlunparse(parsed._replace(query=new_query))
        return v

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

        # 3. Gemini key is mandatory in production; development requests may fall back per call.
        if self.ai_provider == "gemini" and not self.gemini_api_key.strip():
            if not self.is_development:
                raise ValueError("GEMINI_API_KEY is required when AI_PROVIDER=gemini in production")
            object.__setattr__(self, "ai_status", "AI: fallback (Gemini key not configured)")
        elif self.ai_provider == "gemini":
            object.__setattr__(self, "ai_status", f"AI: Gemini live ({self.gemini_model})")
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

