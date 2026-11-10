"""Mock AI providers — deterministic, never fabricates sources."""
from __future__ import annotations

import hashlib
import struct

from app.ai.base import EmbeddingProvider, EmbeddingResponse, LLMProvider, LLMResponse

# Deterministic response templates keyed by content hash bucket
_RESPONSE_TEMPLATES = [
    (
        "The content aligns with brand guidelines. No violations detected. "
        "All claims appear to be properly substantiated based on available knowledge items."
    ),
    (
        "Minor tone inconsistency detected: the language used is slightly informal for the brand voice. "
        "Recommend reviewing phrasing for alignment with established guidelines."
    ),
    (
        "The content makes factual claims that require verification against brand knowledge sources. "
        "Specific assertions should be cross-referenced with approved knowledge items."
    ),
    (
        "Brand guideline adherence: PASS. The content correctly uses approved terminology "
        "and maintains the expected professional tone throughout."
    ),
    (
        "One potential guideline breach identified: the usage of competitor product names "
        "without appropriate context. Please review against the competitor mention policy."
    ),
]


def _deterministic_choice(text: str, n: int) -> int:
    """Hash text to a stable integer in range [0, n)."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    value = struct.unpack(">I", digest[:4])[0]
    return value % n


class MockLLMProvider(LLMProvider):
    """
    Deterministic mock LLM provider.
    Returns stable responses based on input hash.
    NEVER fabricates source IDs, item IDs, or citations.
    """

    @property
    def provider_name(self) -> str:
        return "mock"

    async def complete(self, system: str, user: str, **kwargs: object) -> LLMResponse:
        combined = f"{system}||{user}"
        idx = _deterministic_choice(combined, len(_RESPONSE_TEMPLATES))
        return LLMResponse(
            content=_RESPONSE_TEMPLATES[idx],
            provider=self.provider_name,
            model="mock-v1",
            is_mock=True,
        )


class HashEmbeddingProvider(EmbeddingProvider):
    """
    Offline deterministic embedding provider.
    Uses consistent hashing to produce stable 384-dimensional vectors.
    is_offline=True on all responses.
    """

    DIMENSIONS = 384

    @property
    def provider_name(self) -> str:
        return "hash-embedding"

    async def embed(self, texts: list[str]) -> EmbeddingResponse:
        embeddings = [self._hash_to_vector(t) for t in texts]
        return EmbeddingResponse(
            embeddings=embeddings,
            provider=self.provider_name,
            is_offline=True,
            dimensions=self.DIMENSIONS,
            model="hash-embedding-v1",
        )

    def _hash_to_vector(self, text: str) -> list[float]:
        """Produce a deterministic unit-normalized vector from text."""
        # Use SHA-512 to get enough bytes for 384 floats
        digest = hashlib.sha512(text.encode("utf-8")).digest()
        # Build 384 floats by taking pairs of bytes
        values: list[float] = []
        for i in range(self.DIMENSIONS):
            byte_idx = (i * 2) % len(digest)
            raw = struct.unpack_from("H", digest, byte_idx % (len(digest) - 1))[0]
            # Normalize to [-1, 1]
            values.append((raw / 32767.5) - 1.0)
        # L2-normalize
        magnitude = sum(v * v for v in values) ** 0.5
        if magnitude > 0:
            values = [v / magnitude for v in values]
        return values
