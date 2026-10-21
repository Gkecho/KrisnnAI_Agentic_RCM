# ruff: noqa: E501
"""S5 of the live encounter stream: score the agents against the payer's hidden decisions, and reconcile the remits.

The payer simulator kept a truth log of every decision it made, including where it deviated from its own published rules.
The agents never saw it. Here the two are laid side by side:

  found          the agent that should act on the problem raised work on that claim
  missed         it did not
  false alarm    a payer-problem agent (A8 denials, A10 underpayments) raised work on a claim the payer handled correctly
  recognized     the agent said the payer contradicted what it published (no agent can yet: none reads the Knowledge Book)

The reconciliation reads the 835 files themselves and ties them to the truth log. A remit is money the payer says it paid,
not cash in the bank: no deposits exist in this simulation, so cash collected is always shown as 0.
"""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine, select

import krisnai.model as m
from krisnai.ingest.x12 import read_transactions
from krisnai.live.transcripts import generate
from krisnai.model import tenant_session

PROBLEM_AGENT = {"denied": "a8_denial", "underpaid": "a10_underpay"}
NO_ACTION = "no_action"
DEVIATION_DENIALS = ("wrong_denial", "stale_version", "unpublished_rule")


def _decisions(run: Path) -> dict[str, dict[str, list[dict]]]:
    """agent -> key (claim, appointment or visit) -> its non-'no_action' decisions, with the card text."""
    eng = create_engine(f"sqlite:///{run / 'engine.sqlite'}")
    out: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    with tenant_session(eng, 1) as s:
        known = {e.id: e.known_at for e in s.scalars(select(m.Event))}
        for rec in s.scalars(select(m.DecisionRecord)):
            if rec.action_type == NO_ACTION:
                continue
            p = json.loads(rec.action_payload)
            keys = [p[k] for k in ("claim", "appt", "visit") if p.get(k)] + list(p.get("claims") or [])
            for k in keys:
                out[rec.agent_id][k].append({"action": rec.action_type, "known": known[rec.event_id].isoformat(), "text": json.dumps(p),
                                             "title": (p.get("card") or {}).get("title", "")})
    eng.dispose()
    return out


def _truth(run: Path) -> list[dict]:
    return list(csv.DictReader((run / "truth.csv").read_text("utf-8").splitlines()))


def _kind(r: dict) -> str:
    if r["outcome"] == "underpaid" or r["deviation"] == "underpay_off_schedule":
        return "underpaid"
    if r["deviation"] in DEVIATION_DENIALS:
        return "denied_deviation"
    if r["outcome"] == "denied":
        return "denied_published" if r["published"] == "denied" else "denied_ordinary"
    return "paid_clean"


LABEL = {"denied_ordinary": "ordinary denial", "denied_published": "denial the book predicts (coverage lapsed)",
         "denied_deviation": "denial that contradicts the published rules", "underpaid": "underpayment below the fee schedule",
         "paid_clean": "paid correctly"}  # fmt: skip


def score(run: Path) -> dict:
    st = json.loads((run / "state.json").read_text("utf-8"))
    cfg = st["config"]
    truth = _truth(run)
    dec = _decisions(run)
    by_class: dict[str, dict] = {k: {"label": v, "n": 0, "found": 0, "missed": [], "recognized": 0} for k, v in LABEL.items()}
    false_alarms: list[dict] = []
    recog = _recognitions(run)
    for r in truth:
        k = _kind(r)
        c = by_class[k]
        c["n"] += 1
        agent = PROBLEM_AGENT.get("underpaid" if k == "underpaid" else "denied")
        if k == "paid_clean":
            for ag in PROBLEM_AGENT.values():
                for d in dec.get(ag, {}).get(r["claim_id"], []):
                    false_alarms.append({"claim": r["claim_id"], "agent": ag, "action": d["action"]})
            continue
        got = dec.get(agent, {}).get(r["claim_id"], [])
        by_cards = bool(got) and any(w in d["text"].lower() for d in got for w in ("knowledge book", "published rule", "contradicts"))
        if k == "denied_deviation" and (by_cards or r["claim_id"] in recog):  # S8: the responder's recognition events count too
            c["recognized"] += 1
        if got:
            c["found"] += 1
        else:
            c["missed"].append({"claim": r["claim_id"], "outcome": r["outcome"], "carc": r["carc"], "deviation": r["deviation"]})
    # coverage lapsed before the visit: did Gatekeeper (A1) raise a coverage exception?
    elig = {"inactive": 0, "flagged": 0, "flagged_before_visit": 0, "active": 0, "false_alarms": 0}
    for e in st["enc"].values():
        got = dec.get("a1_clearance", {}).get(e["appt"], [])
        exc = [d for d in got if "coverage" in d["action"]]
        if e.get("active") is False:
            elig["inactive"] += 1
            if exc:
                elig["flagged"] += 1
                if any(d["known"][:10] < e["visit_day"] for d in exc):
                    elig["flagged_before_visit"] += 1
        elif e.get("active"):
            elig["active"] += 1
            elig["false_alarms"] += 1 if exc else 0
    # coding against the answer key
    visits = {f"SYNVS{i:05d}L1": v for i, v in enumerate(generate(cfg["seed"], cfg["count"], date.fromisoformat(cfg["start"])), start=1)}
    coding = {"auto_correct": 0, "auto_wrong": [], "problem_routed_right": 0, "problem_missed": [], "clean_to_coder": 0}
    for e in st["enc"].values():
        rc, v = e.get("coding"), visits.get(e["visit_id"])
        if not rc or not v:
            continue
        if v.expected.route == "auto":
            if rc["route"] == "auto":
                ok = rc["cpt"] == v.expected.cpt and rc["dx"][0][0] == v.expected.dx
                coding["auto_correct"] += ok
                if not ok:
                    coding["auto_wrong"].append(e["visit_id"])
            else:
                coding["clean_to_coder"] += 1
        elif rc["route"] == "coder" and rc["reason"] == v.expected.reason:
            coding["problem_routed_right"] += 1
        else:
            coding["problem_missed"].append(e["visit_id"])
    a4 = sum(len(v) for v in dec.get("a4_coding", {}).values())
    problems = [c for k, c in by_class.items() if k != "paid_clean"]
    out = {
        "claims": len(truth), "by_class": by_class, "false_alarms": false_alarms,
        "found": sum(c["found"] for c in problems), "problems": sum(c["n"] for c in problems),
        "recognized_as_contradiction": sum(c["recognized"] for c in problems),
        "eligibility": elig, "coding": coding, "a4_findings_on_stream": a4,
        "agents_read_the_knowledge_book": False,
        "note": "scored against the payer simulator's own hidden decisions: a measure of the loop on synthetic data, not of accuracy on real payers",
    }  # fmt: skip
    out["ledger"] = reconcile(run, truth, st)
    out["replies"] = replies_section(st, truth, recog)  # S8, additive
    return out


def _recognitions(run: Path) -> set[str]:
    """Claims where the S8 responder said the payer contradicted its own published rule (from events.jsonl)."""
    p = run / "events.jsonl"
    if not p.exists():
        return set()
    rows = (json.loads(ln) for ln in p.read_text("utf-8").splitlines() if ln)
    return {r["subject"] for r in rows if r["step"] == "8 reply: recognized"}


def replies_section(st: dict, truth: list[dict], recog: set[str]) -> dict:
    """Replies sent by kind, the payer's answer to each, and how many claims ended settled. Zeros when replies were off."""
    sent: dict[str, int] = defaultdict(int)
    answers: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    approvals: dict[str, int] = defaultdict(int)
    for e in st["enc"].values():
        for r in e.get("rounds", []):
            sent[r["plan"]["kind"]] += 1
            approvals[r["plan"]["approval"]] += 1
            if r.get("answer"):
                answers[r["answer"]["kind"]][r["answer"]["outcome"]] += 1
    billed = [e for e in st["enc"].values() if e.get("billed_on")]
    settled = [e for e in billed if e["stage"] in ("settled", "patient_balance")]
    dev = {r["claim_id"] for r in truth if r["deviation"] in DEVIATION_DENIALS}
    return {
        "enabled": bool(st["config"].get("replies")), "sent_by_kind": dict(sent), "outcome_by_kind": {k: dict(v) for k, v in answers.items()},
        "approvals": dict(approvals), "claims_billed": len(billed), "settled": len(settled), "settled_share": round(len(settled) / len(billed), 3) if billed else 0.0,
        "in_review": sum(1 for e in billed if e["stage"] == "review"), "recognized_claims": len(recog), "recognized_true": len(recog & dev), "recognized_false": len(recog - dev),
        "note": "second-round answers come from the payer simulator's reply rules (krisnai/live/payer_replies.py), not from any real payer",
    }  # fmt: skip


def _amt(x: str) -> Decimal:
    return Decimal(x or "0")


def reconcile(run: Path, truth: list[dict] | None = None, st: dict | None = None) -> dict:
    """Read every 835 issued, build a per-claim ledger, and tie it to the truth log. Cash collected is always 0 here."""
    truth = truth if truth is not None else _truth(run)
    st = st or json.loads((run / "state.json").read_text("utf-8"))
    allfiles = sorted({p for d in ("inbox", "archive") for p in (run / d).rglob("835_*.835")}, key=lambda p: p.name)
    # S8: a second remit (the payer's answer to a reply) carries the claim id `<claim>-R<n>` and only that round's money; it is read
    # on its own so the first remit is never counted twice, and it ties out to truth_replies.csv instead of truth.csv
    files = [p for p in allfiles if not _REPLY_FILE.search(p.name)]
    reply_files = [p for p in allfiles if _REPLY_FILE.search(p.name)]
    rows: dict[str, dict] = {}
    for p in files:
        for tx in read_transactions(p.read_text("utf-8")):
            cur = None
            for seg in tx.segments:
                if seg.id == "CLP":
                    cur = rows.setdefault(seg[1], {"claim": seg[1], "billed": _amt(seg[3]), "paid": Decimal(0), "patient_resp": _amt(seg[5]), "contractual": Decimal(0), "status": seg[2], "files": set()})
                    cur["paid"] = _amt(seg[4])
                    cur["files"].add(p.name)
                elif seg.id == "CAS" and cur is not None and seg[1] == "CO" and seg[2] == "45":
                    cur["contractual"] += _amt(seg[3])
    tie_out = []
    by_truth = {r["claim_id"]: r for r in truth}
    for cid, r in rows.items():
        t = by_truth.get(cid)
        if t is None or _amt(t["paid"]) != r["paid"]:
            tie_out.append({"claim": cid, "remit": str(r["paid"]), "truth": t["paid"] if t else None})
    second = _second_remits(run, reply_files)
    tie_out += second["mismatches"]
    issued = set(st.get("issued", []))
    total = lambda f: sum((r[f] for r in rows.values()), Decimal(0))  # noqa: E731
    return {
        "remits_read": len(rows), "files": len(files), "duplicate_claims": len(files) - len(rows) if len(files) > len(rows) else 0,
        "billed_on_remits": str(total("billed")), "remitted_by_payer": str(total("paid")), "patient_responsibility": str(total("patient_resp")),
        "contractual_adjustment": str(total("contractual")),
        "denied_billed": str(sum((r["billed"] for r in rows.values() if r["paid"] == 0), Decimal(0))),
        "claims_in_truth": len(truth), "remits_issued_in_state": len(issued),
        "awaiting_remit": [r["claim_id"] for r in truth if r["claim_id"] not in rows],
        "tie_out_mismatches": tie_out,
        "cash_collected": "0.00",
        "cash_note": "A remit is what the payer says it paid. No bank deposits exist in this simulation, so no cash has been collected and none is shown as collected.",
        "by_claim": [{**{k: (str(v) if isinstance(v, Decimal) else v) for k, v in r.items() if k != "files"}} for r in sorted(rows.values(), key=lambda x: x["claim"])],
        # S8, additive: "remitted_by_payer" above stays the FIRST remits only
        "second_remits_read": len(second["rows"]), "remitted_by_replies": str(second["paid"]),
        "remitted_total": str(total("paid") + second["paid"]),
        "by_reply": [{"reply": rid, "paid": str(v["paid"]), "patient_resp": str(v["patient_resp"])} for rid, v in sorted(second["rows"].items())],
    }  # fmt: skip


_REPLY_FILE = re.compile(r"-R\d+\.835$")


def _second_remits(run: Path, files: list[Path]) -> dict:
    rows: dict[str, dict] = {}
    for p in files:
        for tx in read_transactions(p.read_text("utf-8")):
            for seg in tx.segments:
                if seg.id == "CLP":
                    rows[seg[1]] = {"paid": _amt(seg[4]), "patient_resp": _amt(seg[5])}
    tf = run / "truth_replies.csv"
    truth = {r["reply_id"]: r for r in csv.DictReader(tf.read_text("utf-8").splitlines())} if tf.exists() else {}
    bad = [{"claim": rid, "remit": str(v["paid"]), "truth": truth[rid]["paid"] if rid in truth else None} for rid, v in rows.items() if rid not in truth or _amt(truth[rid]["paid"]) != v["paid"]]
    return {"rows": rows, "paid": sum((v["paid"] for v in rows.values()), Decimal(0)), "mismatches": bad}


def write_reports(run: Path) -> dict:
    sc = score(run)
    (run / "scorecard.json").write_text(json.dumps(sc, indent=1, default=str), encoding="utf-8")
    led = sc["ledger"]["by_claim"]
    with (run / "ledger.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["claim", "billed", "paid", "patient_resp", "contractual", "status"])
        w.writeheader()
        w.writerows(led)
    (run / "scorecard.html").write_text(_html(sc), encoding="utf-8")
    return sc


def _html(sc: dict) -> str:
    from html import escape as e

    rows = "".join(f"<tr><td>{e(c['label'])}</td><td>{c['n']}</td><td>{c['found'] if k != 'paid_clean' else '-'}</td><td>{len(c['missed']) if k != 'paid_clean' else '-'}</td></tr>" for k, c in sc["by_class"].items())
    miss = "".join(f"<li>{e(x['claim'])}: {e(x['outcome'])} {e(x['carc'])} {e(x['deviation'])}</li>" for c in sc["by_class"].values() for x in c["missed"]) or "<li>none</li>"
    fa = "".join(f"<li>{e(x['claim'])}: {e(x['agent'])} {e(x['action'])}</li>" for x in sc["false_alarms"]) or "<li>none</li>"
    led, co, el = sc["ledger"], sc["coding"], sc["eligibility"]
    return f"""<!doctype html><meta charset="utf-8"><title>Live stream scorecard</title>
<style>body{{font:15px system-ui;max-width:900px;margin:24px auto;padding:0 16px}}table{{border-collapse:collapse;width:100%}}td,th{{border-bottom:1px solid #ccc;padding:6px;text-align:left}}.b{{background:#fff3cd;padding:10px;border-radius:6px}}</style>
<h1>Live stream: agents against the payer's hidden decisions</h1>
<p class="b"><b>Synthetic, shadow mode.</b> {e(sc['note'])}. The payer is our own simulator; its rates and deviations are demo settings.</p>
<h2>Payer problems: found, missed</h2>
<p><b>{sc['found']} of {sc['problems']}</b> payer problems got work raised by the agent that should act. <b>{sc['recognized_as_contradiction']}</b> were recognized as contradicting the payer's published rules (no agent reads the Knowledge Book yet).</p>
<table><tr><th>Kind</th><th>Claims</th><th>Found</th><th>Missed</th></tr>{rows}</table>
<h3>Missed</h3><ul>{miss}</ul><h3>False alarms (work raised on claims the payer handled correctly)</h3><ul>{fa}</ul>
<h2>Eligibility</h2><p>{el['inactive']} patients had lapsed coverage; Gatekeeper raised a coverage exception for {el['flagged']} ({el['flagged_before_visit']} before the visit). False alarms on {el['active']} active patients: {el['false_alarms']}.</p>
<h2>Coding against the answer key</h2><p>{co['auto_correct']} auto-accepted visits had the right code and diagnosis; {len(co['auto_wrong'])} wrong. {co['problem_routed_right']} problem visits were routed to a coder with the right reason; {len(co['problem_missed'])} slipped through. {co['clean_to_coder']} clean visits went to a coder for the quality check or because a cap applied. A4 raised {sc['a4_findings_on_stream']} findings.</p>
<h2>Remits reconciled to the payer's truth log</h2>
<p>{led['remits_read']} remits read from the 835 files. Billed {e(led['billed_on_remits'])}, the payer remitted {e(led['remitted_by_payer'])}, patient responsibility {e(led['patient_responsibility'])}, contractual adjustment {e(led['contractual_adjustment'])}. Tie-out mismatches: {len(led['tie_out_mismatches'])}. Awaiting a remit: {len(led['awaiting_remit'])}.</p>
<p class="b"><b>Cash collected: {e(led['cash_collected'])}.</b> {e(led['cash_note'])}</p>"""
