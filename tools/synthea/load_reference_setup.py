"""Stage 3: fills the reference, setup and appointment-detail tables of krisnnai_r2 that the Synthea load left empty.

Nothing here comes from Synthea itself. Lookups (modifiers, claim status codes, calendar), setup (staff, settings, identifiers, fee schedule, contracts, rules) are built here and
marked is_inferred / is_synthetic where the model has the flag. Contract rates are inferred from the claim lines already loaded. ndc_code is left empty on purpose: Synthea
carries RxNorm, not NDC, and none of the billable codes in the crosswalk is a drug.

    python tools/synthea/load_reference_setup.py --reset
"""
import datetime as dt
import sys

from r2load import END, NOW, TBL, Loader, connect, h
from crosswalk import FEE

TABLES = ["modifier", "claim_status_code", "calendar", "staff", "practice_settings", "payer_identifier", "provider_identifier", "fee_schedule", "fee_schedule_line",
          "payer_contract", "contract_rate", "payer_rule", "appointment_line", "appointment_slot", "appointment_status_log"]
BOILER = dict(tenant_id="1", load_batch_id="1", is_source_deleted="false", version="1", is_current="true", is_active="true", source="'synthea'", loaded_at=f"'{NOW}'")
START = dt.date(2023, 1, 1)
TODAY = dt.date(2026, 11, 6)


def sql_insert(cur, table, cols, tail):
    """INSERT ... SELECT with the boilerplate columns the table has. cols maps column to a SQL expression."""
    names = {c["name"] for c in TBL[table]["cols"]}
    bad = [k for k in cols if k not in names]
    assert not bad, (table, bad)
    full = {**{k: v for k, v in BOILER.items() if k in names}, **cols}
    cur.execute(f'INSERT INTO "{table}" ({",".join(full)}) SELECT {",".join(full.values())} {tail}')
    return cur.rowcount


def nth_weekday(year, month, weekday, n):
    d = dt.date(year, month, 1)
    d += dt.timedelta(days=(weekday - d.weekday()) % 7)
    return d + dt.timedelta(weeks=n - 1)


def last_weekday(year, month, weekday):
    d = dt.date(year + (month == 12), month % 12 + 1, 1) - dt.timedelta(days=1)
    return d - dt.timedelta(days=(d.weekday() - weekday) % 7)


def holidays(year):
    fixed = {"NEW_YEAR": dt.date(year, 1, 1), "JUNETEENTH": dt.date(year, 6, 19), "INDEPENDENCE": dt.date(year, 7, 4), "VETERANS": dt.date(year, 11, 11), "CHRISTMAS": dt.date(year, 12, 25)}
    out = {}
    for code, d in fixed.items():  # a weekend holiday is observed on the Friday or the Monday
        out[d + dt.timedelta(days=-1 if d.weekday() == 5 else 1 if d.weekday() == 6 else 0)] = code
    out[nth_weekday(year, 1, 0, 3)] = "MLK"
    out[nth_weekday(year, 2, 0, 3)] = "PRESIDENTS"
    out[last_weekday(year, 5, 0)] = "MEMORIAL"
    out[nth_weekday(year, 9, 0, 1)] = "LABOR"
    out[nth_weekday(year, 10, 0, 2)] = "COLUMBUS"
    out[nth_weekday(year, 11, 3, 4)] = "THANKSGIVING"
    return out


# (code, group, affects payment, payment %, label)
MODIFIERS = [("25", "em", False, None, "Significant, separate E/M on the same day"), ("24", "em", False, None, "Unrelated E/M in the post-operative period"),
             ("57", "em", False, None, "E/M that led to the decision for surgery"), ("59", "ncci", False, None, "Distinct procedural service"),
             ("XE", "ncci", False, None, "Separate encounter"), ("XS", "ncci", False, None, "Separate structure"), ("XP", "ncci", False, None, "Separate practitioner"),
             ("XU", "ncci", False, None, "Unusual non-overlapping service"), ("GP", "therapy", False, None, "Service under a physical therapy plan of care"),
             ("GO", "therapy", False, None, "Service under an occupational therapy plan of care"), ("GN", "therapy", False, None, "Service under a speech therapy plan of care"),
             ("KX", "therapy", False, None, "Requirements for the therapy threshold are met"), ("CQ", "assistant", True, 85, "Physical therapist assistant: paid at 85%"),
             ("CO", "assistant", True, 85, "Occupational therapy assistant: paid at 85%"), ("RT", "laterality", False, None, "Right side"), ("LT", "laterality", False, None, "Left side"),
             ("26", "component", True, None, "Professional component"), ("TC", "component", True, None, "Technical component"), ("50", "bilateral", True, 150, "Bilateral procedure"),
             ("51", "multiple", True, 50, "Multiple procedures"), ("76", "repeat", False, None, "Repeat procedure by the same clinician"),
             ("77", "repeat", False, None, "Repeat procedure by another clinician"), ("91", "repeat", False, None, "Repeat clinical lab test"),
             ("95", "telehealth", False, None, "Synchronous telemedicine service"), ("GT", "telehealth", False, None, "Interactive audio and video telecommunications")]
# 277 claim status category codes (labels paraphrased; check against the published list before using them for matching)
STATUS = [("A0", "Acknowledgement: forwarded to another entity", "ack", False), ("A1", "Acknowledgement: receipt", "ack", False),
          ("A2", "Acknowledgement: accepted into the adjudication system", "ack", False), ("A3", "Acknowledgement: returned as unprocessable", "ack", True),
          ("A4", "Acknowledgement: not found", "ack", False), ("A5", "Acknowledgement: split claim", "ack", False),
          ("A6", "Acknowledgement: rejected for missing information", "ack", True), ("A7", "Acknowledgement: rejected for invalid information", "ack", True),
          ("A8", "Acknowledgement: rejected for a relational field in error", "ack", True), ("P0", "Pending: adjudication in progress", "pending", False),
          ("P1", "Pending: in process", "pending", False), ("P2", "Pending: payer review", "pending", False), ("P3", "Pending: provider information requested", "pending", False),
          ("P4", "Pending: patient information requested", "pending", False), ("P5", "Pending: payer administrative or system hold", "pending", False),
          ("F0", "Finalized: adjudication complete", "finalized", False), ("F1", "Finalized: payment", "finalized", False), ("F2", "Finalized: denial", "finalized", False),
          ("F3", "Finalized: revised", "finalized", False), ("F3F", "Finalized: forwarded", "finalized", False), ("F4", "Finalized: no payment forthcoming", "finalized", False),
          ("E0", "Response not possible: error in the submitted request", "error", False), ("D0", "Data reporting only", "info", False)]
STAFF = [("biller_manager", "billing"), ("biller", "billing"), ("biller", "billing"), ("biller", "billing"), ("coder", "coding"), ("coder", "coding"),
         ("denial_analyst", "denials"), ("denial_analyst", "denials"), ("ar_specialist", "ar"), ("ar_specialist", "ar"), ("payment_poster", "billing"),
         ("front_desk", "front_desk"), ("front_desk", "front_desk"), ("front_desk", "front_desk")]
SETTINGS = [("timely_filing_alert_days", "30", "int"), ("small_balance_writeoff_usd", "5.00", "decimal"), ("write_off_limit_usd", "25.00", "decimal"),
            ("appeal_min_amount_usd", "100.00", "decimal"), ("auto_post_payments", "true", "bool"), ("claim_scrub_enabled", "true", "bool"),
            ("statement_cycle_days", "30", "int"), ("first_statement_days_after_adjudication", "7", "int"), ("collections_threshold_days", "120", "int"),
            ("fiscal_year_start_month", "1", "int"), ("default_fee_schedule", "Practice standard fees", "text")]
# payer_rule seeds: (code, family, action, source, source_ref, payer code, cpt, paired cpt, modifier, dx, requirement, unit limit, basis, owner, severity)
EM = ["99211", "99213", "99214", "99203", "99204"]
RULES = []
for e in EM:
    RULES.append((f"NCCI-25-{e}-96372", "ncci_edit", "require_modifier", "cms_ncci", "NCCI procedure-to-procedure edits", None, e, "96372", "25", None, "modifier_25", None, None, "coder", "high"))
for p in ["99395", "99396", "99393"]:
    RULES.append((f"NCCI-25-99213-{p}", "ncci_edit", "require_modifier", "cms_ncci", "Problem visit with a preventive visit", None, "99213", p, "25", None, "modifier_25", None, None, "coder", "high"))
for c, dx in [("99395", "Z0000"), ("99396", "Z0000"), ("99393", "Z00129")]:
    RULES.append((f"DX-{c}-{dx}", "dx_required", "deny_without", "coding_guideline", "Preventive visit needs a routine exam diagnosis", None, c, None, None, dx, "diagnosis", None, None, "coder", "medium"))
for c, n, b in [("96127", 4, "per_day"), ("97110", 4, "per_day"), ("99408", 1, "per_day"), ("90935", 1, "per_day"), ("92250", 1, "per_day"), ("G0136", 1, "per_year"), ("G0444", 1, "per_year")]:
    RULES.append((f"UNITS-{c}", "unit_limit", "cap_units", "payer_policy", "Frequency limit", None, c, None, None, None, "units", n, b, "coder", "medium"))
RULES.append(("MCR-G0444-ANNUAL", "frequency", "deny_over", "cms_ncd", "Annual depression screening", "MEDICARE", "G0444", None, None, None, "frequency", 1, "per_year", "coder", "medium"))


def main():
    reset = "--reset" in sys.argv
    conn = connect()
    cur = conn.cursor()
    cur.execute("SET session_replication_role = replica")
    if reset:
        for t in TABLES:  # DELETE, not TRUNCATE: empty tables elsewhere (patient_estimate_line, ...) hold foreign keys to these
            cur.execute(f'DELETE FROM "{t}"')
    else:
        for t in TABLES:
            cur.execute(f'select count(*) from "{t}"')
            assert cur.fetchone()[0] == 0, f"{t} is not empty; use --reset"
    L = Loader(conn)
    cur.execute("select cpt_code_id, code from cpt_code")
    cpt = {c: i for i, c in cur.fetchall()}
    cur.execute("select diagnosis_code_id, icd10_code from diagnosis_code")
    dx = {c: i for i, c in cur.fetchall()}
    cur.execute("select payer_id, payer_code, payer_type, filing_days, corrected_claim_days, appeal_days from payer order by payer_id")
    payers = cur.fetchall()
    pid = {p[1]: p[0] for p in payers}
    cur.execute("select practice_id from practice")
    practice = cur.fetchone()[0]
    n = {}

    mod = {}
    rows = []
    for code, grp, pays, pct, label in MODIFIERS:
        mod[code] = L.key("modifier")
        rows.append(dict(modifier_id=mod[code], modifier_code=code, modifier_group=grp, affects_payment=pays, payment_adjustment_pct=pct, short_label=label, effective_from=dt.date(2019, 1, 1), effective_to=END))
    n["modifier"] = L.rows("modifier", rows)

    n["claim_status_code"] = L.rows("claim_status_code", [dict(claim_status_code_id=L.key("claim_status_code"), code_set="277_CAT", code=c, short_label=lab, status_group=g, is_rejection=rej,
                                                               effective_from=dt.date(2019, 1, 1), effective_to=END, is_unrecognized=False) for c, lab, g, rej in STATUS])

    rows, hol, bday, d = [], {}, 0, START
    for y in range(2023, 2028):
        hol.update(holidays(y))
    while d <= dt.date(2027, 12, 31):
        biz = d.weekday() < 5 and d not in hol
        bday += biz
        rows.append(dict(calendar_id=L.key("calendar"), practice_id=practice, calendar_date=d, is_business_day=biz, is_holiday=d in hol, holiday_code=hol.get(d), business_day_number=bday))
        d += dt.timedelta(days=1)
    n["calendar"] = L.rows("calendar", rows)

    rows = []
    for i, (role, team) in enumerate(STAFF, 1):
        rows.append(dict(staff_id=L.key("staff"), staff_number=f"STF-{i:03d}", practice_id=practice, staff_role=role, team=team, weekly_hours=40.0, start_date=START))
    n["staff"] = L.rows("staff", rows)

    n["practice_settings"] = L.rows("practice_settings", [dict(practice_settings_id=L.key("practice_settings"), practice_id=practice, setting_key=k, setting_value=v, value_type=t,
                                                               effective_from=START, effective_to=END, set_by_role="admin", approved_by_staff_id=1) for k, v, t in SETTINGS])

    n["payer_identifier"] = L.rows("payer_identifier", [dict(payer_identifier_id=L.key("payer_identifier"), payer_id=p[0], identifier_value=f"KRN-{p[1]}", identifier_type="edi_payer_id",
                                                             clearinghouse_code="SYNTHETIC", effective_from=START, effective_to=END) for p in payers if p[2] != "self_pay"])

    fs = L.key("fee_schedule")
    L.rows("fee_schedule", [dict(fee_schedule_id=fs, practice_id=practice, fee_schedule_name="Practice standard fees", fee_basis="charge", is_default=True, is_inferred=True,
                                 effective_from=START, effective_to=END)])
    cur.execute("select cpt_code_id, code from cpt_code order by cpt_code_id")
    n["fee_schedule"] = 1
    n["fee_schedule_line"] = L.rows("fee_schedule_line", [dict(fee_schedule_line_id=L.key("fee_schedule_line"), fee_schedule_id=fs, cpt_code_id=i, fee_per_unit=FEE[c], effective_from=START,
                                                                is_inferred=True, effective_to=END) for i, c in cur.fetchall()])

    # what each payer pays for a code, from the lines already loaded; a payer's level against Medicare gives the contract percentage
    cur.execute("select p.payer_code, sum(allowed_amount)/nullif(sum(charge_amount),0) from claim_line l join payer p using(payer_id) group by 1")
    ratio = {c: float(r) for c, r in cur.fetchall()}
    rows, contract = [], {}
    for pid_, code, ptype, filing, corrected, appeal in payers:
        if ptype == "self_pay":
            continue
        contract[pid_] = L.key("payer_contract")
        govt = ptype in ("medicare", "medicaid")
        rows.append(dict(payer_contract_id=contract[pid_], practice_id=practice, payer_id=pid_, contract_number=f"{code}-2023", contract_status="active", effective_from=START,
                         effective_to=END if govt else dt.date(2027, 12, 31), filing_days=filing, corrected_claim_days=corrected, appeal_days=appeal, lesser_of_billed=True,
                         default_rate_basis="pct_of_medicare", default_pct_of_medicare=round(ratio[code] / ratio["MEDICARE"] * 100, 2), escalator_pct=None if govt else 2.0,
                         renewal_notice_days=None if govt else 90))
    n["payer_contract"] = L.rows("payer_contract", rows)

    r = []
    for code, grp, act, src, ref, payer, c1, c2, m, d_, req, lim, basis, owner, sev in RULES:
        r.append(dict(payer_rule_id=L.key("payer_rule"), rule_code=code, rule_family=grp, rule_action=act, rule_source_code=src, rule_source_ref=ref, payer_id=pid[payer] if payer else None,
                      practice_id=practice, cpt_code_id=cpt[c1], paired_cpt_code_id=cpt[c2] if c2 else None, modifier_id=mod[m] if m else None, diagnosis_code_id=dx[d_] if d_ else None,
                      requirement_code=req, unit_limit=lim, unit_limit_basis=basis, owner_role=owner, severity=sev, is_enabled=True, is_synthetic=True, approval_status="approved",
                      approved_by_staff_id=1, approved_date=START, last_confirmed_date=TODAY, effective_from=START, effective_to=END))
    for p_, code, ptype, filing, _c, _a in payers:
        if ptype != "self_pay":
            r.append(dict(payer_rule_id=L.key("payer_rule"), rule_code=f"TF-{code}", rule_family="timely_filing", rule_action="deny_if_late", rule_source_code="payer_policy",
                          rule_source_ref=f"{filing} days from the date of service", payer_id=p_, practice_id=practice, requirement_code=f"{filing}d", owner_role="biller", severity="high",
                          is_enabled=True, is_synthetic=True, approval_status="approved", approved_by_staff_id=1, approved_date=START, last_confirmed_date=TODAY, effective_from=START,
                          effective_to=END))
    n["payer_rule"] = L.rows("payer_rule", r)

    # big tables by SQL
    n["provider_identifier"] = sql_insert(cur, "provider_identifier", dict(
        provider_identifier_id="row_number() over (order by x.provider_id, x.k)", provider_id="x.provider_id", identifier_type="x.t", identifier_value="x.v", issuing_state="x.st",
        effective_from="coalesce(x.start_date, date '2019-01-01')", effective_to="date '9999-12-31'", verified_date=f"date '{TODAY}'"),
        "FROM (select provider_id, start_date, 1 k, 'npi' t, npi v, null::char(2) st from provider union all "
        "select provider_id, start_date, 2, 'state_license', 'TX' || lpad(provider_id::text, 7, '0'), 'TX' from provider) x")

    n["contract_rate"] = sql_insert(cur, "contract_rate", dict(
        contract_rate_id="row_number() over (order by g.payer_id, g.cpt_code_id)", practice_id=str(practice), payer_id="g.payer_id", payer_contract_id="pc.payer_contract_id",
        cpt_code_id="g.cpt_code_id", allowed_per_unit="g.rate", effective_from=f"date '{START}'", rate_source="'observed_claims'", is_inferred="true", effective_to="pc.effective_to",
        rate_setting="'in_network'", contract_number="pc.contract_number", rate_basis="'observed_per_unit'", lesser_of_billed="pc.lesser_of_billed",
        confidence="round(least(1.0, g.n / 30.0)::numeric, 4)", sample_size="g.n"),
        "FROM (select payer_id, cpt_code_id, round((sum(allowed_amount) / sum(units))::numeric, 2) rate, count(*) n from claim_line where units > 0 group by 1, 2) g "
        "JOIN payer_contract pc ON pc.payer_id = g.payer_id")

    n["appointment_line"] = sql_insert(cur, "appointment_line", dict(
        appointment_line_id="row_number() over (order by el.encounter_id, el.line_number)", appointment_id="e.appointment_id", line_number="el.line_number", practice_id="el.practice_id",
        patient_id="el.patient_id", payer_id="el.payer_id", provider_id="el.rendering_provider_id", specialty_id="el.specialty_id", planned_cpt_code_id="el.cpt_code_id",
        is_inferred="true", planned_units="el.units", expected_charge="el.expected_charge",
        expected_allowed="round(coalesce(cr.allowed_per_unit * el.units, el.expected_charge)::numeric, 2)", auth_required="'no'", planned_diagnosis_code_id="el.diagnosis_1_id"),
        "FROM encounter_line el JOIN encounter e ON e.encounter_id = el.encounter_id AND e.appointment_id IS NOT NULL "
        "LEFT JOIN contract_rate cr ON cr.payer_id = el.payer_id AND cr.cpt_code_id = el.cpt_code_id")

    n["appointment_slot"] = sql_insert(cur, "appointment_slot", dict(
        appointment_slot_id="a.appointment_id", practice_id="a.practice_id", provider_id="a.provider_id", slot_date="a.appointment_date", start_time="date_trunc('second', a.start_time)::time(0)",
        duration_minutes="case a.appointment_type when 'wellness' then 40 when 'outpatient' then 30 when 'virtual' then 15 else 20 end", slot_status="'used'",
        slot_number="'SL-' || a.appointment_id", facility_id="a.facility_id", specialty_id="p.specialty_id", slot_type="a.appointment_type", appointment_id="a.appointment_id",
        created_date="a.booked_date", is_overbook="false"),
        "FROM appointment a JOIN provider p ON p.provider_id = a.provider_id")

    for k, (frm, to, when, who, chan) in enumerate([
            (None, "scheduled", "(a.booked_date + time '09:00')", "null", "'scheduler'"),
            ("scheduled", "checked_in", "(a.appointment_date + date_trunc('second', a.start_time)::time(0))", "null", "'front_desk'"),
            ("checked_in", "completed", "(a.appointment_date + date_trunc('second', a.start_time)::time(0) + interval '30 minutes')", "null", "'system'")]):
        n["appointment_status_log"] = n.get("appointment_status_log", 0) + sql_insert(cur, "appointment_status_log", dict(
            appointment_status_log_id=f"{k} * (select count(*) from appointment) + row_number() over (order by a.appointment_id) + 1000000000",
            appointment_id="a.appointment_id", from_status="null" if frm is None else f"'{frm}'", to_status=f"'{to}'", status_changed_at=when, change_channel=chan), "FROM appointment a")

    conn.commit()
    for t in TABLES:
        print(f"{t:26s}{n[t]:>10,}")


if __name__ == "__main__":
    main()
