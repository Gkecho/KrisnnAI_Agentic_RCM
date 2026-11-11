# Financial analytics: metric definitions and SQL

Exporter: `tools/analytics/export_fin_data.py` (output shape: `docs/fin_data_contract.md`). Source: Postgres `krisnnai_r2`, synthetic data, tenant 1, data date 2026-11-06.
The SQL below is the metric logic; the exact text the exporter runs now lives in the query registry (seed: `tools/analytics/fin_seed.py`, see `docs/fin_admin.md`) with named binds `:tenant_id` / `:asof` / `:d` instead of `%(t)s` / `%(asof)s` / `%(d)s`. In the snippets below `%(t)s` = tenant id, `%(asof)s` = 2026-11-06, `%(d)s` = an as-of date.
Money is `Decimal`, written as 2-decimal strings. Rates are 0..1 rounded to 4 places. All queries are SELECT only and filter `tenant_id`.

## Ground rules used by every metric
- "Charged" = `claim.total_charge` = sum of `claim_line.charge_amount` (identical, 39,724,812.00).
- The ledger (`ledger_entry`) is the money truth. `balance_effect` is signed; summed by `responsible_party` (payer / patient) it gives who owes what.
  Transfers move a balance from payer to patient (two rows that net to zero). Denial adjustments have `balance_effect = 0` (the denied amount stays on the payer balance until it is resolved).
- Month = service month of the claim line (`claim_line.service_date`) unless the metric says "payment month" (ledger `transaction_date`).
- Self-pay (patient charges with no claim, `claim_id IS NULL`) are in the ledger and in patient AR and patient payments, but not in claim-based metrics (Sankey, triangle, billing).

## headline
| Field | Definition |
|---|---|
| charged | sum of `claim.total_charge` |
| paid_payer / paid_patient | ledger `payment` rows by `responsible_party` (patient figure includes self-pay payments) |
| owed_payer / owed_patient | sum of `ledger_entry.balance_effect` by `responsible_party` (as of the data date) |
| denied | sum of `denial.denied_amount` (all denials ever raised) |
| denial_rate | denials / adjudicated claim lines (`line_status <> 'open'`) |
| claims, patients | `COUNT(*)` and `COUNT(DISTINCT patient_id)` of claims; the count only, no ids leave the database |

```sql
SELECT COUNT(*), COUNT(DISTINCT patient_id), SUM(total_charge) FROM claim WHERE tenant_id = %(t)s;
SELECT responsible_party, transaction_type, SUM(amount), SUM(balance_effect)
FROM ledger_entry WHERE tenant_id = %(t)s AND transaction_date <= %(d)s GROUP BY responsible_party, transaction_type;
SELECT COUNT(*), SUM(denied_amount) FROM denial WHERE tenant_id = %(t)s;
```

## flow (Sankey), `flow.all` and `flow.by_payer`
Built from one row per claim line, classified into three kinds:
- **denied**: the line has a `denial` row (or `line_status = 'denied'`). Its whole charge goes to `denied`, then splits by `denial_status`:
  `overturned` -> `overturned_recovered`; `upheld`, `deadline_missed`, `non_appealable` -> `denied_lost`; `open`, `appealed` -> `denial_open`.
- **in_process**: `line_status = 'open'` (not adjudicated yet): charge goes to `in_process`.
- **paid** (adjudicated, never denied): charge = `paid_amount` (`payer_paid`) + `contractual_adjustment` (`contractual`) + `patient_responsibility` (`patient_share`). Verified exact for every line.
  `patient_share` splits into `patient_paid` (ledger patient payments tied to the line), `at_agency` (unpaid remainder for patients with an `active` `collection_placement`), and `patient_owed` (the rest).

Consequence to be aware of: a line that was denied and then overturned is shown wholly under `denied -> overturned_recovered` (its payment, contractual and patient parts are not repeated under `payer_paid` etc.). So `payer_paid` in the Sankey (20,031,914.59) is lower than `headline.paid_payer` (20,419,146.83) by the 387,232.24 paid on overturned lines. Self-pay payments are not in the Sankey either.

```sql
WITH patient_paid AS (SELECT claim_line_id, SUM(amount) paid FROM ledger_entry
                      WHERE tenant_id = %(t)s AND transaction_type = 'payment' AND responsible_party = 'patient'
                        AND claim_line_id IS NOT NULL GROUP BY claim_line_id),
     agency_patient AS (SELECT DISTINCT patient_id FROM collection_placement
                        WHERE tenant_id = %(t)s AND placement_status = 'active'),
     line AS (SELECT p.payer_code, cl.charge_amount, cl.line_status, cl.paid_amount, cl.contractual_adjustment,
                     cl.patient_responsibility, d.denial_status, COALESCE(pp.paid, 0) patient_paid,
                     (ap.patient_id IS NOT NULL) at_agency
              FROM claim_line cl
              JOIN payer p ON p.payer_id = cl.payer_id AND p.tenant_id = %(t)s
              LEFT JOIN denial d ON d.claim_line_id = cl.claim_line_id AND d.tenant_id = %(t)s
              LEFT JOIN patient_paid pp ON pp.claim_line_id = cl.claim_line_id
              LEFT JOIN agency_patient ap ON ap.patient_id = cl.patient_id
              WHERE cl.tenant_id = %(t)s)
SELECT payer_code, SUM(charge_amount),
       SUM(paid_amount) FILTER (WHERE kind = 'paid'), SUM(contractual_adjustment) FILTER (WHERE kind = 'paid'),
       SUM(patient_responsibility) FILTER (WHERE kind = 'paid'), SUM(patient_paid) FILTER (WHERE kind = 'paid'),
       SUM(patient_responsibility - patient_paid) FILTER (WHERE kind = 'paid' AND at_agency),
       SUM(charge_amount) FILTER (WHERE kind = 'denied' AND dclass = 'recovered'),   -- ... 'lost', 'open'
       SUM(charge_amount) FILTER (WHERE kind = 'in_process')
FROM (SELECT *, CASE WHEN denial_status IS NOT NULL OR line_status = 'denied' THEN 'denied'
                     WHEN line_status = 'open' THEN 'in_process' ELSE 'paid' END kind,
                CASE WHEN denial_status = 'overturned' THEN 'recovered'
                     WHEN denial_status IN ('upheld','deadline_missed','non_appealable') THEN 'lost' ELSE 'open' END dclass
      FROM line) x GROUP BY payer_code;
```
`patient_owed = patient_share - patient_paid - at_agency` (computed in Python so the node balances to the cent). Zero-value links are omitted.

### Clarifications (agreed 2026-11-11)
- `at_agency` IS inside the patient owner balance: placing an account with an agency creates no ledger transfer, so `headline.owed_patient` and `ar.by_asof[as_of].owner.patient` (1,354,409.77) still include those dollars. The Sankey is claim-based, so `patient_owed + at_agency` (557,181.24 + 3,762.50) is only the claim-linked part of it; the rest of the patient balance is self-pay and older statement balances with no claim line. `headline.owed_*` equals `ar.by_asof[as_of].owner` (tested).
- The `overturned_recovered` node is labelled "Overturned after denial" and carries the denied charge of overturned lines (695,268.00), not cash. Payer cash on those lines is 387,232.24, so `headline.paid_payer` (20,419,146.83) = Sankey `payer_paid` (20,031,914.59) + that cash, not + the node value. This cannot be made to equal `payer_paid + overturned_recovered` without breaking the node's inflow = outflow rule; flagged for the pages.

## lag (triangle)
Rows = service month. Cells = ledger payments (payer + patient) tied to claim lines of that month, bucketed by `payment date - service date` (`WIDTH_BUCKET` with edges 31, 61, 91, 121, 181 -> 0-30 ... 181+).
`unpaid = charged - payments - contractual - denied_final`, where `denied_final` = charge of lines with a lost denial (`upheld`, `deadline_missed`, `non_appealable`) and `contractual` = `contractual_adjustment` on never-denied or overturned lines.
Row identity (checked by a test): `sum(cells) + contractual + denied_final = charged`. The two extra row fields `contractual` and `denied_final` are an addition to the contract so that this identity is visible.

```sql
SELECT TO_CHAR(cl.service_date,'YYYY-MM'), p.payer_code,
       WIDTH_BUCKET(le.transaction_date - cl.service_date, ARRAY[31,61,91,121,181]), SUM(le.amount)
FROM ledger_entry le
JOIN claim_line cl ON cl.claim_line_id = le.claim_line_id AND cl.tenant_id = %(t)s
JOIN payer p ON p.payer_id = cl.payer_id AND p.tenant_id = %(t)s
WHERE le.tenant_id = %(t)s AND le.transaction_type = 'payment' GROUP BY 1, 2, 3;
-- charged / contractual / denied_final per month and payer: see SQL_TRIANGLE_CHARGED (same line CTE as the Sankey)
```

## billing
- `monthly`: claims, charged (`claim.total_charge`) and claim counts by `claim_status` (paid / partial / submitted / denied) per service month.
- `top_cpt`: top 12 CPT codes by charged dollars (`claim_line` join `cpt_code`), with line count.
```sql
SELECT TO_CHAR(service_date_from,'YYYY-MM'), COUNT(*), SUM(total_charge),
       COUNT(*) FILTER (WHERE claim_status = 'paid'), ... 'partial', 'submitted', 'denied'
FROM claim WHERE tenant_id = %(t)s GROUP BY 1;
SELECT cpt.code, cpt.short_label, COUNT(*), SUM(cl.charge_amount) FROM claim_line cl
JOIN cpt_code cpt ON cpt.cpt_code_id = cl.cpt_code_id AND cpt.tenant_id = %(t)s
WHERE cl.tenant_id = %(t)s GROUP BY 1, 2 ORDER BY 4 DESC LIMIT 12;
```

## payments
- `monthly.payer_paid / patient_paid`: ledger `payment` rows by payment month and `responsible_party`.
- `tie_out`: `payments_total` = `payment.posted_amount` (payer source, not void); `remittance_total` = `remittance_claim.paid_amount`; `ledger_total` = ledger payer payments.
  `ok` = payments == remittance == ledger (to the cent).
```sql
SELECT SUM(posted_amount) FROM payment WHERE tenant_id = %(t)s AND payment_source = 'payer' AND NOT is_void;
SELECT SUM(paid_amount) FROM remittance_claim WHERE tenant_id = %(t)s;
SELECT SUM(amount) FROM ledger_entry WHERE tenant_id = %(t)s AND transaction_type = 'payment' AND responsible_party = 'payer';
```
(`payment.payment_amount` is 635.93 lower than `posted_amount` for payers, so the posted amount is used.)

## ar (point in time)
For each of 13 as-of dates (12 month-ends Nov 2025 - Oct 2026 and 2026-11-06) the matrix comes from `ar_snapshot` rows with `as_of_date = that date`; age = `days_outstanding` stored on the snapshot (days since submission for payer balances, since bill date for patient balances), bucketed 0-30, 31-60, 61-90, 91-120, 121-180, 181+ (the table's own `aging_bucket` stops at "120+", so the buckets are rebuilt from the days).
`matrix[payer]` = payer-owned balance by bucket; `owner` = payer-owned and patient-owned totals; `total` = their sum. Tests tie `total` to `SUM(ledger_entry.balance_effect)` up to that date and the owner split to `ar_interval` (month rows).
```sql
SELECT s.balance_owner, p.payer_code, WIDTH_BUCKET(s.days_outstanding, ARRAY[31,61,91,121,181]), SUM(s.balance)
FROM ar_snapshot s JOIN payer p ON p.payer_id = s.payer_id AND p.tenant_id = %(t)s
WHERE s.tenant_id = %(t)s AND s.as_of_date = %(d)s GROUP BY 1, 2, 3;
```

## denials
- `waterfall` (count, denied amount): `denied` = all denials; `appealed` = status appealed + overturned + upheld (an appeal was filed); `overturned`; `recovered` = denials with `recovered_amount > 0`, amount = `SUM(recovered_amount)` (cash actually paid after overturn, not the denied amount); `upheld`; `deadline_missed`; `final_no_appeal` = `non_appealable`; `open` = status open + appealed (still in play).
- `matrix`: top 8 CARC codes by denied dollars x payer. `by_reason`: every CARC: count, amount, `preventable` (denied dollars flagged `is_preventable`, a money string), `appealable` (`adjustment_reason.is_appealable`).
- `preventable`: denied dollars split by `denial.is_preventable`.
- `monthly`: per service month, `denied_amount` = denial dollars on that month's lines; `denial_rate` = lines with a denial / adjudicated lines.
```sql
SELECT denial_status, COUNT(*), SUM(denied_amount), COUNT(*) FILTER (WHERE recovered_amount > 0), SUM(recovered_amount)
FROM denial WHERE tenant_id = %(t)s GROUP BY 1;
SELECT ar.carc_code, ar.short_label, ar.is_appealable, p.payer_code, COUNT(*), SUM(d.denied_amount),
       SUM(d.denied_amount) FILTER (WHERE d.is_preventable)
FROM denial d JOIN adjustment_reason ar ON ar.adjustment_reason_id = d.adjustment_reason_id AND ar.tenant_id = %(t)s
JOIN payer p ON p.payer_id = d.payer_id AND p.tenant_id = %(t)s WHERE d.tenant_id = %(t)s GROUP BY 1, 2, 3, 4;
```

## patient
- `ladder`: `statement_1..4` = `patient_statement` by `dunning_level` 0..3; `paid` = `statement_status = 'paid'`; `remaining` = every other status at that level (sent, overdue, superseded = moved on to the next level, in_plan, collections), so remaining at step N overlaps the people who reappear at step N+1.
  `payment_plan`: paid = completed plans (`total_amount`), remaining = active + defaulted plans. `agency`: paid = `recovered_amount` of placements, remaining = `placed_amount` of `active` placements (recalled placements are neither).
- `plans`: count and total of `payment_plan`; `paid` = total of completed plans (proxy: there is no instalment-paid column).
- `agency`: placed, recovered, fees (`agency_fee_amount`), count over all `collection_placement` rows.
- `estimates`: `count` = all estimates; `matched` = insured estimates joined estimate -> encounter (`appointment_id`) -> paid/partial claims; `estimated_patient` vs `actual_patient` (claim `patient_responsibility`) on the matched set; `abs_error_median` = median of |estimated - actual| per matched estimate. GFE (self-pay) estimates have no claim and are excluded from the comparison.
```sql
SELECT dunning_level, statement_status, COUNT(*), SUM(statement_amount) FROM patient_statement WHERE tenant_id = %(t)s GROUP BY 1, 2;
SELECT plan_status, COUNT(*), SUM(total_amount) FROM payment_plan WHERE tenant_id = %(t)s GROUP BY 1;
SELECT placement_status, COUNT(*), SUM(placed_amount), SUM(recovered_amount), SUM(agency_fee_amount)
FROM collection_placement WHERE tenant_id = %(t)s GROUP BY 1;
-- estimates: see SQL_ESTIMATES (PERCENTILE_CONT(0.5) over ABS(est - act))
```

## scorecard (per payer, total and by service month)
- `claims`, `charged`: claim count and `total_charge`.
- `paid_rate` = `SUM(paid_amount) / SUM(total_charge)` over adjudicated claims (`claim_status` in paid, partial, denied).
- `denial_rate` = lines with a denial / adjudicated lines.
- `days_to_pay` = median days from `claim.submitted_date` to the first payer payment in the ledger (claims never paid are ignored).
```sql
WITH first_pay AS (SELECT claim_id, MIN(transaction_date) first_paid FROM ledger_entry
                   WHERE tenant_id = %(t)s AND transaction_type = 'payment' AND responsible_party = 'payer' AND claim_id IS NOT NULL
                   GROUP BY claim_id)
SELECT p.payer_code, TO_CHAR(c.service_date_from,'YYYY-MM'), COUNT(*), SUM(c.total_charge),
       SUM(c.total_charge) FILTER (WHERE c.claim_status IN ('paid','partial','denied')),
       SUM(c.paid_amount)  FILTER (WHERE c.claim_status IN ('paid','partial','denied')),
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY (fp.first_paid - c.submitted_date)::double precision)
FROM claim c JOIN payer p ON p.payer_id = c.payer_id AND p.tenant_id = %(t)s
LEFT JOIN first_pay fp ON fp.claim_id = c.claim_id
WHERE c.tenant_id = %(t)s GROUP BY ROLLUP (p.payer_code, TO_CHAR(c.service_date_from,'YYYY-MM'));
```

## Known data limits (reported, not papered over)
- Payer payment lag is narrow: 276,484 of 294,901 payer payments land within 0-30 days (16-137 days overall). The triangle's later columns are thin for payers; patient payments supply most of the 31+ columns.
- Patient `agency` remaining dollars are small (active placements only); recalled placements (482,827.04 placed, nothing recovered) are not counted as at the agency.
