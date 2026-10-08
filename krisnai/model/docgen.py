"""Generate docs/data_model.md (ERD + one line per column with its X12 source) from the models.

python -m krisnai.model.docgen          # rewrite docs/data_model.md
python -m krisnai.model.docgen --check  # exit 1 if the file is out of date (used by tests)
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import Table
from sqlalchemy.dialects import mssql

import krisnai.model  # noqa: F401
from krisnai.model.base import Base

DOC_PATH = Path(__file__).resolve().parents[2] / "docs" / "data_model.md"

INFRA_SOURCES = {
    "id": "surrogate key (IDENTITY)",
    "tenant_id": "owning tenant; every query filters on it",
    "source_file_id": "file this row was loaded from (lineage)",
    "loaded_at": "server UTC time the row was loaded",
}

HEADER = """# KrisnAI core data model (M1)

> Generated from `krisnai/model` by `python -m krisnai.model.docgen`. Do not edit by hand;
> a test fails when this file is out of date.

## Principles

- **Event sourced.** `event` rows are append-only (a SQL Server trigger rejects UPDATE and DELETE).
  Normalized tables are rebuilt from events.
- **Tenant isolation.** Every table has `tenant_id`. Every child references its parent with a
  composite `(tenant_id, parent_id)` foreign key, so a row can never point at another tenant's
  parent. Application code reads and writes through `tenant_session`, which filters every
  SELECT by tenant and stamps every INSERT.
- **Idempotency.** Unique keys marked below make re-ingesting a file (same SHA-256) or a
  transaction (same ISA13/GS06/ST02) a no-op instead of a duplicate.
- **No raw PHI columns.** Patients exist only as `patient_ref.ref_hash`, a salted SHA-256.
- **Money is DECIMAL(18,2), units DECIMAL(9,2), dates are DATE.**
- Match links (`remit.claim_id`, `remit_line.claim_line_id`, `ack_277ca.claim_id`) stay NULL until
  M3 fills them in and records `match_method`.
"""


def _tables() -> list[Table]:
    return list(Base.metadata.sorted_tables)


def _erd() -> str:
    lines = ["```mermaid", "erDiagram"]
    edges: set[tuple[str, str]] = set()
    for t in _tables():
        for fk in t.foreign_key_constraints:
            parent = fk.referred_table.name
            if parent not in ("tenant", "source_file"):
                edges.add((parent, t.name))
    lines += [f"    {parent} ||--o{{ {child} : has" for parent, child in sorted(edges)]
    lines.append("```")
    return "\n".join(lines)


def _type(column) -> str:
    return column.type.compile(dialect=mssql.dialect())


def render() -> str:
    out = [
        HEADER,
        "## Relationships\n",
        "`tenant` owns every table (omitted from the diagram).\n",
        _erd(),
        "",
    ]
    out.append("## Tables\n")
    for t in _tables():
        out.append(f"### `{t.name}`\n")
        uniques = [
            ", ".join(c.name for c in u.columns)
            for u in t.constraints
            if u.__class__.__name__ == "UniqueConstraint"
            and [c.name for c in u.columns] != ["tenant_id", "id"]
        ]
        if uniques:
            out.append(
                "Unique keys (idempotency): "
                + "; ".join(f"`({u})`" for u in sorted(uniques))
                + "\n"
            )
        out.append("| Column | Type | Null | Source |")
        out.append("|---|---|---|---|")
        for c in t.columns:
            src = c.info.get("src") or INFRA_SOURCES.get(c.name, "")
            if t.name == "tenant" and c.name == "tenant_id":
                src = "surrogate key (IDENTITY); the tenant id used everywhere"
            if t.name == "tenant" and c.name == "created_at":
                src = "server UTC time the tenant was created"
            out.append(f"| `{c.name}` | {_type(c)} | {'yes' if c.nullable else 'no'} | {src} |")
        out.append("")
    return "\n".join(out)


def main() -> int:
    text = render()
    if "--check" in sys.argv:
        current = DOC_PATH.read_text(encoding="utf-8") if DOC_PATH.exists() else ""
        if current.replace("\r\n", "\n") != text:
            print("docs/data_model.md is out of date; run python -m krisnai.model.docgen")
            return 1
        return 0
    DOC_PATH.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {DOC_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
