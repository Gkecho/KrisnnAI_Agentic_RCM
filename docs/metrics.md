# Metric dictionary (M4)

Each KPI is one SQL file in `krisnnai/metrics/sql/` (shared building blocks in `_prelude.sql`). `krisnnai metrics --tenant ID --as-of DATE`
runs them; on SQL Server the same text is installed by migration 0002 as `metrics.fn_<kpi>(@as_of, @tenant_id)`
(a view cannot take a date). **Run `krisnnai match` first**: the KPIs read the remit-to-claim and 277CA-to-claim links.

## Rules that apply to every KPI
- **As of:** a row counts only if its event was known (ISA date of its file) on or before `as_of`. No future data.
- **Claims:** every claim version except voids (frequency 8). A replacement claim counts as its own claim; the first
  adjudication of each claim is its earliest remit by payment date, reversals (CLP02 22) are ignored for that.
- **Zero denominators** return NULL, never 0.
- **Open balance of a claim** = billed - sum of payments - patient share (CLP05) - non-patient adjustments (CO, OA, PI, CR),
  never below 0. It is what the payer still owes. Adjustments are taken from the service lines; claim-level CAS is used
  only for a remit that has no line-level CAS. Claims rejected by the 999/277CA are not AR.
- **Money** is exact `DECIMAL`; the SQLite test copy rounds to 6 places.

## KPIs

### `clean_claim_rate` - `krisnnai/metrics/sql/clean_claim_rate.sql`
Claims with no 999 rejection (status R) and no 277CA A3/A4, divided by claims submitted. The 999 is tied to a claim by
the control numbers (GS06, ST02) of the 837 it came in.

### `rejection_rate` - `krisnnai/metrics/sql/rejection_rate.sql`
Claims rejected by the 999 or returned / not found by the 277CA, divided by claims submitted. Counts split by source.

### `first_pass_paid_rate` - `krisnnai/metrics/sql/first_pass_paid_rate.sql`
Claims whose first remit is processed (CLP02 1, 2 or 3) with a payment above 0, divided by claims with at least one remit.

### `denial_rate` - `krisnnai/metrics/sql/denial_rate.sql`
Claims whose first remit is denied (CLP02 4), divided by claims with a remit; count and billed dollars. One row per slice:
`overall`, `payer` (denominator = that payer's claims), `carc` and `cpt` (denominator = all adjudicated claims, so the rate
is a share of everything). CARC is the CAS reason code on the denied remit; CPT is the denied remit line.

### `days_in_ar` - `krisnnai/metrics/sql/days_in_ar.sql`
Open AR at `as_of` divided by average daily charges, where average daily charges = billed on claims submitted in the
last 90 days / 90.

### `ar_over_90` - `krisnnai/metrics/sql/ar_over_90.sql`
Open balance of claims older than 90 days (as_of minus service date) and its share of total open AR.

### `net_collection_rate` - `krisnnai/metrics/sql/net_collection_rate.sql`
Payer payments / (billed - contractual adjustments) for claims with a remit. Contractual is CAS group CO, reason 45. Patient
payments are not in the data, so a second rate counts the patient share (CLP05) as collectable.

### `underpayment` - `krisnnai/metrics/sql/underpayment.sql`
For each paid remit line with a fee-schedule row (payer + CPT + first modifier, latest `effective_date` in force on the
service date): `max(0, allowed x units - (paid + patient share))`, summed. Lines with no fee row are counted separately
(`lines_without_fee`) and never guessed. Denied lines (paid 0) are denials, not underpayments.

### `charge_lag` - `krisnnai/metrics/sql/charge_lag.sql`
Average days from service date to the claim's submission date (BHT04), for claims submitted by `as_of`.

## Known limits (decide before relying on them)
- Replacement claims are not folded into the claim they replace.
- Patient-balance AR is not tracked; open AR is the payer's side only.
- The 999 link needs control numbers to be unique across files for a tenant.
