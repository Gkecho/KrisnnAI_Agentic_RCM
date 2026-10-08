# Ingestion spec (M2)

`krisnai ingest PATH --tenant ID` loads a file, or every X12 / fee-schedule CSV under a folder.

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
