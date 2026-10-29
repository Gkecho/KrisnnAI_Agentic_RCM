# Ingestion spec (M2)

`krisnnai ingest PATH --tenant ID` loads a file, or every X12 / fee-schedule CSV under a folder.

## Flow per file
1. SHA-256 of the bytes. If the tenant already has that hash: **skipped** (idempotent).
2. Parse with no DB writes. Any structural problem raises `X12Error`: the file is stored as `failed`
   with the reason and nothing else is written.
3. One transaction: `source_file` -> `event` rows -> normalized rows. Rolled back on any error.
4. If every transaction was already loaded from another file (same ISA13/GS06/ST02 and identical
   content), the file is **skipped** ("re-sent file").

## Envelope checks
ISA is 106 characters with 16 elements; delimiters are read from it (element = char 4, component = char
105, terminator = char 106). SE01 must equal the ST..SE segment count and SE02 = ST02; GE01/GE02 must match
the group; IEA01/IEA02 must match the interchange. Unsupported sets (anything but 837, 835, 999, 277) fail.

## Events (one row per fact, append-only)
| event_type | one per | normalized into |
|---|---|---|
| `837P.claim` | CLM | claim, claim_line, claim_dx |
| `835.payment` | BPR/TRN (+PLB) | payment, plb_adjustment |
| `835.remit` | CLP | remit, remit_line, adjustment, remit_remark |
| `999.ack` | AK2..IK5 | ack_999 |
| `277CA.claim_status` | STC | ack_277ca |

`payload` is the parsed record as JSON with patient identifiers already hashed. Fee-schedule CSVs
(`payer_id,cpt,modifier,allowed_amount,effective_date[,end_date]`) load into `fee_schedule` with lineage to
`source_file` only (no events).

## Patients
`patient_hash = SHA-256(salt | MEMBER_ID upper-cased)`, salt from the environment variable named by
`tenant.patient_salt_key`. 837 uses NM1*IL, 835 uses NM1*QC (member id, else last|first). Dependents share their
subscriber's reference in the 837 (known limitation).

## Element map
Each column's X12 source is in `docs/data_model.md`. CAS is read as (reason, amount, quantity) triplets;
claim-level CAS (before the first SVC) has `remit_line_id` NULL. PLB is read from the trailer after the last
claim.

## Not done here
Matching claim to remit (M3, `match_method` stays NULL), KPIs (M4), 837I/837D, 270/271.

## Valley Wellness loader (`krisnnai load-valley`)
Source: the fabricated PostgreSQL database `valleywellnessedi` (read-only session; Valley is never written).
`--files N` loads the first N 837P files (about 860 claims each, ordered by file name) plus the 835 files that
remit those claims (`--max-remit-files`, default 500). Each Valley source file becomes one `source_file`
(fingerprint `valley:<type>:<source_file>`), so reloading is a no-op.

| KrisnnAI | Valley table(s) | Join |
|---|---|---|
| claim | edi_837p_claims + _header (control numbers) | per source_file |
| provider / payer / patient | _billing_provider, _payer, _subscriber | billing_hl_id / subscriber_hl_id |
| claim_line, claim_dx | _service_lines, _diagnosis_codes | (source_file, claim_number) |
| payment, plb | edi_835_payment_header, _payer, _provider_adjustments | one payment per source_file |
| remit, remit_line | edi_835_claims, _service_payments | (source_file, claim_number, line_seq) |
| adjustment, remark | edi_835_adjustments (reason, RARC) | line_seq (all Valley adjustments are line level) |
| allowed amount | edi_835_amounts qualifier B6 | line_seq |
| patient hash | edi_835_claim_parties role QC (835), subscriber member_id (837) | same salted hash |

Valley stores amounts and dates as text. Conversion is exact (`Decimal`, CCYYMMDD); a row that cannot be converted
or joined is skipped and counted in the report, never guessed. Orphan remits (835 claims with no 837 claim loaded)
are kept, since leakage analysis needs them.

First live check (1 837P file, 11 remit files): 10 claims, 103 remits, 201 remit lines; every line balances
(charge = paid + adjustments), every remit's totals equal its lines, and each payment equals the sum of its
claim payments less its PLB.
