# Synthea CSV to R2 tables

Source: Synthea CSV export (Texas, seed 20261102, 3 years of history), headers read from the real files in `tools/synthea/output/csv`. Target: the R2 model in `krisnnai_r2` on AWS RDS.
Synthea is clinical-first. It gives people, visits, diagnoses, procedures, coverage periods and a billing ledger per claim. It does not give ICD-10, CPT, modifiers, payer adjudication detail (CARC/RARC), denials, appeals, appointments, authorizations or notes. Those come from our own generator on top.

## Direct mappings

| Synthea file | R2 table(s) | How |
|---|---|---|
| patients.csv | `patient`, `guarantor` | `Id` → hashed `patient_number_hash` (never store the id); `BIRTHDATE` → `birth_year` and `is_age_90_plus`; `GENDER` → `sex`; `STATE`; `DEATHDATE` → `is_active`. Name, SSN, address, driver's licence and passport are dropped. One guarantor per patient (adults) or per parent (children). |
| organizations.csv | `practice`, `facility` | One practice for the tenant; each organization becomes a facility (`ADDRESS` state, `STATE`). |
| providers.csv | `provider`, `provider_practice` | `Id` → `provider_number`; `NAME` → `provider_name`; `SPECIALITY` → `specialty` and `specialty_id`; `ORGANIZATION` → `practice_id` and `provider_practice`. NPI is generated (Synthea has none). |
| payers.csv | `payer`, `payer_plan`, `payer_identifier` | `NAME` → `payer_name`; ownership → `payer_type` (Medicare, Medicaid, commercial, self-pay for NO_INSURANCE). Filing and appeal days from our payer defaults. |
| payer_transitions.csv | `coverage` | One row per period: `START_DATE` → `effective_date`; `END_DATE` → `termination_date`; `MEMBERID` → hashed `member_number_hash`; `PAYER` → `payer_id`; `SECONDARY_PAYER` → a second coverage row with `coverage_order` 2; `OWNER_NAME` and `PLAN_OWNERSHIP` → `relationship_to_holder`. |
| encounters.csv | `encounter`, `appointment`, `appointment_status_log` | `START` → `encounter_date`; `PATIENT`, `PROVIDER`, `ORGANIZATION` → patient, rendering provider, facility; `PAYER` → `payer_id` and `coverage_id` (the coverage active on the date); `ENCOUNTERCLASS` → `encounter_type` and `place_of_service_id` (ambulatory 11, wellness 11, outpatient 22, urgentcare 20, emergency 23, inpatient 21). `TOTAL_CLAIM_COST` → expected total. Appointments are derived: one per ambulatory, wellness and outpatient encounter. |
| conditions.csv | `encounter_diagnosis`, `diagnosis_code` | `ENCOUNTER` → encounter; `CODE` (SNOMED) → crosswalk to ICD-10 (see gaps). First diagnosis by `START` → `is_principal`. |
| procedures.csv | `encounter_line`, `cpt_code` | `ENCOUNTER`; `CODE` (SNOMED) → crosswalk to CPT; `BASE_COST` → `expected_charge`; `START` → `service_date`. |
| claims.csv | `bill`, `claim`, `claim_diagnosis` | `Id` → `claim_number`; `PATIENTID`, `PROVIDERID`; `PRIMARYPATIENTINSURANCEID` → coverage; `SERVICEDATE` → `service_date_from` and `service_date_to`; `DIAGNOSIS1..8` → `claim_diagnosis` positions 1 to 8; `SUPERVISINGPROVIDERID`, `REFERRINGPROVIDERID`; `STATUS1/2/P` and `OUTSTANDING1/2/P` → `claim_status`, `balance`, `claim_sequence`; `LASTBILLEDDATE1` → `submitted_date`; `APPOINTMENTID` links the appointment. |
| claims_transactions.csv | `bill_line`, `claim_line`, `ledger_entry` | `TYPE` CHARGE → `bill_line` and `claim_line` (`PROCEDURECODE` → CPT, `UNITS`, `UNITAMOUNT` → `fee_per_unit`, `MODIFIER1/2`, `DIAGNOSISREF1..4` → `diagnosis_pointers`, `FEESCHEDULEID`); `TYPE` PAYMENT → ledger payment (`METHOD` → `payment_method`, `PATIENTINSURANCEID` says payer or patient → `responsible_party`); `TYPE` ADJUSTMENT → ledger adjustment; `TYPE` TRANSFERIN/TRANSFEROUT → transfer between payer and patient (`TRANSFERTYPE`); `AMOUNT` → `amount`; `OUTSTANDING` → `balance_effect`. |
| medications.csv | none for now | Pharmacy is outside this model. Keep for `ndc_code` and drug lines later. |
| observations.csv, immunizations.csv, allergies.csv, careplans.csv, devices.csv, imaging_studies.csv, supplies.csv | none | Clinical only. Imaging studies could feed `clinical_order` later. Observations are the largest file (about 1.9M rows at 8,500 patients); skip them. |

## What Synthea cannot fill (our generator adds it)

| R2 table or column | Why |
|---|---|
| `diagnosis_code.icd10_code`, `cpt_code.code` | Synthea uses SNOMED for conditions and procedures. We need a SNOMED to ICD-10 and SNOMED to CPT crosswalk. The 20 to 40 most common codes are enough: map those, drop or remap the rest. |
| `claim_line.modifier_*`, `place_of_service` quality | Synthea gives few modifiers. Our rules (25, GP/GO, RT/LT) are added by the generator. |
| `denial`, `denial_reason`, `appeal`, `adjustment_reason`, `remittance_claim` | Synthea has payments and adjustments but no CARC/RARC and no denials. Our money stage plants them. |
| `authorization`, `authorization_line`, `referral` | Not modelled. Generated for the payers that require them. |
| `eligibility_check`, `eligibility_benefit`, `appointment` details, notes and signing | Not modelled. Generated. |
| `agent_*` tables | Written by the agents, never loaded. |
| `load_batch`, `edi_file`, `tenant`, `access_audit`, `data_quality_result` | Written by the loader. |

## Load order

1. `tenant`, `practice`, reference tables (specialty, place_of_service, payer, payer_plan, diagnosis_code, cpt_code).
2. `provider`, `facility`, `provider_practice`, `guarantor`.
3. `patient`, `coverage`.
4. `appointment`, `encounter`, `encounter_diagnosis`, `encounter_line`.
5. `bill`, `bill_line`, `claim`, `claim_diagnosis`, `claim_line`.
6. `ledger_entry`.
7. Our generator: authorization, eligibility, denials, appeals, remittance, and so on.

## Known risks

- Synthea claims have no CPT: expect many encounters to map to a generic E/M code unless the crosswalk is wide.
- `PROCEDURECODE` in claims_transactions is mostly SNOMED, not CPT.
- Patients with `NO_INSURANCE` become self-pay: no claim in R2, only a bill.
- Dates run to the day Synthea ran; shift them if we want the history to end on 2026-11-02.
- IDs are UUIDs: map each to our own integer keys at load, keep a lookup, and never store the UUID in a column.
