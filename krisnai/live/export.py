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
    truth = {r["claim_id"]: r for r in csv.DictReader((run / "truth.csv").read_text("utf-8").splitlines())}
    dec = _decisions(run)
    claims = []
    for eid, e in sorted(st["enc"].items()):
        keys = {e["appt"], e["visit_id"], e.get("claim", "")} - {""}
        work = [{"agent": ag, "action": d["action"], "title": d["title"], "day": d["known"][:10]}
                for ag, by in sorted(dec.items()) for k in sorted(keys) for d in by.get(k, [])]  # fmt: skip
        claims.append({
            "id": eid, "claim": e.get("claim", ""), "visit_type": e["visit_type"], "booking": e["booking"], "visit_day": e["visit_day"],
            "active": e.get("active"), "stage": e["stage"], "coding": e.get("coding"), "approval": e.get("approval", ""),
            "payer": truth.get(e.get("claim", "")), "work": work, "events": [x for x in events if x["subject"] in keys],
        })  # fmt: skip
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
