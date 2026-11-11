"""Write the site's ui_data.js / ui_data.json from what Replay persisted in krisnnai_r2.

Reads the agent_* tables (written by r2_persist.py) and R2 reference data. Writes the EXISTING export schema (schema = 1; same top-level keys as
krisnnai/demo/export.py) so the product preview, which reads `window.KRISNNAI_LIVE`, works unchanged. Nothing is written to the database and nothing
is written into the site folder: the default output is out/ui/.

Point in time (hard rule 9): every figure is computed as of `as_of` (default: the last day any agent ran). A task is open as of a date when it was
created by then and not completed by then; a finding is resolved as of a date only if resolved_date is on or before it.

Money is a two-decimal string. No patient data is read at all: claims are shown by claim_number (a synthetic internal number), other work by entity
reference ("APT-123"), payers by payer_code.

    python tools/replay/r2_export_ui.py [--out out/ui] [--as-of 2026-11-02] [--tenant 1]

build_payload(inputs, as_of) is pure (no database) so it can be tested with hand-made inputs; load_inputs(conn, ...) fills `inputs` from R2.
"""
import argparse
import datetime as dt
import json
import pathlib
import re
import statistics
import sys
from collections import Counter, defaultdict
from decimal import Decimal

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE.parents[0] / "synthea"))

SCHEMA = 1
SHADOW_NOTE = "Rows written by Replay (source = 'replay') on the synthetic R2 database; shadow mode, nothing was sent anywhere."
QUEUE_PER_KEY = 40
FILING_RISK_DAYS = 30
DAYS = 90
HISTORY_WEEKS = 13
MIN_TASKS = 20
D = Decimal
TOP_KEYS = ["agents", "baseline", "meta", "queue", "queue_stats", "queue_totals", "reference", "replay", "schema", "slices", "staff"]

# ---------------------------------------------------------------- vocabulary the site already uses
SITE_AGENT = {"A1": "a1_clearance", "A2": "a2_authorization", "A3": "a3_documentation", "A4": "a4_coding", "A5": "a5_prevention", "A6": "a6_submission", "A7": "a7_ar",
              "A8": "a8_denial", "A9": "a9_learning", "A10": "a10_underpay", "A11": "a11_cash", "A12": "a12_patient", "A13": "a13_credentialing", "A14": "a14_tower",
              "A15": "a15_investigator"}
AGENT_INFO = [
    ("A1", "Pre-visit financial clearance", "Checks coverage, other-payer and eligibility 72 h and 24 h before a visit."),
    ("A2", "Authorization intelligence", "Finds visits that need an authorization that is missing, expired, pending or used up."),
    ("A3", "Documentation completeness", "Finds visits with a missing or unsigned note, missing elements, late or missing charges."),
    ("A4", "Coding audit (suggestions only)", "Compares the billed E/M level with the level the note supports; a coder decides."),
    ("A5", "Claim prevention", "Scores each claim before the payer sees it: duplicates, bundling, unit limits, filing deadline."),
    ("A6", "Submission and response", "Turns rejections (999/277CA) into a correction task with a deadline."),
    ("A7", "AR next-best-action", "Ranks open claims by what to do next and when."),
    ("A8", "Denial resolution and appeal", "Routes each denial to an owner and drafts the appeal package with a deadline."),
    ("A9", "Denial prevention learning", "Finds payer + CPT + reason denial patterns and proposes a rule; a named person approves."),
    ("A10", "Contract and underpayment", "Compares each payment with the contract and finds payer-wide short-pay patterns."),
    ("A11", "Payment posting and reconciliation", "Finds missing, short, duplicate or unposted deposits and payments."),
    ("A12", "Patient financial engagement (staff-facing)", "Worklist of patient balances with a plain-language explanation; sends nothing."),
    ("A13", "Credentialing and enrollment", "Finds provider enrollments that are missing, pending too long, expiring or excluded."),
    ("A14", "Control tower", "One queue across agents: backlog, deadlines, cash forecast and signals."),
    ("A15", "Revenue assurance investigator", "Watches realisation against contract by payer and CPT and explains each drop."),
]
# (agent, replay task_type) -> the site's action type; owner_role (+agent) -> the site's owner
ACTION = {("A1", "coverage_follow_up"): "a1_coverage_exception_review", ("A2", "authorization_check"): "a2_auth_request_task", ("A3", "unsigned_note"): "a3_signature_task", ("A3", "unbilled_visit"): "a3_unbilled_task",
          ("A4", "code_review"): "a4_coding_review", ("A5", "claim_hold_review"): "a5_hold_review", ("A6", "fix_rejection"): "a6_rejection_task",
          ("A7", "claim_follow_up"): "a7_escalate_review", ("A8", "denial_work"): "a8_fix_task", ("A9", "rule_review"): "a9_rule_proposal_review",
          ("A10", "dispute_package"): "a10_dispute_review", ("A11", "post_remit"): "a11_posting_task", ("A12", "patient_follow_up"): "a12_followup_task",
          ("A13", "revalidation"): "a13_enrollment_task", ("A15", "dispute_package"): "a15_investigation_review"}
# The site's personas (product.html PERSONAS) pick queue items by owner `o` or agent `a`: biller {o: biller | o: billing + a6/a7}, denials {a: a8_denial}, arlead {o: ar_lead},
# poster {o: payment_poster}, finance {o: finance}, provider {o: provider}, coder {o: coder/coding + a4/a5}, frontdesk {o: front_desk}, manager {o: practice_manager},
# owner {o: revenue_assurance_lead}. The engine's owner_role is mapped to those words here, so product.html needs no change.
OWNER = {"front_desk": "front_desk", "biller": "biller", "denial_specialist": "billing", "coder": "coder", "ar_specialist": "ar_lead", "payment_poster": "payment_poster",
         "billing_lead": "billing", "manager": "practice_manager", "provider": "provider", "patient_billing": "patient_billing"}
# agent-wide overrides: A10 disputes are approved by finance; A12 balances are patient billing; A13 enrollment; A15 variances go to the revenue-assurance lead
OWNER_BY_AGENT = {"A10": "finance", "A12": "patient_billing", "A13": "credentialing", "A15": "revenue_assurance_lead"}
LABEL = {"a1_coverage_exception_review": "Coverage exceptions", "a2_auth_request_task": "Authorization requests", "a3_signature_task": "Note signatures", "a3_unbilled_task": "Unbilled visits",
         "a4_coding_review": "Coding reviews", "a5_hold_review": "Claim holds", "a6_rejection_task": "Rejected claims", "a7_escalate_review": "Unpaid claim escalation",
         "a8_appeal_task": "Appeals", "a8_fix_task": "Denial fixes", "a9_rule_proposal_review": "Rule approvals", "a10_dispute_review": "Underpayment disputes",
         "a11_posting_task": "Remit posting", "a12_followup_task": "Patient balances", "a13_enrollment_task": "Enrollment revalidation",
         "a15_investigation_review": "Payer-wide investigations"}
NEXT = {"a1_coverage_exception_review": ["Confirm the patient's current insurance before the visit", "Update the coverage on file in the practice-management system"],
        "a2_auth_request_task": ["Ask the payer for more visits before the next appointment", "Record the answer on the authorization"],
        "a3_signature_task": ["Ask the provider to sign the visit note", "The charge stays on hold until the note is signed"],
        "a3_unbilled_task": ["Find out why the visit has no charge", "Enter the charge in the practice-management system (a person does it) or record why none is due"],
        "a4_coding_review": ["A coder reviews the suggested level against the note", "A person changes the code; the agent never does"],
        "a5_hold_review": ["Review the flagged rule before the claim is released", "Fix the cause (a person edits), then release"],
        "a6_rejection_task": ["Correct the rejected claim data", "Resubmit through the clearinghouse after a named approval"],
        "a7_escalate_review": ["Call the payer or resubmit before the filing window closes", "Choose: escalate, appeal path, or a write-off review (a person decides)"],
        "a8_appeal_task": ["Review the draft appeal", "Gather the supporting records", "Send the appeal before the deadline (named approval)"],
        "a8_fix_task": ["Fix the cause named in the denial (a person edits; the agent never changes codes)", "Resubmit the corrected claim"],
        "a9_rule_proposal_review": ["Review the pattern and the proposed rule", "A named person approves before the rule is enabled"],
        "a10_dispute_review": ["Compare the allowed amount with the contract rate", "Send the dispute within the appeal window (named approval)"],
        "a11_posting_task": ["Post the remit to the ledger", "Check the unapplied balance clears"],
        "a12_followup_task": ["Follow up on the patient balance", "The agent sends nothing; staff contact the patient"],
        "a13_enrollment_task": ["Start the payer revalidation", "Confirm the new effective dates"],
        "a15_investigation_review": ["Investigate why this payer pays below contract on this code", "Open a payer-wide dispute if it holds"]}
QUEUE_TYPE = {"A8": "Denial", "A6": "Rejection", "A10": "Underpaid"}
BASELINE_TYPE = {"denial": "denial", "clearinghouse_rejection": "rejection", "no_payer_response": "timely_filing", "unsigned_note": "unbilled_visit", "underpayment": "underpayment"}
ENTITY_PREFIX = {"appointment": "APT", "encounter": "ENC", "payment": "PAY", "enrollment": "ENR", "ar_snapshot": "AR", "ar": "AR", "payer": "PAYER", "claim_line": "LINE",
                 "cpt_code": "CPT", "denial": "DEN", "bill": "BILL", "authorization": "AUTH"}
CLAIM_AGENTS = {"A5", "A6", "A7", "A8", "A10"}

# The patterns the R2 data generators built in (tools/synthea/load_denials.py, load_auth_eligibility.py). They are generator rules written by the same team
# as the agents, not a simulator's hidden answer key: a match shows the pipeline is wired, not that the rules are right on a real practice.
GENERATOR_RULES = [
    {"carc": "96", "rule": "Medicare dental (CDT) lines are denied as non-covered", "payer": "MEDICARE", "cpt": "CDT codes", "rate": 0.5, "defect": "carc_96_medicare_dental"},
    {"carc": "4", "rule": "E/M visit with an injection on the same encounter and no modifier 25", "payer": "UHC (other payers 0.5)", "cpt": "99211, 99213, 99214, 99203, 99204",
     "rate": 0.8, "defect": "carc_4_em_injection_no_modifier_25"},
    {"carc": "151", "rule": "Unit and frequency limits (96127, 97110 over 4 units; 99408 over 1; G0444/G0136 repeat in a year)", "payer": "all", "cpt": "96127, 97110, 99408, G0444, G0136",
     "rate": 0.25, "defect": "carc_151_unit_frequency_limit"},
    {"carc": "11", "rule": "Preventive visit without a routine-exam diagnosis", "payer": "all", "cpt": "99393, 99395, 99396", "rate": 0.2, "defect": "carc_11_preventive_without_routine_dx"},
    {"carc": "197", "rule": "Line needs prior authorization and has none", "payer": "payers with an authorization rule", "cpt": "per payer list (payer_rule family authorization)", "rate": 0.9,
     "defect": "carc_197_missing_authorization"},
]
PLANTED_NOTE = ("These are the rule patterns the R2 data generators built in (load_denials.py, load_auth_eligibility.py). They are generator rules, not a simulator's hidden "
                "answer key. A small random mix of denials with other CARCs (and a few of the same CARCs) is also in the data, so counts are denials carrying the CARC, not only rule hits.")


def _m(v):
    return f"{D(str(v if v is not None else 0)):.2f}"


def _d(v):
    if v is None:
        return None
    if isinstance(v, dt.datetime):
        return v.date()
    return v


def _iso(v):
    v = _d(v)
    return v.isoformat() if v else None


def age_bucket(days):
    for limit, label in ((7, "0-7"), (14, "8-14"), (30, "15-30")):
        if days <= limit:
            return label
    return "30+"


def owner_of(agent, owner_role):
    """The site's owner word for an engine task: an agent-wide override first (A10 finance, A12 patient billing, A13, A15), else the engine's owner_role mapped."""
    return OWNER_BY_AGENT.get(agent) or OWNER.get(owner_role, owner_role)


def _carc_of(summary):
    m = re.search(r"CARC (\d+)", summary or "")
    return m.group(1) if m else None


def _carcs_of(summary):
    """Every CARC a prediction names: 'Predicted CARC 4, 151: rules' -> ['4', '151']."""
    m = re.match(r"Predicted CARC ((?:\d+(?:, )?)+)", summary or "")
    return re.findall(r"\d+", m.group(1)) if m else []


# ---------------------------------------------------------------- pure builders
def task_state(tasks, as_of):
    """-> {task_id: 'open'|'closed'|'future'} as of the date. A rework version only opens once the version before it was returned."""
    by_id = {t["agent_task_id"]: t for t in tasks}
    out = {}
    for t in tasks:
        c = _d(t["created_date"])
        if c is None or c > as_of:
            out[t["agent_task_id"]] = "future"
            continue
        prev = by_id.get(t.get("previous_agent_task_id"))
        if prev is not None and (prev.get("completed_date") is None or _d(prev["completed_date"]) > as_of):
            out[t["agent_task_id"]] = "future"
            continue
        done = _d(t.get("completed_date"))
        out[t["agent_task_id"]] = "closed" if done is not None and done <= as_of else "open"
    return out


def _entity_ref(t, claims):
    cl = claims.get(t.get("claim_id"))
    if cl:
        return cl["claim_number"]
    return f"{ENTITY_PREFIX.get(t.get('entity_type'), 'ENT')}-{t.get('entity_id')}"


def build_cards(inp, as_of, states):
    """One card per visible task version, in the shape of the site's queue item (plus private fields starting with _)."""
    dec = {d["agent_decision_id"]: d for d in inp["decisions"]}
    fnd = {}
    for f in inp["findings"]:
        if f["agent_finding_id"] not in fnd or f.get("version", 1) >= fnd[f["agent_finding_id"]].get("version", 1):
            fnd[f["agent_finding_id"]] = f
    payers, claims, checks = inp["payers"], inp["claims"], inp.get("checks", {})
    cards = []
    for t in inp["tasks"]:
        st = states[t["agent_task_id"]]
        if st == "future":
            continue
        a = t["agent_code"]
        site = SITE_AGENT[a]
        d = dec.get(t.get("agent_decision_id")) or {}
        f = fnd.get(t.get("agent_finding_id")) or {}
        action = ACTION.get((a, t["task_type"]), f"{site}_{t['task_type']}")
        if a == "A8":
            action = "a8_appeal_task" if t["owner_role"] == "denial_specialist" else "a8_fix_task"
        owner = owner_of(a, t["owner_role"])
        conf = d.get("confidence")
        stake = D(str(t.get("amount_at_stake") or d.get("amount_at_stake") or 0))
        value = (stake * D(str(conf))).quantize(D("0.01")) if conf is not None else stake
        raised = _d(t["created_date"])
        deadline = _d(f.get("deadline_date")) or _d(t.get("due_date")) or raised
        overdue = deadline < as_of
        payer_id = t.get("payer_id") or d.get("payer_id") or f.get("payer_id")
        payer = payers.get(payer_id, {}).get("payer_code", "") if payer_id else ""
        cl = claims.get(t.get("claim_id"))
        ref = _entity_ref(t, claims)
        fdl = (deadline - as_of).days if a == "A7" else None
        qt = ("Filing risk" if fdl is not None and fdl <= FILING_RISK_DAYS else "No response") if a == "A7" else QUEUE_TYPE.get(a)
        why = [x for x in (d.get("reason_summary") or f.get("summary") or t.get("title"),) if x]
        ev = []
        for c in checks.get(t.get("agent_decision_id"), []):
            ev.append({"detail": f"observed {c.get('observed_value')}; expected {c.get('expected_value')}", "result": c["check_result"] == "pass", "rule": c["rule_code"]})
            if c["check_result"] == "fail" and len(why) < 3:
                why.append(f"{c['rule_code']} failed: observed {c.get('observed_value')}, expected {c.get('expected_value')}")
        why.append(f"{_m(stake)} at stake" + (f"; confidence {D(str(conf)):.2f}" if conf is not None else ""))
        prio = value * (D("1.5") if overdue else D(1)) * (D("1.2") if t.get("priority") == "high" else D(1))
        cause = (f"CARC {_carc_of(f.get('summary'))}" if a == "A8" and _carc_of(f.get("summary")) else f.get("finding_type")) or action
        cards.append({
            "agent": site, "owner": owner, "title": f"{t.get('title') or action} - {ref}", "value": _m(value), "priority": _m(prio), "deadline": deadline.isoformat(),
            "overdue": overdue, "raised_on": raised.isoformat(), "why": why, "next_steps": NEXT.get(action, ["A named person decides"]), "evidence": ev, "action_type": action,
            "claim": ref, "payer": payer, "billed": _m(cl["total_charge"]) if cl and a in CLAIM_AGENTS and cl.get("total_charge") is not None else None, "queue_type": qt,
            "filing_days_left": fdl, "confidence": f"{D(str(conf)):.2f}" if conf is not None else None,
            "_state": st, "_value": value, "_prio": prio, "_cause": cause, "_age": (as_of - raised).days, "_code": a, "_task": t, "_payer_id": payer_id,
        })
    return cards


def _public(c):
    return {k: v for k, v in c.items() if not k.startswith("_")}


def queue_parts(cards):
    open_cards = sorted((c for c in cards if c["_state"] == "open"), key=lambda c: (-c["_prio"], c["title"]))
    taken, shown, totals = Counter(), [], defaultdict(lambda: [0, D(0)])
    for c in open_cards:
        k = f"{c['owner']}|{c['agent']}"
        totals[k][0] += 1
        totals[k][1] += c["_value"]
        if taken[k] < QUEUE_PER_KEY:
            taken[k] += 1
            shown.append(c)
    return open_cards, [_public(c) for c in shown], {k: {"open": n, "value": _m(v)} for k, (n, v) in sorted(totals.items())}


def queue_stats(open_cards, payers, as_of):
    out = {}
    for c in open_cards:
        k = out.setdefault(f"{c['owner']}|{c['agent']}", {"open": 0, "value": D(0), "cause": defaultdict(lambda: [0, D(0)]), "payer": defaultdict(lambda: [0, D(0)]), "age": Counter(), "due": Counter()})
        v = c["_value"]
        k["open"] += 1
        k["value"] += v
        for group, key in (("cause", c["_cause"]), ("payer", c["payer"])):
            if key:
                k[group][key][0] += 1
                k[group][key][1] += v
        k["age"][age_bucket(c["_age"])] += 1
        due = dt.date.fromisoformat(c["deadline"])
        k["due"]["overdue" if due < as_of else "next_30" if due <= as_of + dt.timedelta(days=30) else "later"] += 1

    def ranked(dct):
        return [{"key": x, "open": n, "value": _m(v)} for x, (n, v) in sorted(dct.items(), key=lambda i: -i[1][1])]
    return {key: {"open": k["open"], "value": _m(k["value"]), "by_cause": ranked(k["cause"]), "by_payer": ranked(k["payer"])[:8], "age": dict(k["age"]), "due": dict(k["due"])} for key, k in out.items()}


def agents_section(inp, cards, as_of):
    decs = [d for d in inp["decisions"] if _d(d["decided_at"]) <= as_of]
    task_by_dec = {}
    for t in inp["tasks"]:
        if t.get("version", 1) == 1 and t.get("agent_decision_id") is not None:
            task_by_dec[t["agent_decision_id"]] = t
    planted_by = defaultdict(list)
    dn = inp.get("denials_by_carc", {})
    for r in GENERATOR_RULES:
        if r["carc"] in dn:
            planted_by["A8"].append({"defect": r["defect"], "count": int(dn[r["carc"]])})
    by_card = defaultdict(list)
    for c in sorted(cards, key=lambda c: (-c["_value"], c["title"])):
        if c["_task"].get("version", 1) == 1:
            by_card[c["_code"]].append(c)
    out = []
    for code, name, blurb in AGENT_INFO:
        rows = [d for d in decs if d["agent_code"] == code]
        by_action = defaultdict(lambda: [0, D(0)])
        no_action = 0
        for d in rows:
            if d["outcome"] in ("proceed", "no_action"):
                no_action += 1
                continue
            t = task_by_dec.get(d["agent_decision_id"])
            action = ACTION.get((code, t["task_type"])) if t else None
            if code == "A8" and t:
                action = "a8_appeal_task" if t["owner_role"] == "denial_specialist" else "a8_fix_task"
            action = action or f"{SITE_AGENT[code]}_{d['decision_type']}"
            by_action[action][0] += 1
            by_action[action][1] += D(str(d.get("amount_at_stake") or 0))
        actions = [{"action": a, "count": n, "dollars": _m(v)} for a, (n, v) in sorted(by_action.items())]
        if no_action:
            actions.append({"action": "no_action", "count": no_action, "dollars": "0.00"})
        actions.sort(key=lambda x: x["action"])
        seen, examples = set(), []
        for c in by_card.get(code, []):
            if c["title"] in seen:
                continue
            seen.add(c["title"])
            examples.append({"title": c["title"], "owner": c["owner"], "value": c["value"], "deadline": c["deadline"], "why": c["why"], "next_steps": c["next_steps"]})
            if len(examples) == 3:
                break
        out.append({"id": code, "name": name, "blurb": blurb, "decisions": len(rows), "proposed": len(rows) - no_action, "no_action": no_action, "actions": actions,
                    "planted": planted_by.get(code, []), "examples": examples})
    return out


def baseline_section(findings, as_of):
    by_type = defaultdict(lambda: {"findings": 0, "recoverable": D(0), "structural": D(0)})
    rec = stru = D(0)
    n = 0
    prevention = {"findings": 0, "at_risk": D(0)}
    for f in findings:
        if _d(f["found_date"]) > as_of:
            continue
        risk = D(str(f.get("amount_at_risk") or 0))
        if f["finding_type"] == "predicted_denial":
            # A5 holds a claim BEFORE submission: that is prevention, not money left behind, and it overlaps the denials
            # that follow if the claim is released anyway. Reported on its own so the leakage totals are not inflated.
            prevention["findings"] += 1
            prevention["at_risk"] += risk
            continue
        n += 1
        got = D(str(f.get("amount_recovered") or 0)) if f.get("resolved_date") and _d(f["resolved_date"]) <= as_of else D(0)
        left = max(D(0), risk - got)
        k = by_type[BASELINE_TYPE.get(f["finding_type"], f["finding_type"])]
        k["findings"] += 1
        if f.get("is_preventable"):
            k["recoverable"] += left
            rec += left
        else:
            k["structural"] += left
            stru += left
    for key in ("denial", "rejection", "timely_filing", "unbilled_visit", "underpayment"):
        by_type[key]                                     # the site's cause table expects these five rows even when empty
    return {"by_type": {k: {"findings": v["findings"], "recoverable": _m(v["recoverable"]), "structural": _m(v["structural"])} for k, v in sorted(by_type.items())},
            "fallback_priced": 0, "findings": n, "recoverable": _m(rec), "structural": _m(stru),
            "prevention": {"findings": prevention["findings"], "at_risk": _m(prevention["at_risk"]),
                           "note": "Claims A5 held before submission (billed amount at risk); not counted in recoverable or structural."}}


def slices_section(findings, payers, cpt, as_of):
    out = defaultdict(D)
    for f in findings:
        if f["agent_code"] == "A15" and _d(f["found_date"]) <= as_of:
            key = f"{payers.get(f.get('payer_id'), {}).get('payer_code', '?')}|{cpt.get(f['entity_id'], f['entity_id'])}"
            out[key] += D(str(f.get("amount_at_risk") or 0))
    return [{"slice": k, "dollars": _m(v), "top_cause": "underpayment:realisation"} for k, v in sorted(out.items(), key=lambda i: -i[1])[:12]]


def replay_section(inp, as_of):
    findings = [f for f in inp["findings"] if _d(f["found_date"]) <= as_of]
    payers, claims = inp["payers"], inp["claims"]
    by_payer = defaultdict(lambda: [0, D(0), D(0)])
    for f in findings:
        k = payers.get(f.get("payer_id"), {}).get("payer_code")
        if not k:
            continue
        v = D(str(f.get("amount_at_risk") or 0))
        by_payer[k][0] += 1
        by_payer[k][1 if f.get("is_preventable") else 2] += v
    bp = [{"findings": n, "key": k, "recoverable": _m(r), "structural": _m(s), "total": _m(r + s)} for k, (n, r, s) in sorted(by_payer.items(), key=lambda i: -(i[1][1] + i[1][2]))[:10]]
    opp = []
    for rank, f in enumerate(sorted(findings, key=lambda f: (-D(str(f.get("amount_at_risk") or 0)), f["agent_finding_id"]))[:25], 1):
        cl = claims.get(f.get("claim_id"))
        opp.append({"agent": f["agent_code"], "basis": "agent_finding", "carc": _carc_of(f.get("summary")) or "", "category": f.get("upstream_stage") or "", "claim": cl["claim_number"] if cl else
                    f"{ENTITY_PREFIX.get(f.get('entity_type'), 'ENT')}-{f.get('entity_id')}", "cpt": "", "deadline": _iso(f.get("deadline_date")) or "", "expected_amount": _m(f.get("amount_at_risk")),
                    "line_no": None, "location": "", "payer": payers.get(f.get("payer_id"), {}).get("payer_code", ""), "provider": f"PRV-{f['provider_id']}" if f.get("provider_id") else "",
                    "rank": rank, "reason": f.get("summary") or "", "status": "recoverable" if f.get("is_preventable") else "structural",
                    "type": BASELINE_TYPE.get(f["finding_type"], f["finding_type"]), "visit": ""})
    # were the generator's denial patterns caught before the denial? claim level: planted = claims denied with that CARC; found = of those, claims with an A5 hold naming that CARC raised before the denial
    pred = defaultdict(lambda: [0, 0])
    for f in findings:
        if f["finding_type"] == "predicted_denial":
            for c in _carcs_of(f.get("summary")):
                pred[c][0] += 1
                pred[c][1] += 1 if f["finding_status"] == "accepted" else 0
    fvp = []
    for r in GENERATOR_RULES:
        s = inp.get("fvp", {}).get(r["carc"])
        if s is None:
            continue
        planted, found = int(s["planted"]), int(s["found"])
        n_pred, n_conf = pred.get(r["carc"], [0, 0])
        fvp.append({"type": f"carc_{r['carc']}", "planted": planted, "found": found, "precision": round(n_conf / n_pred, 3) if n_pred else None,
                    "recall": round(found / planted, 3) if planted else None, "correct_recall": round(found / planted, 3) if planted else None})
    return {"health": inp.get("health", {}), "reconciliation": inp.get("reconciliation", []), "by_payer": bp, "opportunities": opp, "found_vs_planted": fvp}


def staff_section(inp, tasks, states, as_of):
    """Pseudonymous R2 staff and the Replay run's simulated task handling (minutes, returns). Suggestions (gaps, allocation) are not produced yet."""
    staff = inp["staff"]
    done = [t for t in tasks if t.get("completed_date") and _d(t["completed_date"]) <= as_of and t.get("assigned_to_staff_id") in staff and t.get("minutes_spent") is not None]
    ttype = lambda t: (ACTION.get((t["agent_code"], t["task_type"])) or f"{SITE_AGENT[t['agent_code']]}_{t['task_type']}")  # noqa: E731
    per = defaultdict(lambda: defaultdict(list))
    for t in done:
        a = "a8_appeal_task" if t["agent_code"] == "A8" and t["owner_role"] == "denial_specialist" else "a8_fix_task" if t["agent_code"] == "A8" else ttype(t)
        per[t["assigned_to_staff_id"]][a].append(t)
    team_of = {sid: ("coding" if s.get("team") == "coding" else "billing") for sid, s in staff.items()}
    metrics, handle, rework_min, benchmark_src, employees = {}, {}, {}, defaultdict(list), []
    for sid, kinds in per.items():
        e = staff[sid]["staff_number"]
        metrics[e], handle[e], rework_min[e] = {}, {}, {}
        for a, rows in kinds.items():
            mins = sorted(float(r["minutes_spent"]) for r in rows)
            first = [r.get("outcome") != "returned" for r in rows]
            recent = [x for x, r in zip(first, rows) if (as_of - _d(r["completed_date"])).days < 30]
            older = [x for x, r in zip(first, rows) if (as_of - _d(r["completed_date"])).days >= 30]
            ontime = [(r.get("due_date") is None or _d(r["completed_date"]) <= _d(r["due_date"])) for r in rows]
            rate = lambda x: sum(x) / len(x) if x else None  # noqa: E731
            m = {"n": len(rows), "done_30d": len(recent), "median_min": round(statistics.median(mins), 1), "first_pass": round(rate(first), 3), "on_time": round(rate(ontime), 3),
                 "trend": round(rate(recent) - rate(older), 3) if recent and older else None}
            metrics[e][a] = m
            q = lambda p: round(mins[min(len(mins) - 1, int(p * len(mins)))], 1)  # noqa: E731
            handle[e][a] = [q(p) for p in (0.1, 0.25, 0.5, 0.75, 0.9)]
            rework_min[e][a] = round(m["n"] * (1 - m["first_pass"]) * m["median_min"])
            benchmark_src[a].append(m)
    bench = {}
    for a, ms in benchmark_src.items():
        if len(ms) >= 2:
            bench[a] = {"median_min": round(statistics.median(m["median_min"] for m in ms), 1), "first_pass": round(sum(m["first_pass"] * m["n"] for m in ms) / sum(m["n"] for m in ms), 3), "people": len(ms)}
    open_by = Counter(t["assigned_to_staff_id"] for t in tasks if states[t["agent_task_id"]] == "open" and t.get("assigned_to_staff_id"))
    for sid in sorted(per):
        s = staff[sid]
        mm = metrics[s["staff_number"]]
        usual = sum(m["median_min"] * m["n"] for m in mm.values()) / sum(m["n"] for m in mm.values())
        week_min = round(float(s.get("weekly_hours") or 40) * 60)
        cap = max(1, round(week_min / usual)) if usual else 0
        employees.append({"id": s["staff_number"], "name": s["staff_number"], "role": s["staff_role"], "team": team_of[sid], "capacity_week": cap, "assigned": open_by.get(sid, 0),
                          "task_types": sorted(mm), "done_30d": sum(m["done_30d"] for m in mm.values()), "minutes_week": week_min, "busy": bool(cap) and open_by.get(sid, 0) >= 0.9 * cap})
    gaps, strengths = [], []
    for e, mm in metrics.items():
        for a, m in mm.items():
            b = bench.get(a)
            if not b or m["n"] < MIN_TASKS:
                continue
            rw, trw = 1 - m["first_pass"], 1 - b["first_pass"]
            label = LABEL.get(a, a).lower()
            if rw - trw >= 0.12 and rw >= 1.5 * trw:
                gaps.append({"employee": e, "task_type": a, "kind": "quality", "n": m["n"], "module": "Team lead review of returned work", "avoidable_tasks": round(m["n"] * (rw - trw)),
                             "avoidable_minutes": round(m["n"] * (rw - trw) * m["median_min"]), "evidence": f"Returned {rw:.0%} against the team's {trw:.0%} on {label} ({m['n']} tasks)."})
            if m["median_min"] >= 1.4 * b["median_min"]:
                gaps.append({"employee": e, "task_type": a, "kind": "speed", "n": m["n"], "module": "Team lead review of handling time", "avoidable_tasks": 0,
                             "avoidable_minutes": round(m["n"] * (m["median_min"] - b["median_min"])), "evidence": f"Median {m['median_min']:.0f} min against the team's {b['median_min']:.0f} on {label} ({m['n']} tasks)."})
            if m["median_min"] <= 0.8 * b["median_min"] and m["first_pass"] >= b["first_pass"]:
                strengths.append({"employee": e, "task_type": a, "kind": "strength", "n": m["n"], "evidence": f"Median {m['median_min']:.0f} min against the team's {b['median_min']:.0f} on {label}, first pass {m['first_pass']:.0%} ({m['n']} tasks)."})
    sid_team = {staff[s]["staff_number"]: team_of[s] for s in staff}
    hist, teams = {}, {}
    for sid, kinds in per.items():
        team = team_of[sid]
        h = hist.setdefault(team, {"by_type": {}, "tasks": [0] * HISTORY_WEEKS, "rework": [0] * HISTORY_WEEKS})
        for a, rows in kinds.items():
            row = h["by_type"].setdefault(a, [0] * HISTORY_WEEKS)
            for r in rows:
                w = HISTORY_WEEKS - 1 - min(HISTORY_WEEKS - 1, (as_of - _d(r["completed_date"])).days // 7)
                row[w] += 1
                h["tasks"][w] += 1
                h["rework"][w] += 1 if r.get("outcome") == "returned" else 0
        teams.setdefault(team, set()).update(kinds)
    for h in hist.values():
        h["first_pass"] = [round(1 - r / n, 3) if n else None for r, n in zip(h["rework"], h["tasks"])]
    label = {"billing": "Billing team", "coding": "Coding team"}
    return {
        "synthetic": True,
        "note": "Staff are pseudonymous staff ids from R2. Task minutes and returns come from the Replay run's simulated human actions in shadow mode, not from real employees. "
                "Suggestions are for the manager to decide, not for hiring, firing or pay decisions. Allocation and scenarios are not produced from this data yet.",
        "as_of": as_of.isoformat(), "days": DAYS, "min_tasks": MIN_TASKS,
        "teams": {t: {"label": label[t], "task_types": [{"id": a, "label": LABEL.get(a, a)} for a in sorted(v)]} for t, v in sorted(teams.items())},
        "employees": employees, "metrics": metrics, "benchmark": bench, "reasons": {e: {a: {} for a in mm} for e, mm in metrics.items()}, "history": hist, "handle_time": handle,
        "rework_minutes": rework_min,
        "scenarios": {t: {"ceiling_per_week": 0, "inflow_per_week": 0, "open_dollars": 0, "open_items": 0, "scenarios": [], "unplaceable": 0} for t in sorted(teams)},
        "assumptions": {"week_minutes": "Weekly minutes = the staff row's weekly_hours x 60; weekly slots = those minutes / the person's usual handling time.",
                        "rework": "A returned task is done twice.", "inflow": "Not modelled yet.", "overtime": 0.1, "upstream_cut": 0.5, "weeks": 12},
        "gaps": gaps, "strengths": strengths, "allocation": [], "unallocated": [], "improvements": [], "planted": [],
        "found_vs_planted": {"planted": 0, "found": 0, "flagged_but_not_planted": []},
    }


def meta_section(inp, as_of):
    run = inp.get("runs", {})
    first = next((r for r in GENERATOR_RULES if r["carc"] == "4"), GENERATOR_RULES[0])
    start = _iso(inp.get("data_start")) or as_of.isoformat()
    dn = inp.get("denials_by_carc", {})
    return {
        "as_of": as_of.isoformat(), "shadow": True,
        "planted": {
            "claims_billed": int(inp.get("claims_billed", 0)),
            # the site reads these two keys; filled from the generator rules. The rate-cut slot is empty: the R2 generators build no payer-wide rate cut.
            "denial_pattern": {"payer": "UHC", "cpt": "99213", "carc": first["carc"], "rate": first["rate"], "from": start, "rule": first["rule"]},
            "rate_cut": {"payer": "none", "cpt": "none", "percent": 0, "from": start, "rule": "no payer-wide rate cut is built into the R2 data"},
            "generator_rules": [dict(r, denials=int(dn.get(r["carc"], 0)), source="tools/synthea/load_denials.py" if r["carc"] != "197" else "tools/synthea/load_auth_eligibility.py + load_denials.py")
                                for r in GENERATOR_RULES],
            "note": PLANTED_NOTE,
        },
        "run": {"status": run.get("status", "ok"), "gate": run.get("gate", "passed"), "files_loaded": int(run.get("files_loaded", 0)), "events_added": int(run.get("events_added", 0)),
                "practice": inp.get("practice", {}).get("practice_name"), "runs": int(run.get("runs", 0)), "first_run": run.get("first_run"), "last_run": run.get("last_run"),
                "code_version": run.get("code_version"), "load_batch_id": run.get("load_batch_id"), "source": run.get("source", "replay"), "note": SHADOW_NOTE},
    }


def build_payload(inp, as_of):
    tasks = inp["tasks"]
    states = task_state(tasks, as_of)
    cards = build_cards(inp, as_of, states)
    open_cards, queue, totals = queue_parts(cards)
    return {
        "schema": SCHEMA,
        "meta": meta_section(inp, as_of),
        "queue": queue,
        "queue_totals": totals,
        "queue_stats": queue_stats(open_cards, inp["payers"], as_of),
        "staff": staff_section(inp, tasks, states, as_of),
        "reference": inp.get("reference", {}),
        "agents": agents_section(inp, cards, as_of),
        "baseline": baseline_section(inp["findings"], as_of),
        "replay": replay_section(inp, as_of),
        "slices": slices_section(inp["findings"], inp["payers"], inp.get("cpt", {}), as_of),
    }


def dumps(payload):
    """JSON text; Decimal or float money leaking in raises (default is not set on purpose)."""
    return json.dumps(payload, indent=1, sort_keys=True)


def write_ui_data(payload, out_dir):
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    text = dumps(payload)
    j, js = out_dir / "ui_data.json", out_dir / "ui_data.js"
    j.write_text(text + "\n", encoding="utf-8", newline="\n")
    js.write_text("window.KRISNNAI_LIVE = " + text + ";\n", encoding="utf-8", newline="\n")
    return j, js


# ---------------------------------------------------------------- database (read only)
def _rows(cur, sql, args=None):
    cur.execute(sql, args)
    names = [c[0] for c in cur.description]
    return [dict(zip(names, r)) for r in cur.fetchall()]


def default_as_of(cur, tenant_id, source):
    cur.execute("select max(started_at)::date from agent_run where tenant_id = %s and source = %s", (tenant_id, source))
    v = cur.fetchone()[0]
    if v is None:
        cur.execute("select max(submitted_date) from claim where tenant_id = %s", (tenant_id,))
        v = cur.fetchone()[0]
    return v


def load_inputs(conn, tenant_id=1, as_of=None, source="replay"):
    """Reads R2 (SELECT only, every query filtered by tenant_id and, for agent rows, by source) into the plain dicts build_payload() takes."""
    cur = conn.cursor()
    as_of = as_of or default_as_of(cur, tenant_id, source)
    end = as_of + dt.timedelta(days=1)
    T, S = (tenant_id,), (tenant_id, source)
    inp = {"as_of": as_of}
    inp["practice"] = (_rows(cur, "select practice_id, practice_name from practice where tenant_id = %s order by practice_id limit 1", T) or [{}])[0]
    inp["payers"] = {r["payer_id"]: r for r in _rows(cur, "select payer_id, payer_code, payer_name, filing_days, appeal_days from payer where tenant_id = %s and is_current", T)}
    inp["staff"] = {r["staff_id"]: r for r in _rows(cur, "select staff_id, staff_number, staff_role, team, weekly_hours from staff where tenant_id = %s", T)}
    inp["cpt"] = {r["cpt_code_id"]: r["code"] for r in _rows(cur, "select cpt_code_id, code from cpt_code where tenant_id = %s", T)}
    inp["decisions"] = _rows(cur, "select agent_decision_id, agent_code, decision_type, outcome, confidence, reason_summary, amount_at_stake, entity_type, entity_id, decided_at, payer_id, claim_id "
                                  "from agent_decision where tenant_id = %s and source = %s and decided_at < %s", S + (end,))
    inp["findings"] = _rows(cur, "select agent_finding_id, agent_code, finding_type, entity_type, entity_id, found_date, finding_status, amount_at_risk, amount_recovered, upstream_stage, is_preventable, "
                                 "severity, deadline_date, resolved_date, resolution, summary, payer_id, claim_id, provider_id, agent_decision_id, version from agent_finding "
                                 "where tenant_id = %s and source = %s and found_date <= %s", S + (as_of,))
    inp["tasks"] = _rows(cur, "select agent_task_id, task_type, owner_role, task_status, created_date, agent_code, entity_type, entity_id, agent_decision_id, agent_finding_id, priority, due_date, "
                              "completed_date, assigned_to_staff_id, amount_at_stake, outcome, title, payer_id, claim_id, version, previous_agent_task_id, minutes_spent from agent_task "
                              "where tenant_id = %s and source = %s and created_date <= %s", S + (as_of,))
    # claims behind any task or finding
    ids = sorted({x["claim_id"] for x in inp["tasks"] + inp["findings"] if x.get("claim_id") is not None})
    inp["claims"] = {r["claim_id"]: r for r in _rows(cur, "select claim_id, claim_number, total_charge, payer_id, service_date_from from claim where tenant_id = %s and claim_id = any(%s)", (tenant_id, ids))} if ids else {}
    states = task_state(inp["tasks"], as_of)
    want = sorted({t["agent_decision_id"] for t in inp["tasks"] if states[t["agent_task_id"]] == "open" and t.get("agent_decision_id") is not None})
    inp["checks"] = defaultdict(list)
    if want:
        for r in _rows(cur, "select agent_decision_id, check_seq, rule_code, check_result, severity, observed_value, expected_value from agent_decision_check "
                            "where tenant_id = %s and source = %s and agent_decision_id = any(%s) order by agent_decision_id, check_seq", S + (want,)):
            inp["checks"][r["agent_decision_id"]].append(r)
    inp["checks"] = dict(inp["checks"])
    # run and data facts
    r = _rows(cur, "select count(*) n, min(started_at) first_run, max(started_at) last_run, max(code_version) code_version, count(*) filter (where run_status <> 'succeeded') bad "
                   "from agent_run where tenant_id = %s and source = %s and started_at < %s", S + (end,))[0]
    cur.execute("select count(*) from load_batch where tenant_id = %s", T)
    batches = cur.fetchone()[0]
    cur.execute("select count(*) from claim_status_history where tenant_id = %s and event_date <= %s", (tenant_id, as_of))
    events = cur.fetchone()[0]
    lb = re.search(r"\|lb(\d+)", r["code_version"] or "")
    cv = (r["code_version"] or "").split("|")[0] or None
    inp["runs"] = {"status": "ok" if not r["bad"] else "failed_runs", "files_loaded": batches, "events_added": events, "runs": r["n"], "first_run": _iso(r["first_run"]), "last_run": _iso(r["last_run"]),
                   "code_version": cv, "load_batch_id": int(lb.group(1)) if lb else None, "source": source}
    cur.execute("select count(*), min(submitted_date) from claim where tenant_id = %s and submitted_date <= %s", (tenant_id, as_of))
    inp["claims_billed"], inp["data_start"] = cur.fetchone()
    inp["denials_by_carc"] = {k: v for k, v in _rows_kv(cur, "select a.carc_code, count(*) from denial d join adjustment_reason a on a.adjustment_reason_id = d.adjustment_reason_id and a.tenant_id = d.tenant_id "
                                                      "where d.tenant_id = %s and d.denial_date <= %s group by 1", (tenant_id, as_of))}
    inp["fvp"] = {k: {"planted": p, "found": f} for k, p, f in _rows3(cur, """
        select a.carc_code, count(distinct d.claim_id),
               count(distinct d.claim_id) filter (where exists (select 1 from agent_finding f where f.tenant_id = d.tenant_id and f.source = %s and f.agent_code = 'A5'
                                                                  and f.finding_type = 'predicted_denial' and f.claim_id = d.claim_id and f.found_date < d.denial_date
                                                                  and f.summary ~ ('^Predicted CARC ([0-9]+, )*' || a.carc_code || '[,:]')))
        from denial d join adjustment_reason a on a.adjustment_reason_id = d.adjustment_reason_id and a.tenant_id = d.tenant_id
        where d.tenant_id = %s and d.denial_date <= %s and a.carc_code in ('96','4','151','11','197') group by 1""", (source, tenant_id, as_of))}
    inp["health"] = _health(cur, tenant_id, as_of)
    inp["reconciliation"] = _reconciliation(cur, tenant_id, as_of, end, source)
    inp["reference"] = _reference(cur, tenant_id)
    return inp


def _rows_kv(cur, sql, args):
    cur.execute(sql, args)
    return cur.fetchall()


_rows3 = _rows_kv


def _health(cur, t, as_of):
    cur.execute("select count(*) from claim where tenant_id = %s and submitted_date <= %s", (t, as_of))
    n = cur.fetchone()[0]
    cur.execute("select count(distinct claim_id) from denial where tenant_id = %s and denial_date <= %s", (t, as_of))
    dn = cur.fetchone()[0]
    cur.execute("select max(as_of_date) from ar_snapshot where tenant_id = %s and as_of_date <= %s", (t, as_of))
    snap = cur.fetchone()[0]
    days_ar = share90 = None
    if snap:
        cur.execute("select coalesce(sum(balance), 0), coalesce(sum(balance) filter (where days_outstanding > 90), 0) from ar_snapshot where tenant_id = %s and as_of_date = %s and balance_owner = 'payer'", (t, snap))
        bal, over = cur.fetchone()
        cur.execute("select coalesce(sum(total_charge), 0) from claim where tenant_id = %s and submitted_date > %s::date - 90 and submitted_date <= %s", (t, snap, snap))
        ch = cur.fetchone()[0]
        days_ar = (bal / (ch / 90)) if ch else None
        share90 = (over / bal) if bal else None
    f = lambda v: f"{D(str(v)):.6f}" if v is not None else "0.000000"  # noqa: E731
    return {"claims": n, "clean_claim_rate": f(1 - D(dn) / D(n)) if n else f(None), "days_in_ar": f(days_ar), "ar_over_90_share": f(share90)}


def _reconciliation(cur, t, as_of, end, source):
    S = (t, source)
    out = []

    def add(name, desc, items, bad, maxdiff="0.00", tol="0"):
        out.append({"name": name, "description": desc, "items": int(items), "mismatches": int(bad), "max_difference": maxdiff, "passed": int(bad) == 0, "tolerance": tol})

    cur.execute("select count(*), count(*) filter (where r.decisions_made is distinct from coalesce(d.n, 0)) from agent_run r left join (select agent_run_id, count(*) n from agent_decision "
                "where tenant_id = %s and source = %s group by 1) d on d.agent_run_id = r.agent_run_id where r.tenant_id = %s and r.source = %s and r.started_at < %s", S + S + (end,))
    add("run_decision_count", "agent_run.decisions_made = the agent_decision rows of that run", *cur.fetchone())
    cur.execute("select count(*), count(*) filter (where d.rules_checked is distinct from coalesce(c.n, 0)) from agent_decision d left join (select agent_decision_id, count(*) n from agent_decision_check "
                "where tenant_id = %s and source = %s group by 1) c on c.agent_decision_id = d.agent_decision_id where d.tenant_id = %s and d.source = %s and d.decided_at < %s", S + S + (end,))
    add("decision_rule_count", "agent_decision.rules_checked = the agent_decision_check rows of that decision (hard rule 5)", *cur.fetchone())
    cur.execute("select count(*), count(*) filter (where d.agent_decision_id is null) from agent_finding f left join agent_decision d on d.agent_decision_id = f.agent_decision_id and d.tenant_id = f.tenant_id "
                "where f.tenant_id = %s and f.source = %s and f.found_date <= %s", S + (as_of,))
    add("finding_has_decision", "every agent_finding points at the decision that produced it", *cur.fetchone())
    cur.execute("select count(*), count(*) filter (where d.agent_decision_id is null) from agent_task k left join agent_decision d on d.agent_decision_id = k.agent_decision_id and d.tenant_id = k.tenant_id "
                "where k.tenant_id = %s and k.source = %s and k.created_date <= %s", S + (as_of,))
    add("task_has_decision", "every agent_task points at the decision that produced it", *cur.fetchone())
    cur.execute("select count(*), count(*) filter (where f.agent_finding_id is null) from agent_value v left join agent_finding f on f.agent_finding_id = v.agent_finding_id and f.tenant_id = v.tenant_id "
                "where v.tenant_id = %s and v.source = %s and v.value_date <= %s", S + (as_of,))
    add("value_has_finding", "every agent_value row follows from an agent_finding", *cur.fetchone())
    cur.execute("select count(*), count(*) filter (where abs(c.total_charge - coalesce(l.s, 0)) > 0.01), coalesce(max(abs(c.total_charge - coalesce(l.s, 0))), 0) from claim c "
                "left join (select claim_id, sum(charge_amount) s from claim_line where tenant_id = %s group by 1) l on l.claim_id = c.claim_id where c.tenant_id = %s and c.submitted_date <= %s", (t, t, as_of))
    n, bad, mx = cur.fetchone()
    add("claim_charge", "claim total charge = sum of its service lines", n, bad, _m(mx), "0.01")
    return out


def _reference(cur, t):
    T = (t,)
    ref = {}
    ref["carc_routes"] = _rows(cur, "select carc_code as carc, reason_category as category, owner_role as owner, suggested_action as disposition, short_label as description from adjustment_reason where tenant_id = %s order by carc_code", T)
    ref["rejection_routes"] = _rows(cur, "select code_set as source, code as status_category, '*' as status_code, status_group as category, 'business' as kind, 'biller' as owner, short_label as description "
                                         "from claim_status_code where tenant_id = %s and is_rejection order by code_set, code", T)
    ref["ncci_pairs"] = _rows(cur, "select a.code as cpt_a, b.code as cpt_b, '1' as modifier_indicator from payer_rule r join cpt_code a on a.cpt_code_id = r.cpt_code_id and a.tenant_id = r.tenant_id "
                                   "join cpt_code b on b.cpt_code_id = r.paired_cpt_code_id and b.tenant_id = r.tenant_id where r.tenant_id = %s and r.rule_family = 'ncci_edit' order by 1, 2", T)
    ref["mue_limits"] = _rows(cur, "select k.code as cpt, min(r.unit_limit) as max_units from payer_rule r join cpt_code k on k.cpt_code_id = r.cpt_code_id and k.tenant_id = r.tenant_id "
                                   "where r.tenant_id = %s and r.rule_family = 'unit_limit' group by 1 order by 1", T)
    ref["fee_schedule"] = _rows(cur, "select 'PRACTICE' as payer, k.code as cpt, '' as modifier, l.fee_per_unit as allowed, l.effective_from as effective, case when l.effective_to >= '9999-01-01' then null else l.effective_to end as ends "
                                     "from fee_schedule_line l join cpt_code k on k.cpt_code_id = l.cpt_code_id and k.tenant_id = l.tenant_id where l.tenant_id = %s and l.is_active order by k.code", T)
    ref["auth_requirements"] = _rows(cur, 'select p.payer_code as payer, k.code as cpt, coalesce(max(a.valid_to - a.valid_from), 90) as validity_days from payer_rule r join payer p on p.payer_id = r.payer_id and p.tenant_id = r.tenant_id '
                                          'join cpt_code k on k.cpt_code_id = r.cpt_code_id and k.tenant_id = r.tenant_id left join "authorization" a on a.payer_id = r.payer_id and a.tenant_id = r.tenant_id '
                                          "and a.primary_cpt_code_id = r.cpt_code_id where r.tenant_id = %s and r.rule_family = 'authorization' group by 1, 2 order by 1, 2", T)
    ref["filing_windows"] = _rows(cur, "select payer_code as payer, filing_days as days from payer where tenant_id = %s and is_current and filing_days is not null order by payer_code", T)
    ref["appeal_windows"] = _rows(cur, "select payer_code as payer, appeal_days as days from payer where tenant_id = %s and is_current and appeal_days > 0 order by payer_code", T)
    ref["policy"] = []        # R2 has no policy table: every action type is L0 / shadow by default (CLAUDE.md)
    for rows in ref.values():
        for r in rows:
            for k, v in list(r.items()):
                if isinstance(v, Decimal):
                    r[k] = _m(v) if k in ("allowed",) else int(v)
                elif isinstance(v, (dt.date, dt.datetime)):
                    r[k] = v.isoformat()
    return ref


def main(argv=None):
    ap = argparse.ArgumentParser(description="Write ui_data.js/json from the agent_* tables in krisnnai_r2")
    ap.add_argument("--out", default=str(ROOT / "out" / "ui"))
    ap.add_argument("--as-of", help="YYYY-MM-DD; default: the last day an agent ran")
    ap.add_argument("--tenant", type=int, default=1)
    ap.add_argument("--source", default="replay")
    a = ap.parse_args(argv)
    import r2load
    conn = r2load.connect()                                 # asserts krisnnai_r2
    try:
        conn.rollback()
        conn.set_session(readonly=True)
        as_of = dt.date.fromisoformat(a.as_of) if a.as_of else None
        inp = load_inputs(conn, a.tenant, as_of, a.source)
        as_of = inp["as_of"]
    finally:
        conn.rollback()
    payload = build_payload(inp, as_of)
    j, js = write_ui_data(payload, a.out)
    print("wrote", js, "and", j, "as_of", as_of, "queue", len(payload["queue"]), "decisions", sum(x["decisions"] for x in payload["agents"]))


if __name__ == "__main__":
    main()
