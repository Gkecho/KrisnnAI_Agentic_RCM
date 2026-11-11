"""Tests for the analytics query registry / admin (tools/analytics/q*.py, query_admin.py).

Registry, resolver, validator and workflow tests run offline (in-memory SQLite). The tests marked DB read krisnnai_r2
(synthetic, read-only, SELECT only) and skip if it is unreachable.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import re
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from typing import Any

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "synthea"))
sys.path.insert(0, str(ROOT / "tools" / "synth"))
sys.path.insert(0, str(ROOT / "tools" / "analytics"))
import fin_seed  # noqa: E402
import qreg  # noqa: E402
import qsafe  # noqa: E402
import qsvc  # noqa: E402

_spec = importlib.util.spec_from_file_location("export_fin_data", ROOT / "tools" / "analytics" / "export_fin_data.py")
assert _spec and _spec.loader
if "export_fin_data" in sys.modules:
    fin = sys.modules["export_fin_data"]
else:
    fin = importlib.util.module_from_spec(_spec)
    sys.modules["export_fin_data"] = fin
    _spec.loader.exec_module(fin)

_qa_spec = importlib.util.spec_from_file_location("query_admin", ROOT / "tools" / "analytics" / "query_admin.py")
assert _qa_spec and _qa_spec.loader
qa = importlib.util.module_from_spec(_qa_spec)
sys.modules["query_admin"] = qa
_qa_spec.loader.exec_module(qa)


# ---------------------------------------------------------------------------------------------------------------------
# helpers / fixtures
# ---------------------------------------------------------------------------------------------------------------------
@pytest.fixture()
def reg():
    r = qreg.Registry(":memory:")
    r.seed()
    yield r
    r.close()


def node(r: qreg.Registry, level: str, key: str | None = None, app: str = "billing") -> int:
    if level == "solution":
        return r.children(None)[0]["id"]
    if level == "parent_app":
        return r.children(node(r, "solution"))[0]["id"]
    app_id = next(n["id"] for n in r.children(node(r, "parent_app")) if n["key"] == app)
    if level == "application":
        return app_id
    cust = r.find_node("customer", "1", app_id)
    assert cust
    if level == "customer":
        return cust
    role = r.find_node("role", key or "billing_manager", cust)
    assert role
    return role


def marked(qid: str, marker: str) -> str:
    return f"-- {marker}\n" + fin_seed.SEED[qid]["sql"]


def publish_at(r: qreg.Registry, qid: str, node_id: int, marker: str, actor: str = "maker") -> int:
    vid = r.save_draft(qid, node_id, marked(qid, marker), actor, marker)
    r.record_test(vid, True, actor)
    r.submit(vid, actor)
    r.approve(vid, actor)  # demo mode: maker may approve
    r.publish(vid, actor)
    return vid


def marker_of(res: qreg.Resolved) -> str:
    m = re.match(r"-- (\S+)", res.sql)
    return m.group(1) if m else "seed"


CTX = {"app": "billing", "customer": "1", "role": "billing_manager"}
QID = "billing.monthly"
LEVELS = ["solution", "parent_app", "application", "customer", "role"]


# ---------------------------------------------------------------------------------------------------------------------
# resolver
# ---------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("level", LEVELS)
def test_resolver_each_level_wins_when_it_is_the_only_override(level: str) -> None:
    r = qreg.Registry(":memory:")
    r.seed()
    if level != "solution":
        publish_at(r, QID, node(r, level), f"L-{level}")
    res = r.resolve(QID, CTX)
    assert res.level == level
    assert marker_of(res) == (f"L-{level}" if level != "solution" else "seed")
    r.close()


def test_resolver_narrowest_wins_and_falls_through(reg: qreg.Registry) -> None:
    assert reg.resolve(QID, CTX).level == "solution"
    publish_at(reg, QID, node(reg, "parent_app"), "P")
    assert reg.resolve(QID, CTX).level == "parent_app"
    publish_at(reg, QID, node(reg, "application"), "A")
    assert marker_of(reg.resolve(QID, CTX)) == "A"
    publish_at(reg, QID, node(reg, "customer"), "C")
    publish_at(reg, QID, node(reg, "role", "billing_manager"), "R")
    assert marker_of(reg.resolve(QID, CTX)) == "R"
    # a sibling role has no override -> falls through to the customer level
    assert marker_of(reg.resolve(QID, {**CTX, "role": "practice_manager"})) == "C"
    # no role in the context -> customer; unknown customer -> application; other app -> parent application
    assert marker_of(reg.resolve(QID, {"app": "billing", "customer": "1", "role": None})) == "C"
    assert marker_of(reg.resolve(QID, {"app": "billing", "customer": "2", "role": "billing_manager"})) == "A"
    assert reg.resolve("payers.list", {"app": "payments", "customer": "1", "role": None}).level == "solution"
    # retiring the role override falls through to the customer override
    reg.retire_override(QID, node(reg, "role", "billing_manager"), "maker")
    assert marker_of(reg.resolve(QID, CTX)) == "C"
    assert reg.resolve_at(QID, node(reg, "solution")).level == "solution"


def test_override_does_not_leak_sideways(reg: qreg.Registry) -> None:
    publish_at(reg, "payers.list", node(reg, "application", app="payments"), "PAY")
    assert reg.resolve("payers.list", {"app": "payments", "customer": "1", "role": None}).level == "application"
    assert reg.resolve("payers.list", {"app": "billing", "customer": "1", "role": None}).level == "solution"


def test_query_cannot_be_overridden_in_an_app_that_does_not_use_it(reg: qreg.Registry) -> None:
    with pytest.raises(qreg.WorkflowError):
        reg.save_draft("ar.matrix", node(reg, "application", app="billing"), fin_seed.SEED["ar.matrix"]["sql"], "maker")


# ---------------------------------------------------------------------------------------------------------------------
# impact preview
# ---------------------------------------------------------------------------------------------------------------------
def test_impact_counts_come_from_the_hierarchy(reg: qreg.Registry) -> None:
    sol = reg.impact(QID, node(reg, "solution"))  # billing-only query: billing app + 1 customer + 2 roles
    assert sol["queries"] == 1 and sol["contexts_affected"] == 4 and sol["apps"] == ["billing"]
    assert sol["customers"] == ["1"] and sol["roles"] == ["billing_manager", "practice_manager"]
    assert sol["charts"] == len(fin_seed.SEED[QID]["charts"])
    assert reg.impact(QID, node(reg, "role"))["contexts_affected"] == 1
    assert reg.impact(QID, node(reg, "customer"))["contexts_affected"] == 3
    everywhere = reg.impact("payers.list", node(reg, "solution"))  # used by all 7 pages
    assert everywhere["contexts_affected"] == 7 * 4 and len(everywhere["apps"]) == 7
    assert reg.impact("payers.list", node(reg, "application", app="payments"))["contexts_affected"] == 4


def test_impact_excludes_contexts_with_a_narrower_override(reg: qreg.Registry) -> None:
    publish_at(reg, QID, node(reg, "role", "billing_manager"), "R")
    imp = reg.impact(QID, node(reg, "solution"))
    assert imp["contexts_affected"] == 3 and imp["contexts_shadowed"] == 1
    assert imp["shadowed"] == ["billing/1/billing_manager"]
    assert "keep a narrower override" in imp["summary"]
    # a broader override does not shadow a narrower edit
    publish_at(reg, QID, node(reg, "application"), "A")
    assert reg.impact(QID, node(reg, "role", "practice_manager"))["contexts_affected"] == 1


# ---------------------------------------------------------------------------------------------------------------------
# validation (offline)
# ---------------------------------------------------------------------------------------------------------------------
OK_SQL = "SELECT payer_code AS payer_code FROM payer WHERE tenant_id = :tenant_id"


def reject(sql: str, match: str, **kw: Any) -> None:
    with pytest.raises(qsafe.SqlRejected, match=match):
        qsafe.validate_sql(sql, **kw)


def test_validator_accepts_all_seed_queries() -> None:
    for qid, s in fin_seed.SEED.items():
        v = qsafe.validate_sql(s["sql"], allowed_binds=tuple(s["params"]))
        assert "tenant_id" in v.binds, qid
        assert ";" not in v.canonical and "--" not in v.canonical, qid


@pytest.mark.parametrize(
    ("sql", "why"),
    [
        ("DROP TABLE payer", "only SELECT"),
        ("CREATE TABLE x AS SELECT 1", "only SELECT"),
        ("INSERT INTO payer SELECT * FROM payer", "only SELECT"),
        ("WITH d AS (DELETE FROM payer WHERE tenant_id = :tenant_id RETURNING 1) SELECT 1", "not allowed"),
        (
            "WITH d AS (UPDATE payer SET payer_name = 'x' WHERE tenant_id = :tenant_id RETURNING 1) SELECT 1",
            "not allowed",
        ),
        ("SELECT 1 INTO newtable FROM payer WHERE tenant_id = :tenant_id", "INTO"),
        (OK_SQL + " FOR UPDATE", "FOR"),
        ("SELECT payer_code FROM payer WHERE tenant_id = :tenant_id; DROP TABLE payer", "single statement"),
        ("SELECT 1; SELECT 2", "single statement"),
        ("SELECT pg_sleep(100) FROM payer WHERE tenant_id = :tenant_id", "function not allowed"),
        ("SELECT pg_read_file('/etc/passwd') FROM payer WHERE tenant_id = :tenant_id", "function not allowed"),
        ("SELECT 1 FROM payer WHERE tenant_id = :tenant_id AND x = '1'::regclass", "cast"),
        ("SELECT a FROM payer WHERE tenant_id = :tenant_id /* unterminated", "unterminated"),
        ("SELECT a FROM payer WHERE tenant_id = :tenant_id AND b = 'abc", "unterminated"),
        ('SELECT "payer_code" FROM payer WHERE tenant_id = :tenant_id', "quoted"),
        ("SELECT $$x$$ FROM payer WHERE tenant_id = :tenant_id", "dollar"),
        ("SELECT 1 FROM payer WHERE tenant_id = :tenant_id AND a = :evil", "bind parameter"),
        ("EXPLAIN ANALYZE SELECT 1", "only SELECT"),
        ("", "empty"),
    ],
)
def test_validator_rejects_dangerous_sql(sql: str, why: str) -> None:
    reject(sql, why)


def test_validator_requires_tenant_bind_on_every_table() -> None:
    reject("SELECT payer_code FROM payer", "tenant_id")
    reject("SELECT 1", ":tenant_id")
    reject("SELECT payer_code FROM payer WHERE payer_type = 'x'", "tenant_id")
    reject("SELECT payer_code FROM payer WHERE tenant_id = 1", "tenant_id")  # a literal is not the bind
    reject("SELECT payer_code FROM payer WHERE x = 1 OR tenant_id = :tenant_id", "tenant_id")  # OR defeats the filter
    # one filter is not enough for two tables
    reject(
        "SELECT p.payer_code FROM payer p JOIN claim c ON c.payer_id = p.payer_id WHERE p.tenant_id = :tenant_id",
        "every table",
    )
    reject("SELECT a.x FROM payer a, claim b WHERE a.tenant_id = :tenant_id", "every table")  # comma join is counted
    qsafe.validate_sql(
        "SELECT p.payer_code FROM payer p JOIN claim c ON c.payer_id = p.payer_id AND c.tenant_id = :tenant_id "
        "WHERE p.tenant_id = :tenant_id"
    )


def test_validator_table_allowlist_and_schema_names() -> None:
    allowed = frozenset({"payer"})
    qsafe.validate_sql(OK_SQL, allowed_tables=allowed)
    reject("SELECT x FROM patient WHERE tenant_id = :tenant_id", "table not allowed", allowed_tables=allowed)
    reject("SELECT x FROM pg_catalog.pg_user WHERE tenant_id = :tenant_id", "plain table", allowed_tables=allowed)
    reject("SELECT x FROM generate_series(1,10) WHERE tenant_id = :tenant_id", "not allowed", allowed_tables=allowed)
    reject(
        "SELECT x FROM (SELECT 1) a, patient b WHERE b.tenant_id = :tenant_id",
        "table not allowed",
        allowed_tables=allowed,
    )


def test_comments_cannot_smuggle_statements() -> None:
    v = qsafe.validate_sql(
        "SELECT payer_code FROM payer -- ; DROP TABLE payer\nWHERE tenant_id = :tenant_id /* ; DELETE */"
    )
    assert "DROP" not in v.canonical.upper() and "DELETE" not in v.canonical.upper()
    pg = qsafe.to_psycopg(v)
    assert "--" not in pg and "/*" not in pg and "%(tenant_id)s" in pg
    # the stored/edited text may keep comments, but a forbidden word is rejected even if it is the only thing in a comment's way
    reject("SELECT 1 FROM payer WHERE tenant_id = :tenant_id /* x */ ; /* y */ DELETE FROM payer", "single statement")


def test_percent_signs_are_escaped_for_the_driver() -> None:
    v = qsafe.validate_sql(
        "SELECT COUNT(*) AS c FROM payer WHERE tenant_id = :tenant_id AND payer_name LIKE 'A%' AND 5 % 2 = 1"
    )
    pg = qsafe.to_psycopg(v)
    assert "'A%%'" in pg and "%(tenant_id)s" in pg and " %% " in pg


SPEC = qsafe.Spec("t", (("payer_code", "text"), ("n", "int"), ("amt", "money")), ("tenant_id",), frozenset({"payer"}))


def test_result_columns_must_match_the_contract() -> None:
    qsafe.check_columns(SPEC, ["payer_code", "n", "amt"])
    with pytest.raises(qsafe.ResultRejected, match="exactly"):
        qsafe.check_columns(SPEC, ["payer_code", "n", "amt", "extra"])  # extra column
    with pytest.raises(qsafe.ResultRejected, match="exactly"):
        qsafe.check_columns(SPEC, ["payer_code", "n"])  # missing column
    with pytest.raises(qsafe.ResultRejected, match="exactly"):
        qsafe.check_columns(SPEC, ["n", "payer_code", "amt"])  # wrong order (builders read by position)


@pytest.mark.parametrize(
    "bad",
    ["patient_id", "claim_id", "member_number", "subscriber", "dob", "ssn", "first_name", "mrn", "foo_id", "email"],
)
def test_forbidden_person_level_column_names(bad: str) -> None:
    spec = qsafe.Spec("t", ((bad, "text"),))
    with pytest.raises(qsafe.ResultRejected, match="identifier"):
        qsafe.check_columns(spec, [bad])


def test_money_must_be_decimal_never_float() -> None:
    from decimal import Decimal

    qsafe.check_rows(SPEC, [("A", 1, Decimal("1.50")), ("B", None, None)])
    with pytest.raises(qsafe.ResultRejected, match="Decimal"):
        qsafe.check_rows(SPEC, [("A", 1, 1.5)])
    with pytest.raises(qsafe.ResultRejected, match="must be int"):
        qsafe.check_rows(SPEC, [("A", "1", Decimal("1"))])
    with pytest.raises(qsafe.ResultRejected, match="identifier"):
        qsafe.check_rows(SPEC, [("123-45-6789", 1, Decimal("1"))])
    with pytest.raises(qsafe.ResultRejected, match="identifier"):
        qsafe.check_rows(SPEC, [("0b9f1a0e-1111-4222-8333-444455556666", 1, Decimal("1"))])


def test_save_draft_rejects_bad_sql_and_stores_nothing(reg: qreg.Registry) -> None:
    n = node(reg, "application")
    for bad in ["DROP TABLE payer", OK_SQL.replace("tenant_id = :tenant_id", "1 = 1"), "SELECT 1; SELECT 2"]:
        with pytest.raises(qsafe.SqlRejected):
            reg.save_draft(QID, n, bad, "maker")
    assert reg.history(QID, n) == []


def test_run_query_refuses_a_connection_that_is_not_read_only() -> None:
    class Cur:
        def __enter__(self) -> Cur:
            return self

        def __exit__(self, *a: Any) -> None:
            return None

        def execute(self, *a: Any) -> None:
            self.last = a

        def fetchone(self) -> tuple[str]:
            return ("off",)

    class Conn:
        def cursor(self) -> Cur:
            return Cur()

        def rollback(self) -> None:
            pass

    with pytest.raises(qsafe.SqlRejected, match="not read-only"):
        qsafe.run_query(Conn(), SPEC, OK_SQL, {"tenant_id": 1})


# ---------------------------------------------------------------------------------------------------------------------
# workflow state machine, rollback, audit
# ---------------------------------------------------------------------------------------------------------------------
def draft(r: qreg.Registry, actor: str = "maker", marker: str = "X") -> int:
    return r.save_draft(QID, node(r, "application"), marked(QID, marker), actor, "change")


def test_happy_path_draft_to_published(reg: qreg.Registry) -> None:
    vid = draft(reg)
    assert reg.version(vid)["status"] == "draft"
    with pytest.raises(qreg.WorkflowError, match="passing test run"):
        reg.submit(vid, "maker")  # no test run yet
    reg.record_test(vid, True, "maker")
    reg.submit(vid, "maker")
    assert reg.version(vid)["status"] == "in_review"
    with pytest.raises(qreg.WorkflowError):
        reg.publish(vid, "maker")  # not approved yet
    reg.approve(vid, "maker")
    reg.publish(vid, "maker")
    assert reg.version(vid)["status"] == "published"
    assert reg.resolve(QID, CTX).level == "application"


def test_failed_or_stale_test_blocks_submit(reg: qreg.Registry) -> None:
    vid = draft(reg)
    reg.record_test(vid, False, "maker")
    with pytest.raises(qreg.WorkflowError):
        reg.submit(vid, "maker")
    reg.record_test(vid, True, "maker")
    reg.save_draft(QID, node(reg, "application"), marked(QID, "changed again"), "maker")  # edit resets the test
    with pytest.raises(qreg.WorkflowError, match="passing test run"):
        reg.submit(vid, "maker")


def test_illegal_transitions(reg: qreg.Registry) -> None:
    vid = draft(reg)
    with pytest.raises(qreg.WorkflowError):
        reg.approve(vid, "other")  # draft cannot be approved
    with pytest.raises(qreg.WorkflowError):
        reg.publish(vid, "other")
    reg.record_test(vid, True, "maker")
    reg.submit(vid, "maker")
    with pytest.raises(qreg.WorkflowError):
        reg.submit(vid, "maker")  # already in review
    with pytest.raises(qreg.WorkflowError, match="reject it back"):
        draft(reg)  # in review: no edits until sent back
    reg.reject(vid, "other", "needs work")
    assert reg.version(vid)["status"] == "draft" and reg.version(vid)["tested_ok"] == 0
    with pytest.raises(qreg.WorkflowError):
        reg.reject(vid, "other")


def test_default_mode_is_demo_and_self_approval_is_marked(reg: qreg.Registry) -> None:
    assert reg.approval_mode == "demo"
    vid = draft(reg)
    reg.record_test(vid, True, "maker")
    reg.submit(vid, "maker")
    reg.approve(vid, "maker")
    v = reg.version(vid)
    assert v["approver"] == "maker" and v["approval_note"] == "single-user demo"
    approve = next(a for a in reg.audit_log() if a["action"] == "approve")
    assert (
        approve["mode"] == "demo"
        and approve["detail"]["self_approval"] is True
        and approve["detail"]["note"] == "single-user demo"
    )


def test_strict_mode_refuses_self_approval_but_allows_a_second_person(reg: qreg.Registry) -> None:
    reg.set_approval_mode("strict", "admin")
    vid = draft(reg, "maker")
    reg.record_test(vid, True, "maker")
    reg.submit(vid, "maker")
    with pytest.raises(qreg.WorkflowError, match="strict mode"):
        reg.approve(vid, "maker")
    assert reg.version(vid)["status"] == "in_review"
    reg.approve(vid, "checker")
    assert reg.version(vid)["approver"] == "checker" and reg.version(vid)["approval_note"] is None
    reg.publish(vid, "checker")
    assert reg.version(vid)["status"] == "published"
    with pytest.raises(qreg.WorkflowError):
        reg.set_approval_mode("whatever", "admin")


def test_rollback_republishes_old_sql_as_a_new_version(reg: qreg.Registry) -> None:
    app = node(reg, "application")
    publish_at(reg, QID, app, "one")
    publish_at(reg, QID, app, "two")
    assert marker_of(reg.resolve(QID, CTX)) == "two"
    hist = {h["version"]: h["status"] for h in reg.history(QID, app)}
    assert hist == {1: "retired", 2: "published"}
    new = reg.rollback(QID, app, 1, "maker")
    assert new == 3 and marker_of(reg.resolve(QID, CTX)) == "one"
    h3 = next(h for h in reg.history(QID, app) if h["version"] == 3)
    assert h3["source_version"] == 1 and h3["status"] == "published"
    assert {h["version"]: h["status"] for h in reg.history(QID, app)} == {1: "retired", 2: "retired", 3: "published"}
    with pytest.raises(qreg.WorkflowError, match="only a retired"):
        reg.rollback(QID, app, 3, "maker")
    with pytest.raises(qreg.WorkflowError):
        reg.rollback(QID, app, 99, "maker")
    # rolling back at the solution node works too and never loses the seed
    sol = node(reg, "solution")
    publish_at(reg, QID, sol, "sol2")
    reg.rollback(QID, sol, 1, "maker")
    assert reg.resolve_at(QID, sol).sql.startswith("SELECT TO_CHAR")
    with pytest.raises(qreg.WorkflowError):
        reg.retire_override(QID, sol, "maker")


def test_audit_log_records_every_step_and_is_tamper_evident(reg: qreg.Registry) -> None:
    vid = draft(reg)
    reg.record_test(vid, True, "maker", {"row_count": 37})
    reg.submit(vid, "maker")
    reg.approve(vid, "maker")
    reg.publish(vid, "maker")
    actions = [a["action"] for a in reversed(reg.audit_log(500, QID))]
    assert actions[-5:] == ["create_draft", "test_run", "submit", "approve", "publish"]
    pub = next(a for a in reg.audit_log() if a["action"] == "publish")
    assert pub["actor"] == "maker" and pub["version"] == 1 and pub["query_id"] == QID and pub["ts"].endswith("Z")
    assert reg.audit_chain_ok()
    reg.db.execute("UPDATE audit SET actor='someone-else' WHERE action='submit'")  # tamper
    assert not reg.audit_chain_ok()


def test_registry_is_separate_from_the_r2_model_and_in_var() -> None:
    assert qreg.DEFAULT_PATH == ROOT / "var" / "analytics_registry.sqlite"
    assert "/var/" in (ROOT / ".gitignore").read_text()
    model = (ROOT / "docs" / "data_model" / "r2_model.json").read_text(encoding="utf-8")
    assert "query_version" not in model and "scope_node" not in model


# ---------------------------------------------------------------------------------------------------------------------
# exporter wiring (offline)
# ---------------------------------------------------------------------------------------------------------------------
def test_exporter_uses_exactly_the_seeded_query_ids() -> None:
    text = (ROOT / "tools" / "analytics" / "export_fin_data.py").read_text(encoding="utf-8")
    used = set(re.findall(r'db\.rows\(\s*"([a-z_.]+)"', text))
    assert used == set(fin_seed.SEED)
    assert "psycopg2" not in text and "%(t)s" not in text


# ---------------------------------------------------------------------------------------------------------------------
# HTTP layer (offline): binding, headers, no secrets
# ---------------------------------------------------------------------------------------------------------------------
def test_server_defaults_to_loopback_8780_not_the_other_apps_ports() -> None:
    assert (qa.HOST, qa.PORT) == ("127.0.0.1", 8780) and qa.PORT not in (8765, 8766)


@pytest.fixture()
def http_server(reg: qreg.Registry):
    class NoDb(qsvc.Service):
        def __init__(self, r: qreg.Registry) -> None:
            super().__init__(r, conn_factory=lambda: (_ for _ in ()).throw(RuntimeError("no db in this test")))

    app = qa.App(NoDb(reg))
    srv = ThreadingHTTPServer(("127.0.0.1", 0), qa.make_handler(app))
    port = srv.server_address[1]
    old = set(qa.EXPECTED_HOSTS)
    qa.EXPECTED_HOSTS.add(f"127.0.0.1:{port}")
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield port
    srv.shutdown()
    srv.server_close()
    qa.EXPECTED_HOSTS.intersection_update(old)


def call(port: int, path: str, body: dict | None = None, headers: dict | None = None) -> tuple[int, dict | bytes]:
    h = dict(headers or {})
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        h.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:  # noqa: S310
            raw = r.read()
            return r.status, (json.loads(raw) if r.headers["Content-Type"].startswith("application/json") else raw)
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_http_api_basic_flow_and_csrf_guard(http_server: int) -> None:
    port = http_server
    code, tree = call(port, "/api/tree")
    assert code == 200 and tree["approval_mode"] == "demo" and tree["tree"][0]["level"] == "solution"
    code, page = call(port, "/")
    assert code == 200 and b"Query Admin" in page
    # POST without the admin header / JSON content type is refused (another web page cannot drive this app)
    assert call(port, "/api/mode", {"mode": "strict"})[0] == 403
    assert call(port, "/api/mode", {"mode": "strict"}, {"X-Admin-Request": "1", "Content-Type": "text/plain"})[0] == 403
    # wrong Host header (DNS rebinding) is refused
    assert call(port, "/api/tree", headers={"Host": "evil.example:8780"})[0] == 403
    ok = {"X-Admin-Request": "1"}
    app_node = next(n for n in tree["tree"][0]["children"][0]["children"] if n["key"] == "billing")["id"]
    code, d = call(
        port, "/api/draft", {"query_id": QID, "node_id": app_node, "sql": "DROP TABLE payer", "actor": "x"}, ok
    )
    assert code == 400 and "only SELECT" in d["error"]
    code, d = call(
        port, "/api/draft", {"query_id": QID, "node_id": app_node, "sql": marked(QID, "http"), "actor": "x"}, ok
    )
    assert code == 200
    code, d = call(port, "/api/submit", {"version_id": d["version_id"], "actor": "x"}, ok)
    assert code == 400 and "test run" in d["error"]
    code, q = call(port, f"/api/queries?node={app_node}")
    row = next(r for r in q["queries"] if r["query_id"] == QID)
    assert row["level"] == "solution" and row["inherited"] and row["open_status"] == "draft"
    assert call(port, "/api/nothing")[0] == 404


def test_errors_never_expose_connection_details() -> None:
    msg = qsvc.safe_error(
        RuntimeError('connection to server at "db.example.com", port 5432 failed: password authentication failed')
    )
    assert "example" not in msg and "password" not in msg and "hidden" in msg
    assert "boom" in qsvc.safe_error(ValueError("boom"))


def test_registry_file_and_audit_do_not_contain_the_db_password(reg: qreg.Registry) -> None:
    try:
        from core import load_env

        pw = load_env().get("PGPASSWORD", "")
    except Exception:  # noqa: BLE001
        pytest.skip("no env config on this machine")
    if len(pw) < 6:
        pytest.skip("no password configured")
    dump = "\n".join(reg.db.iterdump())
    assert pw not in dump
    assert pw not in (ROOT / "tools" / "analytics" / "admin_ui" / "index.html").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------------------------------------------------
# DB tests (krisnnai_r2, SELECT only, read-only connection)
# ---------------------------------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def conn():
    try:
        c = fin.open_connection()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"krisnnai_r2 not reachable: {type(exc).__name__}")
    yield c
    c.close()


def run(conn: Any, qid: str, sql: str, tenant: int = 1) -> qsafe.QueryResult:
    return qsafe.run_query(
        conn, qsafe.Spec(qid, **_spec_kwargs(qid)), sql, {"tenant_id": tenant, "asof": fin.AS_OF, "d": fin.AS_OF}
    )


def _spec_kwargs(qid: str) -> dict[str, Any]:
    r = qreg.Registry(":memory:")
    r.seed()
    sp = r.spec(qid)
    r.close()
    return {"columns": sp.columns, "params": sp.params, "tables": sp.tables}


def test_db_writes_are_impossible_on_the_read_only_connection(conn) -> None:
    import psycopg2

    with pytest.raises(psycopg2.errors.ReadOnlySqlTransaction):
        with conn.cursor() as cur:
            cur.execute("CREATE TEMP TABLE should_not_exist(a int)")  # a write; the server refuses it
    conn.rollback()
    with conn.cursor() as cur:
        cur.execute("SHOW transaction_read_only")
        assert cur.fetchone()[0] == "on"
    conn.rollback()
    # and a "SELECT" that smuggles a write never reaches the server: the validator stops it first
    with pytest.raises(qsafe.SqlRejected):
        run(conn, "payers.list", "WITH w AS (INSERT INTO payer(payer_code) VALUES ('x') RETURNING 1) SELECT 1")


def test_db_seed_queries_run_and_match_their_contract(conn) -> None:
    r = qreg.Registry(":memory:")
    r.seed()
    for qid in ("payers.list", "headline.claims", "payments.tie_out", "billing.top_cpt"):
        res = run(conn, qid, r.resolve_at(qid, node(r, "solution")).sql)
        assert res.columns == r.spec(qid).column_names and res.rows, qid
    assert run(conn, "headline.claims", fin_seed.SEED["headline.claims"]["sql"]).rows[0][0] == 119_941
    r.close()


def test_db_extra_or_forbidden_columns_are_rejected(conn) -> None:
    base = fin_seed.SEED["payers.list"]["sql"]
    with pytest.raises(qsafe.ResultRejected, match="exactly"):
        run(
            conn,
            "payers.list",
            base.replace("payer_type AS payer_type", "payer_type AS payer_type, payer_code AS extra"),
        )
    with pytest.raises(qsafe.ResultRejected, match="exactly"):
        run(conn, "payers.list", base.replace("payer_name AS payer_name, ", ""))
    sneaky = "SELECT payer_code AS payer_code, payer_name AS payer_name, payer_type AS patient_id FROM payer WHERE tenant_id = :tenant_id"
    with pytest.raises(qsafe.ResultRejected, match="identifier|exactly"):
        run(conn, "payers.list", sneaky)
    # a table that is not part of this chart's contract is rejected before it runs
    with pytest.raises(qsafe.SqlRejected, match="table not allowed"):
        run(
            conn,
            "payers.list",
            "SELECT payer_code AS payer_code, payer_name AS payer_name, payer_type AS payer_type FROM patient WHERE tenant_id = :tenant_id",
        )


def test_db_money_columns_must_stay_decimal(conn) -> None:
    sql = fin_seed.SEED["payments.tie_out"]["sql"]
    floaty = re.sub(
        r"^SELECT\n\s+\(SELECT COALESCE\(SUM\(posted_amount\), 0\)",
        "SELECT\n  (SELECT COALESCE(SUM(posted_amount), 0)::double precision",
        sql,
    )
    assert floaty != sql
    with pytest.raises(qsafe.ResultRejected, match="Decimal"):
        run(conn, "payments.tie_out", floaty)


def test_db_row_cap_and_timeout_are_enforced(conn) -> None:
    sql = fin_seed.SEED["billing.monthly"]["sql"]
    spec = qsafe.Spec("billing.monthly", **_spec_kwargs("billing.monthly"))
    with pytest.raises(qsafe.ResultRejected, match="row cap"):
        qsafe.run_query(conn, spec, sql, {"tenant_id": 1, "asof": fin.AS_OF}, row_cap=5)
    heavy = fin_seed.SEED["flow.links"]["sql"]
    import psycopg2

    with pytest.raises(psycopg2.errors.QueryCanceled):
        qsafe.run_query(
            conn,
            qsafe.Spec("flow.links", **_spec_kwargs("flow.links")),
            heavy,
            {"tenant_id": 1, "asof": fin.AS_OF},
            timeout_ms=5,
        )
    with conn.cursor() as cur:  # the connection is still usable afterwards
        cur.execute("SELECT 1")
    conn.rollback()


def test_db_cross_tenant_leak_every_seed_query_is_empty_for_another_tenant(conn) -> None:
    r = qreg.Registry(":memory:")
    r.seed()
    for qid in r.query_ids():
        sql = r.resolve_at(qid, node(r, "solution")).sql
        assert qsafe.probe_other_tenant(conn, r.spec(qid), sql, {"tenant_id": 1, "asof": fin.AS_OF, "d": fin.AS_OF}), (
            qid
        )
        assert run(conn, qid, sql, tenant=1).rows or qid in ()  # and tenant 1 still gets its own data
    r.close()


def test_db_test_run_diff_and_probe_through_the_service(conn) -> None:
    r = qreg.Registry(":memory:")
    r.seed()
    svc = qsvc.Service(r, conn_factory=fin.open_connection)
    app = node(r, "application")
    same = r.save_draft(QID, app, marked(QID, "same"), "maker")
    res = svc.test_run(same, "maker")
    assert res["ok"] and res["baseline"]["identical"] and res["row_count"] == 37 and res["tenant_probe_ok"]
    assert r.version(same)["tested_ok"] == 1
    # an edit that changes the output shows up as a diff against the published version
    changed = marked(QID, "changed").replace(
        "service_date_from <= :asof", "service_date_from <= :asof AND claim_status <> 'denied'"
    )
    r.save_draft(QID, app, changed, "maker")
    res = svc.test_run(same, "maker")
    assert (
        res["ok"]
        and not res["baseline"]["identical"]
        and res["baseline"]["rows_added"] > 0
        and res["baseline"]["rows_removed"] > 0
    )
    assert res["baseline"]["level"] == "solution"
    # a draft that breaks the contract fails the test run and cannot be submitted
    r.save_draft(QID, app, marked(QID, "bad").replace("COUNT(*) AS claims, ", ""), "maker")
    bad = svc.test_run(same, "maker")
    assert not bad["ok"] and "exactly" in bad["error"]
    with pytest.raises(qreg.WorkflowError):
        r.submit(same, "maker")
    r.close()


def test_db_override_changes_the_export_input_and_other_levels_are_untouched(conn) -> None:
    r = qreg.Registry(":memory:")
    r.seed()
    publish_at(r, "billing.top_cpt", node(r, "application"), "top5")
    vid = r.save_draft(
        "billing.top_cpt",
        node(r, "role", "billing_manager"),
        fin_seed.SEED["billing.top_cpt"]["sql"].replace("LIMIT 12", "LIMIT 3"),
        "maker",
    )
    r.record_test(vid, True, "maker")
    r.submit(vid, "maker")
    r.approve(vid, "maker")
    r.publish(vid, "maker")
    rows_for = lambda role: fin.Db(conn, 1, qreg.QuerySource(r, "1", role)).rows("billing.top_cpt")  # noqa: E731
    assert len(rows_for("billing_manager")) == 3
    assert len(rows_for("practice_manager")) == 12 and len(rows_for(None)) == 12
    src = qreg.QuerySource(r, "1", "billing_manager")
    fin.Db(conn, 1, src).rows("billing.top_cpt")
    assert src.used["billing.top_cpt"]["level"] == "role"
    r.close()


def test_db_publish_site_is_deterministic_and_matches_the_exporter(conn, tmp_path) -> None:
    r = qreg.Registry(":memory:")
    r.seed()
    svc = qsvc.Service(r, conn_factory=fin.open_connection)
    a = svc.publish_site("maker", out_path=tmp_path / "a" / "fin_data.js")
    b = svc.publish_site("maker", out_path=tmp_path / "b" / "fin_data.js")
    strip = lambda p: re.sub(rb'"generated_at":"[^"]*"', b'"generated_at":""', pathlib.Path(p).read_bytes())  # noqa: E731
    assert strip(a["path"]) == strip(b["path"]) and a["sha256"] == b["sha256"]
    body = pathlib.Path(a["path"]).read_text(encoding="utf-8")
    assert body.startswith("window.KRISNNAI_FIN = {") and '"tenant_id":1' in body
    assert all(v["level"] == "solution" for v in a["queries"].values()) and len(a["queries"]) == len(fin_seed.SEED)
    audits = [x for x in r.audit_log() if x["action"] == "publish_site_data"]
    assert len(audits) == 2 and audits[0]["detail"]["sha256_without_generated_at"] == a["sha256"]
    assert "site" in a["next_step"] and "deploy" in a["next_step"]
    # nothing was written anywhere else (no site folder copy)
    assert sorted(p.name for p in tmp_path.rglob("*") if p.is_file()) == ["fin_data.js", "fin_data.js"]
    r.close()
