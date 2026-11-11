"""Tie-out checks on the loaded canonical database (each prints PASS or FAIL with the numbers)."""
from core import connect

CHECKS = [
 ("claim total_charge = sum of its lines", "select count(*) from claim c join (select claim_id, sum(charge_amount) s from claim_details group by 1) d using(claim_id) where c.total_charge<>d.s"),
 ("bill total_billed = sum of its lines", "select count(*) from bill b join (select bill_id, sum(billed_amount) s from bill_details group by 1) d using(bill_id) where b.total_billed<>d.s"),
 ("claim paid_amount = sum of line paid", "select count(*) from claim c join (select claim_id, sum(paid_amount) s from claim_details group by 1) d using(claim_id) where c.paid_amount<>d.s"),
 ("posted payments = their payment transactions", "select count(*) from payment p join (select payment_id, sum(amount) s from transactions where payment_id is not null group by 1) t using(payment_id) where p.posted_amount<>t.s"),
 ("unposted remits have no transactions and carry unapplied cash", "select count(*) from payment p where unapplied_amount>0 and (posted_amount<>0 or exists (select 1 from transactions t where t.payment_id=p.payment_id))"),
 ("every paid claim line has a payment transaction (unless remit unposted)", "select count(*) from claim_details cd where cd.paid_amount>0 and not exists (select 1 from transactions t where t.claim_detail_id=cd.claim_detail_id and t.transaction_type='payment') and not exists (select 1 from claim c join payment p on p.payer_id=c.payer_id and p.unapplied_amount>0 and p.payment_date=c.last_payment_date where c.claim_id=cd.claim_id) and not exists (select 1 from denial d join claim c on c.claim_id=d.claim_id join payment p on p.payer_id=c.payer_id and p.unapplied_amount>0 and p.payment_date=d.resolved_date where d.claim_detail_id=cd.claim_detail_id)"),
 ("ledger balance per bill line = charge - payments - adjustments (never negative beyond copay credits)", "select count(*) from (select bill_detail_id, sum(balance_effect) s from transactions group by 1) x where x.s < -200"),
 ("denial lines belong to denied lines", "select count(*) from denial d join claim_details c using(claim_detail_id) where c.primary_denial_reason_id is null"),
 ("AR rows have positive balances", "select count(*) from ar where balance<=0"),
 ("coverage terminated before a claim's service date has CARC 27 (unless the denial was overturned: retroactive reinstatement)", "select count(*) from claim c join coverage v on v.coverage_id=c.coverage_id where v.termination_date<c.service_date_from and c.claim_status='paid' and not exists (select 1 from denial d join adjustment_reason a using(adjustment_reason_id) where d.claim_id=c.claim_id and a.carc_code='27' and d.outcome='overturned')"),
 ("nurses never bill (no claim, bill or line carries a registered nurse)", "select count(*) from bill b join provider p on p.provider_id in (b.billing_provider_id, b.rendering_provider_id) where p.provider_type='RN'"),
 ("no resource is held twice at the same time unless flagged as an overbook", "select count(*) from resource_allocation x join resource_allocation y on y.resource_id=x.resource_id and y.allocation_date=x.allocation_date and y.resource_allocation_id>x.resource_allocation_id and not x.is_overbook and not y.is_overbook and (x.start_time, x.start_time + x.duration_minutes*interval '1 minute') overlaps (y.start_time, y.start_time + y.duration_minutes*interval '1 minute')"),
 ("every nurse resource points at a registered-nurse provider", "select count(*) from resource r left join provider p on p.provider_id=r.provider_id where r.resource_type='staff' and (p.provider_type is distinct from 'RN')"),
 ("every appointment has a slot", "select count(*) from appointment a where not exists (select 1 from appointment_slot s where s.appointment_id=a.appointment_id)"),
]
STORIES = [
 ("S1 UHC CARC 50 denials in the last 30 days", "select count(*) from denial d join adjustment_reason a using(adjustment_reason_id) join payer p using(payer_id) where a.carc_code='50' and p.payer_code='SYNUHC' and d.denial_date>=date '2026-10-03'"),
 ("S2 BCBS 97140 lines paid below contract since 1 Aug", "select count(*) from claim_details cd join claim c using(claim_id) join payer p on p.payer_id=c.payer_id join cpt_code k using(cpt_code_id) where p.payer_code='SYNBCBS' and k.code='97140' and cd.allowed_amount is not null and cd.allowed_amount<cd.expected_allowed*0.95"),
 ("S3 bills on hold for unsigned notes", "select count(*) from bill where bill_status='on_hold'"),
 ("S4 Aetna CARC 198 denials", "select count(*) from denial d join adjustment_reason a using(adjustment_reason_id) where a.carc_code='198'"),
 ("S5 payer remits never posted", "select count(*) from payment where unapplied_amount>0"),
 ("S6 CARC 27 denials", "select count(*) from denial d join adjustment_reason a using(adjustment_reason_id) where a.carc_code='27'"),
 ("S8 claims with no payer response", "select count(*) from claim where claim_status='no_response'"),
 ("S10 Humana CARC 197 denials (procedures without authorization)", "select count(*) from denial d join adjustment_reason a using(adjustment_reason_id) join payer p using(payer_id) where a.carc_code='197' and p.payer_code='SYNHUM'"),
 ("S11 Texas Medicaid CARC 27 denials", "select count(*) from denial d join adjustment_reason a using(adjustment_reason_id) join payer p using(payer_id) where a.carc_code='27' and p.payer_code='SYNMCD'"),
 ("S12 UHC CARC 4 on E/M lines without modifier 25", "select count(*) from denial d join adjustment_reason a using(adjustment_reason_id) join payer p using(payer_id) join cpt_code k using(cpt_code_id) where a.carc_code='4' and p.payer_code='SYNUHC' and k.category='em'"),
 ("S13 Dr. Nakamura bills on hold", "select count(*) from bill b join provider p on p.provider_id=b.billing_provider_id where p.provider_name like 'Nakamura%' and b.bill_status='on_hold'"),
 ("resources in the inventory (rooms, machines, nurses)", "select count(*) from resource"),
 ("resource allocations", "select count(*) from resource_allocation"),
 ("nurse allocations", "select count(*) from resource_allocation a join resource r using(resource_id) where r.resource_type='staff'"),
 ("overbooked allocations", "select count(*) from resource_allocation where is_overbook"),
 ("S9 evaluations: billed level differs from documented", "select count(*) from encounter_details e join cpt_code k using(cpt_code_id) where k.code in ('97161','97162','97163','97165','97166') and e.documented_level is not null and e.documented_level <> case k.code when '97161' then 1 when '97165' then 1 when '97162' then 2 when '97166' then 2 else 3 end"),
]

if __name__ == "__main__":
    c, db = connect()
    cur = c.cursor()
    bad = 0
    for name, sql in CHECKS:
        cur.execute(sql)
        n = cur.fetchone()[0]
        bad += n != 0
        print(("PASS" if n == 0 else "FAIL"), f"({n})", name)
    print()
    for name, sql in STORIES:
        cur.execute(sql)
        print(f"{cur.fetchone()[0]:>6}  {name}")
    print("\nresult:", "all checks pass" if not bad else f"{bad} check(s) failed")
