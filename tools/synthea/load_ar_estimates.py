"""Stage 6b: patient estimates, A/R snapshots and A/R intervals for krisnnai_r2.

Run after load_patient_billing.py. Everything here is computed from tables already loaded; no money changes.

- patient_estimate / patient_estimate_line: one estimate per appointment that has lines, given when the visit was booked. Self-pay visits get a good-faith estimate equal to the price
  list, except 4% where the estimate left out part of the bill; insured visits get an estimate within -20% to +20% of the patient share the claim later showed. The flag
  exceeds_gfe_by_400 marks a self-pay bill that ran $400 or more over its estimate.
- ar_snapshot: month-end for the last 12 months plus 2026-11-06, one row per bill and balance owner (payer or patient) with a balance on that date. Balances, status, denials,
  statements and collection placements are all taken as of that date (hard rule 9: nothing from after the date).
- ar_interval: one row per bill line per month for the same period, with opening, charges, payments, adjustments and closing balance from the ledger.

    python tools/synthea/load_ar_estimates.py --reset
"""
import datetime as dt
import sys

from load_denials import U, ins
from r2load import connect

TODAY = dt.date(2026, 11, 6)
TABLES = ["ar_interval", "ar_snapshot", "patient_estimate_line", "patient_estimate"]


def month_ends():
    out, d = [], dt.date(2025, 11, 1)
    while d <= dt.date(2026, 10, 1):
        nxt = dt.date(d.year + (d.month == 12), d.month % 12 + 1, 1)
        out.append((d, nxt - dt.timedelta(days=1)))
        d = nxt
    return out


def bucket(days):
    return f"case when {days} <= 30 then '0-30' when {days} <= 60 then '31-60' when {days} <= 90 then '61-90' when {days} <= 120 then '91-120' else '120+' end"


def main():
    reset = "--reset" in sys.argv
    conn = connect()
    cur = conn.cursor()
    cur.execute("SET session_replication_role = replica")
    if reset:
        for t in TABLES:
            cur.execute(f'DELETE FROM "{t}"')
    else:
        for t in TABLES:
            cur.execute(f'select count(*) from "{t}"')
            assert cur.fetchone()[0] == 0, f"{t} is not empty; use --reset"
    n = {}

    # ---- estimates
    cur.execute("""
        CREATE TEMP TABLE ea AS
        SELECT a.appointment_id, a.patient_id, a.coverage_id, a.practice_id, a.booked_date, a.appointment_date, a.facility_id, p.payer_type = 'self_pay' AS self_pay,
               l.total, b.total_billed, coalesce(c.patient_responsibility, 0) actual_patient, pc.preferred_channel
        FROM appointment a JOIN payer p ON p.payer_id = a.payer_id
        JOIN (select appointment_id, sum(expected_charge) total from appointment_line group by 1) l ON l.appointment_id = a.appointment_id
        LEFT JOIN encounter e ON e.appointment_id = a.appointment_id LEFT JOIN bill b ON b.encounter_id = e.encounter_id LEFT JOIN claim c ON c.bill_id = b.bill_id
        LEFT JOIN patient_contact_preference pc ON pc.patient_id = a.patient_id""")
    cur.execute(f"""
        CREATE TEMP TABLE est AS
        SELECT ea.*, CASE WHEN self_pay AND {U('appointment_id', 'g1')} < .04 THEN round(total * .5, 2) ELSE total END est_total,
               CASE WHEN self_pay THEN CASE WHEN {U('appointment_id', 'g1')} < .04 THEN round(total * .5, 2) ELSE total END
                    ELSE round(actual_patient * (.8 + .4 * {U('appointment_id', 'g2')}), 2) END est_patient
        FROM ea""")
    n["patient_estimate"] = ins(cur, "patient_estimate", dict(
        patient_estimate_id="e.appointment_id", estimate_number="'EST-' || lpad(e.appointment_id::text, 9, '0')", patient_id="e.patient_id", appointment_id="e.appointment_id",
        coverage_id="e.coverage_id", estimate_type="case when e.self_pay then 'gfe' else 'insured' end", estimate_date="e.booked_date", service_date="e.appointment_date",
        estimated_total="e.est_total", estimated_patient_amount="e.est_patient",
        delivered_channel="case e.preferred_channel when 'text' then 'email' else coalesce(e.preferred_channel, 'mail') end",
        delivered_date=f"least(e.booked_date + floor({U('e.appointment_id', 'g3')} * 2)::int, e.appointment_date)", actual_billed_amount="e.total_billed",
        exceeds_gfe_by_400="coalesce(e.self_pay and e.total_billed - e.est_total >= 400, false)", practice_id="e.practice_id"), "FROM est e")
    n["patient_estimate_line"] = ins(cur, "patient_estimate_line", dict(
        patient_estimate_id="al.appointment_id", patient_estimate_line_id="al.appointment_line_id", line_number="al.line_number", cpt_code_id="al.planned_cpt_code_id",
        diagnosis_code_id="al.planned_diagnosis_code_id", provider_id="al.provider_id", facility_id="e.facility_id", is_co_provider_item="false", units="al.planned_units",
        expected_charge="al.expected_charge", expected_patient_amount="round(e.est_patient * al.expected_charge / nullif(e.total, 0), 2)", appointment_line_id="al.appointment_line_id",
        billed_amount="bl.billed_amount", practice_id="al.practice_id"),
        """FROM appointment_line al JOIN est e ON e.appointment_id = al.appointment_id
           LEFT JOIN encounter en ON en.appointment_id = al.appointment_id LEFT JOIN encounter_line el ON el.encounter_id = en.encounter_id AND el.line_number = al.line_number
           LEFT JOIN bill_line bl ON bl.encounter_line_id = el.encounter_line_id""")

    # ---- helper tables so every snapshot sees only what existed on its date
    cur.execute("""CREATE TEMP TABLE lb AS SELECT bl.bill_id, e.responsible_party party, e.transaction_date d, sum(e.balance_effect) eff, sum(e.amount) filter (where e.transaction_type = 'payment') paid
                   FROM ledger_entry e JOIN bill_line bl ON bl.bill_line_id = e.bill_line_id GROUP BY 1, 2, 3""")
    cur.execute("CREATE TEMP TABLE csh AS SELECT claim_id, event_date, status_after, claim_status_history_id seq FROM claim_status_history")
    cur.execute("CREATE INDEX ON csh (claim_id, event_date)")
    cur.execute("CREATE TEMP TABLE stm AS SELECT bill_id, statement_date FROM patient_statement")
    cur.execute("CREATE INDEX ON stm (bill_id)")
    cur.execute("""CREATE TEMP TABLE dd AS SELECT bl.bill_id, d.denial_date, d.denied_amount amt, CASE WHEN d.denial_status = 'overturned' THEN d.resolved_date END ovt
                   FROM denial d JOIN claim_line cl ON cl.claim_line_id = d.claim_line_id JOIN bill_line bl ON bl.bill_line_id = cl.bill_line_id""")
    cur.execute("CREATE INDEX ON dd (bill_id)")
    cur.execute("""CREATE TEMP TABLE plc AS SELECT DISTINCT s.bill_id, p.placed_date, p.closed_date FROM patient_statement s
                   JOIN collection_placement p ON p.collection_placement_id = s.collection_placement_id""")
    cur.execute("CREATE INDEX ON plc (bill_id)")
    cur.execute("CREATE TEMP TABLE fl AS SELECT DISTINCT ON (bill_id) bill_id, cpt_code_id FROM bill_line ORDER BY bill_id, line_number")
    cur.execute("CREATE INDEX ON fl (bill_id)")

    # ---- snapshots
    dates = [(e, "month_end") for _, e in month_ends()] + [(TODAY, "current")]
    n["ar_snapshot"] = 0
    for D, kind in dates:
        d = f"date '{D}'"
        age = f"({d} - (case when x.party = 'patient' then x.firstpos when c.submitted_date <= {d} then c.submitted_date else x.firstpos end))"
        cur.execute("select coalesce(max(ar_snapshot_id), 0) from ar_snapshot")
        base = cur.fetchone()[0]
        n["ar_snapshot"] += ins(cur, "ar_snapshot", dict(
            ar_snapshot_id=f"{base} + row_number() over (order by x.bill_id, x.party)", as_of_date=d, snapshot_type=f"'{kind}'", bill_id="x.bill_id", balance_owner="x.party", balance="x.bal",
            practice_id="b.practice_id", patient_id="b.patient_id", guarantor_id="pt.guarantor_id",
            aging_date=f"case when x.party = 'patient' then x.firstpos when c.submitted_date <= {d} then c.submitted_date else x.firstpos end", days_outstanding=age, aging_bucket=bucket(age),
            aging_basis=f"case when x.party = 'patient' then 'balance_date' when c.submitted_date <= {d} then 'submitted_date' else 'charge_date' end",
            claim_id="c.claim_id", payer_id="b.payer_id", claim_status="st.status_after", submitted_date=f"case when c.submitted_date <= {d} then c.submitted_date end",
            last_payment_date="x.lastpay", last_activity_date="x.lastact", days_since_activity=f"{d} - x.lastact", last_statement_date="ls.d",
            open_denied_amount="case when x.party = 'payer' then coalesce(od.amt, 0) else 0 end", is_in_denial="coalesce(x.party = 'payer' and od.amt > 0, false)", is_credit="false",
            filing_deadline="case when x.party = 'payer' then b.service_date + py.filing_days end", provider_id="b.rendering_provider_id", specialty_id="b.specialty_id", facility_id="b.facility_id",
            service_date="b.service_date", primary_cpt_code_id="fl.cpt_code_id", collections_agency_flag="coalesce(cp.one is not null, false)"),
            f"""FROM (SELECT bill_id, party, sum(eff) bal, max(d) filter (where paid > 0) lastpay, max(d) lastact, min(d) filter (where eff > 0) firstpos
                       FROM lb WHERE d <= {d} GROUP BY bill_id, party HAVING sum(eff) > 0.005) x
                JOIN bill b ON b.bill_id = x.bill_id JOIN patient pt ON pt.patient_id = b.patient_id JOIN payer py ON py.payer_id = b.payer_id
                LEFT JOIN claim c ON c.bill_id = b.bill_id
                LEFT JOIN LATERAL (select status_after from csh h where h.claim_id = c.claim_id and h.event_date <= {d} order by h.event_date desc, h.seq desc limit 1) st ON true
                LEFT JOIN LATERAL (select max(statement_date) d from stm s where s.bill_id = b.bill_id and s.statement_date <= {d}) ls ON x.party = 'patient'
                LEFT JOIN LATERAL (select sum(amt) amt from dd where dd.bill_id = b.bill_id and dd.denial_date <= {d} and not (dd.ovt is not null and dd.ovt <= {d})) od ON x.party = 'payer'
                LEFT JOIN LATERAL (select 1 one from plc p where p.bill_id = b.bill_id and p.placed_date <= {d} and (p.closed_date is null or p.closed_date > {d}) limit 1) cp ON x.party = 'patient'
                LEFT JOIN fl ON fl.bill_id = b.bill_id""")
        print("snapshot", D, flush=True)
    values = ",".join(f"(date '{dates[i][0]}', {'null' if i == 0 else f'date {chr(39)}{dates[i - 1][0]}{chr(39)}'})" for i in range(len(dates)))
    cur.execute(f"""UPDATE ar_snapshot s SET change_since_last_snapshot = z.chg FROM (
                      SELECT t.ar_snapshot_id, t.balance - CASE WHEN lag(t.as_of_date) OVER w = m.prev THEN lag(t.balance) OVER w ELSE 0 END chg
                      FROM ar_snapshot t JOIN (VALUES {values}) m(d, prev) ON m.d = t.as_of_date
                      WINDOW w AS (PARTITION BY t.bill_id, t.balance_owner ORDER BY t.as_of_date)) z
                    WHERE z.ar_snapshot_id = s.ar_snapshot_id AND s.as_of_date > date '{dates[0][0]}'""")

    # ---- intervals
    cur.execute("""CREATE TEMP TABLE lbl AS SELECT bill_line_id, responsible_party party, transaction_type typ, transaction_subtype sub, transaction_date d, balance_effect eff, amount
                   FROM ledger_entry""")
    periods = [(s, e, "closed") for s, e in month_ends()] + [(dt.date(2026, 11, 1), TODAY, "open")]
    n["ar_interval"] = 0
    for ps, pe, status in periods:
        s_, e_ = f"date '{ps}'", f"date '{pe}'"
        pag = f"coalesce(case when c.submitted_date <= {e_} then c.submitted_date end, y.firstpay)"
        pdays, tdays = f"({e_} - {pag})", f"({e_} - y.firstpat)"
        cur.execute("select coalesce(max(ar_interval_id), 0) from ar_interval")
        base = cur.fetchone()[0]
        n["ar_interval"] += ins(cur, "ar_interval", dict(
            ar_interval_id=f"{base} + row_number() over (order by y.bill_line_id)", bill_line_id="y.bill_line_id", period_start_date=s_, period_end_date=e_, period_type="'month'",
            practice_id="bl.practice_id", patient_id="bl.patient_id", guarantor_id="pt.guarantor_id", opening_balance="y.opening", charges="y.charges", payments="y.payments",
            adjustments="y.adjustments", write_offs="0", refunds="0", closing_balance="y.closing", payer_balance="y.payer_bal", patient_balance="y.patient_bal",
            payer_bucket=f"case when y.payer_bal <= 0.005 then 'none' else {bucket(pdays)} end", patient_bucket=f"case when y.patient_bal <= 0.005 then 'none' else {bucket(tdays)} end",
            aging_basis="'submitted_date'", reconciles="abs(y.opening + y.charges - y.payments - y.adjustments - y.closing) < 0.005", payer_days=f"case when y.payer_bal > 0.005 then {pdays} end",
            patient_days=f"case when y.patient_bal > 0.005 then {tdays} end", payer_aging_date=pag, patient_aging_date="y.firstpat", unbilled_balance="0",
            payments_payer="y.pay_payer", payments_patient="y.pay_patient", adjustments_contractual="y.contractual", adjustments_denial="y.denial_amt", adjustments_other="0",
            transfers_to_patient="y.transfers", claim_id="cl.claim_id", claim_line_id="cl.claim_line_id", claim_status="st.status_after", payer_id="bl.payer_id",
            open_denied_amount="coalesce(dn.denied_amount, 0)", is_in_denial="dn.denial_id is not null", ledger_balance="y.closing", variance_amount="0", is_restated="false",
            period_status=f"'{status}'", provider_id="bl.provider_id", specialty_id="bl.specialty_id", cpt_code_id="bl.cpt_code_id", service_date="bl.service_date"),
            f"""FROM (SELECT bill_line_id,
                       coalesce(sum(eff) filter (where d < {s_}), 0) opening,
                       coalesce(sum(eff) filter (where d >= {s_} and typ = 'charge'), 0) charges,
                       coalesce(-sum(eff) filter (where d >= {s_} and typ = 'payment'), 0) payments,
                       coalesce(-sum(eff) filter (where d >= {s_} and typ = 'adjustment'), 0) adjustments,
                       coalesce(-sum(eff) filter (where d >= {s_} and typ = 'payment' and party = 'payer'), 0) pay_payer,
                       coalesce(-sum(eff) filter (where d >= {s_} and typ = 'payment' and party = 'patient'), 0) pay_patient,
                       coalesce(-sum(eff) filter (where d >= {s_} and sub = 'contractual'), 0) contractual,
                       coalesce(sum(amount) filter (where d >= {s_} and sub = 'denial'), 0) denial_amt,
                       coalesce(sum(amount) filter (where d >= {s_} and typ = 'transfer' and party = 'payer'), 0) transfers,
                       sum(eff) closing, coalesce(sum(eff) filter (where party = 'payer'), 0) payer_bal, coalesce(sum(eff) filter (where party = 'patient'), 0) patient_bal,
                       min(d) filter (where party = 'payer' and eff > 0) firstpay, min(d) filter (where party = 'patient' and eff > 0) firstpat
                     FROM lbl WHERE d <= {e_} GROUP BY bill_line_id
                     HAVING abs(sum(eff)) > 0.005 OR abs(coalesce(sum(eff) filter (where d < {s_}), 0)) > 0.005 OR count(*) filter (where d >= {s_}) > 0) y
                JOIN bill_line bl ON bl.bill_line_id = y.bill_line_id JOIN patient pt ON pt.patient_id = bl.patient_id
                LEFT JOIN claim_line cl ON cl.bill_line_id = y.bill_line_id LEFT JOIN claim c ON c.claim_id = cl.claim_id
                LEFT JOIN LATERAL (select status_after from csh h where h.claim_id = cl.claim_id and h.event_date <= {e_} order by h.event_date desc, h.seq desc limit 1) st ON true
                LEFT JOIN denial dn ON dn.claim_line_id = cl.claim_line_id AND dn.denial_date <= {e_} AND NOT (dn.denial_status = 'overturned' AND dn.resolved_date <= {e_})""")
        print("interval", ps, flush=True)
    conn.commit()
    for t, c in n.items():
        print(f"{t:28s}{c:>10,}")


if __name__ == "__main__":
    main()
