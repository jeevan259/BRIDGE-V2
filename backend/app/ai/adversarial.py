"""Adversarial Mock Provider — deliberately fabricates citations to demonstrate Hallucination Trap.

The server-side citation resolver strips these fabricated IDs, proving the system
cannot be fooled by an LLM that invents sources.
"""
from __future__ import annotations

import hashlib
import struct
import uuid

from app.ai.base import EmbeddingProvider, EmbeddingResponse, LLMProvider, LLMResponse
from app.ai.mock import HashEmbeddingProvider

# Fabricated (non-existent) UUIDs the adversarial provider will cite
_FAKE_ITEM_IDS = [
    "00000000-dead-beef-0000-000000000001",
    "00000000-dead-beef-0000-000000000002",
    "00000000-dead-beef-0000-000000000003",
]

_FAKE_PASSAGES = [
    "According to Brand Standard §4.2.1: 'All marketing materials must use the official logo at minimum 120px width.'",
    "Per the Global Tone Guide v3 (2024): 'The brand voice is authoritative yet approachable, never aggressive.'",
    "Internal Research Report QR-2024-089: 'Customer satisfaction scores improved 34% with consistent brand application.'",
]

_ADVERSARIAL_TEMPLATES = [
    (
        "The content VIOLATES brand guidelines as documented in item {item_id}. "
        "Specifically, the passage states: '{passage}' — "
        "this directly contradicts the submitted content's approach. "
        "Citation source: knowledge_item_version:{item_id}, passage_id:{fake_uuid}."
    ),
    (
        "CRITICAL FINDING: This content misrepresents approved brand language. "
        "According to knowledge item {item_id}: '{passage}' — "
        "the submitted content deviates from this approved guideline. "
        "Evidence: item_version_id={item_id}, exact_quote='{passage}'"
    ),
    (
        "Brand compliance check FAILED. Source document ID {item_id} states: '{passage}' "
        "The content under review contradicts section 3.4.7 of this approved guideline. "
        "Passage reference: {fake_uuid}"
    ),
]


def _pick(text: str, lst: list) -> object:
    digest = hashlib.sha256(text.encode()).digest()
    idx = struct.unpack(">I", digest[:4])[0] % len(lst)
    return lst[idx]


class AdversarialMockProvider(LLMProvider):
    """
    Adversarial LLM provider that deliberately fabricates citations.
    Used to demonstrate the Hallucination Trap: the server resolves all
    cited item_ids and passage_ids against the real database — fabricated
    IDs will not resolve, exposing the hallucination.
    """

    @property
    def provider_name(self) -> str:
        return "adversarial"

    async def complete(self, system: str, user: str, **kwargs: object) -> LLMResponse:
        combined = f"{system}||{user}"
        fake_item_id = _pick(combined, _FAKE_ITEM_IDS)
        fake_passage = _pick(combined + "p", _FAKE_PASSAGES)
        fake_uuid = str(uuid.uuid4())
        template = _pick(combined + "t", _ADVERSARIAL_TEMPLATES)

        content = str(template).format(
            item_id=fake_item_id,
            passage=fake_passage,
            fake_uuid=fake_uuid,
        )
        return LLMResponse(
            content=content,
            provider=self.provider_name,
            model="adversarial-mock-v1",
            is_mock=True,
        )


# Adversarial provider reuses HashEmbeddingProvider for embeddings
# (embeddings themselves don't hallucinate)
AdversarialEmbeddingProvider = HashEmbeddingProvider
