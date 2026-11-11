# KrisnnAI data model R2: questions about the new tables

Your R2 dictionary has 85 tables; ours has 59. Of the 38 names we don't have, 10 are renames of our tables, so 28 are new. Each new table adds columns, a loader, tests and synthetic data, so we want to add the ones that earn their place and phase the rest. Please answer in plain words; one or two lines each is enough.

## A. Answer for every new table (one row per table in the grid at the end)

1. **Need:** What breaks or cannot be measured without it? (Give one concrete question the business could not answer today.)
2. **Consumer:** Which agent (A1 to A10), metric or report reads it? If none, say "none yet".
3. **Source:** Which source (837, 835, 270/271, 277CA, PM export, our own) fills it? Is that source available in the shadow-mode pilot?
4. **Phase:** Needed for the shadow pilot, needed before go-live, or later?
5. **Alternative:** Could a column on an existing table do the job? Why is a table better?

## B. Questions by group

**Diagnoses and authorizations** (claim_diagnosis, encounter_diagnosis, authorization_line)
- Do payers deny on diagnosis pointers 2 to 12 often enough to justify claim_diagnosis, or is the principal diagnosis plus four per line enough?
- encounter_diagnosis, claim_diagnosis and the line diagnosis columns now hold the same facts. Which one is the source of truth?
- How common are authorizations with several codes in the practices we expect? Is one row per authorization with a codes list enough for the pilot?

**Payers and contracts** (payer_plan, payer_contract, payer_identifier, fee_schedule)
- Do we have real cases where rules or contracts differ by plan inside one payer? Which payers?
- Who maintains payer_contract, and from what? Contracts are usually PDFs. Will a person key them in?
- Which clearinghouse and payer IDs differ in the data we will actually receive?
- Is fee_schedule a header with one version at a time, or do we need history of fee changes from day one?

**Money** (remittance_claim, bank_deposit, guarantor, collection_placement)
- Is remittance_claim needed beyond what the payment, ledger and denial tables carry? Which fields (CLP status 22, crossover, MIA/MOA) have no home today?
- Do the practices give us bank data at all? If not, bank_deposit would stay empty.
- Is guarantor in scope while we are only reading claims? Do patient balances matter for the pilot agents?
- Are collections in scope for the first release?

**Claim quality** (claim_edit, claim_status_code)
- Which system produces the edits (PM scrubber, clearinghouse, our agent)? Do we get them as data, or only the final result?
- Does clean-claim rate need a table, or can it come from claim_status_history?

**Patients, eligibility and estimates** (patient_estimate, patient_estimate_line, eligibility_benefit, appointment_status_log)
- Are good faith estimates in scope? They apply to self-pay patients; which agent uses them?
- Which benefit lines from a 271 do agents need? Is the summary on eligibility_check not enough?
- Do the PM systems we connect to export appointment status changes as events, or only the current status?

**Providers and enrollment** (provider_identifier, provider_practice, edi_enrollment)
- Do we expect providers across several practices in one tenant in the pilot?
- Who owns credentialing data? Is this our job or the PM's? How does it differ from the existing enrollment table?
- Which agent acts on a missing ERA or EFT enrollment?

**Replacing comma lists and codes** (document_element, claim_attachment_document, ndc_code)
- Are drug claims in scope for the pilot practices? If not, can ndc_code wait?
- For documents, do we get named elements from the EHR, or would we infer them?

**Data operations** (tenant, load_batch, edi_file, data_quality_result, access_audit)
- tenant: does it replace the practice table, or sit above it? Which tables use the composite key (tenant_id, id)?
- load_batch and edi_file: do they replace what data_feed holds, or sit beside it?
- access_audit: who writes it, the database or the application? What must it capture for HIPAA?
- data_quality_result: which rules, and who reads the results?

## C. Changes to existing tables

1. You removed `known_at` and `is_reconstructed` from 152 columns. Our rule 9 requires replay "as of a time, using only data known then". How do we compute that with `loaded_at` and `modified_at` alone? What about late-arriving data and rows we rebuilt?
2. You removed `appointment.specialty_id`, `copay_due`, `eligibility_state`, `reschedule_count` and `cancel_reason`. Where do these live now? Our live simulator and replay agents read some of them.
3. The renames (`transactions` to `ledger_entry`, `*_details` to `*_line`, `ar` to `ar_snapshot`, `order` to `clinical_order`) change every query. Are they worth doing now, or can we keep the old names and add views?
4. The composite key `(id, version)` on 34 tables makes every foreign key two columns. What problem does it solve that `id` plus `is_current` did not?
5. You added `claim` columns for 837 (service_date_to, referral_number, supervising_provider_id and others). Which are required by the payers we will hit first?
6. Open items in your file: Agent A1 is not credited under "Wanted by", and 837I (institutional) is out of scope. Do you want either fixed in R2 or R3?

## D. Process

1. Did you start from our 57-table version? We have since added `resource` and `resource_allocation` (88 resources, 67,110 allocations); please keep them.
2. Who reviewed R2 on the business side? Which real PM or clearinghouse formats did you check it against?
3. If we can only add ten tables first, which ten do you pick?

## Grid (one row per table)

| Table | Need | Consumer | Source | Phase | Alternative |
|---|---|---|---|---|---|
| claim_diagnosis | | | | | |
| encounter_diagnosis | | | | | |
| authorization_line | | | | | |
| payer_plan | | | | | |
| payer_contract | | | | | |
| payer_identifier | | | | | |
| fee_schedule | | | | | |
| remittance_claim | | | | | |
| bank_deposit | | | | | |
| guarantor | | | | | |
| collection_placement | | | | | |
| claim_edit | | | | | |
| claim_status_code | | | | | |
| patient_estimate | | | | | |
| patient_estimate_line | | | | | |
| eligibility_benefit | | | | | |
| appointment_status_log | | | | | |
| provider_identifier | | | | | |
| provider_practice | | | | | |
| edi_enrollment | | | | | |
| document_element | | | | | |
| claim_attachment_document | | | | | |
| ndc_code | | | | | |
| tenant | | | | | |
| load_batch | | | | | |
| edi_file | | | | | |
| data_quality_result | | | | | |
| access_audit | | | | | |
