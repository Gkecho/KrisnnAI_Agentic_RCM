"""Query safety for the analytics query registry: validate SQL text, then run it read-only with limits.

Hard rules served: 1 (no person-level data leaves), 2 (read-only), 8 (tenant isolation), 10 (money is Decimal).

What this module does
- ``validate_sql``  tokenizes the SQL itself (no regexes over raw text), drops comments, and accepts only ONE
  ``SELECT`` / ``WITH ... SELECT`` statement that uses a function allow-list, a per-query table allow-list, only the
  declared ``:name`` binds, and a ``tenant_id = :tenant_id`` predicate for every table it reads. The text that is
  executed is rebuilt from the validated tokens, so what was checked is exactly what runs.
- ``run_query``     runs it on a READ-ONLY connection with ``statement_timeout`` and a row cap, then checks that the
  result columns are exactly the expected ones (names, order, value types) and that no cell looks like an identifier.

What it cannot guarantee is listed in docs/fin_admin.md ("Limits of the validation").
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

DEFAULT_ROW_CAP = 5000
DEFAULT_TIMEOUT_MS = 120_000
KINDS = ("text", "int", "money", "float", "bool")
ALLOWED_BINDS = ("tenant_id", "asof", "d")

# Column names that must never appear in a result (person-level / identifier shapes).
FORBIDDEN_COLUMN = re.compile(
    r"(patient_id|guarantor|member|subscriber|mrn|dob|ssn|birth|first_?name|last_?name|address|phone|email"
    r"|claim_id|claim_number|_id$|_hash$|_key$|^id$)",
    re.I,
)
# Cell values that look like identifiers (uuid, bytea hash, ssn shape) or are too long to be a label.
FORBIDDEN_VALUE = re.compile(
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|\\x[0-9a-f]{16,}|\b\d{3}-\d{2}-\d{4}\b)", re.I
)
MAX_TEXT_LEN = 80

FORBIDDEN_WORDS = frozenset(
    """insert update delete drop alter create truncate grant revoke copy call do execute set reset vacuum lock merge
    into analyze explain declare fetch for listen notify unlisten prepare deallocate begin commit rollback
    savepoint release abort start refresh reindex cluster comment security import discard load checkpoint show returning
    """.split()
)
FUNC_ALLOW = frozenset(
    """count sum avg min max coalesce nullif greatest least round abs ceil ceiling floor to_char width_bucket
    percentile_cont percentile_disc date_trunc lower upper length btrim concat row_number rank dense_rank lag lead
    bool_and bool_or""".split()
)
# Words that may legitimately be followed by "(" without being a function call.
PAREN_WORDS = frozenset(
    """in exists any all some as on and or not from join when then else case by select where having union except
    intersect rollup cube grouping filter over within group between like ilike is using distinct limit offset end with
    left right inner outer cross full values array""".split()
)
CAST_TYPES = frozenset(
    "int integer bigint smallint numeric decimal text varchar date boolean bool float real double precision".split()
)
FROM_END = frozenset(
    "where group order having limit union intersect except offset window select fetch".split()
)  # keywords that end a FROM list at the same nesting depth


class SqlRejected(ValueError):
    """The SQL text is not acceptable (the message says why; it never contains connection details)."""


class ResultRejected(ValueError):
    """The query ran but its result does not match the chart's output contract."""


@dataclass(frozen=True)
class Spec:
    """The contract of one named query: what it may read, bind and return."""

    query_id: str
    columns: tuple[tuple[str, str], ...]  # (name, kind)
    params: tuple[str, ...] = ("tenant_id",)
    tables: frozenset[str] = field(default_factory=frozenset)
    row_cap: int = DEFAULT_ROW_CAP

    @property
    def column_names(self) -> list[str]:
        return [c[0] for c in self.columns]


@dataclass(frozen=True)
class Validated:
    tokens: tuple[tuple[str, str], ...]
    binds: frozenset[str]
    tables: frozenset[str]

    @property
    def canonical(self) -> str:
        """Comment-free text with ``:name`` binds; this is what gets stored and executed."""
        return " ".join(v for _, v in self.tokens)


@dataclass
class QueryResult:
    columns: list[str]
    rows: list[tuple[Any, ...]]


# ---------------------------------------------------------------------------------------------------------------------
# tokenizer + validator
# ---------------------------------------------------------------------------------------------------------------------
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_NUM = re.compile(r"\d+(\.\d*)?([eE][+-]?\d+)?|\.\d+")
_OPCH = "+-*/%<>=!|~^&@#"


def tokenize(sql: str) -> list[tuple[str, str]]:
    """Split into (kind, text). Comments vanish; strings stay whole. Anything unusual is rejected."""
    toks: list[tuple[str, str]] = []
    i, n = 0, len(sql)
    while i < n:
        c = sql[i]
        if c.isspace():
            i += 1
        elif sql.startswith("--", i):
            j = sql.find("\n", i)
            i = n if j < 0 else j + 1
        elif sql.startswith("/*", i):
            j = sql.find("*/", i + 2)
            if j < 0:
                raise SqlRejected("unterminated block comment")
            i = j + 2
        elif c == "'":
            j = i + 1
            while True:
                j = sql.find("'", j)
                if j < 0:
                    raise SqlRejected("unterminated string literal")
                if sql.startswith("''", j):
                    j += 2
                    continue
                break
            toks.append(("str", sql[i : j + 1]))
            i = j + 1
        elif c == '"':
            raise SqlRejected('quoted identifiers ("...") are not allowed')
        elif c == "$":
            raise SqlRejected("dollar quoting and $n parameters are not allowed")
        elif c == ":":
            if sql.startswith("::", i):
                toks.append(("op", "::"))
                i += 2
            else:
                m = _IDENT.match(sql, i + 1)
                if not m:
                    raise SqlRejected("stray ':'")
                toks.append(("bind", ":" + m.group(0).lower()))
                i = m.end()
        elif c.isascii() and (c.isalpha() or c == "_"):
            m = _IDENT.match(sql, i)
            assert m
            toks.append(("ident", m.group(0).lower()))
            i = m.end()
        elif (c.isdigit() or (c == "." and sql[i + 1 : i + 2].isdigit())) and c.isascii():
            m = _NUM.match(sql, i)
            assert m
            toks.append(("num", m.group(0)))
            i = m.end()
        elif c in "()[],;.":
            toks.append(("punct", c))
            i += 1
        elif c in _OPCH:
            j = i
            while j < n and sql[j] in _OPCH and not sql.startswith("--", j) and not sql.startswith("/*", j):
                j += 1
            toks.append(("op", sql[i:j]))
            i = j
        else:
            raise SqlRejected(f"character not allowed: {c!r}")
    return toks


def validate_sql(
    sql: str,
    *,
    allowed_binds: tuple[str, ...] | frozenset[str] = ALLOWED_BINDS,
    allowed_tables: frozenset[str] | None = None,
    require_tenant: bool = True,
) -> Validated:
    if not isinstance(sql, str) or not sql.strip():
        raise SqlRejected("empty SQL")
    if len(sql) > 20_000:
        raise SqlRejected("SQL too long (20,000 characters max)")
    toks = tokenize(sql)
    while toks and toks[-1] == ("punct", ";"):
        toks.pop()
    if not toks:
        raise SqlRejected("empty SQL")
    if any(t == ("punct", ";") for t in toks):
        raise SqlRejected("only a single statement is allowed (found ';' inside)")
    first = toks[0][1] if toks[0][0] == "ident" else ""
    if first not in ("select", "with"):
        raise SqlRejected("only SELECT statements are allowed (must start with SELECT or WITH)")

    binds: set[str] = set()
    ctes: set[str] = set()
    for k, (kind, v) in enumerate(toks):
        nxt = toks[k + 1] if k + 1 < len(toks) else ("", "")
        if kind == "ident":
            if v in FORBIDDEN_WORDS:
                raise SqlRejected(f"keyword not allowed: {v.upper()}")
            if nxt == ("punct", "(") and v not in FUNC_ALLOW and v not in PAREN_WORDS:
                raise SqlRejected(f"function not allowed: {v}()")
            if nxt == ("ident", "as") and k + 2 < len(toks) and toks[k + 2] == ("punct", "("):
                ctes.add(v)
        elif kind == "bind":
            name = v[1:]
            if name not in allowed_binds:
                raise SqlRejected(
                    f"bind parameter {v} is not allowed for this query (allowed: {sorted(allowed_binds)})"
                )
            binds.add(name)
        elif kind == "op" and v == "::":
            ty = nxt[1] if nxt[0] == "ident" else ""
            if ty not in CAST_TYPES:
                raise SqlRejected(f"cast to {ty or '?'} is not allowed")

    tables = _table_refs(toks, ctes)
    for t in tables:
        if t not in ctes and allowed_tables is not None and t not in allowed_tables:
            raise SqlRejected(f"table not allowed for this query: {t}")
    base_refs = [t for t in tables if t not in ctes]
    if require_tenant:
        if "tenant_id" not in binds:
            raise SqlRejected("the query must use the :tenant_id bind parameter")
        preds = _tenant_predicates(toks)
        if preds < max(1, len(base_refs)):
            raise SqlRejected(
                f"every table needs its own 'tenant_id = :tenant_id' condition ({len(base_refs)} table reference(s), "
                f"{preds} such condition(s) found)"
            )
    return Validated(tuple(toks), frozenset(binds), frozenset(t for t in tables if t not in ctes))


def _table_refs(toks: list[tuple[str, str]], ctes: set[str]) -> list[str]:
    """Names after FROM / JOIN / comma-in-FROM, with multiplicity. Subselects are walked by the same loop."""
    refs: list[str] = []
    in_from = [False]
    expect = False
    for k, (kind, v) in enumerate(toks):
        nxt = toks[k + 1] if k + 1 < len(toks) else ("", "")
        prev = toks[k - 1] if k else ("", "")
        if expect:
            expect = False
            if (kind, v) == ("punct", "("):
                pass  # subselect: handled below as a new depth
            elif kind == "ident":
                if nxt == ("punct", "(") or nxt == ("punct", "."):
                    raise SqlRejected(f"only plain table names are allowed after FROM/JOIN (got {v})")
                refs.append(v)
                continue
            else:
                raise SqlRejected("unsupported FROM clause")
        if (kind, v) == ("punct", "("):
            in_from.append(False)
        elif (kind, v) == ("punct", ")"):
            if len(in_from) > 1:
                in_from.pop()
        elif kind == "ident" and v == "from" and prev != ("ident", "distinct"):
            in_from[-1] = True
            expect = True
        elif kind == "ident" and v == "join":
            expect = True
        elif kind == "ident" and v in FROM_END:
            in_from[-1] = False
        elif (kind, v) == ("punct", ",") and in_from[-1]:
            expect = True
    return refs


def _tenant_predicates(toks: list[tuple[str, str]]) -> int:
    """Count ``[alias.]tenant_id = :tenant_id`` conditions that are AND-ed (not next to OR)."""
    n = 0
    for k in range(len(toks) - 2):
        a, b, c = toks[k], toks[k + 1], toks[k + 2]
        if not (
            b == ("op", "=")
            and (
                (a == ("ident", "tenant_id") and c == ("bind", ":tenant_id"))
                or (a == ("bind", ":tenant_id") and c == ("ident", "tenant_id"))
            )
        ):
            continue
        start = k - 2 if a == ("ident", "tenant_id") and k >= 2 and toks[k - 1] == ("punct", ".") else k
        before = toks[start - 1] if start else ("", "")
        after = toks[k + 3] if k + 3 < len(toks) else ("", "")
        if before == ("ident", "or") or after == ("ident", "or"):
            continue
        n += 1
    return n


def to_psycopg(v: Validated) -> str:
    """Canonical text -> psycopg2 text: ``:name`` -> ``%(name)s`` and every literal ``%`` doubled."""
    out: list[str] = []
    for kind, text in v.tokens:
        if kind == "bind":
            out.append(f"%({text[1:]})s")
        else:
            out.append(text.replace("%", "%%"))
    return " ".join(out)


# ---------------------------------------------------------------------------------------------------------------------
# result checks
# ---------------------------------------------------------------------------------------------------------------------
def _kind_ok(kind: str, value: Any) -> bool:
    if value is None:
        return True
    if kind == "text":
        return isinstance(value, str)
    if kind == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == "money":
        return isinstance(value, Decimal)  # hard rule 10: a float here means the SQL broke the money contract
    if kind == "float":
        return isinstance(value, float)
    if kind == "bool":
        return isinstance(value, bool)
    return False


def check_columns(spec: Spec, names: list[str]) -> None:
    for nm in names:
        if FORBIDDEN_COLUMN.search(nm):
            raise ResultRejected(f"column {nm!r} looks like an identifier / person-level field and is not allowed")
    if names != spec.column_names:
        extra = [n for n in names if n not in spec.column_names]
        missing = [n for n in spec.column_names if n not in names]
        raise ResultRejected(
            f"result columns must be exactly {spec.column_names} in this order; got {names}"
            + (f" (extra: {extra})" if extra else "")
            + (f" (missing: {missing})" if missing else "")
        )


def check_rows(spec: Spec, rows: list[tuple[Any, ...]]) -> None:
    kinds = [c[1] for c in spec.columns]
    for r, row in enumerate(rows):
        for (name, _), kind, value in zip(spec.columns, kinds, row, strict=True):
            if not _kind_ok(kind, value):
                raise ResultRejected(
                    f"column {name!r} must be {kind} but row {r + 1} has {type(value).__name__}"
                    + (" (money must be exact Decimal, never float)" if kind == "money" else "")
                )
            if kind == "text" and value is not None and (len(value) > MAX_TEXT_LEN or FORBIDDEN_VALUE.search(value)):
                raise ResultRejected(f"column {name!r} row {r + 1}: text value looks like an identifier or free text")


# ---------------------------------------------------------------------------------------------------------------------
# execution
# ---------------------------------------------------------------------------------------------------------------------
def run_query(
    conn: Any,
    spec: Spec,
    sql: str,
    params: dict[str, Any],
    *,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    row_cap: int | None = None,
) -> QueryResult:
    """Validate ``sql`` against ``spec``, run it read-only, validate the result. Always ends the transaction."""
    v = validate_sql(sql, allowed_binds=spec.params, allowed_tables=spec.tables or None)
    cap = row_cap or spec.row_cap
    bound = {k: params[k] for k in v.binds}
    missing = [k for k in v.binds if k not in params]
    if missing:
        raise SqlRejected(f"missing bind value(s): {missing}")
    if not isinstance(bound["tenant_id"], int) or isinstance(bound["tenant_id"], bool):
        raise SqlRejected("tenant_id must be an integer")
    for k in ("asof", "d"):
        if k in bound and not isinstance(bound[k], dt.date):
            raise SqlRejected(f"{k} must be a date")
    try:
        with conn.cursor() as cur:
            cur.execute("SHOW transaction_read_only")
            if cur.fetchone()[0] != "on":
                raise SqlRejected("refusing to run: the connection is not read-only")
            cur.execute("SELECT set_config('statement_timeout', %s, true)", (str(int(timeout_ms)),))
            cur.execute(to_psycopg(v), bound)
            names = [d[0] for d in cur.description]
            rows = list(cur.fetchmany(cap + 1))
    finally:
        conn.rollback()
    if len(rows) > cap:
        raise ResultRejected(f"more than {cap} rows returned (row cap)")
    check_columns(spec, names)
    check_rows(spec, rows)
    return QueryResult(names, rows)


def is_all_zero(rows: list[tuple[Any, ...]]) -> bool:
    return all(v is None or v == 0 or v == "" for row in rows for v in row)


def probe_other_tenant(conn: Any, spec: Spec, sql: str, params: dict[str, Any], alien: int = -987_654) -> bool:
    """True if the query returns nothing for a tenant that has no data (no rows, or only zeros / NULLs)."""
    res = run_query(conn, spec, sql, {**params, "tenant_id": alien})
    return is_all_zero(res.rows)
