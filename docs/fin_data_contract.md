# Financial analytics: data contract (`fin_data.js`)

Shared agreement between the exporter (`tools/analytics/export_fin_data.py`, reads `krisnnai_r2`) and the pages (`krisnnai-site/finance/*.html`).
The exporter writes `window.KRISNNAI_FIN = {...};`. Pages only read it. Synthetic data, shadow mode, tenant 1 only, aggregates only (no patient rows, no ids of people).

Conventions
- Money = string with two decimals, e.g. `"1234567.89"` (charts convert with `Number()` for drawing only). Rates = number 0..1. Dates = ISO `YYYY-MM-DD`; months = `YYYY-MM`.
- Data date ("today") is `2026-11-06`. Nothing may be dated after it.
- `payer` keys are `payer.payer_code` (MEDICARE, ANTHEM, HUMANA, AETNA, CIGNA, BCBS, MEDICAID, UHC, DUAL).
- Point-in-time: anything under `asof[...]` is computed as of that date using only data known then (hard rule 9).

## Top level
```
meta     { as_of:"2026-11-06", generated_at, source:"krisnnai_r2", shadow:true, synthetic:true, tenant_id:1 }
payers   [ {code, name, type} ]                         // type: medicare | commercial | medicaid
months   ["2023-11", ... "2026-11"]                     // service/event months; last one is partial (to the 6th)
asof     ["2025-11-30", ... "2026-10-31", "2026-11-06"] // 13 dates; keys for the `ar` object
headline { charged, paid_payer, paid_patient, owed_payer, owed_patient, denied, denial_rate, claims, patients }   // all as of meta.as_of
flow     { all: Sankey, by_payer: { CODE: Sankey } }
lag      Triangle
billing  { monthly:[...], top_cpt:[...] }
payments { monthly:[...], tie_out:{...} }
ar       { buckets:[...], by_asof: { "<asof>": { matrix:{CODE:[$ per bucket]}, owner:{payer, patient}, total } } }
denials  { waterfall:[...], matrix:{reasons:[...], payers:[...], cells:[[$]]}, by_reason:[...], preventable:{...}, monthly:[...] }
patient  { ladder:[...], plans:{...}, agency:{...}, estimates:{...} }
scorecard{ CODE: { claims, charged, paid_rate, denial_rate, days_to_pay, monthly:[{month, paid_rate, denial_rate, days_to_pay}] } }
```

## Sankey (`flow.*`)
```
{ nodes:[{id,label,group}], links:[{source,target,value}] }     // value = money string
```
Left to right: `charged` -> `payer_paid`, `contractual`, `patient_share`, `denied`, `in_process` (claims not yet adjudicated).
Then: `patient_share` -> `patient_paid`, `patient_owed`, `at_agency`. `denied` -> `overturned_recovered`, `denied_lost` (final + expired + upheld), `denial_open`.
Rule: for every node, inflow == outflow (except `charged`, which only has outflow, and terminal nodes, which only have inflow). The exporter test checks this exactly.

## Clarifications (agreed after the front-end build, 2026-11-11)
- `months` has 37 entries (2023-11 to 2026-11).
- Sankey: `denied` = final + upheld + overturned + open denials. `payer_paid` = payments on lines that were NOT denied. Overturned recoveries flow `denied` -> `overturned_recovered` (label "Overturned after denial", never "recovered"/"saved"). `headline.paid_payer` = `payer_paid` + `overturned_recovered` (all payer cash).
- Triangle rows carry optional `contractual` and `denied_final` money strings; cells sum to `charged - contractual - denied_final`. Open denials sit in `unpaid`.
- `headline.owed_payer` / `owed_patient` equal `ar.by_asof[meta.as_of].owner`. The exporter must state in `docs/fin_metrics.md` whether `at_agency` is inside the patient owner balance, and keep Sankey and headline consistent with that.
- Only `ar` is as-of driven; `headline`, `flow`, `lag` are at `meta.as_of`.

## Triangle (`lag`)
```
{ cols:["0-30","31-60","61-90","91-120","121-180","181+","unpaid"],      // days from service date to payment
  rows:[ { month:"2024-03", charged:"$", cells:["$ paid in that lag bucket", ... 7 values], by_payer:{CODE:[7 values]} } ] }
```
Cells are payer + patient payments by service month. `unpaid` = charged minus all paid minus contractual minus denied-final (still collectible). Row sums reconcile to charged.

## billing
`monthly:[{month, claims, charged, status:{paid,partial,submitted,denied}}]` (status = claim counts). `top_cpt:[{code,label,lines,charged}]` top 12.

## payments
`monthly:[{month, payer_paid, patient_paid}]`. `tie_out:{payments_total, remittance_total, ledger_total, ok:true}`. (Bank deposits are deliberately not part of the analytics, per the owner.)

## ar
`buckets:["0-30","31-60","61-90","91-120","121-180","181+"]` (age since claim submission or bill date). `matrix` holds the payer-owner dollars per payer per bucket; `owner` = `{payer:"$", patient:"$"}`; `total` = sum of both.
Source of truth is `ar_snapshot` / `ar_interval` for each as-of date.

## denials
`waterfall:[{step:"denied"|"appealed"|"overturned"|"recovered"|"upheld"|"deadline_missed"|"final_no_appeal"|"open", count, amount}]`.
`matrix`: reasons = top 8 CARC with `short_label`; payers = codes; cells[reason][payer] = denied dollars. `by_reason:[{carc,label,count,amount,preventable,appealable}]`.
`preventable:{preventable:"$", other:"$"}`. `monthly:[{month, denied_amount, denial_rate}]`.

## patient
`ladder:[{step:"statement_1".."statement_4"|"payment_plan"|"agency", paid_count, paid_amount, remaining_count, remaining_amount}]` (cumulative, from `patient_statement`, `payment`, `payment_plan`, `collection_placement`).
`plans:{count, total, paid}`. `agency:{placed, recovered, fees, count}`. `estimates:{count, estimated_patient, actual_patient, abs_error_median}`.

## scorecard
Per payer. `days_to_pay` = median days from submission to first payment. `paid_rate` = paid / charged on adjudicated claims. `denial_rate` = denied lines / lines.

## Pages
`finance/index.html` (Overview), `billing.html`, `payments.html`, `ar.html`, `denials.html`, `patient.html`, `payers.html`.
Shared: `finance.css`, `fin-charts.js` (window.FinCharts: sankey, triangle, heatmap, waterfall, matrix, ladder, sparkline), `fin-shell.js` (nav, as-of slider, banner, theme).
