"""Read Synthea's CSV exporter output (patients, encounters, claims, claims_transactions, payers).

Column names follow the Synthea CSV data dictionary. Headers are matched case-insensitively, and a missing file is an
empty table, so the caller decides what is required.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

TABLES = ("patients", "encounters", "claims", "claims_transactions", "payers")


@dataclass
class SyntheaData:
    patients: list[dict[str, str]] = field(default_factory=list)
    encounters: list[dict[str, str]] = field(default_factory=list)
    claims: list[dict[str, str]] = field(default_factory=list)
    claims_transactions: list[dict[str, str]] = field(default_factory=list)
    payers: list[dict[str, str]] = field(default_factory=list)


def read_table(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return [{(k or "").strip().lower(): (v or "").strip() for k, v in row.items()} for row in csv.DictReader(fh)]


def find_csv_dir(path: Path) -> Path:
    """Synthea writes into <out>/csv; accept either the run folder or the csv folder itself."""
    for candidate in (path, path / "csv"):
        if (candidate / "claims.csv").exists() or (candidate / "encounters.csv").exists():
            return candidate
    raise FileNotFoundError(f"no Synthea CSV files (claims.csv / encounters.csv) under {path}")


def read_dir(path: Path) -> SyntheaData:
    base = find_csv_dir(path)
    return SyntheaData(**{name: read_table(base / f"{name}.csv") for name in TABLES})
