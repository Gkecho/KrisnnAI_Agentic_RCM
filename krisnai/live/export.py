# ruff: noqa: E501
"""Turn a finished live-stream run into the data the product preview's "Tools in action" screen shows (`tools_stream.js`).

Everything in it is already in the run folder: the summary, the scorecard, the remit ledger totals and the event log. Nothing
is invented here, and the file says in its own header that it is a recorded synthetic run.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from krisnai.knowledge.demo import demo_book
from krisnai.live.score import _decisions, write_reports

NOTE = ("A recorded run on synthetic data, in shadow mode. The payer is our own simulator, so its rates and deviations are demo settings. "
        "'Real time' is a simulated clock, one day at a time.")


AGENT_NAME = {"a1_clearance": "Gatekeeper (A1)", "a2_authorization": "Permit Clerk (A2)", "a3_documentation": "Note Chaser (A3)", "a4_coding": "Code Whisperer (A4)",
              "a5_prevention": "Mirror (A5)", "a6_submission": "Courier (A6)", "a7_ar": "Hunter (A7)", "a8_denial": "Advocate (A8)", "a10_underpay": "Auditor (A10)",
              "a11_cash": "Bookkeeper (A11)", "a12_patient": "Concierge (A12)", "a13_credentialing": "Credentialing (A13)", "a14_tower": "Captain (A14)"}  # fmt: skip
ACTION_SAYS = {
    "a1_coverage_exception_review": "Flagged, before the visit, that the payer reports the patient's coverage as inactive.",
    "a7_status_check_task": "Raised a task to chase the payer: no answer had come back for this claim.",
    "a8_fix_task": "Raised a fix task: this denial looks correctable (for example wrong or missing information), so a person fixes and resubmits.",
    "a8_appeal_task": "Raised an appeal task and prepared an appeal draft (a stub: nothing was sent anywhere).",
    "a8_write_off_review": "Raised a write-off review for a person to decide. It never writes anything off by itself.",
    "a10_dispute_review": "Raised a dispute review: the payer paid less than the contract fee schedule.",
    "a12_statement_task": "Raised a task to send the patient a statement for the balance they owe.",
}  # fmt: skip
NO_ACTION_SAYS = {
    "a1_clearance": "Checked the appointment's eligibility and found nothing to flag.",
    "a4_coding": "Compared the billed level with what the note documents and found nothing to flag.",
    "a5_prevention": "Checked the claim before release (required fields, duplicates, filing deadline, code pairs, unit limits) and found nothing to hold.",
    "a10_underpay": "Compared what the payer paid with the contract fee schedule and found no shortfall.",
}  # fmt: skip
SKIP_FACTS = {"as_of", "claim", "appt", "visit", "lineage", "claim_matched", "history_n", "history_wins"}


def _fact_text(v) -> str:  # noqa: ANN001
    if isinstance(v, list):
        if v and isinstance(v[0], dict):
            return "; ".join(str(x.get("kind") or x.get("cpt") or next(iter(x.values()), "")) + (f" ({x['detail']})" if x.get("detail") else "") for x in v)
        return ", ".join(str(x) for x in v)
    return str(v)


def agent_log(run: Path) -> dict[str, list[dict]]:
    """For every claim, appointment and visit: what each agent did and how (the rules it checked, the facts it looked at)."""
    from sqlalchemy import create_engine, select

    import krisnai.model as m
    from krisnai.model import tenant_session

    if not (run / "engine.sqlite").exists():
        return {}
    eng = create_engine(f"sqlite:///{run / 'engine.sqlite'}")
    raw: dict[str, list[dict]] = {}
    with tenant_session(eng, 1) as s:
        known = {x.id: x.known_at for x in s.scalars(select(m.Event))}
        for rec in s.scalars(select(m.DecisionRecord).order_by(m.DecisionRecord.id)):
            p = json.loads(rec.action_payload)
            keys = [p[k] for k in ("claim", "appt", "visit") if p.get(k)] + list(p.get("claims") or [])
            if not keys:
                continue
            snap = json.loads(rec.input_snapshot or "{}").get("data", {})
            card = p.get("card") or {}
            no_act = rec.action_type == "no_action"
            entry = {
                "agent": rec.agent_id, "name": AGENT_NAME.get(rec.agent_id, rec.agent_id), "action": rec.action_type, "day": known[rec.event_id].date().isoformat(),
                "did": NO_ACTION_SAYS.get(rec.agent_id, "Looked and raised nothing.") if no_act else ACTION_SAYS.get(rec.action_type, rec.action_type.replace("_", " ").capitalize() + "."),
                "raised": not no_act, "title": card.get("title", ""), "owner": card.get("owner", ""), "deadline": card.get("deadline", ""),
                "expected": str(rec.materiality_amount) if rec.materiality_amount is not None else "", "confidence": str(rec.confidence) if rec.confidence is not None else "",
                "level": f"L{rec.autonomy_level} {rec.mode}",
                "rules": [{"rule": r["rule"].replace("_", " "), "ok": bool(r["result"]), "detail": str(r.get("detail", ""))} for r in json.loads(rec.rules_fired or "[]")],
                "facts": {k: _fact_text(v)[:110] for k, v in snap.items() if k not in SKIP_FACTS and v not in (None, "", [], {})},
            }  # fmt: skip
            for k in keys:
                raw.setdefault(k, []).append(entry)
    eng.dispose()
    out: dict[str, list[dict]] = {}
    for k, entries in raw.items():  # the same finding seen on several days is one entry with a date range
        grouped: dict[tuple, dict] = {}
        for en in entries:
            sig = (en["agent"], en["action"], json.dumps(en["rules"], sort_keys=True))
            g = grouped.get(sig)
            if g is None:
                grouped[sig] = {**en, "first": en["day"], "last": en["day"], "times": 1}
            else:
                g["last"], g["times"] = en["day"], g["times"] + 1
        out[k] = sorted(grouped.values(), key=lambda g: (g["first"], g["agent"]))
    return out


def claim_traces(run: Path, st: dict, events: list[dict]) -> list[dict]:
    """One trace per encounter: the coder's checks, the payer's hidden decision, the agents' work and the timeline."""
    truth = {r["claim_id"]: r for r in csv.DictReader((run / "truth.csv").read_text("utf-8").splitlines())} if (run / "truth.csv").exists() else {}
    dec = _decisions(run) if (run / "engine.sqlite").exists() else {}
    log = agent_log(run)
    claims = []
    for eid, e in sorted(st["enc"].items()):
        keys = {e["appt"], e["visit_id"], e.get("claim", "")} - {""}
        work = [{"agent": ag, "action": d["action"], "title": d["title"], "day": d["known"][:10]}
                for ag, by in sorted(dec.items()) for k in sorted(keys) for d in by.get(k, [])]  # fmt: skip
        cf = None
        f = run / "claims" / f"{e.get('claim', '')}.837"
        if e.get("billed_on") and f.exists():  # the form is read back from the claim file itself, so it shows exactly what was sent
            from krisnai.live.claim_form import claim_form

            cf = claim_form(f.read_text("utf-8"))
        claims.append({
            "form": cf["form"] if cf else None, "edi": cf["lines"] if cf else None,
            "id": eid, "claim": e.get("claim", "") if e.get("billed_on") else "", "visit_type": e["visit_type"], "booking": e["booking"], "visit_day": e["visit_day"],
            "active": e.get("active"), "stage": e["stage"], "coding": e.get("coding"), "approval": e.get("approval", ""), "payer_id": e.get("payer_id", ""),
            "payer": truth.get(e.get("claim", "")), "work": work,
            "agents": sorted((a for k in sorted(keys) for a in log.get(k, [])), key=lambda a: (a["first"], a["agent"])), "events": [x for x in events if x["subject"] in keys],
        })  # fmt: skip
    return claims


def trace_run(run: Path) -> dict:
    """What the demo service returns for a run of typed-in visits: traces and the remit ledger, with no scoring (there is no answer key)."""
    from krisnai.live.score import reconcile

    st = json.loads((run / "state.json").read_text("utf-8"))
    events = [json.loads(ln) for ln in (run / "events.jsonl").read_text("utf-8").splitlines() if ln] if (run / "events.jsonl").exists() else []
    for ev in events:
        ev.pop("key", None)
    led = reconcile(run, None, st) if (run / "truth.csv").exists() else None
    return {"claims": claim_traces(run, st, events), "events": events, "day": st.get("day"),
            "ledger": {k: led[k] for k in ("remits_read", "billed_on_remits", "remitted_by_payer", "patient_responsibility",
                                           "contractual_adjustment", "denied_billed", "cash_collected", "cash_note")} if led else None}  # fmt: skip


def build(run: Path) -> dict:
    sc = write_reports(run)
    st = json.loads((run / "state.json").read_text("utf-8"))
    summary = json.loads((run / "summary.json").read_text("utf-8"))
    events = [json.loads(ln) for ln in (run / "events.jsonl").read_text("utf-8").splitlines() if ln]
    for e in events:
        e.pop("key", None)
        e["detail"] = e["detail"][:170]
    enc = st["enc"].values()
    coding = Counter(e["coding"]["route"] for e in enc if e.get("coding"))
    led = sc["ledger"]
    outcomes = summary["payer_outcomes"]
    funnel = [
        ["Booked and eligibility checked", len(st["enc"])],
        ["Visited, note and transcript in the EMR", sum(1 for e in enc if e.get("eno"))],
        ["Auto-accepted by the coding policy", coding.get("auto", 0)],
        ["Sent to a coder (checks failed or sampled)", coding.get("coder", 0)],
        ["Billed (837P written by the EMR)", sum(1 for e in enc if e.get("billed_on"))],
        ["Remit received from the payer", led["remits_read"]],
        ["Paid", outcomes.get("paid", 0)], ["Denied", outcomes.get("denied", 0)], ["Underpaid", outcomes.get("underpaid", 0)],
    ]  # fmt: skip
    claims = claim_traces(run, st, events)
    return {
        "book": json.loads(demo_book().to_json()), "claims": claims,
        "note": NOTE, "start": st["config"]["start"], "end": st["day"], "encounters": len(st["enc"]), "summary": summary,
        "funnel": funnel, "events": events,
        "score": {
            "found": sc["found"], "problems": sc["problems"], "recognized": sc["recognized_as_contradiction"],
            "false_alarms": len(sc["false_alarms"]), "agents_read_the_knowledge_book": sc["agents_read_the_knowledge_book"],
            "classes": [{"label": c["label"], "n": c["n"], "found": c["found"], "missed": [x["claim"] for x in c["missed"]], "kind": k} for k, c in sc["by_class"].items()],
            "eligibility": sc["eligibility"], "coding": {k: (len(v) if isinstance(v, list) else v) for k, v in sc["coding"].items()},
            "a4": sc["a4_findings_on_stream"],
        },  # fmt: skip
        "ledger": {k: led[k] for k in ("remits_read", "billed_on_remits", "remitted_by_payer", "patient_responsibility", "contractual_adjustment",
                                      "denied_billed", "cash_collected", "cash_note")} | {"tie_out_mismatches": len(led["tie_out_mismatches"])},  # fmt: skip
    }


def write_js(run: Path, dest: Path) -> dict:
    data = build(run)
    dest.write_text("window.TOOLS_STREAM=" + json.dumps(data, separators=(",", ":")) + ";\n", encoding="utf-8")
    return data
