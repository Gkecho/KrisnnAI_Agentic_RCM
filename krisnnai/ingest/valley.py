"""Loader for the Valley Wellness database (fabricated, PostgreSQL): its parsed 837P / 835 tables ->
the same records the X12 parsers produce -> the same event + normalized writer.

Read-only toward Valley. Rows that cannot be converted exactly (bad amount, missing join) are skipped
and counted in the report; nothing is guessed. Valley stores amounts and dates as text.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy.engine import Engine

from krisnnai.ingest.hashing import patient_hash
from krisnnai.ingest.loader import IngestResult, ingest_parsed
from krisnnai.ingest.records import (
    AdjustmentRec,
    ClaimLineRec,
    ClaimRec,
    PaymentRec,
    PlbRec,
    RemitLineRec,
    RemitRec,
)
from krisnnai.ingest.x12 import Transaction, x12_date

CHUNK = 400

H837 = ["source_file", "interchange_control_number", "group_control_number", "transaction_control_number",
        "interchange_date", "transaction_date"]  # fmt: skip
H835 = ["source_file", "interchange_control_number", "group_control_number", "transaction_control_number",
        "interchange_date", "total_payment_amount", "credit_debit_flag", "payment_method", "payment_date",
        "trace_number", "payer_id"]  # fmt: skip


@dataclass
class ValleyReport:
    results: list[IngestResult] = field(default_factory=list)
    skipped_rows: Counter = field(default_factory=Counter)

    def count(self, status: str) -> int:
        return sum(1 for r in self.results if r.status == status)


class ValleyReader:
    """Tiny SELECT-only query helper over a psycopg2 (or sqlite3, in tests) connection."""

    def __init__(self, conn):
        self.conn = conn
        self.ph = "?" if type(conn).__module__.startswith("sqlite3") else "%s"

    def rows(self, table: str, cols: list[str], key: str, values: list[str], order: str = "") -> list[dict]:
        out: list[dict] = []
        for i in range(0, len(values), CHUNK):
            chunk = values[i : i + CHUNK]
            marks = ",".join([self.ph] * len(chunk))
            sql = f"SELECT {', '.join(cols)} FROM {table} WHERE {key} IN ({marks})"
            if order:
                sql += f" ORDER BY {order}"
            cur = self.conn.cursor()
            cur.execute(sql, chunk)
            out += [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]
            cur.close()
        return out

    def column(self, sql: str, params: list | None = None) -> list[str]:
        cur = self.conn.cursor()
        cur.execute(sql, params or [])
        out = [r[0] for r in cur.fetchall()]
        cur.close()
        return out


def _money(text) -> Decimal:
    try:
        v = Decimal(str(text).strip())
    except (InvalidOperation, AttributeError):
        raise ValueError(f"bad amount {text!r}") from None
    if not v.is_finite():
        raise ValueError(f"bad amount {text!r}")
    return v


def _opt_money(text) -> Decimal | None:
    return None if text in (None, "") else _money(text)


def _date(text) -> date | None:
    if not text:
        return None
    try:
        return x12_date(str(text).strip(), "valley date")
    except Exception:
        raise ValueError(f"bad date {text!r}") from None


def _mods(text) -> list[str]:
    return [m for m in (text or "").replace(",", ":").split(":") if m][:4]


def _by(rows: list[dict], *keys: str) -> dict:
    out = defaultdict(list)
    for r in rows:
        out[tuple(r[k] for k in keys)].append(r)
    return out


def _tx(header: dict, st01: str, gs01: str) -> Transaction:
    return Transaction(
        isa13=header["interchange_control_number"] or "0",
        gs06=header["group_control_number"] or "0",
        gs01=gs01,
        st01=st01,
        st02=header["transaction_control_number"] or "0",
        version="",
        isa_date=x12_date(header["interchange_date"], "interchange_date"),
    )


def build_837(rd: ValleyReader, files: list[str], salt: str, report: ValleyReport) -> dict[str, tuple]:
    sf_key = "source_file"
    hdr = {r[sf_key]: r for r in rd.rows("edi_837p_header", H837, sf_key, files)}
    prov = _by(
        rd.rows("edi_837p_billing_provider", ["source_file", "hl_id", "npi", "tax_id", "last_name_or_org"], sf_key, files),
        "source_file", "hl_id",
    )  # fmt: skip
    subs = _by(
        rd.rows("edi_837p_subscriber", ["source_file", "hl_id", "member_id"], sf_key, files), "source_file", "hl_id"
    )
    payers = _by(
        rd.rows("edi_837p_payer", ["source_file", "claim_context_hl_id", "name", "payer_id"], sf_key, files),
        "source_file", "claim_context_hl_id",
    )  # fmt: skip
    claims = rd.rows(
        "edi_837p_claims",
        ["source_file", "claim_number", "claim_seq", "billing_hl_id", "subscriber_hl_id", "total_charge_amount",
         "place_of_service_code", "frequency_code", "claim_service_date_start"],
        sf_key, files, "source_file, claim_seq",
    )  # fmt: skip
    lines = _by(
        rd.rows(
            "edi_837p_service_lines",
            ["source_file", "claim_number", "line_seq", "line_number", "procedure_code", "modifiers",
             "line_charge_amount", "unit_measure", "service_units", "diagnosis_pointers", "service_date"],
            sf_key, files, "source_file, claim_number, line_seq",
        ),
        "source_file", "claim_number",
    )  # fmt: skip
    dx = _by(
        rd.rows("edi_837p_diagnosis_codes", ["source_file", "claim_number", "sequence", "qualifier", "code"],
                sf_key, files, "source_file, claim_number, sequence"),
        "source_file", "claim_number",
    )  # fmt: skip

    recs: dict[str, list[ClaimRec]] = defaultdict(list)
    for c in claims:
        sf, num = c["source_file"], c["claim_number"]
        try:
            p = prov.get((sf, c["billing_hl_id"]))
            sb = subs.get((sf, c["subscriber_hl_id"]))
            py = payers.get((sf, c["subscriber_hl_id"]))
            if not (p and sb and py and sb[0]["member_id"]):
                report.skipped_rows["837 claim missing provider/subscriber/payer"] += 1
                continue
            rec_lines = [
                ClaimLineRec(
                    line_number=int(ln["line_number"] or ln["line_seq"]),
                    cpt=ln["procedure_code"],
                    modifiers=_mods(ln["modifiers"]),
                    charge=_money(ln["line_charge_amount"]),
                    units=_money(ln["service_units"] or "1"),
                    unit_basis=ln["unit_measure"] or "UN",
                    dx_pointer=ln["diagnosis_pointers"] or None,
                    service_date=_date(ln["service_date"]),
                )
                for ln in lines.get((sf, num), [])
            ]
            service = _date(c["claim_service_date_start"]) or min(
                (x.service_date for x in rec_lines if x.service_date), default=None
            )
            recs[sf].append(
                ClaimRec(
                    claim_submitter_id=num,
                    total_charge=_money(c["total_charge_amount"]),
                    place_of_service=c["place_of_service_code"] or None,
                    frequency_code=c["frequency_code"] or "1",
                    payer_claim_control_number=None,
                    service_date=service,
                    submitted_on=_date(hdr[sf]["transaction_date"]),
                    payer_code=py[0]["payer_id"] or "",
                    payer_name=py[0]["name"] or "",
                    provider_npi=p[0]["npi"],
                    provider_name=p[0]["last_name_or_org"] or p[0]["npi"],
                    tax_id=p[0]["tax_id"] or None,
                    patient_hash=patient_hash(salt, sb[0]["member_id"]),
                    dx=[(d["qualifier"], d["code"]) for d in dx.get((sf, num), [])],
                    lines=rec_lines,
                )
            )
        except (ValueError, KeyError, TypeError) as e:
            report.skipped_rows[f"837 claim {type(e).__name__}: {e}"[:80]] += 1
    return {sf: (_tx(hdr[sf], "837", "HC"), "837P.claim", r) for sf, r in recs.items() if r}


def build_835(rd: ValleyReader, files: list[str], salt: str, report: ValleyReport) -> dict[str, tuple]:
    sf_key = "source_file"
    hdr = {r[sf_key]: r for r in rd.rows("edi_835_payment_header", H835, sf_key, files)}
    payer = {r[sf_key]: r for r in rd.rows("edi_835_payer", ["source_file", "name", "payer_id"], sf_key, files)}
    plb = _by(
        rd.rows("edi_835_provider_adjustments",
                ["source_file", "provider_id", "fiscal_period_date", "adjustment_reason_code", "reference_id", "amount"],
                sf_key, files, "source_file, id"),
        "source_file",
    )  # fmt: skip
    claims = rd.rows(
        "edi_835_claims",
        ["source_file", "claim_number", "claim_seq", "claim_status_code", "total_charge_amount", "total_paid_amount",
         "patient_responsibility_amount", "claim_filing_indicator_code", "payer_claim_control_number"],
        sf_key, files, "source_file, claim_seq",
    )  # fmt: skip
    svc = _by(
        rd.rows(
            "edi_835_service_payments",
            ["source_file", "claim_number", "line_seq", "procedure_code", "modifiers", "line_charge_amount",
             "line_paid_amount", "units_paid", "service_date"],
            sf_key, files, "source_file, claim_number, line_seq",
        ),
        "source_file", "claim_number",
    )  # fmt: skip
    adj = _by(
        rd.rows(
            "edi_835_adjustments",
            ["source_file", "claim_number", "line_seq", "group_code", "reason_code", "amount", "quantity",
             "remark_code", "remark_code_2", "remark_qualifier"],
            sf_key, files, "source_file, claim_number, line_seq, id",
        ),
        "source_file", "claim_number",
    )  # fmt: skip
    amounts = {
        (r["source_file"], r["claim_number"], str(r["line_seq"])): r["amount"]
        for r in rd.rows("edi_835_amounts", ["source_file", "claim_number", "line_seq", "qualifier", "amount"], sf_key, files)
        if r["qualifier"] == "B6"
    }  # fmt: skip
    parties = {
        (r["source_file"], r["claim_number"]): r["id_code"]
        for r in rd.rows("edi_835_claim_parties", ["source_file", "claim_number", "role_code", "id_code"], sf_key, files)
        if r["role_code"] == "QC"
    }  # fmt: skip
    dates = {
        (r["source_file"], r["claim_number"], str(r["line_seq"] or ""), r["qualifier"]): r["raw_value"]
        for r in rd.rows("edi_835_dates", ["source_file", "claim_number", "line_seq", "qualifier", "raw_value"], sf_key, files)
        if r["qualifier"] in ("232", "472")
    }  # fmt: skip

    remits: dict[str, list[RemitRec]] = defaultdict(list)
    for c in claims:
        sf, num = c["source_file"], c["claim_number"]
        try:
            member = parties.get((sf, num))
            rem = RemitRec(
                claim_submitter_id=num,
                status_code=c["claim_status_code"],
                total_charge=_money(c["total_charge_amount"]),
                total_paid=_money(c["total_paid_amount"]),
                patient_responsibility=_money(c["patient_responsibility_amount"] or "0"),
                filing_indicator=c["claim_filing_indicator_code"] or None,
                payer_claim_control_number=c["payer_claim_control_number"] or "",
                patient_hash=patient_hash(salt, member) if member else None,
                service_date=_date(dates.get((sf, num, "", "232"))),
            )
            line_recs: dict[str, RemitLineRec] = {}
            for ln in svc.get((sf, num), []):
                key = str(ln["line_seq"])
                line_recs[key] = RemitLineRec(
                    line_number=int(ln["line_seq"]),
                    cpt=ln["procedure_code"],
                    modifiers=_mods(ln["modifiers"]),
                    charge=_money(ln["line_charge_amount"]),
                    paid=_money(ln["line_paid_amount"] or "0"),
                    units=_opt_money(ln["units_paid"]),
                    allowed=_opt_money(amounts.get((sf, num, key))),
                    service_date=_date(dates.get((sf, num, key, "472"))),
                )
            for a in adj.get((sf, num), []):
                owner = line_recs.get(str(a["line_seq"])) if a["line_seq"] else None
                owner = owner or rem
                owner.adjustments.append(
                    AdjustmentRec(a["group_code"], a["reason_code"], _money(a["amount"]), _opt_money(a["quantity"]))
                )
                for code in (a["remark_code"], a["remark_code_2"]):
                    if code:
                        owner.remarks.append((a["remark_qualifier"] or "HE", code))
            rem.lines = [line_recs[k] for k in sorted(line_recs, key=int)]
            remits[sf].append(rem)
        except (ValueError, KeyError, TypeError) as e:
            report.skipped_rows[f"835 claim {type(e).__name__}: {e}"[:80]] += 1

    out = {}
    for sf, recs in remits.items():
        h, py = hdr.get(sf), payer.get(sf)
        if h is None or py is None:
            report.skipped_rows["835 file missing payment header/payer"] += 1
            continue
        try:
            payment_date = _date(h["payment_date"])
            if payment_date is None:
                raise ValueError("no payment date")
            pay = PaymentRec(
                trace_number=h["trace_number"] or "",
                amount=_money(h["total_payment_amount"]),
                credit_debit=h["credit_debit_flag"] or "C",
                method=h["payment_method"] or "NON",
                payment_date=payment_date,
                payer_code=py["payer_id"] or h["payer_id"] or "",
                payer_name=py["name"] or "",
                plb=[
                    PlbRec(
                        i, p["provider_id"], _date(p["fiscal_period_date"]), p["adjustment_reason_code"],
                        p["reference_id"] or None, _money(p["amount"]),
                    )
                    for i, p in enumerate(plb.get((sf,), []), start=1)
                ],
            )  # fmt: skip
        except (ValueError, KeyError, TypeError) as e:
            report.skipped_rows[f"835 payment {type(e).__name__}: {e}"[:80]] += 1
            continue
        out[sf] = (_tx(h, "835", "HP"), "835", [pay, *recs])
    return out


def load_valley(
    engine: Engine, tenant_id: int, salt: str, conn, n_837_files: int = 2, max_835_files: int = 500
) -> ValleyReport:
    """Load the first `n_837_files` 837P files and the 835 files that remit their claims."""
    rd = ValleyReader(conn)
    report = ValleyReport()
    files_837 = rd.column("SELECT DISTINCT source_file FROM edi_837p_header ORDER BY source_file")[:n_837_files]
    built = build_837(rd, files_837, salt, report)
    for sf in files_837:
        if sf in built:
            report.results.append(ingest_parsed(engine, tenant_id, sf, f"valley:837P:{sf}", "837P", [built[sf]]))
    claim_numbers = [c.claim_submitter_id for _, _, recs in built.values() for c in recs]
    remit_files: set[str] = set()
    for i in range(0, len(claim_numbers), CHUNK):
        chunk = claim_numbers[i : i + CHUNK]
        marks = ",".join([rd.ph] * len(chunk))
        remit_files.update(
            rd.column(f"SELECT DISTINCT source_file FROM edi_835_claims WHERE claim_number IN ({marks})", chunk)
        )
    ordered = sorted(remit_files)[:max_835_files]
    for i in range(0, len(ordered), 50):
        batch = ordered[i : i + 50]
        built_835 = build_835(rd, batch, salt, report)
        for sf in batch:
            if sf in built_835:
                report.results.append(ingest_parsed(engine, tenant_id, sf, f"valley:835:{sf}", "835", [built_835[sf]]))
    return report


def connect_readonly(config_path: Path):
    """Open a read-only psycopg2 connection from a KEY=VALUE env file (PGHOST, PGPORT, PGDATABASE, ...)."""
    import psycopg2  # optional dependency: pip install psycopg2-binary

    cfg = {}
    for line in config_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.strip()
    conn = psycopg2.connect(
        host=cfg["PGHOST"], port=cfg.get("PGPORT", "5432"), dbname=cfg["PGDATABASE"],
        user=cfg["PGUSER"], password=cfg["PGPASSWORD"], connect_timeout=15,
    )  # fmt: skip
    conn.set_session(readonly=True, autocommit=True)
    return conn
