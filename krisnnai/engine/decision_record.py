"""Decision record writer and the canonical fingerprint replay uses to prove two runs are identical."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy.orm import Session

from krisnnai.model import DecisionRecord

# Changes between two otherwise identical runs, so never part of the fingerprint
_VOLATILE = {"id", "loaded_at", "approved_at"}


def canonical_json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def as_dict(record: DecisionRecord) -> dict:
    return {c.name: getattr(record, c.name) for c in DecisionRecord.__table__.columns}


def fingerprint(record: DecisionRecord) -> str:
    content = {k: v for k, v in as_dict(record).items() if k not in _VOLATILE}
    return hashlib.sha256(canonical_json(content).encode("utf-8")).hexdigest()


def write_record(session: Session, **fields) -> DecisionRecord:
    record = DecisionRecord(**fields)
    session.add(record)
    session.flush()
    return record
