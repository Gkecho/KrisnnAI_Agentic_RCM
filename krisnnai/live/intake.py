# ruff: noqa: E501
"""Other ways an appointment can reach the trigger, besides OpenEMR's API: a drop folder of HL7 scheduling messages and CSV files.

Many practice systems cannot be called through an API but can write a file or send an HL7 message to a folder. This reads such a folder
(read-only: files are never moved, changed or deleted) and answers the same two questions the trigger asks the EMR (`/appointment` and
`/patient`), so the trigger, the re-checks, Gatekeeper and the decision records work exactly as they do with OpenEMR. The insurance
travels in the same file, so no second lookup is needed.

Formats (general knowledge of HL7 v2.x and a simple CSV, to be confirmed against the client's actual interface specification):
  * HL7 v2 scheduling, one message per file (*.hl7): MSH (trigger SIU^S12 new, S13 rescheduled, S14 changed, S15 cancelled, S17 deleted),
    SCH (appointment id, start time), PID (patient id, name, birth date), IN1 (one segment per policy: set id = order, company id and
    name, group, insured, relationship, effective and expiry dates, policy number).
  * CSV (*.csv), one row per policy: appointment_id, patient_id, first_name, last_name, dob, visit_date, visit_time, status,
    policy_order, payer_code, payer_name, member_id, plan, group_number, relationship, holder_last, holder_first, holder_dob, policy_begin, policy_end, copay.
(Column names avoid SQL reserved words so the same names work as a database view.)
An appointment is the same one when its id, date and time are the same; a new date or time is a new version, like in OpenEMR.
Demo data is synthetic.
"""

from __future__ import annotations

import csv
import hashlib
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from krisnnai.live.insurance import ORDER, Policy

HL7_RELATION = {"SEL": "self", "SPO": "spouse", "CHD": "child", "OTH": "other"}  # IN1-17
CANCEL_EVENTS = {"S15", "S17"}


def _num(text: str) -> int:
    """A stable numeric id (the trigger names its folders by number): the digits of the id, or a hash of it."""
    digits = "".join(c for c in text if c.isdigit())
    return int(digits[-6:]) if digits else int(hashlib.sha1(text.encode()).hexdigest()[:6], 16)


def _day(text: str) -> date | None:
    t = text.strip().replace("-", "")[:8]
    try:
        return date(int(t[:4]), int(t[4:6]), int(t[6:8]))
    except ValueError:
        return None


def _iso(text: str) -> str:
    d = _day(text)
    return d.isoformat() if d else ""


def _money(text: str) -> Decimal | None:
    try:
        return Decimal(text).quantize(Decimal("0.01")) if text.strip() else None
    except InvalidOperation:
        return None


def parse_hl7(text: str) -> dict | None:
    """One HL7 scheduling message -> an appointment row with its policies, or None when it is not one."""
    segs = [s.split("|") for s in text.replace("\r\n", "\r").replace("\n", "\r").split("\r") if s.strip()]
    by: dict[str, list[list[str]]] = {}
    for s in segs:
        by.setdefault(s[0], []).append(s)
    if "MSH" not in by or "SCH" not in by or "PID" not in by:
        return None
    msh, sch, pid = by["MSH"][0], by["SCH"][0], by["PID"][0]
    # MSH-9 sits at index 8 because the field separator itself is MSH-1
    trigger = (msh[8].split("^") + ["", ""])[1] if len(msh) > 8 else ""
    appt_id = (sch[2].split("^")[0] or sch[1].split("^")[0]) if len(sch) > 2 else ""
    start = (sch[11].split("^") + ["", "", "", ""])[3] if len(sch) > 11 else ""
    name = (pid[5].split("^") + ["", ""]) if len(pid) > 5 else ["", ""]
    visit = _day(start)
    if not appt_id or visit is None:
        return None
    ais = by.get("AIS", [[]])[0]
    cpt = (ais[3].split("^")[0] if len(ais) > 3 else "").strip()
    policies = []
    for n, f in enumerate(by.get("IN1", []), 1):
        def g(i: int, f: list[str] = f) -> str:
            return f[i] if len(f) > i else ""

        insured = (g(16).split("^") + ["", ""])
        policies.append(
            Policy(
                _order(g(1), n), g(36), g(3).split("^")[0], g(4), g(2).split("^")[0], g(8),
                HL7_RELATION.get(g(17).upper(), "other"), insured[0], insured[1], _iso(g(18)), _day(g(12)), _day(g(13)), None,
            )  # fmt: skip
        )
    return {
        "appt_id": appt_id, "patient_id": pid[3].split("^")[0] if len(pid) > 3 else "", "last": name[0], "first": name[1],
        "dob": _iso(pid[7]) if len(pid) > 7 else "", "visit": visit.isoformat(),
        "time": f"{start[8:10]}:{start[10:12]}:00" if len(start) >= 12 else "00:00:00",
        "cancelled": trigger in CANCEL_EVENTS, "policies": policies, "cpt": cpt, "units": "", "dx": "", "auth_number": "", "docs": True,
    }  # fmt: skip


def _clock(text: str) -> str:
    """HH:MM or HH:MM:SS -> HH:MM:SS."""
    t = text.strip() or "00:00"
    return t if t.count(":") >= 2 else t + ":00"


def _order(raw: str, fallback: int) -> int:
    return int(raw) if raw.strip().isdigit() and 1 <= int(raw) <= 3 else min(fallback, 3)


COLUMNS = (
    "appointment_id", "patient_id", "first_name", "last_name", "dob", "visit_date", "visit_time", "status", "policy_order", "payer_code",
    "payer_name", "member_id", "plan", "group_number", "relationship", "holder_last", "holder_first", "holder_dob", "policy_begin", "policy_end", "copay",
    "cpt", "units", "dx", "auth_number", "docs",
)  # the last five are the planned service, used by the prior authorization check; they may be left out
REQUIRED = ("appointment_id", "patient_id", "first_name", "last_name", "dob", "visit_date")


def rows_to_appointments(rows) -> list[dict]:  # noqa: ANN001
    """Rows with the column names above (one row per policy; rows of the same appointment id are merged) -> appointment rows."""
    out: dict[str, dict] = {}
    for r in rows:
        r = {k: ("" if v is None else str(v)) for k, v in r.items()}  # noqa: PLW2901
        key = r["appointment_id"].strip()
        if not key:
            continue
        a = out.setdefault(key, {
            "appt_id": key, "patient_id": r["patient_id"].strip(), "last": r["last_name"].strip(), "first": r["first_name"].strip(),
            "dob": _iso(r["dob"]), "visit": _iso(r["visit_date"]), "time": _clock(r.get("visit_time") or ""),
            "cancelled": (r.get("status") or "").strip().lower() in ("cancelled", "canceled", "x"), "policies": [],
            "cpt": r.get("cpt", "").strip(), "units": r.get("units", "").strip(), "dx": r.get("dx", "").strip(),
            "auth_number": r.get("auth_number", "").strip(), "docs": r.get("docs", "").strip().lower() not in ("n", "no", "false", "0"),
        })  # fmt: skip
        if r.get("member_id", "").strip():
            a["policies"].append(
                Policy(
                    _order(r.get("policy_order") or str(ORDER.get((r.get("type") or "").lower(), "")), len(a["policies"]) + 1),
                    r["member_id"].strip(), r["payer_code"].strip(), r.get("payer_name", "").strip(), r.get("plan", "").strip(),
                    r.get("group_number", "").strip(), (r.get("relationship") or "self").strip().lower(), r.get("holder_last", "").strip(),
                    r.get("holder_first", "").strip(), _iso(r.get("holder_dob", "")), _day(r.get("policy_begin", "")), _day(r.get("policy_end", "")),
                    _money(r.get("copay", "")),
                )  # fmt: skip
            )
    return [a for a in out.values() if a["visit"]]


def parse_csv(path: Path) -> list[dict]:
    """A CSV drop file -> appointment rows."""
    with path.open(encoding="utf-8", newline="") as f:
        return rows_to_appointments(csv.DictReader(f))


def validate_csv(path: Path) -> list[str]:
    """Problems a person should fix before a manually uploaded CSV is used. Empty = fine."""
    problems: list[str] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            return [f"missing column(s): {', '.join(missing)}"]
        for n, r in enumerate(reader, start=2):
            if not (r.get("appointment_id") or "").strip():
                problems.append(f"line {n}: appointment_id is empty")
            elif _day(r.get("visit_date") or "") is None:
                problems.append(f"line {n}: visit_date '{r.get('visit_date')}' is not a date (use YYYY-MM-DD)")
            if (r.get("member_id") or "").strip() and not (r.get("payer_code") or "").strip():
                problems.append(f"line {n}: a policy needs a payer_code")
    return problems


def upload(path: Path, folder: Path) -> tuple[Path | None, list[str]]:
    """Manual upload: check the file, and only if it is clean copy it into the drop folder (the original is left alone)."""
    problems = validate_csv(path) if path.suffix.lower() == ".csv" else ([] if parse_hl7(path.read_text(encoding="utf-8", errors="ignore")) else ["not a readable HL7 scheduling message"])
    if problems:
        return None, problems
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / f"upload_{path.name}"
    dest.write_bytes(path.read_bytes())
    return dest, []


def _rest_rows(self, path: str) -> list[dict]:
    msgs = self._messages()
    if path == "/patient":
        return [{"pid": _num(m["patient_id"] or m["appt_id"]), "pubpid": m["patient_id"] or m["appt_id"], "uuid": ""} for m in msgs]
    if path != "/appointment":
        return []
    return [
        {
            "pc_eid": str(_num(m["appt_id"])), "pid": str(_num(m["patient_id"] or m["appt_id"])), "fname": m["first"], "lname": m["last"],
            "DOB": m["dob"], "pc_eventDate": m["visit"], "pc_startTime": m["time"], "pc_apptstatus": "x" if m["cancelled"] else "-",
            "pc_title": "Office Visit", "_service": {k: m.get(k) for k in ("cpt", "units", "dx", "auth_number", "docs")}, "_policies": [p for p in sorted(m["policies"], key=lambda p: p.order)],
        }
        for m in msgs
    ]  # fmt: skip


class DatabaseView:
    """Reads the same columns from a database view the practice-system vendor or the client's IT creates (read-only SELECT).

    `url` is a SQLAlchemy URL (SQL Server in production, e.g. mssql+pyodbc://...; SQLite in the demo). Only `SELECT * FROM <view>` is ever run,
    with a plain view name, so nothing can be written or changed. The account used should have read access to that one view only.
    """

    def __init__(self, url: str, view: str):
        import re

        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", view):
            raise ValueError("the view name must be a plain identifier")
        from sqlalchemy import create_engine

        self.engine, self.view = create_engine(url), view

    def _messages(self) -> list[dict]:
        from sqlalchemy import text

        with self.engine.connect() as conn:
            rows = [dict(r._mapping) for r in conn.execute(text(f"SELECT * FROM {self.view}"))]  # noqa: S608 - name validated above
        return rows_to_appointments(rows)

    rest_rows = _rest_rows


class DropFolder:
    """Looks like the EMR to the trigger: `rest_rows('/appointment')` and `rest_rows('/patient')`, read from the files in a folder."""

    def __init__(self, folder: Path):
        self.folder = folder

    def _messages(self) -> list[dict]:
        found: dict[str, dict] = {}
        for p in sorted(self.folder.glob("*")):  # name order: a later file for the same appointment id replaces an earlier one
            if p.suffix.lower() == ".hl7":
                m = parse_hl7(p.read_text(encoding="utf-8", errors="ignore"))
                rows = [m] if m else []
            elif p.suffix.lower() == ".csv":
                rows = parse_csv(p)
            else:
                continue
            for m in rows:
                found[m["appt_id"]] = m
        return list(found.values())

    rest_rows = _rest_rows
