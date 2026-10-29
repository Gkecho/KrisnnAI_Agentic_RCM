"""Action adapters. Everything here is disabled or a stub by default."""

from krisnnai.engine.adapters.base import Adapter, AdapterDisabled, AdapterResult
from krisnnai.engine.adapters.clearinghouse import ClearinghouseStub
from krisnnai.engine.adapters.task_note import TaskNoteAdapter

__all__ = ["Adapter", "AdapterDisabled", "AdapterResult", "ClearinghouseStub", "TaskNoteAdapter"]
