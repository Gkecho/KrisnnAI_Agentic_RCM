"""Read the KPI SQL files, adapt them to the database, and run them.

Each KPI is one SQL file in `sql/` (readable SQL for review). The same text runs on SQLite (tests, dev) and on
SQL Server (production), so there is one definition to maintain. Two tokens differ by database and are swapped
here: `{date_of(x)}` and `{days_between(a, b)}`. `{{prelude}}` expands to the shared CTEs in `_prelude.sql`.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine

SQL_DIR = Path(__file__).parent / "sql"

_DATE_OF = re.compile(r"\{date_of\(([^{}]+)\)\}")
_DAYS_BETWEEN = re.compile(r"\{days_between\(([^,{}]+),\s*([^{}]+)\)\}")
_PARAM = re.compile(r"(?<![:\w]):(as_of|tenant_id)\b")


def kpi_names() -> list[str]:
    return sorted(p.stem for p in SQL_DIR.glob("*.sql") if not p.stem.startswith("_"))


def render(kpi: str, dialect: str) -> str:
    """SQL text for one KPI. `dialect` is 'sqlite' or 'mssql'; mssql gets @as_of / @tenant_id parameters."""
    path = SQL_DIR / f"{kpi}.sql"
    if not path.is_file() or kpi.startswith("_"):
        raise ValueError(f"unknown KPI {kpi!r}; choose from {', '.join(kpi_names())}")
    prelude = (SQL_DIR / "_prelude.sql").read_text(encoding="utf8").strip()
    sql = path.read_text(encoding="utf8").replace("{{prelude}}", prelude)
    if dialect == "mssql":
        sql = _DATE_OF.sub(r"CAST(\1 AS DATE)", sql)
        sql = _DAYS_BETWEEN.sub(r"DATEDIFF(day, \1, \2)", sql)
        sql = _PARAM.sub(r"@\1", sql)
    elif dialect == "sqlite":
        sql = _DATE_OF.sub(r"date(\1)", sql)
        sql = _DAYS_BETWEEN.sub(r"CAST(julianday(\2) - julianday(\1) AS INTEGER)", sql)
    else:
        raise ValueError(f"unsupported dialect {dialect!r}")
    return sql


def function_ddl(kpi: str) -> str:
    """T-SQL inline table-valued function: metrics.fn_<kpi>(@as_of, @tenant_id). A view cannot take a date."""
    body = render(kpi, "mssql")
    return (
        f"CREATE OR ALTER FUNCTION metrics.fn_{kpi} (@as_of DATE, @tenant_id BIGINT)\n"
        f"RETURNS TABLE\nAS\nRETURN (\n{body}\n)"
    )


def _clean(value):
    if isinstance(value, float):  # SQLite stores Numeric as float; money has 2 places, ratios 6
        return Decimal(str(round(value, 6)))
    return value


def compute(engine: Engine, tenant_id: int, kpi: str, as_of: date) -> list[dict]:
    """Run one KPI for one tenant as of a date. Only data known by then is used (rule 9)."""
    dialect = engine.dialect.name
    sql = render(kpi, dialect)
    as_of_param = as_of.isoformat() if dialect == "sqlite" else as_of
    with engine.connect() as conn:
        rows = conn.execute(text(sql), {"tenant_id": tenant_id, "as_of": as_of_param}).mappings().all()
    out = [{k: _clean(v) for k, v in row.items()} for row in rows]
    if out and "dimension" in out[0]:
        out.sort(key=lambda r: (r["dimension"], str(r["dim_key"])))
    return out


def compute_all(engine: Engine, tenant_id: int, as_of: date) -> dict[str, list[dict]]:
    return {kpi: compute(engine, tenant_id, kpi, as_of) for kpi in kpi_names()}
