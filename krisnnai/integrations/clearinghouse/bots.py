"""Bots that act on what the agents flagged, through a clearinghouse client.

    eligibility bot   A1 appointments needing a check          -> 270 -> 271 -> file in the inbox
    status bot        A7 claims needing a status check         -> 276 -> 277 -> file in the inbox
    resubmission bot  A6 claims returned by the clearinghouse  -> replacement 837 -> 999 + 277CA -> files in the inbox

Each response is written as an X12 file where the daily loader will pick it up, so the same agents re-run on the new
facts. Every request and response is logged (identifiers masked). A bot only reads what the practice's own extract
holds and only talks to the client it was given; it changes nothing in any system of record.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.engine import Engine

import krisnnai.model as m
from krisnnai.engine import NO_ACTION
from krisnnai.integrations.clearinghouse.claim_store import PmExtract
from krisnnai.integrations.clearinghouse.client import ClearinghouseClient
from krisnnai.integrations.clearinghouse.x12_out import (
    parse_277_status,
    write_270,
    write_276,
    write_corrected_837,
)
from krisnnai.ingest.eligibility import parse_271
from krisnnai.ingest.x12 import X12Error, read_transactions
from krisnnai.model import tenant_session

SALT_FOR_PARSE = "bot-parse-only"  # 271 member ids are hashed by the parser; the hash is discarded here


def mask(value: str) -> str:
    return ("*" * max(len(value) - 3, 0)) + value[-3:] if value else ""


@dataclass
class BotEvent:
    bot: str
    subject: str  # appointment id or claim id
    outcome: str
    detail: str
    request_file: str = ""
    response_files: list[str] = field(default_factory=list)


@dataclass
class BotReport:
    bot: str
    events: list[BotEvent] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for e in self.events:
            out[e.outcome] = out.get(e.outcome, 0) + 1
        return out


def latest_decisions(engine: Engine, tenant_id: int, agent_id: str, key: str) -> dict[str, tuple[str, dict]]:
    """key value -> (action, payload) of the latest decision, by the event's known_at."""
    out: dict[str, tuple] = {}
    with tenant_session(engine, tenant_id) as s:
        known = {e.id: e.known_at for e in s.scalars(select(m.Event))}
        for rec in s.scalars(select(m.DecisionRecord).where(m.DecisionRecord.agent_id == agent_id)):
            p = json.loads(rec.action_payload)
            values = p.get(key)
            for v in (values if isinstance(values, list) else [values]):
                if not v:
                    continue
                at = known[rec.event_id]
                if v not in out or at >= out[v][0]:
                    out[v] = (at, rec.action_type, p)
    return {k: (a, p) for k, (_, a, p) in out.items() if a != NO_ACTION}


def _write(out_dir: Path, name: str, text: str) -> str:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / name
    path.write_text(text, encoding="ascii", newline="")
    return path.name


def _log(log_path: Path | None, ev: BotEvent) -> None:
    if log_path is None:
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(ev), sort_keys=True) + "\n")


# ------------------------------------------------------------------------------------------ failure handling
TRANSIENT_KINDS = ("timeout", "connection", "server")


class CallFailed(Exception):
    """A clearinghouse call did not produce a usable reply. `kind` is short and holds no identifiers or body text."""

    def __init__(self, kind: str):
        super().__init__(kind)
        self.kind = kind


def classify(exc: Exception) -> CallFailed:
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        return CallFailed("unauthorized" if code in (401, 403) else "server" if code >= 500 else "refused")
    if isinstance(exc, httpx.ConnectError):
        return CallFailed("connection")
    if isinstance(exc, httpx.TimeoutException):
        return CallFailed("timeout")
    return CallFailed("connection")  # any other transport failure: the request did not complete


def guarded_call(fn, request: str, retries: int = 2, backoff: float = 0.0, retry_kinds=TRANSIENT_KINDS):  # noqa: ANN001
    """Call the clearinghouse; retry only the kinds in `retry_kinds`; raise CallFailed for anything that still fails."""
    for attempt in range(retries + 1):
        try:
            return fn(request)
        except httpx.HTTPError as exc:  # HTTPStatusError and every transport error derive from this
            failure = classify(exc)
            if failure.kind not in retry_kinds or attempt == retries:
                raise failure from None
            if backoff:
                time.sleep(backoff * (2**attempt))
    raise CallFailed("timeout")  # unreachable


class Breaker:
    """Stops a batch after repeated failures, or at once on a rejected credential."""

    def __init__(self, limit: int = 3):
        self.limit, self.fails, self.reason = limit, 0, ""

    def ok(self) -> None:
        self.fails = 0

    def fail(self, kind: str) -> None:
        self.fails += 1
        if kind == "unauthorized":
            self.reason = "credential rejected; stopped"
        elif self.fails >= self.limit:
            self.reason = f"{self.fails} failures in a row ({kind}); stopped"

    @property
    def open(self) -> bool:
        return bool(self.reason)


def _refs(tx) -> set[str]:  # noqa: ANN001
    """Every reference a reply may echo its request by: BHT03 and the TRN reference numbers."""
    out = {seg[3] for seg in tx.segments if seg.id == "BHT"}
    out |= {seg[2] for seg in tx.segments if seg.id == "TRN"}
    return {r for r in out if r}


def _record(rep: BotReport, log_path: Path | None, ev: BotEvent) -> None:
    rep.events.append(ev)
    _log(log_path, ev)


def eligibility_bot(engine: Engine, tenant_id: int, extract: PmExtract, client: ClearinghouseClient, out_dir: Path,
                    when: date, limit: int = 25, log_path: Path | None = None, retries: int = 2,
                    backoff: float = 0.0, breaker_limit: int = 3) -> BotReport:  # fmt: skip
    rep = BotReport("eligibility")
    todo = latest_decisions(engine, tenant_id, "a1_clearance", "appt")
    ctrl = 90000
    breaker = Breaker(breaker_limit)
    # only visits that have not happened yet, soonest first: that is where a fresh answer can still change the outcome
    upcoming = [a for a in todo if a in extract.appointments
                and date.fromisoformat(extract.appointments[a]["appt_date"]) >= when]  # fmt: skip
    for appt_id in sorted(upcoming, key=lambda a: (extract.appointments[a]["appt_date"], a))[:limit]:
        row = extract.appointments.get(appt_id)
        if breaker.open:
            _record(rep, log_path, BotEvent("eligibility", appt_id, "not_attempted", breaker.reason))
            continue
        if row is None:
            _record(rep, log_path, BotEvent("eligibility", appt_id, "skipped", "appointment not in the practice extract"))
            continue
        claim = next((c for c in extract.claims.values() if c.member_id == row.get("patient_ref")), None)
        ctrl += 1
        dos = date.fromisoformat(row["appt_date"])
        payer_name = claim.payer_name if claim and claim.payer_id == row["payer_id"] else row["payer_id"]
        ref = f"BOT{appt_id}"
        req = write_270(row["payer_id"], payer_name, row["patient_ref"], claim.last if claim else "",
                        claim.first if claim else "", claim.dob if claim else "", dos, ref, ctrl, when)  # fmt: skip
        try:
            text = guarded_call(client.check_eligibility, req, retries, backoff)
        except CallFailed as e:
            breaker.fail(e.kind)
            _record(rep, log_path, BotEvent("eligibility", appt_id, "error", f"clearinghouse call failed: {e.kind}"))
            continue
        try:
            txs = read_transactions(text)
            if not txs or txs[0].st01 != "271":
                raise X12Error("not a 271")
        except X12Error:
            breaker.fail("bad_response")
            _record(rep, log_path, BotEvent("eligibility", appt_id, "bad_response", "reply is not a valid 271; not kept"))
            continue
        if ref not in _refs(txs[0]):
            breaker.fail("bad_response")
            _record(rep, log_path, BotEvent("eligibility", appt_id, "bad_response",
                                            "reply does not echo this request; not kept"))  # fmt: skip
            continue
        breaker.ok()
        name = _write(out_dir, f"271_{appt_id}.x12", text)
        try:
            r = parse_271(txs[0], SALT_FOR_PARSE)[0]
            outcome = "coverage_inactive" if not r.active else "other_payer" if r.other_payer else "active"
            detail = f"member {mask(row['patient_ref'])}, {row['payer_id']}, visit {dos}"
        except X12Error:
            outcome, detail = "not_found", f"payer could not find member {mask(row['patient_ref'])}"
        _record(rep, log_path, BotEvent("eligibility", appt_id, outcome, detail, "", [name]))
    return rep


def status_bot(engine: Engine, tenant_id: int, extract: PmExtract, client: ClearinghouseClient, out_dir: Path,
               when: date, limit: int = 25, log_path: Path | None = None, retries: int = 2,
               backoff: float = 0.0, breaker_limit: int = 3) -> BotReport:  # fmt: skip
    rep = BotReport("status")
    todo = latest_decisions(engine, tenant_id, "a7_ar", "claim")
    ctrl = 91000
    breaker = Breaker(breaker_limit)
    for claim_id in sorted(todo)[:limit]:
        claim = extract.claims.get(claim_id)
        if breaker.open:
            _record(rep, log_path, BotEvent("status", claim_id, "not_attempted", breaker.reason))
            continue
        if claim is None:
            _record(rep, log_path, BotEvent("status", claim_id, "skipped", "claim not in the practice extract"))
            continue
        ctrl += 1
        ans = extract.answers.get(claim_id)
        req = write_276(claim, ans.payer_claim_no if ans else "", f"BOT{claim_id}", ctrl, when)
        try:
            text = guarded_call(client.claim_status, req, retries, backoff)
        except CallFailed as e:
            breaker.fail(e.kind)
            _record(rep, log_path, BotEvent("status", claim_id, "error", f"clearinghouse call failed: {e.kind}"))
            continue
        try:
            answers = parse_277_status(text)
        except X12Error:
            breaker.fail("bad_response")
            _record(rep, log_path, BotEvent("status", claim_id, "bad_response", "reply is not a valid 277; not kept"))
            continue
        st = next((a for a in answers if a.claim_id == claim_id), None)
        if st is None:
            breaker.fail("bad_response")
            _record(rep, log_path, BotEvent("status", claim_id, "bad_response",
                                            "reply is for a different claim; not kept"))  # fmt: skip
            continue
        breaker.ok()
        name = _write(out_dir, f"277_{claim_id}.x12", text)
        meaning = {"A1": "acknowledged", "A2": "accepted", "A3": "rejected", "A4": "rejected", "P1": "pending",
                   "F1": "paid", "F2": "denied", "E1": "not_found"}.get(st.category, st.category)
        _record(rep, log_path, BotEvent("status", claim_id, meaning, f"{claim.payer_id}, category {st.category}:{st.code}",
                                        "", [name]))  # fmt: skip
    return rep


LEDGER_NAME = "sent_ledger.jsonl"
BLOCKING = {"sending", "accepted", "rejected_again", "unknown_sent"}  # states after which the bot never sends again


def _ledger_state(path: Path) -> dict[str, str]:
    state: dict[str, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                d = json.loads(line)
                state[d["key"]] = d["state"]
    return state


def _ledger_add(path: Path, key: str, state: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"key": key, "state": state}, sort_keys=True) + "\n")


def resubmission_bot(engine: Engine, tenant_id: int, extract: PmExtract, client: ClearinghouseClient, out_dir: Path,
                     when: date, limit: int = 25, log_path: Path | None = None, retries: int = 2,
                     backoff: float = 0.0, breaker_limit: int = 3, ledger_path: Path | None = None) -> BotReport:  # fmt: skip
    """Sends each returned claim's replacement at most once. The ledger is written before the send; a send whose answer
    is lost (timeout, 5xx) stays `unknown_sent` and is never retried by the bot: the status bot or a person resolves it.
    Only a connection error (the request never reached the clearinghouse) is retried."""
    rep = BotReport("resubmission")
    todo = latest_decisions(engine, tenant_id, "a6_submission", "claims")
    ctrl = 92000
    breaker = Breaker(breaker_limit)
    ledger = ledger_path or (out_dir / LEDGER_NAME)
    for claim_id in sorted(todo)[:limit]:
        claim, ans = extract.claims.get(claim_id), extract.answers.get(claim_id)
        if breaker.open:
            _record(rep, log_path, BotEvent("resubmission", claim_id, "not_attempted", breaker.reason))
            continue
        if claim is None:
            _record(rep, log_path, BotEvent("resubmission", claim_id, "skipped", "claim not in the practice extract"))
            continue
        if ans is None or ans.state != "rejected":
            _record(rep, log_path, BotEvent("resubmission", claim_id, "skipped", "claim is not currently rejected"))
            continue
        key = f"{claim_id}|{ans.payer_claim_no}"
        prior = _ledger_state(ledger).get(key)
        if prior in BLOCKING:
            _record(rep, log_path, BotEvent("resubmission", claim_id, "skipped", f"already sent once ({prior})"))
            continue
        ctrl += 1
        text = write_corrected_837(claim, ans.payer_claim_no, ctrl, when)
        sent = _write(out_dir, f"837P_{claim_id}_corrected.x12", text)
        _ledger_add(ledger, key, "sending")
        try:
            res = guarded_call(client.submit_claim, text, retries, backoff, retry_kinds=("connection",))
        except CallFailed as e:
            breaker.fail(e.kind)
            if e.kind in ("timeout", "server"):  # the clearinghouse may have processed it
                _ledger_add(ledger, key, "unknown_sent")
                _record(rep, log_path, BotEvent("resubmission", claim_id, "unknown_sent",
                                                f"no usable answer ({e.kind}); not resent, needs a status check", sent))
            else:  # never reached the clearinghouse, or it refused the request outright
                _ledger_add(ledger, key, "refused")
                _record(rep, log_path, BotEvent("resubmission", claim_id, "error",
                                                f"clearinghouse call failed: {e.kind}", sent))  # fmt: skip
            continue
        results = res.get("results") if isinstance(res, dict) else None
        if not results or claim_id not in {r.get("claim") for r in results}:
            breaker.fail("bad_response")
            _ledger_add(ledger, key, "unknown_sent")
            _record(rep, log_path, BotEvent("resubmission", claim_id, "bad_response",
                                            "answer does not cover this claim; not resent", sent))  # fmt: skip
            continue
        breaker.ok()
        names = [_write(out_dir, f"{kind}_{claim_id}.x12", res[kind]) for kind in ("999", "277CA") if res.get(kind)]
        ok = all(r["ok"] for r in results)
        _ledger_add(ledger, key, "accepted" if ok else "rejected_again")
        _record(rep, log_path, BotEvent("resubmission", claim_id, "accepted" if ok else "rejected_again",
                                        "; ".join(r["reason"] for r in results), sent, names))  # fmt: skip
    return rep
