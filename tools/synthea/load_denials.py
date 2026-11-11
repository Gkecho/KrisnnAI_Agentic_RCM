"""Stage 4: the denial layer on top of the Synthea claims in krisnnai_r2.

Takes the settled (paid) claim lines and turns some of them into denials with CARC/RARC reasons, then builds what a payer sends back: payments, remittance per claim, bank deposits,
claim status history, and appeals with their outcomes. Denied money is rewritten in the claim lines, claim, bill and ledger so every tie-out still holds.

Which line is denied is decided by rules over the data (Medicare dental, E/M with an injection and no modifier 25, unit and frequency limits, preventive visit without a routine
exam diagnosis) plus a small random mix, all from a hash of the line id, so a rerun gives the same result. Nothing is written off (hard rule 4): unappealed denials stay open.
Authorization denials (CARC 197) come from load_auth_eligibility.py: a line that needs authorization and has none is denied; timely-filing denials are not generated because no claim in the data was filed late.

Before it changes anything it copies claim, claim_line, ledger_entry, bill and bill_line into the schema backup_pre_denial. `--reset` restores from that copy first, so the stage
can be rerun without redoing stage 2.

    python tools/synthea/load_denials.py --reset
"""
import datetime as dt
import sys

from r2load import END, NOW, TBL, Loader, connect

TODAY = "2026-11-06"
BACKUP = "backup_pre_denial"
MUTATED = ["claim", "claim_line", "ledger_entry", "bill", "bill_line"]
BUILT = ["adjustment_reason", "remark_code", "denial", "denial_reason", "appeal", "payment", "payment_adjustment", "remittance_claim", "bank_deposit", "claim_status_history"]
BOILER = dict(tenant_id="1", load_batch_id="1", is_source_deleted="false", version="1", is_current="true", is_active="true", source="'synthea'", loaded_at=f"'{NOW}'")


def U(expr, salt):
    """Repeatable pseudo-random number in [0, 1) from a hash of expr."""
    return f"(('x' || substr(md5(({expr})::text || '{salt}'), 1, 7))::bit(28)::int / 268435456.0)"


def ins(cur, table, cols, tail):
    """INSERT ... SELECT with the boilerplate columns the table has; checks that every mandatory column is given."""
    names = {c["name"] for c in TBL[table]["cols"]}
    bad = [k for k in cols if k not in names]
    assert not bad, (table, bad)
    full = {**{k: v for k, v in BOILER.items() if k in names}, **cols}
    missing = [c["name"] for c in TBL[table]["cols"] if c["priority"] == "Mandatory" and c["name"] not in full]
    assert not missing, (table, "mandatory columns not filled", missing)
    cur.execute(f'INSERT INTO "{table}" ({",".join(full)}) SELECT {",".join(full.values())} {tail}')
    return cur.rowcount


# (carc, class, label, category, action, owner, upstream stage, appealable, technical, preventable, group)
CARC = [("1", "patient_responsibility", "Deductible amount", "patient_resp", "bill_patient", "biller", "payer", False, False, False, "PR"),
        ("2", "patient_responsibility", "Coinsurance amount", "patient_resp", "bill_patient", "biller", "payer", False, False, False, "PR"),
        ("3", "patient_responsibility", "Co-payment amount", "patient_resp", "bill_patient", "biller", "payer", False, False, False, "PR"),
        ("45", "contractual", "Charge exceeds the fee schedule or contracted amount", "contractual", "write_down", "biller", "contract", False, False, False, "CO"),
        ("4", "denial", "Procedure code inconsistent with the modifier, or modifier missing", "coding", "correct_and_appeal", "coder", "coding", True, True, True, "CO"),
        ("11", "denial", "Diagnosis inconsistent with the procedure", "coding", "correct_and_appeal", "coder", "coding", True, True, True, "CO"),
        ("16", "denial", "Claim lacks information needed for adjudication", "missing_info", "correct_and_resubmit", "biller", "charge_entry", True, True, True, "CO"),
        ("18", "denial", "Exact duplicate claim or service", "duplicate", "verify_no_action", "biller", "charge_entry", False, False, True, "CO"),
        ("27", "denial", "Expenses incurred after coverage terminated", "eligibility", "bill_patient_or_other", "front_desk", "eligibility", False, False, True, "CO"),
        ("29", "denial", "Time limit for filing has expired", "timely_filing", "appeal_with_proof", "biller", "submission", True, False, True, "CO"),
        ("50", "denial", "Not deemed a medical necessity by the payer", "medical_necessity", "appeal_with_notes", "clinician", "clinical_doc", True, False, False, "CO"),
        ("96", "denial", "Non-covered charge(s)", "non_covered", "bill_patient_if_waiver", "biller", "coverage", False, False, False, "CO"),
        ("97", "denial", "Benefit included in the payment for another service", "bundling", "correct_and_appeal", "coder", "coding", True, True, True, "CO"),
        ("109", "denial", "Claim not covered by this payer or contractor", "wrong_payer", "rebill_correct_payer", "front_desk", "eligibility", False, False, True, "CO"),
        ("119", "denial", "Benefit maximum for this period reached", "benefit_limit", "bill_patient", "biller", "coverage", False, False, False, "CO"),
        ("151", "denial", "Information submitted does not support this many services", "frequency", "appeal_with_notes", "coder", "coding", True, False, True, "CO"),
        ("197", "denial", "Precertification or authorization absent", "authorization", "obtain_auth_and_appeal", "front_desk", "authorization", True, False, True, "CO")]
# RARC labels are paraphrased; check them against the published list before using them for matching
RARC = [("N425", "Statutory exclusion", "informational", "bill_patient_if_waiver", "96"), ("N362", "Number of days or units exceeds the acceptable maximum", "informational", "appeal_with_notes", "151"),
        ("M86", "Payment already made for the same or a similar procedure in the time frame", "informational", "appeal_with_notes", "151"),
        ("MA130", "Claim contains incomplete or invalid information", "alert", "correct_and_resubmit", "16"), ("N522", "Duplicate of a claim already processed", "informational", "verify_no_action", "18"),
        ("M80", "Not covered when performed on the same date as another service", "informational", "correct_and_appeal", "97"),
        ("N19", "Procedure code incidental to the primary procedure", "informational", "correct_and_appeal", "97")]


def restore_or_backup(cur, reset):
    cur.execute("select to_regclass(%s)", (f"{BACKUP}.claim",))
    have = cur.fetchone()[0] is not None
    if not have:
        cur.execute(f"select count(*) from denial")
        assert cur.fetchone()[0] == 0, "denial has rows but there is no backup; cannot restore"
        cur.execute(f"CREATE SCHEMA IF NOT EXISTS {BACKUP}")
        for t in MUTATED:
            cur.execute(f'CREATE TABLE {BACKUP}."{t}" AS SELECT * FROM "{t}"')
        print("backup written to schema", BACKUP)
        return
    assert reset, f"{BACKUP} exists, so the stage has run before; use --reset to restore and rerun"
    for t in BUILT:
        cur.execute(f'DELETE FROM "{t}"')
    for t in MUTATED:
        cur.execute(f'DELETE FROM "{t}"')
        cur.execute(f'INSERT INTO "{t}" SELECT * FROM {BACKUP}."{t}"')
    print("restored", ", ".join(MUTATED), "from", BACKUP)


def relink(cur):
    """The restore puts back claim rows from before the authorization stage; this puts the authorization and referral links (set from the encounter) back."""
    cur.execute('''UPDATE claim c SET authorization_id = e.authorization_id, referral_id = e.referral_id, prior_auth_number = au.authorization_number, referral_number = r.referral_number
                   FROM encounter e LEFT JOIN "authorization" au ON au.authorization_id = e.authorization_id LEFT JOIN referral r ON r.referral_id = e.referral_id
                   WHERE e.encounter_id = c.encounter_id AND (e.authorization_id IS NOT NULL OR e.referral_id IS NOT NULL)''')


def build_denials(cur):
    """Temp tables: cand (settled lines), den (the denied ones with reason, dates, appeal path)."""
    cur.execute(f"""
        CREATE TEMP TABLE cand AS
        SELECT l.claim_line_id, l.claim_id, l.bill_line_id, l.payer_id, l.patient_id, l.practice_id, l.cpt_code_id, k.code cpt, k.code_type, l.units, l.charge_amount, l.allowed_amount,
               l.service_date, l.specialty_id, l.rendering_provider_id, l.modifier_1_id, el.auth_required, el.authorization_id auth_id, c.principal_diagnosis_code_id dx, c.encounter_id, p.payer_code, p.appeal_days, pay.pdate,
               row_number() over (partition by l.patient_id, extract(year from l.service_date), k.code order by l.service_date, l.claim_line_id) yr_rn,
               exists (select 1 from claim_line i join claim ic using (claim_id) join cpt_code ik on ik.cpt_code_id = i.cpt_code_id
                       where ic.encounter_id = c.encounter_id and ik.code in ('96372', '95115')) has_injection
        FROM claim_line l JOIN claim c USING (claim_id) JOIN cpt_code k ON k.cpt_code_id = l.cpt_code_id JOIN payer p ON p.payer_id = l.payer_id
        LEFT JOIN bill_line bl ON bl.bill_line_id = l.bill_line_id LEFT JOIN encounter_line el ON el.encounter_line_id = bl.encounter_line_id
        JOIN (select claim_line_id, min(transaction_date) pdate from ledger_entry where transaction_type = 'payment' and responsible_party = 'payer' group by 1) pay
          ON pay.claim_line_id = l.claim_line_id
        WHERE l.line_status = 'paid'""")
    cur.execute("select diagnosis_code_id from diagnosis_code where icd10_code in ('Z0000', 'Z00129')")
    routine = ",".join(str(r[0]) for r in cur.fetchall())
    cur.execute(f"""
        CREATE TEMP TABLE rsn AS
        SELECT cand.*,
          CASE WHEN payer_code = 'MEDICARE' AND code_type = 'CDT' THEN '96'
               WHEN has_injection AND cpt IN ('99211','99213','99214','99203','99204') AND modifier_1_id IS NULL THEN '4'
               WHEN (cpt = '96127' AND units > 4) OR (cpt = '97110' AND units > 4) OR (cpt = '99408' AND units > 1) THEN '151'
               WHEN cpt IN ('G0444', 'G0136') AND yr_rn > 1 AND (cpt = 'G0136' OR payer_code = 'MEDICARE') THEN '151F'
               WHEN cpt IN ('99395','99396','99393') AND dx NOT IN ({routine}) THEN '11'
               WHEN auth_required = 'yes' AND auth_id IS NULL THEN '197'
          END rule,
          {U('claim_line_id', 'a')} u1, {U('claim_line_id', 'b')} u2, {U('claim_line_id', 'c')} u3
        FROM cand""")
    cur.execute(f"""
        CREATE TEMP TABLE pick AS
        SELECT r.*,
          CASE WHEN rule IS NOT NULL THEN (u1 < CASE rule WHEN '96' THEN .5 WHEN '4' THEN CASE WHEN payer_code = 'UHC' THEN .8 ELSE .5 END WHEN '151' THEN .25 WHEN '151F' THEN .25 WHEN '197' THEN .9 ELSE .2 END)
               ELSE (u1 < .015 * CASE payer_code WHEN 'UHC' THEN 1.6 WHEN 'HUMANA' THEN 1.4 ELSE 1 END) END is_denied,
          COALESCE(replace(rule, 'F', ''), CASE WHEN u3 < .25 THEN '16' WHEN u3 < .40 THEN '18' WHEN u3 < .65 THEN '50' WHEN u3 < .75 THEN '11' WHEN u3 < .85 THEN '109' ELSE '27' END) carc,
          CASE WHEN rule = '96' THEN 'N425' WHEN rule = '151' THEN 'N362' WHEN rule = '151F' THEN 'M86'
               WHEN rule IS NULL AND u3 < .25 THEN 'MA130' WHEN rule IS NULL AND u3 >= .25 AND u3 < .40 THEN 'N522' END rarc
        FROM rsn r""")
    cur.execute(f"""
        CREATE TEMP TABLE den AS
        SELECT row_number() over (order by p.claim_line_id) denial_id, p.*, ar.adjustment_reason_id, ar.reason_category, ar.is_appealable, ar.is_technical, ar.is_preventable_default, ar.owner_role,
               ar.upstream_stage, ar.suggested_action, rc.remark_code_id,
               ar.is_appealable AND {U('p.claim_line_id', 'd')} < .55 AS wants_appeal,
               p.pdate + 14 + floor({U('p.claim_line_id', 'e')} * 31)::int AS appeal_submit,
               {U('p.claim_line_id', 'f')} u_dec, {U('p.claim_line_id', 'g')} u_over
        FROM pick p JOIN adjustment_reason ar ON ar.carc_code = p.carc LEFT JOIN remark_code rc ON rc.rarc_code = p.rarc
        WHERE p.is_denied""")
    cur.execute(f"""
        CREATE TEMP TABLE den2 AS
        SELECT d.*, (d.wants_appeal AND d.appeal_submit <= date '{TODAY}') appealed,
               d.appeal_submit + 30 + floor(d.u_dec * 31)::int decision_date_raw
        FROM den d""")
    cur.execute(f"""
        CREATE TEMP TABLE den3 AS
        SELECT d.*, (d.appealed AND d.decision_date_raw <= date '{TODAY}') decided,
               CASE carc WHEN '4' THEN .7 WHEN '11' THEN .6 WHEN '16' THEN .8 WHEN '50' THEN .5 WHEN '197' THEN .45 ELSE .35 END p_over
        FROM den2 d""")
    cur.execute("""
        CREATE TEMP TABLE denf AS
        SELECT d.*, (d.decided AND d.u_over < d.p_over) overturned,
               CASE WHEN NOT d.is_appealable THEN 'non_appealable' WHEN d.decided AND d.u_over < d.p_over THEN 'overturned' WHEN d.decided THEN 'upheld' WHEN d.appealed THEN 'appealed'
                    WHEN d.pdate + d.appeal_days < date '%s' THEN 'deadline_missed' ELSE 'open' END status
        FROM den3 d""" % TODAY)
    cur.execute("select count(*) from denf")
    return cur.fetchone()[0]


def main():
    reset = "--reset" in sys.argv
    conn = connect()
    cur = conn.cursor()
    cur.execute("SET session_replication_role = replica")
    restore_or_backup(cur, reset)
    relink(cur)
    n = {}

    L = Loader(conn)
    L.rows("adjustment_reason", [dict(adjustment_reason_id=i, carc_code=c, effective_from=dt.date(2019, 1, 1), effective_to=END, reason_class=cl, short_label=lab[:60], reason_category=cat,
                                       suggested_action=act, owner_role=own, upstream_stage=up, is_appealable=ap, is_technical=te, is_preventable_default=pre, typical_group=g, is_unrecognized=False)
                                  for i, (c, cl, lab, cat, act, own, up, ap, te, pre, g) in enumerate(CARC, 1)])
    L.rows("remark_code", [dict(remark_code_id=i, rarc_code=c, effective_from=dt.date(2019, 1, 1), effective_to=END, code_qualifier="RARC", short_label=lab[:60], remark_type=t, suggests_action=a,
                                related_reason_code=r, is_unrecognized=False) for i, (c, lab, t, a, r) in enumerate(RARC, 1)])
    n["adjustment_reason"], n["remark_code"] = len(CARC), len(RARC)
    cur.execute("UPDATE ledger_entry SET adjustment_reason_id = (select adjustment_reason_id from adjustment_reason where carc_code = '45') WHERE transaction_type = 'adjustment' AND transaction_subtype = 'contractual'")

    total = build_denials(cur)
    print(f"{total:,} denied lines out of the settled lines")

    n["denial"] = ins(cur, "denial", dict(
        denial_id="d.denial_id", claim_id="d.claim_id", claim_line_id="d.claim_line_id", practice_id="d.practice_id", patient_id="d.patient_id", payer_id="d.payer_id", denial_date="d.pdate",
        denied_amount="d.charge_amount", adjustment_reason_id="d.adjustment_reason_id", denial_status="d.status", bill_line_id="d.bill_line_id", group_code="'CO'", reason_category="d.reason_category",
        clock_start_date="d.pdate", appeal_deadline="d.pdate + d.appeal_days", root_cause="d.reason_category", upstream_stage="d.upstream_stage", is_preventable="d.is_preventable_default",
        is_technical="d.is_technical", owner_role="d.owner_role",
        resolved_date="case when d.decided then d.decision_date_raw end",
        outcome="case d.status when 'overturned' then 'overturned' when 'upheld' then 'upheld' when 'deadline_missed' then 'expired' when 'non_appealable' then 'denied_final' end",
        recovered_amount="case when d.overturned then d.allowed_amount else 0 end",
        is_repeat="exists (select 1 from den p2 where p2.payer_id = d.payer_id and p2.cpt_code_id = d.cpt_code_id and p2.claim_line_id < d.claim_line_id)",
        denial_count_on_line="1", cpt_code_id="d.cpt_code_id", provider_id="d.rendering_provider_id", specialty_id="d.specialty_id", is_claim_level="false", units_denied="d.units"), "FROM denf d")

    n["denial_reason"] = ins(cur, "denial_reason", dict(
        denial_reason_id="d.denial_id * 2 - 1", denial_id="d.denial_id", detail_seq="1", detail_type="'CARC'", adjustment_reason_id="d.adjustment_reason_id", group_code="'CO'",
        reason_amount="d.charge_amount", is_amount_allocated="true", reason_units="d.units", is_primary="true", reason_category="d.reason_category", is_appealable="d.is_appealable",
        suggested_action="d.suggested_action", denial_date="d.pdate", practice_id="d.practice_id", payer_id="d.payer_id", cpt_code_id="d.cpt_code_id", claim_line_id="d.claim_line_id",
        provider_id="d.rendering_provider_id", specialty_id="d.specialty_id", patient_id="d.patient_id", payer_reason_code="d.carc"), "FROM denf d")
    n["denial_reason"] += ins(cur, "denial_reason", dict(
        denial_reason_id="d.denial_id * 2", denial_id="d.denial_id", detail_seq="2", detail_type="'RARC'", remark_code_id="d.remark_code_id", is_primary="false",
        reason_category="d.reason_category", is_appealable="d.is_appealable", suggested_action="d.suggested_action", denial_date="d.pdate", practice_id="d.practice_id", payer_id="d.payer_id",
        cpt_code_id="d.cpt_code_id", claim_line_id="d.claim_line_id", provider_id="d.rendering_provider_id", specialty_id="d.specialty_id", patient_id="d.patient_id",
        remark_qualifier="'RARC'", documents_needed="null"), "FROM denf d WHERE d.remark_code_id IS NOT NULL")

    n["appeal"] = ins(cur, "appeal", dict(
        appeal_id="d.denial_id", appeal_number="'APL-' || lpad(d.denial_id::text, 7, '0')", denial_id="d.denial_id", appeal_level="'first'",
        appeal_status="case when d.overturned then 'overturned' when d.decided then 'upheld' else 'pending' end", clock_start_date="d.pdate", deadline_date="d.pdate + d.appeal_days",
        claim_id="d.claim_id", submitted_date="d.appeal_submit", submission_channel="case when d.u_dec < .6 then 'portal' when d.u_dec < .85 then 'fax' else 'mail' end",
        amount_disputed="d.charge_amount", evidence_count="1 + floor(d.u_over * 4)::int", payer_reference="'REF' || lpad(d.denial_id::text, 9, '0')",
        decision_date="case when d.decided then d.decision_date_raw end", payer_decision="case when d.overturned then 'overturned' when d.decided then 'upheld' end",
        is_overturned="d.overturned", recovered_amount="case when d.overturned then d.allowed_amount else 0 end", practice_id="d.practice_id", patient_id="d.patient_id", payer_id="d.payer_id"),
        "FROM denf d WHERE d.appealed")

    # money: the lines that stay denied lose their payment, contractual and patient-share entries; overturned lines keep them, dated at the decision
    cur.execute("""UPDATE claim_line l SET line_status = 'denied', paid_amount = 0, allowed_amount = 0, patient_responsibility = 0, contractual_adjustment = 0, denied_amount = l.charge_amount
                   FROM denf d WHERE l.claim_line_id = d.claim_line_id AND NOT d.overturned""")
    cur.execute("UPDATE claim_line l SET primary_denial_reason_id = d.denial_id * 2 - 1 FROM denf d WHERE l.claim_line_id = d.claim_line_id")
    cur.execute("UPDATE bill_line b SET line_status = 'denied' FROM denf d JOIN claim_line l ON l.claim_line_id = d.claim_line_id WHERE b.bill_line_id = l.bill_line_id AND NOT d.overturned")
    cur.execute("""DELETE FROM ledger_entry e USING denf d WHERE e.claim_line_id = d.claim_line_id AND NOT d.overturned
                   AND ((e.transaction_type = 'payment' AND e.responsible_party = 'payer') OR (e.transaction_type = 'adjustment' AND e.transaction_subtype IN ('contractual', 'patient_responsibility')))""")
    cur.execute("""UPDATE ledger_entry e SET transaction_date = d.decision_date_raw, posted_date = d.decision_date_raw FROM denf d WHERE e.claim_line_id = d.claim_line_id AND d.overturned
                   AND ((e.transaction_type = 'payment' AND e.responsible_party = 'payer') OR (e.transaction_type = 'adjustment' AND e.transaction_subtype IN ('contractual', 'patient_responsibility')))""")
    cur.execute("select coalesce(max(ledger_entry_id), 0) from ledger_entry")
    base = cur.fetchone()[0]
    ins(cur, "ledger_entry", dict(
        ledger_entry_id=f"{base} + row_number() over (order by d.denial_id)", transaction_number=f"'TXN-' || ({base} + row_number() over (order by d.denial_id))", practice_id="d.practice_id",
        patient_id="d.patient_id", bill_line_id="d.bill_line_id", transaction_type="'adjustment'", amount="d.charge_amount", balance_effect="0", transaction_date="d.pdate", responsible_party="'payer'",
        claim_line_id="d.claim_line_id", claim_id="d.claim_id", transaction_subtype="'denial'", posted_date="d.pdate", payer_id="d.payer_id", provider_id="d.rendering_provider_id",
        specialty_id="d.specialty_id", cpt_code_id="d.cpt_code_id", adjustment_reason_id="d.adjustment_reason_id", group_code="'CO'", remark_code_id="d.remark_code_id", posted_by_role="'system'"),
        "FROM denf d")

    # payments: one per payer per day (payments and denials come on the same remittance), one per patient card payment
    cur.execute("""
        CREATE TEMP TABLE pdays AS
        SELECT row_number() over (order by transaction_date, payer_id) payment_id, payer_id, transaction_date d,
               coalesce(sum(amount) filter (where transaction_type = 'payment'), 0) posted, count(distinct claim_id) claims
        FROM ledger_entry WHERE responsible_party = 'payer' AND (transaction_type = 'payment' OR transaction_subtype = 'denial') GROUP BY payer_id, transaction_date""")
    cur.execute(f"""
        CREATE TEMP TABLE plb AS
        SELECT payment_id, payer_id, d, posted,
               CASE WHEN {U('payment_id', 'p')} < .015 THEN 'interest' WHEN {U('payment_id', 'p')} < .025 AND posted > 100 THEN 'recoupment' END kind
        FROM pdays WHERE posted > 0""")
    cur.execute("""
        CREATE TEMP TABLE plb2 AS
        SELECT payment_id, payer_id, d, kind, CASE kind WHEN 'interest' THEN round(posted * .002, 2) ELSE -round(posted * .01, 2) END amount FROM plb WHERE kind IS NOT NULL""")
    n["payment"] = ins(cur, "payment", dict(
        payment_id="x.payment_id", payment_number="'EFT-' || pr.payer_code || '-' || to_char(x.d, 'YYYYMMDD')", practice_id="1", payment_source="'payer'", payment_date="x.d",
        payment_amount="x.posted + coalesce(a.amount, 0)", payment_method="'eft'", payer_id="x.payer_id", payment_type="'eft'", received_date="x.d", posted_date="x.d", credit_debit="'C'",
        has_remittance="true", claim_count="x.claims", posted_amount="x.posted", unapplied_amount="0", plb_amount="coalesce(a.amount, 0)", reconciles="true", is_void="false"),
        "FROM pdays x JOIN payer pr ON pr.payer_id = x.payer_id LEFT JOIN plb2 a ON a.payment_id = x.payment_id")
    cur.execute("select coalesce(max(payment_id), 0) from payment")
    off = cur.fetchone()[0]
    n["payment"] += ins(cur, "payment", dict(
        payment_id=f"{off} + row_number() over (order by e.ledger_entry_id)", payment_number="'PT-' || e.ledger_entry_id", practice_id="e.practice_id", payment_source="'patient'",
        payment_date="e.transaction_date", payment_amount="e.amount", payment_method="coalesce(e.payment_method, 'card')", patient_id="e.patient_id", payment_type="'card'",
        received_date="e.transaction_date", posted_date="e.posted_date", credit_debit="'C'", has_remittance="false", claim_count="0", posted_amount="e.amount", unapplied_amount="0",
        plb_amount="0", reconciles="true", is_void="false"),
        "FROM ledger_entry e WHERE e.transaction_type = 'payment' AND e.responsible_party = 'patient'")
    cur.execute("UPDATE ledger_entry e SET payment_id = x.payment_id FROM pdays x WHERE e.responsible_party = 'payer' AND e.payer_id = x.payer_id AND e.transaction_date = x.d "
                "AND (e.transaction_type = 'payment' OR e.transaction_subtype = 'denial')")
    cur.execute(f"""UPDATE ledger_entry e SET payment_id = p.payment_id FROM payment p WHERE p.payment_source = 'patient' AND e.transaction_type = 'payment' AND e.responsible_party = 'patient'
                    AND p.payment_number = 'PT-' || e.ledger_entry_id""")
    n["payment_adjustment"] = ins(cur, "payment_adjustment", dict(
        payment_adjustment_id="a.payment_id", payment_id="a.payment_id", adjustment_type="a.kind", amount="a.amount", adjustment_date="a.d",
        plb_reason_code="case a.kind when 'interest' then 'L6' else 'WO' end", practice_id="1", payer_id="a.payer_id"), "FROM plb2 a")

    # remittance: one row per claim per payment
    cur.execute("""
        CREATE TEMP TABLE shares AS
        SELECT claim_id, transaction_date d, sum(amount) filter (where transaction_subtype = 'patient_responsibility') pr, sum(amount) filter (where transaction_subtype = 'contractual') adj
        FROM ledger_entry WHERE transaction_type = 'adjustment' AND transaction_subtype IN ('patient_responsibility', 'contractual') GROUP BY 1, 2""")
    cur.execute("""
        CREATE TEMP TABLE rem AS
        SELECT g.*, coalesce(s.pr, 0) pr, coalesce(s.adj, 0) adj FROM (
          SELECT e.payer_id, e.transaction_date d, e.claim_id,
                 coalesce(sum(e.amount) filter (where e.transaction_type = 'payment'), 0) paid,
                 count(*) filter (where e.transaction_type = 'payment') npaid, min(e.remark_code_id) filter (where e.transaction_subtype = 'denial') remark
          FROM ledger_entry e WHERE e.responsible_party = 'payer' AND (e.transaction_type = 'payment' OR e.transaction_subtype = 'denial') GROUP BY e.payer_id, e.transaction_date, e.claim_id) g
        LEFT JOIN shares s ON s.claim_id = g.claim_id AND s.d = g.d""")
    n["remittance_claim"] = ins(cur, "remittance_claim", dict(
        remittance_claim_id="row_number() over (order by r.d, r.payer_id, r.claim_id)", payment_id="p.payment_id", claim_id="r.claim_id", patient_control_number="c.claim_number",
        claim_status_code="case when r.npaid = 0 then '4' else '1' end", is_reversal="false", charge_amount="c.total_charge", paid_amount="r.paid", patient_responsibility="r.pr",
        claim_filing_indicator="case pr.payer_type when 'medicare' then 'MA' when 'medicaid' then 'MC' else 'CI' end", payer_claim_number="'PCN' || lpad(r.claim_id::text, 9, '0')",
        claim_level_adjustment="r.adj", remark_code_id="r.remark", is_crossover="false", match_method="'claim_number'", payer_id="r.payer_id", practice_id="c.practice_id"),
        "FROM rem r JOIN claim c ON c.claim_id = r.claim_id JOIN payer pr ON pr.payer_id = r.payer_id JOIN payment p ON p.payer_id = r.payer_id AND p.payment_date = r.d AND p.payment_source = 'payer'")

    cur.execute(f"""
        CREATE TEMP TABLE dep AS
        SELECT payment_id, payer_id, payment_date, payment_amount, {U('payment_id', 'q')} u FROM payment
        WHERE payment_source = 'payer' AND payment_amount > 0 AND payment_date + 1 <= date '{TODAY}'""")
    n["bank_deposit"] = ins(cur, "bank_deposit", dict(
        bank_deposit_id="row_number() over (order by x.payment_id)", practice_id="1", deposit_date="x.payment_date + 1",
        deposit_amount="x.payment_amount + case when x.u >= .01 and x.u < .03 then -round(x.payment_amount * .02, 2) else 0 end", deposit_method="'eft'",
        trace_number="'TRN' || lpad(x.payment_id::text, 9, '0')", payer_id="x.payer_id", payment_id="case when x.u < .01 then null else x.payment_id end",
        match_status="case when x.u < .01 then 'unmatched' when x.u < .03 then 'variance' else 'matched' end",
        matched_date=f"case when x.u < .01 then null else least(x.payment_date + 2, date '{TODAY}') end",
        variance_amount="case when x.u >= .01 and x.u < .03 then -round(x.payment_amount * .02, 2) else 0 end", bank_account_label="'Operating'"), "FROM dep x")

    # claim totals, status, bill status
    cur.execute("""
        UPDATE claim c SET paid_amount = a.paid, adjusted_amount = a.adj, patient_responsibility = a.pr, denied_amount = a.den, balance = a.pr + a.den,
               claim_status = CASE WHEN a.nd = a.n THEN 'denied' WHEN a.nd > 0 THEN 'partial' ELSE 'paid' END
        FROM (select claim_id, sum(paid_amount) paid, sum(contractual_adjustment) adj, sum(patient_responsibility) pr, sum(denied_amount) den, count(*) n,
                     count(*) filter (where line_status = 'denied') nd from claim_line group by 1) a
        WHERE a.claim_id = c.claim_id AND c.claim_status = 'paid'""")
    cur.execute("""
        UPDATE claim c SET last_payment_date = x.lp, last_status_date = x.ls
        FROM (select claim_id, max(transaction_date) filter (where transaction_type = 'payment') lp, max(transaction_date) ls from ledger_entry
              where responsible_party = 'payer' and (transaction_type = 'payment' or transaction_subtype = 'denial') group by 1) x
        WHERE x.claim_id = c.claim_id""")
    cur.execute("UPDATE claim SET payer_claim_number = 'PCN' || lpad(claim_id::text, 9, '0')")
    cur.execute("UPDATE bill b SET latest_claim_status = c.claim_status, bill_status = 'open' FROM claim c WHERE c.bill_id = b.bill_id AND c.claim_status IN ('denied', 'partial')")

    # status history: submitted, acknowledged, then pending or adjudicated, plus reprocessing after an overturn
    cur.execute("select claim_status_code_id, code from claim_status_code")
    cs = {c: i for i, c in cur.fetchall()}
    n["claim_status_history"] = 0
    events = [
        ("'submitted'", "c.submitted_date", "'submitted'", None, None, "true", ""),
        ("'acknowledged'", "c.submitted_date + 1", "'accepted'", "A2", "A", f"c.submitted_date + 1 <= date '{TODAY}'", ""),
        ("'pending'", "c.submitted_date + 5", "'pending'", "P1", "P", f"c.claim_status = 'submitted' AND c.submitted_date + 5 <= date '{TODAY}'", ""),
        ("'adjudicated'", "adj.d1", "case c.claim_status when 'denied' then 'denied' when 'partial' then 'partial' else 'paid' end", "F", "F", "adj.d1 IS NOT NULL", "")]
    cur.execute("CREATE TEMP TABLE adjd AS SELECT claim_id, min(transaction_date) d1 FROM ledger_entry WHERE responsible_party = 'payer' AND (transaction_type = 'payment' OR transaction_subtype = 'denial') GROUP BY 1")
    cur.execute("CREATE TEMP TABLE reproc AS SELECT d.claim_id, max(d.decision_date_raw) d2 FROM denf d WHERE d.overturned GROUP BY 1")
    kinds = 0
    for et, ed, st, code, cat, cond, _ in events + [("'reprocessed'", "rp.d2", "case c.claim_status when 'partial' then 'partial' else 'paid' end", "F1", "F", "rp.d2 IS NOT NULL", "")]:
        joins = "LEFT JOIN adjd adj ON adj.claim_id = c.claim_id LEFT JOIN reproc rp ON rp.claim_id = c.claim_id"
        code_sql = "null" if code is None else (f"case c.claim_status when 'denied' then 'F2' else 'F1' end" if code == "F" else f"'{code}'")
        cid = ("case c.claim_status when 'denied' then (select claim_status_code_id from claim_status_code where code = 'F2') else (select claim_status_code_id from claim_status_code where code = 'F1') end"
               if code == "F" else ("null" if code is None else str(cs[code])))
        n["claim_status_history"] += ins(cur, "claim_status_history", dict(
            claim_status_history_id=f"{kinds} * 1000000 + c.claim_id", claim_id="c.claim_id", event_type=et, event_date=ed, status_after=st, practice_id="c.practice_id", payer_id="c.payer_id",
            patient_id="c.patient_id", event_ts=f"({ed})::timestamp + time '09:00'", response_sequence="1", status_category="null" if cat is None else f"'{cat}'", status_category_code_id=cid,
            status_code=code_sql, status_code_id=cid, is_rejection="false", is_technical="false", channel="'clearinghouse'", payer_claim_number="'PCN' || lpad(c.claim_id::text, 9, '0')",
            billing_provider_id="c.billing_provider_id", specialty_id="c.specialty_id",
            reported_paid_amount="case when " + et + " in ('adjudicated', 'reprocessed') then c.paid_amount end".replace("'adjudicated'", "'adjudicated'")), f"FROM claim c {joins} WHERE {cond}")
        kinds += 1
    conn.commit()

    for t in ["adjustment_reason", "remark_code", "denial", "denial_reason", "appeal", "payment", "payment_adjustment", "remittance_claim", "bank_deposit", "claim_status_history"]:
        print(f"{t:24s}{n[t]:>10,}")


if __name__ == "__main__":
    main()
