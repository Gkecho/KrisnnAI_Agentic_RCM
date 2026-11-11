"""Decision traces: for every agent decision, what woke the agent, what it read (tables, columns, SQL, rows, values), what it concluded, and why the work moved on.

The SQL is the equivalent statement on the canonical tables. The engine serves these reads from its in-memory copy of those tables (loaded from
Postgres when the server started), so each read can be re-run on the real database from the UI to confirm it returns the same answer.
Each builder takes the same source row the agent evaluated, so what is logged is what the rule used.
"""
import datetime as dt
from decimal import Decimal


def _v(x):
    if isinstance(x, Decimal):
        return float(x)
    if isinstance(x, (dt.date, dt.datetime)):
        return x.isoformat()
    return x


def read(table, cols, sql, params, result, why, rows=1, runnable=True):
    return dict(runnable=runnable, table=table, cols=cols, sql=sql, params=[_v(p) for p in params], rows=rows, result={k: _v(v) for k, v in result.items()} if isinstance(result, dict) else _v(result), why=why)


def build(R, dtype, d, src, rules, refs, outcome):
    """Returns (trigger, reads, handoff) for one decision."""
    W = R.W
    fn = globals().get("_" + dtype)
    if fn is None or src is None:
        return "Scheduled evaluation", [], ""
    return fn(R, W, d, src, rules, refs, outcome)


# ------------------------------------------------------------------ A1
def _eligibility_review(R, W, d, ck, rules, refs, outcome):
    ap = W.appt[ck["appointment_id"]]
    amt = W.appt_expected[ck["appointment_id"]]
    reads = [
        read("eligibility_check", ["plan_end_date", "service_date", "is_aaa_reject"], "SELECT plan_end_date, service_date, is_aaa_reject FROM eligibility_check WHERE eligibility_check_id = %s",
             [ck["eligibility_check_id"]], dict(plan_end_date=ck["plan_end_date"], service_date=ck["service_date"], is_aaa_reject=ck["is_aaa_reject"]), "the payer's 271 answer for this visit"),
        read("appointment", ["provider_id"], "SELECT provider_id FROM appointment WHERE appointment_id = %s", [ck["appointment_id"]], dict(provider_id=ap["provider_id"]), "who the visit is with"),
        read("appointment_details", ["expected_charge"], "SELECT COALESCE(SUM(expected_charge), 0) AS expected_charge FROM appointment_details WHERE appointment_id = %s", [ck["appointment_id"]],
             dict(expected_charge=amt), "dollars at stake if the visit goes ahead uninsured"),
    ]
    trig = f"A 271 eligibility response (check #{ck['eligibility_check_id']}) reached the practice on {ck['check_date']} for the visit on {ck['service_date']}"
    hand = ("Front desk gets a task to confirm new insurance. The visit is not blocked; A2 Permit Clerk (authorization) and A5 Mirror (claim release) will check the same patient again at their stages."
            if outcome == "flag" else "Coverage is active, so the next check is A2 Permit Clerk (authorization) for visits that need one.")
    return trig, reads, hand


# ------------------------------------------------------------------ A2
def _authorization_review(R, W, d, src, rules, refs, outcome):
    ap, n, aid = src
    au = W.auth[aid]
    reads = [
        read("appointment_details", ["authorization_id"], "SELECT authorization_id FROM appointment_details WHERE appointment_id = %s AND line_number = 1", [ap["appointment_id"]], dict(authorization_id=aid),
             "which authorization covers this appointment"),
        read("authorization", ["units_approved"], "SELECT units_approved FROM \"authorization\" WHERE authorization_id = %s", [aid], dict(units_approved=au["units_approved"]), "visits the payer approved"),
        read("appointment", ["appointment_date", "appointment_status"],
             "SELECT COUNT(*) AS visit_number FROM appointment_details d JOIN appointment a USING (appointment_id) WHERE d.line_number = 1 AND d.authorization_id = %s "
             "AND a.appointment_status IN ('completed','scheduled') AND a.appointment_date <= %s", [aid, ap["appointment_date"]], dict(visit_number=n), "how many visits use this authorization up to and including this one"),
    ]
    trig = f"Appointment #{ap['appointment_id']} on {ap['appointment_date']} is one week away (booked {ap['booked_date']})"
    return trig, reads, "Front desk gets a task to ask the payer for more visits. At claim time A5 Mirror will predict a CARC 198 denial if no extension is on file; A3 Note Chaser watches the visit note."


# ------------------------------------------------------------------ A3
def _documentation_review(R, W, d, e, rules, refs, outcome):
    b = W.bill_by_enc.get(e["encounter_id"])
    reads = [
        read("encounter", ["note_signed_date", "encounter_date"], "SELECT CASE WHEN note_signed_date <= %s THEN note_signed_date END AS note_signed_date_as_of_today, encounter_date FROM encounter WHERE encounter_id = %s",
             [d, e["encounter_id"]], dict(note_signed_date_as_of_today=None, encounter_date=e["encounter_date"]), "whether the note was signed by today (only facts known today)"),
    ]
    if b is not None:
        reads.append(read("bill", ["total_billed", "bill_status"], "SELECT total_billed, bill_status FROM bill WHERE encounter_id = %s", [e["encounter_id"]], dict(total_billed=b["total_billed"]), "charge waiting on the note"))
    trig = f"Three days after the visit on {e['encounter_date']} the note was still unsigned"
    return trig, reads, "Provider gets a task to sign. The charge stays on hold, so no claim exists yet: A4 Code Whisperer waits for the signed note and A5 Mirror sees nothing until then."


def _unbilled_visit_review(R, W, d, e, rules, refs, outcome):
    reads = [read("encounter", ["encounter_date", "note_signed_date", "payer_id"], "SELECT encounter_date, CASE WHEN note_signed_date <= %s THEN note_signed_date END AS note_signed_by_today, payer_id FROM encounter WHERE encounter_id = %s",
                  [d, e["encounter_id"]], dict(encounter_date=e["encounter_date"]), "the visit"),
             read("bill", ["bill_id"], "SELECT COUNT(*) AS bills FROM bill WHERE encounter_id = %s AND charge_entered_date <= %s", [e["encounter_id"], d], dict(bills=0), "no charge has been entered for this visit by today")]
    return (f"Four days after the visit on {e['encounter_date']} no bill exists", reads,
            "Biller gets a task to enter the charge (or record why there is none). If the note is unsigned the provider also gets the signing task.")


def _pre_visit_review(R, W, d, ap, rules, refs, outcome):
    reads = [read("appointment", ["appointment_date", "payer_id", "coverage_id"], "SELECT appointment_date, payer_id, coverage_id FROM appointment WHERE appointment_id = %s", [ap["appointment_id"]],
                  dict(appointment_date=ap["appointment_date"]), "the scheduled visit"),
             read("eligibility_check", ["check_date", "other_payer_id"], "SELECT MAX(check_date) AS last_check, COUNT(other_payer_id) AS other_payer_named FROM eligibility_check WHERE appointment_id = %s AND check_date <= %s",
                  [ap["appointment_id"], d], dict(note="only checks done by the review date"), "the latest eligibility check known today")]
    return (f"The visit on {ap['appointment_date']} is within {3} business days", reads, "Front desk gets a task to verify coverage before the visit.")


def _scheduled_auth_review(R, W, d, ap, rules, refs, outcome):
    reads = [read("appointment_line", ["planned_cpt_code_id", "planned_units"], "SELECT k.code, l.planned_units FROM appointment_line l JOIN cpt_code k ON k.cpt_code_id = l.planned_cpt_code_id WHERE l.appointment_id = %s ORDER BY l.line_number",
                  [ap["appointment_id"]], dict(lines=[W.cpt[c] for _n, c, _u in W.appt_lines.get(ap["appointment_id"], ())]), "every planned line, not only the first", rows=len(W.appt_lines.get(ap["appointment_id"], ()))),
             read("authorization", ["authorization_status", "valid_from", "valid_to", "units_approved", "decision_date"],
                  "SELECT authorization_status, valid_from, valid_to, units_approved FROM \"authorization\" WHERE patient_id = %s AND payer_id = %s AND decision_date <= %s", [ap["patient_id"], ap["payer_id"], d],
                  dict(note="only authorizations decided by the review date"), "authorizations on file that day")]
    return (f"The visit on {ap['appointment_date']} is a week away", reads, "Front desk gets a task to request, extend or renew the authorization before the visit.")


# ------------------------------------------------------------------ A4
def _code_review(R, W, d, e, rules, refs, outcome):
    lines = [l for l in W.enc_lines[e["encounter_id"]] if W.cpt[l["cpt_code_id"]] in ("97161", "97162", "97163", "97165", "97166")]
    ln = lines[0]
    kc = W.cpt[ln["cpt_code_id"]]
    reads = [
        read("encounter_details", ["cpt_code_id", "documented_level"],
             "SELECT k.code, d.documented_level FROM encounter_details d JOIN cpt_code k USING (cpt_code_id) WHERE d.encounter_id = %s AND k.code IN ('97161','97162','97163','97165','97166')",
             [e["encounter_id"]], dict(code=kc, documented_level=ln["documented_level"]), "the evaluation code billed and the complexity the note documents"),
        read("fee_list", ["fee_per_unit"], "SELECT c.code, f.fee_per_unit FROM fee_list f JOIN cpt_code c USING (cpt_code_id) WHERE c.code IN (%s, %s)", [kc, rules[0][3].split()[-1]],
             dict(billed_fee=W.fee[kc]), "the fee difference between the two codes", rows=2),
    ]
    trig = f"The note for the visit on {e['encounter_date']} was signed on {e['note_signed_date']}, so documentation is complete"
    return trig, reads, "Coder reviews the suggestion. If accepted, the charge is corrected before the claim reaches A5 Mirror. A code billed higher than documented is also marked a compliance risk. Nothing changes without a named person."


# ------------------------------------------------------------------ A5
def _prerelease_review(R, W, d, cl, rules, refs, outcome):
    e = W.enc[cl["encounter_id"]]
    cv = W.cov.get(cl["coverage_id"]) or {"termination_date": None}
    reads = [
        read("claim", ["payer_id", "encounter_id", "coverage_id", "total_charge"], "SELECT payer_id, encounter_id, coverage_id, total_charge FROM claim WHERE claim_id = %s", [cl["claim_id"]],
             dict(payer=W.payer_code[cl["payer_id"]], total_charge=cl["total_charge"]), "the claim about to be released"),
        read("encounter", ["encounter_date", "authorization_id", "patient_id"], "SELECT encounter_date, authorization_id, patient_id FROM encounter WHERE encounter_id = %s", [cl["encounter_id"]],
             dict(encounter_date=e["encounter_date"], authorization_id=e["authorization_id"]), "the visit behind the claim"),
        read("coverage", ["termination_date"], "SELECT termination_date FROM coverage WHERE coverage_id = %s", [cl["coverage_id"]], dict(termination_date=cv["termination_date"]), "was the policy still active on the visit date"),
    ]
    names = [r_[0] for r_ in rules]
    if "R-AUTH-VISITS" in names:
        au = W.auth[e["authorization_id"]]
        n = sum(1 for x in W.auth_dates[au["authorization_id"]] if x <= e["encounter_date"])
        reads.append(read("authorization", ["units_approved"], "SELECT units_approved FROM \"authorization\" WHERE authorization_id = %s", [au["authorization_id"]], dict(units_approved=au["units_approved"]), "visits approved"))
        reads.append(read("encounter", ["authorization_id", "encounter_date"], "SELECT COUNT(*) AS visit_number FROM encounter WHERE authorization_id = %s AND encounter_date <= %s", [au["authorization_id"], e["encounter_date"]],
                          dict(visit_number=n), "visits already used against the authorization"))
    if "R-UHC-POC-V" in names or "R-AET-XU" in names:
        reads.append(read("payer_rule", ["rule_code", "rule_action", "approval_status", "effective_from", "unit_limit"],
                          "SELECT rule_code, rule_action, approval_status, effective_from, unit_limit FROM payer_rule WHERE payer_id = %s AND is_enabled AND effective_from <= %s", [cl["payer_id"], d],
                          dict(rules=[x[0] for x in rules if x[5] and x[5] not in R.generic.values()]), "approved payer rules in force on this date (learned by A9 Coach)", rows=1))
    if "R-UHC-POC-V" in names:
        vn, poc = R.visit_no(e), R.has_poc(e)
        reads.append(read("encounter", ["patient_id", "encounter_type", "encounter_date"],
                          "SELECT COUNT(*) AS visit_number FROM encounter WHERE patient_id = %s AND encounter_date <= %s AND encounter_date >= "
                          "(SELECT MAX(encounter_date) FROM encounter WHERE patient_id = %s AND encounter_type = 'evaluation' AND encounter_date <= %s)",
                          [e["patient_id"], e["encounter_date"], e["patient_id"], e["encounter_date"]], dict(visit_number=vn), "which visit of the episode this is"))
        reads.append(read("document", ["document_type", "document_date"],
                          "SELECT COUNT(*) AS plan_of_care_on_file FROM document WHERE patient_id = %s AND document_type = 'plan_of_care' AND document_date <= %s "
                          "AND document_date >= (SELECT MAX(encounter_date) FROM encounter WHERE patient_id = %s AND encounter_type = 'evaluation' AND encounter_date <= %s)",
                          [e["patient_id"], e["encounter_date"], e["patient_id"], e["encounter_date"]], dict(plan_of_care_on_file=1 if poc else 0), "is a signed plan of care on file for this episode"))
    if "R-AET-XU" in names:
        lines = W.cd[cl["claim_id"]]
        reads.append(read("claim_details", ["cpt_code_id", "modifier_1_id", "modifier_2_id"],
                          "SELECT k.code, m1.modifier_code AS modifier_1, m2.modifier_code AS modifier_2 FROM claim_details c JOIN cpt_code k USING (cpt_code_id) "
                          "LEFT JOIN modifier m1 ON m1.modifier_id = c.modifier_1_id LEFT JOIN modifier m2 ON m2.modifier_id = c.modifier_2_id WHERE c.claim_id = %s ORDER BY c.line_number",
                          [cl["claim_id"]], dict(lines=[W.cpt[x["cpt_code_id"]] for x in lines]), "the billed lines and their modifiers", rows=len(lines)))
    pattern = {"R-DENTAL-MEDICARE", "R-EM-INJ-MOD25", "R-UNIT-LIMIT", "R-PREVENTIVE-DX", "R-AUTH-REQUIRED"} & set(names)
    if pattern:
        lines = W.cd[cl["claim_id"]]
        reads.append(read("claim_line", ["cpt_code_id", "units", "modifier_1_id", "modifier_2_id"],
                          "SELECT k.code, l.units, m1.modifier_code AS modifier_1, m2.modifier_code AS modifier_2 FROM claim_line l JOIN cpt_code k USING (cpt_code_id) "
                          "LEFT JOIN modifier m1 ON m1.modifier_id = l.modifier_1_id LEFT JOIN modifier m2 ON m2.modifier_id = l.modifier_2_id WHERE l.claim_id = %s ORDER BY l.line_number",
                          [cl["claim_id"]], dict(lines=[f"{W.cpt[x['cpt_code_id']]} x{W.line_units.get(x['claim_detail_id'])}" for x in lines]), "the billed lines, units and modifiers", rows=len(lines)))
    if "R-PREVENTIVE-DX" in pattern:
        reads.append(read("claim", ["principal_diagnosis_code_id"], "SELECT d.icd10_code FROM claim c JOIN diagnosis_code d ON d.diagnosis_code_id = c.principal_diagnosis_code_id WHERE c.claim_id = %s", [cl["claim_id"]],
                          dict(icd10=W.claim_dx.get(cl["claim_id"])), "the claim's principal diagnosis"))
    if "R-UNIT-LIMIT" in pattern:
        reads.append(read("claim", ["patient_id", "service_date_from", "submitted_date"],
                          "SELECT COUNT(*) AS earlier_claims FROM claim_line l JOIN claim c USING (claim_id) WHERE c.patient_id = %s AND l.cpt_code_id IN (SELECT cpt_code_id FROM cpt_code WHERE code IN ('G0444', 'G0136')) "
                          "AND EXTRACT(year FROM l.service_date) = %s AND l.service_date < %s AND c.submitted_date <= %s", [cl["patient_id"], cl["service_date_from"].year, cl["service_date_from"], d],
                          dict(observed=next(r_[2] for r_ in rules if r_[0] == "R-UNIT-LIMIT")), "earlier once-a-year services already billed by this review date (only claims submitted by then count)"))
    if "R-AUTH-REQUIRED" in pattern:
        reads.append(read("authorization", ["authorization_status", "valid_from", "valid_to", "units_approved", "decision_date"],
                          "SELECT authorization_status, valid_from, valid_to, units_approved FROM \"authorization\" WHERE patient_id = %s AND payer_id = %s AND decision_date <= %s AND authorization_status = 'approved' "
                          "AND %s BETWEEN valid_from AND valid_to", [cl["patient_id"], cl["payer_id"], d, cl["service_date_from"]], dict(note="only authorizations decided by the review date"), "authorizations on file that day"))
    trig = f"Claim {cl['claim_number']} reached its release date ({cl['submitted_date']}) and is about to go to the clearinghouse"
    hand = ("Biller gets a review task. In shadow mode the claim is not actually stopped: it goes to A6 Courier as normal and this prediction is scored when the payer answers."
            if outcome == "hold" else "No rule failed, so the claim moves on to A6 Courier for submission.")
    return trig, reads, hand


# ------------------------------------------------------------------ A6
def _rejection_review(R, W, d, src, rules, refs, outcome):
    cl_id, x = src
    cl = W.claim[cl_id]
    reads = [read("claim_status_history", ["event_type", "event_date", "is_rejection", "rejection_reason"],
                  "SELECT event_type, event_date, is_rejection, rejection_reason FROM claim_status_history WHERE claim_id = %s AND is_rejection ORDER BY event_date", [cl_id],
                  dict(event_type=x["event_type"], event_date=x["event_date"], rejection_reason=x["rejection_reason"]), "the clearinghouse's 277CA answer"),
             read("claim", ["total_charge", "claim_number"], "SELECT total_charge, claim_number FROM claim WHERE claim_id = %s", [cl_id], dict(total_charge=cl["total_charge"]), "money waiting on the fix")]
    return f"The clearinghouse rejected claim {cl['claim_number']} on {x['event_date']} (277CA)", reads, "Biller gets a same-day task to correct and resubmit. If the payer then goes quiet, A7 Hunter takes the claim; if the payer denies it, A8 Advocate does."


# ------------------------------------------------------------------ A7
def _claim_follow_up(R, W, d, cl, rules, refs, outcome):
    pay = W.payer[cl["payer_id"]]
    reads = [read("claim_status_history", ["event_type", "event_date"], "SELECT COUNT(*) AS remit_835_events FROM claim_status_history WHERE claim_id = %s AND event_type = 'remit_835' AND event_date <= %s",
                  [cl["claim_id"], d], dict(remit_835_events=0), "has the payer answered with a remittance by today"),
             read("claim", ["submitted_date", "service_date_from", "total_charge"], "SELECT submitted_date, service_date_from, total_charge FROM claim WHERE claim_id = %s", [cl["claim_id"]],
                  dict(submitted_date=cl["submitted_date"], service_date_from=cl["service_date_from"]), "when it was sent and when the visit was"),
             read("payer", ["standard_turnaround_days", "filing_days"], "SELECT standard_turnaround_days, filing_days FROM payer WHERE payer_id = %s", [cl["payer_id"]],
                  dict(standard_turnaround_days=pay["standard_turnaround_days"], filing_days=pay["filing_days"]), "the payer's normal answer time and filing window")]
    return (f"Claim {cl['claim_number']} passed the payer's normal answer time plus 14 days ({cl['submitted_date']} + {pay['standard_turnaround_days']} + 14) with no remittance", reads,
            "AR specialist gets a task to call the payer or resubmit before the filing window closes. If the payer later denies it, A8 Advocate takes over.")


# ------------------------------------------------------------------ A8
def _denial_triage(R, W, d, dn, rules, refs, outcome):
    cr = W.carc[dn["adjustment_reason_id"]]
    reads = [read("denial", ["claim_id", "denial_date", "denied_amount", "adjustment_reason_id", "appeal_deadline"], "SELECT claim_id, denial_date, denied_amount, adjustment_reason_id, appeal_deadline FROM denial WHERE denial_id = %s",
                  [dn["denial_id"]], dict(denied_amount=dn["denied_amount"], appeal_deadline=dn["appeal_deadline"]), "the payer's denial on the 835"),
             read("adjustment_reason", ["carc_code", "reason_class", "owner_role", "is_appealable", "upstream_stage"], "SELECT carc_code, reason_class, owner_role, is_appealable, upstream_stage FROM adjustment_reason WHERE adjustment_reason_id = %s",
                  [dn["adjustment_reason_id"]], dict(carc_code=cr["carc_code"], owner_role=cr["owner_role"], is_appealable=cr["is_appealable"], upstream_stage=cr["upstream_stage"]), "what this reason code means and who owns it")]
    return (f"The 835 for claim {W.claim[dn['claim_id']]['claim_number']} arrived on {dn['denial_date']} with a denial", reads,
            f"Task goes to the {cr['owner_role'].replace('_', ' ')}. The denial is also counted by A9 Coach (10 like it in 60 days proposes a prevention rule), and a corrected claim will pass A5 Mirror again.")


# ------------------------------------------------------------------ A9
def _rule_proposal(R, W, d, src, rules, refs, outcome):
    recent = src["recent"]
    reads = [read("denial", ["payer_id", "adjustment_reason_id", "denial_date", "denied_amount"],
                  "SELECT COUNT(*) AS denials, COALESCE(SUM(denied_amount),0) AS denied_amount FROM denial WHERE payer_id = %s AND adjustment_reason_id = %s AND denial_date <= %s AND denial_date > %s::date - 60",
                  [src["pid"], W.carc_id[src["carc"]], d, d], dict(denials=len(recent), denied_amount=sum(x["denied_amount"] for x in recent)), "how many denials like this the payer sent in 60 days")]
    if src["thr"]:
        reads.append(read("encounter", ["patient_id", "encounter_date"], "SELECT MIN(visit_number) FROM (episode visit number of each denied claim)", [], dict(min_visit_number=src["thr"]),
                          "the earliest visit number among the denials, used as the rule's threshold (computed in the engine from the encounters of each denied claim)", rows=len(recent), runnable=False))
    return (f"Pattern watch: {len(recent)} CARC {src['carc']} denials from {src['pc']} within 60 days reached the threshold of 10", reads,
            "Manager gets a task to approve the proposed rule. Once approved (about 5 business days) A5 Mirror starts holding matching claims before release.")


# ------------------------------------------------------------------ A10
def _payment_audit(R, W, d, src, rules, refs, outcome):
    cl, ln = src
    reads = [read("claim_details", ["allowed_amount", "expected_allowed", "modifier_1_id", "modifier_2_id", "cpt_code_id"],
                  "SELECT allowed_amount, expected_allowed, modifier_1_id, modifier_2_id FROM claim_details WHERE claim_detail_id = %s", [ln["claim_detail_id"]],
                  dict(allowed_amount=ln["allowed_amount"], expected_allowed=ln["expected_allowed"]), "what the payer allowed against the contract rate")]
    return (f"The 835 for claim {cl['claim_number']} posted on {d}; paid lines are compared with the contract rate", reads,
            "Billing lead gets a dispute task. A15 Detective watches whether the same payer and code are short across many claims.")


# ------------------------------------------------------------------ A11
def _remit_reconciliation(R, W, d, p, rules, refs, outcome):
    reads = [read("payment", ["payment_amount", "posted_amount", "unapplied_amount", "payment_date"], "SELECT payment_amount, posted_amount, unapplied_amount, payment_date FROM payment WHERE payment_id = %s", [p["payment_id"]],
                  dict(payment_amount=p["payment_amount"], posted_amount=p["posted_amount"], unapplied_amount=p["unapplied_amount"]), "what the payer paid against what was posted"),
             read("transactions", ["payment_id", "amount"], "SELECT COALESCE(SUM(amount),0) AS posted_in_ledger FROM transactions WHERE payment_id = %s", [p["payment_id"]],
                  dict(posted_in_ledger=0 if p["unapplied_amount"] else p["payment_amount"]), "payments actually posted to the ledger")]
    return (f"Remit {p['payment_id']} was received on {p['payment_date']}; checked the next business day", reads,
            "Payment poster gets a task to post it. Until it is posted A14 Captain's cash forecast and the AR balances are off by this amount.")


# ------------------------------------------------------------------ A12
def _balance_follow_up(R, W, d, a, rules, refs, outcome):
    reads = [read("ar", ["balance", "days_outstanding", "balance_owner"], "SELECT balance, days_outstanding, balance_owner FROM ar WHERE ar_id = %s", [a["ar_id"]],
                  dict(balance=a["balance"], days_outstanding=a["days_outstanding"]), "the patient-owed balance")]
    return f"The patient balance on bill {a['bill_id']} reached 30 days after the visit ({a['service_date']})", reads, "A statement row is written (patient_statement). Biller gets a gentle follow-up task; unpaid balances escalate in dunning level."


# ------------------------------------------------------------------ A13
def _enrollment_review(R, W, d, en, rules, refs, outcome):
    reads = [read("enrollment", ["provider_id", "payer_id", "expires_date"], "SELECT provider_id, payer_id, expires_date FROM enrollment WHERE enrollment_id = %s", [en["enrollment_id"]],
                  dict(expires_date=en["expires_date"]), "when this provider's payer enrolment ends")]
    return f"Enrolment {en['enrollment_id']} reached 60 days before it expires ({en['expires_date']})", reads, "Manager gets a revalidation task. A5 Mirror would start predicting denials if the enrolment lapsed."


# ------------------------------------------------------------------ A15
def _revenue_assurance(R, W, d, src, rules, refs, outcome):
    reads = [read("claim_details", ["allowed_amount", "expected_allowed", "cpt_code_id"],
                  "SELECT SUM(c.allowed_amount) AS paid, SUM(c.expected_allowed) AS contract, COUNT(*) AS lines FROM claim_details c JOIN claim x USING (claim_id) WHERE x.payer_id = %s AND c.cpt_code_id = %s AND c.allowed_amount IS NOT NULL",
                  [src["pid"], src["cid"]], dict(paid=src["got"], contract=src["exp"], lines=src["n"]), "what this payer actually allowed for this code against the contract (60 days, CQ lines adjusted; the engine computes this over claims answered in the window)", runnable=False)]
    return f"Weekly realisation check (Monday {d}): payer and code combinations are scored over the last 60 days", reads, "Billing lead gets a task. A10 Auditor handles single claims; this is the payer-wide pattern."
