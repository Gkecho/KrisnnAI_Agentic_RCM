"""Action adapters: the only place an engine decision can touch the outside world."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class AdapterDisabled(Exception):
    """The adapter exists but is switched off (the default)."""


@dataclass(frozen=True)
class AdapterResult:
    ok: bool
    detail: str


class Adapter(Protocol):
    name: str

    def execute(self, action_type: str, payload: dict) -> AdapterResult: ...
