"""The inbox: one folder the PM, EHR and clearinghouse files land in each day.

`scan` lists what is there in dependency order (reference data, claims, acknowledgements, payments, then the PM feeds
that point at claims). `load_inbox` ingests each file through the same idempotent loader as `krisnnai ingest`, then
moves it: loaded and already-loaded files to `archive/<run date>/`, files that did not parse to `rejected/<run date>/`
with the reason beside them. A file is never deleted, and a second run over an empty inbox does nothing.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from sqlalchemy.engine import Engine

from krisnnai.ingest.loader import CSV_NAME_HINTS, X12_SUFFIXES, IngestResult, csv_kind, ingest_file

CSV_RANK = {
    "fee_schedule": 0, "crosswalk": 0, "enrollments": 0, "screenings": 0,
    "visits": 4, "notes": 4, "charges": 4, "appointments": 4, "authorizations": 4,
    "deposits": 5, "postings": 5, "patient_payments": 5, "statements": 5,
}  # fmt: skip
X12_RANK = {"HC": 1, "FA": 2, "HN": 2, "HP": 3, "HB": 4}  # GS01: 837, 999, 277CA, 835, 271
_GS = re.compile(r"GS[*~](\w\w)[*~]")


def _rank(path: Path) -> int:
    if path.suffix.lower() == ".csv":
        return CSV_RANK.get(csv_kind(path.name), 0)
    try:
        head = path.read_bytes()[:400].decode("utf-8", "ignore")
    except OSError:
        return 9
    found = _GS.search(head)
    return X12_RANK.get(found.group(1), 6) if found else 6


def scan(inbox: Path) -> list[Path]:
    files = [
        p for p in inbox.rglob("*")
        if p.is_file() and (p.suffix.lower() in X12_SUFFIXES or p.suffix.lower() == ".csv")
        and (p.suffix.lower() != ".csv" or any(k in p.name.lower() for k in CSV_NAME_HINTS))
    ]  # fmt: skip
    return sorted(files, key=lambda p: (_rank(p), p.name, str(p)))


@dataclass
class LoadReport:
    results: list[IngestResult] = field(default_factory=list)

    def count(self, status: str) -> int:
        return sum(1 for r in self.results if r.status == status)

    @property
    def events(self) -> int:
        return sum(r.events for r in self.results)


def _move(src: Path, folder: Path, reason: str | None = None) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / src.name
    n = 1
    while dest.exists():
        dest = folder / f"{src.stem}.{n}{src.suffix}"
        n += 1
    shutil.move(str(src), str(dest))
    if reason is not None:
        dest.with_name(dest.name + ".reason.txt").write_text(reason + "\n", encoding="utf-8")


def load_inbox(
    engine: Engine, tenant_id: int, inbox: Path, archive: Path, salt: str, run_date: date,
    rejected: Path | None = None,
) -> LoadReport:
    report = LoadReport()
    rejected = rejected or archive.parent / "rejected"
    for path in scan(inbox):
        try:
            res = ingest_file(engine, tenant_id, path, salt)
        except Exception as e:  # noqa: BLE001 - one bad file must not stop the day; it goes to rejected/ with its error
            res = IngestResult(str(path), "failed", "", f"{type(e).__name__}: {e}")
        if res.status == "skipped" and res.reason.endswith("(failed)"):
            res = IngestResult(res.path, "failed", res.file_type, "this file failed to load before: " + res.reason)
        report.results.append(res)
        if res.status == "failed":
            _move(path, rejected / run_date.isoformat(), res.reason)
        else:
            _move(path, archive / run_date.isoformat())
    return report
