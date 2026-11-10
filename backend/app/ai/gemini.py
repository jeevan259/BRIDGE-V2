"""Gemini API clients with per-request mock fallback and status reporting."""
from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from app.ai.base import EmbeddingProvider, EmbeddingResponse, LLMProvider, LLMResponse
from app.ai.mock import HashEmbeddingProvider, MockLLMProvider
from app.config import settings

_API_ROOT = "https://generativelanguage.googleapis.com/v1beta/models"
_last_error: str | None = None
_status_cache: dict[str, Any] | None = None
_status_cache_until = 0.0
_status_lock = asyncio.Lock()


def _error_summary(exc: Exception) -> str:
    detail = str(exc)
    if detail in {"GEMINI_API_KEY is not configured", "Gemini response contained no text"}:
        return detail
    if detail.startswith("Gemini request returned HTTP ") or detail.startswith("Gemini embedding returned HTTP "):
        return detail
    if isinstance(exc, httpx.TimeoutException):
        return "Gemini request timed out"
    if isinstance(exc, httpx.HTTPError):
        return "Gemini network request failed"
    return f"{type(exc).__name__}: Gemini request failed"


class GeminiLLMProvider(LLMProvider):
    @property
    def provider_name(self) -> str:
        return "gemini"

    async def complete(self, system: str, user: str, **kwargs: object) -> LLMResponse:
        if not settings.gemini_api_key.strip():
            raise RuntimeError("GEMINI_API_KEY is not configured")
        prompt = f"{system}\n\n---\n\n{user}"
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                f"{_API_ROOT}/{settings.gemini_model}:generateContent",
                headers={"x-goog-api-key": settings.gemini_api_key},
                json={"contents": [{"parts": [{"text": prompt}]}]},
            )
        if response.is_error:
            raise RuntimeError(f"Gemini request returned HTTP {response.status_code}")
        body = response.json()
        content = "".join(
            part.get("text", "")
            for candidate in body.get("candidates", [])[:1]
            for part in candidate.get("content", {}).get("parts", [])
        )
        if not content:
            raise RuntimeError("Gemini response contained no text")
        return LLMResponse(content=content, provider="gemini", model=settings.gemini_model)


class FallbackLLMProvider(LLMProvider):
    def __init__(self) -> None:
        self.live = GeminiLLMProvider()
        self.mock = MockLLMProvider()

    @property
    def provider_name(self) -> str:
        return "gemini"

    async def complete(self, system: str, user: str, **kwargs: object) -> LLMResponse:
        global _last_error
        try:
            result = await self.live.complete(system, user, **kwargs)
            _last_error = None
            return result
        except Exception as exc:
            _last_error = (
                "GEMINI_API_KEY is not configured"
                if not settings.gemini_api_key.strip()
                else _error_summary(exc)
            )
            fallback = await self.mock.complete(system, user, **kwargs)
            fallback.fallback_used = True
            fallback.fallback_error = _last_error
            return fallback


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Gemini Embedding 2 vectors, fixed at 768 dimensions for pgvector."""

    def __init__(self) -> None:
        self.mock = HashEmbeddingProvider()
        self._fallback = not bool(settings.gemini_api_key.strip())

    @property
    def provider_name(self) -> str:
        return "gemini"

    async def embed(self, texts: list[str]) -> EmbeddingResponse:
        if self._fallback:
            result = await self.mock.embed(texts)
            result.fallback_used = settings.ai_provider.lower() == "gemini"
            return result
        try:
            async with httpx.AsyncClient(timeout=45) as client:
                responses = await asyncio.gather(*[
                    client.post(
                        f"{_API_ROOT}/{settings.gemini_embedding_model}:embedContent",
                        headers={"x-goog-api-key": settings.gemini_api_key},
                        json={
                            "content": {"parts": [{"text": text}]},
                            "output_dimensionality": settings.gemini_embedding_dimensions,
                        },
                    )
                    for text in texts
                ])
            vectors: list[list[float]] = []
            for response in responses:
                if response.is_error:
                    raise RuntimeError(f"Gemini embedding returned HTTP {response.status_code}")
                vector = response.json().get("embedding", {}).get("values", [])
                if len(vector) != settings.gemini_embedding_dimensions:
                    raise ValueError("Gemini embedding dimension did not match configuration")
                vectors.append(vector)
            return EmbeddingResponse(
                embeddings=vectors,
                provider="gemini",
                dimensions=settings.gemini_embedding_dimensions,
                model=settings.gemini_embedding_model,
            )
        except Exception as exc:
            global _last_error
            _last_error = _error_summary(exc)
            self._fallback = True
            result = await self.mock.embed(texts)
            result.fallback_used = True
            return result


def get_llm_provider() -> LLMProvider:
    provider = settings.ai_provider.lower()
    if provider == "gemini":
        return FallbackLLMProvider()
    if provider == "adversarial":
        from app.ai.adversarial import AdversarialMockProvider
        return AdversarialMockProvider()
    return MockLLMProvider()


def get_embedding_provider() -> EmbeddingProvider:
    if settings.ai_provider.lower() == "gemini":
        return GeminiEmbeddingProvider()
    return HashEmbeddingProvider()


async def get_ai_status() -> dict[str, str | None]:
    """Return cached live AI status, probing Gemini at most once per minute."""
    global _status_cache, _status_cache_until, _last_error
    provider = settings.ai_provider.lower()
    if provider != "gemini":
        model = "adversarial-mock-v1" if provider == "adversarial" else "mock-v1"
        return {"provider": provider, "mode": "mock", "model": model, "last_error": None}
    if not settings.gemini_api_key.strip():
        return {
            "provider": "gemini",
            "mode": "fallback",
            "model": "mock-v1",
            "last_error": "GEMINI_API_KEY is not configured",
        }
    if _last_error and time.monotonic() < _status_cache_until:
        return {"provider": "gemini", "mode": "fallback", "model": "mock-v1", "last_error": _last_error}
    if _status_cache and time.monotonic() < _status_cache_until:
        return dict(_status_cache)
    async with _status_lock:
        if _status_cache and time.monotonic() < _status_cache_until:
            return dict(_status_cache)
        try:
            await GeminiLLMProvider().complete("Status probe.", "Reply with OK.")
            _last_error = None
            _status_cache = {
                "provider": "gemini", "mode": "live", "model": settings.gemini_model, "last_error": None
            }
        except Exception as exc:
            _last_error = _error_summary(exc)
            _status_cache = {
                "provider": "gemini", "mode": "fallback", "model": "mock-v1", "last_error": _last_error
            }
        _status_cache_until = time.monotonic() + 60
        return dict(_status_cache)
