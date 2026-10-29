# Matching spec (M3)

`krisnnai match --tenant ID [--as-of ISO-TIMESTAMP] [--json]` links remits to claims, remit lines to claim lines and
277CAs to claims, then prints a match quality report. It only touches rows whose link is still NULL, so a second run
changes nothing. With `--as-of`, only rows whose event was known by then are used.

## Order
1. **277CA -> claim** by CLM01 echo (`ack_277ca.claim_submitter_id`). This also makes the payer claim number (REF*1K)
   usable to find a claim, because the synthetic 837 carries no REF*F8.
2. **Remit -> claim.** Candidates are limited to the payment's payer. First hit wins; the rule is stored in `remit.match_method`.
   | method | rule |
   |---|---|
   | `clp01` | CLP01 = claim CLM01 |
   | `clp07` | CLP07 = claim REF*F8, or the payer claim number of a matched 277CA |
   | `patient_dos_amount` | same patient reference + service date + billed amount (CLP03 = CLM02) |
3. **Remit line -> claim line**, inside the matched claim; stored in `remit_line.match_method`.
   | method | rule |
   |---|---|
   | `line_exact` | CPT + modifiers + service date + units (a missing date or units on the remit is not compared) |
   | `line_cpt_mod` | CPT + modifiers, only when exactly one claim line fits |
4. **Remit -> payment** is set at ingest (the CLP sits under its BPR/TRN). M3 checks it: BPR02 must equal the sum of
   CLP04 less PLB amounts, and TRN02 must be present.

## Never guess
Several versions of one CLM01 (replacement, re-send): the latest `submitted_on` wins. Candidates with different CLM01
values are `ambiguous` and the row stays unmatched. Line position is not used.

## Unmatched reasons
Remits: `no_candidate`, `ambiguous`, `payer_mismatch` (CLM01 exists but under another payer),
`amount_mismatch` (patient + date found, billed amount differs). Lines: `claim_not_matched`, `no_candidate`, `ambiguous`.
