"""Task / note write-back to the practice-management system. Disabled by default (rule 2).

MVP write-back is limited to tasks and notes. No PM connector exists yet, so even when enabled this keeps the
requests in an outbox for a future connector to deliver; it never touches a client database.
"""

from __future__ import annotations

from krisnnai.engine.adapters.base import AdapterDisabled, AdapterResult


class TaskNoteAdapter:
    name = "task_note"

    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self.outbox: list[tuple[str, dict]] = []

    def execute(self, action_type: str, payload: dict) -> AdapterResult:
        if not self.enabled:
            raise AdapterDisabled("task/note write-back is disabled for this tenant")
        self.outbox.append((action_type, dict(payload)))
        return AdapterResult(True, f"queued {action_type} in the outbox (no PM connector yet)")
