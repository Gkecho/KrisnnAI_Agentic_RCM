# A15-lite: revenue leakage diagnostic (M5)

`krisnai a15 --tenant ID --as-of DATE --out DIR [--ground-truth ground_truth.csv] [--g0-tolerance 0.01]`
Run `krisnai ingest` and `krisnai match` first. Writes `a15_lite.json` and `a15_lite.xlsx`. **Read-only**: it changes no
claim, remit or setting and recovers no money. Findings are *detected* opportunities. It proposes no action, so it writes no
decision record (that starts with the decision engine, M6).

## Order of work
1. **G0 reconciliation** (`g0.py`). If any check is off by more than the tolerance, the run stops with exit code 2 and
   **writes nothing**: claim total = sum of its lines, remit billed and paid = sum of its lines, payment BPR02 = sum of its
   remits less PLB, and at least 99% of remits linked to a claim.
2. **Snapshot** (`snapshot.py`): only data known on or before the as-of date.
3. **Pricing** (`expected.py`): allowed = fee schedule x units (latest row in force on the service date, first modifier).
   With no fee row: the payer's median received per unit for that CPT, flagged `fallback`; no data at all is `unpriced` ($0).
   The patient share is learned per payer as patient responsibility / contract allowed on paid lines (not hard-coded).
   Expected payer payment = allowed less that share.
4. **Detection** (`detect.py`), one finding per item:
   | type | rule | $ | window | agent |
   |---|---|---|---|---|
   | `denial` | first remit denied (CLP02 4) | expected payer payment of its lines | appeal, from payment date | by CARC category |
   | `timely_filing` | denial with CARC 29 | same | always structural | A5 |
   | `underpayment` | paid line, allowed - (paid + patient share) > 0 | the shortfall | appeal, from payment date | A10 |
   | `rejection` | 999 rejected / 277CA A3 or A4, never answered by an 835 | expected payer payment of the claim | filing, from service date | A6 |
   | `unbilled_visit` | PM visit with no claim for that payer, patient, date and CPT | expected payer payment | filing, from service date | A3 |
   | `unexplained_adjustment` | CO / OA / PI adjustment other than CARC 45 on a paid line not already an underpayment | the adjustment | appeal | A7 |
   Fallback-priced underpayments are only flagged when 20% or more below the median.
5. **Report** (`report.py`): summary, by payer / CPT / location (place of service) / provider, recoverable vs structural,
   ranked opportunities (recoverable first, then by dollars), baseline KPIs (M4), reconciliation. No patient identifiers.

## Defaults awaiting sign-off (`config.py`)
Appeal window 180 days and filing window 365 days for every payer (per-payer overrides exist); CARC categories
(16 missing information, 18 duplicate, 50 medical necessity, 97 bundling, 27 / 31 coverage, 197 authorization, 4 coding, 29 timely
filing); denial category to agent (coverage A1; duplicate and timely filing A5; everything else A8); G0 tolerance 0.01.

## Score on the synthetic set
`--ground-truth` prints precision, recall and "right dollars + status" per issue type. On the 200-claim synthetic set every
planted issue (49) is found with the right type, dollars and recoverable / structural status, with no extra findings.

## Not done yet
Multiple-procedure reductions in expected allowed; payer-specific windows from contracts (A10); claim-level CAS on remits with
several lines is used for denial reasons only; replacement claims are not folded into the claim they replace.
