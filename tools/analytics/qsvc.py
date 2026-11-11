"""Service layer for the query admin: test runs with before/after diff, and "publish to site data".

Needs a read-only Postgres connection (``conn_factory``); the registry itself is plain SQLite.
Nothing here writes to krisnnai_r2, copies into the site folder, or deploys.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
import re
import threading
from collections import Counter
from collections.abc import Callable
from decimal import Decimal
from typing import Any

import qreg
import qsafe

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT_PATH = ROOT / "out" / "fin" / "fin_data.js"
AS_OF = dt.date(2026, 11, 6)
PREVIEW_ROWS = 50
DIFF_SAMPLE = 15


def jsonable(v: Any) -> Any:
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, dt.date):
        return v.isoformat()
    return v


def safe_error(exc: BaseException) -> str:
    """One-line error text that is safe to show: never a connection string, never a password."""
    if isinstance(exc, (qsafe.SqlRejected, qsafe.ResultRejected, qreg.WorkflowError)):
        return str(exc)
    name = type(exc).__name__
    first = str(exc).strip().splitlines()[0] if str(exc).strip() else ""
    if "password" in first.lower() or "connect" in first.lower() or "host" in first.lower() or "dsn" in first.lower():
        return f"{name}: database connection problem (details hidden)"
    return f"{name}: {first[:300]}"


def default_conn_factory() -> Any:
    import export_fin_data as fin

    return fin.open_connection()


class Service:
    def __init__(self, registry: qreg.Registry, conn_factory: Callable[[], Any] = default_conn_factory) -> None:
        self.registry = registry
        self.conn_factory = conn_factory
        self._publish_lock = threading.Lock()

    # -- test run ------------------------------------------------------------------------------------------------
    def _params(self, query_id: str, tenant_id: int) -> dict[str, Any]:
        return {"tenant_id": tenant_id, "asof": AS_OF, "d": AS_OF}

    def run_sql(self, conn: Any, query_id: str, sql: str, tenant_id: int) -> qsafe.QueryResult:
        return qsafe.run_query(conn, self.registry.spec(query_id), sql, self._params(query_id, tenant_id))

    def test_run(self, version_id: int, actor: str, tenant_id: int = 1) -> dict[str, Any]:
        """Run a draft read-only, compare with the currently effective published SQL, probe another tenant."""
        v = self.registry.version(version_id)
        qid, node_id = v["query_id"], v["node_id"]
        out: dict[str, Any] = {"version_id": version_id, "query_id": qid, "tenant_id": tenant_id, "ok": False}
        conn = None
        try:
            conn = self.conn_factory()
            spec = self.registry.spec(qid)
            res = self.run_sql(conn, qid, v["sql"], tenant_id)
            out.update(
                columns=res.columns,
                row_count=len(res.rows),
                preview=[[jsonable(c) for c in r] for r in res.rows[:PREVIEW_ROWS]],
            )
            probe_ok = qsafe.probe_other_tenant(conn, spec, v["sql"], self._params(qid, tenant_id))
            out["tenant_probe_ok"] = probe_ok
            try:
                base = self.registry.resolve_at(qid, node_id)
                base_res = self.run_sql(conn, qid, base.sql, tenant_id)
                out["baseline"] = {
                    "level": base.level,
                    "version": base.version,
                    "row_count": len(base_res.rows),
                    **self.diff(base_res.rows, res.rows),
                }
            except KeyError:
                out["baseline"] = None
            out["ok"] = probe_ok
            if not probe_ok:
                out["error"] = "tenant probe failed: the query returned data for a tenant that has none"
        except Exception as exc:
            out["error"] = safe_error(exc)
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:  # noqa: BLE001
                    pass
        self.registry.record_test(
            version_id, bool(out["ok"]), actor, {"row_count": out.get("row_count"), "error": out.get("error", "")}
        )
        return out

    @staticmethod
    def diff(before: list[tuple[Any, ...]], after: list[tuple[Any, ...]]) -> dict[str, Any]:
        b = Counter(json.dumps([jsonable(c) for c in r]) for r in before)
        a = Counter(json.dumps([jsonable(c) for c in r]) for r in after)
        removed, added = b - a, a - b
        return {
            "identical": not removed and not added,
            "rows_removed": sum(removed.values()),
            "rows_added": sum(added.values()),
            "sample_removed": [json.loads(k) for k in list(removed)[:DIFF_SAMPLE]],
            "sample_added": [json.loads(k) for k in list(added)[:DIFF_SAMPLE]],
        }

    # -- publish to site data ------------------------------------------------------------------------------------
    def publish_site(
        self, actor: str, tenant_id: int = 1, role: str | None = None, out_path: pathlib.Path | None = None
    ) -> dict[str, Any]:
        """Regenerate fin_data.js from the resolved queries. Writes ONE local file; never copies or deploys it."""
        import export_fin_data as fin

        with self._publish_lock:
            source = qreg.QuerySource(self.registry, customer=str(tenant_id), role=role)
            conn = self.conn_factory()
            try:
                data = fin.build(conn, tenant_id, source)
            finally:
                conn.close()
            text = fin.render(data)
            out = pathlib.Path(out_path) if out_path else OUT_PATH
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text, encoding="utf-8")
            stable = re.sub(r'"generated_at":"[^"]*"', '"generated_at":""', text)
            digest = hashlib.sha256(stable.encode("utf-8")).hexdigest()
            used = {k: v for k, v in sorted(source.used.items())}
            with self.registry.tx() as db:
                self.registry.audit(
                    db,
                    actor,
                    "publish_site_data",
                    detail={
                        "path": str(out),
                        "bytes": len(text.encode("utf-8")),
                        "sha256_without_generated_at": digest,
                        "tenant_id": tenant_id,
                        "role": role,
                        "non_solution_queries": {k: v for k, v in used.items() if v["level"] != "solution"},
                    },
                )
            return {
                "path": str(out),
                "bytes": len(text.encode("utf-8")),
                "sha256": digest,
                "queries": used,
                "next_step": (
                    "Copy this file into the site folder and deploy when you are ready. This tool does neither."
                ),
            }
