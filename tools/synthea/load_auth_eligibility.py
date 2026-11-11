"""Stage 5: authorizations, referrals and eligibility checks for krisnnai_r2.

Synthea has none of these, so they are generated here, from rules and a hash of the ids (a rerun gives the same result):
- Which payer needs authorization for which code is set in REQUIRED below and also stored as payer_rule rows (family 'authorization').
- Visits for those codes are grouped per patient, payer, code and calendar quarter. About 12% of groups never got an authorization, 3% were denied, the rest are approved;
  of the approved ones 8% have too few units and 5% expire early, so some lines are uncovered.
- encounter_line.auth_required, encounter_line/encounter/claim.authorization_id and the claim's prior_auth_number are filled. A line that needs authorization and is not
  covered by an approved one is what load_denials.py turns into a CARC 197 denial, so run load_denials.py --reset after this stage.
- Referrals for the HMO-style payers (Humana, UnitedHealthcare): about 5% of ambulatory visits.
- One eligibility check per appointment that has a coverage, 1 to 3 days before the visit, with 3% AAA rejections, and benefit rows for the accepted ones.
Copay, deductible and out-of-pocket values are our own assumptions, not payer data.

    python tools/synthea/load_auth_eligibility.py --reset
"""
import sys

from load_denials import U, ins
from r2load import connect

TODAY = "2026-11-06"
# payer code -> codes that need prior authorization
REQUIRED = {"HUMANA": ["90935", "96413", "97110"], "UHC": ["90935", "96413", "95115"], "AETNA": ["90935", "96413"], "CIGNA": ["90935", "96413"], "ANTHEM": ["90935", "96413"],
            "BCBS": ["90935", "96413"], "MEDICAID": ["90935", "96413", "97110"], "DUAL": ["90935", "96413", "97110"]}
HMO = ("HUMANA", "UHC")
TABLES = ["eligibility_benefit", "eligibility_check", "authorization_line", "authorization", "referral"]


def run(cur, sql):
    cur.execute(sql)
    return cur.rowcount


def clean(cur):
    for t in TABLES:
        run(cur, f'DELETE FROM "{t}"')
    run(cur, "DELETE FROM payer_rule WHERE rule_family = 'authorization'")
    run(cur, "UPDATE encounter SET authorization_id = NULL, referral_id = NULL")
    run(cur, "UPDATE encounter_line SET auth_required = NULL, authorization_id = NULL")
    run(cur, "UPDATE appointment_line SET auth_required = 'no', authorization_id = NULL")
    run(cur, "UPDATE appointment SET referral_id = NULL")
    run(cur, "UPDATE claim SET authorization_id = NULL, prior_auth_number = NULL, referral_id = NULL, referral_number = NULL")


def main():
    reset = "--reset" in sys.argv
    conn = connect()
    cur = conn.cursor()
    cur.execute("SET session_replication_role = replica")
    if reset:
        clean(cur)
    else:
        for t in TABLES:
            cur.execute(f'select count(*) from "{t}"')
            assert cur.fetchone()[0] == 0, f"{t} is not empty; use --reset"
    n = {}

    # the rules, as data
    cur.execute("select coalesce(max(payer_rule_id), 0) from payer_rule")
    base = cur.fetchone()[0]
    values = ",".join(f"('{p}','{c}')" for p, cs in REQUIRED.items() for c in cs)
    ins(cur, "payer_rule", dict(
        payer_rule_id=f"{base} + row_number() over (order by r.payer_code, r.code)", rule_code="'AUTH-' || r.payer_code || '-' || r.code", rule_family="'authorization'", rule_action="'require_auth'",
        rule_source_code="'payer_policy'", rule_source_ref="'Prior authorization list'", payer_id="p.payer_id", practice_id="1", cpt_code_id="k.cpt_code_id", requirement_code="'prior_auth'",
        owner_role="'front_desk'", severity="'high'", is_enabled="true", is_synthetic="true", approval_status="'approved'", approved_by_staff_id="1", approved_date="date '2023-01-01'",
        last_confirmed_date=f"date '{TODAY}'", effective_from="date '2023-01-01'", effective_to="date '9999-12-31'"),
        f"FROM (VALUES {values}) r(payer_code, code) JOIN payer p ON p.payer_code = r.payer_code JOIN cpt_code k ON k.code = r.code")

    # visit lines that need an authorization, grouped into authorization windows
    cur.execute(f"""
        CREATE TEMP TABLE need0 AS
        SELECT el.encounter_line_id, el.encounter_id, el.patient_id, el.payer_id, p.payer_code, el.cpt_code_id, el.units, el.service_date, e.coverage_id, e.rendering_provider_id prov,
               e.principal_diagnosis_code_id dx, e.facility_id, e.place_of_service_id pos,
               extract(year from el.service_date)::int * 10 + extract(quarter from el.service_date)::int q
        FROM encounter_line el JOIN encounter e ON e.encounter_id = el.encounter_id JOIN payer p ON p.payer_id = el.payer_id JOIN cpt_code k ON k.cpt_code_id = el.cpt_code_id
        JOIN (VALUES {values}) r(payer_code, code) ON r.payer_code = p.payer_code AND r.code = k.code""")
    cur.execute("""
        CREATE TEMP TABLE grp0 AS
        SELECT row_number() over (order by patient_id, payer_id, cpt_code_id, q) gid, patient_id, payer_id, cpt_code_id, q, min(service_date) d0, max(service_date) d1, sum(units) units,
               (array_agg(coverage_id order by service_date, encounter_line_id))[1] coverage_id, (array_agg(prov order by service_date, encounter_line_id))[1] prov,
               (array_agg(dx order by service_date, encounter_line_id))[1] dx, (array_agg(facility_id order by service_date, encounter_line_id))[1] facility_id,
               (array_agg(pos order by service_date, encounter_line_id))[1] pos
        FROM need0 GROUP BY patient_id, payer_id, cpt_code_id, q""")
    cur.execute(f"""
        CREATE TEMP TABLE grp AS
        SELECT g.*, s.status, s.flavor,
               CASE WHEN s.status <> 'none' THEN row_number() over (partition by s.status <> 'none' order by g.gid) END authid,
               g.d0 - 1 - floor({U('g.gid', 'v')} * 5)::int valid_from_raw
        FROM grp0 g JOIN LATERAL (SELECT CASE WHEN {U('g.gid', 'auth')} < .12 THEN 'none' WHEN {U('g.gid', 'auth')} < .15 THEN 'denied' ELSE 'approved' END status,
                                        CASE WHEN {U('g.gid', 'flav')} < .08 THEN 'short' WHEN {U('g.gid', 'flav')} < .13 THEN 'expired' ELSE 'full' END flavor) s ON true""")
    cur.execute("""
        CREATE TEMP TABLE cov AS
        SELECT n.encounter_line_id, n.encounter_id, g.gid, g.authid, g.status,
               g.valid_from_raw valid_from, g.valid_from_raw + CASE WHEN g.flavor = 'expired' THEN 45 ELSE 100 END valid_to,
               CASE WHEN g.flavor = 'short' THEN ceil(g.units * .6) ELSE g.units END units_approved, n.units, n.service_date,
               sum(n.units) over (partition by g.gid order by n.service_date, n.encounter_line_id) cum
        FROM need0 n JOIN grp g ON g.patient_id = n.patient_id AND g.payer_id = n.payer_id AND g.cpt_code_id = n.cpt_code_id AND g.q = n.q""")
    cur.execute("ALTER TABLE cov ADD COLUMN covered boolean")
    cur.execute("UPDATE cov SET covered = (status = 'approved' AND service_date BETWEEN valid_from AND valid_to AND cum <= units_approved)")

    n["authorization"] = ins(cur, "authorization", dict(
        authorization_id="g.authid", authorization_number="'AUTH-' || p.payer_code || '-' || lpad(g.authid::text, 7, '0')", patient_id="g.patient_id", payer_id="g.payer_id", practice_id="1",
        authorization_status="g.status", coverage_id="g.coverage_id", primary_cpt_code_id="g.cpt_code_id", units_requested="g.units",
        units_approved="case when g.status = 'approved' then case when g.flavor = 'short' then ceil(g.units * .6) else g.units end else 0 end", units_used="coalesce(u.used, 0)",
        valid_from="case when g.status = 'approved' then g.valid_from_raw end", valid_to="case when g.status = 'approved' then g.valid_from_raw + case when g.flavor = 'expired' then 45 else 100 end end",
        request_date="g.valid_from_raw - 2 - floor(" + U('g.gid', 'r') + " * 6)::int", decision_date="g.valid_from_raw - 2 - floor(" + U('g.gid', 'r') + " * 6)::int + 1 + floor(" + U('g.gid', 'd') + " * 3)::int",
        authorization_type="'prior_auth'", requesting_provider_id="g.prov", rendering_provider_id="g.prov", urgency="'routine'",
        request_channel="case when " + U('g.gid', 'ch') + " < .6 then 'portal' when " + U('g.gid', 'ch') + " < .85 then 'fax' else 'phone' end",
        decision_reason_code="case when g.status = 'denied' then 'not_medically_nec' end", diagnosis_code_id="g.dx", facility_id="g.facility_id", place_of_service_id="g.pos"),
        "FROM grp g JOIN payer p ON p.payer_id = g.payer_id LEFT JOIN (select gid, sum(units) used from cov where covered group by 1) u ON u.gid = g.gid WHERE g.status <> 'none'")
    n["authorization_line"] = ins(cur, "authorization_line", dict(
        authorization_line_id="a.authorization_id", authorization_id="a.authorization_id", line_number="1", cpt_code_id="a.primary_cpt_code_id", unit_type="'units'",
        units_requested="a.units_requested", units_approved="a.units_approved", units_used="a.units_used", line_status="a.authorization_status", valid_from="a.valid_from", valid_to="a.valid_to",
        practice_id="a.practice_id", patient_id="a.patient_id", payer_id="a.payer_id"), 'FROM "authorization" a')

    # links
    run(cur, "UPDATE encounter_line SET auth_required = 'no'")
    run(cur, "UPDATE encounter_line el SET auth_required = 'yes' FROM need0 n WHERE n.encounter_line_id = el.encounter_line_id")
    run(cur, "UPDATE encounter_line el SET authorization_id = c.authid FROM cov c WHERE c.encounter_line_id = el.encounter_line_id AND c.covered")
    run(cur, "UPDATE encounter e SET authorization_id = x.a FROM (select encounter_id, min(authid) a from cov where covered group by 1) x WHERE x.encounter_id = e.encounter_id")
    run(cur, """UPDATE appointment_line al SET auth_required = el.auth_required, authorization_id = el.authorization_id FROM encounter_line el JOIN encounter e ON e.encounter_id = el.encounter_id
                WHERE e.appointment_id = al.appointment_id AND el.line_number = al.line_number""")

    # referrals for the HMO-style payers
    n["referral"] = ins(cur, "referral", dict(
        referral_id="row_number() over (order by e.encounter_id)", referral_number="'REF-' || lpad(e.encounter_id::text, 8, '0')", practice_id="e.practice_id", patient_id="e.patient_id",
        coverage_id="e.coverage_id", payer_id="e.payer_id",
        referring_provider_id="case when cv.pcp_provider_id is not null and cv.pcp_provider_id <> e.rendering_provider_id then cv.pcp_provider_id else (e.rendering_provider_id % 4483) + 1 end",
        referred_to_provider_id="e.rendering_provider_id", specialty_id="e.specialty_id", referral_status="'used'", request_date="e.encounter_date - 14", received_date="e.encounter_date - 12",
        valid_from="e.encounter_date - 7", valid_to="e.encounter_date + 83", visits_allowed="3", visits_used="1", diagnosis_code_id="e.principal_diagnosis_code_id"),
        f"FROM encounter e JOIN payer p ON p.payer_id = e.payer_id LEFT JOIN coverage cv ON cv.coverage_id = e.coverage_id WHERE p.payer_code IN {HMO} AND e.encounter_type = 'ambulatory' AND {U('e.encounter_id', 'ref')} < .05")
    run(cur, "UPDATE encounter e SET referral_id = r.referral_id FROM referral r WHERE r.referral_number = 'REF-' || lpad(e.encounter_id::text, 8, '0')")
    run(cur, "UPDATE appointment a SET referral_id = e.referral_id FROM encounter e WHERE e.appointment_id = a.appointment_id AND e.referral_id IS NOT NULL")
    run(cur, """UPDATE claim c SET authorization_id = e.authorization_id, referral_id = e.referral_id, prior_auth_number = au.authorization_number, referral_number = r.referral_number
                FROM encounter e LEFT JOIN "authorization" au ON au.authorization_id = e.authorization_id LEFT JOIN referral r ON r.referral_id = e.referral_id
                WHERE e.encounter_id = c.encounter_id AND (e.authorization_id IS NOT NULL OR e.referral_id IS NOT NULL)""")

    # eligibility checks and benefits
    n["eligibility_check"] = ins(cur, "eligibility_check", dict(
        eligibility_check_id="a.appointment_id", trace_number="'ELG' || lpad(a.appointment_id::text, 9, '0')", check_sequence="1", appointment_id="a.appointment_id", coverage_id="a.coverage_id",
        patient_id="a.patient_id", payer_id="a.payer_id", practice_id="a.practice_id", is_secondary="false", check_date="a.appointment_date - 1 - floor(" + U('a.appointment_id', 'e1') + " * 3)::int",
        check_ts="(a.appointment_date - 1 - floor(" + U('a.appointment_id', 'e1') + " * 3)::int)::timestamp + time '08:30'", service_date="a.appointment_date", service_type_code="'30'",
        is_aaa_reject=U('a.appointment_id', 'e2') + " < .03", aaa_reason_code="case when " + U('a.appointment_id', 'e2') + " < .015 then '72' when " + U('a.appointment_id', 'e2') + " < .03 then '75' end",
        plan_begin_date="cv.effective_date", plan_end_date="nullif(cv.termination_date, date '9999-12-31')",
        copay_amount="coalesce(cv.copay_amount, case p.payer_type when 'commercial' then 25 else 0 end)",
        coinsurance_pct="coalesce(cv.coinsurance_pct, case p.payer_type when 'medicaid' then 0 else .20 end)", coverage_level="'individual'", network_indicator="'Y'",
        deductible_remaining="coalesce(cv.deductible_remaining, round((case p.payer_type when 'commercial' then 1500 when 'medicare' then 240 else 0 end) * " + U('a.appointment_id', 'e3') + ", 2))",
        deductible_total="case p.payer_type when 'commercial' then 1500 when 'medicare' then 240 else 0 end", oop_max="case p.payer_type when 'commercial' then 6000 end",
        oop_remaining="case p.payer_type when 'commercial' then round(6000 * " + U('a.appointment_id', 'e4') + ", 2) end",
        auth_required_hint="exists (select 1 from appointment_line al where al.appointment_id = a.appointment_id and al.auth_required = 'yes')"),
        "FROM appointment a JOIN coverage cv ON cv.coverage_id = a.coverage_id JOIN payer p ON p.payer_id = a.payer_id")
    n["eligibility_benefit"] = ins(cur, "eligibility_benefit", dict(
        eligibility_benefit_id="(c.eligibility_check_id - 1) * 5 + s.i", eligibility_check_id="c.eligibility_check_id", benefit_sequence="s.i",
        eligibility_code="case s.i when 1 then '1' when 2 then 'B' when 3 then 'A' when 4 then 'C' else 'G' end",
        coverage_level="'individual'", service_type_code="case s.i when 2 then '98' else '30' end",
        insurance_type_code="case p.payer_type when 'medicare' then 'MA' when 'medicaid' then 'MC' else 'CI' end", plan_description="coalesce(cv.plan_name, 'Plan ' || p.payer_code)",
        time_period_code="case s.i when 2 then '27' when 4 then '29' when 5 then '29' end", benefit_amount="case s.i when 2 then c.copay_amount when 4 then c.deductible_remaining when 5 then c.oop_remaining end",
        benefit_pct="case s.i when 3 then c.coinsurance_pct end", auth_required="case when c.auth_required_hint then 'yes' else 'no' end", network_indicator="'Y'", patient_id="c.patient_id",
        payer_id="c.payer_id", practice_id="c.practice_id"),
        "FROM eligibility_check c JOIN payer p ON p.payer_id = c.payer_id JOIN coverage cv ON cv.coverage_id = c.coverage_id CROSS JOIN generate_series(1, 5) s(i) "
        "WHERE NOT c.is_aaa_reject AND (s.i < 5 OR c.oop_max IS NOT NULL)")
    conn.commit()

    for t in ["authorization", "authorization_line", "referral", "eligibility_check", "eligibility_benefit"]:
        print(f"{t:24s}{n[t]:>10,}")
    cur.execute("select authorization_status, count(*), sum(units_requested), sum(units_approved), sum(units_used) from \"authorization\" group by 1 order by 1")
    print("authorizations by status:", cur.fetchall())
    cur.execute("select auth_required, count(*), count(authorization_id) from encounter_line group by 1 order by 1")
    print("lines (auth_required, lines, with authorization):", cur.fetchall())


if __name__ == "__main__":
    main()
