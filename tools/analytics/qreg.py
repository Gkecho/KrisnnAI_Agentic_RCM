"""Query registry: scope hierarchy, versioned query definitions, resolver, workflow, impact preview and audit log.

Storage is a local SQLite file (default ``var/analytics_registry.sqlite``). It is NOT part of the locked krisnnai_r2
model and holds no patient data: only SQL text, scope names and who changed what.

Hierarchy: solution > parent application > application > customer > role. A query saved at a node applies to
everything below it; the narrowest node with a PUBLISHED version wins, otherwise the next broader one is used.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

import fin_seed
import qsafe

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_PATH = ROOT / "var" / "analytics_registry.sqlite"
LEVELS = ("solution", "parent_app", "application", "customer", "role")
STATUSES = ("draft", "in_review", "approved", "published", "retired")
OPEN_STATUSES = ("draft", "in_review", "approved")
MODES = ("demo", "strict")
DEMO_NOTE = "single-user demo"


class WorkflowError(Exception):
    """A workflow step that is not allowed right now (wrong state, strict-mode self-approval, ...)."""


SCHEMA = """
CREATE TABLE IF NOT EXISTS scope_node(
  id INTEGER PRIMARY KEY, level TEXT NOT NULL, key TEXT NOT NULL, name TEXT NOT NULL,
  parent_id INTEGER REFERENCES scope_node(id), UNIQUE(parent_id, key));
CREATE TABLE IF NOT EXISTS query_spec(
  query_id TEXT PRIMARY KEY, title TEXT NOT NULL, owner_app TEXT NOT NULL, apps_json TEXT NOT NULL,
  charts_json TEXT NOT NULL, params_json TEXT NOT NULL, columns_json TEXT NOT NULL, tables_json TEXT NOT NULL,
  row_cap INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS query_version(
  id INTEGER PRIMARY KEY, query_id TEXT NOT NULL REFERENCES query_spec(query_id),
  node_id INTEGER NOT NULL REFERENCES scope_node(id), version INTEGER NOT NULL, sql TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('draft','in_review','approved','published','retired')),
  author TEXT NOT NULL, approver TEXT, change_note TEXT NOT NULL DEFAULT '', approval_note TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL, submitted_at TEXT, approved_at TEXT, published_at TEXT,
  retired_at TEXT, tested_hash TEXT, tested_ok INTEGER NOT NULL DEFAULT 0, source_version INTEGER,
  UNIQUE(query_id, node_id, version));
CREATE UNIQUE INDEX IF NOT EXISTS one_published ON query_version(query_id, node_id) WHERE status = 'published';
CREATE UNIQUE INDEX IF NOT EXISTS one_open ON query_version(query_id, node_id)
  WHERE status IN ('draft','in_review','approved');
CREATE TABLE IF NOT EXISTS audit(
  id INTEGER PRIMARY KEY, ts TEXT NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL, query_id TEXT, node_id INTEGER,
  version INTEGER, detail TEXT NOT NULL, mode TEXT NOT NULL, prev_hash TEXT NOT NULL, hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS setting(key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""


def now_iso() -> str:
    import datetime as dt

    return dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _text(sql: str) -> str:
    return sql.strip() + chr(10)


def sql_hash(sql: str) -> str:
    return hashlib.sha256(sql.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Resolved:
    query_id: str
    sql: str
    level: str
    node_id: int
    node_name: str
    version: int
    version_id: int


class Registry:
    def __init__(self, path: str | os.PathLike[str] | None = None) -> None:
        p = pathlib.Path(path or os.environ.get("KRISNNAI_REGISTRY") or DEFAULT_PATH)
        if str(p) != ":memory:":
            p.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = p
        self._lock = threading.RLock()
        self.db = sqlite3.connect(str(p), check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript(SCHEMA)
        if self.get_setting("approval_mode") is None:
            self._set("approval_mode", "demo")

    # -- plumbing ------------------------------------------------------------------------------------------------
    @contextmanager
    def tx(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                yield self.db
            except BaseException:
                self.db.execute("ROLLBACK")
                raise
            else:
                self.db.execute("COMMIT")

    def q(self, sql: str, *a: Any) -> list[sqlite3.Row]:
        with self._lock:
            return self.db.execute(sql, a).fetchall()

    def close(self) -> None:
        self.db.close()

    def _set(self, key: str, value: str) -> None:
        with self.tx() as db:
            db.execute(
                "INSERT INTO setting(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )

    def get_setting(self, key: str) -> str | None:
        r = self.q("SELECT value FROM setting WHERE key=?", key)
        return r[0][0] if r else None

    # -- audit ---------------------------------------------------------------------------------------------------
    def audit(
        self,
        db: sqlite3.Connection,
        actor: str,
        action: str,
        query_id: str | None = None,
        node_id: int | None = None,
        version: int | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        """Append-only, hash-chained (each row hashes the previous one, so edits to history are detectable)."""
        prev = db.execute("SELECT hash FROM audit ORDER BY id DESC LIMIT 1").fetchone()
        prev_hash = prev[0] if prev else "0" * 64
        mode = db.execute("SELECT value FROM setting WHERE key='approval_mode'").fetchone()[0]
        ts, dj = now_iso(), json.dumps(detail or {}, sort_keys=True)
        h = sql_hash("|".join([prev_hash, ts, actor, action, str(query_id), str(node_id), str(version), dj, mode]))
        db.execute(
            "INSERT INTO "
            "audit(ts,actor,action,query_id,node_id,version,detail,mode,prev_hash,hash) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (ts, actor, action, query_id, node_id, version, dj, mode, prev_hash, h),
        )

    def audit_log(self, limit: int = 200, query_id: str | None = None) -> list[dict[str, Any]]:
        rows = self.q(
            "SELECT * FROM audit WHERE (?1 IS NULL OR query_id=?1) ORDER BY id DESC LIMIT ?2", query_id, limit
        )
        return [dict(r) | {"detail": json.loads(r["detail"])} for r in rows]

    def audit_chain_ok(self) -> bool:
        prev = "0" * 64
        for r in self.q("SELECT * FROM audit ORDER BY id"):
            h = sql_hash(
                "|".join(
                    [
                        prev,
                        r["ts"],
                        r["actor"],
                        r["action"],
                        str(r["query_id"]),
                        str(r["node_id"]),
                        str(r["version"]),
                        r["detail"],
                        r["mode"],
                    ]
                )
            )
            if r["prev_hash"] != prev or r["hash"] != h:
                return False
            prev = h
        return True

    # -- settings ------------------------------------------------------------------------------------------------
    @property
    def approval_mode(self) -> str:
        return self.get_setting("approval_mode") or "demo"

    def set_approval_mode(self, mode: str, actor: str) -> None:
        if mode not in MODES:
            raise WorkflowError(f"approval mode must be one of {MODES}")
        with self.tx() as db:
            old = self.approval_mode
            db.execute("UPDATE setting SET value=? WHERE key='approval_mode'", (mode,))
            self.audit(db, actor, "set_approval_mode", detail={"from": old, "to": mode})

    # -- scope nodes ---------------------------------------------------------------------------------------------
    def add_node(self, level: str, key: str, name: str, parent_id: int | None, actor: str = "system") -> int:
        if level not in LEVELS:
            raise WorkflowError(f"unknown level {level}")
        with self.tx() as db:
            if level == "solution":
                if parent_id is not None:
                    raise WorkflowError("the solution node has no parent")
            else:
                par = db.execute("SELECT level FROM scope_node WHERE id=?", (parent_id,)).fetchone()
                if not par or LEVELS.index(par[0]) + 1 != LEVELS.index(level):
                    raise WorkflowError(
                        f"a {level} node must sit directly under a {LEVELS[LEVELS.index(level) - 1]} node"
                    )
            ex = db.execute(
                "SELECT id FROM scope_node WHERE level=? AND key=? AND parent_id IS ?", (level, key, parent_id)
            ).fetchone()
            if ex:
                return int(ex[0])
            cur = db.execute(
                "INSERT INTO scope_node(level,key,name,parent_id) VALUES(?,?,?,?)", (level, key, name, parent_id)
            )
            self.audit(
                db, actor, "add_scope", detail={"level": level, "key": key, "name": name, "parent_id": parent_id}
            )
            return int(cur.lastrowid or 0)

    def node(self, node_id: int) -> dict[str, Any]:
        r = self.q("SELECT * FROM scope_node WHERE id=?", node_id)
        if not r:
            raise KeyError(f"no scope node {node_id}")
        return dict(r[0])

    def find_node(self, level: str, key: str, parent_id: int | None = None) -> int | None:
        r = self.q(
            "SELECT id FROM scope_node WHERE level=? AND key=? AND (?3 IS NULL OR parent_id=?3)", level, key, parent_id
        )
        return int(r[0][0]) if r else None

    def children(self, node_id: int | None) -> list[dict[str, Any]]:
        return [dict(r) for r in self.q("SELECT * FROM scope_node WHERE parent_id IS ? ORDER BY id", node_id)]

    def tree(self) -> list[dict[str, Any]]:
        def build(n: dict[str, Any]) -> dict[str, Any]:
            return n | {"children": [build(c) for c in self.children(n["id"])]}

        return [build(n) for n in self.children(None)]

    def path(self, node_id: int) -> list[dict[str, Any]]:
        """Root .. node."""
        out: list[dict[str, Any]] = []
        cur: int | None = node_id
        while cur is not None:
            n = self.node(cur)
            out.append(n)
            cur = n["parent_id"]
        return out[::-1]

    def app_of(self, node_id: int) -> str | None:
        for n in self.path(node_id):
            if n["level"] == "application":
                return str(n["key"])
        return None

    def descendants(self, node_id: int) -> list[dict[str, Any]]:
        out = []
        for c in self.children(node_id):
            out.append(c)
            out.extend(self.descendants(c["id"]))
        return out

    # -- query specs ---------------------------------------------------------------------------------------------
    def spec_row(self, query_id: str) -> dict[str, Any]:
        r = self.q("SELECT * FROM query_spec WHERE query_id=?", query_id)
        if not r:
            raise KeyError(f"unknown query {query_id}")
        d = dict(r[0])
        for k in ("apps", "charts", "params", "columns", "tables"):
            d[k] = json.loads(d.pop(k + "_json"))
        return d

    def spec(self, query_id: str) -> qsafe.Spec:
        d = self.spec_row(query_id)
        return qsafe.Spec(
            query_id,
            tuple((c[0], c[1]) for c in d["columns"]),
            tuple(d["params"]),
            frozenset(d["tables"]),
            d["row_cap"],
        )

    def query_ids(self) -> list[str]:
        return [r[0] for r in self.q("SELECT query_id FROM query_spec ORDER BY query_id")]

    # -- seeding -------------------------------------------------------------------------------------------------
    def seed(self) -> None:
        """Create the hierarchy and a published solution-level version of every seed query (idempotent)."""
        sol = self.add_node("solution", *fin_seed.SOLUTION, None)
        parent = self.add_node("parent_app", *fin_seed.PARENT_APP, sol)
        for key, name in fin_seed.APPS:
            app = self.add_node("application", key, name, parent)
            cust = self.add_node("customer", *fin_seed.DEMO_CUSTOMER, app)
            for rk, rn in fin_seed.DEMO_ROLES:
                self.add_node("role", rk, rn, cust)
        for qid, s in fin_seed.SEED.items():
            if self.q("SELECT 1 FROM query_spec WHERE query_id=?", qid):
                continue
            v = qsafe.validate_sql(s["sql"], allowed_binds=tuple(s["params"]))
            with self.tx() as db:
                db.execute(
                    "INSERT INTO query_spec VALUES(?,?,?,?,?,?,?,?,?)",
                    (
                        qid,
                        s["title"],
                        s["owner_app"],
                        json.dumps(s["apps"]),
                        json.dumps(s["charts"]),
                        json.dumps(s["params"]),
                        json.dumps(s["columns"]),
                        json.dumps(sorted(v.tables)),
                        qsafe.DEFAULT_ROW_CAP,
                    ),
                )
                t = now_iso()
                db.execute(
                    "INSERT INTO "
                    "query_version(query_id,node_id,version,sql,status,author,approver,change_note,approval_note,"
                    "created_at,updated_at,submitted_at,approved_at,published_at,tested_hash,tested_ok) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)",
                    (
                        qid,
                        sol,
                        1,
                        s["sql"],
                        "published",
                        "seed",
                        "seed",
                        "seeded from export_fin_data.py",
                        "seed",
                        t,
                        t,
                        t,
                        t,
                        t,
                        sql_hash(s["sql"]),
                    ),
                )
                self.audit(db, "seed", "seed_query", qid, sol, 1, {"title": s["title"]})

    # -- resolver ------------------------------------------------------------------------------------------------
    def chain_for_context(self, app: str | None, customer: str | None, role: str | None) -> list[int]:
        """Node ids from the solution down to the deepest node that exists for the context (broadest first)."""
        sols = self.children(None)
        if not sols:
            return []
        chain = [sols[0]["id"]]
        parents = self.children(chain[0])
        app_id = None
        for p in parents:
            for a in self.children(p["id"]):
                if a["key"] == app:
                    chain.append(p["id"])
                    chain.append(a["id"])
                    app_id = a["id"]
        if app_id is None:
            return chain
        cust_id = None
        if customer is not None:
            cust_id = self.find_node("customer", str(customer), app_id)
            if cust_id:
                chain.append(cust_id)
        if cust_id and role is not None:
            role_id = self.find_node("role", role, cust_id)
            if role_id:
                chain.append(role_id)
        return chain

    def resolve_chain(self, query_id: str, chain: list[int]) -> Resolved:
        for node_id in reversed(chain):  # narrowest first
            r = self.q(
                "SELECT * FROM query_version WHERE query_id=? AND node_id=? AND status='published'", query_id, node_id
            )
            if r:
                n = self.node(node_id)
                return Resolved(query_id, r[0]["sql"], n["level"], node_id, n["name"], r[0]["version"], r[0]["id"])
        raise KeyError(f"no published definition of {query_id} on this path")

    def resolve(self, query_id: str, context: dict[str, Any]) -> Resolved:
        """Effective SQL for ``context = {app, customer, role}`` and the level it came from."""
        chain = self.chain_for_context(context.get("app"), context.get("customer"), context.get("role"))
        return self.resolve_chain(query_id, chain)

    def resolve_at(self, query_id: str, node_id: int) -> Resolved:
        return self.resolve_chain(query_id, [n["id"] for n in self.path(node_id)])

    def queries_for_node(self, node_id: int) -> list[str]:
        """Queries that are relevant at a node: all of them above application level, else the app's own."""
        app = self.app_of(node_id)
        out = []
        for qid in self.query_ids():
            if app is None or app in self.spec_row(qid)["apps"]:
                out.append(qid)
        return out

    def effective_list(self, node_id: int) -> list[dict[str, Any]]:
        rows = []
        for qid in self.queries_for_node(node_id):
            sp = self.spec_row(qid)
            try:
                r = self.resolve_at(qid, node_id)
            except KeyError:
                continue
            own = self.q(
                "SELECT status, version FROM query_version WHERE query_id=? AND node_id=? ORDER BY version DESC",
                qid,
                node_id,
            )
            open_v = next((x for x in own if x["status"] in OPEN_STATUSES), None)
            rows.append(
                {
                    "query_id": qid,
                    "title": sp["title"],
                    "charts": sp["charts"],
                    "apps": sp["apps"],
                    "level": r.level,
                    "from_node": r.node_name,
                    "from_node_id": r.node_id,
                    "version": r.version,
                    "inherited": r.node_id != node_id,
                    "open_status": open_v["status"] if open_v else None,
                }
            )
        return rows

    # -- impact --------------------------------------------------------------------------------------------------
    def contexts_under(self, node_id: int, query_id: str) -> list[dict[str, Any]]:
        """Every (app, customer, role) context below ``node_id`` for the apps that use ``query_id``."""
        apps = set(self.spec_row(query_id)["apps"])
        n = self.node(node_id)
        ctxs: list[dict[str, Any]] = []
        for nd in [n, *self.descendants(node_id)]:
            if nd["level"] not in ("application", "customer", "role"):
                continue
            path = self.path(nd["id"])
            app = next(p["key"] for p in path if p["level"] == "application")
            if app not in apps:
                continue
            cust = next((p["key"] for p in path if p["level"] == "customer"), None)
            role = next((p["key"] for p in path if p["level"] == "role"), None)
            ctxs.append({"node_id": nd["id"], "app": app, "customer": cust, "role": role, "level": nd["level"]})
        return ctxs

    def impact(self, query_id: str, node_id: int) -> dict[str, Any]:
        """What changes if the definition at ``node_id`` is (re)published (contexts whose SQL would come from it)."""
        affected, shadowed = [], []
        for c in self.contexts_under(node_id, query_id):
            chain = [p["id"] for p in self.path(c["node_id"])]
            sans = [x for x in chain if x != node_id]
            try:
                other = self.resolve_chain(query_id, sans)
                # a published version strictly narrower than node_id shadows this edit
                narrower = (
                    chain.index(other.node_id) > chain.index(node_id)
                    if node_id in chain and other.node_id in chain
                    else False
                )
            except KeyError:
                narrower = False
            (shadowed if narrower else affected).append(c)
        # app-level contexts under solution / parent_app nodes: apps that use the query but have no node are not listed
        apps_all = self.spec_row(query_id)["apps"]
        charts = self.spec_row(query_id)["charts"]
        apps_aff = sorted({c["app"] for c in affected})
        cust = sorted({str(c["customer"]) for c in affected if c["customer"]})
        roles = sorted({c["role"] for c in affected if c["role"]})
        node = self.node(node_id)
        return {
            "query_id": query_id,
            "node": node["name"],
            "level": node["level"],
            "queries": 1,
            "charts": len(charts),
            "chart_names": charts,
            "apps": apps_aff,
            "customers": cust,
            "roles": roles,
            "contexts_affected": len(affected),
            "contexts_shadowed": len(shadowed),
            "shadowed": [f"{c['app']}/{c['customer'] or '*'}/{c['role'] or '*'}" for c in shadowed],
            "apps_using_query": apps_all,
            "summary": (
                f"This edit changes 1 query ({len(charts)} chart(s)) at the {node['level'].replace('_', ' ')} level "
                f"'{node['name']}': {len(affected)} context(s) across {len(apps_aff)} application(s), "
                f"{len(cust)} customer(s) and {len(roles)} role(s)"
                + (f"; {len(shadowed)} context(s) keep a narrower override." if shadowed else ".")
            ),
        }

    # -- versions / workflow -------------------------------------------------------------------------------------
    def version(self, version_id: int) -> dict[str, Any]:
        r = self.q("SELECT * FROM query_version WHERE id=?", version_id)
        if not r:
            raise KeyError(f"no version {version_id}")
        return dict(r[0])

    def history(self, query_id: str, node_id: int) -> list[dict[str, Any]]:
        return [
            dict(r)
            for r in self.q(
                "SELECT * FROM query_version WHERE query_id=? AND node_id=? ORDER BY version DESC", query_id, node_id
            )
        ]

    def _check_scope(self, query_id: str, node_id: int) -> None:
        sp = self.spec_row(query_id)
        app = self.app_of(node_id)
        if app is not None and app not in sp["apps"]:
            raise WorkflowError(f"{query_id} is not used by the {app} application")

    def save_draft(self, query_id: str, node_id: int, sql: str, author: str, note: str = "") -> int:
        """Validate and store a draft at a node (one open version per query and node). Returns the version id."""
        self._check_scope(query_id, node_id)
        sp = self.spec(query_id)
        qsafe.validate_sql(sql, allowed_binds=sp.params, allowed_tables=sp.tables or None)  # raises SqlRejected
        with self.tx() as db:
            open_v = db.execute(
                "SELECT * FROM query_version WHERE query_id=? AND node_id=? "
                "AND status IN ('draft','in_review','approved')",
                (query_id, node_id),
            ).fetchone()
            t = now_iso()
            if open_v and open_v["status"] != "draft":
                raise WorkflowError(f"version {open_v['version']} is {open_v['status']}; reject it back to draft first")
            if open_v:
                db.execute(
                    "UPDATE query_version SET sql=?, change_note=?, author=?, "
                    "updated_at=?, tested_ok=0, tested_hash=NULL WHERE id=?",
                    (_text(sql), note, author, t, open_v["id"]),
                )
                self.audit(
                    db,
                    author,
                    "save_draft",
                    query_id,
                    node_id,
                    open_v["version"],
                    {"sql_hash": sql_hash(_text(sql)), "note": note},
                )
                return int(open_v["id"])
            nxt = db.execute(
                "SELECT COALESCE(MAX(version),0)+1 FROM query_version WHERE query_id=? AND node_id=?",
                (query_id, node_id),
            ).fetchone()[0]
            cur = db.execute(
                "INSERT INTO "
                "query_version(query_id,node_id,version,sql,status,author,change_note,created_at,updated_at) "
                "VALUES(?,?,?,?,'draft',?,?,?,?)",
                (query_id, node_id, nxt, _text(sql), author, note, t, t),
            )
            self.audit(
                db, author, "create_draft", query_id, node_id, nxt, {"sql_hash": sql_hash(_text(sql)), "note": note}
            )
            return int(cur.lastrowid or 0)

    def discard_draft(self, version_id: int, actor: str) -> None:
        with self.tx() as db:
            v = self._row(db, version_id)
            if v["status"] != "draft":
                raise WorkflowError("only a draft can be discarded")
            db.execute("DELETE FROM query_version WHERE id=?", (version_id,))
            self.audit(db, actor, "discard_draft", v["query_id"], v["node_id"], v["version"])

    def _row(self, db: sqlite3.Connection, version_id: int) -> sqlite3.Row:
        r = db.execute("SELECT * FROM query_version WHERE id=?", (version_id,)).fetchone()
        if not r:
            raise KeyError(f"no version {version_id}")
        return r

    def record_test(self, version_id: int, ok: bool, actor: str, detail: dict[str, Any] | None = None) -> None:
        with self.tx() as db:
            v = self._row(db, version_id)
            db.execute(
                "UPDATE query_version SET tested_ok=?, tested_hash=? WHERE id=?",
                (1 if ok else 0, sql_hash(v["sql"]), version_id),
            )
            self.audit(db, actor, "test_run", v["query_id"], v["node_id"], v["version"], {"ok": ok, **(detail or {})})

    def submit(self, version_id: int, actor: str) -> None:
        with self.tx() as db:
            v = self._row(db, version_id)
            if v["status"] != "draft":
                raise WorkflowError(f"only a draft can be submitted (this one is {v['status']})")
            if not (v["tested_ok"] and v["tested_hash"] == sql_hash(v["sql"])):
                raise WorkflowError("run a passing test run of the current SQL before submitting")
            db.execute(
                "UPDATE query_version SET status='in_review', submitted_at=?, updated_at=? WHERE id=?",
                (now_iso(), now_iso(), version_id),
            )
            self.audit(db, actor, "submit", v["query_id"], v["node_id"], v["version"])

    def approve(self, version_id: int, actor: str) -> None:
        with self.tx() as db:
            v = self._row(db, version_id)
            if v["status"] != "in_review":
                raise WorkflowError(f"only a version in review can be approved (this one is {v['status']})")
            mode = self.approval_mode
            note = None
            if actor == v["author"]:
                if mode == "strict":
                    raise WorkflowError("strict mode: the author cannot approve their own change")
                note = DEMO_NOTE
            t = now_iso()
            db.execute(
                "UPDATE query_version SET status='approved', approver=?, "
                "approved_at=?, approval_note=?, updated_at=? WHERE id=?",
                (actor, t, note, t, version_id),
            )
            self.audit(
                db,
                actor,
                "approve",
                v["query_id"],
                v["node_id"],
                v["version"],
                {"self_approval": actor == v["author"], "note": note or ""},
            )

    def reject(self, version_id: int, actor: str, note: str = "") -> None:
        with self.tx() as db:
            v = self._row(db, version_id)
            if v["status"] not in ("in_review", "approved"):
                raise WorkflowError("only a version in review or approved can be sent back to draft")
            db.execute(
                "UPDATE query_version SET status='draft', approver=NULL, approved_at=NULL, "
                "approval_note=NULL, tested_ok=0, updated_at=? WHERE id=?",
                (now_iso(), version_id),
            )
            self.audit(db, actor, "reject", v["query_id"], v["node_id"], v["version"], {"note": note})

    def publish(self, version_id: int, actor: str) -> None:
        with self.tx() as db:
            v = self._row(db, version_id)
            if v["status"] != "approved":
                raise WorkflowError(f"only an approved version can be published (this one is {v['status']})")
            t = now_iso()
            prev = db.execute(
                "SELECT id, version FROM query_version WHERE query_id=? AND node_id=? AND status='published'",
                (v["query_id"], v["node_id"]),
            ).fetchone()
            if prev:
                db.execute("UPDATE query_version SET status='retired', retired_at=? WHERE id=?", (t, prev["id"]))
            db.execute(
                "UPDATE query_version SET status='published', published_at=?, updated_at=? WHERE id=?",
                (t, t, version_id),
            )
            self.audit(
                db,
                actor,
                "publish",
                v["query_id"],
                v["node_id"],
                v["version"],
                {"retired_version": prev["version"] if prev else None, "approval_note": v["approval_note"] or ""},
            )

    def rollback(self, query_id: str, node_id: int, to_version: int, actor: str, note: str = "") -> int:
        """Re-publish the SQL of an earlier version as a NEW version (history is never rewritten)."""
        with self.tx() as db:
            old = db.execute(
                "SELECT * FROM query_version WHERE query_id=? AND node_id=? AND version=?",
                (query_id, node_id, to_version),
            ).fetchone()
            if not old:
                raise WorkflowError(f"no version {to_version} at this node")
            if old["status"] != "retired":
                raise WorkflowError(
                    f"version {to_version} is {old['status']}; only a retired version can be rolled back to"
                )
            sp = self.spec(query_id)
            qsafe.validate_sql(old["sql"], allowed_binds=sp.params, allowed_tables=sp.tables or None)
            t = now_iso()
            cur_pub = db.execute(
                "SELECT id, version FROM query_version WHERE query_id=? AND node_id=? AND status='published'",
                (query_id, node_id),
            ).fetchone()
            if cur_pub:
                db.execute("UPDATE query_version SET status='retired', retired_at=? WHERE id=?", (t, cur_pub["id"]))
            nxt = db.execute(
                "SELECT MAX(version)+1 FROM query_version WHERE query_id=? AND node_id=?", (query_id, node_id)
            ).fetchone()[0]
            db.execute(
                "INSERT INTO "
                "query_version(query_id,node_id,version,sql,status,author,approver,change_note,approval_note,created_at,updated_at,"
                "published_at,tested_hash,tested_ok,source_version) VALUES(?,?,?,?,'published',?,?,?,?,?,?,?,?,1,?)",
                (
                    query_id,
                    node_id,
                    nxt,
                    old["sql"],
                    actor,
                    actor,
                    note or f"rollback to v{to_version}",
                    "rollback",
                    t,
                    t,
                    t,
                    sql_hash(old["sql"]),
                    to_version,
                ),
            )
            self.audit(
                db,
                actor,
                "rollback",
                query_id,
                node_id,
                nxt,
                {"to_version": to_version, "replaced_version": cur_pub["version"] if cur_pub else None},
            )
            return int(nxt)

    def retire_override(self, query_id: str, node_id: int, actor: str) -> None:
        """Retire the published version at a node so the query falls through to the broader level."""
        with self.tx() as db:
            n = db.execute("SELECT level FROM scope_node WHERE id=?", (node_id,)).fetchone()
            if n and n["level"] == "solution":
                raise WorkflowError(
                    "the solution-level definition cannot be retired (nothing would be left to fall back to)"
                )
            cur = db.execute(
                "SELECT id, version FROM query_version WHERE query_id=? AND node_id=? AND status='published'",
                (query_id, node_id),
            ).fetchone()
            if not cur:
                raise WorkflowError("nothing is published at this node")
            db.execute("UPDATE query_version SET status='retired', retired_at=? WHERE id=?", (now_iso(), cur["id"]))
            self.audit(db, actor, "retire_override", query_id, node_id, cur["version"])


def open_default(path: str | os.PathLike[str] | None = None) -> Registry:
    """Open the registry and make sure it is seeded (safe to call repeatedly)."""
    reg = Registry(path)
    reg.seed()
    return reg


class QuerySource:
    """What the exporter reads: resolved SQL + spec for a fixed context, remembering what was used."""

    def __init__(self, registry: Registry, customer: str, role: str | None = None, app: str | None = None) -> None:
        self.registry, self.customer, self.role, self.app = registry, customer, role, app
        self.used: dict[str, dict[str, Any]] = {}

    def get(self, query_id: str) -> tuple[str, qsafe.Spec]:
        app = self.app or self.registry.spec_row(query_id)["owner_app"]
        r = self.registry.resolve(query_id, {"app": app, "customer": self.customer, "role": self.role})
        self.used[query_id] = {"level": r.level, "node": r.node_name, "version": r.version}
        return r.sql, self.registry.spec(query_id)
