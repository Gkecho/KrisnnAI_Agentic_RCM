"""Financial analytics export: reads krisnnai_r2 (read-only) and writes ``window.KRISNNAI_FIN = {...};``.

Output shape: docs/fin_data_contract.md. Metric definitions: docs/fin_metrics.md.
The SQL no longer lives here: every data section's SQL is a named query in the query registry
(tools/analytics/qreg.py, seeded from fin_seed.py) and is resolved through the scope hierarchy at export time.
Rules: SELECT only on a read-only connection, every query filters tenant_id, money is Decimal (serialized as 2-decimal
strings), nothing is dated after the data date, aggregates only (no patient identifiers, no person-level rows).

Run from the repo root:  python tools/analytics/export_fin_data.py [--out out/fin/fin_data.js]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys
from collections.abc import Sequence
from decimal import Decimal
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "synthea"))
sys.path.insert(0, str(ROOT / "tools" / "analytics"))

import qreg  # noqa: E402
import qsafe  # noqa: E402

AS_OF = dt.date(2026, 11, 6)
TENANT_ID = 1
ZERO = Decimal("0.00")
LAG_COLS = ["0-30", "31-60", "61-90", "91-120", "121-180", "181+", "unpaid"]
AR_BUCKETS = ["0-30", "31-60", "61-90", "91-120", "121-180", "181+"]
DENIAL_LOST = ("upheld", "deadline_missed", "non_appealable")  # denial_status values that are final losses
SANKEY_NODES = [
    ("charged", "Charged", "charged"),
    ("payer_paid", "Paid by payer", "paid"),
    ("contractual", "Contractual write-down", "adjustment"),
    ("patient_share", "Patient share", "patient"),
    ("denied", "Denied", "denial"),
    ("in_process", "In process", "pending"),
    ("patient_paid", "Patient paid", "paid"),
    ("patient_owed", "Patient owes", "patient"),
    ("at_agency", "At collection agency", "patient"),
    ("overturned_recovered", "Overturned after denial", "paid"),
    ("denied_lost", "Denied, lost", "denial"),
    ("denial_open", "Denial still open", "denial"),
]


# ---------------------------------------------------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------------------------------------------------
def money(value: Any) -> str:
    """Decimal (or None) -> 2-decimal string. Never goes through float."""
    d = Decimal(0) if value is None else Decimal(value)
    return str(d.quantize(Decimal("0.01")))


def rate(num: Any, den: Any) -> float:
    """Ratio 0..1 rounded to 4 places (a rate is a number, not money); 0 when the denominator is 0."""
    n, d = Decimal(num or 0), Decimal(den or 0)
    return float(round(n / d, 4)) if d else 0.0


def month_range(first: str, last: str) -> list[str]:
    y, m = int(first[:4]), int(first[5:7])
    ly, lm = int(last[:4]), int(last[5:7])
    out: list[str] = []
    while (y, m) <= (ly, lm):
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def asof_dates() -> list[dt.date]:
    """12 month-ends (Nov 2025 .. Oct 2026) plus the data date."""
    dates: list[dt.date] = []
    y, m = 2025, 11
    while (y, m) <= (2026, 10):
        nxt = dt.date(y + (m == 12), 1 if m == 12 else m + 1, 1)
        dates.append(nxt - dt.timedelta(days=1))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return [*dates, AS_OF]


class Db:
    """Runs named registry queries read-only: every query gets :tenant_id and :asof (the data date) as binds."""

    def __init__(self, conn: Any, tenant_id: int, source: qreg.QuerySource) -> None:
        self.conn = conn
        self.tenant_id = tenant_id
        self.source = source

    def rows(self, query_id: str, **params: Any) -> list[tuple[Any, ...]]:
        sql, spec = self.source.get(query_id)
        res = qsafe.run_query(self.conn, spec, sql, {"tenant_id": self.tenant_id, "asof": AS_OF, **params})
        return res.rows


def open_connection() -> Any:
    from r2load import connect  # reads the password from the config file; never printed

    conn = connect()
    conn.rollback()
    conn.set_session(readonly=True)  # belt and braces: the server rejects any write
    return conn


# ---------------------------------------------------------------------------------------------------------------------
# builders
# ---------------------------------------------------------------------------------------------------------------------
def ledger_by_party(db: Db, as_of: dt.date) -> dict[tuple[str, str], tuple[Decimal, Decimal]]:
    return {(r[0], r[1]): (r[2], r[3]) for r in db.rows("headline.ledger", d=as_of)}


def build_headline(db: Db) -> dict[str, Any]:
    claims, patients, charged, _ = db.rows("headline.claims")[0]
    led = ledger_by_party(db, AS_OF)
    zero = (ZERO, ZERO)
    n_den, denied = db.rows("headline.denials")[0]
    adjudicated = sum(r[3] for r in db.rows("scorecard.lines") if r[0] is None)
    return {
        "charged": money(charged),
        "paid_payer": money(led.get(("payer", "payment"), zero)[0]),
        "paid_patient": money(led.get(("patient", "payment"), zero)[0]),
        "owed_payer": money(sum(v[1] for k, v in led.items() if k[0] == "payer")),
        "owed_patient": money(sum(v[1] for k, v in led.items() if k[0] == "patient")),
        "denied": money(denied),
        "denial_rate": rate(n_den, adjudicated),
        "claims": int(claims),
        "patients": int(patients),
    }


def sankey(t: dict[str, Decimal]) -> dict[str, Any]:
    """Turn one set of totals into nodes + links. patient_owed is the remainder, so patient_share balances exactly."""
    patient_owed = t["patient_share"] - t["patient_paid"] - t["at_agency"]
    denied = t["denied_recovered"] + t["denied_lost"] + t["denied_open"]
    links = [
        ("charged", "payer_paid", t["payer_paid"]),
        ("charged", "contractual", t["contractual"]),
        ("charged", "patient_share", t["patient_share"]),
        ("charged", "denied", denied),
        ("charged", "in_process", t["in_process"]),
        ("patient_share", "patient_paid", t["patient_paid"]),
        ("patient_share", "patient_owed", patient_owed),
        ("patient_share", "at_agency", t["at_agency"]),
        ("denied", "overturned_recovered", t["denied_recovered"]),
        ("denied", "denied_lost", t["denied_lost"]),
        ("denied", "denial_open", t["denied_open"]),
    ]
    return {
        "nodes": [{"id": i, "label": label, "group": g} for i, label, g in SANKEY_NODES],
        "links": [{"source": s, "target": d, "value": money(v)} for s, d, v in links if v != 0],
    }


SANKEY_KEYS = [
    "charged", "payer_paid", "contractual", "patient_share", "patient_paid", "at_agency",
    "denied_recovered", "denied_lost", "denied_open", "in_process",
]  # fmt: skip


def build_flow(db: Db, payer_codes: Sequence[str]) -> dict[str, Any]:
    by_payer: dict[str, dict[str, Decimal]] = {c: dict.fromkeys(SANKEY_KEYS, ZERO) for c in payer_codes}
    for row in db.rows("flow.links"):
        code = row[0]
        by_payer.setdefault(code, dict.fromkeys(SANKEY_KEYS, ZERO))
        for key, val in zip(SANKEY_KEYS, row[1:], strict=True):
            by_payer[code][key] = Decimal(val or 0)
    total = {k: sum((v[k] for v in by_payer.values()), ZERO) for k in SANKEY_KEYS}
    return {"all": sankey(total), "by_payer": {c: sankey(by_payer[c]) for c in sorted(by_payer)}}


def build_lag(db: Db, payer_codes: Sequence[str]) -> dict[str, Any]:
    paid: dict[str, dict[str, list[Decimal]]] = {}
    for month, code, bucket, amount in db.rows("lag.paid"):
        cells = paid.setdefault(month, {}).setdefault(code, [ZERO] * 7)
        cells[bucket] += Decimal(amount)
    charged: dict[str, dict[str, tuple[Decimal, Decimal, Decimal]]] = {}
    for month, code, chg, contractual, denied_final in db.rows("lag.charged"):
        charged.setdefault(month, {})[code] = (Decimal(chg), Decimal(contractual or 0), Decimal(denied_final or 0))
    rows = []
    for month in sorted(charged):
        per_payer: dict[str, list[Decimal]] = {}
        total_cells = [ZERO] * 7
        row_charged = row_contr = row_denied = ZERO
        for code in sorted(set(payer_codes) | set(charged[month])):
            chg, contr, den = charged[month].get(code, (ZERO, ZERO, ZERO))
            cells = list(paid.get(month, {}).get(code, [ZERO] * 7))
            cells[6] = chg - sum(cells[:6], ZERO) - contr - den  # unpaid = still collectible
            per_payer[code] = cells
            total_cells = [a + b for a, b in zip(total_cells, cells, strict=True)]
            row_charged, row_contr, row_denied = row_charged + chg, row_contr + contr, row_denied + den
        rows.append(
            {
                "month": month,
                "charged": money(row_charged),
                "cells": [money(c) for c in total_cells],
                "by_payer": {c: [money(x) for x in v] for c, v in per_payer.items()},
                # extra (additive) fields so that sum(cells) + contractual + denied_final == charged
                "contractual": money(row_contr),
                "denied_final": money(row_denied),
            }
        )
    return {"cols": LAG_COLS, "rows": rows}


def build_billing(db: Db, months: Sequence[str]) -> dict[str, Any]:
    data = {r[0]: r for r in db.rows("billing.monthly")}
    monthly = []
    for m in months:
        r = data.get(m)
        status = (
            {"paid": r[3], "partial": r[4], "submitted": r[5], "denied": r[6]}
            if r
            else dict.fromkeys(["paid", "partial", "submitted", "denied"], 0)
        )
        monthly.append(
            {"month": m, "claims": int(r[1]) if r else 0, "charged": money(r[2] if r else 0),
             "status": {k: int(v) for k, v in status.items()}}
        )  # fmt: skip
    top = [
        {"code": r[0], "label": r[1], "lines": int(r[2]), "charged": money(r[3])} for r in db.rows("billing.top_cpt")
    ]
    return {"monthly": monthly, "top_cpt": top}


def build_payments(db: Db, months: Sequence[str]) -> dict[str, Any]:
    pay: dict[tuple[str, str], Decimal] = {(r[0], r[1]): Decimal(r[2]) for r in db.rows("payments.monthly")}
    monthly = [
        {
            "month": m,
            "payer_paid": money(pay.get((m, "payer"), ZERO)),
            "patient_paid": money(pay.get((m, "patient"), ZERO)),
        }
        for m in months
    ]
    payments, remittance, ledger = (Decimal(x) for x in db.rows("payments.tie_out")[0])
    return {
        "monthly": monthly,
        "tie_out": {
            "payments_total": money(payments),
            "remittance_total": money(remittance),
            "ledger_total": money(ledger),
            # payments, remittance and ledger must agree to the cent
            "ok": payments == remittance == ledger,
        },
    }


def build_ar(db: Db, payer_codes: Sequence[str]) -> dict[str, Any]:
    by_asof: dict[str, Any] = {}
    for d in asof_dates():
        matrix = {c: [ZERO] * 6 for c in payer_codes}
        owner = {"payer": ZERO, "patient": ZERO}
        for who, code, bucket, amount in db.rows("ar.matrix", d=d):
            owner[who] += Decimal(amount)
            if who == "payer":
                matrix.setdefault(code, [ZERO] * 6)[bucket] += Decimal(amount)
        by_asof[d.isoformat()] = {
            "matrix": {c: [money(x) for x in v] for c, v in sorted(matrix.items())},
            "owner": {k: money(v) for k, v in owner.items()},
            "total": money(owner["payer"] + owner["patient"]),
        }
    return {"buckets": AR_BUCKETS, "by_asof": by_asof}


def build_denials(db: Db, payer_codes: Sequence[str], months: Sequence[str]) -> dict[str, Any]:
    st = {r[0]: r for r in db.rows("denials.status")}

    def agg(*statuses: str) -> tuple[int, Decimal]:
        return sum(int(st[s][1]) for s in statuses if s in st), sum(
            (Decimal(st[s][2]) for s in statuses if s in st), ZERO
        )

    n_all, a_all = agg(*st)
    n_ov, a_ov = agg("overturned")
    n_app, a_app = agg("appealed", "overturned", "upheld")
    rec_n = sum(int(r[3]) for r in st.values())
    rec_a = sum((Decimal(r[4]) for r in st.values()), ZERO)
    waterfall = [
        ("denied", n_all, a_all),
        ("appealed", n_app, a_app),
        ("overturned", n_ov, a_ov),
        ("recovered", rec_n, rec_a),  # amount = dollars actually paid after overturn
        ("upheld", *agg("upheld")),
        ("deadline_missed", *agg("deadline_missed")),
        ("final_no_appeal", *agg("non_appealable")),
        ("open", *agg("open", "appealed")),
    ]
    cell: dict[tuple[str, str], Decimal] = {}
    reasons: dict[str, dict[str, Any]] = {}
    for carc, label, appealable, code, n, amount, prev in db.rows("denials.matrix"):
        r = reasons.setdefault(
            carc,
            {"carc": carc, "label": label, "count": 0, "amount": ZERO, "preventable": ZERO, "appealable": appealable},
        )
        r["count"] += int(n)
        r["amount"] += Decimal(amount)
        r["preventable"] += Decimal(prev)
        cell[(carc, code)] = Decimal(amount)
    ranked = sorted(reasons.values(), key=lambda r: (-r["amount"], r["carc"]))
    top8 = ranked[:8]
    prev, other = db.rows("denials.preventable")[0]
    month_data = {r[0]: r for r in db.rows("denials.monthly")}
    monthly = [
        {
            "month": m,
            "denied_amount": money(month_data[m][1] if m in month_data else 0),
            "denial_rate": rate(month_data[m][2], month_data[m][3]) if m in month_data else 0.0,
        }
        for m in months
    ]
    return {
        "waterfall": [{"step": s, "count": n, "amount": money(a)} for s, n, a in waterfall],
        "matrix": {
            "reasons": [{"carc": r["carc"], "label": r["label"]} for r in top8],
            "payers": list(payer_codes),
            "cells": [[money(cell.get((r["carc"], c), ZERO)) for c in payer_codes] for r in top8],
        },
        "by_reason": [
            {
                "carc": r["carc"],
                "label": r["label"],
                "count": r["count"],
                "amount": money(r["amount"]),
                "preventable": money(r["preventable"]),
                "appealable": bool(r["appealable"]),
            }
            for r in ranked
        ],  # fmt: skip
        "preventable": {"preventable": money(prev), "other": money(other)},
        "monthly": monthly,
    }


def build_patient(db: Db) -> dict[str, Any]:
    stmt: dict[int, dict[str, tuple[int, Decimal]]] = {}
    for level, status, n, amount in db.rows("patient.statements"):
        stmt.setdefault(int(level), {})[status] = (int(n), Decimal(amount))
    ladder = []
    for level in range(4):
        by_status = stmt.get(level, {})
        paid_n, paid_a = by_status.get("paid", (0, ZERO))
        all_n = sum(v[0] for v in by_status.values())
        all_a = sum((v[1] for v in by_status.values()), ZERO)
        ladder.append(
            {"step": f"statement_{level + 1}", "paid_count": paid_n, "paid_amount": money(paid_a),
             "remaining_count": all_n - paid_n, "remaining_amount": money(all_a - paid_a)}
        )  # fmt: skip
    plans = {r[0]: (int(r[1]), Decimal(r[2])) for r in db.rows("patient.plans")}
    done_n, done_a = plans.get("completed", (0, ZERO))
    rest_n = sum(v[0] for k, v in plans.items() if k != "completed")
    rest_a = sum((v[1] for k, v in plans.items() if k != "completed"), ZERO)
    ladder.append(
        {"step": "payment_plan", "paid_count": done_n, "paid_amount": money(done_a),
         "remaining_count": rest_n, "remaining_amount": money(rest_a)}
    )  # fmt: skip
    ag = {r[0]: r for r in db.rows("patient.agency")}
    recovered_n = sum(int(r[1]) for r in ag.values() if Decimal(r[3]) > 0)
    ag_rec = sum((Decimal(r[3]) for r in ag.values()), ZERO)
    active = ag.get("active")
    ladder.append(
        {"step": "agency", "paid_count": recovered_n, "paid_amount": money(ag_rec),
         "remaining_count": int(active[1]) if active else 0, "remaining_amount": money(active[2] if active else 0)}
    )  # fmt: skip
    n_est, n_match, est, act, med = db.rows("patient.estimates")[0]
    return {
        "ladder": ladder,
        "plans": {"count": sum(v[0] for v in plans.values()), "total": money(sum((v[1] for v in plans.values()), ZERO)),
                  "paid": money(done_a)},
        "agency": {"placed": money(sum((Decimal(r[2]) for r in ag.values()), ZERO)), "recovered": money(ag_rec),
                   "fees": money(sum((Decimal(r[4]) for r in ag.values()), ZERO)),
                   "count": sum(int(r[1]) for r in ag.values())},
        "estimates": {"count": int(n_est), "matched": int(n_match), "estimated_patient": money(est),
                      "actual_patient": money(act), "abs_error_median": money(Decimal(str(med)))},
    }  # fmt: skip


def build_scorecard(db: Db, payer_codes: Sequence[str], months: Sequence[str]) -> dict[str, Any]:
    claims: dict[tuple[str | None, str | None], tuple[Any, ...]] = {
        (r[0], r[1]): r for r in db.rows("scorecard.claims")
    }
    lines: dict[tuple[str | None, str | None], tuple[Any, ...]] = {(r[0], r[1]): r for r in db.rows("scorecard.lines")}

    def days(row: tuple[Any, ...] | None) -> float:
        return round(float(row[6]), 1) if row and row[6] is not None else 0.0

    def denial(key: tuple[str | None, str | None]) -> float:
        row = lines.get(key)
        return rate(row[2], row[3]) if row else 0.0

    out: dict[str, Any] = {}
    for code in payer_codes:
        tot = claims.get((code, None))
        out[code] = {
            "claims": int(tot[2]) if tot else 0,
            "charged": money(tot[3] if tot else 0),
            "paid_rate": rate(tot[5], tot[4]) if tot else 0.0,
            "denial_rate": denial((code, None)),
            "days_to_pay": days(tot),
            "monthly": [
                {
                    "month": m,
                    "paid_rate": rate(claims[(code, m)][5], claims[(code, m)][4]) if (code, m) in claims else 0.0,
                    "denial_rate": denial((code, m)),
                    "days_to_pay": days(claims.get((code, m))),
                }
                for m in months
            ],
        }
    return out


def build(conn: Any, tenant_id: int = TENANT_ID, source: qreg.QuerySource | None = None) -> dict[str, Any]:
    """Assemble the whole KRISNNAI_FIN object for one tenant (read-only).

    ``source`` supplies the resolved SQL (registry + context). Default: the local registry file, seeded if needed,
    resolved for the tenant with no role.
    """
    own: qreg.Registry | None = None
    if source is None:
        own = qreg.open_default()
        source = qreg.QuerySource(own, customer=str(tenant_id))
    try:
        return _build(Db(conn, tenant_id, source), tenant_id)
    finally:
        if own is not None:
            own.close()


def _build(db: Db, tenant_id: int) -> dict[str, Any]:
    payers = db.rows("payers.list")
    codes = [p[0] for p in payers]
    first_month = db.rows("headline.claims")[0][3]
    months = month_range(first_month, AS_OF.strftime("%Y-%m")) if first_month else []
    return {
        "meta": {
            "as_of": AS_OF.isoformat(),
            "generated_at": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": "krisnnai_r2",
            "shadow": True,
            "synthetic": True,
            "tenant_id": tenant_id,
        },
        "payers": [{"code": c, "name": n, "type": t} for c, n, t in payers],
        "months": months,
        "asof": [d.isoformat() for d in asof_dates()],
        "headline": build_headline(db),
        "flow": build_flow(db, codes),
        "lag": build_lag(db, codes),
        "billing": build_billing(db, months),
        "payments": build_payments(db, months),
        "ar": build_ar(db, codes),
        "denials": build_denials(db, codes, months),
        "patient": build_patient(db),
        "scorecard": build_scorecard(db, codes, months),
    }


def render(data: dict[str, Any]) -> str:
    return "window.KRISNNAI_FIN = " + json.dumps(data, separators=(",", ":"), ensure_ascii=True) + ";\n"


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="out/fin/fin_data.js", help="output file (relative to the repo root)")
    ap.add_argument("--registry", default=None, help="registry sqlite file (default var/analytics_registry.sqlite)")
    ap.add_argument("--role", default=None, help="resolve queries for this role (default: none)")
    args = ap.parse_args(argv)
    out = pathlib.Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    reg = qreg.open_default(args.registry)
    source = qreg.QuerySource(reg, customer=str(TENANT_ID), role=args.role)
    conn = open_connection()
    try:
        data = build(conn, TENANT_ID, source)
    finally:
        conn.close()
        reg.close()
    non_seed = {k: v for k, v in source.used.items() if v["level"] != "solution"}
    if non_seed:
        print(
            "queries resolved below solution level:",
            ", ".join(f"{k}@{v['level']} v{v['version']}" for k, v in sorted(non_seed.items())),
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(data), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
