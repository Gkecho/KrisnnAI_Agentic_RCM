"""Model abstraction (rule 6: rules first, AI second). The default provider is a deterministic stub with no network.

A real provider may only be used after the tenant's BAA is approved; until then `call_model` refuses it, so PHI
cannot reach a model endpoint by accident.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Protocol


class BaaNotApproved(Exception):
    pass


@dataclass(frozen=True)
class ModelResult:
    text: str
    model_id: str
    model_version: str
    prompt_hash: str


class ModelProvider(Protocol):
    model_id: str
    model_version: str

    def complete(self, prompt: str) -> str: ...


def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


class StubProvider:
    """Deterministic stand-in: the answer depends only on the prompt hash."""

    model_id = "stub"
    model_version = "1"

    def complete(self, prompt: str) -> str:
        return f"stub-answer-{prompt_hash(prompt)[:12]}"


def call_model(provider: ModelProvider, prompt: str, baa_approved: bool = False) -> ModelResult:
    if provider.model_id != StubProvider.model_id and not baa_approved:
        raise BaaNotApproved(f"model provider {provider.model_id!r} needs an approved BAA before it may see any data")
    return ModelResult(provider.complete(prompt), provider.model_id, provider.model_version, prompt_hash(prompt))
