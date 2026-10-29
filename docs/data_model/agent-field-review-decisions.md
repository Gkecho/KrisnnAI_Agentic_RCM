# Gap decisions (applied to gen_final.py at the end of the walk-through)
## claim  (approved)
- ADD claim.signature_on_file (Optional, Yes/No/Unknown) -- from consent_flags
- ADD claim.onset_date (Optional) -- from onset_date_key
- ADD claim.late_filing_reason (Optional) -- from filing_exception_code
- DROP claim_content_hash (covered by claim_id per version + agent_decision.input_hash)
- DROP target_send_date (use agent_task.due_date)
## claim_details  (proposed)
- match_method -> Derived: transactions.claim_detail_id blank = unmatched
- unit_basis -> Derived from cpt_code.is_timed
- ndc_code -> RENAMED to claim_details.drug_code / drug_units (false gap)
- line_indicators -> RENAMED to claim_details.line_flags (false gap)
## claim_details -- APPROVED as proposed (no model change)
## claim_status_history (approved)
- status_domain -> RENAMED to event_type (ack_999 / ack_277ca)
- transaction_set -> DROP (always 837 on this table)
- ack_code -> status_code; TWEAK description: for ack_999 events status_code holds A / E / R
- entity_code -> DROP
- status_label -> no column; looked up from the status code list (Allowed values)
## transactions (APPROVED)
- event_ref, posting_ref -> RENAMED transactions.transaction_number
- payment_trace -> RENAMED transactions.payment_number (via payment)
- days_to_post -> DERIVED posted_date minus payment.payment_date
- adjustment_quantity -> use denial.units_denied for denials; drop for other adjustments
- reference_id (PLB03) -> DROP (payment.plb_amount holds the total; reference stays in raw 835)
- remark_code_key -> ADD transactions.remark_code_id (Optional, FK remark_code)

## payment -- DECISION: bank deposit feed REMOVED from Bookkeeper (A11) and Captain (A14); no payment columns added
- 38 rows removed, 8 rows to reword (see Remapped sheet, Result = Removed / note REWORD)
## payment (APPROVED)
- handling_code (BPR01) -> no new column; non-payment handling kept via payment_method + has_remittance
## authorization (APPROVED)
- ADD authorization.units_requested (Optional)
- ADD authorization.place_of_service_id (Optional, FK place_of_service)
- rule_key -> covered by agent_decision_details (rule_code, check_result); no column
## coverage (APPROVED)
- trace_number -> no column on coverage; goes to planned eligibility_check table (note on TBD sheet); derivable as TRG + appointment id (-2 secondary)
## reference tables (APPROVED)
- adjustment_reason.disposition -> RENAMED suggested_action; is_denial -> RENAMED reason_class (denial vs contractual)
- contract_rate: contract_ref -> contract_number; multi_proc_reduction_pct -> multi_procedure_reduction_pct; extraction_confidence -> confidence (+ is_inferred)  (all RENAMED)
- ADD cpt_code.unit_limit_basis (Optional: per line / per day / per date of service) from mue_adjudication_indicator
- diagnosis_code.parent_icd10_code -> DERIVED (rows whose parent_code = this code)
- facility.facility_ref -> RENAMED facility_number
- ADD payer.filing_clock_basis (Optional: service date / discharge date / claim received ...) from filing_clock_start
- data_feed.system_code (ISA sender/receiver ids) -> practice_settings, not data_feed
## patient (default taken: planned table, not columns on patient)
- preferred_language -> RENAMED patient.language
- NEW TBD TABLE patient_contact_preference (Phase 3, with Concierge): preferred_channel, quiet_hours, address_status (flag), has_phone (flag), text_consent, opt_out, authorized_rep, guarantor_hash; no phone numbers or addresses stored
- autopay_enrolled -> planned payment_plan TBD table
## ALL REMAINING (agent_decision, agent_finding, agent_task): applied in one go with defaults (user: "fix all together once")
- 23 optional columns added in total + status_code description change; see gap_block.py. gen_final.py, model.json, Excel, HTML and remap workbook rebuilt.
## planned-table review (APPROVED, all locked)
- 16 new tables designed by 4 agents (A value/forecast, B document/clinical, C rules/enrollment/eligibility/staff/calendar, D appeal/patient billing); estimate and encounter_diagnosis not needed
- 3 locked-table changes applied: referral_id on appointment + encounter; payer_rule_id on agent_decision_details; approver/assignee columns relinked to staff_id (transactions.approved_by, bill_details.change_approved_by, practice_settings.approved_by, agent_approval.approved_by, agent_task.assigned_to)
- 57 tables, 1,595 columns, all Locked
