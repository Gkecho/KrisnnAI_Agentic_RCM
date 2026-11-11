"""Tests for tools/analytics/export_fin_data.py. They read krisnnai_r2 (synthetic, read-only) and skip if it is unreachable."""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import pathlib
import re
import sys
from decimal import Decimal
from typing import Any

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "synthea"))
_spec = importlib.util.spec_from_file_location("export_fin_data", ROOT / "tools" / "analytics" / "export_fin_data.py")
assert _spec and _spec.loader
fin = importlib.util.module_from_spec(_spec)
sys.modules["export_fin_data"] = fin
_spec.loader.exec_module(fin)
sys.path.insert(0, str(ROOT / "tools" / "analytics"))
import fin_seed as seed  # noqa: E402

AS_OF = dt.date(2026, 11, 6)


@pytest.fixture(scope="module")
def conn():
    try:
        c = fin.open_connection()
    except Exception as exc:  # no network / no config on this machine
        pytest.skip(f"krisnnai_r2 not reachable: {type(exc).__name__}")
    yield c
    c.close()


@pytest.fixture(scope="module")
def data(conn) -> dict[str, Any]:
    return fin.build(conn)


def one(conn, sql: str, *params: Any) -> tuple[Any, ...]:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def D(s: str) -> Decimal:
    return Decimal(s)


def test_connection_is_read_only(conn) -> None:
    assert one(conn, "SHOW transaction_read_only")[0] == "on"


def test_known_facts(data) -> None:
    h = data["headline"]
    assert h["claims"] == 119_941
    assert D(h["owed_payer"]) == D("3721240.00")
    assert D(h["owed_patient"]) == D("1354409.77")
    assert 39_700_000 < D(h["charged"]) < 39_800_000
    assert data["meta"]["tenant_id"] == 1 and data["meta"]["as_of"] == "2026-11-06"
    assert len(data["asof"]) == 13 and data["asof"][-1] == "2026-11-06"


def _check_sankey(s: dict[str, Any]) -> None:
    inflow: dict[str, Decimal] = {}
    outflow: dict[str, Decimal] = {}
    for link in s["links"]:
        v = D(link["value"])
        assert v >= 0
        outflow[link["source"]] = outflow.get(link["source"], Decimal(0)) + v
        inflow[link["target"]] = inflow.get(link["target"], Decimal(0)) + v
    for node in s["nodes"]:
        n = node["id"]
        if n == "charged":
            assert n not in inflow
        elif n in ("patient_share", "denied"):
            assert inflow.get(n, Decimal(0)) == outflow.get(n, Decimal(0)), n  # exact, to the cent
        else:
            assert n not in outflow, f"terminal node {n} has outflow"


def test_sankey_inflow_equals_outflow_all(data) -> None:
    _check_sankey(data["flow"]["all"])


def test_sankey_inflow_equals_outflow_each_payer(data) -> None:
    assert set(data["flow"]["by_payer"]) == {p["code"] for p in data["payers"]}
    for s in data["flow"]["by_payer"].values():
        _check_sankey(s)


def test_sankey_charged_matches_headline_and_payers_sum_to_all(data) -> None:
    def out_of_charged(s: dict[str, Any]) -> Decimal:
        return sum((D(link["value"]) for link in s["links"] if link["source"] == "charged"), Decimal(0))

    assert out_of_charged(data["flow"]["all"]) == D(data["headline"]["charged"])
    assert sum(out_of_charged(s) for s in data["flow"]["by_payer"].values()) == D(data["headline"]["charged"])


def test_triangle_rows_reconcile_to_charged(data) -> None:
    rows = data["lag"]["rows"]
    assert len(data["lag"]["cols"]) == 7 and rows
    for r in rows:
        total = sum((D(c) for c in r["cells"]), Decimal(0)) + D(r["contractual"]) + D(r["denied_final"])
        assert total == D(r["charged"]), r["month"]
        assert D(r["cells"][6]) >= 0, r["month"]  # unpaid is never negative
        for cells in r["by_payer"].values():
            assert len(cells) == 7
    assert sum((D(r["charged"]) for r in rows), Decimal(0)) == D(data["headline"]["charged"])


def test_payments_tie_out_ok(data) -> None:
    t = data["payments"]["tie_out"]
    assert t["ok"] is True
    assert t["payments_total"] == t["remittance_total"] == t["ledger_total"]
    monthly_payer = sum((D(m["payer_paid"]) for m in data["payments"]["monthly"]), Decimal(0))
    assert monthly_payer == D(t["ledger_total"])


def test_headline_matches_direct_sql(conn, data) -> None:
    h = data["headline"]
    claims, charged = one(conn, "SELECT COUNT(*), SUM(total_charge) FROM claim WHERE tenant_id = 1")
    assert (h["claims"], D(h["charged"])) == (claims, charged)
    paid_payer, paid_patient = one(
        conn,
        "SELECT SUM(amount) FILTER (WHERE responsible_party = 'payer'), "
        "SUM(amount) FILTER (WHERE responsible_party = 'patient') "
        "FROM ledger_entry WHERE tenant_id = 1 AND transaction_type = 'payment'",
    )
    assert (D(h["paid_payer"]), D(h["paid_patient"])) == (paid_payer, paid_patient)
    owed = dict(
        conn_rows(
            conn, "SELECT responsible_party, SUM(balance_effect) FROM ledger_entry WHERE tenant_id = 1 GROUP BY 1"
        )
    )
    assert (D(h["owed_payer"]), D(h["owed_patient"])) == (owed["payer"], owed["patient"])
    (denied,) = one(conn, "SELECT SUM(denied_amount) FROM denial WHERE tenant_id = 1")
    assert D(h["denied"]) == denied
    status = dict(conn_rows(conn, "SELECT claim_status, COUNT(*) FROM claim WHERE tenant_id = 1 GROUP BY 1"))
    got = {
        k: sum(m["status"][k] for m in data["billing"]["monthly"]) for k in ("paid", "partial", "submitted", "denied")
    }
    assert got == {k: status[k] for k in got}


def conn_rows(conn, sql: str) -> list[tuple[Any, ...]]:
    with conn.cursor() as cur:
        cur.execute(sql)
        return list(cur.fetchall())


def test_ar_total_per_asof_equals_ledger(conn, data) -> None:
    assert len(data["ar"]["by_asof"]) == 13
    for d, block in data["ar"]["by_asof"].items():
        (ledger,) = one(
            conn, "SELECT SUM(balance_effect) FROM ledger_entry WHERE tenant_id = 1 AND transaction_date <= %s", d
        )
        assert D(block["total"]) == ledger, d
        assert D(block["owner"]["payer"]) + D(block["owner"]["patient"]) == D(block["total"])
        matrix_total = sum((D(x) for row in block["matrix"].values() for x in row), Decimal(0))
        assert matrix_total == D(block["owner"]["payer"]), d
        # second source of truth: ar_interval agrees on the owner split
        ip, ipt = one(
            conn,
            "SELECT SUM(payer_balance), SUM(patient_balance) FROM ar_interval "
            "WHERE tenant_id = 1 AND period_type = 'month' AND period_end_date = %s",
            d,
        )
        assert (D(block["owner"]["payer"]), D(block["owner"]["patient"])) == (ip, ipt), d


FORBIDDEN_KEYS = re.compile(
    r"(patient_id|guarantor|member|subscriber|mrn|dob|ssn|birth|first_?name|last_?name|address|phone|email|claim_id|claim_number)",
    re.I,
)


def _walk(node: Any, path: str = ""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield path, k, v
            yield from _walk(v, f"{path}/{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk(v, f"{path}[{i}]")
    else:
        yield path, None, node


def test_no_patient_identifiers_or_person_rows(data) -> None:
    for path, key, _ in _walk(data):
        if key is not None:
            assert not FORBIDDEN_KEYS.search(key), f"{path}/{key}"
    text = fin.render(data)
    assert not re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", text)  # uuid
    assert not re.search(r"\\\\x[0-9a-f]{16,}", text)  # bytea hash
    assert not re.search(r"\b\d{3}-\d{2}-\d{4}\b", text)  # ssn shape
    # aggregates only: no list is anywhere near patient/claim cardinality
    assert max(len(v) for _, _, v in _walk(data) if isinstance(v, list)) <= 60


def test_nothing_dated_after_data_date(data) -> None:
    text = fin.render(data)
    for iso in re.findall(r"\b(\d{4}-\d{2}-\d{2})\b", text):
        assert dt.date.fromisoformat(iso) <= AS_OF, iso
    assert max(data["months"]) == "2026-11"
    for r in data["lag"]["rows"]:
        assert r["month"] <= "2026-11"
    for key in ("billing", "payments", "denials"):
        assert all(m["month"] <= "2026-11" for m in data[key]["monthly"])


def test_money_is_two_decimal_strings(data) -> None:
    money_pat = re.compile(r"^-?\d+\.\d{2}$")
    for path, key, v in _walk(data):
        if isinstance(v, str) and (key in {"charged", "amount", "value", "total", "paid", "fees", "placed"}):
            assert money_pat.match(v), (path, v)
    assert all(money_pat.match(v) for v in data["headline"].values() if isinstance(v, str))


def test_two_runs_identical_except_generated_at(conn, data) -> None:
    second = fin.build(conn)
    strip = lambda d: re.sub(r'"generated_at":"[^"]*"', '"generated_at":""', fin.render(d))  # noqa: E731
    assert strip(data) == strip(second)
    assert strip(data).encode() == strip(second).encode()


def test_cross_tenant_leak(conn, data) -> None:
    empty = fin.build(conn, tenant_id=999_999)
    assert empty["meta"]["tenant_id"] == 999_999
    assert empty["payers"] == [] and empty["months"] == []
    assert empty["headline"]["claims"] == 0 and D(empty["headline"]["charged"]) == 0
    assert empty["flow"]["all"]["links"] == [] and empty["lag"]["rows"] == []
    assert all(D(b["total"]) == 0 for b in empty["ar"]["by_asof"].values())
    assert empty["denials"]["by_reason"] == [] and empty["billing"]["top_cpt"] == []
    assert empty["payments"]["tie_out"]["ledger_total"] == "0.00"
    assert data["headline"]["claims"] > 0  # and tenant 1 still sees its own rows


def test_every_query_filters_tenant() -> None:
    # The SQL now lives in the query registry seed (tools/analytics/fin_seed.py), not as SQL_* constants here.
    assert not [n for n in dir(fin) if n.startswith("SQL_")], "inline SQL should be gone from the exporter"
    assert len(seed.SEED) >= 20
    for qid, s in seed.SEED.items():
        sql = s["sql"]
        assert ":tenant_id" in sql, qid
        assert not re.search(r"\b(insert|update|delete|drop|alter|truncate)\b", sql, re.I), qid


def test_file_size_under_limit(conn, data, tmp_path) -> None:
    out = tmp_path / "fin_data.js"
    out.write_text(fin.render(data), encoding="utf-8")
    assert out.stat().st_size < 1_500_000
    body = out.read_text(encoding="utf-8")
    assert body.startswith("window.KRISNNAI_FIN = {") and body.rstrip().endswith("};")
    json.loads(body[len("window.KRISNNAI_FIN = ") :].rstrip()[:-1])


def test_headline_owed_equals_ar_owner_and_months(data) -> None:
    owner = data["ar"]["by_asof"][data["meta"]["as_of"]]["owner"]
    assert data["headline"]["owed_payer"] == owner["payer"]
    assert data["headline"]["owed_patient"] == owner["patient"]
    assert len(data["months"]) == 37 and data["months"][0] == "2023-11"
    labels = {n["id"]: n["label"] for n in data["flow"]["all"]["nodes"]}
    assert labels["overturned_recovered"] == "Overturned after denial"
