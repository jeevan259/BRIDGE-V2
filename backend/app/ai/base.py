"""Abstract base interfaces for LLM and embedding providers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LLMResponse:
    content: str
    provider: str
    model: str
    is_mock: bool = False


@dataclass
class EmbeddingResponse:
    embeddings: list[list[float]]
    provider: str
    is_offline: bool = False
    dimensions: int = 384


class LLMProvider(ABC):
    """Abstract LLM provider interface."""

    @abstractmethod
    async def complete(self, system: str, user: str, **kwargs: object) -> LLMResponse:
        """Generate a completion given system and user prompts."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...


class EmbeddingProvider(ABC):
    """Abstract embedding provider interface."""

    @abstractmethod
    async def embed(self, texts: list[str]) -> EmbeddingResponse:
        """Generate embeddings for a list of texts."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...
