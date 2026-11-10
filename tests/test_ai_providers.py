"""Tests for AI provider interfaces: mock, adversarial, and hash embeddings."""
from __future__ import annotations

import asyncio
import uuid

import pytest

from app.ai.base import EmbeddingResponse, LLMResponse
from app.ai.mock import MockLLMProvider, HashEmbeddingProvider
from app.ai.adversarial import AdversarialMockProvider


def test_mock_llm_provider_deterministic():
    """Same input always produces same output (deterministic)."""
    async def _run():
        provider = MockLLMProvider()
        r1 = await provider.complete(system="check brand", user="test content ABC")
        r2 = await provider.complete(system="check brand", user="test content ABC")

        assert isinstance(r1, LLMResponse)
        assert r1.content == r2.content
        assert r1.provider == "mock"
        assert r1.is_mock is True
        assert r1.model == "mock-v1"
        assert len(r1.content) > 0

    asyncio.run(_run())


def test_mock_llm_never_fabricates_uuids():
    """Mock LLM must never include UUID-like strings that look like source IDs."""
    import re
    async def _run():
        provider = MockLLMProvider()
        for i in range(10):
            r = await provider.complete(system=f"sys_{i}", user=f"user_{i}")
            uuids_found = re.findall(
                r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
                r.content,
                re.IGNORECASE,
            )
            assert len(uuids_found) == 0, f"Mock LLM fabricated UUID: {uuids_found}"

    asyncio.run(_run())


def test_adversarial_provider_fabricates_citations():
    """Adversarial provider MUST fabricate fake UUIDs (for the hallucination trap demo)."""
    import re
    async def _run():
        provider = AdversarialMockProvider()
        r = await provider.complete(system="check brand", user="test content")

        assert isinstance(r, LLMResponse)
        assert r.provider == "adversarial"
        assert r.is_mock is True

        # Must contain fabricated UUIDs
        uuids = re.findall(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            r.content,
            re.IGNORECASE,
        )
        assert len(uuids) > 0, "Adversarial provider did not fabricate any UUIDs"

        # Must contain fabricated passage text
        assert any(kw in r.content for kw in ["Brand Standard", "Tone Guide", "Research Report", "VIOLATES", "CRITICAL", "compliance"]), \
            "Adversarial provider missing expected fabricated content markers"

    asyncio.run(_run())


def test_hash_embedding_deterministic():
    """Hash embeddings must be deterministic and produce correct dimensions."""
    async def _run():
        provider = HashEmbeddingProvider()
        texts = ["brand guideline text", "product specification"]

        r1 = await provider.embed(texts)
        r2 = await provider.embed(texts)

        assert isinstance(r1, EmbeddingResponse)
        assert r1.is_offline is True
        assert r1.provider == "hash-embedding"
        assert r1.dimensions == 384

        # Same input -> same output
        assert len(r1.embeddings) == 2
        assert r1.embeddings[0] == r2.embeddings[0]
        assert r1.embeddings[1] == r2.embeddings[1]

        # Different texts -> different embeddings
        assert r1.embeddings[0] != r1.embeddings[1]

        # Each embedding has correct dimensions
        for emb in r1.embeddings:
            assert len(emb) == 384

        # Vectors are approximately unit-normalized
        import math
        for emb in r1.embeddings:
            magnitude = math.sqrt(sum(v * v for v in emb))
            assert abs(magnitude - 1.0) < 0.01, f"Magnitude {magnitude} not unit-normalized"

    asyncio.run(_run())


def test_hash_embedding_empty_input():
    """Empty text list returns empty embeddings."""
    async def _run():
        provider = HashEmbeddingProvider()
        r = await provider.embed([])
        assert r.embeddings == []
        assert r.is_offline is True

    asyncio.run(_run())


def test_provider_factory():
    """Provider factory returns correct types based on config."""
    from app.ai.gemini import get_llm_provider, get_embedding_provider

    llm = get_llm_provider()
    emb = get_embedding_provider()

    # With default config (AI_PROVIDER=mock), should return mock providers
    assert llm.provider_name in ("mock", "adversarial", "gemini")
    assert emb.provider_name == "hash-embedding"


def test_gemini_missing_key_falls_back_and_reports_mode():
    from app.ai.gemini import get_ai_status, get_embedding_provider, get_llm_provider
    from app.core.config import settings

    async def _run():
        old_provider = settings.ai_provider
        old_key = settings.gemini_api_key
        try:
            object.__setattr__(settings, "ai_provider", "gemini")
            object.__setattr__(settings, "gemini_api_key", "")
            response = await get_llm_provider().complete("system", "content")
            embeddings = await get_embedding_provider().embed(["brand rule"])
            status = await get_ai_status()
            assert response.provider == "mock"
            assert response.fallback_used is True
            assert embeddings.provider == "hash-embedding"
            assert embeddings.fallback_used is True
            assert status == {
                "provider": "gemini",
                "mode": "fallback",
                "model": "mock-v1",
                "last_error": "GEMINI_API_KEY is not configured",
            }
        finally:
            object.__setattr__(settings, "ai_provider", old_provider)
            object.__setattr__(settings, "gemini_api_key", old_key)

    asyncio.run(_run())


def test_production_gemini_requires_key():
    from app.core.config import Settings

    with pytest.raises(ValueError, match="GEMINI_API_KEY is required"):
        Settings(
            environment="production",
            ai_provider="gemini",
            gemini_api_key="",
            jwt_secret_key="configured-test-secret",
        )

