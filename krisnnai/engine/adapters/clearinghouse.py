"""Clearinghouse adapter stub (rule 3: nothing is ever submitted to a payer directly).

This stub records what would have been sent and sends nothing. A real adapter is a later, gated milestone.
"""

from __future__ import annotations

from krisnnai.engine.adapters.base import AdapterResult


class ClearinghouseStub:
    name = "clearinghouse_stub"

    def __init__(self) -> None:
        self.requests: list[tuple[str, dict]] = []

    def execute(self, action_type: str, payload: dict) -> AdapterResult:
        self.requests.append((action_type, dict(payload)))
        return AdapterResult(True, "stub: recorded, not sent")
