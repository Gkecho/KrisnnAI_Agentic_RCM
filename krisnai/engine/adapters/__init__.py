"""Action adapters. Everything here is disabled or a stub by default."""

from krisnai.engine.adapters.base import Adapter, AdapterDisabled, AdapterResult
from krisnai.engine.adapters.clearinghouse import ClearinghouseStub
from krisnai.engine.adapters.task_note import TaskNoteAdapter

__all__ = ["Adapter", "AdapterDisabled", "AdapterResult", "ClearinghouseStub", "TaskNoteAdapter"]
