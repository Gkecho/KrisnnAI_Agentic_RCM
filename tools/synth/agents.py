"""Stage 3: run the fifteen agents (shadow mode) over the loaded canonical data and fill the agent output tables.

Each agent is a rule engine that reads only canonical rows that were visible on the day it ran (rules first, no model).
It never reads the generator's hidden story flags, so what it finds and misses is a fair test of the rules.
Shadow mode: every decision is recorded with run_mode 'shadow'; nothing is sent. A human works the resulting tasks.

Tables filled: agent_run, agent_decision, agent_decision_details, agent_finding, agent_task, agent_approval,
agent_writeback, agent_value, agent_forecast; also payer_rule (learned rules), enrollment, patient_statement.
"""
import datetime as dt
from collections import defaultdict
from decimal import Decimal

from core import TODAY, h
from journey import q, next_biz, is_biz

D = Decimal
START = dt.date(2025, 11, 3)
VERSION = "v0.9-shadow"
NAMES = {"A1": "Gatekeeper", "A2": "Permit Clerk", "A3": "Note Chaser", "A4": "Code Whisperer", "A5": "Mirror", "A6": "Courier", "A7": "Hunter",
         "A8": "Advocate", "A9": "Coach", "A10": "Auditor", "A11": "Bookkeeper", "A12": "Concierge", "A13": "Credentialing", "A14": "Captain", "A15": "Detective"}
ROLE_STAFF = {"front_desk": ["FD01", "FD02"], "biller": ["B01", "B02"], "denial_specialist": ["D01"], "coder": ["C01", "C02", "C03"], "ar_specialist": ["AR01"],
              "payment_poster": ["PP01"], "billing_lead": ["B03"], "manager": ["M01"], "provider": []}
SPEED = {"C02": 1.5, "B02": 1.1, "FD02": 1.3, "C03": .8}
REWORK = {"C02": .10, "B02": .14, "C03": .18, "FD02": .12, "D01": .05}
BASE_MIN = {"authorization_check": 14, "coverage_follow_up": 12, "unsigned_note": 6, "code_review": 18, "claim_hold_review": 16, "fix_rejection": 11,
            "claim_follow_up": 22, "denial_work": 26, "dispute_package": 40, "post_remit": 14, "patient_follow_up": 9, "revalidation": 35, "rule_review": 20}
SLA = {"hi": 1, "md": 3, "lo": 5}


def build_agents(s, ctx):
    r = s.rnd
    P, cpt, carc_ids, staff, prov = ctx["payer"], ctx["cpt"], ctx["carc"], ctx["staff"], ctx["provider"]
    code_of = {v: k for k, v in P.items()}
    cpt_code = {v: k for k, v in cpt.items()}
    carc_code = {v: k for k, v in carc_ids.items()}
    carc_row = {x["adjustment_reason_id"]: x for x in s.rows["adjustment_reason"]}
    pinfo = ctx["pinfo"]
    # ------------------------------------------------------------------ indexes over canonical rows
    ENC = {e["encounter_id"]: e for e in s.rows["encounter"]}
    ENCLINES = defaultdict(list)
    for x in s.rows["encounter_details"]:
        ENCLINES[x["encounter_id"]].append(x)
    CLAIM = {c["claim_id"]: c for c in s.rows["claim"]}
    CD = defaultdict(list)
    for x in s.rows["claim_details"]:
        CD[x["claim_id"]].append(x)
    DEN = defaultdict(list)
    for d in s.rows["denial"]:
        DEN[d["claim_id"]].append(d)
    AUTH = {a["authorization_id"]: a for a in s.rows["authorization"]}
    COV = {c["coverage_id"]: c for c in s.rows["coverage"]}
    PAT_ENC = defaultdict(list)
    for e in s.rows["encounter"]:
        PAT_ENC[e["patient_id"]].append(e)
    for v in PAT_ENC.values():
        v.sort(key=lambda e: e["encounter_date"])
    PAT_DOC = defaultdict(list)
    for d in s.rows["document"]:
        PAT_DOC[d["patient_id"]].append(d)
    AUTH_ENC = defaultdict(list)
    for e in s.rows["encounter"]:
        if e["authorization_id"]:
            AUTH_ENC[e["authorization_id"]].append(e["encounter_date"])
    for v in AUTH_ENC.values():
        v.sort()
    HIST = defaultdict(list)
    for x in s.rows["claim_status_history"]:
        HIST[x["claim_id"]].append(x)
    TX_DEN = {}
    for t in s.rows["transactions"]:
        if t["denial_id"] and t["transaction_type"] == "payment":
            TX_DEN[t["denial_id"]] = t["transaction_id"]
    APPEAL = {a["denial_id"]: a for a in s.rows["appeal"]}
    APPT = {a["appointment_id"]: a for a in s.rows["appointment"]}
    BILL_BY_ENC = {b["encounter_id"]: b for b in s.rows["bill"]}
    APPT_EXPECTED = defaultdict(lambda: D(0))
    for x in s.rows["appointment_details"]:
        APPT_EXPECTED[x["appointment_id"]] += x["expected_charge"] or 0

    def visit_no(e):
        """Visit number within the episode: encounters since the latest evaluation on or before this one."""
        lst = PAT_ENC[e["patient_id"]]
        n = 0
        for x in lst:
            if x["encounter_date"] > e["encounter_date"]:
                break
            n = 1 if x["encounter_type"] == "evaluation" else n + 1
        return max(n, 1)

    def has_poc(e):
        lst = PAT_ENC[e["patient_id"]]
        ev = max((x["encounter_date"] for x in lst if x["encounter_type"] == "evaluation" and x["encounter_date"] <= e["encounter_date"]), default=None)
        return any(d["document_type"] == "plan_of_care" and ev and d["document_date"] >= ev and d["document_date"] <= e["encounter_date"] for d in PAT_DOC[e["patient_id"]])

    # ------------------------------------------------------------------ runs: one per agent per business day
    runs = {}
    d = START
    while d <= TODAY:
        if is_biz(d):
            for code in NAMES:
                runs[(code, d)] = s.add("agent_run", agent_code=code, agent_name=NAMES[code], run_mode="shadow", trigger_type="schedule",
                                        started_at=dt.datetime.combine(d, dt.time(6, 0)), ended_at=dt.datetime.combine(d, dt.time(6, 3)), run_status="ok",
                                        practice_id=ctx["practice"], items_in=0, decisions_made=0, error_count=0, code_version=VERSION)
        d += dt.timedelta(days=1)
    run_rows = {x["agent_run_id"]: x for x in s.rows["agent_run"]}

    def run_for(code, when):
        when = max(START, min(when, TODAY))
        while (code, when) not in runs:
            when += dt.timedelta(days=1) if when < TODAY else -dt.timedelta(days=1)
        return runs[(code, when)]

    # ------------------------------------------------------------------ the common emitter
    stats = defaultdict(int)

    def pick_staff(role, ttype):
        names = ROLE_STAFF.get(role, [])
        return staff[r.choice(names)] if names else None, (r.choice(names) if names else None)

    def emit(agent, dtype, entity, eid, when, outcome, amount, rules, refs, finding=None, task=None, values=(), conf=.9, human=None, approval=None, writeback=None):
        when = max(START, min(when, TODAY))
        run = run_for(agent, when)
        run_rows[run]["items_in"] += 1
        run_rows[run]["decisions_made"] += 1
        dec = s.add("agent_decision", agent_run_id=run, agent_code=agent, decision_type=dtype, entity_type=entity, entity_id=eid, outcome=outcome,
                    decided_at=dt.datetime.combine(when, dt.time(6, 1)), run_mode="shadow", confidence=D(str(conf)).quantize(D("0.0001")), reason_summary=(finding or {}).get("summary", dtype)[:300],
                    rules_checked=len(rules), rules_failed=sum(1 for x in rules if x[1] == "fail"), amount_at_stake=q(amount), data_fallback_level=0, human_outcome=human,
                    human_outcome_date=when if human else None, input_hash=h("input", f"{agent}{entity}{eid}{when}"), practice_id=ctx["practice"], **refs)
        dec_row = s.rows["agent_decision"][-1]
        for i, (rule, res, obs, exp, sev, prid) in enumerate(rules, 1):
            s.add("agent_decision_details", agent_decision_id=dec, check_seq=i, rule_code=rule, check_result=res, agent_code=agent, rule_version="1", rule_source="learned" if prid else "built_in",
                  severity=sev, observed_value=str(obs)[:100], expected_value=str(exp)[:100], input_table=entity, input_fallback_level=0, practice_id=ctx["practice"],
                  payer_id=refs.get("payer_id"), payer_rule_id=prid)
        fid = tid = None
        if finding:
            fkw = {k: v for k, v in finding.items() if k not in ("summary",)}
            fid = s.add("agent_finding", agent_run_id=run, agent_code=agent, entity_type=entity, entity_id=eid, found_date=when, agent_decision_id=dec, summary=finding["summary"][:300],
                        practice_id=ctx["practice"], finding_hash=h("finding", f"{agent}{entity}{eid}{finding['finding_type']}"), **fkw, **refs)
            stats["findings"] += 1
        if task:
            tid = make_task(agent, entity, eid, when, dec, fid, amount, refs, **task)
        if fid or tid:
            dec_row["finding_id"], dec_row["task_id"] = fid, tid
        aid = None
        if approval:
            staff_no = approval.get("by") or r.choice(ROLE_STAFF[approval["role"]])
            ok = r.random() < approval.get("rate", .92)
            adate = min(TODAY, next_biz(when, r.randint(1, 3)))
            aid = s.add("agent_approval", agent_decision_id=dec, approval_type=approval["type"], approval_status="approved" if ok else "rejected", approved_by=staff[staff_no],
                        approver_role=approval["role"], approval_date=adate, amount_approved=q(amount) if ok else None, limit_checked=True, entity_type=entity, entity_id=eid,
                        practice_id=ctx["practice"], approval_ts=dt.datetime.combine(adate, dt.time(10, 15)), agent_task_id=tid)
            if ok and writeback:
                s.add("agent_writeback", agent_decision_id=dec, target_system=writeback[0], writeback_type=writeback[1], send_status="suppressed",
                      attempted_at=dt.datetime.combine(adate, dt.time(10, 20)), agent_approval_id=aid, agent_code=agent, entity_type=entity, entity_id=eid, attempt_no=1,
                      payload_hash=h("payload", f"{dec}"), practice_id=ctx["practice"], claim_id=refs.get("claim_id"), appointment_id=refs.get("appointment_id"))
        for stage, kind, amt, vdate, est, txn in values:
            s.add("agent_value", agent_code=agent, value_stage=stage, amount=q(amt), value_date=min(vdate, TODAY), entity_type=entity, entity_id=eid, agent_finding_id=fid,
                  agent_decision_id=dec, practice_id=ctx["practice"], claim_id=refs.get("claim_id"), denial_id=refs.get("denial_id"), payer_id=refs.get("payer_id"),
                  provider_id=refs.get("provider_id"), transaction_id=txn, is_holdout=False, incremental_amount=q(amt), value_kind=kind, is_estimate=est, attribution_share=D("1.0000"))
        return dec, fid, tid

    def make_task(agent, entity, eid, when, dec, fid, amount, refs, ttype, role, priority="md", title="", **_):
        sid, sname = pick_staff(role, ttype)
        speed = SPEED.get(sname, 1.0)
        due = next_biz(when, SLA[priority])
        lag = max(0, round(SLA[priority] * speed * r.uniform(.4, 2.2)))
        done = next_biz(when, lag) if when + dt.timedelta(days=lag) <= TODAY else None
        mins = int(BASE_MIN.get(ttype, 15) * speed * r.uniform(.7, 1.4))
        late = (done - due).days if done else 0
        esc = 0 if late <= 2 else 1 if late <= 5 else 2 if late <= 10 else 3
        kw = dict(task_type=ttype, owner_role=role, created_date=when, agent_code=agent, entity_type=entity, entity_id=eid, agent_decision_id=dec, agent_finding_id=fid, priority=priority,
                  due_date=due, assigned_to=sid, amount_at_stake=q(amount), title=title[:100], practice_id=ctx["practice"], **refs)
        rework = done and sname and r.random() < REWORK.get(sname, .04) and ttype not in ("unsigned_note",)
        if done and not rework:
            return s.add("agent_task", task_status="done", completed_date=done, outcome="resolved", minutes_spent=mins, contact_channel="system", escalation_level=esc,
                         reminder_count=esc + (1 if r.random() < .25 else 0), **kw)
        if rework:
            t1 = s.add("agent_task", task_status="returned", completed_date=done, outcome="returned", minutes_spent=mins, contact_channel="system", escalation_level=esc, reminder_count=esc, **kw)
            done2 = min(TODAY, next_biz(done, 1))
            return s.version("agent_task", t1, task_status="done", completed_date=done2, outcome="resolved", minutes_spent=int(mins * .6), escalation_level=esc)
        return s.add("agent_task", task_status="open", outcome=None, minutes_spent=None, escalation_level=0, reminder_count=0, **kw)

    def refs_of(claim=None, **kw):
        out = dict(kw)
        if claim:
            out.update(claim_id=claim["claim_id"], patient_id=claim["patient_id"], payer_id=claim["payer_id"], provider_id=claim["rendering_provider_id"],
                       encounter_id=claim["encounter_id"], bill_id=claim["bill_id"], authorization_id=claim["authorization_id"])
            out.pop("claim", None)
        return out

    def rule(code, ok, observed, expected, sev="medium", prid=None):
        return (code, "pass" if ok else "fail", observed, expected, sev, prid)

    # ================================================================== A9 Coach first: it proposes the rules that Mirror then enforces
    generic = {}
    for code, fam, act, src in [("R-AUTH-VISITS", "authorization", "hold_for_review", "built_in"), ("R-COV-ACTIVE", "eligibility", "hold_for_review", "built_in")]:
        generic[code] = s.add("payer_rule", rule_code=code, rule_family=fam, rule_action=act, rule_source_code=src, is_enabled=True, is_synthetic=True, approval_status="approved",
                              effective_from=dt.date(2025, 11, 1), owner_role="front_desk", severity="high", approved_by_staff_id=staff["M01"], approved_date=dt.date(2025, 11, 1))
    learned = {}
    denial_ctx = []
    for dn in s.rows["denial"]:
        cl = CLAIM[dn["claim_id"]]
        e = ENC[cl["encounter_id"]]
        denial_ctx.append((dn["denial_date"], code_of[dn["payer_id"]], carc_code[dn["adjustment_reason_id"]], visit_no(e), dn))
    denial_ctx.sort(key=lambda x: x[0])
    for payer_code, carc_c, rule_code, fam, req in [("SYNUHC", "50", "R-UHC-POC-V", "documentation", "plan_of_care"), ("SYNAET", "97", "R-AET-XU", "coding", "xu_modifier")]:
        seen = [x for x in denial_ctx if x[1] == payer_code and x[2] == carc_c]
        trig = None
        for i in range(9, len(seen)):
            if (seen[i][0] - seen[i - 9][0]).days <= 60:
                trig = seen[i][0]
                evidence = [x for x in seen if x[0] <= trig and (trig - x[0]).days <= 60]
                break
        if not trig:
            continue
        threshold = min(x[3] for x in evidence) if carc_c == "50" else None
        prop = next_biz(trig, 2)
        appr = next_biz(prop, 5)
        pr = s.add("payer_rule", rule_code=rule_code + (str(threshold) if threshold else ""), rule_family=fam, rule_action="hold_for_review", rule_source_code="learned", payer_id=P[payer_code],
                   adjustment_reason_id=carc_ids[carc_c], requirement_code=req, unit_limit=threshold, evidence_claim_count=len(evidence),
                   evidence_denied_count=len(evidence), evidence_denied_amount=q(sum(x[4]["denied_amount"] for x in evidence)), evidence_from_date=evidence[0][0], evidence_to_date=trig,
                   owner_role="biller", severity="high", is_enabled=True, is_synthetic=True, approval_status="approved", approved_by_staff_id=staff["M01"], approved_date=appr,
                   effective_from=appr, last_confirmed_date=appr)
        learned[payer_code] = dict(id=pr, since=appr, threshold=threshold, carc=carc_c)
        emit("A9", "rule_proposal", "payer_rule", pr, prop, "proposed", sum(x[4]["denied_amount"] for x in evidence),
             [rule("PATTERN-CLUSTER", False, f"{len(evidence)} denials in 60 days", ">= 10", "high", None)], refs_of(payer_id=P[payer_code]),
             finding=dict(finding_type="rule_proposal", finding_status="resolved", upstream_stage="billing", is_preventable=True, severity="high", resolved_date=appr, resolution="approved",
                          amount_at_risk=q(sum(x[4]["denied_amount"] for x in evidence)),
                          summary=f"{len(evidence)} CARC {carc_c} denials from {payer_code} in 60 days; proposed rule {rule_code}"),
             task=dict(ttype="rule_review", role="manager", priority="md", title=f"Approve rule {rule_code} for {payer_code}"),
             approval=dict(type="rule_activation", role="manager", by="M01", rate=1.0), conf=.9)

    # ================================================================== A5 Mirror: pre-release review of every claim
    tp = fp = fn = tn = 0
    held = []
    for cl in s.rows["claim"]:
        e = ENC[cl["encounter_id"]]
        code = code_of[cl["payer_id"]]
        when = cl["submitted_date"]
        lines = CD[cl["claim_id"]]
        results, fails = [], []
        # generic: authorization visits
        if e["authorization_id"]:
            au = AUTH[e["authorization_id"]]
            n = sum(1 for dte in AUTH_ENC[au["authorization_id"]] if dte <= e["encounter_date"])
            bad = n > au["units_approved"]
            results.append(rule("R-AUTH-VISITS", not bad, f"visit {n}", f"<= {au['units_approved']}", "high", generic["R-AUTH-VISITS"]))
            if bad:
                fails.append(("198", .92))
        cv = COV[cl["coverage_id"]]
        bad = bool(cv["termination_date"] and cv["termination_date"] < e["encounter_date"])
        results.append(rule("R-COV-ACTIVE", not bad, f"ended {cv['termination_date']}", f">= {e['encounter_date']}", "high", generic["R-COV-ACTIVE"]))
        if bad:
            fails.append(("27", .95))
        if code in learned and learned[code]["since"] <= when:
            L = learned[code]
            if L["carc"] == "50":
                vn = visit_no(e)
                bad = vn >= L["threshold"] and not has_poc(e)
                results.append(rule("R-UHC-POC-V", not bad, f"visit {vn}, plan of care {'on file' if has_poc(e) else 'missing'}", f"visit < {L['threshold']} or plan on file", "high", L["id"]))
            else:
                l97 = [x for x in lines if cpt_code[x["cpt_code_id"]] == "97530"]
                pair = any(cpt_code[x["cpt_code_id"]] == "97140" for x in lines) and l97
                mods = {x["modifier_2_id"] for x in l97} | {x["modifier_1_id"] for x in l97}
                bad = bool(pair) and not (mods & {ctx["modifier"]["XU"], ctx["modifier"]["59"]})
                results.append(rule("R-AET-XU", not bad, "97140+97530 without XU/59" if bad else "ok", "distinct-service modifier", "high", L["id"]))
            if bad:
                fails.append((L["carc"], .85))
        actually_denied = bool(DEN.get(cl["claim_id"]))
        if fails:
            carc_c, p = max(fails, key=lambda x: x[1])
            hold_amt = cl["total_charge"]
            tp += actually_denied
            fp += not actually_denied
            held.append(cl)
            expected_allowed = sum((x["expected_allowed"] or 0) for x in lines)
            dn_list = DEN.get(cl["claim_id"], [])
            dec, fid, tid = emit("A5", "prerelease_review", "claim", cl["claim_id"], when, "hold", hold_amt, results, refs_of(cl),
                                 finding=dict(finding_type="predicted_denial", finding_status="confirmed" if actually_denied else "unconfirmed", amount_at_risk=q(hold_amt),
                                              upstream_stage=carc_row[carc_ids[carc_c]]["upstream_stage"], is_preventable=True, severity="high",
                                              resolved_date=dn_list[0]["denial_date"] if dn_list else None, resolution="denied_confirmed" if actually_denied else "no_denial",
                                              predicted_probability=D(str(p)).quantize(D("0.0001")), predicted_reason_category=carc_row[carc_ids[carc_c]]["reason_category"],
                                              predicted_allowed_amount=q(expected_allowed), summary=f"Predicted CARC {carc_c}: {[x[0] for x in results if x[1] == 'fail'][0]}"),
                                 task=dict(ttype="claim_hold_review", role="biller", priority="hi", title=f"Review before release: CARC {carc_c} risk"),
                                 values=([("detected", "denial_prevented", sum(x["denied_amount"] for x in dn_list), when, True, None)] if actually_denied else []), conf=p)
        else:
            fn += actually_denied
            tn += not actually_denied
            if actually_denied or r.random() < .03:
                emit("A5", "prerelease_review", "claim", cl["claim_id"], when, "release", cl["total_charge"], results, refs_of(cl), conf=.9)
    ctx["mirror_score"] = dict(tp=tp, fp=fp, fn=fn, tn=tn)

    # ================================================================== A1 Gatekeeper: every eligibility check
    for ck in s.rows["eligibility_check"]:
        ended = ck["plan_end_date"] and ck["plan_end_date"] < ck["service_date"]
        ap = APPT[ck["appointment_id"]]
        rules = [rule("R-COV-ACTIVE", not ended, f"ends {ck['plan_end_date']}", f">= {ck['service_date']}", "high"), rule("R-AAA-REJECT", not ck["is_aaa_reject"], "no reject", "no reject", "medium")]
        refs = dict(patient_id=ck["patient_id"], payer_id=ck["payer_id"], appointment_id=ck["appointment_id"], provider_id=ap["provider_id"])
        if ended:
            emit("A1", "eligibility_review", "appointment", ck["appointment_id"], ck["check_date"], "flag", q(APPT_EXPECTED[ck["appointment_id"]]), rules, refs,
                 finding=dict(finding_type="coverage_ended", finding_status="open" if ck["service_date"] >= TODAY else "resolved", upstream_stage="eligibility", is_preventable=True, severity="high",
                              amount_at_risk=q(APPT_EXPECTED[ck["appointment_id"]]), deadline_date=ck["service_date"], summary=f"Coverage ended {ck['plan_end_date']}, before the visit on {ck['service_date']}"),
                 task=dict(ttype="coverage_follow_up", role="front_desk", priority="hi", title="Coverage has ended: confirm new insurance before the visit"), conf=.95)
        elif r.random() < .03:
            emit("A1", "eligibility_review", "appointment", ck["appointment_id"], ck["check_date"], "clear", 0, rules, refs, conf=.97)

    # ================================================================== A2 Permit Clerk: authorization about to run out
    appts_by_auth = defaultdict(list)
    for ap_det in s.rows["appointment_details"]:
        if ap_det["authorization_id"] and ap_det["line_number"] == 1:
            appts_by_auth[ap_det["authorization_id"]].append(ap_det["appointment_id"])
    for aid, appts in appts_by_auth.items():
        au = AUTH[aid]
        appts.sort(key=lambda i: APPT[i]["appointment_date"])
        for n, apid in enumerate(appts, 1):
            ap = APPT[apid]
            if ap["appointment_status"] == "cancelled" or ap["appointment_status"] == "no_show":
                continue
            when = ap["appointment_date"] - dt.timedelta(days=7)
            if n > au["units_approved"] and when <= TODAY:
                emit("A2", "authorization_review", "appointment", apid, when, "flag", q(APPT_EXPECTED[apid]),
                     [rule("R-AUTH-VISITS", False, f"visit {n}", f"<= {au['units_approved']}", "high", generic["R-AUTH-VISITS"])],
                     dict(patient_id=ap["patient_id"], payer_id=ap["payer_id"], appointment_id=apid, provider_id=ap["provider_id"], authorization_id=aid),
                     finding=dict(finding_type="authorization_exhausted", finding_status="open" if ap["appointment_date"] >= TODAY else "resolved", upstream_stage="authorization", is_preventable=True,
                                  severity="high", amount_at_risk=q(APPT_EXPECTED[apid]), deadline_date=ap["appointment_date"], summary=f"Authorization allows {au['units_approved']} visits; this is visit {n}"),
                     task=dict(ttype="authorization_check", role="front_desk", priority="hi", title="Request more visits before the next appointment"), conf=.9)

    # ================================================================== A3 Note Chaser and A4 Code Whisperer
    for e in s.rows["encounter"]:
        lag = e["signature_lag_days"]
        late = e["note_status"] == "unsigned" or (lag is not None and lag >= 4)
        if late:
            when = e["encounter_date"] + dt.timedelta(days=1)
            unsigned = e["note_status"] == "unsigned"
            amt = BILL_BY_ENC[e["encounter_id"]]["total_billed"]
            emit("A3", "documentation_review", "encounter", e["encounter_id"], when, "flag", amt,
                 [rule("R-NOTE-SIGNED", False, "unsigned" if unsigned else f"signed after {lag} days", "signed within 2 days", "medium")],
                 dict(patient_id=e["patient_id"], payer_id=e["payer_id"], provider_id=e["rendering_provider_id"], encounter_id=e["encounter_id"]),
                 finding=dict(finding_type="unsigned_note", finding_status="open" if unsigned else "resolved", upstream_stage="documentation", is_preventable=True, severity="medium",
                              amount_at_risk=q(amt), resolved_date=None if unsigned else e["note_signed_date"], resolution=None if unsigned else "signed",
                              summary="Note not signed; the charge is held" if unsigned else f"Note signed {lag} days after the visit"),
                 task=dict(ttype="unsigned_note", role="provider", priority="md", title="Sign the visit note"), conf=.97)
        for ln in ENCLINES[e["encounter_id"]]:
            kc = cpt_code[ln["cpt_code_id"]]
            if kc in ("97161", "97162", "97163", "97165", "97166") and ln["documented_level"]:
                billed = {"97161": 1, "97165": 1, "97162": 2, "97166": 2, "97163": 3}[kc]
                if billed != ln["documented_level"]:
                    ot = kc in ("97165", "97166")
                    suggest = (("97165", "97166", "97166") if ot else ("97161", "97162", "97163"))[ln["documented_level"] - 1]
                    diff = q(ctx["fee"][suggest] - ctx["fee"][kc])
                    over = diff < 0
                    dec, fid, tid = emit("A4", "code_review", "encounter", e["encounter_id"], e["encounter_date"] + dt.timedelta(days=1), "suggest", abs(diff),
                                         [rule("R-EVAL-LEVEL", False, f"billed {kc}", f"documentation supports {suggest}", "high" if over else "medium")],
                                         dict(patient_id=e["patient_id"], payer_id=e["payer_id"], provider_id=e["rendering_provider_id"], encounter_id=e["encounter_id"]),
                                         finding=dict(finding_type="code_level_mismatch", finding_status="resolved", upstream_stage="coding", is_preventable=True, severity="high" if over else "medium",
                                                      amount_at_risk=abs(diff), suggested_value=suggest, final_value=suggest if r.random() < .7 else kc, value_difference=diff,
                                                      is_compliance_risk=over, resolved_date=min(TODAY, e["encounter_date"] + dt.timedelta(days=4)), resolution="reviewed",
                                                      summary=f"{kc} billed, documentation supports {suggest}" + (" (billed higher: compliance risk)" if over else "")),
                                         task=dict(ttype="code_review", role="coder", priority="md", title=f"Review evaluation level: {kc} vs {suggest}"),
                                         values=[] if over else [("detected", "charge_capture", diff, e["encounter_date"], True, None)],
                                         approval=dict(type="code_change", role="coder", rate=.75), conf=.82, human="accepted")

    # ================================================================== A6 Courier: clearinghouse rejections
    for cl in s.rows["claim"]:
        rej = [x for x in HIST[cl["claim_id"]] if x["is_rejection"]]
        for x in rej:
            emit("A6", "rejection_review", "claim", cl["claim_id"], x["event_date"], "flag", cl["total_charge"],
                 [rule("R-277CA-ACCEPT", False, x["rejection_reason"], "accepted", "high")], refs_of(cl),
                 finding=dict(finding_type="clearinghouse_rejection", finding_status="resolved", upstream_stage="billing", is_preventable=True, severity="high", amount_at_risk=cl["total_charge"],
                              resolved_date=min(TODAY, next_biz(x["event_date"], 1)), resolution="corrected", deadline_date=next_biz(x["event_date"], 1),
                              summary=f"Rejected at the clearinghouse: {x['rejection_reason']}"),
                 task=dict(ttype="fix_rejection", role="biller", priority="hi", title="Correct and resubmit the rejected claim"),
                 approval=dict(type="resubmit", role="billing_lead", by="B03", rate=.98), writeback=("PM", "task_note"), conf=.95, human="accepted",
                 values=[("detected", "cash_acceleration", cl["total_charge"], x["event_date"], True, None)])

    # ================================================================== A7 Hunter: no payer response, and filing deadlines
    for cl in s.rows["claim"]:
        if cl["claim_status"] == "no_response":
            code = code_of[cl["payer_id"]]
            when = next_biz(cl["submitted_date"], pinfo[code]["turn"] + 14)
            if when > TODAY:
                continue
            days = (TODAY - cl["submitted_date"]).days
            deadline = cl["service_date_from"] + dt.timedelta(days=pinfo[code]["filing"])
            risk = (deadline - TODAY).days
            emit("A7", "claim_follow_up", "claim", cl["claim_id"], when, "flag", cl["total_charge"],
                 [rule("R-PAYER-RESPONSE", False, f"{days} days, no response", f"<= {pinfo[code]['turn'] + 14} days", "high"), rule("R-FILING-WINDOW", risk > 30, f"{risk} days left", "> 30", "high")],
                 refs_of(cl), finding=dict(finding_type="no_payer_response", finding_status="open", upstream_stage="billing", is_preventable=False, severity="high" if risk <= 30 else "medium",
                                           amount_at_risk=cl["total_charge"], deadline_date=deadline, summary=f"No payer response after {days} days; filing window ends {deadline}"),
                 task=dict(ttype="claim_follow_up", role="ar_specialist", priority="hi" if risk <= 30 else "md", title="Call the payer or resubmit: no response"), conf=.88,
                 values=[("detected", "claim_recovery", cl["total_charge"], when, True, None)])

    # ================================================================== A8 Advocate: every denial
    approved_appeal = {}
    for dn in s.rows["denial"]:
        cl = CLAIM[dn["claim_id"]]
        cr = carc_row[dn["adjustment_reason_id"]]
        recovered = dn["outcome"] == "overturned"
        appealable = cr["is_appealable"]
        dl = dn["appeal_deadline"]
        sev = "high" if (dl - TODAY).days <= 30 and dn["denial_status"] in ("open", "in_appeal") else "medium"
        values = [("detected", "denial_recovery", dn["denied_amount"], dn["denial_date"], False, None)]
        if recovered:     # confirmed only with ledger proof; cash that was paid but never posted stays pending
            values.append(("confirmed" if TX_DEN.get(dn["denial_id"]) else "pending", "denial_recovery", dn["recovered_amount"], dn["resolved_date"], False, TX_DEN.get(dn["denial_id"])))
        dec, fid, tid = emit("A8", "denial_triage", "denial", dn["denial_id"], dn["denial_date"], "route", dn["denied_amount"],
                             [rule("R-CARC-ROUTE", True, f"CARC {carc_code[dn['adjustment_reason_id']]}", cr["owner_role"], "medium"), rule("R-APPEAL-WINDOW", dl > TODAY, f"deadline {dl}", "open", "high")],
                             refs_of(cl, denial_id=dn["denial_id"]),
                             finding=dict(finding_type="denial", finding_status={"resolved": "resolved", "written_off": "resolved", "in_appeal": "in_progress", "open": "open"}[dn["denial_status"]],
                                          upstream_stage=dn["upstream_stage"], is_preventable=dn["is_preventable"], severity=sev, amount_at_risk=dn["denied_amount"], amount_recovered=dn["recovered_amount"],
                                          deadline_date=dl, resolved_date=dn["resolved_date"], resolution={"overturned": "recovered", "written_off": "written_off"}.get(dn["outcome"]),
                                          summary=f"CARC {carc_code[dn['adjustment_reason_id']]}: {cr['short_label']}; owner {cr['owner_role']}"),
                             task=dict(ttype="denial_work", role="denial_specialist" if appealable else cr["owner_role"] if cr["owner_role"] in ROLE_STAFF else "biller", priority="hi" if sev == "high" else "md",
                                       title=f"Work the denial: {cr['short_label']}"[:100]),
                             values=values, conf=.9, human="accepted",
                             approval=dict(type="appeal_send", role="denial_specialist", by="D01", rate=.95) if (appealable and dn["denial_id"] in APPEAL) else None,
                             writeback=("portal", "appeal_submit"))
        if dn["denial_id"] in APPEAL:
            ap = APPEAL[dn["denial_id"]]
            ap["agent_decision_id"] = dec
            ap_row = next((x for x in s.rows["agent_approval"] if x["agent_decision_id"] == dec), None)
            if ap_row:
                ap["agent_approval_id"] = ap_row["agent_approval_id"]

    # ================================================================== A10 Auditor: paid below the contract
    for cl in s.rows["claim"]:
        for ln in CD[cl["claim_id"]]:
            if ln["allowed_amount"] is None or not ln["expected_allowed"]:
                continue
            expected = ln["expected_allowed"] * (D("0.85") if ctx["modifier"]["CQ"] in (ln["modifier_1_id"], ln["modifier_2_id"]) else D(1))
            gap = q(expected - ln["allowed_amount"])
            if gap > q(expected * D("0.03")):
                when = cl["last_payment_date"] or cl["submitted_date"]
                emit("A10", "payment_audit", "claim_detail", ln["claim_detail_id"], when, "flag", gap,
                     [rule("R-CONTRACT-RATE", False, f"allowed {ln['allowed_amount']}", f"{q(expected)}", "high")], refs_of(cl),
                     finding=dict(finding_type="underpayment", finding_status="open", upstream_stage="payment", is_preventable=False, severity="medium", amount_at_risk=gap,
                                  deadline_date=when + dt.timedelta(days=pinfo[code_of[cl["payer_id"]]]["appeal"]),
                                  summary=f"{cpt_code[ln['cpt_code_id']]} paid {gap} below the contract rate"),
                     task=dict(ttype="dispute_package", role="billing_lead", priority="md", title="Dispute the underpayment with the payer"),
                     approval=dict(type="dispute_send", role="billing_lead", by="B03", rate=.9), writeback=("portal", "dispute_submit"), conf=.93,
                     values=[("detected", "underpayment", gap, when, False, None)])

    # ================================================================== A11 Bookkeeper: remits received but not posted
    for p in s.rows["payment"]:
        if p["unapplied_amount"] and p["unapplied_amount"] > 0:
            emit("A11", "remit_reconciliation", "payment", p["payment_id"], next_biz(p["payment_date"], 1), "flag", p["unapplied_amount"],
                 [rule("R-REMIT-POSTED", False, f"posted {p['posted_amount']}", f"{p['payment_amount']}", "high")], dict(payer_id=p["payer_id"]),
                 finding=dict(finding_type="unposted_remit", finding_status="open", upstream_stage="payment", is_preventable=True, severity="high", amount_at_risk=p["unapplied_amount"],
                              summary="Payer paid but the remit was not posted to the ledger"),
                 task=dict(ttype="post_remit", role="payment_poster", priority="hi", title="Post the remit"), conf=.99,
                 values=[("detected", "unposted_cash", p["unapplied_amount"], p["payment_date"], False, None)])
        elif p["payment_source"] == "payer" and r.random() < .04:
            emit("A11", "remit_reconciliation", "payment", p["payment_id"], next_biz(p["payment_date"], 1), "match", 0, [rule("R-REMIT-POSTED", True, "posted in full", "posted in full", "high")],
                 dict(payer_id=p["payer_id"]), conf=.99)

    # ================================================================== A12 Concierge: patient balances and statements
    stmt = 0
    for a in s.rows["ar"]:
        if a["balance_owner"] == "patient" and a["days_outstanding"] >= 20:
            when = a["service_date"] + dt.timedelta(days=30)
            if when > TODAY:
                continue
            level = 0 if a["days_outstanding"] < 60 else 1 if a["days_outstanding"] < 90 else 2
            st = s.add("patient_statement", statement_number=ctx["num"]("STM", "stm"), patient_id=a["patient_id"], statement_date=when, statement_amount=a["balance"], channel=r.choice(["mail", "email", "portal"]),
                       statement_status="sent", practice_id=ctx["practice"], bill_id=a["bill_id"], claim_id=a["claim_id"], due_date=when + dt.timedelta(days=30), sent_at=dt.datetime.combine(when, dt.time(8, 0)),
                       status_date=when, dunning_level=level)
            stmt += 1
            if r.random() < .25:
                emit("A12", "balance_follow_up", "ar", a["ar_id"], when, "flag", a["balance"], [rule("R-BALANCE-AGE", False, f"{a['days_outstanding']} days", "<= 60", "medium")],
                     dict(patient_id=a["patient_id"], payer_id=a["payer_id"]),
                     finding=dict(finding_type="patient_balance", finding_status="open", upstream_stage="patient", is_preventable=False, severity="low", amount_at_risk=a["balance"],
                                  summary=f"Patient balance {a['balance']} open {a['days_outstanding']} days"),
                     task=dict(ttype="patient_follow_up", role="biller", priority="lo", title="Follow up on the patient balance"), conf=.85)

    # ================================================================== A13 Credentialing: provider enrolments and screening
    en_providers = [p for p in s.rows["provider"] if p["provider_type"] in ("PT", "OT", "PTA")]
    for i, pr in enumerate(en_providers):
        for code in ("SYNUHC", "SYNBCBS", "SYNAET", "SYNCIG", "SYNMCR"):
            exp_days = 70 + (i * 37 + len(code) * 11) % 500
            if pr["provider_name"].startswith("Haines") and code == "SYNCIG":
                exp_days = 21
            if pr["provider_name"].startswith("Okafor") and code == "SYNMCR":
                exp_days = 38
            exp = TODAY + dt.timedelta(days=exp_days)
            en = s.add("enrollment", enrollment_number=ctx["num"]("ENR", "enr"), provider_id=pr["provider_id"], payer_id=P[code], practice_id=ctx["practice"], event_type="enrollment",
                       event_date=dt.date(2024, 1, 15), enrollment_status="active", enrollment_type="individual", effective_date=dt.date(2024, 1, 15), expires_date=exp,
                       revalidation_due_date=exp - dt.timedelta(days=60), last_revalidated_date=dt.date(2025, 2, 1))
            if exp_days <= 60:
                emit("A13", "enrollment_review", "enrollment", en, TODAY - dt.timedelta(days=1), "flag", 0,
                     [rule("R-ENROLL-EXPIRY", False, f"expires {exp}", "> 60 days", "high")], dict(provider_id=pr["provider_id"], payer_id=P[code]),
                     finding=dict(finding_type="enrollment_expiring", finding_status="open", upstream_stage="credentialing", is_preventable=True, severity="high", deadline_date=exp,
                                  summary=f"{pr['provider_name']} enrolment with {code} expires in {exp_days} days"),
                     task=dict(ttype="revalidation", role="manager", priority="hi", title="Start revalidation"), conf=.96)
        for mth in range(0, 12):
            sd = dt.date(2025, 11, 15) + dt.timedelta(days=30 * mth)
            if sd <= TODAY:
                s.add("enrollment", provider_id=pr["provider_id"], practice_id=ctx["practice"], event_type="screening", event_date=sd, screening_source="OIG", screening_result="clear",
                      screening_list_date=sd, match_method="npi")

    # ================================================================== A14 Captain: weekly cash forecast per payer, scored against what arrived
    pays = defaultdict(list)
    for p in s.rows["payment"]:
        if p["payment_source"] == "payer":
            pays[p["payer_id"]].append(p)
    first = dt.date(2026, 2, 2)
    n_f = 0
    for pcode, pid in P.items():
        if pinfo[pcode]["typ"] == "self_pay":
            continue
        for k in range(0, 40):
            asof = first + dt.timedelta(days=7 * k)
            if asof > TODAY:
                break
            w0, w1 = asof + dt.timedelta(days=1), asof + dt.timedelta(days=7)
            exp, cnt = D(0), 0
            for cl in s.rows["claim"]:
                if cl["payer_id"] != pid or cl["submitted_date"] > asof or cl["submitted_date"] < asof - dt.timedelta(days=75):
                    continue
                done = [x for x in HIST[cl["claim_id"]] if x["event_type"] == "remit_835" and x["event_date"] <= asof]
                if done:
                    continue
                pay_date = next_biz(cl["submitted_date"], pinfo[pcode]["turn"] + 2)
                if w0 <= pay_date <= w1:
                    exp += sum((x["expected_allowed"] or 0) for x in CD[cl["claim_id"]]) * D("0.93")
                    cnt += 1
            actual = sum((p["payment_amount"] for p in pays[pid] if w0 <= p["payment_date"] <= w1), D(0)) if w1 <= TODAY else None
            lo, hi = q(exp * D("0.70")), q(exp * D("1.30"))
            s.add("agent_forecast", forecast_type="weekly_cash", as_of_date=asof, target_start_date=w0, target_end_date=w1, expected_amount=q(exp), low_amount=lo, high_amount=hi,
                  probability=D("0.8000"), claim_count=cnt, practice_id=ctx["practice"], payer_id=pid, actual_amount=q(actual) if actual is not None else None,
                  actual_known_date=w1 if actual is not None else None, within_range=(lo <= actual <= hi) if actual is not None else None, interval_level=D("0.80"),
                  model_name="rules", code_version=VERSION)
            n_f += 1
    # overdue human work gets escalated by the Captain
    for t in list(s.rows["agent_task"]):
        if t["task_status"] == "open" and t["due_date"] < TODAY - dt.timedelta(days=3) and t["version"] == 1:
            late = (TODAY - t["due_date"]).days
            t["escalation_level"] = 1 if late <= 5 else 2
            t["reminder_count"] = 1 + (late > 5)
    # A15 Detective: realisation by payer and code over the last 60 days
    cells = defaultdict(lambda: [D(0), D(0), 0])
    for cl in s.rows["claim"]:
        if cl["submitted_date"] < TODAY - dt.timedelta(days=60):
            continue
        for ln in CD[cl["claim_id"]]:
            if ln["allowed_amount"] is not None and ln["expected_allowed"]:
                exp_ = ln["expected_allowed"] * (D("0.85") if ctx["modifier"]["CQ"] in (ln["modifier_1_id"], ln["modifier_2_id"]) else D(1))
                c = cells[(cl["payer_id"], ln["cpt_code_id"])]
                c[0] += ln["allowed_amount"]; c[1] += exp_; c[2] += 1
    for (pid, cid), (got, exp_, n) in cells.items():
        if n >= 20 and exp_ > 0 and got / exp_ < D("0.95"):
            emit("A15", "revenue_assurance", "payer_cpt", cid, TODAY, "flag", q(exp_ - got),
                 [rule("R-REALISATION", False, f"{(got / exp_ * 100):.1f}% of contract", ">= 95%", "high")], dict(payer_id=pid),
                 finding=dict(finding_type="realisation_variance", finding_status="open", upstream_stage="payment", is_preventable=False, severity="high", amount_at_risk=q(exp_ - got),
                              summary=f"{code_of[pid]} pays {(got / exp_ * 100):.1f}% of the contract on {cpt_code[cid]} over {n} lines (60 days)"),
                 task=dict(ttype="dispute_package", role="billing_lead", priority="hi", title="Investigate payer-wide underpayment"), conf=.9)
    ctx["agent_stats"] = dict(forecasts=n_f, statements=stmt)
    return ctx
