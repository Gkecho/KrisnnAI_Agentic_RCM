A, R, D, DR, PL, PA = "Added", "Renamed", "Derived", "Dropped", "Planned table", "Partial"
# old column -> (final table, final column, result, note)   decisions approved table by table
DEC = {
 "disposition": ("adjustment_reason", "suggested_action", R, ""), "is_denial": ("adjustment_reason", "reason_class", R, "code 45 is contractual, not a denial"),
 "verification_condition": ("agent_decision", "recheck_condition", A, "added in review"), "prompt_hash": ("agent_decision", "prompt_hash", A, "added in review"),
 "action_type": ("agent_decision", "decision_type", R, ""), "event_key": ("agent_decision", "entity_id", PA, "entity is held; source file lineage is the data_feed registry"),
 "suggested_code_key": ("agent_finding", "suggested_value", A, "added in review"), "suggested_dx_key": ("agent_finding", "suggested_value", A, "added in review"),
 "default_action_type_key": ("agent_finding", "", DR, "configuration, not data"), "is_compliance_risk": ("agent_finding", "is_compliance_risk", A, "added in review"),
 "dollar_difference": ("agent_finding", "value_difference", A, "added in review"), "decision_status_key": ("agent_decision", "human_outcome", R, ""),
 "final_code_key": ("agent_finding", "final_value", A, "added in review"), "predicted_denial_probability": ("agent_finding", "predicted_probability", A, "added in review"),
 "predicted_reason_key": ("agent_finding", "predicted_reason_category", A, "added in review"), "simulated_outcome": ("agent_decision", "outcome", R, ""),
 "simulated_allowed_amount": ("agent_finding", "predicted_allowed_amount", A, "added in review"),
 "simulated_patient_responsibility": ("agent_finding", "predicted_patient_responsibility", A, "added in review"),
 "minutes_spent": ("agent_task", "minutes_spent", A, "added in review"), "channel_key": ("agent_task", "contact_channel", A, "added in review"),
 "escalation_level": ("agent_task", "escalation_level", A, "added in review"), "reminder_count": ("agent_task", "reminder_count", A, "added in review"),
 "units_requested": ("authorization", "units_requested", A, "added in review"), "pos_key": ("authorization", "place_of_service_id", A, "added in review"),
 "rule_key": ("agent_decision_details", "rule_code", R, ""), "consent_flags": ("claim", "signature_on_file", A, "added in review"),
 "onset_date_key": ("claim", "onset_date", A, "added in review"), "filing_exception_code": ("claim", "late_filing_reason", A, "added in review"),
 "claim_content_hash": ("claim", "", DR, "covered by claim_id per version and agent_decision.input_hash"), "target_send_date_key": ("agent_task", "due_date", R, "a deadline for a work item"),
 "match_method": ("claim_details", "", D, "transactions with no claim_detail_id are unmatched"), "unit_basis": ("cpt_code", "is_timed", D, ""),
 "ndc_code": ("claim_details", "drug_code", R, ""), "line_indicators": ("claim_details", "line_flags", R, ""),
 "transaction_set": ("claim_status_history", "", DR, "always 837 on this table"), "ack_code": ("claim_status_history", "status_code", R, "A / E / R for ack_999"),
 "entity_code": ("claim_status_history", "", DR, "no reporting use"), "status_label": ("claim_status_history", "", DR, "looked up from the status code list"),
 "status_domain": ("claim_status_history", "event_type", R, ""), "contract_ref": ("contract_rate", "contract_number", R, ""),
 "multi_proc_reduction_pct": ("contract_rate", "multi_procedure_reduction_pct", R, ""), "extraction_confidence": ("contract_rate", "confidence", R, ""),
 "trace_number": ("eligibility_check", "", PL, "270/271 trace goes to the planned eligibility_check table"),
 "mue_adjudication_indicator": ("cpt_code", "unit_limit_basis", A, "added in review"), "system_code": ("practice_settings", "", R, "connection setting, moved to practice_settings"),
 "parent_icd10_code": ("diagnosis_code", "parent_code", D, "children are rows naming this code as parent"), "facility_ref": ("facility", "facility_number", R, ""),
 "preferred_language": ("patient", "language", R, ""), "filing_clock_start": ("payer", "filing_clock_basis", A, "added in review"),
 "handling_code": ("payment", "", D, "payment_amount 0 / has_remittance"), "event_ref": ("transactions", "transaction_number", R, ""),
 "posting_ref": ("transactions", "transaction_number", R, ""), "remark_code_key": ("transactions", "remark_code_id", A, "added in review"),
 "adjustment_quantity": ("denial", "units_denied", PA, "denials only"), "reference_id": ("transactions", "", DR, "stays in the raw 835"),
 "payment_trace": ("transactions", "payment_number", R, ""), "days_to_post": ("transactions", "posted_date", D, "posted_date minus payment_date"),
}
for c in ("preferred_channel_key", "quiet_hours", "address_status", "has_phone", "text_consent", "opt_out", "guarantor_ref_hash", "authorized_rep"):
    DEC[c] = ("patient_contact_preference", "", PL, "planned table, flags only")
DEC["autopay_enrolled"] = ("payment_plan", "", PL, "planned table")
