"""Gemini AI provider — real API calls, only used when GEMINI_API_KEY is set."""
from __future__ import annotations

import logging

from app.ai.base import EmbeddingProvider, EmbeddingResponse, LLMProvider, LLMResponse
from app.ai.mock import HashEmbeddingProvider
from app.config import settings

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai  # type: ignore[import-untyped]
    _GEMINI_AVAILABLE = True
except ImportError:
    _GEMINI_AVAILABLE = False
    logger.warning("google-generativeai not installed; GeminiProvider unavailable")


class GeminiLLMProvider(LLMProvider):
    """
    Gemini LLM provider using the Google Generative AI SDK.
    Only functional when GEMINI_API_KEY is set and AI_PROVIDER=gemini.
    """

    def __init__(self) -> None:
        if not _GEMINI_AVAILABLE:
            raise RuntimeError("google-generativeai package not installed")
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY not configured")
        genai.configure(api_key=settings.gemini_api_key)
        self._client = genai.GenerativeModel("gemini-1.5-flash")

    @property
    def provider_name(self) -> str:
        return "gemini"

    async def complete(self, system: str, user: str, **kwargs: object) -> LLMResponse:
        prompt = f"{system}\n\n---\n\n{user}"
        try:
            response = await self._client.generate_content_async(prompt)
            content = response.text
        except Exception as exc:
            logger.exception("Gemini API error: %s", exc)
            raise
        return LLMResponse(
            content=content,
            provider=self.provider_name,
            model="gemini-1.5-flash",
            is_mock=False,
        )


# Gemini uses HashEmbeddingProvider for offline embeddings in this stage.
# A real Gemini embedding endpoint can be wired in later.
GeminiEmbeddingProvider = HashEmbeddingProvider


def get_llm_provider() -> LLMProvider:
    """Factory: returns the configured LLM provider."""
    from app.ai.mock import MockLLMProvider
    from app.ai.adversarial import AdversarialMockProvider

    provider = settings.ai_provider.lower()
    if provider == "gemini" and settings.gemini_api_key and _GEMINI_AVAILABLE:
        return GeminiLLMProvider()
    elif provider == "adversarial":
        return AdversarialMockProvider()
    else:
        if provider == "gemini":
            logger.warning(
                "AI_PROVIDER=gemini but GEMINI_API_KEY is not set; falling back to mock"
            )
        return MockLLMProvider()


def get_embedding_provider() -> EmbeddingProvider:
    """Factory: returns the configured embedding provider."""
    return HashEmbeddingProvider()
