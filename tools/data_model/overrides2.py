R, D, P, G = "Renamed", "Derived", "Partial", "Gap"
X = {}


def add(old, rows):
    for col, tbl, new, lvl, note in rows:
        X[(old, col)] = (tbl, new, lvl, note)


add("fact_claim", [
    ("accident_related_code", "claim", "accident_related", R, ""),
    ("claim_content_hash", "claim", "", G, "no hash of the sent claim body is stored"),
    ("consent_flags", "claim", "", G, "consent flags are not stored on the claim"),
    ("filing_exception_code", "claim", "", G, "late-filing exception code has no column"),
    ("isa13", "claim", "batch_control_number", R, ""),
    ("target_send_date_key", "claim", "", G, "planned send date is not stored; submitted_date is the actual"),
    ("pos_key", "claim", "place_of_service_id", R, ""),
    ("service_date_key", "claim", "service_date_from", R, ""),
    ("status_key", "claim", "claim_status", R, ""),
    ("visit_ref", "claim", "encounter_id", R, "joined to encounter"),
])
add("fact_claim_line", [
    ("claim_submitter_id", "claim", "claim_number", R, "reached through claim_id"),
    ("frequency_code", "claim", "frequency_code", R, "kept on the claim"),
    ("pos_key", "claim", "place_of_service_id", R, "kept on the claim"),
    ("submitted_date_key", "claim", "submitted_date", R, "kept on the claim"),
])
add("fact_remit_line", [
    ("claim_status_key", "claim", "claim_status", R, "kept on the claim"),
    ("claim_submitter_id", "claim", "claim_number", R, "reached through claim_id"),
    ("payer_claim_control_number", "claim", "payer_claim_number", R, ""),
    ("payment_date_key", "payment", "payment_date", R, "reached through payment_id"),
    ("contract_expected", "claim_details", "expected_allowed", R, ""),
    ("match_method", "claim_details", "", G, "how the remit line was matched to the claim line is not stored"),
    ("underpayment_amount", "claim_details", "", D, "expected_allowed minus allowed_amount"),
])
add("fact_claim_status_event", [
    ("charge_amount", "claim", "total_charge", R, "kept on the claim"),
    ("claim_status_key", "claim_status_history", "status_code", R, ""),
    ("claim_submitter_id", "claim", "claim_number", R, "reached through claim_id"),
    ("paid_amount", "claim_status_history", "reported_paid_amount", R, ""),
    ("ack_code_key", "claim_status_history", "status_code", R, "999 and 277CA codes share status_code"),
    ("acked_control_ref", "claim_status_history", "acked_control_number", R, ""),
    ("event_ref", "claim_status_history", "response_sequence", P, "order is held; source file name is not"),
    ("rejection_owner_role_key", "claim_status_history", "owner_role", R, ""),
    ("seconds_since_sent", "claim_status_history", "event_ts", D, "event_ts minus claim.submitted_date"),
])
add("fact_remit_adjustment", [
    ("adjustment_amount", "transactions", "amount", R, ""),
    ("adjustment_quantity", "transactions", "", G, "adjustment quantity (CAS units) has no column"),
    ("line_number", "claim_details", "line_number", R, "reached through claim_detail_id"),
    ("payment_date_key", "payment", "payment_date", R, "reached through payment_id"),
    ("remark_code_key", "transactions", "", G, "transactions has no remark code column (remark_code reference table exists)"),
])
add("fact_visit", [
    ("total_time_minutes", "encounter", "visit_minutes", R, ""),
    ("visit_kind", "encounter", "encounter_type", R, ""),
    ("visit_status_key", "encounter", "encounter_status", R, ""),
    ("visit_type", "encounter", "encounter_type", R, ""),
])
add("fact_payment", [
    ("handling_code", "payment", "", G, "BPR handling code has no column"),
    ("payment_format_code", "payment", "payment_method", P, "method is held; the exact BPR format code is not"),
    ("plb_adjustment_total", "payment", "plb_amount", R, ""),
    ("trace_number", "payment", "payment_number", R, "restricted column"),
])
add("dim_payer", [
    ("corrected_filing_days", "payer", "corrected_claim_days", R, ""),
    ("filing_clock_start", "payer", "", G, "which date starts the filing clock is not stored"),
    ("payer_id_code", "payer", "payer_code", R, ""),
])
add("dim_patient", [
    ("age_band", "patient", "birth_year", D, "worked out from birth_year"),
    ("patient_ref_hash", "patient", "patient_number_hash", R, ""),
])
add("dim_coverage", [
    ("coverage_ref", "coverage", "coverage_id", R, ""),
    ("holder_ref_hash", "coverage", "subscriber_hash", R, ""),
])
add("dim_service_code", [
    ("code_set_version", "cpt_code", "effective_from", P, "yearly set is held through effective dates"),
    ("mue_adjudication_indicator", "cpt_code", "", G, "MUE indicator has no column"),
    ("mue_units_per_day", "cpt_code", "unit_limit_per_day", R, ""),
])
add("fact_charge_line", [
    ("charge_lag_days", "bill_details", "charge_entered_date", D, "charge_entered_date minus service_date"),
    ("charge_ref", "bill_details", "bill_detail_id", R, ""),
    ("entered_by_staff_key", "bill_details", "entered_by_role", P, "role is held, not the named person"),
    ("entered_date_key", "bill_details", "charge_entered_date", R, ""),
])
add("fact_claim_dx", [
    ("diagnosis_key", "claim_details", "primary_diagnosis_code_id", P, "principal and pointers are held; the full diagnosis list per claim is not"),
    ("dx_seq", "claim_details", "diagnosis_pointers", P, "pointers only"),
    ("onset_date_key", "claim", "", G, "onset date has no column"),
])
add("fact_eligibility_check", [
    ("check_date_key", "coverage", "last_verified_date", P, "latest check only; history is the planned eligibility_check table"),
    ("plan_begin_date_key", "coverage", "effective_date", P, "latest only"),
    ("is_aaa_reject", "coverage", "last_verified_status", P, "latest status only"),
    ("other_payer_key", "coverage", "coverage_order", P, "other coverage is another coverage row"),
    ("trace_number", "coverage", "", G, "271 trace number is not stored"),
])
add("fact_auth_request_line", [
    ("auth_request_ref", "authorization", "authorization_id", R, ""),
    ("payer_auth_number", "authorization", "authorization_number", R, "restricted column"),
    ("primary_diagnosis_key", "authorization", "diagnosis_code_id", R, ""),
    ("review_action_code", "authorization", "authorization_status", P, ""),
    ("units_requested", "authorization", "", G, "only units_approved and units_used are held"),
    ("valid_from_date_key", "authorization", "valid_from", R, ""),
    ("valid_to_date_key", "authorization", "valid_to", R, ""),
    ("channel_key", "authorization", "request_channel", R, ""),
    ("pos_key", "authorization", "", G, "place of service of the request is not stored (facility only)"),
    ("rule_key", "authorization", "", G, "which payer rule drove the request is not stored"),
    ("service_code_key", "authorization", "primary_cpt_code_id", R, ""),
    ("status_key", "authorization", "authorization_status", R, ""),
])
for c in ("deposit_amount", "deposit_date_key", "deposit_ref", "match_method", "trace_ref"):
    X[("fact_bank_deposit", c)] = ("payment", "", G, "bank side of the money (deposit) is not modelled; payment has only a reconciles flag")
add("fact_patient_balance_event", [
    ("claim_submitter_id", "claim", "claim_number", R, "reached through claim_id"),
    ("event_date_key", "transactions", "transaction_date", R, ""),
    ("event_type", "transactions", "transaction_type", R, ""),
    ("channel_key", "patient_statement", "", "Planned table", "statement channel belongs to the planned patient_statement table"),
    ("status_key", "patient_statement", "", "Planned table", "statement status belongs to the planned patient_statement table"),
])
add("dim_claim_status", [
    ("category_code", "claim_status_history", "status_category", R, ""),
    ("is_technical_reject", "claim_status_history", "is_technical", R, ""),
    ("entity_code", "claim_status_history", "", G, "status code list (labels, domain) is held as allowed values, not a table"),
    ("status_domain", "claim_status_history", "", G, "status code list (labels, domain) is held as allowed values, not a table"),
    ("status_label", "claim_status_history", "", G, "status code list (labels, domain) is held as allowed values, not a table"),
])
add("dim_finding_type", [
    ("finding_code", "agent_finding", "finding_type", R, ""),
    ("default_action_type_key", "agent_finding", "", G, "default action per finding type is configuration, not stored"),
    ("severity_rank", "agent_finding", "severity", P, ""),
])
for c in ("address_status", "authorized_rep", "autopay_enrolled", "guarantor_ref_hash", "has_phone", "opt_out",
          "preferred_channel_key", "preferred_language", "quiet_hours", "text_consent"):
    X[("dim_patient_contact", c)] = ("patient", "", G, "patient outreach preferences are not in the model (patient has language only)")
for c in ("decision_status_key", "dollar_difference", "final_code_key", "is_compliance_risk", "suggested_code_key", "suggested_dx_key"):
    X[("fact_coding_review_line", c)] = ("agent_finding", "", G, "suggested vs final code comparison is only free text in agent_finding.summary")

add("fact_appointment", [("status_key", "appointment", "appointment_status", R, "")])
add("fact_charge_line", [("status_key", "bill_details", "line_status", R, ""),
                         ("supervising_provider_key", "encounter", "supervising_provider_id", R, "kept on the encounter"),
                         ("laterality", "encounter_details", "laterality", R, "kept on the encounter detail")])
add("fact_visit", [("service_date_key", "encounter", "encounter_date", R, "")])
add("fact_eligibility_check", [("service_date_key", "eligibility_check", "", "Planned table", "planned eligibility_check table"),
                               ("is_active", "eligibility_check", "", "Planned table", "planned eligibility_check table")])
add("dim_provider", [("tax_id", "practice", "tax_id", R, "tax ID is held at practice level")])
add("fact_plb_adjustment", [("reason_code", "transactions", "adjustment_reason_id", R, "")])
add("dim_adjustment_reason", [("description", "adjustment_reason", "short_label", R, "")])
add("dim_contract_rate", [("effective_date", "contract_rate", "effective_from", R, ""), ("end_date", "contract_rate", "effective_to", R, "")])
add("fact_payment", [("channel_key", "payment", "payment_source", P, "source of the payment is held; channel is not split out")])
add("fact_posting", [("claim_submitter_id", "claim", "claim_number", R, "reached through claim_id"),
                     ("posted_amount", "transactions", "amount", R, "")])
add("fact_bank_deposit", [("channel_key", "payment", "", G, "bank side of the money (deposit) is not modelled; payment has only a reconciles flag")])
