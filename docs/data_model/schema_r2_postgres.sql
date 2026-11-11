-- KrisnnAI R2 (PostgreSQL). Generated from docs/data_model/r2_model.json by tools/data_model/build_r2_sql.py. Do not edit by hand.
CREATE TABLE "appointment" (
    "appointment_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "appointment_number" VARCHAR(50) NOT NULL,
    "practice_id" INT NOT NULL,
    "patient_id" BIGINT NOT NULL,
    "appointment_date" DATE NOT NULL,
    "appointment_status" VARCHAR(20) NOT NULL,
    "provider_id" INT NULL,
    "payer_id" INT NULL,
    "coverage_id" BIGINT NULL,
    "facility_id" INT NULL,
    "start_time" TIME(0) NULL,
    "booked_date" DATE NULL,
    "appointment_type" VARCHAR(20) NULL,
    "booked_via" VARCHAR(20) NULL,
    "referring_provider_id" INT NULL,
    "referral_id" BIGINT NULL,
    "version" SMALLINT NOT NULL,
    "is_current" BOOLEAN NOT NULL,
    "previous_appointment_id" BIGINT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_appointment" PRIMARY KEY ("appointment_id", "version")
);
CREATE TABLE "appointment_status_log" (
    "appointment_status_log_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "appointment_id" BIGINT NOT NULL,
    "from_status" VARCHAR(20) NULL,
    "to_status" VARCHAR(20) NOT NULL,
    "status_changed_at" TIMESTAMP(0) NOT NULL,
    "changed_by_staff_id" INT NULL,
    "change_channel" VARCHAR(15) NULL,
    "reason_code" VARCHAR(30) NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_appointment_status_log" PRIMARY KEY ("appointment_status_log_id")
);
CREATE TABLE "referral" (
    "referral_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "referral_number" VARCHAR(50) NOT NULL,
    "practice_id" INT NULL,
    "patient_id" BIGINT NOT NULL,
    "coverage_id" BIGINT NULL,
    "payer_id" INT NULL,
    "referring_provider_id" INT NOT NULL,
    "referred_to_provider_id" INT NULL,
    "specialty_id" INT NULL,
    "referral_status" VARCHAR(15) NOT NULL,
    "request_date" DATE NULL,
    "received_date" DATE NULL,
    "valid_from" DATE NULL,
    "valid_to" DATE NULL,
    "visits_allowed" SMALLINT NULL,
    "visits_used" SMALLINT NULL,
    "diagnosis_code_id" INT NULL,
    "cpt_code_id" INT NULL,
    "authorization_id" BIGINT NULL,
    "document_id" BIGINT NULL,
    "version" SMALLINT NOT NULL,
    "is_current" BOOLEAN NOT NULL,
    "previous_referral_id" BIGINT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_referral" PRIMARY KEY ("referral_id", "version")
);
CREATE TABLE "appointment_line" (
    "appointment_line_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "appointment_id" BIGINT NOT NULL,
    "line_number" SMALLINT NOT NULL,
    "practice_id" INT NULL,
    "patient_id" BIGINT NULL,
    "payer_id" INT NULL,
    "provider_id" INT NULL,
    "specialty_id" INT NULL,
    "planned_cpt_code_id" INT NULL,
    "is_inferred" BOOLEAN NOT NULL,
    "planned_units" DECIMAL(7,2) NULL,
    "expected_charge" DECIMAL(12,2) NULL,
    "expected_allowed" DECIMAL(12,2) NULL,
    "auth_required" VARCHAR(10) NULL,
    "authorization_id" BIGINT NULL,
    "planned_diagnosis_code_id" INT NULL,
    "planned_provider_id" INT NULL,
    "room_or_equipment" VARCHAR(50) NULL,
    "duration_minutes" SMALLINT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_appointment_line" PRIMARY KEY ("appointment_line_id")
);
CREATE TABLE "appointment_slot" (
    "appointment_slot_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "practice_id" INT NOT NULL,
    "provider_id" INT NOT NULL,
    "slot_date" DATE NOT NULL,
    "start_time" TIME(0) NOT NULL,
    "duration_minutes" SMALLINT NOT NULL,
    "slot_status" VARCHAR(10) NOT NULL,
    "slot_number" VARCHAR(50) NULL,
    "facility_id" INT NULL,
    "specialty_id" INT NULL,
    "slot_type" VARCHAR(15) NULL,
    "appointment_id" BIGINT NULL,
    "created_date" DATE NULL,
    "room_or_resource" VARCHAR(50) NULL,
    "is_overbook" BOOLEAN NULL,
    "version" SMALLINT NOT NULL,
    "is_current" BOOLEAN NOT NULL,
    "previous_appointment_slot_id" BIGINT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_appointment_slot" PRIMARY KEY ("appointment_slot_id", "version")
);
CREATE TABLE "eligibility_check" (
    "eligibility_check_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "trace_number" VARCHAR(30) NOT NULL,
    "check_sequence" SMALLINT NOT NULL,
    "appointment_id" BIGINT NULL,
    "coverage_id" BIGINT NOT NULL,
    "patient_id" BIGINT NULL,
    "payer_id" INT NULL,
    "practice_id" INT NULL,
    "is_secondary" BOOLEAN NULL,
    "check_date" DATE NOT NULL,
    "check_ts" TIMESTAMP(0) NULL,
    "service_date" DATE NOT NULL,
    "service_type_code" VARCHAR(5) NULL,
    "is_active" BOOLEAN NULL,
    "is_aaa_reject" BOOLEAN NOT NULL,
    "aaa_reason_code" VARCHAR(5) NULL,
    "plan_begin_date" DATE NULL,
    "plan_end_date" DATE NULL,
    "copay_amount" DECIMAL(12,2) NULL,
    "coinsurance_pct" DECIMAL(5,4) NULL,
    "coverage_level" VARCHAR(20) NULL,
    "network_indicator" CHAR(1) NULL,
    "deductible_remaining" DECIMAL(12,2) NULL,
    "deductible_total" DECIMAL(12,2) NULL,
    "oop_max" DECIMAL(12,2) NULL,
    "oop_remaining" DECIMAL(12,2) NULL,
    "other_payer_id" INT NULL,
    "auth_required_hint" BOOLEAN NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_eligibility_check" PRIMARY KEY ("eligibility_check_id")
);
CREATE TABLE "patient_estimate" (
    "patient_estimate_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "estimate_number" VARCHAR(50) NULL,
    "patient_id" BIGINT NOT NULL,
    "appointment_id" BIGINT NULL,
    "coverage_id" BIGINT NULL,
    "estimate_type" VARCHAR(20) NOT NULL,
    "estimate_date" DATE NOT NULL,
    "service_date" DATE NULL,
    "estimated_total" DECIMAL(12,2) NOT NULL,
    "estimated_patient_amount" DECIMAL(12,2) NOT NULL,
    "delivered_channel" VARCHAR(10) NULL,
    "delivered_date" DATE NULL,
    "actual_billed_amount" DECIMAL(12,2) NULL,
    "exceeds_gfe_by_400" BOOLEAN NULL,
    "practice_id" INT NULL,
    "version" SMALLINT NOT NULL,
    "is_current" BOOLEAN NOT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_patient_estimate" PRIMARY KEY ("patient_estimate_id", "version")
);
CREATE TABLE "eligibility_benefit" (
    "eligibility_benefit_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "eligibility_check_id" BIGINT NOT NULL,
    "benefit_sequence" SMALLINT NOT NULL,
    "eligibility_code" VARCHAR(2) NOT NULL,
    "coverage_level" VARCHAR(20) NULL,
    "service_type_code" VARCHAR(3) NULL,
    "insurance_type_code" VARCHAR(3) NULL,
    "plan_description" VARCHAR(50) NULL,
    "time_period_code" VARCHAR(2) NULL,
    "benefit_amount" DECIMAL(12,2) NULL,
    "benefit_pct" DECIMAL(5,4) NULL,
    "quantity_qualifier" VARCHAR(2) NULL,
    "quantity" DECIMAL(9,2) NULL,
    "auth_required" VARCHAR(10) NULL,
    "network_indicator" CHAR(1) NULL,
    "cpt_code_id" INT NULL,
    "patient_id" BIGINT NULL,
    "payer_id" INT NULL,
    "practice_id" INT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_eligibility_benefit" PRIMARY KEY ("eligibility_benefit_id")
);
CREATE TABLE "patient_estimate_line" (
    "patient_estimate_line_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "patient_estimate_id" BIGINT NOT NULL,
    "line_number" SMALLINT NOT NULL,
    "cpt_code_id" INT NOT NULL,
    "modifier_id" INT NULL,
    "diagnosis_code_id" INT NULL,
    "provider_id" INT NULL,
    "facility_id" INT NULL,
    "is_co_provider_item" BOOLEAN NULL,
    "units" DECIMAL(9,2) NOT NULL,
    "expected_charge" DECIMAL(12,2) NOT NULL,
    "expected_patient_amount" DECIMAL(12,2) NULL,
    "appointment_line_id" BIGINT NULL,
    "billed_amount" DECIMAL(12,2) NULL,
    "practice_id" INT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_patient_estimate_line" PRIMARY KEY ("patient_estimate_line_id")
);
CREATE TABLE "encounter" (
    "encounter_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "encounter_number" VARCHAR(50) NOT NULL,
    "practice_id" INT NOT NULL,
    "patient_id" BIGINT NOT NULL,
    "encounter_date" DATE NOT NULL,
    "rendering_provider_id" INT NOT NULL,
    "encounter_status" VARCHAR(20) NOT NULL,
    "appointment_id" BIGINT NULL,
    "payer_id" INT NULL,
    "coverage_id" BIGINT NULL,
    "facility_id" INT NULL,
    "place_of_service_id" INT NULL,
    "specialty_id" INT NULL,
    "encounter_type" VARCHAR(20) NULL,
    "visit_minutes" SMALLINT NULL,
    "note_status" VARCHAR(20) NULL,
    "note_signed_date" DATE NULL,
    "signature_lag_days" SMALLINT NULL,
    "elements_documented_count" SMALLINT NULL,
    "charge_status" VARCHAR(20) NULL,
    "coding_status" VARCHAR(20) NULL,
    "principal_diagnosis_code_id" INT NULL,
    "authorization_id" BIGINT NULL,
    "supervising_provider_id" INT NULL,
    "referring_provider_id" INT NULL,
    "referral_id" BIGINT NULL,
    "version" SMALLINT NOT NULL,
    "is_current" BOOLEAN NOT NULL,
    "previous_encounter_id" BIGINT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_encounter" PRIMARY KEY ("encounter_id", "version")
);
CREATE TABLE "document" (
    "document_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "document_number" VARCHAR(50) NOT NULL,
    "practice_id" INT NULL,
    "patient_id" BIGINT NULL,
    "document_class" VARCHAR(20) NOT NULL,
    "document_type" VARCHAR(30) NOT NULL,
    "document_status" VARCHAR(20) NOT NULL,
    "encounter_id" BIGINT NULL,
    "authorization_id" BIGINT NULL,
    "claim_id" BIGINT NULL,
    "author_provider_id" INT NULL,
    "signer_role" VARCHAR(20) NULL,
    "document_date" DATE NULL,
    "signed_at" TIMESTAMP(0) NULL,
    "is_late_entry" BOOLEAN NULL,
    "is_addendum" BOOLEAN NULL,
    "addendum_of_document_id" BIGINT NULL,
    "is_locked" BOOLEAN NULL,
    "cosign_required" BOOLEAN NULL,
    "cosign_status" VARCHAR(10) NULL,
    "cosigned_at" TIMESTAMP(0) NULL,
    "expiry_date" DATE NULL,
    "minutes_documented" SMALLINT NULL,
    "hpi_component_count" SMALLINT NULL,
    "ros_system_count" SMALLINT NULL,
    "mdm_problem_level" VARCHAR(10) NULL,
    "mdm_data_level" VARCHAR(10) NULL,
    "mdm_risk_level" VARCHAR(10) NULL,
    "content_hash" BYTEA NULL,
    "page_count" SMALLINT NULL,
    "document_type_code" VARCHAR(20) NULL,
    "source_quality" VARCHAR(20) NULL,
    "version" SMALLINT NOT NULL,
    "is_current" BOOLEAN NOT NULL,
    "previous_document_id" BIGINT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_document" PRIMARY KEY ("document_id", "version")
);
CREATE TABLE "clinical_order" (
    "clinical_order_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "order_number" VARCHAR(50) NOT NULL,
    "practice_id" INT NULL,
    "patient_id" BIGINT NULL,
    "encounter_id" BIGINT NULL,
    "encounter_line_id" BIGINT NULL,
    "ordering_provider_id" INT NULL,
    "order_type" VARCHAR(20) NOT NULL,
    "order_status" VARCHAR(15) NOT NULL,
    "order_date" DATE NULL,
    "signed_date" DATE NULL,
    "cpt_code_id" INT NULL,
    "diagnosis_code_id" INT NULL,
    "authorization_id" BIGINT NULL,
    "auth_required" VARCHAR(7) NULL,
    "document_id" BIGINT NULL,
    "result_status" VARCHAR(10) NULL,
    "result_received_date" DATE NULL,
    "result_document_id" BIGINT NULL,
    "version" SMALLINT NOT NULL,
    "is_current" BOOLEAN NOT NULL,
    "previous_clinical_order_id" BIGINT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_clinical_order" PRIMARY KEY ("clinical_order_id", "version")
);
CREATE TABLE "encounter_line" (
    "encounter_line_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "encounter_id" BIGINT NOT NULL,
    "line_number" SMALLINT NOT NULL,
    "practice_id" INT NULL,
    "patient_id" BIGINT NULL,
    "payer_id" INT NULL,
    "provider_id" INT NULL,
    "specialty_id" INT NULL,
    "cpt_code_id" INT NOT NULL,
    "units" DECIMAL(7,2) NOT NULL,
    "service_date" DATE NULL,
    "rendering_provider_id" INT NULL,
    "diagnosis_1_id" INT NULL,
    "diagnosis_2_id" INT NULL,
    "diagnosis_3_id" INT NULL,
    "diagnosis_4_id" INT NULL,
    "modifier_1_id" INT NULL,
    "modifier_2_id" INT NULL,
    "modifier_3_id" INT NULL,
    "modifier_4_id" INT NULL,
    "laterality" CHAR(1) NULL,
    "procedure_documented" BOOLEAN NULL,
    "documented_level" SMALLINT NULL,
    "time_minutes" SMALLINT NULL,
    "authorization_id" BIGINT NULL,
    "auth_required" VARCHAR(10) NULL,
    "line_status" VARCHAR(20) NULL,
    "expected_charge" DECIMAL(12,2) NULL,
    "place_of_service_id" INT NULL,
    "ordering_provider_id" INT NULL,
    "drug_code" VARCHAR(11) NULL,
    "ndc_code_id" INT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_encounter_line" PRIMARY KEY ("encounter_line_id")
);
CREATE TABLE "encounter_diagnosis" (
    "encounter_diagnosis_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "encounter_id" BIGINT NOT NULL,
    "diagnosis_sequence" SMALLINT NOT NULL,
    "diagnosis_code_id" INT NOT NULL,
    "is_principal" BOOLEAN NOT NULL,
    "diagnosis_role" VARCHAR(15) NULL,
    "practice_id" INT NULL,
    "patient_id" BIGINT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_encounter_diagnosis" PRIMARY KEY ("encounter_diagnosis_id")
);
CREATE TABLE "document_element" (
    "document_element_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "document_id" BIGINT NOT NULL,
    "element_code" VARCHAR(30) NOT NULL,
    "is_present" BOOLEAN NOT NULL,
    "practice_id" INT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_document_element" PRIMARY KEY ("document_element_id")
);
CREATE TABLE "bill" (
    "bill_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "bill_number" VARCHAR(50) NOT NULL,
    "practice_id" INT NOT NULL,
    "patient_id" BIGINT NOT NULL,
    "encounter_id" BIGINT NOT NULL,
    "service_date" DATE NOT NULL,
    "charge_entered_date" DATE NOT NULL,
    "bill_status" VARCHAR(20) NOT NULL,
    "bill_type" VARCHAR(20) NOT NULL,
    "total_billed" DECIMAL(12,2) NOT NULL,
    "billing_provider_id" INT NULL,
    "rendering_provider_id" INT NULL,
    "specialty_id" INT NULL,
    "payer_id" INT NULL,
    "coverage_id" BIGINT NULL,
    "facility_id" INT NULL,
    "place_of_service_id" INT NULL,
    "ready_to_bill_date" DATE NULL,
    "hold_reason" VARCHAR(30) NULL,
    "hold_date" DATE NULL,
    "last_charge_date" DATE NULL,
    "claims_created" SMALLINT NULL,
    "latest_claim_status" VARCHAR(20) NULL,
    "first_claim_submitted_date" DATE NULL,
    "expected_allowed" DECIMAL(12,2) NULL,
    "entered_by_role" VARCHAR(30) NULL,
    "no_charge_amount" DECIMAL(12,2) NULL,
    "patient_statement_flag" BOOLEAN NULL,
    "version" SMALLINT NOT NULL,
    "is_current" BOOLEAN NOT NULL,
    "previous_bill_id" BIGINT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_bill" PRIMARY KEY ("bill_id", "version")
);
CREATE TABLE "claim" (
    "claim_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "claim_number" VARCHAR(50) NOT NULL,
    "practice_id" INT NOT NULL,
    "payer_id" INT NOT NULL,
    "patient_id" BIGINT NOT NULL,
    "billing_provider_id" INT NOT NULL,
    "service_date_from" DATE NOT NULL,
    "service_date_to" DATE NOT NULL,
    "submitted_date" DATE NOT NULL,
    "total_charge" DECIMAL(12,2) NOT NULL,
    "claim_status" VARCHAR(20) NOT NULL,
    "rendering_provider_id" INT NULL,
    "supervising_provider_id" INT NULL,
    "facility_id" INT NULL,
    "place_of_service_id" INT NULL,
    "specialty_id" INT NULL,
    "coverage_id" BIGINT NULL,
    "claim_sequence" VARCHAR(10) NULL,
    "primary_claim_id" BIGINT NULL,
    "other_payer_paid_amount" DECIMAL(12,2) NULL,
    "claim_filing_indicator" VARCHAR(2) NULL,
    "frequency_code" CHAR(1) NULL,
    "accept_assignment" CHAR(1) NULL,
    "benefits_assigned" CHAR(1) NULL,
    "release_of_info" CHAR(1) NULL,
    "payer_claim_number" VARCHAR(50) NULL,
    "original_payer_claim_number" VARCHAR(50) NULL,
    "bill_id" BIGINT NULL,
    "encounter_id" BIGINT NULL,
    "principal_diagnosis_code_id" INT NULL,
    "prior_auth_number" VARCHAR(50) NULL,
    "authorization_id" BIGINT NULL,
    "paid_amount" DECIMAL(12,2) NULL,
    "patient_responsibility" DECIMAL(12,2) NULL,
    "adjusted_amount" DECIMAL(12,2) NULL,
    "denied_amount" DECIMAL(12,2) NULL,
    "balance" DECIMAL(12,2) NULL,
    "last_payment_date" DATE NULL,
    "last_status_date" DATE NULL,
    "claim_type" VARCHAR(15) NULL,
    "accident_related" VARCHAR(10) NULL,
    "referring_provider_id" INT NULL,
    "referral_id" BIGINT NULL,
    "referral_number" VARCHAR(50) NULL,
    "batch_control_number" VARCHAR(20) NULL,
    "edi_file_id" BIGINT NULL,
    "signature_on_file" CHAR(1) NULL,
    "onset_date" DATE NULL,
    "late_filing_reason" VARCHAR(30) NULL,
    "delay_reason_code" VARCHAR(2) NULL,
    "version" SMALLINT NOT NULL,
    "is_current" BOOLEAN NOT NULL,
    "previous_claim_id" BIGINT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_claim" PRIMARY KEY ("claim_id", "version")
);
CREATE TABLE "claim_attachment" (
    "claim_attachment_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "claim_attachment_number" VARCHAR(50) NOT NULL,
    "practice_id" INT NULL,
    "patient_id" BIGINT NULL,
    "claim_id" BIGINT NOT NULL,
    "payer_id" INT NOT NULL,
    "request_type" VARCHAR(30) NOT NULL,
    "payer_reference_number" VARCHAR(50) NULL,
    "requesting_unit" VARCHAR(30) NULL,
    "request_received_date" DATE NULL,
    "request_channel" VARCHAR(15) NULL,
    "due_date" DATE NULL,
    "extended_due_date" DATE NULL,
    "request_text_hash" BYTEA NULL,
    "response_status" VARCHAR(20) NOT NULL,
    "response_sent_date" DATE NULL,
    "response_method" VARCHAR(15) NULL,
    "response_tracking_number" VARCHAR(50) NULL,
    "page_count" SMALLINT NULL,
    "payer_acknowledgement" VARCHAR(15) NULL,
    "attachment_report_type_code" VARCHAR(10) NULL,
    "attachment_transmission_code" VARCHAR(5) NULL,
    "attachment_control_number" VARCHAR(50) NULL,
    "document_id" BIGINT NULL,
    "version" SMALLINT NOT NULL,
    "is_current" BOOLEAN NOT NULL,
    "previous_claim_attachment_id" BIGINT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_claim_attachment" PRIMARY KEY ("claim_attachment_id", "version")
);
CREATE TABLE "bill_line" (
    "bill_line_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "bill_id" BIGINT NOT NULL,
    "line_number" SMALLINT NOT NULL,
    "practice_id" INT NULL,
    "patient_id" BIGINT NULL,
    "payer_id" INT NULL,
    "provider_id" INT NULL,
    "specialty_id" INT NULL,
    "cpt_code_id" INT NOT NULL,
    "units" DECIMAL(7,2) NOT NULL,
    "fee_per_unit" DECIMAL(12,2) NOT NULL,
    "billed_amount" DECIMAL(12,2) NOT NULL,
    "line_status" VARCHAR(20) NOT NULL,
    "service_date" DATE NULL,
    "modifier_1_id" INT NULL,
    "modifier_2_id" INT NULL,
    "modifier_3_id" INT NULL,
    "modifier_4_id" INT NULL,
    "diagnosis_1_id" INT NULL,
    "diagnosis_2_id" INT NULL,
    "diagnosis_3_id" INT NULL,
    "diagnosis_4_id" INT NULL,
    "rendering_provider_id" INT NULL,
    "encounter_line_id" BIGINT NULL,
    "charge_entered_date" DATE NULL,
    "cpt_as_entered_id" INT NULL,
    "code_changed" BOOLEAN NULL,
    "change_approved_by_staff_id" INT NULL,
    "fee_schedule_id" INT NULL,
    "expected_allowed" DECIMAL(12,2) NULL,
    "hold_reason" VARCHAR(30) NULL,
    "authorization_id" BIGINT NULL,
    "claims_on" SMALLINT NULL,
    "latest_claim_line_status" VARCHAR(20) NULL,
    "claimed_date" DATE NULL,
    "drug_code" VARCHAR(11) NULL,
    "ndc_code_id" INT NULL,
    "drug_units" DECIMAL(12,3) NULL,
    "drug_unit_measure" CHAR(2) NULL,
    "place_of_service_id" INT NULL,
    "entered_by_role" VARCHAR(30) NULL,
    "no_charge_amount" DECIMAL(12,2) NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_bill_line" PRIMARY KEY ("bill_line_id")
);
CREATE TABLE "claim_line" (
    "claim_line_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "claim_id" BIGINT NOT NULL,
    "line_number" SMALLINT NOT NULL,
    "practice_id" INT NULL,
    "payer_id" INT NULL,
    "patient_id" BIGINT NULL,
    "billing_provider_id" INT NULL,
    "specialty_id" INT NULL,
    "cpt_code_id" INT NOT NULL,
    "units" DECIMAL(7,2) NOT NULL,
    "charge_amount" DECIMAL(12,2) NOT NULL,
    "line_status" VARCHAR(20) NOT NULL,
    "paid_amount" DECIMAL(12,2) NULL,
    "service_date" DATE NULL,
    "service_date_to" DATE NULL,
    "place_of_service_id" INT NULL,
    "modifier_1_id" INT NULL,
    "modifier_2_id" INT NULL,
    "modifier_3_id" INT NULL,
    "modifier_4_id" INT NULL,
    "diagnosis_pointers" VARCHAR(4) NULL,
    "primary_diagnosis_code_id" INT NULL,
    "rendering_provider_id" INT NULL,
    "ordering_provider_id" INT NULL,
    "supervising_provider_id" INT NULL,
    "allowed_amount" DECIMAL(12,2) NULL,
    "patient_responsibility" DECIMAL(12,2) NULL,
    "contractual_adjustment" DECIMAL(12,2) NULL,
    "denied_amount" DECIMAL(12,2) NULL,
    "primary_denial_reason_id" INT NULL,
    "expected_allowed" DECIMAL(12,2) NULL,
    "bill_line_id" BIGINT NULL,
    "line_control_number" VARCHAR(30) NULL,
    "drug_code" VARCHAR(11) NULL,
    "ndc_code_id" INT NULL,
    "drug_units" DECIMAL(12,3) NULL,
    "drug_unit_measure" CHAR(2) NULL,
    "line_flags" VARCHAR(30) NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_claim_line" PRIMARY KEY ("claim_line_id")
);
CREATE TABLE "claim_status_history" (
    "claim_status_history_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "claim_id" BIGINT NOT NULL,
    "claim_line_id" BIGINT NULL,
    "event_type" VARCHAR(20) NOT NULL,
    "event_date" DATE NOT NULL,
    "status_after" VARCHAR(20) NOT NULL,
    "practice_id" INT NOT NULL,
    "payer_id" INT NOT NULL,
    "patient_id" BIGINT NOT NULL,
    "event_ts" TIMESTAMP(0) NULL,
    "response_sequence" SMALLINT NULL,
    "status_category" VARCHAR(10) NULL,
    "status_category_code_id" INT NULL,
    "status_code" VARCHAR(10) NULL,
    "status_code_id" INT NULL,
    "is_rejection" BOOLEAN NULL,
    "rejection_reason" VARCHAR(20) NULL,
    "rejection_category" VARCHAR(30) NULL,
    "is_technical" BOOLEAN NULL,
    "owner_role" VARCHAR(20) NULL,
    "fix_by_date" DATE NULL,
    "channel" VARCHAR(20) NULL,
    "payer_claim_number" VARCHAR(50) NULL,
    "billing_provider_id" INT NULL,
    "specialty_id" INT NULL,
    "reported_paid_amount" DECIMAL(12,2) NULL,
    "acked_control_number" VARCHAR(30) NULL,
    "clearinghouse_batch_number" VARCHAR(30) NULL,
    "edi_file_id" BIGINT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_claim_status_history" PRIMARY KEY ("claim_status_history_id")
);
CREATE TABLE "claim_diagnosis" (
    "claim_diagnosis_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "claim_id" BIGINT NOT NULL,
    "diagnosis_sequence" SMALLINT NOT NULL,
    "diagnosis_code_id" INT NOT NULL,
    "is_principal" BOOLEAN NOT NULL,
    "poa_indicator" CHAR(1) NULL,
    "practice_id" INT NULL,
    "payer_id" INT NULL,
    "patient_id" BIGINT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_claim_diagnosis" PRIMARY KEY ("claim_diagnosis_id")
);
CREATE TABLE "claim_attachment_document" (
    "claim_attachment_document_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "claim_attachment_id" BIGINT NOT NULL,
    "document_type" VARCHAR(30) NOT NULL,
    "document_id" BIGINT NULL,
    "item_status" VARCHAR(12) NOT NULL,
    "page_count" SMALLINT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_claim_attachment_document" PRIMARY KEY ("claim_attachment_document_id")
);
CREATE TABLE "claim_edit" (
    "claim_edit_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "claim_id" BIGINT NOT NULL,
    "claim_line_id" BIGINT NULL,
    "edit_source" VARCHAR(15) NOT NULL,
    "edit_code" VARCHAR(50) NOT NULL,
    "edit_category" VARCHAR(30) NULL,
    "severity" VARCHAR(10) NOT NULL,
    "edit_ts" TIMESTAMP(0) NOT NULL,
    "edit_status" VARCHAR(12) NOT NULL,
    "resolved_ts" TIMESTAMP(0) NULL,
    "resolved_by_staff_id" INT NULL,
    "fix_field_code" VARCHAR(40) NULL,
    "payer_rule_id" BIGINT NULL,
    "agent_decision_id" BIGINT NULL,
    "edi_file_id" BIGINT NULL,
    "practice_id" INT NULL,
    "payer_id" INT NULL,
    "patient_id" BIGINT NULL,
    "billing_provider_id" INT NULL,
    "cpt_code_id" INT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_claim_edit" PRIMARY KEY ("claim_edit_id")
);
CREATE TABLE "ledger_entry" (
    "ledger_entry_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "transaction_number" VARCHAR(50) NOT NULL,
    "practice_id" INT NOT NULL,
    "patient_id" BIGINT NOT NULL,
    "bill_line_id" BIGINT NOT NULL,
    "transaction_type" VARCHAR(20) NOT NULL,
    "amount" DECIMAL(12,2) NOT NULL,
    "balance_effect" DECIMAL(12,2) NOT NULL,
    "transaction_date" DATE NOT NULL,
    "responsible_party" VARCHAR(10) NOT NULL,
    "from_party" VARCHAR(10) NULL,
    "to_party" VARCHAR(10) NULL,
    "to_payer_id" INT NULL,
    "claim_line_id" BIGINT NULL,
    "claim_id" BIGINT NULL,
    "transaction_subtype" VARCHAR(30) NULL,
    "posted_date" DATE NULL,
    "payer_id" INT NULL,
    "provider_id" INT NULL,
    "specialty_id" INT NULL,
    "cpt_code_id" INT NULL,
    "adjustment_reason_id" INT NULL,
    "group_code" CHAR(2) NULL,
    "payment_id" BIGINT NULL,
    "payment_method" VARCHAR(15) NULL,
    "payment_number" VARCHAR(50) NULL,
    "approved_by_staff_id" INT NULL,
    "approved_date" DATE NULL,
    "reverses_ledger_entry_id" BIGINT NULL,
    "is_reversal" BOOLEAN NULL,
    "batch_number" VARCHAR(30) NULL,
    "posted_by_role" VARCHAR(30) NULL,
    "refund_reason" VARCHAR(30) NULL,
    "remark_code_id" INT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_ledger_entry" PRIMARY KEY ("ledger_entry_id")
);
CREATE TABLE "denial" (
    "denial_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "claim_id" BIGINT NOT NULL,
    "claim_line_id" BIGINT NOT NULL,
    "practice_id" INT NOT NULL,
    "patient_id" BIGINT NOT NULL,
    "payer_id" INT NOT NULL,
    "denial_date" DATE NOT NULL,
    "denied_amount" DECIMAL(12,2) NOT NULL,
    "adjustment_reason_id" INT NOT NULL,
    "denial_status" VARCHAR(25) NOT NULL,
    "ledger_entry_id" BIGINT NULL,
    "bill_line_id" BIGINT NULL,
    "group_code" CHAR(2) NULL,
    "reason_category" VARCHAR(30) NULL,
    "clock_start_date" DATE NULL,
    "appeal_deadline" DATE NULL,
    "root_cause" VARCHAR(30) NULL,
    "upstream_stage" VARCHAR(15) NULL,
    "is_preventable" BOOLEAN NULL,
    "is_technical" BOOLEAN NULL,
    "owner_role" VARCHAR(20) NULL,
    "resolved_date" DATE NULL,
    "outcome" VARCHAR(20) NULL,
    "recovered_amount" DECIMAL(12,2) NULL,
    "is_repeat" BOOLEAN NULL,
    "denial_count_on_line" SMALLINT NULL,
    "resubmitted_claim_id" BIGINT NULL,
    "cpt_code_id" INT NULL,
    "provider_id" INT NULL,
    "specialty_id" INT NULL,
    "is_claim_level" BOOLEAN NULL,
    "units_denied" DECIMAL(7,2) NULL,
    "authorization_id" BIGINT NULL,
    "version" SMALLINT NOT NULL,
    "is_current" BOOLEAN NOT NULL,
    "previous_denial_id" BIGINT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_denial" PRIMARY KEY ("denial_id", "version")
);
CREATE TABLE "payment" (
    "payment_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "payment_number" VARCHAR(50) NOT NULL,
    "practice_id" INT NOT NULL,
    "payment_source" VARCHAR(10) NOT NULL,
    "payment_date" DATE NOT NULL,
    "payment_amount" DECIMAL(12,2) NOT NULL,
    "payment_method" VARCHAR(15) NOT NULL,
    "payer_id" INT NULL,
    "patient_id" BIGINT NULL,
    "guarantor_id" BIGINT NULL,
    "appointment_id" BIGINT NULL,
    "collection_point" VARCHAR(15) NULL,
    "payment_type" VARCHAR(10) NULL,
    "received_date" DATE NULL,
    "posted_date" DATE NULL,
    "credit_debit" CHAR(1) NULL,
    "has_remittance" BOOLEAN NULL,
    "edi_file_id" BIGINT NULL,
    "claim_count" SMALLINT NULL,
    "posted_amount" DECIMAL(12,2) NULL,
    "unapplied_amount" DECIMAL(12,2) NULL,
    "plb_amount" DECIMAL(12,2) NULL,
    "reconciles" BOOLEAN NULL,
    "is_void" BOOLEAN NULL,
    "payee_provider_id" INT NULL,
    "version" SMALLINT NOT NULL,
    "is_current" BOOLEAN NOT NULL,
    "previous_payment_id" BIGINT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_payment" PRIMARY KEY ("payment_id", "version")
);
CREATE TABLE "payment_plan" (
    "payment_plan_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "payment_plan_number" VARCHAR(50) NULL,
    "patient_id" BIGINT NOT NULL,
    "guarantor_id" BIGINT NULL,
    "plan_status" VARCHAR(10) NOT NULL,
    "start_date" DATE NOT NULL,
    "total_amount" DECIMAL(12,2) NOT NULL,
    "practice_id" INT NULL,
    "instalment_amount" DECIMAL(12,2) NULL,
    "instalment_count" SMALLINT NULL,
    "frequency" VARCHAR(10) NULL,
    "next_due_date" DATE NULL,
    "missed_instalments" SMALLINT NULL,
    "last_missed_date" DATE NULL,
    "autopay_enrolled" BOOLEAN NULL,
    "end_date" DATE NULL,
    "version" SMALLINT NOT NULL,
    "is_current" BOOLEAN NOT NULL,
    "previous_payment_plan_id" BIGINT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_payment_plan" PRIMARY KEY ("payment_plan_id", "version")
);
CREATE TABLE "patient_contact_preference" (
    "patient_contact_preference_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "patient_id" BIGINT NOT NULL,
    "opt_out" BOOLEAN NOT NULL,
    "text_consent" BOOLEAN NOT NULL,
    "preferred_channel" VARCHAR(10) NULL,
    "quiet_hours_start" SMALLINT NULL,
    "quiet_hours_end" SMALLINT NULL,
    "contact_time_zone" VARCHAR(40) NULL,
    "address_status" VARCHAR(10) NULL,
    "has_phone" BOOLEAN NULL,
    "autodial_consent" BOOLEAN NULL,
    "consent_date" DATE NULL,
    "consent_source" VARCHAR(20) NULL,
    "consent_wording_version" VARCHAR(10) NULL,
    "opt_out_date" DATE NULL,
    "has_authorized_rep" BOOLEAN NULL,
    "guarantor_hash" BYTEA NULL,
    "guarantor_id" BIGINT NULL,
    "version" SMALLINT NOT NULL,
    "is_current" BOOLEAN NOT NULL,
    "previous_patient_contact_preference_id" BIGINT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_patient_contact_preference" PRIMARY KEY ("patient_contact_preference_id", "version")
);
CREATE TABLE "denial_reason" (
    "denial_reason_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "denial_id" BIGINT NOT NULL,
    "detail_seq" SMALLINT NOT NULL,
    "detail_type" VARCHAR(10) NOT NULL,
    "adjustment_reason_id" INT NULL,
    "remark_code_id" INT NULL,
    "group_code" CHAR(2) NULL,
    "reason_amount" DECIMAL(12,2) NULL,
    "is_amount_allocated" BOOLEAN NULL,
    "reason_units" DECIMAL(7,2) NULL,
    "is_primary" BOOLEAN NULL,
    "reason_category" VARCHAR(30) NULL,
    "is_appealable" BOOLEAN NULL,
    "suggested_action" VARCHAR(25) NULL,
    "denial_date" DATE NULL,
    "practice_id" INT NULL,
    "payer_id" INT NULL,
    "cpt_code_id" INT NULL,
    "claim_line_id" BIGINT NULL,
    "provider_id" INT NULL,
    "specialty_id" INT NULL,
    "patient_id" BIGINT NULL,
    "payer_reason_code" VARCHAR(20) NULL,
    "remark_qualifier" VARCHAR(5) NULL,
    "documents_needed" VARCHAR(30) NULL,
    "reason_corrected" BOOLEAN NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_denial_reason" PRIMARY KEY ("denial_reason_id")
);
CREATE TABLE "ar_interval" (
    "ar_interval_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "bill_line_id" BIGINT NOT NULL,
    "period_start_date" DATE NOT NULL,
    "period_end_date" DATE NOT NULL,
    "period_type" VARCHAR(10) NOT NULL,
    "practice_id" INT NOT NULL,
    "patient_id" BIGINT NOT NULL,
    "guarantor_id" BIGINT NULL,
    "opening_balance" DECIMAL(12,2) NOT NULL,
    "charges" DECIMAL(12,2) NOT NULL,
    "payments" DECIMAL(12,2) NOT NULL,
    "adjustments" DECIMAL(12,2) NOT NULL,
    "write_offs" DECIMAL(12,2) NOT NULL,
    "refunds" DECIMAL(12,2) NOT NULL,
    "closing_balance" DECIMAL(12,2) NOT NULL,
    "payer_balance" DECIMAL(12,2) NOT NULL,
    "patient_balance" DECIMAL(12,2) NOT NULL,
    "payer_bucket" VARCHAR(10) NOT NULL,
    "patient_bucket" VARCHAR(10) NOT NULL,
    "aging_basis" VARCHAR(20) NOT NULL,
    "reconciles" BOOLEAN NOT NULL,
    "prior_period_ar_interval_id" BIGINT NULL,
    "payer_days" SMALLINT NULL,
    "patient_days" SMALLINT NULL,
    "payer_aging_date" DATE NULL,
    "patient_aging_date" DATE NULL,
    "unbilled_balance" DECIMAL(12,2) NULL,
    "payments_payer" DECIMAL(12,2) NULL,
    "payments_patient" DECIMAL(12,2) NULL,
    "adjustments_contractual" DECIMAL(12,2) NULL,
    "adjustments_denial" DECIMAL(12,2) NULL,
    "adjustments_other" DECIMAL(12,2) NULL,
    "transfers_to_patient" DECIMAL(12,2) NULL,
    "transfers_to_secondary" DECIMAL(12,2) NULL,
    "claim_id" BIGINT NULL,
    "claim_line_id" BIGINT NULL,
    "claim_status" VARCHAR(20) NULL,
    "payer_id" INT NULL,
    "open_denied_amount" DECIMAL(12,2) NULL,
    "is_in_denial" BOOLEAN NULL,
    "expected_collectible" DECIMAL(12,2) NULL,
    "last_payment_date" DATE NULL,
    "last_activity_date" DATE NULL,
    "last_statement_date" DATE NULL,
    "is_credit" BOOLEAN NULL,
    "ledger_balance" DECIMAL(12,2) NULL,
    "variance_amount" DECIMAL(12,2) NULL,
    "is_restated" BOOLEAN NULL,
    "period_status" VARCHAR(10) NULL,
    "provider_id" INT NULL,
    "specialty_id" INT NULL,
    "cpt_code_id" INT NULL,
    "facility_id" INT NULL,
    "service_date" DATE NULL,
    "collections_agency_flag" BOOLEAN NULL,
    "statement_count" SMALLINT NULL,
    "version" SMALLINT NOT NULL,
    "is_current" BOOLEAN NOT NULL,
    "previous_ar_interval_id" BIGINT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_ar_interval" PRIMARY KEY ("ar_interval_id", "version")
);
CREATE TABLE "ar_snapshot" (
    "ar_snapshot_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "as_of_date" DATE NOT NULL,
    "snapshot_type" VARCHAR(10) NOT NULL,
    "bill_id" BIGINT NOT NULL,
    "balance_owner" VARCHAR(10) NOT NULL,
    "balance" DECIMAL(12,2) NOT NULL,
    "practice_id" INT NOT NULL,
    "patient_id" BIGINT NOT NULL,
    "guarantor_id" BIGINT NULL,
    "aging_date" DATE NOT NULL,
    "days_outstanding" SMALLINT NOT NULL,
    "aging_bucket" VARCHAR(10) NOT NULL,
    "aging_basis" VARCHAR(20) NOT NULL,
    "claim_id" BIGINT NULL,
    "payer_id" INT NULL,
    "claim_status" VARCHAR(20) NULL,
    "claim_sequence" VARCHAR(10) NULL,
    "submitted_date" DATE NULL,
    "expected_collectible" DECIMAL(12,2) NULL,
    "last_payment_date" DATE NULL,
    "last_activity_date" DATE NULL,
    "days_since_activity" SMALLINT NULL,
    "last_statement_date" DATE NULL,
    "open_denied_amount" DECIMAL(12,2) NULL,
    "is_in_denial" BOOLEAN NULL,
    "is_credit" BOOLEAN NULL,
    "overpayment_identified_date" DATE NULL,
    "refund_due_date" DATE NULL,
    "filing_deadline" DATE NULL,
    "provider_id" INT NULL,
    "specialty_id" INT NULL,
    "facility_id" INT NULL,
    "service_date" DATE NULL,
    "primary_cpt_code_id" INT NULL,
    "change_since_last_snapshot" DECIMAL(12,2) NULL,
    "collections_agency_flag" BOOLEAN NULL,
    "next_action_date" DATE NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_ar_snapshot" PRIMARY KEY ("ar_snapshot_id")
);
CREATE TABLE "appeal" (
    "appeal_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "appeal_number" VARCHAR(50) NULL,
    "denial_id" BIGINT NOT NULL,
    "appeal_level" VARCHAR(15) NOT NULL,
    "appeal_status" VARCHAR(12) NOT NULL,
    "clock_start_date" DATE NOT NULL,
    "deadline_date" DATE NOT NULL,
    "claim_id" BIGINT NULL,
    "submitted_date" DATE NULL,
    "submission_channel" VARCHAR(10) NULL,
    "amount_disputed" DECIMAL(12,2) NULL,
    "evidence_count" SMALLINT NULL,
    "letter_hash" BYTEA NULL,
    "payer_reference" VARCHAR(50) NULL,
    "decision_date" DATE NULL,
    "payer_decision" VARCHAR(20) NULL,
    "is_overturned" BOOLEAN NULL,
    "recovered_amount" DECIMAL(12,2) NULL,
    "agent_decision_id" BIGINT NULL,
    "agent_approval_id" BIGINT NULL,
    "practice_id" INT NULL,
    "patient_id" BIGINT NULL,
    "payer_id" INT NULL,
    "version" SMALLINT NOT NULL,
    "is_current" BOOLEAN NOT NULL,
    "previous_appeal_id" BIGINT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_appeal" PRIMARY KEY ("appeal_id", "version")
);
CREATE TABLE "patient_statement" (
    "patient_statement_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "statement_number" VARCHAR(50) NULL,
    "patient_id" BIGINT NOT NULL,
    "guarantor_id" BIGINT NOT NULL,
    "statement_date" DATE NOT NULL,
    "statement_amount" DECIMAL(12,2) NOT NULL,
    "channel" VARCHAR(10) NOT NULL,
    "statement_status" VARCHAR(12) NOT NULL,
    "practice_id" INT NULL,
    "bill_id" BIGINT NULL,
    "claim_id" BIGINT NULL,
    "due_date" DATE NULL,
    "sent_at" TIMESTAMP(0) NULL,
    "status_date" DATE NULL,
    "dunning_level" SMALLINT NULL,
    "validation_notice_date" DATE NULL,
    "dispute_window_end_date" DATE NULL,
    "collection_placement_id" BIGINT NULL,
    "payment_plan_id" BIGINT NULL,
    "version" SMALLINT NOT NULL,
    "is_current" BOOLEAN NOT NULL,
    "previous_patient_statement_id" BIGINT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_patient_statement" PRIMARY KEY ("patient_statement_id", "version")
);
CREATE TABLE "payment_adjustment" (
    "payment_adjustment_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "payment_id" BIGINT NOT NULL,
    "adjustment_type" VARCHAR(15) NOT NULL,
    "amount" DECIMAL(12,2) NOT NULL,
    "adjustment_date" DATE NOT NULL,
    "plb_reason_code" VARCHAR(5) NULL,
    "practice_id" INT NULL,
    "payer_id" INT NULL,
    "payee_provider_id" INT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_payment_adjustment" PRIMARY KEY ("payment_adjustment_id")
);
CREATE TABLE "remittance_claim" (
    "remittance_claim_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "payment_id" BIGINT NOT NULL,
    "claim_id" BIGINT NULL,
    "patient_control_number" VARCHAR(50) NOT NULL,
    "claim_status_code" VARCHAR(3) NOT NULL,
    "is_reversal" BOOLEAN NOT NULL,
    "charge_amount" DECIMAL(12,2) NOT NULL,
    "paid_amount" DECIMAL(12,2) NOT NULL,
    "patient_responsibility" DECIMAL(12,2) NULL,
    "claim_filing_indicator" VARCHAR(2) NULL,
    "payer_claim_number" VARCHAR(50) NULL,
    "claim_level_adjustment" DECIMAL(12,2) NULL,
    "remark_code_id" INT NULL,
    "is_crossover" BOOLEAN NULL,
    "crossover_payer_id" INT NULL,
    "match_method" VARCHAR(20) NULL,
    "payer_id" INT NULL,
    "practice_id" INT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_remittance_claim" PRIMARY KEY ("remittance_claim_id")
);
CREATE TABLE "bank_deposit" (
    "bank_deposit_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "practice_id" INT NOT NULL,
    "deposit_date" DATE NOT NULL,
    "deposit_amount" DECIMAL(12,2) NOT NULL,
    "deposit_method" VARCHAR(15) NOT NULL,
    "trace_number" VARCHAR(50) NULL,
    "payer_id" INT NULL,
    "payment_id" BIGINT NULL,
    "match_status" VARCHAR(12) NOT NULL,
    "matched_date" DATE NULL,
    "variance_amount" DECIMAL(12,2) NULL,
    "bank_account_label" VARCHAR(30) NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_bank_deposit" PRIMARY KEY ("bank_deposit_id")
);
CREATE TABLE "collection_placement" (
    "collection_placement_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "placement_number" VARCHAR(50) NULL,
    "guarantor_id" BIGINT NOT NULL,
    "patient_id" BIGINT NULL,
    "agency_code" VARCHAR(30) NOT NULL,
    "placement_type" VARCHAR(15) NOT NULL,
    "is_third_party" BOOLEAN NOT NULL,
    "placed_date" DATE NOT NULL,
    "placed_amount" DECIMAL(12,2) NOT NULL,
    "recovered_amount" DECIMAL(12,2) NULL,
    "agency_fee_amount" DECIMAL(12,2) NULL,
    "placement_status" VARCHAR(25) NOT NULL,
    "recall_date" DATE NULL,
    "recall_reason" VARCHAR(20) NULL,
    "closed_date" DATE NULL,
    "credit_reported" BOOLEAN NULL,
    "practice_id" INT NULL,
    "version" SMALLINT NOT NULL,
    "is_current" BOOLEAN NOT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_collection_placement" PRIMARY KEY ("collection_placement_id", "version")
);
CREATE TABLE "agent_decision" (
    "agent_decision_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "agent_run_id" BIGINT NOT NULL,
    "agent_code" VARCHAR(5) NOT NULL,
    "decision_type" VARCHAR(30) NOT NULL,
    "entity_type" VARCHAR(20) NOT NULL,
    "entity_id" BIGINT NOT NULL,
    "outcome" VARCHAR(15) NOT NULL,
    "decided_at" TIMESTAMP(0) NOT NULL,
    "run_mode" VARCHAR(10) NOT NULL,
    "confidence" DECIMAL(5,4) NULL,
    "reason_summary" VARCHAR(300) NULL,
    "rules_checked" SMALLINT NULL,
    "rules_failed" SMALLINT NULL,
    "amount_at_stake" DECIMAL(12,2) NULL,
    "data_fallback_level" SMALLINT NULL,
    "human_outcome" VARCHAR(15) NULL,
    "human_outcome_date" DATE NULL,
    "supersedes_decision_id" BIGINT NULL,
    "is_current" BOOLEAN NULL,
    "input_hash" BYTEA NULL,
    "practice_id" INT NULL,
    "patient_id" BIGINT NULL,
    "payer_id" INT NULL,
    "provider_id" INT NULL,
    "specialty_id" INT NULL,
    "appointment_id" BIGINT NULL,
    "encounter_id" BIGINT NULL,
    "bill_id" BIGINT NULL,
    "claim_id" BIGINT NULL,
    "denial_id" BIGINT NULL,
    "authorization_id" BIGINT NULL,
    "recheck_condition" VARCHAR(100) NULL,
    "recheck_result" VARCHAR(20) NULL,
    "prompt_hash" BYTEA NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_agent_decision" PRIMARY KEY ("agent_decision_id")
);
CREATE TABLE "agent_value" (
    "agent_value_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "agent_code" VARCHAR(5) NOT NULL,
    "value_stage" VARCHAR(10) NOT NULL,
    "amount" DECIMAL(12,2) NOT NULL,
    "signed_amount" DECIMAL(12,2) NOT NULL,
    "value_date" DATE NOT NULL,
    "entity_type" VARCHAR(20) NOT NULL,
    "entity_id" BIGINT NOT NULL,
    "agent_finding_id" BIGINT NULL,
    "agent_decision_id" BIGINT NULL,
    "practice_id" INT NULL,
    "claim_id" BIGINT NULL,
    "denial_id" BIGINT NULL,
    "payer_id" INT NULL,
    "provider_id" INT NULL,
    "specialty_id" INT NULL,
    "cpt_code_id" INT NULL,
    "ledger_entry_id" BIGINT NULL,
    "is_holdout" BOOLEAN NULL,
    "incremental_amount" DECIMAL(12,2) NULL,
    "value_kind" VARCHAR(30) NULL,
    "is_estimate" BOOLEAN NULL,
    "attribution_share" DECIMAL(5,4) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_agent_value" PRIMARY KEY ("agent_value_id")
);
CREATE TABLE "agent_run" (
    "agent_run_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "agent_code" VARCHAR(5) NOT NULL,
    "agent_name" VARCHAR(40) NULL,
    "run_mode" VARCHAR(10) NOT NULL,
    "trigger_type" VARCHAR(15) NOT NULL,
    "started_at" TIMESTAMP(0) NOT NULL,
    "ended_at" TIMESTAMP(0) NULL,
    "run_status" VARCHAR(12) NOT NULL,
    "practice_id" INT NULL,
    "items_in" INT NULL,
    "decisions_made" INT NULL,
    "error_count" INT NULL,
    "error_summary" VARCHAR(200) NULL,
    "model_name" VARCHAR(40) NULL,
    "input_tokens" BIGINT NULL,
    "output_tokens" BIGINT NULL,
    "cost_amount" DECIMAL(12,4) NULL,
    "trigger_run_id" BIGINT NULL,
    "code_version" VARCHAR(30) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_agent_run" PRIMARY KEY ("agent_run_id")
);
CREATE TABLE "agent_decision_check" (
    "agent_decision_check_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "agent_decision_id" BIGINT NOT NULL,
    "check_seq" SMALLINT NOT NULL,
    "rule_code" VARCHAR(40) NOT NULL,
    "check_result" VARCHAR(10) NOT NULL,
    "agent_code" VARCHAR(5) NULL,
    "rule_version" VARCHAR(20) NULL,
    "rule_source" VARCHAR(20) NULL,
    "severity" VARCHAR(10) NULL,
    "observed_value" VARCHAR(100) NULL,
    "expected_value" VARCHAR(100) NULL,
    "input_table" VARCHAR(40) NULL,
    "input_fallback_level" SMALLINT NULL,
    "practice_id" INT NULL,
    "payer_id" INT NULL,
    "cpt_code_id" INT NULL,
    "evidence_ref" VARCHAR(100) NULL,
    "payer_rule_id" BIGINT NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_agent_decision_check" PRIMARY KEY ("agent_decision_check_id")
);
CREATE TABLE "agent_finding" (
    "agent_finding_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "agent_run_id" BIGINT NOT NULL,
    "agent_code" VARCHAR(5) NOT NULL,
    "finding_type" VARCHAR(30) NOT NULL,
    "entity_type" VARCHAR(20) NOT NULL,
    "entity_id" BIGINT NOT NULL,
    "found_date" DATE NOT NULL,
    "finding_status" VARCHAR(12) NOT NULL,
    "amount_at_risk" DECIMAL(12,2) NULL,
    "amount_recovered" DECIMAL(12,2) NULL,
    "upstream_stage" VARCHAR(15) NULL,
    "is_preventable" BOOLEAN NULL,
    "severity" VARCHAR(10) NULL,
    "deadline_date" DATE NULL,
    "resolved_date" DATE NULL,
    "resolution" VARCHAR(20) NULL,
    "agent_decision_id" BIGINT NULL,
    "finding_hash" BYTEA NULL,
    "summary" VARCHAR(300) NULL,
    "practice_id" INT NULL,
    "patient_id" BIGINT NULL,
    "payer_id" INT NULL,
    "provider_id" INT NULL,
    "specialty_id" INT NULL,
    "appointment_id" BIGINT NULL,
    "encounter_id" BIGINT NULL,
    "bill_id" BIGINT NULL,
    "claim_id" BIGINT NULL,
    "denial_id" BIGINT NULL,
    "authorization_id" BIGINT NULL,
    "suggested_value" VARCHAR(100) NULL,
    "final_value" VARCHAR(100) NULL,
    "value_difference" DECIMAL(12,2) NULL,
    "is_compliance_risk" BOOLEAN NULL,
    "predicted_probability" DECIMAL(5,4) NULL,
    "predicted_reason_category" VARCHAR(30) NULL,
    "predicted_allowed_amount" DECIMAL(12,2) NULL,
    "predicted_patient_responsibility" DECIMAL(12,2) NULL,
    "version" SMALLINT NOT NULL,
    "is_current" BOOLEAN NOT NULL,
    "previous_agent_finding_id" BIGINT NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_agent_finding" PRIMARY KEY ("agent_finding_id", "version")
);
CREATE TABLE "agent_task" (
    "agent_task_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "task_type" VARCHAR(30) NOT NULL,
    "owner_role" VARCHAR(20) NOT NULL,
    "task_status" VARCHAR(12) NOT NULL,
    "created_date" DATE NOT NULL,
    "agent_code" VARCHAR(5) NOT NULL,
    "entity_type" VARCHAR(20) NOT NULL,
    "entity_id" BIGINT NOT NULL,
    "agent_decision_id" BIGINT NULL,
    "agent_finding_id" BIGINT NULL,
    "priority" VARCHAR(8) NULL,
    "due_date" DATE NULL,
    "completed_date" DATE NULL,
    "assigned_to_staff_id" INT NULL,
    "amount_at_stake" DECIMAL(12,2) NULL,
    "outcome" VARCHAR(20) NULL,
    "title" VARCHAR(100) NULL,
    "practice_id" INT NULL,
    "patient_id" BIGINT NULL,
    "payer_id" INT NULL,
    "provider_id" INT NULL,
    "specialty_id" INT NULL,
    "appointment_id" BIGINT NULL,
    "encounter_id" BIGINT NULL,
    "bill_id" BIGINT NULL,
    "claim_id" BIGINT NULL,
    "denial_id" BIGINT NULL,
    "authorization_id" BIGINT NULL,
    "minutes_spent" INT NULL,
    "contact_channel" VARCHAR(30) NULL,
    "escalation_level" SMALLINT NULL,
    "reminder_count" SMALLINT NULL,
    "version" SMALLINT NOT NULL,
    "is_current" BOOLEAN NOT NULL,
    "previous_agent_task_id" BIGINT NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_agent_task" PRIMARY KEY ("agent_task_id", "version")
);
CREATE TABLE "agent_approval" (
    "agent_approval_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "agent_decision_id" BIGINT NOT NULL,
    "approval_type" VARCHAR(25) NOT NULL,
    "approval_status" VARCHAR(10) NOT NULL,
    "approved_by_staff_id" INT NULL,
    "approver_role" VARCHAR(20) NOT NULL,
    "approval_date" DATE NOT NULL,
    "agent_task_id" BIGINT NULL,
    "amount_approved" DECIMAL(12,2) NULL,
    "limit_checked" BOOLEAN NULL,
    "reason_code" VARCHAR(20) NULL,
    "entity_type" VARCHAR(20) NULL,
    "entity_id" BIGINT NULL,
    "practice_id" INT NULL,
    "approval_ts" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_agent_approval" PRIMARY KEY ("agent_approval_id")
);
CREATE TABLE "agent_writeback" (
    "agent_writeback_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "agent_decision_id" BIGINT NOT NULL,
    "target_system" VARCHAR(15) NOT NULL,
    "writeback_type" VARCHAR(30) NOT NULL,
    "send_status" VARCHAR(20) NOT NULL,
    "attempted_at" TIMESTAMP(0) NOT NULL,
    "agent_approval_id" BIGINT NULL,
    "agent_code" VARCHAR(5) NULL,
    "entity_type" VARCHAR(20) NULL,
    "entity_id" BIGINT NULL,
    "attempt_no" SMALLINT NULL,
    "response_code" VARCHAR(20) NULL,
    "response_at" TIMESTAMP(0) NULL,
    "external_ref" VARCHAR(50) NULL,
    "payload_hash" BYTEA NULL,
    "practice_id" INT NULL,
    "claim_id" BIGINT NULL,
    "appointment_id" BIGINT NULL,
    "version" SMALLINT NOT NULL,
    "is_current" BOOLEAN NOT NULL,
    "previous_agent_writeback_id" BIGINT NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_agent_writeback" PRIMARY KEY ("agent_writeback_id", "version")
);
CREATE TABLE "agent_forecast" (
    "agent_forecast_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "forecast_type" VARCHAR(20) NOT NULL,
    "as_of_date" DATE NOT NULL,
    "target_start_date" DATE NOT NULL,
    "target_end_date" DATE NOT NULL,
    "expected_amount" DECIMAL(12,2) NOT NULL,
    "low_amount" DECIMAL(12,2) NULL,
    "high_amount" DECIMAL(12,2) NULL,
    "probability" DECIMAL(5,4) NULL,
    "claim_count" INT NULL,
    "practice_id" INT NULL,
    "payer_id" INT NULL,
    "entity_type" VARCHAR(20) NULL,
    "entity_id" BIGINT NULL,
    "actual_amount" DECIMAL(12,2) NULL,
    "actual_known_date" DATE NULL,
    "within_range" BOOLEAN NULL,
    "interval_level" DECIMAL(3,2) NULL,
    "model_name" VARCHAR(40) NULL,
    "code_version" VARCHAR(30) NULL,
    "version" SMALLINT NOT NULL,
    "is_current" BOOLEAN NOT NULL,
    "previous_agent_forecast_id" BIGINT NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_agent_forecast" PRIMARY KEY ("agent_forecast_id", "version")
);
CREATE TABLE "patient" (
    "patient_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "patient_number_hash" BYTEA NOT NULL,
    "master_patient_hash" BYTEA NULL,
    "merged_into_patient_id" BIGINT NULL,
    "birth_year" SMALLINT NULL,
    "is_age_90_plus" BOOLEAN NULL,
    "sex" CHAR(1) NULL,
    "state" CHAR(2) NULL,
    "primary_practice_id" INT NULL,
    "first_seen_date" DATE NULL,
    "last_seen_date" DATE NULL,
    "primary_coverage_id" BIGINT NULL,
    "guarantor_id" BIGINT NULL,
    "is_self_pay" BOOLEAN NULL,
    "zip3" CHAR(3) NULL,
    "language" VARCHAR(20) NULL,
    "is_deceased" BOOLEAN NULL,
    "is_active" BOOLEAN NOT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_patient" PRIMARY KEY ("patient_id")
);
CREATE TABLE "coverage" (
    "coverage_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "patient_id" BIGINT NOT NULL,
    "payer_id" INT NOT NULL,
    "payer_plan_id" INT NULL,
    "member_number_hash" BYTEA NOT NULL,
    "coverage_order" SMALLINT NOT NULL,
    "effective_date" DATE NOT NULL,
    "termination_date" DATE NULL,
    "plan_type" VARCHAR(25) NULL,
    "plan_name" VARCHAR(100) NULL,
    "group_number_hash" BYTEA NULL,
    "relationship_to_holder" VARCHAR(10) NULL,
    "last_verified_date" DATE NULL,
    "last_verified_status" VARCHAR(12) NULL,
    "requires_referral" BOOLEAN NULL,
    "pcp_provider_id" INT NULL,
    "copay_amount" DECIMAL(12,2) NULL,
    "coinsurance_pct" DECIMAL(5,4) NULL,
    "deductible_remaining" DECIMAL(12,2) NULL,
    "subscriber_hash" BYTEA NULL,
    "version" SMALLINT NOT NULL,
    "is_current" BOOLEAN NOT NULL,
    "previous_coverage_id" BIGINT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_coverage" PRIMARY KEY ("coverage_id", "version")
);
CREATE TABLE "authorization" (
    "authorization_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "authorization_number" VARCHAR(50) NOT NULL,
    "patient_id" BIGINT NOT NULL,
    "payer_id" INT NOT NULL,
    "practice_id" INT NOT NULL,
    "authorization_status" VARCHAR(15) NOT NULL,
    "coverage_id" BIGINT NULL,
    "primary_cpt_code_id" INT NULL,
    "units_approved" INT NULL,
    "units_used" INT NULL,
    "valid_from" DATE NULL,
    "valid_to" DATE NULL,
    "request_date" DATE NULL,
    "decision_date" DATE NULL,
    "authorization_type" VARCHAR(15) NULL,
    "requesting_provider_id" INT NULL,
    "rendering_provider_id" INT NULL,
    "urgency" VARCHAR(10) NULL,
    "request_channel" VARCHAR(10) NULL,
    "decision_reason_code" VARCHAR(20) NULL,
    "diagnosis_code_id" INT NULL,
    "facility_id" INT NULL,
    "units_requested" INT NULL,
    "place_of_service_id" INT NULL,
    "version" SMALLINT NOT NULL,
    "is_current" BOOLEAN NOT NULL,
    "previous_authorization_id" BIGINT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_authorization" PRIMARY KEY ("authorization_id", "version")
);
CREATE TABLE "authorization_line" (
    "authorization_line_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "authorization_id" BIGINT NOT NULL,
    "line_number" SMALLINT NOT NULL,
    "cpt_code_id" INT NOT NULL,
    "cpt_code_to_id" INT NULL,
    "modifier_id" INT NULL,
    "unit_type" VARCHAR(10) NULL,
    "units_requested" INT NULL,
    "units_approved" INT NULL,
    "units_used" INT NULL,
    "line_status" VARCHAR(15) NOT NULL,
    "valid_from" DATE NULL,
    "valid_to" DATE NULL,
    "practice_id" INT NULL,
    "patient_id" BIGINT NULL,
    "payer_id" INT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_authorization_line" PRIMARY KEY ("authorization_line_id")
);
CREATE TABLE "guarantor" (
    "guarantor_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "guarantor_number" VARCHAR(50) NULL,
    "guarantor_hash" BYTEA NOT NULL,
    "guarantor_type" VARCHAR(15) NOT NULL,
    "practice_id" INT NULL,
    "state" CHAR(2) NULL,
    "zip3" CHAR(3) NULL,
    "account_status" VARCHAR(15) NOT NULL,
    "is_inferred" BOOLEAN NOT NULL,
    "has_portal_account" BOOLEAN NULL,
    "is_active" BOOLEAN NOT NULL,
    "version" SMALLINT NOT NULL,
    "is_current" BOOLEAN NOT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_guarantor" PRIMARY KEY ("guarantor_id", "version")
);
CREATE TABLE "staff" (
    "staff_id" INT NOT NULL,
    "tenant_id" INT NOT NULL,
    "staff_number" VARCHAR(30) NOT NULL,
    "practice_id" INT NULL,
    "staff_role" VARCHAR(30) NOT NULL,
    "team" VARCHAR(15) NOT NULL,
    "weekly_hours" DECIMAL(4,1) NULL,
    "start_date" DATE NULL,
    "end_date" DATE NULL,
    "is_active" BOOLEAN NOT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_staff" PRIMARY KEY ("staff_id")
);
CREATE TABLE "enrollment" (
    "enrollment_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "enrollment_number" VARCHAR(50) NULL,
    "provider_id" INT NOT NULL,
    "payer_id" INT NULL,
    "practice_id" INT NULL,
    "facility_id" INT NULL,
    "event_type" VARCHAR(15) NOT NULL,
    "event_date" DATE NOT NULL,
    "enrollment_status" VARCHAR(15) NULL,
    "enrollment_type" VARCHAR(15) NULL,
    "plan_program_code" VARCHAR(15) NULL,
    "submitted_date" DATE NULL,
    "effective_date" DATE NULL,
    "expires_date" DATE NULL,
    "revalidation_due_date" DATE NULL,
    "last_revalidated_date" DATE NULL,
    "payer_provider_number" VARCHAR(30) NULL,
    "application_number" VARCHAR(30) NULL,
    "end_reason_code" VARCHAR(20) NULL,
    "screening_source" VARCHAR(10) NULL,
    "screening_result" VARCHAR(10) NULL,
    "screening_list_date" DATE NULL,
    "exclusion_type" VARCHAR(15) NULL,
    "excluded_date" DATE NULL,
    "reinstated_date" DATE NULL,
    "match_method" VARCHAR(10) NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_enrollment" PRIMARY KEY ("enrollment_id")
);
CREATE TABLE "provider_identifier" (
    "provider_identifier_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "provider_id" INT NOT NULL,
    "identifier_type" VARCHAR(20) NOT NULL,
    "identifier_value" VARCHAR(50) NOT NULL,
    "issuing_state" CHAR(2) NULL,
    "payer_id" INT NULL,
    "effective_from" DATE NOT NULL,
    "effective_to" DATE NOT NULL,
    "verified_date" DATE NULL,
    "is_active" BOOLEAN NOT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_provider_identifier" PRIMARY KEY ("provider_identifier_id")
);
CREATE TABLE "provider_practice" (
    "provider_practice_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "provider_id" INT NOT NULL,
    "practice_id" INT NOT NULL,
    "facility_id" INT NULL,
    "affiliation_role" VARCHAR(15) NULL,
    "is_primary" BOOLEAN NULL,
    "start_date" DATE NOT NULL,
    "end_date" DATE NOT NULL,
    "fte" DECIMAL(3,2) NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_provider_practice" PRIMARY KEY ("provider_practice_id")
);
CREATE TABLE "edi_enrollment" (
    "edi_enrollment_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "practice_id" INT NOT NULL,
    "provider_id" INT NULL,
    "payer_id" INT NOT NULL,
    "transaction_type" VARCHAR(10) NOT NULL,
    "clearinghouse_code" VARCHAR(30) NULL,
    "enrollment_status" VARCHAR(12) NOT NULL,
    "submitted_date" DATE NULL,
    "effective_date" DATE NULL,
    "terminated_date" DATE NULL,
    "is_inferred" BOOLEAN NOT NULL,
    "payer_identifier_id" INT NULL,
    "version" SMALLINT NOT NULL,
    "is_current" BOOLEAN NOT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_edi_enrollment" PRIMARY KEY ("edi_enrollment_id", "version")
);
CREATE TABLE "practice" (
    "practice_id" INT NOT NULL,
    "tenant_id" INT NOT NULL,
    "practice_number" VARCHAR(50) NOT NULL,
    "practice_name" VARCHAR(200) NULL,
    "tax_id" CHAR(9) NULL,
    "group_npi" CHAR(10) NULL,
    "time_zone" VARCHAR(40) NULL,
    "fiscal_year_start_month" SMALLINT NULL,
    "go_live_date" DATE NULL,
    "is_active" BOOLEAN NOT NULL,
    "version" SMALLINT NOT NULL,
    "is_current" BOOLEAN NOT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_practice" PRIMARY KEY ("practice_id", "version")
);
CREATE TABLE "provider" (
    "provider_id" INT NOT NULL,
    "tenant_id" INT NOT NULL,
    "npi" CHAR(10) NOT NULL,
    "provider_number" VARCHAR(50) NULL,
    "provider_type" VARCHAR(12) NULL,
    "specialty_id" INT NULL,
    "taxonomy_code" VARCHAR(12) NULL,
    "credential" VARCHAR(10) NULL,
    "provider_name" VARCHAR(200) NULL,
    "practice_id" INT NULL,
    "start_date" DATE NULL,
    "end_date" DATE NULL,
    "supervising_provider_id" INT NULL,
    "is_active" BOOLEAN NOT NULL,
    "version" SMALLINT NOT NULL,
    "is_current" BOOLEAN NOT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_provider" PRIMARY KEY ("provider_id", "version")
);
CREATE TABLE "payer" (
    "payer_id" INT NOT NULL,
    "tenant_id" INT NOT NULL,
    "payer_code" VARCHAR(50) NOT NULL,
    "payer_name" VARCHAR(200) NOT NULL,
    "payer_number" VARCHAR(50) NULL,
    "payer_type" VARCHAR(20) NOT NULL,
    "parent_payer" VARCHAR(200) NULL,
    "filing_days" SMALLINT NULL,
    "corrected_claim_days" SMALLINT NULL,
    "appeal_days" SMALLINT NULL,
    "standard_turnaround_days" SMALLINT NULL,
    "supports_electronic_auth" BOOLEAN NULL,
    "state" CHAR(2) NULL,
    "dispute_contact" VARCHAR(200) NULL,
    "is_active" BOOLEAN NOT NULL,
    "filing_clock_basis" VARCHAR(30) NULL,
    "version" SMALLINT NOT NULL,
    "is_current" BOOLEAN NOT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_payer" PRIMARY KEY ("payer_id", "version")
);
CREATE TABLE "cpt_code" (
    "cpt_code_id" INT NOT NULL,
    "tenant_id" INT NULL,
    "code" VARCHAR(5) NOT NULL,
    "code_type" VARCHAR(5) NOT NULL,
    "effective_from" DATE NOT NULL,
    "effective_to" DATE NOT NULL,
    "short_label" VARCHAR(60) NULL,
    "category" VARCHAR(20) NULL,
    "em_level" SMALLINT NULL,
    "is_add_on" BOOLEAN NULL,
    "is_timed" BOOLEAN NULL,
    "unit_limit_per_day" SMALLINT NULL,
    "laterality_required" BOOLEAN NULL,
    "work_rvu" DECIMAL(8,2) NULL,
    "global_period_days" SMALLINT NULL,
    "is_unrecognized" BOOLEAN NULL,
    "is_active" BOOLEAN NOT NULL,
    "unit_limit_basis" VARCHAR(20) NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_cpt_code" PRIMARY KEY ("cpt_code_id")
);
CREATE TABLE "diagnosis_code" (
    "diagnosis_code_id" INT NOT NULL,
    "tenant_id" INT NULL,
    "icd10_code" VARCHAR(8) NOT NULL,
    "effective_from" DATE NOT NULL,
    "effective_to" DATE NOT NULL,
    "description" VARCHAR(255) NULL,
    "category" VARCHAR(30) NULL,
    "is_billable" BOOLEAN NULL,
    "is_chronic" BOOLEAN NULL,
    "is_unspecified" BOOLEAN NULL,
    "parent_code" VARCHAR(8) NULL,
    "hcc_category" VARCHAR(10) NULL,
    "is_unrecognized" BOOLEAN NULL,
    "is_active" BOOLEAN NOT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_diagnosis_code" PRIMARY KEY ("diagnosis_code_id")
);
CREATE TABLE "modifier" (
    "modifier_id" INT NOT NULL,
    "tenant_id" INT NULL,
    "modifier_code" CHAR(2) NOT NULL,
    "modifier_group" VARCHAR(20) NULL,
    "affects_payment" BOOLEAN NULL,
    "payment_adjustment_pct" DECIMAL(5,2) NULL,
    "short_label" VARCHAR(60) NULL,
    "effective_from" DATE NULL,
    "effective_to" DATE NULL,
    "is_active" BOOLEAN NOT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_modifier" PRIMARY KEY ("modifier_id")
);
CREATE TABLE "place_of_service" (
    "place_of_service_id" INT NOT NULL,
    "tenant_id" INT NULL,
    "pos_code" CHAR(2) NOT NULL,
    "pos_name" VARCHAR(80) NULL,
    "setting" VARCHAR(15) NULL,
    "is_facility" BOOLEAN NULL,
    "is_telehealth" BOOLEAN NULL,
    "effective_from" DATE NULL,
    "effective_to" DATE NULL,
    "is_active" BOOLEAN NOT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_place_of_service" PRIMARY KEY ("place_of_service_id")
);
CREATE TABLE "specialty" (
    "specialty_id" INT NOT NULL,
    "tenant_id" INT NOT NULL,
    "specialty_code" VARCHAR(20) NOT NULL,
    "specialty_name" VARCHAR(100) NOT NULL,
    "specialty_group" VARCHAR(15) NULL,
    "is_primary_care" BOOLEAN NULL,
    "cms_specialty_code" VARCHAR(5) NULL,
    "taxonomy_prefix" VARCHAR(12) NULL,
    "is_active" BOOLEAN NOT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_specialty" PRIMARY KEY ("specialty_id")
);
CREATE TABLE "facility" (
    "facility_id" INT NOT NULL,
    "tenant_id" INT NOT NULL,
    "facility_number" VARCHAR(50) NOT NULL,
    "facility_name" VARCHAR(200) NULL,
    "practice_id" INT NULL,
    "facility_type" VARCHAR(20) NULL,
    "default_place_of_service_id" INT NULL,
    "facility_npi" CHAR(10) NULL,
    "state" CHAR(2) NULL,
    "open_date" DATE NULL,
    "close_date" DATE NULL,
    "zip" VARCHAR(5) NULL,
    "rooms" SMALLINT NULL,
    "time_zone" VARCHAR(40) NULL,
    "is_active" BOOLEAN NOT NULL,
    "version" SMALLINT NOT NULL,
    "is_current" BOOLEAN NOT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_facility" PRIMARY KEY ("facility_id", "version")
);
CREATE TABLE "fee_schedule" (
    "fee_schedule_id" INT NOT NULL,
    "tenant_id" INT NOT NULL,
    "practice_id" INT NOT NULL,
    "fee_schedule_name" VARCHAR(50) NOT NULL,
    "facility_id" INT NULL,
    "fee_basis" VARCHAR(15) NULL,
    "is_default" BOOLEAN NULL,
    "is_inferred" BOOLEAN NOT NULL,
    "effective_from" DATE NOT NULL,
    "effective_to" DATE NOT NULL,
    "is_active" BOOLEAN NOT NULL,
    "version" SMALLINT NOT NULL,
    "is_current" BOOLEAN NOT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_fee_schedule" PRIMARY KEY ("fee_schedule_id", "version")
);
CREATE TABLE "fee_schedule_line" (
    "fee_schedule_line_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "fee_schedule_id" INT NOT NULL,
    "cpt_code_id" INT NOT NULL,
    "fee_per_unit" DECIMAL(12,2) NOT NULL,
    "effective_from" DATE NOT NULL,
    "is_inferred" BOOLEAN NOT NULL,
    "effective_to" DATE NULL,
    "modifier_id" INT NULL,
    "is_active" BOOLEAN NOT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_fee_schedule_line" PRIMARY KEY ("fee_schedule_line_id")
);
CREATE TABLE "contract_rate" (
    "contract_rate_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "practice_id" INT NOT NULL,
    "payer_id" INT NOT NULL,
    "payer_contract_id" INT NULL,
    "cpt_code_id" INT NOT NULL,
    "allowed_per_unit" DECIMAL(12,2) NOT NULL,
    "effective_from" DATE NOT NULL,
    "rate_source" VARCHAR(20) NOT NULL,
    "is_inferred" BOOLEAN NOT NULL,
    "effective_to" DATE NULL,
    "modifier_id" INT NULL,
    "rate_setting" VARCHAR(12) NULL,
    "contract_number" VARCHAR(50) NULL,
    "rate_basis" VARCHAR(20) NULL,
    "lesser_of_billed" BOOLEAN NULL,
    "confidence" DECIMAL(5,4) NULL,
    "sample_size" INT NULL,
    "plan_type" VARCHAR(25) NULL,
    "provider_id" INT NULL,
    "specialty_id" INT NULL,
    "multi_procedure_reduction_pct" DECIMAL(5,2) NULL,
    "dispute_days" SMALLINT NULL,
    "is_active" BOOLEAN NOT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_contract_rate" PRIMARY KEY ("contract_rate_id")
);
CREATE TABLE "adjustment_reason" (
    "adjustment_reason_id" INT NOT NULL,
    "tenant_id" INT NULL,
    "carc_code" VARCHAR(10) NOT NULL,
    "effective_from" DATE NOT NULL,
    "effective_to" DATE NOT NULL,
    "reason_class" VARCHAR(25) NOT NULL,
    "short_label" VARCHAR(60) NULL,
    "reason_category" VARCHAR(30) NULL,
    "suggested_action" VARCHAR(25) NULL,
    "owner_role" VARCHAR(20) NULL,
    "upstream_stage" VARCHAR(15) NULL,
    "is_appealable" BOOLEAN NULL,
    "is_technical" BOOLEAN NULL,
    "is_preventable_default" BOOLEAN NULL,
    "typical_group" CHAR(2) NULL,
    "is_unrecognized" BOOLEAN NOT NULL,
    "is_active" BOOLEAN NOT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_adjustment_reason" PRIMARY KEY ("adjustment_reason_id")
);
CREATE TABLE "remark_code" (
    "remark_code_id" INT NOT NULL,
    "tenant_id" INT NULL,
    "rarc_code" VARCHAR(10) NOT NULL,
    "effective_from" DATE NOT NULL,
    "effective_to" DATE NOT NULL,
    "code_qualifier" VARCHAR(5) NULL,
    "short_label" VARCHAR(60) NULL,
    "remark_type" VARCHAR(15) NULL,
    "suggests_action" VARCHAR(25) NULL,
    "documents_needed" VARCHAR(30) NULL,
    "related_reason_code" VARCHAR(10) NULL,
    "is_unrecognized" BOOLEAN NOT NULL,
    "is_active" BOOLEAN NOT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_remark_code" PRIMARY KEY ("remark_code_id")
);
CREATE TABLE "practice_settings" (
    "practice_settings_id" INT NOT NULL,
    "tenant_id" INT NOT NULL,
    "practice_id" INT NULL,
    "setting_key" VARCHAR(50) NOT NULL,
    "setting_value" VARCHAR(100) NOT NULL,
    "value_type" VARCHAR(10) NOT NULL,
    "effective_from" DATE NOT NULL,
    "effective_to" DATE NOT NULL,
    "set_by_role" VARCHAR(20) NULL,
    "approved_by_staff_id" INT NULL,
    "is_active" BOOLEAN NOT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_practice_settings" PRIMARY KEY ("practice_settings_id")
);
CREATE TABLE "payer_rule" (
    "payer_rule_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "payer_rule_number" VARCHAR(50) NULL,
    "rule_code" VARCHAR(50) NOT NULL,
    "rule_family" VARCHAR(30) NOT NULL,
    "rule_action" VARCHAR(25) NOT NULL,
    "rule_source_code" VARCHAR(20) NOT NULL,
    "rule_source_ref" VARCHAR(50) NULL,
    "payer_id" INT NULL,
    "plan_type" VARCHAR(25) NULL,
    "place_of_service_id" INT NULL,
    "practice_id" INT NULL,
    "cpt_code_id" INT NULL,
    "cpt_code_to_id" INT NULL,
    "paired_cpt_code_id" INT NULL,
    "modifier_id" INT NULL,
    "diagnosis_code_id" INT NULL,
    "adjustment_reason_id" INT NULL,
    "edit_field_code" VARCHAR(30) NULL,
    "requirement_code" VARCHAR(20) NULL,
    "unit_limit" SMALLINT NULL,
    "unit_limit_basis" VARCHAR(20) NULL,
    "evidence_claim_count" INT NULL,
    "evidence_denied_count" INT NULL,
    "evidence_denied_amount" DECIMAL(12,2) NULL,
    "evidence_from_date" DATE NULL,
    "evidence_to_date" DATE NULL,
    "owner_role" VARCHAR(20) NULL,
    "severity" VARCHAR(10) NULL,
    "is_enabled" BOOLEAN NOT NULL,
    "is_synthetic" BOOLEAN NOT NULL,
    "approval_status" VARCHAR(15) NOT NULL,
    "approved_by_staff_id" INT NULL,
    "approved_date" DATE NULL,
    "last_confirmed_date" DATE NULL,
    "effective_from" DATE NOT NULL,
    "effective_to" DATE NULL,
    "retire_reason_code" VARCHAR(20) NULL,
    "version" SMALLINT NOT NULL,
    "is_current" BOOLEAN NOT NULL,
    "previous_payer_rule_id" BIGINT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_payer_rule" PRIMARY KEY ("payer_rule_id", "version")
);
CREATE TABLE "calendar" (
    "calendar_id" INT NOT NULL,
    "tenant_id" INT NULL,
    "practice_id" INT NULL,
    "calendar_date" DATE NOT NULL,
    "is_business_day" BOOLEAN NOT NULL,
    "is_holiday" BOOLEAN NOT NULL,
    "holiday_code" VARCHAR(20) NULL,
    "business_day_number" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_calendar" PRIMARY KEY ("calendar_id")
);
CREATE TABLE "payer_identifier" (
    "payer_identifier_id" INT NOT NULL,
    "tenant_id" INT NOT NULL,
    "payer_id" INT NOT NULL,
    "identifier_value" VARCHAR(50) NOT NULL,
    "identifier_type" VARCHAR(20) NOT NULL,
    "clearinghouse_code" VARCHAR(30) NULL,
    "effective_from" DATE NOT NULL,
    "effective_to" DATE NOT NULL,
    "is_active" BOOLEAN NOT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_payer_identifier" PRIMARY KEY ("payer_identifier_id")
);
CREATE TABLE "payer_plan" (
    "payer_plan_id" INT NOT NULL,
    "tenant_id" INT NOT NULL,
    "payer_id" INT NOT NULL,
    "plan_code" VARCHAR(50) NOT NULL,
    "plan_name" VARCHAR(100) NULL,
    "plan_type" VARCHAR(25) NULL,
    "product_line" VARCHAR(20) NULL,
    "requires_referral" BOOLEAN NULL,
    "filing_days" SMALLINT NULL,
    "appeal_days" SMALLINT NULL,
    "state" CHAR(2) NULL,
    "effective_from" DATE NOT NULL,
    "effective_to" DATE NOT NULL,
    "is_active" BOOLEAN NOT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_payer_plan" PRIMARY KEY ("payer_plan_id")
);
CREATE TABLE "payer_contract" (
    "payer_contract_id" INT NOT NULL,
    "tenant_id" INT NOT NULL,
    "practice_id" INT NOT NULL,
    "payer_id" INT NOT NULL,
    "payer_plan_id" INT NULL,
    "contract_number" VARCHAR(50) NULL,
    "contract_status" VARCHAR(12) NOT NULL,
    "effective_from" DATE NOT NULL,
    "effective_to" DATE NOT NULL,
    "filing_days" SMALLINT NULL,
    "corrected_claim_days" SMALLINT NULL,
    "appeal_days" SMALLINT NULL,
    "lesser_of_billed" BOOLEAN NULL,
    "default_rate_basis" VARCHAR(20) NULL,
    "default_pct_of_medicare" DECIMAL(6,2) NULL,
    "escalator_pct" DECIMAL(5,2) NULL,
    "renewal_notice_days" SMALLINT NULL,
    "document_hash" BYTEA NULL,
    "version" SMALLINT NOT NULL,
    "is_current" BOOLEAN NOT NULL,
    "created_at" TIMESTAMP(0) NULL,
    "created_by_staff_id" INT NULL,
    "modified_at" TIMESTAMP(0) NULL,
    "modified_by_staff_id" INT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_payer_contract" PRIMARY KEY ("payer_contract_id", "version")
);
CREATE TABLE "claim_status_code" (
    "claim_status_code_id" INT NOT NULL,
    "tenant_id" INT NULL,
    "code_set" VARCHAR(10) NOT NULL,
    "code" VARCHAR(5) NOT NULL,
    "short_label" VARCHAR(100) NOT NULL,
    "status_group" VARCHAR(15) NULL,
    "is_rejection" BOOLEAN NULL,
    "effective_from" DATE NOT NULL,
    "effective_to" DATE NOT NULL,
    "is_unrecognized" BOOLEAN NOT NULL,
    "is_active" BOOLEAN NOT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_claim_status_code" PRIMARY KEY ("claim_status_code_id")
);
CREATE TABLE "ndc_code" (
    "ndc_code_id" INT NOT NULL,
    "tenant_id" INT NULL,
    "ndc_11" CHAR(11) NOT NULL,
    "product_label" VARCHAR(100) NULL,
    "hcpcs_cpt_code_id" INT NULL,
    "billing_unit" CHAR(2) NULL,
    "package_quantity" DECIMAL(12,3) NULL,
    "hcpcs_units_per_package" DECIMAL(12,3) NULL,
    "effective_from" DATE NOT NULL,
    "effective_to" DATE NOT NULL,
    "is_unrecognized" BOOLEAN NOT NULL,
    "is_active" BOOLEAN NOT NULL,
    "load_batch_id" BIGINT NOT NULL,
    "source_record_hash" BYTEA NULL,
    "is_source_deleted" BOOLEAN NOT NULL,
    "source_deleted_at" TIMESTAMP(0) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_ndc_code" PRIMARY KEY ("ndc_code_id")
);
CREATE TABLE "tenant" (
    "tenant_id" INT NOT NULL,
    "tenant_code" VARCHAR(30) NOT NULL,
    "tenant_name" VARCHAR(200) NOT NULL,
    "tenant_status" VARCHAR(12) NOT NULL,
    "baa_signed_date" DATE NOT NULL,
    "salt_key_ref" VARCHAR(100) NOT NULL,
    "data_region" VARCHAR(20) NULL,
    "go_live_date" DATE NULL,
    "retention_years" SMALLINT NULL,
    "offboard_date" DATE NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_tenant" PRIMARY KEY ("tenant_id")
);
CREATE TABLE "data_feed" (
    "data_feed_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "table_name" VARCHAR(40) NOT NULL,
    "feed_name" VARCHAR(80) NOT NULL,
    "source_system" VARCHAR(20) NOT NULL,
    "feed_status" VARCHAR(15) NOT NULL,
    "fallback_level" SMALLINT NOT NULL,
    "practice_id" INT NULL,
    "source_kind" VARCHAR(15) NULL,
    "load_frequency" VARCHAR(10) NULL,
    "first_data_date" DATE NULL,
    "last_data_date" DATE NULL,
    "last_load_at" TIMESTAMP(0) NULL,
    "rows_loaded" BIGINT NULL,
    "completeness_pct" DECIMAL(5,2) NULL,
    "freshness_hours" SMALLINT NULL,
    "reliability_default" DECIMAL(3,2) NULL,
    "expected_row_count" BIGINT NULL,
    "version" SMALLINT NOT NULL,
    "is_current" BOOLEAN NOT NULL,
    "previous_data_feed_id" BIGINT NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_data_feed" PRIMARY KEY ("data_feed_id", "version")
);
CREATE TABLE "edi_file" (
    "edi_file_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "data_feed_id" BIGINT NULL,
    "load_batch_id" BIGINT NULL,
    "transaction_set" VARCHAR(5) NOT NULL,
    "direction" CHAR(1) NOT NULL,
    "interchange_control_number" VARCHAR(9) NOT NULL,
    "group_control_number" VARCHAR(9) NULL,
    "clearinghouse_code" VARCHAR(30) NULL,
    "file_hash" BYTEA NOT NULL,
    "file_name_hash" BYTEA NULL,
    "received_at" TIMESTAMP(0) NOT NULL,
    "transaction_count" INT NULL,
    "file_status" VARCHAR(12) NOT NULL,
    "parse_error_count" INT NULL,
    "replaced_by_edi_file_id" BIGINT NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_edi_file" PRIMARY KEY ("edi_file_id")
);
CREATE TABLE "load_batch" (
    "load_batch_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "data_feed_id" BIGINT NOT NULL,
    "started_at" TIMESTAMP(0) NOT NULL,
    "ended_at" TIMESTAMP(0) NULL,
    "batch_status" VARCHAR(12) NOT NULL,
    "rows_read" BIGINT NULL,
    "rows_inserted" BIGINT NULL,
    "rows_unchanged" BIGINT NULL,
    "rows_rejected" BIGINT NULL,
    "source_watermark" VARCHAR(50) NULL,
    "code_version" VARCHAR(30) NULL,
    "rolled_back_at" TIMESTAMP(0) NULL,
    "error_summary" VARCHAR(200) NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_load_batch" PRIMARY KEY ("load_batch_id")
);
CREATE TABLE "data_quality_result" (
    "data_quality_result_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "load_batch_id" BIGINT NULL,
    "dq_rule_code" VARCHAR(50) NOT NULL,
    "table_name" VARCHAR(40) NOT NULL,
    "column_name" VARCHAR(60) NULL,
    "severity" VARCHAR(10) NOT NULL,
    "rows_checked" BIGINT NULL,
    "rows_failed" BIGINT NOT NULL,
    "sample_ref" VARCHAR(100) NULL,
    "run_at" TIMESTAMP(0) NOT NULL,
    "dq_status" VARCHAR(12) NOT NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_data_quality_result" PRIMARY KEY ("data_quality_result_id")
);
CREATE TABLE "access_audit" (
    "access_audit_id" BIGINT NOT NULL,
    "tenant_id" INT NOT NULL,
    "accessed_at" TIMESTAMP(0) NOT NULL,
    "actor_type" VARCHAR(10) NOT NULL,
    "staff_id" INT NULL,
    "agent_run_id" BIGINT NULL,
    "action" VARCHAR(15) NOT NULL,
    "table_name" VARCHAR(40) NOT NULL,
    "row_count" INT NULL,
    "touched_restricted" BOOLEAN NOT NULL,
    "purpose_code" VARCHAR(20) NULL,
    "query_hash" BYTEA NULL,
    "source" VARCHAR(30) NOT NULL,
    "loaded_at" TIMESTAMP(0) NOT NULL,
    CONSTRAINT "pk_access_audit" PRIMARY KEY ("access_audit_id")
);
ALTER TABLE "appointment" ADD CONSTRAINT "FK_appointment_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "appointment" ADD CONSTRAINT "FK_appointment_patient_id" FOREIGN KEY ("patient_id") REFERENCES "patient" ("patient_id");
ALTER TABLE "appointment" ADD CONSTRAINT "FK_appointment_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "appointment" ADD CONSTRAINT "FK_appointment_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "appointment" ADD CONSTRAINT "FK_appointment_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "appointment_status_log" ADD CONSTRAINT "FK_appointment_status_log_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "appointment_status_log" ADD CONSTRAINT "FK_appointment_status_log_changed_by_staff_id" FOREIGN KEY ("changed_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "appointment_status_log" ADD CONSTRAINT "FK_appointment_status_log_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "referral" ADD CONSTRAINT "FK_referral_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "referral" ADD CONSTRAINT "FK_referral_patient_id" FOREIGN KEY ("patient_id") REFERENCES "patient" ("patient_id");
ALTER TABLE "referral" ADD CONSTRAINT "FK_referral_specialty_id" FOREIGN KEY ("specialty_id") REFERENCES "specialty" ("specialty_id");
ALTER TABLE "referral" ADD CONSTRAINT "FK_referral_diagnosis_code_id" FOREIGN KEY ("diagnosis_code_id") REFERENCES "diagnosis_code" ("diagnosis_code_id");
ALTER TABLE "referral" ADD CONSTRAINT "FK_referral_cpt_code_id" FOREIGN KEY ("cpt_code_id") REFERENCES "cpt_code" ("cpt_code_id");
ALTER TABLE "referral" ADD CONSTRAINT "FK_referral_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "referral" ADD CONSTRAINT "FK_referral_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "referral" ADD CONSTRAINT "FK_referral_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "appointment_line" ADD CONSTRAINT "FK_appointment_line_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "appointment_line" ADD CONSTRAINT "FK_appointment_line_patient_id" FOREIGN KEY ("patient_id") REFERENCES "patient" ("patient_id");
ALTER TABLE "appointment_line" ADD CONSTRAINT "FK_appointment_line_specialty_id" FOREIGN KEY ("specialty_id") REFERENCES "specialty" ("specialty_id");
ALTER TABLE "appointment_line" ADD CONSTRAINT "FK_appointment_line_planned_cpt_code_id" FOREIGN KEY ("planned_cpt_code_id") REFERENCES "cpt_code" ("cpt_code_id");
ALTER TABLE "appointment_line" ADD CONSTRAINT "FK_appointment_line_planned_diagnosis_code_id" FOREIGN KEY ("planned_diagnosis_code_id") REFERENCES "diagnosis_code" ("diagnosis_code_id");
ALTER TABLE "appointment_line" ADD CONSTRAINT "FK_appointment_line_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "appointment_line" ADD CONSTRAINT "FK_appointment_line_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "appointment_line" ADD CONSTRAINT "FK_appointment_line_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "appointment_slot" ADD CONSTRAINT "FK_appointment_slot_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "appointment_slot" ADD CONSTRAINT "FK_appointment_slot_specialty_id" FOREIGN KEY ("specialty_id") REFERENCES "specialty" ("specialty_id");
ALTER TABLE "appointment_slot" ADD CONSTRAINT "FK_appointment_slot_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "appointment_slot" ADD CONSTRAINT "FK_appointment_slot_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "appointment_slot" ADD CONSTRAINT "FK_appointment_slot_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "eligibility_check" ADD CONSTRAINT "FK_eligibility_check_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "eligibility_check" ADD CONSTRAINT "FK_eligibility_check_patient_id" FOREIGN KEY ("patient_id") REFERENCES "patient" ("patient_id");
ALTER TABLE "eligibility_check" ADD CONSTRAINT "FK_eligibility_check_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "eligibility_check" ADD CONSTRAINT "FK_eligibility_check_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "eligibility_check" ADD CONSTRAINT "FK_eligibility_check_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "patient_estimate" ADD CONSTRAINT "FK_patient_estimate_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "patient_estimate" ADD CONSTRAINT "FK_patient_estimate_patient_id" FOREIGN KEY ("patient_id") REFERENCES "patient" ("patient_id");
ALTER TABLE "patient_estimate" ADD CONSTRAINT "FK_patient_estimate_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "patient_estimate" ADD CONSTRAINT "FK_patient_estimate_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "patient_estimate" ADD CONSTRAINT "FK_patient_estimate_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "eligibility_benefit" ADD CONSTRAINT "FK_eligibility_benefit_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "eligibility_benefit" ADD CONSTRAINT "FK_eligibility_benefit_eligibility_check_id" FOREIGN KEY ("eligibility_check_id") REFERENCES "eligibility_check" ("eligibility_check_id");
ALTER TABLE "eligibility_benefit" ADD CONSTRAINT "FK_eligibility_benefit_cpt_code_id" FOREIGN KEY ("cpt_code_id") REFERENCES "cpt_code" ("cpt_code_id");
ALTER TABLE "eligibility_benefit" ADD CONSTRAINT "FK_eligibility_benefit_patient_id" FOREIGN KEY ("patient_id") REFERENCES "patient" ("patient_id");
ALTER TABLE "eligibility_benefit" ADD CONSTRAINT "FK_eligibility_benefit_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "eligibility_benefit" ADD CONSTRAINT "FK_eligibility_benefit_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "eligibility_benefit" ADD CONSTRAINT "FK_eligibility_benefit_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "patient_estimate_line" ADD CONSTRAINT "FK_patient_estimate_line_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "patient_estimate_line" ADD CONSTRAINT "FK_patient_estimate_line_cpt_code_id" FOREIGN KEY ("cpt_code_id") REFERENCES "cpt_code" ("cpt_code_id");
ALTER TABLE "patient_estimate_line" ADD CONSTRAINT "FK_patient_estimate_line_modifier_id" FOREIGN KEY ("modifier_id") REFERENCES "modifier" ("modifier_id");
ALTER TABLE "patient_estimate_line" ADD CONSTRAINT "FK_patient_estimate_line_diagnosis_code_id" FOREIGN KEY ("diagnosis_code_id") REFERENCES "diagnosis_code" ("diagnosis_code_id");
ALTER TABLE "patient_estimate_line" ADD CONSTRAINT "FK_patient_estimate_line_appointment_line_id" FOREIGN KEY ("appointment_line_id") REFERENCES "appointment_line" ("appointment_line_id");
ALTER TABLE "patient_estimate_line" ADD CONSTRAINT "FK_patient_estimate_line_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "patient_estimate_line" ADD CONSTRAINT "FK_patient_estimate_line_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "patient_estimate_line" ADD CONSTRAINT "FK_patient_estimate_line_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "encounter" ADD CONSTRAINT "FK_encounter_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "encounter" ADD CONSTRAINT "FK_encounter_patient_id" FOREIGN KEY ("patient_id") REFERENCES "patient" ("patient_id");
ALTER TABLE "encounter" ADD CONSTRAINT "FK_encounter_place_of_service_id" FOREIGN KEY ("place_of_service_id") REFERENCES "place_of_service" ("place_of_service_id");
ALTER TABLE "encounter" ADD CONSTRAINT "FK_encounter_specialty_id" FOREIGN KEY ("specialty_id") REFERENCES "specialty" ("specialty_id");
ALTER TABLE "encounter" ADD CONSTRAINT "FK_encounter_principal_diagnosis_code_id" FOREIGN KEY ("principal_diagnosis_code_id") REFERENCES "diagnosis_code" ("diagnosis_code_id");
ALTER TABLE "encounter" ADD CONSTRAINT "FK_encounter_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "encounter" ADD CONSTRAINT "FK_encounter_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "encounter" ADD CONSTRAINT "FK_encounter_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "document" ADD CONSTRAINT "FK_document_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "document" ADD CONSTRAINT "FK_document_patient_id" FOREIGN KEY ("patient_id") REFERENCES "patient" ("patient_id");
ALTER TABLE "document" ADD CONSTRAINT "FK_document_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "document" ADD CONSTRAINT "FK_document_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "document" ADD CONSTRAINT "FK_document_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "clinical_order" ADD CONSTRAINT "FK_clinical_order_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "clinical_order" ADD CONSTRAINT "FK_clinical_order_patient_id" FOREIGN KEY ("patient_id") REFERENCES "patient" ("patient_id");
ALTER TABLE "clinical_order" ADD CONSTRAINT "FK_clinical_order_encounter_line_id" FOREIGN KEY ("encounter_line_id") REFERENCES "encounter_line" ("encounter_line_id");
ALTER TABLE "clinical_order" ADD CONSTRAINT "FK_clinical_order_cpt_code_id" FOREIGN KEY ("cpt_code_id") REFERENCES "cpt_code" ("cpt_code_id");
ALTER TABLE "clinical_order" ADD CONSTRAINT "FK_clinical_order_diagnosis_code_id" FOREIGN KEY ("diagnosis_code_id") REFERENCES "diagnosis_code" ("diagnosis_code_id");
ALTER TABLE "clinical_order" ADD CONSTRAINT "FK_clinical_order_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "clinical_order" ADD CONSTRAINT "FK_clinical_order_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "clinical_order" ADD CONSTRAINT "FK_clinical_order_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "encounter_line" ADD CONSTRAINT "FK_encounter_line_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "encounter_line" ADD CONSTRAINT "FK_encounter_line_patient_id" FOREIGN KEY ("patient_id") REFERENCES "patient" ("patient_id");
ALTER TABLE "encounter_line" ADD CONSTRAINT "FK_encounter_line_specialty_id" FOREIGN KEY ("specialty_id") REFERENCES "specialty" ("specialty_id");
ALTER TABLE "encounter_line" ADD CONSTRAINT "FK_encounter_line_cpt_code_id" FOREIGN KEY ("cpt_code_id") REFERENCES "cpt_code" ("cpt_code_id");
ALTER TABLE "encounter_line" ADD CONSTRAINT "FK_encounter_line_diagnosis_1_id" FOREIGN KEY ("diagnosis_1_id") REFERENCES "diagnosis_code" ("diagnosis_code_id");
ALTER TABLE "encounter_line" ADD CONSTRAINT "FK_encounter_line_diagnosis_2_id" FOREIGN KEY ("diagnosis_2_id") REFERENCES "diagnosis_code" ("diagnosis_code_id");
ALTER TABLE "encounter_line" ADD CONSTRAINT "FK_encounter_line_diagnosis_3_id" FOREIGN KEY ("diagnosis_3_id") REFERENCES "diagnosis_code" ("diagnosis_code_id");
ALTER TABLE "encounter_line" ADD CONSTRAINT "FK_encounter_line_diagnosis_4_id" FOREIGN KEY ("diagnosis_4_id") REFERENCES "diagnosis_code" ("diagnosis_code_id");
ALTER TABLE "encounter_line" ADD CONSTRAINT "FK_encounter_line_modifier_1_id" FOREIGN KEY ("modifier_1_id") REFERENCES "modifier" ("modifier_id");
ALTER TABLE "encounter_line" ADD CONSTRAINT "FK_encounter_line_modifier_2_id" FOREIGN KEY ("modifier_2_id") REFERENCES "modifier" ("modifier_id");
ALTER TABLE "encounter_line" ADD CONSTRAINT "FK_encounter_line_modifier_3_id" FOREIGN KEY ("modifier_3_id") REFERENCES "modifier" ("modifier_id");
ALTER TABLE "encounter_line" ADD CONSTRAINT "FK_encounter_line_modifier_4_id" FOREIGN KEY ("modifier_4_id") REFERENCES "modifier" ("modifier_id");
ALTER TABLE "encounter_line" ADD CONSTRAINT "FK_encounter_line_place_of_service_id" FOREIGN KEY ("place_of_service_id") REFERENCES "place_of_service" ("place_of_service_id");
ALTER TABLE "encounter_line" ADD CONSTRAINT "FK_encounter_line_ndc_code_id" FOREIGN KEY ("ndc_code_id") REFERENCES "ndc_code" ("ndc_code_id");
ALTER TABLE "encounter_line" ADD CONSTRAINT "FK_encounter_line_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "encounter_line" ADD CONSTRAINT "FK_encounter_line_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "encounter_line" ADD CONSTRAINT "FK_encounter_line_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "encounter_diagnosis" ADD CONSTRAINT "FK_encounter_diagnosis_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "encounter_diagnosis" ADD CONSTRAINT "FK_encounter_diagnosis_diagnosis_code_id" FOREIGN KEY ("diagnosis_code_id") REFERENCES "diagnosis_code" ("diagnosis_code_id");
ALTER TABLE "encounter_diagnosis" ADD CONSTRAINT "FK_encounter_diagnosis_patient_id" FOREIGN KEY ("patient_id") REFERENCES "patient" ("patient_id");
ALTER TABLE "encounter_diagnosis" ADD CONSTRAINT "FK_encounter_diagnosis_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "encounter_diagnosis" ADD CONSTRAINT "FK_encounter_diagnosis_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "encounter_diagnosis" ADD CONSTRAINT "FK_encounter_diagnosis_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "document_element" ADD CONSTRAINT "FK_document_element_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "document_element" ADD CONSTRAINT "FK_document_element_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "document_element" ADD CONSTRAINT "FK_document_element_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "document_element" ADD CONSTRAINT "FK_document_element_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "bill" ADD CONSTRAINT "FK_bill_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "bill" ADD CONSTRAINT "FK_bill_patient_id" FOREIGN KEY ("patient_id") REFERENCES "patient" ("patient_id");
ALTER TABLE "bill" ADD CONSTRAINT "FK_bill_specialty_id" FOREIGN KEY ("specialty_id") REFERENCES "specialty" ("specialty_id");
ALTER TABLE "bill" ADD CONSTRAINT "FK_bill_place_of_service_id" FOREIGN KEY ("place_of_service_id") REFERENCES "place_of_service" ("place_of_service_id");
ALTER TABLE "bill" ADD CONSTRAINT "FK_bill_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "bill" ADD CONSTRAINT "FK_bill_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "bill" ADD CONSTRAINT "FK_bill_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "claim" ADD CONSTRAINT "FK_claim_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "claim" ADD CONSTRAINT "FK_claim_patient_id" FOREIGN KEY ("patient_id") REFERENCES "patient" ("patient_id");
ALTER TABLE "claim" ADD CONSTRAINT "FK_claim_place_of_service_id" FOREIGN KEY ("place_of_service_id") REFERENCES "place_of_service" ("place_of_service_id");
ALTER TABLE "claim" ADD CONSTRAINT "FK_claim_specialty_id" FOREIGN KEY ("specialty_id") REFERENCES "specialty" ("specialty_id");
ALTER TABLE "claim" ADD CONSTRAINT "FK_claim_principal_diagnosis_code_id" FOREIGN KEY ("principal_diagnosis_code_id") REFERENCES "diagnosis_code" ("diagnosis_code_id");
ALTER TABLE "claim" ADD CONSTRAINT "FK_claim_edi_file_id" FOREIGN KEY ("edi_file_id") REFERENCES "edi_file" ("edi_file_id");
ALTER TABLE "claim" ADD CONSTRAINT "FK_claim_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "claim" ADD CONSTRAINT "FK_claim_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "claim" ADD CONSTRAINT "FK_claim_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "claim_attachment" ADD CONSTRAINT "FK_claim_attachment_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "claim_attachment" ADD CONSTRAINT "FK_claim_attachment_patient_id" FOREIGN KEY ("patient_id") REFERENCES "patient" ("patient_id");
ALTER TABLE "claim_attachment" ADD CONSTRAINT "FK_claim_attachment_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "claim_attachment" ADD CONSTRAINT "FK_claim_attachment_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "claim_attachment" ADD CONSTRAINT "FK_claim_attachment_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "bill_line" ADD CONSTRAINT "FK_bill_line_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "bill_line" ADD CONSTRAINT "FK_bill_line_patient_id" FOREIGN KEY ("patient_id") REFERENCES "patient" ("patient_id");
ALTER TABLE "bill_line" ADD CONSTRAINT "FK_bill_line_specialty_id" FOREIGN KEY ("specialty_id") REFERENCES "specialty" ("specialty_id");
ALTER TABLE "bill_line" ADD CONSTRAINT "FK_bill_line_cpt_code_id" FOREIGN KEY ("cpt_code_id") REFERENCES "cpt_code" ("cpt_code_id");
ALTER TABLE "bill_line" ADD CONSTRAINT "FK_bill_line_modifier_1_id" FOREIGN KEY ("modifier_1_id") REFERENCES "modifier" ("modifier_id");
ALTER TABLE "bill_line" ADD CONSTRAINT "FK_bill_line_modifier_2_id" FOREIGN KEY ("modifier_2_id") REFERENCES "modifier" ("modifier_id");
ALTER TABLE "bill_line" ADD CONSTRAINT "FK_bill_line_modifier_3_id" FOREIGN KEY ("modifier_3_id") REFERENCES "modifier" ("modifier_id");
ALTER TABLE "bill_line" ADD CONSTRAINT "FK_bill_line_modifier_4_id" FOREIGN KEY ("modifier_4_id") REFERENCES "modifier" ("modifier_id");
ALTER TABLE "bill_line" ADD CONSTRAINT "FK_bill_line_diagnosis_1_id" FOREIGN KEY ("diagnosis_1_id") REFERENCES "diagnosis_code" ("diagnosis_code_id");
ALTER TABLE "bill_line" ADD CONSTRAINT "FK_bill_line_diagnosis_2_id" FOREIGN KEY ("diagnosis_2_id") REFERENCES "diagnosis_code" ("diagnosis_code_id");
ALTER TABLE "bill_line" ADD CONSTRAINT "FK_bill_line_diagnosis_3_id" FOREIGN KEY ("diagnosis_3_id") REFERENCES "diagnosis_code" ("diagnosis_code_id");
ALTER TABLE "bill_line" ADD CONSTRAINT "FK_bill_line_diagnosis_4_id" FOREIGN KEY ("diagnosis_4_id") REFERENCES "diagnosis_code" ("diagnosis_code_id");
ALTER TABLE "bill_line" ADD CONSTRAINT "FK_bill_line_encounter_line_id" FOREIGN KEY ("encounter_line_id") REFERENCES "encounter_line" ("encounter_line_id");
ALTER TABLE "bill_line" ADD CONSTRAINT "FK_bill_line_cpt_as_entered_id" FOREIGN KEY ("cpt_as_entered_id") REFERENCES "cpt_code" ("cpt_code_id");
ALTER TABLE "bill_line" ADD CONSTRAINT "FK_bill_line_change_approved_by_staff_id" FOREIGN KEY ("change_approved_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "bill_line" ADD CONSTRAINT "FK_bill_line_ndc_code_id" FOREIGN KEY ("ndc_code_id") REFERENCES "ndc_code" ("ndc_code_id");
ALTER TABLE "bill_line" ADD CONSTRAINT "FK_bill_line_place_of_service_id" FOREIGN KEY ("place_of_service_id") REFERENCES "place_of_service" ("place_of_service_id");
ALTER TABLE "bill_line" ADD CONSTRAINT "FK_bill_line_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "bill_line" ADD CONSTRAINT "FK_bill_line_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "bill_line" ADD CONSTRAINT "FK_bill_line_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "claim_line" ADD CONSTRAINT "FK_claim_line_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "claim_line" ADD CONSTRAINT "FK_claim_line_patient_id" FOREIGN KEY ("patient_id") REFERENCES "patient" ("patient_id");
ALTER TABLE "claim_line" ADD CONSTRAINT "FK_claim_line_specialty_id" FOREIGN KEY ("specialty_id") REFERENCES "specialty" ("specialty_id");
ALTER TABLE "claim_line" ADD CONSTRAINT "FK_claim_line_cpt_code_id" FOREIGN KEY ("cpt_code_id") REFERENCES "cpt_code" ("cpt_code_id");
ALTER TABLE "claim_line" ADD CONSTRAINT "FK_claim_line_place_of_service_id" FOREIGN KEY ("place_of_service_id") REFERENCES "place_of_service" ("place_of_service_id");
ALTER TABLE "claim_line" ADD CONSTRAINT "FK_claim_line_modifier_1_id" FOREIGN KEY ("modifier_1_id") REFERENCES "modifier" ("modifier_id");
ALTER TABLE "claim_line" ADD CONSTRAINT "FK_claim_line_modifier_2_id" FOREIGN KEY ("modifier_2_id") REFERENCES "modifier" ("modifier_id");
ALTER TABLE "claim_line" ADD CONSTRAINT "FK_claim_line_modifier_3_id" FOREIGN KEY ("modifier_3_id") REFERENCES "modifier" ("modifier_id");
ALTER TABLE "claim_line" ADD CONSTRAINT "FK_claim_line_modifier_4_id" FOREIGN KEY ("modifier_4_id") REFERENCES "modifier" ("modifier_id");
ALTER TABLE "claim_line" ADD CONSTRAINT "FK_claim_line_primary_diagnosis_code_id" FOREIGN KEY ("primary_diagnosis_code_id") REFERENCES "diagnosis_code" ("diagnosis_code_id");
ALTER TABLE "claim_line" ADD CONSTRAINT "FK_claim_line_primary_denial_reason_id" FOREIGN KEY ("primary_denial_reason_id") REFERENCES "adjustment_reason" ("adjustment_reason_id");
ALTER TABLE "claim_line" ADD CONSTRAINT "FK_claim_line_bill_line_id" FOREIGN KEY ("bill_line_id") REFERENCES "bill_line" ("bill_line_id");
ALTER TABLE "claim_line" ADD CONSTRAINT "FK_claim_line_ndc_code_id" FOREIGN KEY ("ndc_code_id") REFERENCES "ndc_code" ("ndc_code_id");
ALTER TABLE "claim_line" ADD CONSTRAINT "FK_claim_line_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "claim_line" ADD CONSTRAINT "FK_claim_line_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "claim_line" ADD CONSTRAINT "FK_claim_line_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "claim_status_history" ADD CONSTRAINT "FK_claim_status_history_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "claim_status_history" ADD CONSTRAINT "FK_claim_status_history_claim_line_id" FOREIGN KEY ("claim_line_id") REFERENCES "claim_line" ("claim_line_id");
ALTER TABLE "claim_status_history" ADD CONSTRAINT "FK_claim_status_history_patient_id" FOREIGN KEY ("patient_id") REFERENCES "patient" ("patient_id");
ALTER TABLE "claim_status_history" ADD CONSTRAINT "FK_claim_status_history_status_category_code_id" FOREIGN KEY ("status_category_code_id") REFERENCES "claim_status_code" ("claim_status_code_id");
ALTER TABLE "claim_status_history" ADD CONSTRAINT "FK_claim_status_history_status_code_id" FOREIGN KEY ("status_code_id") REFERENCES "claim_status_code" ("claim_status_code_id");
ALTER TABLE "claim_status_history" ADD CONSTRAINT "FK_claim_status_history_specialty_id" FOREIGN KEY ("specialty_id") REFERENCES "specialty" ("specialty_id");
ALTER TABLE "claim_status_history" ADD CONSTRAINT "FK_claim_status_history_edi_file_id" FOREIGN KEY ("edi_file_id") REFERENCES "edi_file" ("edi_file_id");
ALTER TABLE "claim_status_history" ADD CONSTRAINT "FK_claim_status_history_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "claim_status_history" ADD CONSTRAINT "FK_claim_status_history_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "claim_status_history" ADD CONSTRAINT "FK_claim_status_history_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "claim_diagnosis" ADD CONSTRAINT "FK_claim_diagnosis_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "claim_diagnosis" ADD CONSTRAINT "FK_claim_diagnosis_diagnosis_code_id" FOREIGN KEY ("diagnosis_code_id") REFERENCES "diagnosis_code" ("diagnosis_code_id");
ALTER TABLE "claim_diagnosis" ADD CONSTRAINT "FK_claim_diagnosis_patient_id" FOREIGN KEY ("patient_id") REFERENCES "patient" ("patient_id");
ALTER TABLE "claim_diagnosis" ADD CONSTRAINT "FK_claim_diagnosis_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "claim_diagnosis" ADD CONSTRAINT "FK_claim_diagnosis_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "claim_diagnosis" ADD CONSTRAINT "FK_claim_diagnosis_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "claim_attachment_document" ADD CONSTRAINT "FK_claim_attachment_document_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "claim_attachment_document" ADD CONSTRAINT "FK_claim_attachment_document_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "claim_attachment_document" ADD CONSTRAINT "FK_claim_attachment_document_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "claim_attachment_document" ADD CONSTRAINT "FK_claim_attachment_document_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "claim_edit" ADD CONSTRAINT "FK_claim_edit_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "claim_edit" ADD CONSTRAINT "FK_claim_edit_claim_line_id" FOREIGN KEY ("claim_line_id") REFERENCES "claim_line" ("claim_line_id");
ALTER TABLE "claim_edit" ADD CONSTRAINT "FK_claim_edit_resolved_by_staff_id" FOREIGN KEY ("resolved_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "claim_edit" ADD CONSTRAINT "FK_claim_edit_agent_decision_id" FOREIGN KEY ("agent_decision_id") REFERENCES "agent_decision" ("agent_decision_id");
ALTER TABLE "claim_edit" ADD CONSTRAINT "FK_claim_edit_edi_file_id" FOREIGN KEY ("edi_file_id") REFERENCES "edi_file" ("edi_file_id");
ALTER TABLE "claim_edit" ADD CONSTRAINT "FK_claim_edit_patient_id" FOREIGN KEY ("patient_id") REFERENCES "patient" ("patient_id");
ALTER TABLE "claim_edit" ADD CONSTRAINT "FK_claim_edit_cpt_code_id" FOREIGN KEY ("cpt_code_id") REFERENCES "cpt_code" ("cpt_code_id");
ALTER TABLE "claim_edit" ADD CONSTRAINT "FK_claim_edit_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "claim_edit" ADD CONSTRAINT "FK_claim_edit_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "claim_edit" ADD CONSTRAINT "FK_claim_edit_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "ledger_entry" ADD CONSTRAINT "FK_ledger_entry_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "ledger_entry" ADD CONSTRAINT "FK_ledger_entry_patient_id" FOREIGN KEY ("patient_id") REFERENCES "patient" ("patient_id");
ALTER TABLE "ledger_entry" ADD CONSTRAINT "FK_ledger_entry_bill_line_id" FOREIGN KEY ("bill_line_id") REFERENCES "bill_line" ("bill_line_id");
ALTER TABLE "ledger_entry" ADD CONSTRAINT "FK_ledger_entry_claim_line_id" FOREIGN KEY ("claim_line_id") REFERENCES "claim_line" ("claim_line_id");
ALTER TABLE "ledger_entry" ADD CONSTRAINT "FK_ledger_entry_specialty_id" FOREIGN KEY ("specialty_id") REFERENCES "specialty" ("specialty_id");
ALTER TABLE "ledger_entry" ADD CONSTRAINT "FK_ledger_entry_cpt_code_id" FOREIGN KEY ("cpt_code_id") REFERENCES "cpt_code" ("cpt_code_id");
ALTER TABLE "ledger_entry" ADD CONSTRAINT "FK_ledger_entry_adjustment_reason_id" FOREIGN KEY ("adjustment_reason_id") REFERENCES "adjustment_reason" ("adjustment_reason_id");
ALTER TABLE "ledger_entry" ADD CONSTRAINT "FK_ledger_entry_approved_by_staff_id" FOREIGN KEY ("approved_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "ledger_entry" ADD CONSTRAINT "FK_ledger_entry_reverses_ledger_entry_id" FOREIGN KEY ("reverses_ledger_entry_id") REFERENCES "ledger_entry" ("ledger_entry_id");
ALTER TABLE "ledger_entry" ADD CONSTRAINT "FK_ledger_entry_remark_code_id" FOREIGN KEY ("remark_code_id") REFERENCES "remark_code" ("remark_code_id");
ALTER TABLE "ledger_entry" ADD CONSTRAINT "FK_ledger_entry_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "ledger_entry" ADD CONSTRAINT "FK_ledger_entry_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "ledger_entry" ADD CONSTRAINT "FK_ledger_entry_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "denial" ADD CONSTRAINT "FK_denial_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "denial" ADD CONSTRAINT "FK_denial_claim_line_id" FOREIGN KEY ("claim_line_id") REFERENCES "claim_line" ("claim_line_id");
ALTER TABLE "denial" ADD CONSTRAINT "FK_denial_patient_id" FOREIGN KEY ("patient_id") REFERENCES "patient" ("patient_id");
ALTER TABLE "denial" ADD CONSTRAINT "FK_denial_adjustment_reason_id" FOREIGN KEY ("adjustment_reason_id") REFERENCES "adjustment_reason" ("adjustment_reason_id");
ALTER TABLE "denial" ADD CONSTRAINT "FK_denial_ledger_entry_id" FOREIGN KEY ("ledger_entry_id") REFERENCES "ledger_entry" ("ledger_entry_id");
ALTER TABLE "denial" ADD CONSTRAINT "FK_denial_bill_line_id" FOREIGN KEY ("bill_line_id") REFERENCES "bill_line" ("bill_line_id");
ALTER TABLE "denial" ADD CONSTRAINT "FK_denial_cpt_code_id" FOREIGN KEY ("cpt_code_id") REFERENCES "cpt_code" ("cpt_code_id");
ALTER TABLE "denial" ADD CONSTRAINT "FK_denial_specialty_id" FOREIGN KEY ("specialty_id") REFERENCES "specialty" ("specialty_id");
ALTER TABLE "denial" ADD CONSTRAINT "FK_denial_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "denial" ADD CONSTRAINT "FK_denial_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "denial" ADD CONSTRAINT "FK_denial_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "payment" ADD CONSTRAINT "FK_payment_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "payment" ADD CONSTRAINT "FK_payment_patient_id" FOREIGN KEY ("patient_id") REFERENCES "patient" ("patient_id");
ALTER TABLE "payment" ADD CONSTRAINT "FK_payment_edi_file_id" FOREIGN KEY ("edi_file_id") REFERENCES "edi_file" ("edi_file_id");
ALTER TABLE "payment" ADD CONSTRAINT "FK_payment_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "payment" ADD CONSTRAINT "FK_payment_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "payment" ADD CONSTRAINT "FK_payment_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "payment_plan" ADD CONSTRAINT "FK_payment_plan_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "payment_plan" ADD CONSTRAINT "FK_payment_plan_patient_id" FOREIGN KEY ("patient_id") REFERENCES "patient" ("patient_id");
ALTER TABLE "payment_plan" ADD CONSTRAINT "FK_payment_plan_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "payment_plan" ADD CONSTRAINT "FK_payment_plan_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "payment_plan" ADD CONSTRAINT "FK_payment_plan_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "patient_contact_preference" ADD CONSTRAINT "FK_patient_contact_preference_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "patient_contact_preference" ADD CONSTRAINT "FK_patient_contact_preference_patient_id" FOREIGN KEY ("patient_id") REFERENCES "patient" ("patient_id");
ALTER TABLE "patient_contact_preference" ADD CONSTRAINT "FK_patient_contact_preference_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "patient_contact_preference" ADD CONSTRAINT "FK_patient_contact_preference_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "patient_contact_preference" ADD CONSTRAINT "FK_patient_contact_preference_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "denial_reason" ADD CONSTRAINT "FK_denial_reason_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "denial_reason" ADD CONSTRAINT "FK_denial_reason_adjustment_reason_id" FOREIGN KEY ("adjustment_reason_id") REFERENCES "adjustment_reason" ("adjustment_reason_id");
ALTER TABLE "denial_reason" ADD CONSTRAINT "FK_denial_reason_remark_code_id" FOREIGN KEY ("remark_code_id") REFERENCES "remark_code" ("remark_code_id");
ALTER TABLE "denial_reason" ADD CONSTRAINT "FK_denial_reason_cpt_code_id" FOREIGN KEY ("cpt_code_id") REFERENCES "cpt_code" ("cpt_code_id");
ALTER TABLE "denial_reason" ADD CONSTRAINT "FK_denial_reason_claim_line_id" FOREIGN KEY ("claim_line_id") REFERENCES "claim_line" ("claim_line_id");
ALTER TABLE "denial_reason" ADD CONSTRAINT "FK_denial_reason_specialty_id" FOREIGN KEY ("specialty_id") REFERENCES "specialty" ("specialty_id");
ALTER TABLE "denial_reason" ADD CONSTRAINT "FK_denial_reason_patient_id" FOREIGN KEY ("patient_id") REFERENCES "patient" ("patient_id");
ALTER TABLE "denial_reason" ADD CONSTRAINT "FK_denial_reason_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "denial_reason" ADD CONSTRAINT "FK_denial_reason_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "denial_reason" ADD CONSTRAINT "FK_denial_reason_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "ar_interval" ADD CONSTRAINT "FK_ar_interval_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "ar_interval" ADD CONSTRAINT "FK_ar_interval_bill_line_id" FOREIGN KEY ("bill_line_id") REFERENCES "bill_line" ("bill_line_id");
ALTER TABLE "ar_interval" ADD CONSTRAINT "FK_ar_interval_patient_id" FOREIGN KEY ("patient_id") REFERENCES "patient" ("patient_id");
ALTER TABLE "ar_interval" ADD CONSTRAINT "FK_ar_interval_claim_line_id" FOREIGN KEY ("claim_line_id") REFERENCES "claim_line" ("claim_line_id");
ALTER TABLE "ar_interval" ADD CONSTRAINT "FK_ar_interval_specialty_id" FOREIGN KEY ("specialty_id") REFERENCES "specialty" ("specialty_id");
ALTER TABLE "ar_interval" ADD CONSTRAINT "FK_ar_interval_cpt_code_id" FOREIGN KEY ("cpt_code_id") REFERENCES "cpt_code" ("cpt_code_id");
ALTER TABLE "ar_interval" ADD CONSTRAINT "FK_ar_interval_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "ar_interval" ADD CONSTRAINT "FK_ar_interval_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "ar_interval" ADD CONSTRAINT "FK_ar_interval_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "ar_snapshot" ADD CONSTRAINT "FK_ar_snapshot_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "ar_snapshot" ADD CONSTRAINT "FK_ar_snapshot_patient_id" FOREIGN KEY ("patient_id") REFERENCES "patient" ("patient_id");
ALTER TABLE "ar_snapshot" ADD CONSTRAINT "FK_ar_snapshot_specialty_id" FOREIGN KEY ("specialty_id") REFERENCES "specialty" ("specialty_id");
ALTER TABLE "ar_snapshot" ADD CONSTRAINT "FK_ar_snapshot_primary_cpt_code_id" FOREIGN KEY ("primary_cpt_code_id") REFERENCES "cpt_code" ("cpt_code_id");
ALTER TABLE "ar_snapshot" ADD CONSTRAINT "FK_ar_snapshot_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "ar_snapshot" ADD CONSTRAINT "FK_ar_snapshot_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "ar_snapshot" ADD CONSTRAINT "FK_ar_snapshot_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "appeal" ADD CONSTRAINT "FK_appeal_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "appeal" ADD CONSTRAINT "FK_appeal_agent_decision_id" FOREIGN KEY ("agent_decision_id") REFERENCES "agent_decision" ("agent_decision_id");
ALTER TABLE "appeal" ADD CONSTRAINT "FK_appeal_agent_approval_id" FOREIGN KEY ("agent_approval_id") REFERENCES "agent_approval" ("agent_approval_id");
ALTER TABLE "appeal" ADD CONSTRAINT "FK_appeal_patient_id" FOREIGN KEY ("patient_id") REFERENCES "patient" ("patient_id");
ALTER TABLE "appeal" ADD CONSTRAINT "FK_appeal_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "appeal" ADD CONSTRAINT "FK_appeal_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "appeal" ADD CONSTRAINT "FK_appeal_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "patient_statement" ADD CONSTRAINT "FK_patient_statement_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "patient_statement" ADD CONSTRAINT "FK_patient_statement_patient_id" FOREIGN KEY ("patient_id") REFERENCES "patient" ("patient_id");
ALTER TABLE "patient_statement" ADD CONSTRAINT "FK_patient_statement_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "patient_statement" ADD CONSTRAINT "FK_patient_statement_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "patient_statement" ADD CONSTRAINT "FK_patient_statement_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "payment_adjustment" ADD CONSTRAINT "FK_payment_adjustment_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "payment_adjustment" ADD CONSTRAINT "FK_payment_adjustment_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "payment_adjustment" ADD CONSTRAINT "FK_payment_adjustment_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "payment_adjustment" ADD CONSTRAINT "FK_payment_adjustment_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "remittance_claim" ADD CONSTRAINT "FK_remittance_claim_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "remittance_claim" ADD CONSTRAINT "FK_remittance_claim_remark_code_id" FOREIGN KEY ("remark_code_id") REFERENCES "remark_code" ("remark_code_id");
ALTER TABLE "remittance_claim" ADD CONSTRAINT "FK_remittance_claim_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "remittance_claim" ADD CONSTRAINT "FK_remittance_claim_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "remittance_claim" ADD CONSTRAINT "FK_remittance_claim_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "bank_deposit" ADD CONSTRAINT "FK_bank_deposit_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "bank_deposit" ADD CONSTRAINT "FK_bank_deposit_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "bank_deposit" ADD CONSTRAINT "FK_bank_deposit_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "bank_deposit" ADD CONSTRAINT "FK_bank_deposit_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "collection_placement" ADD CONSTRAINT "FK_collection_placement_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "collection_placement" ADD CONSTRAINT "FK_collection_placement_patient_id" FOREIGN KEY ("patient_id") REFERENCES "patient" ("patient_id");
ALTER TABLE "collection_placement" ADD CONSTRAINT "FK_collection_placement_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "collection_placement" ADD CONSTRAINT "FK_collection_placement_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "collection_placement" ADD CONSTRAINT "FK_collection_placement_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "agent_decision" ADD CONSTRAINT "FK_agent_decision_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "agent_decision" ADD CONSTRAINT "FK_agent_decision_agent_run_id" FOREIGN KEY ("agent_run_id") REFERENCES "agent_run" ("agent_run_id");
ALTER TABLE "agent_decision" ADD CONSTRAINT "FK_agent_decision_supersedes_decision_id" FOREIGN KEY ("supersedes_decision_id") REFERENCES "agent_decision" ("agent_decision_id");
ALTER TABLE "agent_decision" ADD CONSTRAINT "FK_agent_decision_patient_id" FOREIGN KEY ("patient_id") REFERENCES "patient" ("patient_id");
ALTER TABLE "agent_decision" ADD CONSTRAINT "FK_agent_decision_specialty_id" FOREIGN KEY ("specialty_id") REFERENCES "specialty" ("specialty_id");
ALTER TABLE "agent_value" ADD CONSTRAINT "FK_agent_value_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "agent_value" ADD CONSTRAINT "FK_agent_value_agent_decision_id" FOREIGN KEY ("agent_decision_id") REFERENCES "agent_decision" ("agent_decision_id");
ALTER TABLE "agent_value" ADD CONSTRAINT "FK_agent_value_specialty_id" FOREIGN KEY ("specialty_id") REFERENCES "specialty" ("specialty_id");
ALTER TABLE "agent_value" ADD CONSTRAINT "FK_agent_value_cpt_code_id" FOREIGN KEY ("cpt_code_id") REFERENCES "cpt_code" ("cpt_code_id");
ALTER TABLE "agent_value" ADD CONSTRAINT "FK_agent_value_ledger_entry_id" FOREIGN KEY ("ledger_entry_id") REFERENCES "ledger_entry" ("ledger_entry_id");
ALTER TABLE "agent_run" ADD CONSTRAINT "FK_agent_run_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "agent_run" ADD CONSTRAINT "FK_agent_run_trigger_run_id" FOREIGN KEY ("trigger_run_id") REFERENCES "agent_run" ("agent_run_id");
ALTER TABLE "agent_decision_check" ADD CONSTRAINT "FK_agent_decision_check_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "agent_decision_check" ADD CONSTRAINT "FK_agent_decision_check_agent_decision_id" FOREIGN KEY ("agent_decision_id") REFERENCES "agent_decision" ("agent_decision_id");
ALTER TABLE "agent_decision_check" ADD CONSTRAINT "FK_agent_decision_check_cpt_code_id" FOREIGN KEY ("cpt_code_id") REFERENCES "cpt_code" ("cpt_code_id");
ALTER TABLE "agent_finding" ADD CONSTRAINT "FK_agent_finding_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "agent_finding" ADD CONSTRAINT "FK_agent_finding_agent_run_id" FOREIGN KEY ("agent_run_id") REFERENCES "agent_run" ("agent_run_id");
ALTER TABLE "agent_finding" ADD CONSTRAINT "FK_agent_finding_agent_decision_id" FOREIGN KEY ("agent_decision_id") REFERENCES "agent_decision" ("agent_decision_id");
ALTER TABLE "agent_finding" ADD CONSTRAINT "FK_agent_finding_patient_id" FOREIGN KEY ("patient_id") REFERENCES "patient" ("patient_id");
ALTER TABLE "agent_finding" ADD CONSTRAINT "FK_agent_finding_specialty_id" FOREIGN KEY ("specialty_id") REFERENCES "specialty" ("specialty_id");
ALTER TABLE "agent_task" ADD CONSTRAINT "FK_agent_task_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "agent_task" ADD CONSTRAINT "FK_agent_task_agent_decision_id" FOREIGN KEY ("agent_decision_id") REFERENCES "agent_decision" ("agent_decision_id");
ALTER TABLE "agent_task" ADD CONSTRAINT "FK_agent_task_assigned_to_staff_id" FOREIGN KEY ("assigned_to_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "agent_task" ADD CONSTRAINT "FK_agent_task_patient_id" FOREIGN KEY ("patient_id") REFERENCES "patient" ("patient_id");
ALTER TABLE "agent_task" ADD CONSTRAINT "FK_agent_task_specialty_id" FOREIGN KEY ("specialty_id") REFERENCES "specialty" ("specialty_id");
ALTER TABLE "agent_approval" ADD CONSTRAINT "FK_agent_approval_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "agent_approval" ADD CONSTRAINT "FK_agent_approval_agent_decision_id" FOREIGN KEY ("agent_decision_id") REFERENCES "agent_decision" ("agent_decision_id");
ALTER TABLE "agent_approval" ADD CONSTRAINT "FK_agent_approval_approved_by_staff_id" FOREIGN KEY ("approved_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "agent_writeback" ADD CONSTRAINT "FK_agent_writeback_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "agent_writeback" ADD CONSTRAINT "FK_agent_writeback_agent_decision_id" FOREIGN KEY ("agent_decision_id") REFERENCES "agent_decision" ("agent_decision_id");
ALTER TABLE "agent_writeback" ADD CONSTRAINT "FK_agent_writeback_agent_approval_id" FOREIGN KEY ("agent_approval_id") REFERENCES "agent_approval" ("agent_approval_id");
ALTER TABLE "agent_forecast" ADD CONSTRAINT "FK_agent_forecast_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "patient" ADD CONSTRAINT "FK_patient_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "patient" ADD CONSTRAINT "FK_patient_merged_into_patient_id" FOREIGN KEY ("merged_into_patient_id") REFERENCES "patient" ("patient_id");
ALTER TABLE "patient" ADD CONSTRAINT "FK_patient_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "patient" ADD CONSTRAINT "FK_patient_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "patient" ADD CONSTRAINT "FK_patient_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "coverage" ADD CONSTRAINT "FK_coverage_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "coverage" ADD CONSTRAINT "FK_coverage_patient_id" FOREIGN KEY ("patient_id") REFERENCES "patient" ("patient_id");
ALTER TABLE "coverage" ADD CONSTRAINT "FK_coverage_payer_plan_id" FOREIGN KEY ("payer_plan_id") REFERENCES "payer_plan" ("payer_plan_id");
ALTER TABLE "coverage" ADD CONSTRAINT "FK_coverage_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "coverage" ADD CONSTRAINT "FK_coverage_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "coverage" ADD CONSTRAINT "FK_coverage_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "authorization" ADD CONSTRAINT "FK_authorization_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "authorization" ADD CONSTRAINT "FK_authorization_patient_id" FOREIGN KEY ("patient_id") REFERENCES "patient" ("patient_id");
ALTER TABLE "authorization" ADD CONSTRAINT "FK_authorization_primary_cpt_code_id" FOREIGN KEY ("primary_cpt_code_id") REFERENCES "cpt_code" ("cpt_code_id");
ALTER TABLE "authorization" ADD CONSTRAINT "FK_authorization_diagnosis_code_id" FOREIGN KEY ("diagnosis_code_id") REFERENCES "diagnosis_code" ("diagnosis_code_id");
ALTER TABLE "authorization" ADD CONSTRAINT "FK_authorization_place_of_service_id" FOREIGN KEY ("place_of_service_id") REFERENCES "place_of_service" ("place_of_service_id");
ALTER TABLE "authorization" ADD CONSTRAINT "FK_authorization_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "authorization" ADD CONSTRAINT "FK_authorization_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "authorization" ADD CONSTRAINT "FK_authorization_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "authorization_line" ADD CONSTRAINT "FK_authorization_line_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "authorization_line" ADD CONSTRAINT "FK_authorization_line_cpt_code_id" FOREIGN KEY ("cpt_code_id") REFERENCES "cpt_code" ("cpt_code_id");
ALTER TABLE "authorization_line" ADD CONSTRAINT "FK_authorization_line_cpt_code_to_id" FOREIGN KEY ("cpt_code_to_id") REFERENCES "cpt_code" ("cpt_code_id");
ALTER TABLE "authorization_line" ADD CONSTRAINT "FK_authorization_line_modifier_id" FOREIGN KEY ("modifier_id") REFERENCES "modifier" ("modifier_id");
ALTER TABLE "authorization_line" ADD CONSTRAINT "FK_authorization_line_patient_id" FOREIGN KEY ("patient_id") REFERENCES "patient" ("patient_id");
ALTER TABLE "authorization_line" ADD CONSTRAINT "FK_authorization_line_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "authorization_line" ADD CONSTRAINT "FK_authorization_line_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "authorization_line" ADD CONSTRAINT "FK_authorization_line_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "guarantor" ADD CONSTRAINT "FK_guarantor_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "guarantor" ADD CONSTRAINT "FK_guarantor_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "guarantor" ADD CONSTRAINT "FK_guarantor_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "guarantor" ADD CONSTRAINT "FK_guarantor_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "staff" ADD CONSTRAINT "FK_staff_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "staff" ADD CONSTRAINT "FK_staff_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "staff" ADD CONSTRAINT "FK_staff_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "staff" ADD CONSTRAINT "FK_staff_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "enrollment" ADD CONSTRAINT "FK_enrollment_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "enrollment" ADD CONSTRAINT "FK_enrollment_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "enrollment" ADD CONSTRAINT "FK_enrollment_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "enrollment" ADD CONSTRAINT "FK_enrollment_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "provider_identifier" ADD CONSTRAINT "FK_provider_identifier_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "provider_identifier" ADD CONSTRAINT "FK_provider_identifier_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "provider_identifier" ADD CONSTRAINT "FK_provider_identifier_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "provider_identifier" ADD CONSTRAINT "FK_provider_identifier_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "provider_practice" ADD CONSTRAINT "FK_provider_practice_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "provider_practice" ADD CONSTRAINT "FK_provider_practice_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "provider_practice" ADD CONSTRAINT "FK_provider_practice_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "provider_practice" ADD CONSTRAINT "FK_provider_practice_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "edi_enrollment" ADD CONSTRAINT "FK_edi_enrollment_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "edi_enrollment" ADD CONSTRAINT "FK_edi_enrollment_payer_identifier_id" FOREIGN KEY ("payer_identifier_id") REFERENCES "payer_identifier" ("payer_identifier_id");
ALTER TABLE "edi_enrollment" ADD CONSTRAINT "FK_edi_enrollment_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "edi_enrollment" ADD CONSTRAINT "FK_edi_enrollment_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "edi_enrollment" ADD CONSTRAINT "FK_edi_enrollment_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "practice" ADD CONSTRAINT "FK_practice_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "practice" ADD CONSTRAINT "FK_practice_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "practice" ADD CONSTRAINT "FK_practice_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "practice" ADD CONSTRAINT "FK_practice_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "provider" ADD CONSTRAINT "FK_provider_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "provider" ADD CONSTRAINT "FK_provider_specialty_id" FOREIGN KEY ("specialty_id") REFERENCES "specialty" ("specialty_id");
ALTER TABLE "provider" ADD CONSTRAINT "FK_provider_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "provider" ADD CONSTRAINT "FK_provider_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "provider" ADD CONSTRAINT "FK_provider_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "payer" ADD CONSTRAINT "FK_payer_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "payer" ADD CONSTRAINT "FK_payer_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "payer" ADD CONSTRAINT "FK_payer_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "payer" ADD CONSTRAINT "FK_payer_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "cpt_code" ADD CONSTRAINT "FK_cpt_code_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "cpt_code" ADD CONSTRAINT "FK_cpt_code_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "diagnosis_code" ADD CONSTRAINT "FK_diagnosis_code_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "diagnosis_code" ADD CONSTRAINT "FK_diagnosis_code_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "modifier" ADD CONSTRAINT "FK_modifier_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "modifier" ADD CONSTRAINT "FK_modifier_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "place_of_service" ADD CONSTRAINT "FK_place_of_service_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "place_of_service" ADD CONSTRAINT "FK_place_of_service_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "specialty" ADD CONSTRAINT "FK_specialty_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "specialty" ADD CONSTRAINT "FK_specialty_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "facility" ADD CONSTRAINT "FK_facility_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "facility" ADD CONSTRAINT "FK_facility_default_place_of_service_id" FOREIGN KEY ("default_place_of_service_id") REFERENCES "place_of_service" ("place_of_service_id");
ALTER TABLE "facility" ADD CONSTRAINT "FK_facility_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "facility" ADD CONSTRAINT "FK_facility_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "facility" ADD CONSTRAINT "FK_facility_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "fee_schedule" ADD CONSTRAINT "FK_fee_schedule_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "fee_schedule" ADD CONSTRAINT "FK_fee_schedule_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "fee_schedule" ADD CONSTRAINT "FK_fee_schedule_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "fee_schedule" ADD CONSTRAINT "FK_fee_schedule_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "fee_schedule_line" ADD CONSTRAINT "FK_fee_schedule_line_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "fee_schedule_line" ADD CONSTRAINT "FK_fee_schedule_line_cpt_code_id" FOREIGN KEY ("cpt_code_id") REFERENCES "cpt_code" ("cpt_code_id");
ALTER TABLE "fee_schedule_line" ADD CONSTRAINT "FK_fee_schedule_line_modifier_id" FOREIGN KEY ("modifier_id") REFERENCES "modifier" ("modifier_id");
ALTER TABLE "fee_schedule_line" ADD CONSTRAINT "FK_fee_schedule_line_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "fee_schedule_line" ADD CONSTRAINT "FK_fee_schedule_line_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "fee_schedule_line" ADD CONSTRAINT "FK_fee_schedule_line_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "contract_rate" ADD CONSTRAINT "FK_contract_rate_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "contract_rate" ADD CONSTRAINT "FK_contract_rate_cpt_code_id" FOREIGN KEY ("cpt_code_id") REFERENCES "cpt_code" ("cpt_code_id");
ALTER TABLE "contract_rate" ADD CONSTRAINT "FK_contract_rate_modifier_id" FOREIGN KEY ("modifier_id") REFERENCES "modifier" ("modifier_id");
ALTER TABLE "contract_rate" ADD CONSTRAINT "FK_contract_rate_specialty_id" FOREIGN KEY ("specialty_id") REFERENCES "specialty" ("specialty_id");
ALTER TABLE "contract_rate" ADD CONSTRAINT "FK_contract_rate_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "contract_rate" ADD CONSTRAINT "FK_contract_rate_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "contract_rate" ADD CONSTRAINT "FK_contract_rate_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "adjustment_reason" ADD CONSTRAINT "FK_adjustment_reason_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "adjustment_reason" ADD CONSTRAINT "FK_adjustment_reason_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "remark_code" ADD CONSTRAINT "FK_remark_code_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "remark_code" ADD CONSTRAINT "FK_remark_code_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "practice_settings" ADD CONSTRAINT "FK_practice_settings_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "practice_settings" ADD CONSTRAINT "FK_practice_settings_approved_by_staff_id" FOREIGN KEY ("approved_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "practice_settings" ADD CONSTRAINT "FK_practice_settings_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "practice_settings" ADD CONSTRAINT "FK_practice_settings_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "practice_settings" ADD CONSTRAINT "FK_practice_settings_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "payer_rule" ADD CONSTRAINT "FK_payer_rule_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "payer_rule" ADD CONSTRAINT "FK_payer_rule_place_of_service_id" FOREIGN KEY ("place_of_service_id") REFERENCES "place_of_service" ("place_of_service_id");
ALTER TABLE "payer_rule" ADD CONSTRAINT "FK_payer_rule_cpt_code_id" FOREIGN KEY ("cpt_code_id") REFERENCES "cpt_code" ("cpt_code_id");
ALTER TABLE "payer_rule" ADD CONSTRAINT "FK_payer_rule_cpt_code_to_id" FOREIGN KEY ("cpt_code_to_id") REFERENCES "cpt_code" ("cpt_code_id");
ALTER TABLE "payer_rule" ADD CONSTRAINT "FK_payer_rule_paired_cpt_code_id" FOREIGN KEY ("paired_cpt_code_id") REFERENCES "cpt_code" ("cpt_code_id");
ALTER TABLE "payer_rule" ADD CONSTRAINT "FK_payer_rule_modifier_id" FOREIGN KEY ("modifier_id") REFERENCES "modifier" ("modifier_id");
ALTER TABLE "payer_rule" ADD CONSTRAINT "FK_payer_rule_diagnosis_code_id" FOREIGN KEY ("diagnosis_code_id") REFERENCES "diagnosis_code" ("diagnosis_code_id");
ALTER TABLE "payer_rule" ADD CONSTRAINT "FK_payer_rule_adjustment_reason_id" FOREIGN KEY ("adjustment_reason_id") REFERENCES "adjustment_reason" ("adjustment_reason_id");
ALTER TABLE "payer_rule" ADD CONSTRAINT "FK_payer_rule_approved_by_staff_id" FOREIGN KEY ("approved_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "payer_rule" ADD CONSTRAINT "FK_payer_rule_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "payer_rule" ADD CONSTRAINT "FK_payer_rule_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "payer_rule" ADD CONSTRAINT "FK_payer_rule_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "calendar" ADD CONSTRAINT "FK_calendar_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "calendar" ADD CONSTRAINT "FK_calendar_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "payer_identifier" ADD CONSTRAINT "FK_payer_identifier_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "payer_identifier" ADD CONSTRAINT "FK_payer_identifier_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "payer_identifier" ADD CONSTRAINT "FK_payer_identifier_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "payer_identifier" ADD CONSTRAINT "FK_payer_identifier_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "payer_plan" ADD CONSTRAINT "FK_payer_plan_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "payer_plan" ADD CONSTRAINT "FK_payer_plan_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "payer_plan" ADD CONSTRAINT "FK_payer_plan_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "payer_plan" ADD CONSTRAINT "FK_payer_plan_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "payer_contract" ADD CONSTRAINT "FK_payer_contract_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "payer_contract" ADD CONSTRAINT "FK_payer_contract_payer_plan_id" FOREIGN KEY ("payer_plan_id") REFERENCES "payer_plan" ("payer_plan_id");
ALTER TABLE "payer_contract" ADD CONSTRAINT "FK_payer_contract_created_by_staff_id" FOREIGN KEY ("created_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "payer_contract" ADD CONSTRAINT "FK_payer_contract_modified_by_staff_id" FOREIGN KEY ("modified_by_staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "payer_contract" ADD CONSTRAINT "FK_payer_contract_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "claim_status_code" ADD CONSTRAINT "FK_claim_status_code_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "claim_status_code" ADD CONSTRAINT "FK_claim_status_code_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "ndc_code" ADD CONSTRAINT "FK_ndc_code_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "ndc_code" ADD CONSTRAINT "FK_ndc_code_hcpcs_cpt_code_id" FOREIGN KEY ("hcpcs_cpt_code_id") REFERENCES "cpt_code" ("cpt_code_id");
ALTER TABLE "ndc_code" ADD CONSTRAINT "FK_ndc_code_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "data_feed" ADD CONSTRAINT "FK_data_feed_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "edi_file" ADD CONSTRAINT "FK_edi_file_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "edi_file" ADD CONSTRAINT "FK_edi_file_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "edi_file" ADD CONSTRAINT "FK_edi_file_replaced_by_edi_file_id" FOREIGN KEY ("replaced_by_edi_file_id") REFERENCES "edi_file" ("edi_file_id");
ALTER TABLE "load_batch" ADD CONSTRAINT "FK_load_batch_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "data_quality_result" ADD CONSTRAINT "FK_data_quality_result_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "data_quality_result" ADD CONSTRAINT "FK_data_quality_result_load_batch_id" FOREIGN KEY ("load_batch_id") REFERENCES "load_batch" ("load_batch_id");
ALTER TABLE "access_audit" ADD CONSTRAINT "FK_access_audit_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "tenant" ("tenant_id");
ALTER TABLE "access_audit" ADD CONSTRAINT "FK_access_audit_staff_id" FOREIGN KEY ("staff_id") REFERENCES "staff" ("staff_id");
ALTER TABLE "access_audit" ADD CONSTRAINT "FK_access_audit_agent_run_id" FOREIGN KEY ("agent_run_id") REFERENCES "agent_run" ("agent_run_id");
COMMENT ON TABLE "appointment" IS 'One row per appointment version (a cancel or reschedule keeps the old row and adds a new one).';
COMMENT ON COLUMN "appointment"."appointment_id" IS 'Stable ID of the record: the same on every version. The primary key is (appointment_id, version). Every link from another table uses appointment_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.';
COMMENT ON COLUMN "appointment"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "appointment"."appointment_number" IS 'The client''s own appointment ID. Restricted: used only to match the source system.';
COMMENT ON COLUMN "appointment"."practice_id" IS 'Billing entity.';
COMMENT ON COLUMN "appointment"."patient_id" IS 'The patient.';
COMMENT ON COLUMN "appointment"."appointment_date" IS 'Visit date; sets the 3-day and 1-day check timing.';
COMMENT ON COLUMN "appointment"."appointment_status" IS 'Booked, confirmed, arrived, completed, cancelled, no_show, rescheduled.';
COMMENT ON COLUMN "appointment"."provider_id" IS 'Scheduled provider; utilization and no-shows by provider.';
COMMENT ON COLUMN "appointment"."payer_id" IS 'Insurer on file at booking. Not borrowed from the claim: no claim exists yet, and none ever will for a no-show.';
COMMENT ON COLUMN "appointment"."coverage_id" IS 'The policy the eligibility check will test.';
COMMENT ON COLUMN "appointment"."facility_id" IS 'Site capacity.';
COMMENT ON COLUMN "appointment"."start_time" IS 'Day utilization and ordering.';
COMMENT ON COLUMN "appointment"."booked_date" IS 'Lead time; the pre-visit checks key off it.';
COMMENT ON COLUMN "appointment"."appointment_type" IS 'New, follow_up, procedure, preventive, telehealth, emergency.';
COMMENT ON COLUMN "appointment"."booked_via" IS 'Phone, portal, walk-in, referral.';
COMMENT ON COLUMN "appointment"."referring_provider_id" IS 'HMO referrals.';
COMMENT ON COLUMN "appointment"."referral_id" IS 'The referral this visit was booked under, when there is one.';
COMMENT ON COLUMN "appointment"."version" IS '1 for the first row; higher for each change.';
COMMENT ON COLUMN "appointment"."is_current" IS '1 on the latest version. Counts use current rows only.';
COMMENT ON COLUMN "appointment"."previous_appointment_id" IS 'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.';
COMMENT ON COLUMN "appointment"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "appointment"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "appointment"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "appointment"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "appointment"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "appointment"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "appointment"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "appointment"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "appointment"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "appointment"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "appointment_status_log" IS 'One status change of an appointment: from which status to which, when, by whom and why.';
COMMENT ON COLUMN "appointment_status_log"."appointment_status_log_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "appointment_status_log"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "appointment_status_log"."appointment_id" IS 'The appointment (stable ID).';
COMMENT ON COLUMN "appointment_status_log"."from_status" IS 'Status before the change. Blank on the first row.';
COMMENT ON COLUMN "appointment_status_log"."to_status" IS 'Status after the change (same values as appointment.appointment_status).';
COMMENT ON COLUMN "appointment_status_log"."status_changed_at" IS 'When the change happened in the source system (practice local time).';
COMMENT ON COLUMN "appointment_status_log"."changed_by_staff_id" IS 'Who made the change (pseudonymous staff_id).';
COMMENT ON COLUMN "appointment_status_log"."change_channel" IS 'front_desk, phone, portal, online_booking, text_reply, interface, agent.';
COMMENT ON COLUMN "appointment_status_log"."reason_code" IS 'Coded reason on a cancel, reschedule or no-show. Never free text.';
COMMENT ON COLUMN "appointment_status_log"."load_batch_id" IS 'The load that wrote the row.';
COMMENT ON COLUMN "appointment_status_log"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "appointment_status_log"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "referral" IS 'One row per referral into the practice: who referred, which payer and plan, valid dates, visits allowed and used.';
COMMENT ON COLUMN "referral"."referral_id" IS 'Stable ID of the record: the same on every version. The primary key is (referral_id, version). Every link from another table uses referral_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.';
COMMENT ON COLUMN "referral"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "referral"."referral_number" IS 'The referral number in the EMR or on the payer side. Restricted.';
COMMENT ON COLUMN "referral"."practice_id" IS 'Reports by practice.';
COMMENT ON COLUMN "referral"."patient_id" IS 'Which patient. Hashed identity only.';
COMMENT ON COLUMN "referral"."coverage_id" IS 'The plan that requires the referral.';
COMMENT ON COLUMN "referral"."payer_id" IS 'The payer that issued or requires the referral.';
COMMENT ON COLUMN "referral"."referring_provider_id" IS 'The referring clinician (internal provider; the NPI sits on the provider row).';
COMMENT ON COLUMN "referral"."referred_to_provider_id" IS 'The clinician in our practice the patient is referred to.';
COMMENT ON COLUMN "referral"."specialty_id" IS 'Specialty the referral is for.';
COMMENT ON COLUMN "referral"."referral_status" IS 'needed, requested, received, expired, used_up, cancelled.';
COMMENT ON COLUMN "referral"."request_date" IS 'When the referral was requested. Request-to-receipt lag.';
COMMENT ON COLUMN "referral"."received_date" IS 'When the referral arrived.';
COMMENT ON COLUMN "referral"."valid_from" IS 'First date the referral covers.';
COMMENT ON COLUMN "referral"."valid_to" IS 'Last date the referral covers. Expiry warnings.';
COMMENT ON COLUMN "referral"."visits_allowed" IS 'Visits approved.';
COMMENT ON COLUMN "referral"."visits_used" IS 'Visits already used. Visits remaining = allowed - used.';
COMMENT ON COLUMN "referral"."diagnosis_code_id" IS 'Diagnosis on the referral.';
COMMENT ON COLUMN "referral"."cpt_code_id" IS 'Service the referral names, when it names one.';
COMMENT ON COLUMN "referral"."authorization_id" IS 'Linked authorization, when the plan needs both.';
COMMENT ON COLUMN "referral"."document_id" IS 'The signed referral document (metadata row).';
COMMENT ON COLUMN "referral"."version" IS '1 for the first row; higher for each change.';
COMMENT ON COLUMN "referral"."is_current" IS '1 on the latest version. Counts use current rows only.';
COMMENT ON COLUMN "referral"."previous_referral_id" IS 'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.';
COMMENT ON COLUMN "referral"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "referral"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "referral"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "referral"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "referral"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "referral"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "referral"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "referral"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "referral"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "referral"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "appointment_line" IS 'One row per service planned for the appointment.';
COMMENT ON COLUMN "appointment_line"."appointment_line_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "appointment_line"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "appointment_line"."appointment_id" IS 'Ties the planned service to its appointment.';
COMMENT ON COLUMN "appointment_line"."line_number" IS 'Position within the appointment.';
COMMENT ON COLUMN "appointment_line"."practice_id" IS 'Copied from the header, so reports by practice never join up.';
COMMENT ON COLUMN "appointment_line"."patient_id" IS 'Copied from the header.';
COMMENT ON COLUMN "appointment_line"."payer_id" IS 'Copied from the header, as of this stage.';
COMMENT ON COLUMN "appointment_line"."provider_id" IS 'Copied from the header.';
COMMENT ON COLUMN "appointment_line"."specialty_id" IS 'Copied from the provider''s specialty; fast specialty reports.';
COMMENT ON COLUMN "appointment_line"."planned_cpt_code_id" IS 'Drives the authorization check, patient estimate and eligibility service type.';
COMMENT ON COLUMN "appointment_line"."is_inferred" IS 'Whether the planned code was given or guessed, so a guess is never treated as known.';
COMMENT ON COLUMN "appointment_line"."planned_units" IS 'Units for the estimate.';
COMMENT ON COLUMN "appointment_line"."expected_charge" IS 'Units x the fee list; estimate and forecast.';
COMMENT ON COLUMN "appointment_line"."expected_allowed" IS 'Contract rate; estimates the patient''s share.';
COMMENT ON COLUMN "appointment_line"."auth_required" IS 'Yes, no, unknown. Unknown is never read as no.';
COMMENT ON COLUMN "appointment_line"."authorization_id" IS 'Authorization on file.';
COMMENT ON COLUMN "appointment_line"."planned_diagnosis_code_id" IS 'Some referrals and authorizations need it.';
COMMENT ON COLUMN "appointment_line"."planned_provider_id" IS 'When a different provider performs the service.';
COMMENT ON COLUMN "appointment_line"."room_or_equipment" IS 'Capacity planning.';
COMMENT ON COLUMN "appointment_line"."duration_minutes" IS 'Slot length.';
COMMENT ON COLUMN "appointment_line"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "appointment_line"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "appointment_line"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "appointment_line"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "appointment_line"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "appointment_line"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "appointment_line"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "appointment_line"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "appointment_line"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "appointment_line"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "appointment_slot" IS 'One row per slot: provider, day, start time, length, type and status. A change of state is a new version.';
COMMENT ON COLUMN "appointment_slot"."appointment_slot_id" IS 'Stable ID of the record: the same on every version. The primary key is (appointment_slot_id, version). Every link from another table uses appointment_slot_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.';
COMMENT ON COLUMN "appointment_slot"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "appointment_slot"."practice_id" IS 'Reports by practice.';
COMMENT ON COLUMN "appointment_slot"."provider_id" IS 'Whose schedule.';
COMMENT ON COLUMN "appointment_slot"."slot_date" IS 'Slot day.';
COMMENT ON COLUMN "appointment_slot"."start_time" IS 'Slot start.';
COMMENT ON COLUMN "appointment_slot"."duration_minutes" IS 'Slot length.';
COMMENT ON COLUMN "appointment_slot"."slot_status" IS 'Open, booked, held, blocked.';
COMMENT ON COLUMN "appointment_slot"."slot_number" IS 'The scheduler''s slot ID. Restricted.';
COMMENT ON COLUMN "appointment_slot"."facility_id" IS 'Site capacity.';
COMMENT ON COLUMN "appointment_slot"."specialty_id" IS 'Copied from the provider.';
COMMENT ON COLUMN "appointment_slot"."slot_type" IS 'New_patient, follow_up, procedure, telehealth, any, block.';
COMMENT ON COLUMN "appointment_slot"."appointment_id" IS 'The appointment filling the slot.';
COMMENT ON COLUMN "appointment_slot"."created_date" IS 'When the slot was opened for booking; time to next available.';
COMMENT ON COLUMN "appointment_slot"."room_or_resource" IS 'Room or equipment.';
COMMENT ON COLUMN "appointment_slot"."is_overbook" IS 'Overbooked slot.';
COMMENT ON COLUMN "appointment_slot"."version" IS '1 for the first row; higher for each change.';
COMMENT ON COLUMN "appointment_slot"."is_current" IS '1 on the latest version. Counts use current rows only.';
COMMENT ON COLUMN "appointment_slot"."previous_appointment_slot_id" IS 'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.';
COMMENT ON COLUMN "appointment_slot"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "appointment_slot"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "appointment_slot"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "appointment_slot"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "appointment_slot"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "appointment_slot"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "appointment_slot"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "appointment_slot"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "appointment_slot"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "appointment_slot"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "eligibility_check" IS 'One 270/271 exchange: the question asked of a payer about a patient''s coverage for a service date, and the answer that came back.';
COMMENT ON COLUMN "eligibility_check"."eligibility_check_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "eligibility_check"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "eligibility_check"."trace_number" IS 'Reference that ties the 270 to its 271 (TRN02). Unique per request: TRG + appointment id + check_sequence (+ -2 on the secondary payer).';
COMMENT ON COLUMN "eligibility_check"."check_sequence" IS 'Order of checks for the same appointment and coverage (1, 2, 3 ...). Makes trace_number unique.';
COMMENT ON COLUMN "eligibility_check"."appointment_id" IS 'Visit the check was done for.';
COMMENT ON COLUMN "eligibility_check"."coverage_id" IS 'Coverage that was checked.';
COMMENT ON COLUMN "eligibility_check"."patient_id" IS 'Copied from the coverage so patient history needs no join.';
COMMENT ON COLUMN "eligibility_check"."payer_id" IS 'Payer asked.';
COMMENT ON COLUMN "eligibility_check"."practice_id" IS 'Reports by practice.';
COMMENT ON COLUMN "eligibility_check"."is_secondary" IS '1 when the check was for the secondary coverage.';
COMMENT ON COLUMN "eligibility_check"."check_date" IS 'Day the 271 was obtained; age of the check is service date minus this.';
COMMENT ON COLUMN "eligibility_check"."check_ts" IS 'Exact time of the answer, to tell same-day repeats apart.';
COMMENT ON COLUMN "eligibility_check"."service_date" IS 'Date of service asked about (DTP 291).';
COMMENT ON COLUMN "eligibility_check"."service_type_code" IS 'Service type asked about (EQ01).';
COMMENT ON COLUMN "eligibility_check"."is_active" IS '1 when the payer says coverage is active (EB 1), 0 when not active (EB 6). Blank when the payer rejected the request; CHECK: is_active is set or is_aaa_reject = 1.';
COMMENT ON COLUMN "eligibility_check"."is_aaa_reject" IS '1 when the payer answered with an AAA error, for example member not found.';
COMMENT ON COLUMN "eligibility_check"."aaa_reason_code" IS 'AAA reason code (43, 72, 75 ...). Tells a typing error from no coverage.';
COMMENT ON COLUMN "eligibility_check"."plan_begin_date" IS 'Plan start date from the answer (DTP 346).';
COMMENT ON COLUMN "eligibility_check"."plan_end_date" IS 'Plan end date from the answer (DTP 347).';
COMMENT ON COLUMN "eligibility_check"."copay_amount" IS 'Copay in the answer (EB B). Summary for the checked service type; every benefit line is in eligibility_benefit.';
COMMENT ON COLUMN "eligibility_check"."coinsurance_pct" IS 'Coinsurance in the answer (EB A), as a fraction 0 to 1 (0.2000 = 20%).';
COMMENT ON COLUMN "eligibility_check"."coverage_level" IS 'Benefit level of the amounts (EB02): individual, family, employee_spouse.';
COMMENT ON COLUMN "eligibility_check"."network_indicator" IS 'In-network Y, out-of-network N, not applicable W (EB12).';
COMMENT ON COLUMN "eligibility_check"."deductible_remaining" IS 'Deductible left in the answer (EB C).';
COMMENT ON COLUMN "eligibility_check"."deductible_total" IS 'Deductible for the plan year (EB C, period 23).';
COMMENT ON COLUMN "eligibility_check"."oop_max" IS 'Out-of-pocket maximum (EB G).';
COMMENT ON COLUMN "eligibility_check"."oop_remaining" IS 'Out-of-pocket left (EB G, period 29).';
COMMENT ON COLUMN "eligibility_check"."other_payer_id" IS 'Another payer the answer says is primary (EB R).';
COMMENT ON COLUMN "eligibility_check"."auth_required_hint" IS '1 when a benefit line implies prior authorization for the service type; evidence for the authorization rule.';
COMMENT ON COLUMN "eligibility_check"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "eligibility_check"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "eligibility_check"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "eligibility_check"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "eligibility_check"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "eligibility_check"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "eligibility_check"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "eligibility_check"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "eligibility_check"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "eligibility_check"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "patient_estimate" IS 'One cost estimate given to a patient before service: a good faith estimate (self-pay) or an insured estimate.';
COMMENT ON COLUMN "patient_estimate"."patient_estimate_id" IS 'Stable ID of the record: the same on every version. The primary key is (patient_estimate_id, version). Every link from another table uses patient_estimate_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.';
COMMENT ON COLUMN "patient_estimate"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "patient_estimate"."estimate_number" IS 'The practice''s estimate number. Restricted.';
COMMENT ON COLUMN "patient_estimate"."patient_id" IS 'The patient.';
COMMENT ON COLUMN "patient_estimate"."appointment_id" IS 'The visit estimated.';
COMMENT ON COLUMN "patient_estimate"."coverage_id" IS 'Coverage used, blank for self-pay.';
COMMENT ON COLUMN "patient_estimate"."estimate_type" IS 'gfe_self_pay, insured_estimate, advance_eob.';
COMMENT ON COLUMN "patient_estimate"."estimate_date" IS 'When given.';
COMMENT ON COLUMN "patient_estimate"."service_date" IS 'Planned service date.';
COMMENT ON COLUMN "patient_estimate"."estimated_total" IS 'Total expected charges.';
COMMENT ON COLUMN "patient_estimate"."estimated_patient_amount" IS 'Patient share expected.';
COMMENT ON COLUMN "patient_estimate"."delivered_channel" IS 'mail, portal, email, in_person.';
COMMENT ON COLUMN "patient_estimate"."delivered_date" IS 'When delivered (GFE timing rules).';
COMMENT ON COLUMN "patient_estimate"."actual_billed_amount" IS 'What was billed, rebuilt from bills.';
COMMENT ON COLUMN "patient_estimate"."exceeds_gfe_by_400" IS '1 when billed exceeds the good faith estimate by $400 or more (patient may dispute).';
COMMENT ON COLUMN "patient_estimate"."practice_id" IS 'Copied, so reports skip the join.';
COMMENT ON COLUMN "patient_estimate"."version" IS '1 for the first row; higher for each change.';
COMMENT ON COLUMN "patient_estimate"."is_current" IS '1 on the latest version. Counts use current rows only.';
COMMENT ON COLUMN "patient_estimate"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "patient_estimate"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "patient_estimate"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "patient_estimate"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "patient_estimate"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "patient_estimate"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "patient_estimate"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "patient_estimate"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "patient_estimate"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "patient_estimate"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "eligibility_benefit" IS 'One benefit line (EB segment) in a 271 answer: service type, coverage level, network, time period and amount or percent.';
COMMENT ON COLUMN "eligibility_benefit"."eligibility_benefit_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "eligibility_benefit"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "eligibility_benefit"."eligibility_check_id" IS 'The check it belongs to.';
COMMENT ON COLUMN "eligibility_benefit"."benefit_sequence" IS 'Order in the 271.';
COMMENT ON COLUMN "eligibility_benefit"."eligibility_code" IS 'EB01: 1 active, 6 inactive, A coinsurance, B copay, C deductible, F limitation, G out-of-pocket, CB coverage basis ...';
COMMENT ON COLUMN "eligibility_benefit"."coverage_level" IS 'EB02, same values as eligibility_check.coverage_level.';
COMMENT ON COLUMN "eligibility_benefit"."service_type_code" IS 'EB03 service type (30 health plan, 98 office visit, AL vision, PT physical therapy ...).';
COMMENT ON COLUMN "eligibility_benefit"."insurance_type_code" IS 'EB04.';
COMMENT ON COLUMN "eligibility_benefit"."plan_description" IS 'EB05 plan coverage description; no patient text.';
COMMENT ON COLUMN "eligibility_benefit"."time_period_code" IS 'EB06: 23 calendar year, 29 remaining, 27 visit, 7 day ...';
COMMENT ON COLUMN "eligibility_benefit"."benefit_amount" IS 'EB07.';
COMMENT ON COLUMN "eligibility_benefit"."benefit_pct" IS 'EB08 as a fraction 0 to 1.';
COMMENT ON COLUMN "eligibility_benefit"."quantity_qualifier" IS 'EB09: VS visits, DY days ...';
COMMENT ON COLUMN "eligibility_benefit"."quantity" IS 'EB10.';
COMMENT ON COLUMN "eligibility_benefit"."auth_required" IS 'EB11 mapped to yes, no, unknown.';
COMMENT ON COLUMN "eligibility_benefit"."network_indicator" IS 'EB12: Y, N, W.';
COMMENT ON COLUMN "eligibility_benefit"."cpt_code_id" IS 'When the benefit is for one procedure (EB13).';
COMMENT ON COLUMN "eligibility_benefit"."patient_id" IS 'Copied, so reports skip the join.';
COMMENT ON COLUMN "eligibility_benefit"."payer_id" IS 'Copied, so reports skip the join.';
COMMENT ON COLUMN "eligibility_benefit"."practice_id" IS 'Copied, so reports skip the join.';
COMMENT ON COLUMN "eligibility_benefit"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "eligibility_benefit"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "eligibility_benefit"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "eligibility_benefit"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "eligibility_benefit"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "eligibility_benefit"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "eligibility_benefit"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "eligibility_benefit"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "eligibility_benefit"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "eligibility_benefit"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "patient_estimate_line" IS 'One item on a patient estimate: code, diagnosis, provider or facility, units and expected charge.';
COMMENT ON COLUMN "patient_estimate_line"."patient_estimate_line_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "patient_estimate_line"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "patient_estimate_line"."patient_estimate_id" IS 'The estimate (stable ID).';
COMMENT ON COLUMN "patient_estimate_line"."line_number" IS 'Position.';
COMMENT ON COLUMN "patient_estimate_line"."cpt_code_id" IS 'Service code.';
COMMENT ON COLUMN "patient_estimate_line"."modifier_id" IS 'Modifier.';
COMMENT ON COLUMN "patient_estimate_line"."diagnosis_code_id" IS 'Expected diagnosis (required on a GFE).';
COMMENT ON COLUMN "patient_estimate_line"."provider_id" IS 'Provider expected to perform it.';
COMMENT ON COLUMN "patient_estimate_line"."facility_id" IS 'Facility, for facility items.';
COMMENT ON COLUMN "patient_estimate_line"."is_co_provider_item" IS '1 when another provider or facility supplied the item (co-provider GFE).';
COMMENT ON COLUMN "patient_estimate_line"."units" IS 'Expected units.';
COMMENT ON COLUMN "patient_estimate_line"."expected_charge" IS 'Expected charge.';
COMMENT ON COLUMN "patient_estimate_line"."expected_patient_amount" IS 'Patient share for the line.';
COMMENT ON COLUMN "patient_estimate_line"."appointment_line_id" IS 'The planned service it came from.';
COMMENT ON COLUMN "patient_estimate_line"."billed_amount" IS 'What was billed for the item, rebuilt from bill lines.';
COMMENT ON COLUMN "patient_estimate_line"."practice_id" IS 'Copied, so reports skip the join.';
COMMENT ON COLUMN "patient_estimate_line"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "patient_estimate_line"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "patient_estimate_line"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "patient_estimate_line"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "patient_estimate_line"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "patient_estimate_line"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "patient_estimate_line"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "patient_estimate_line"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "patient_estimate_line"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "patient_estimate_line"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "encounter" IS 'One row per visit version.';
COMMENT ON COLUMN "encounter"."encounter_id" IS 'Stable ID of the record: the same on every version. The primary key is (encounter_id, version). Every link from another table uses encounter_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.';
COMMENT ON COLUMN "encounter"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "encounter"."encounter_number" IS 'The client''s own visit ID. Restricted.';
COMMENT ON COLUMN "encounter"."practice_id" IS 'Billing entity.';
COMMENT ON COLUMN "encounter"."patient_id" IS 'The patient.';
COMMENT ON COLUMN "encounter"."encounter_date" IS 'Date of service; bill lag and timely filing start here.';
COMMENT ON COLUMN "encounter"."rendering_provider_id" IS 'Who saw the patient; productivity and documentation owner.';
COMMENT ON COLUMN "encounter"."encounter_status" IS 'In progress, completed, note pending, signed, charge ready.';
COMMENT ON COLUMN "encounter"."appointment_id" IS 'Appointment-to-visit conversion. Blank for walk-ins.';
COMMENT ON COLUMN "encounter"."payer_id" IS 'Insurer at the visit; eligibility on the date of service.';
COMMENT ON COLUMN "encounter"."coverage_id" IS 'The policy in force at the visit.';
COMMENT ON COLUMN "encounter"."facility_id" IS 'Site reporting.';
COMMENT ON COLUMN "encounter"."place_of_service_id" IS 'Pricing differences.';
COMMENT ON COLUMN "encounter"."specialty_id" IS 'Specialty reports.';
COMMENT ON COLUMN "encounter"."encounter_type" IS 'New, established, preventive, emergency, telehealth; sets the expected visit level.';
COMMENT ON COLUMN "encounter"."visit_minutes" IS 'Time-based coding; productivity.';
COMMENT ON COLUMN "encounter"."note_status" IS 'None, draft, signed, amended. Counts only, never note text. Rebuilt from the note records.';
COMMENT ON COLUMN "encounter"."note_signed_date" IS 'Signature timing.';
COMMENT ON COLUMN "encounter"."signature_lag_days" IS 'Visit to signed note.';
COMMENT ON COLUMN "encounter"."elements_documented_count" IS 'Count of note elements present (rows in document_element); documentation completeness.';
COMMENT ON COLUMN "encounter"."charge_status" IS 'Not entered, entered, held, billed. Detects bill lag and missed charges.';
COMMENT ON COLUMN "encounter"."coding_status" IS 'Not reviewed, suggested, accepted, changed.';
COMMENT ON COLUMN "encounter"."principal_diagnosis_code_id" IS 'Condition-level analysis; the line-level diagnoses are in the details.';
COMMENT ON COLUMN "encounter"."authorization_id" IS 'Ties the visit to its authorization.';
COMMENT ON COLUMN "encounter"."supervising_provider_id" IS 'Supervised visits.';
COMMENT ON COLUMN "encounter"."referring_provider_id" IS 'HMO referrals.';
COMMENT ON COLUMN "encounter"."referral_id" IS 'The referral this visit was performed under, when there is one.';
COMMENT ON COLUMN "encounter"."version" IS '1 for the first row; higher for each change.';
COMMENT ON COLUMN "encounter"."is_current" IS '1 on the latest version. Counts use current rows only.';
COMMENT ON COLUMN "encounter"."previous_encounter_id" IS 'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.';
COMMENT ON COLUMN "encounter"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "encounter"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "encounter"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "encounter"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "encounter"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "encounter"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "encounter"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "encounter"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "encounter"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "encounter"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "document" IS 'One row per clinical or administrative document in the EMR (visit note, consent, advance notice, plan of care, result, letter, document pack): who, when, status, signatures. Never the content.';
COMMENT ON COLUMN "document"."document_id" IS 'Stable ID of the record: the same on every version. The primary key is (document_id, version). Every link from another table uses document_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.';
COMMENT ON COLUMN "document"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "document"."document_number" IS 'The EMR''s own ID for the note or document. Makes loads repeatable. Restricted.';
COMMENT ON COLUMN "document"."practice_id" IS 'Reports by practice.';
COMMENT ON COLUMN "document"."patient_id" IS 'Which patient''s chart. Hashed identity only.';
COMMENT ON COLUMN "document"."document_class" IS 'Broad family: note, consent, notice, plan_of_care, order_document, referral_document, result, letter, pack. Lets agents ask for all notes or all consents.';
COMMENT ON COLUMN "document"."document_type" IS 'Specific type: progress_note, procedure_note, consult, discharge, telephone, addendum, treatment_consent, telehealth_consent, financial_consent, release_of_information, advance_notice, lab_result, imaging_result, letter_of_medical_necessity, cover_note and so on.';
COMMENT ON COLUMN "document"."document_status" IS 'Where the document stands: not_started, draft, pended, signed, locked, amended, entered_in_error; for consents and notices on_file, missing, expired, withdrawn; for results received, reviewed. Drives the chase list.';
COMMENT ON COLUMN "document"."encounter_id" IS 'The visit the document belongs to. Blank for a standing consent.';
COMMENT ON COLUMN "document"."authorization_id" IS 'The authorization request the document supports (the supporting-information link). Blank otherwise.';
COMMENT ON COLUMN "document"."claim_id" IS 'The claim the document supports, for attachments and records requests. Blank otherwise.';
COMMENT ON COLUMN "document"."author_provider_id" IS 'The clinician who wrote or signed it (internal provider, never a name).';
COMMENT ON COLUMN "document"."signer_role" IS 'Role of the signer: physician, nurse_practitioner, physician_assistant, resident, therapist, other. Supervision and incident-to rules depend on it.';
COMMENT ON COLUMN "document"."document_date" IS 'Date the document was started (note date, consent date). Late entries are measured against the visit date.';
COMMENT ON COLUMN "document"."signed_at" IS 'Date and time of the signature. Signature lag and the time of day a note is signed.';
COMMENT ON COLUMN "document"."is_late_entry" IS '1 if written well after the visit. Payers question late notes.';
COMMENT ON COLUMN "document"."is_addendum" IS '1 if this row is a later addition to a signed note. The date of the addendum is its signed_at.';
COMMENT ON COLUMN "document"."addendum_of_document_id" IS 'The original note this addendum adds to.';
COMMENT ON COLUMN "document"."is_locked" IS '1 if the document is locked and cannot be edited. A locked unsigned note is a different fix.';
COMMENT ON COLUMN "document"."cosign_required" IS '1 if a second signature is needed (supervision rule).';
COMMENT ON COLUMN "document"."cosign_status" IS 'not_needed, pending or done.';
COMMENT ON COLUMN "document"."cosigned_at" IS 'When the co-signature was added.';
COMMENT ON COLUMN "document"."expiry_date" IS 'When a consent or plan of care stops being valid.';
COMMENT ON COLUMN "document"."minutes_documented" IS 'Minutes written in the note; compared with visit minutes for time-based codes.';
COMMENT ON COLUMN "document"."hpi_component_count" IS 'Number of history-of-present-illness details found; supports the code-level check.';
COMMENT ON COLUMN "document"."ros_system_count" IS 'Number of body systems reviewed; supports the code-level check.';
COMMENT ON COLUMN "document"."mdm_problem_level" IS 'Problems addressed: minimal, low, moderate or high (decision-making input).';
COMMENT ON COLUMN "document"."mdm_data_level" IS 'Data reviewed: minimal, limited, moderate or extensive.';
COMMENT ON COLUMN "document"."mdm_risk_level" IS 'Risk of management: minimal, low, moderate or high.';
COMMENT ON COLUMN "document"."content_hash" IS 'SHA-256 hash of the document. Proves the same text was signed, sent or changed, without keeping it.';
COMMENT ON COLUMN "document"."page_count" IS 'Pages in the document or pack.';
COMMENT ON COLUMN "document"."document_type_code" IS 'Standard code for the type (LOINC or the claim-attachment report type) when the payer needs it.';
COMMENT ON COLUMN "document"."source_quality" IS 'How readable the source is: structured, free_text, scanned_image, dictation. Scanned notes cannot be checked for elements.';
COMMENT ON COLUMN "document"."version" IS '1 for the first row; higher for each change.';
COMMENT ON COLUMN "document"."is_current" IS '1 on the latest version. Counts use current rows only.';
COMMENT ON COLUMN "document"."previous_document_id" IS 'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.';
COMMENT ON COLUMN "document"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "document"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "document"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "document"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "document"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "document"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "document"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "document"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "document"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "document"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "clinical_order" IS 'One row per clinical order (lab, imaging, procedure, equipment, therapy, referral out), with its status and the result status. Reserved word in SQL: always quoted.';
COMMENT ON COLUMN "clinical_order"."clinical_order_id" IS 'Stable ID of the record: the same on every version. The primary key is (clinical_order_id, version). Every link from another table uses clinical_order_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.';
COMMENT ON COLUMN "clinical_order"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "clinical_order"."order_number" IS 'The order number in the EMR. Makes loads repeatable. Restricted.';
COMMENT ON COLUMN "clinical_order"."practice_id" IS 'Reports by practice.';
COMMENT ON COLUMN "clinical_order"."patient_id" IS 'Which patient. Hashed identity only.';
COMMENT ON COLUMN "clinical_order"."encounter_id" IS 'The visit the order came from.';
COMMENT ON COLUMN "clinical_order"."encounter_line_id" IS 'The visit line that records the order (line_status = ordered). From here, billing lines show whether a charge followed.';
COMMENT ON COLUMN "clinical_order"."ordering_provider_id" IS 'Who ordered (internal provider, never a name).';
COMMENT ON COLUMN "clinical_order"."order_type" IS 'lab, imaging, procedure, equipment, therapy, referral.';
COMMENT ON COLUMN "clinical_order"."order_status" IS 'draft, active, signed, completed, cancelled.';
COMMENT ON COLUMN "clinical_order"."order_date" IS 'Date the order was placed.';
COMMENT ON COLUMN "clinical_order"."signed_date" IS 'When the order was signed. Unsigned orders are often not payable.';
COMMENT ON COLUMN "clinical_order"."cpt_code_id" IS 'What was ordered, when a code is known.';
COMMENT ON COLUMN "clinical_order"."diagnosis_code_id" IS 'Main diagnosis written on the order (medical necessity).';
COMMENT ON COLUMN "clinical_order"."authorization_id" IS 'The authorization that covers the order, if one was needed.';
COMMENT ON COLUMN "clinical_order"."auth_required" IS 'yes, no or unknown: whether the order needs an authorization.';
COMMENT ON COLUMN "clinical_order"."document_id" IS 'The signed order document (metadata row).';
COMMENT ON COLUMN "clinical_order"."result_status" IS 'pending, received or reviewed. Orders without a reviewed result may need a follow-up.';
COMMENT ON COLUMN "clinical_order"."result_received_date" IS 'When the result came back.';
COMMENT ON COLUMN "clinical_order"."result_document_id" IS 'The result document (metadata row).';
COMMENT ON COLUMN "clinical_order"."version" IS '1 for the first row; higher for each change.';
COMMENT ON COLUMN "clinical_order"."is_current" IS '1 on the latest version. Counts use current rows only.';
COMMENT ON COLUMN "clinical_order"."previous_clinical_order_id" IS 'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.';
COMMENT ON COLUMN "clinical_order"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "clinical_order"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "clinical_order"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "clinical_order"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "clinical_order"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "clinical_order"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "clinical_order"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "clinical_order"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "clinical_order"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "clinical_order"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "encounter_line" IS 'One row per service performed at the visit.';
COMMENT ON COLUMN "encounter_line"."encounter_line_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "encounter_line"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "encounter_line"."encounter_id" IS 'Ties each performed service to its visit.';
COMMENT ON COLUMN "encounter_line"."line_number" IS 'Position within the visit.';
COMMENT ON COLUMN "encounter_line"."practice_id" IS 'Copied from the header, so reports by practice never join up.';
COMMENT ON COLUMN "encounter_line"."patient_id" IS 'Copied from the header.';
COMMENT ON COLUMN "encounter_line"."payer_id" IS 'Copied from the header, as of this stage.';
COMMENT ON COLUMN "encounter_line"."provider_id" IS 'Copied from the header.';
COMMENT ON COLUMN "encounter_line"."specialty_id" IS 'Copied from the provider''s specialty; fast specialty reports.';
COMMENT ON COLUMN "encounter_line"."cpt_code_id" IS 'The service performed, as entered. The coder''s suggestion lives in the coding review records; the final code sits on the bill line.';
COMMENT ON COLUMN "encounter_line"."units" IS 'Quantity performed.';
COMMENT ON COLUMN "encounter_line"."service_date" IS 'Per-line date for multi-day services.';
COMMENT ON COLUMN "encounter_line"."rendering_provider_id" IS 'When another clinician performed this line.';
COMMENT ON COLUMN "encounter_line"."diagnosis_1_id" IS 'Main diagnosis supporting this service; medical-necessity checks.';
COMMENT ON COLUMN "encounter_line"."diagnosis_2_id" IS 'Second diagnosis.';
COMMENT ON COLUMN "encounter_line"."diagnosis_3_id" IS 'Third diagnosis.';
COMMENT ON COLUMN "encounter_line"."diagnosis_4_id" IS 'Fourth diagnosis.';
COMMENT ON COLUMN "encounter_line"."modifier_1_id" IS 'Pricing and common denial causes.';
COMMENT ON COLUMN "encounter_line"."modifier_2_id" IS 'Second modifier.';
COMMENT ON COLUMN "encounter_line"."modifier_3_id" IS 'Third modifier.';
COMMENT ON COLUMN "encounter_line"."modifier_4_id" IS 'Fourth modifier.';
COMMENT ON COLUMN "encounter_line"."laterality" IS 'Left, right, both. Required for many codes; a common denial.';
COMMENT ON COLUMN "encounter_line"."procedure_documented" IS 'Whether the note supports the procedure. Worked out from the note records.';
COMMENT ON COLUMN "encounter_line"."documented_level" IS 'Visit level (1 to 5) the note supports; compared with the level entered. A number only.';
COMMENT ON COLUMN "encounter_line"."time_minutes" IS 'Units for timed codes.';
COMMENT ON COLUMN "encounter_line"."authorization_id" IS 'Authorization coverage per service.';
COMMENT ON COLUMN "encounter_line"."auth_required" IS 'Yes, no, unknown.';
COMMENT ON COLUMN "encounter_line"."line_status" IS 'Performed, ordered, not done.';
COMMENT ON COLUMN "encounter_line"."expected_charge" IS 'Units x fee list; the missed-charge value.';
COMMENT ON COLUMN "encounter_line"."place_of_service_id" IS 'When different from the visit.';
COMMENT ON COLUMN "encounter_line"."ordering_provider_id" IS 'Who ordered it.';
COMMENT ON COLUMN "encounter_line"."drug_code" IS 'Drug-billing specialties.';
COMMENT ON COLUMN "encounter_line"."ndc_code_id" IS 'Reference row for drug_code.';
COMMENT ON COLUMN "encounter_line"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "encounter_line"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "encounter_line"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "encounter_line"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "encounter_line"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "encounter_line"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "encounter_line"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "encounter_line"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "encounter_line"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "encounter_line"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "encounter_diagnosis" IS 'One diagnosis recorded for a visit.';
COMMENT ON COLUMN "encounter_diagnosis"."encounter_diagnosis_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "encounter_diagnosis"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "encounter_diagnosis"."encounter_id" IS 'The visit (stable ID).';
COMMENT ON COLUMN "encounter_diagnosis"."diagnosis_sequence" IS 'Order on the visit.';
COMMENT ON COLUMN "encounter_diagnosis"."diagnosis_code_id" IS 'The ICD-10-CM code.';
COMMENT ON COLUMN "encounter_diagnosis"."is_principal" IS '1 on the principal diagnosis.';
COMMENT ON COLUMN "encounter_diagnosis"."diagnosis_role" IS 'billing, chief_complaint, comorbidity, admitting.';
COMMENT ON COLUMN "encounter_diagnosis"."practice_id" IS 'Copied, so reports skip the join.';
COMMENT ON COLUMN "encounter_diagnosis"."patient_id" IS 'Copied, so reports skip the join.';
COMMENT ON COLUMN "encounter_diagnosis"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "encounter_diagnosis"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "encounter_diagnosis"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "encounter_diagnosis"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "encounter_diagnosis"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "encounter_diagnosis"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "encounter_diagnosis"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "encounter_diagnosis"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "encounter_diagnosis"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "encounter_diagnosis"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "document_element" IS 'One named element checked in one document: present or not.';
COMMENT ON COLUMN "document_element"."document_element_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "document_element"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "document_element"."document_id" IS 'The document (stable ID).';
COMMENT ON COLUMN "document_element"."element_code" IS 'chief_complaint, history_present, exam, assessment, plan, diagnosis_linked, procedure_note, laterality, result, medical_necessity, mdm, telehealth_statements.';
COMMENT ON COLUMN "document_element"."is_present" IS '1 if found.';
COMMENT ON COLUMN "document_element"."practice_id" IS 'Copied, so reports skip the join.';
COMMENT ON COLUMN "document_element"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "document_element"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "document_element"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "document_element"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "document_element"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "document_element"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "document_element"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "document_element"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "document_element"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "document_element"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "bill" IS 'One row per bill, normally one per visit. Late charges are added as lines.';
COMMENT ON COLUMN "bill"."bill_id" IS 'Stable ID of the record: the same on every version. The primary key is (bill_id, version). Every link from another table uses bill_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.';
COMMENT ON COLUMN "bill"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "bill"."bill_number" IS 'The client''s own charge or bill ID. Restricted.';
COMMENT ON COLUMN "bill"."practice_id" IS 'Billing entity.';
COMMENT ON COLUMN "bill"."patient_id" IS 'The patient.';
COMMENT ON COLUMN "bill"."encounter_id" IS 'Ties the bill to the visit.';
COMMENT ON COLUMN "bill"."service_date" IS 'Start of bill lag and timely filing.';
COMMENT ON COLUMN "bill"."charge_entered_date" IS 'First entry. Bill lag is this minus the service date.';
COMMENT ON COLUMN "bill"."bill_status" IS 'Drafted, held, ready, billed, partly_billed, patient_billed, written_off, voided. Worked out, not typed.';
COMMENT ON COLUMN "bill"."bill_type" IS 'Insurance, self_pay, courtesy, workers_comp_or_auto. Explains why some bills never become a claim.';
COMMENT ON COLUMN "bill"."total_billed" IS 'Gross charges: sum of lines.';
COMMENT ON COLUMN "bill"."billing_provider_id" IS 'Billing enrollment; charges by provider.';
COMMENT ON COLUMN "bill"."rendering_provider_id" IS 'Who performed the service.';
COMMENT ON COLUMN "bill"."specialty_id" IS 'Specialty reports.';
COMMENT ON COLUMN "bill"."payer_id" IS 'Where the bill will go first.';
COMMENT ON COLUMN "bill"."coverage_id" IS 'Policy to bill.';
COMMENT ON COLUMN "bill"."facility_id" IS 'Site reporting.';
COMMENT ON COLUMN "bill"."place_of_service_id" IS 'Pricing.';
COMMENT ON COLUMN "bill"."ready_to_bill_date" IS 'When the note is signed and coding is done. Splits bill lag into documentation delay and billing delay.';
COMMENT ON COLUMN "bill"."hold_reason" IS 'Missing note, authorization, coding or diagnosis.';
COMMENT ON COLUMN "bill"."hold_date" IS 'When the hold began.';
COMMENT ON COLUMN "bill"."last_charge_date" IS 'Late charges added after the first entry.';
COMMENT ON COLUMN "bill"."claims_created" IS 'Claim rollup: shows billed-but-not-claimed. Rebuilt from the claim table.';
COMMENT ON COLUMN "bill"."latest_claim_status" IS 'Claim rollup.';
COMMENT ON COLUMN "bill"."first_claim_submitted_date" IS 'Bill-to-claim lag.';
COMMENT ON COLUMN "bill"."expected_allowed" IS 'Expected revenue before payment.';
COMMENT ON COLUMN "bill"."entered_by_role" IS 'Productivity by role.';
COMMENT ON COLUMN "bill"."no_charge_amount" IS 'Courtesy or write-off before a claim.';
COMMENT ON COLUMN "bill"."patient_statement_flag" IS 'Billed to the patient.';
COMMENT ON COLUMN "bill"."version" IS '1 for the first row; higher for each change.';
COMMENT ON COLUMN "bill"."is_current" IS '1 on the latest version. Counts use current rows only.';
COMMENT ON COLUMN "bill"."previous_bill_id" IS 'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.';
COMMENT ON COLUMN "bill"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "bill"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "bill"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "bill"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "bill"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "bill"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "bill"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "bill"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "bill"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "bill"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "claim" IS 'One row per claim submission to a payer (a replacement is a new row).';
COMMENT ON COLUMN "claim"."claim_id" IS 'Stable ID of the record: the same on every version. The primary key is (claim_id, version). Every link from another table uses claim_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.';
COMMENT ON COLUMN "claim"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "claim"."claim_number" IS 'The client''s claim ID (CLM01). Joins the 837, 277CA, 835 and PM. Restricted.';
COMMENT ON COLUMN "claim"."practice_id" IS 'All reports by practice.';
COMMENT ON COLUMN "claim"."payer_id" IS 'Who we billed.';
COMMENT ON COLUMN "claim"."patient_id" IS 'Duplicates; patient-level balances.';
COMMENT ON COLUMN "claim"."billing_provider_id" IS 'Whose NPI and tax ID billed; enrollment problems.';
COMMENT ON COLUMN "claim"."service_date_from" IS 'Timely filing, aging.';
COMMENT ON COLUMN "claim"."service_date_to" IS 'Last date of service on the claim (multi-day services).';
COMMENT ON COLUMN "claim"."submitted_date" IS 'Claim lag, days in AR.';
COMMENT ON COLUMN "claim"."total_charge" IS 'Base for denial and collection rates. Must equal the sum of the lines.';
COMMENT ON COLUMN "claim"."claim_status" IS 'Submitted, accepted, rejected, pending, paid, partly_paid, denied, closed, voided. The work queue filter.';
COMMENT ON COLUMN "claim"."rendering_provider_id" IS 'Denials and productivity by provider.';
COMMENT ON COLUMN "claim"."supervising_provider_id" IS 'Supervising provider (2310D), for incident-to and mid-level billing.';
COMMENT ON COLUMN "claim"."facility_id" IS 'Site reporting.';
COMMENT ON COLUMN "claim"."place_of_service_id" IS 'Pricing differences.';
COMMENT ON COLUMN "claim"."specialty_id" IS 'Specialty reports.';
COMMENT ON COLUMN "claim"."coverage_id" IS 'Policy billed.';
COMMENT ON COLUMN "claim"."claim_sequence" IS 'Primary, secondary, tertiary: secondary billing and coordination of benefits.';
COMMENT ON COLUMN "claim"."primary_claim_id" IS 'For a secondary or tertiary claim: the claim to the payer before it.';
COMMENT ON COLUMN "claim"."other_payer_paid_amount" IS 'What earlier payers paid (2320 AMT*D), sent on secondary claims.';
COMMENT ON COLUMN "claim"."claim_filing_indicator" IS 'Insurance type on the claim (SBR09: CI commercial, MB Medicare Part B, MC Medicaid, HM HMO ...).';
COMMENT ON COLUMN "claim"."frequency_code" IS '1 original, 7 replacement, 8 void: so resubmits do not double-count.';
COMMENT ON COLUMN "claim"."accept_assignment" IS 'Provider accepts assignment (CLM07: A, B, C).';
COMMENT ON COLUMN "claim"."benefits_assigned" IS 'Patient assigned benefits to the provider (CLM08: Y, N, W).';
COMMENT ON COLUMN "claim"."release_of_info" IS 'Release of information code (CLM09: I, Y).';
COMMENT ON COLUMN "claim"."payer_claim_number" IS 'Payer''s claim number (ICN). Matches appeals and resubmits. Restricted.';
COMMENT ON COLUMN "claim"."original_payer_claim_number" IS 'Payer claim number of the claim being replaced or voided (REF*F8). Required on frequency 7 and 8.';
COMMENT ON COLUMN "claim"."bill_id" IS 'Traces the claim back to the charge.';
COMMENT ON COLUMN "claim"."encounter_id" IS 'Traces the claim back to the visit.';
COMMENT ON COLUMN "claim"."principal_diagnosis_code_id" IS 'Condition-level analysis.';
COMMENT ON COLUMN "claim"."prior_auth_number" IS 'REF*G1: ties an authorization to the claim; reason code 197 denials. Restricted.';
COMMENT ON COLUMN "claim"."authorization_id" IS 'Internal link to the authorization.';
COMMENT ON COLUMN "claim"."paid_amount" IS 'Rollup of payments. Rebuilt nightly; never the source of truth.';
COMMENT ON COLUMN "claim"."patient_responsibility" IS 'Rollup: patient share.';
COMMENT ON COLUMN "claim"."adjusted_amount" IS 'Rollup: contractual write-downs.';
COMMENT ON COLUMN "claim"."denied_amount" IS 'Rollup: denied.';
COMMENT ON COLUMN "claim"."balance" IS 'Rollup: still open.';
COMMENT ON COLUMN "claim"."last_payment_date" IS 'Rollup: latest payment.';
COMMENT ON COLUMN "claim"."last_status_date" IS 'Rollup: latest status event.';
COMMENT ON COLUMN "claim"."claim_type" IS 'Professional (837P). Institutional (837I) is out of scope in this version; the value is reserved until its fields are added.';
COMMENT ON COLUMN "claim"."accident_related" IS 'Accident indicator; some specialties.';
COMMENT ON COLUMN "claim"."referring_provider_id" IS 'Referral; some specialties.';
COMMENT ON COLUMN "claim"."referral_id" IS 'The referral the claim is billed under.';
COMMENT ON COLUMN "claim"."referral_number" IS 'Referral number sent on the claim (REF*9F). Restricted.';
COMMENT ON COLUMN "claim"."batch_control_number" IS 'Batch control number as sent; the file is edi_file_id.';
COMMENT ON COLUMN "claim"."edi_file_id" IS 'The 837 file the claim went out in.';
COMMENT ON COLUMN "claim"."signature_on_file" IS 'Y, N or U (unknown): the provider''s signature is on file, as the 837 states.';
COMMENT ON COLUMN "claim"."onset_date" IS 'Date the condition began, when the claim states one.';
COMMENT ON COLUMN "claim"."late_filing_reason" IS 'Our internal reason a late claim is still acceptable (payer error, coverage dispute). The coded value sent on the claim is delay_reason_code.';
COMMENT ON COLUMN "claim"."delay_reason_code" IS 'X12 delay reason code (CLM20) sent on a late claim.';
COMMENT ON COLUMN "claim"."version" IS '1 for the first row; higher for each change.';
COMMENT ON COLUMN "claim"."is_current" IS '1 on the latest version. Counts use current rows only.';
COMMENT ON COLUMN "claim"."previous_claim_id" IS 'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.';
COMMENT ON COLUMN "claim"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "claim"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "claim"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "claim"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "claim"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "claim"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "claim"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "claim"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "claim"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "claim"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "claim_attachment" IS 'One row per payer records request or attachment announcement for one claim: what was asked, when it is due, what we sent, and the payer''s answer.';
COMMENT ON COLUMN "claim_attachment"."claim_attachment_id" IS 'Stable ID of the record: the same on every version. The primary key is (claim_attachment_id, version). Every link from another table uses claim_attachment_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.';
COMMENT ON COLUMN "claim_attachment"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "claim_attachment"."claim_attachment_number" IS 'Our ID for this request or attachment row. Restricted.';
COMMENT ON COLUMN "claim_attachment"."practice_id" IS 'Reports by practice.';
COMMENT ON COLUMN "claim_attachment"."patient_id" IS 'Which patient. Hashed identity only.';
COMMENT ON COLUMN "claim_attachment"."claim_id" IS 'The claim the request or attachment is about.';
COMMENT ON COLUMN "claim_attachment"."payer_id" IS 'The payer that asked for the records or receives the attachment.';
COMMENT ON COLUMN "claim_attachment"."request_type" IS 'pre_payment_review, post_payment_audit, attachment_request, medical_review, attachment_announcement (sent with the claim), other.';
COMMENT ON COLUMN "claim_attachment"."payer_reference_number" IS 'The payer''s reference for the request; groups rows from one request. Restricted.';
COMMENT ON COLUMN "claim_attachment"."requesting_unit" IS 'Review unit or audit vendor, for example medical_review, audit_vendor.';
COMMENT ON COLUMN "claim_attachment"."request_received_date" IS 'Date the request arrived.';
COMMENT ON COLUMN "claim_attachment"."request_channel" IS 'How it arrived: mail, fax, portal, 277, emr_inbox, phone.';
COMMENT ON COLUMN "claim_attachment"."due_date" IS 'Date the answer is due. Misses are lost money.';
COMMENT ON COLUMN "claim_attachment"."extended_due_date" IS 'Extension date, if the payer gave one.';
COMMENT ON COLUMN "claim_attachment"."request_text_hash" IS 'SHA-256 hash of the request letter, not the letter.';
COMMENT ON COLUMN "claim_attachment"."response_status" IS 'not_started, collecting, ready_for_review, sent, acknowledged, closed.';
COMMENT ON COLUMN "claim_attachment"."response_sent_date" IS 'When our answer went out.';
COMMENT ON COLUMN "claim_attachment"."response_method" IS 'electronic, fax, mail, portal or courier.';
COMMENT ON COLUMN "claim_attachment"."response_tracking_number" IS 'Fax confirmation, portal receipt, courier number or 275 transaction number. Restricted.';
COMMENT ON COLUMN "claim_attachment"."page_count" IS 'Pages sent or announced.';
COMMENT ON COLUMN "claim_attachment"."payer_acknowledgement" IS 'received, incomplete, accepted, rejected.';
COMMENT ON COLUMN "claim_attachment"."attachment_report_type_code" IS 'What kind of document (report type on the claim announcement).';
COMMENT ON COLUMN "claim_attachment"."attachment_transmission_code" IS 'How it is sent: electronic, fax or mail (transmission code).';
COMMENT ON COLUMN "claim_attachment"."attachment_control_number" IS 'ID tying the claim to the later attachment. Restricted.';
COMMENT ON COLUMN "claim_attachment"."document_id" IS 'The document or pack that went out (metadata row; hash and pages live there).';
COMMENT ON COLUMN "claim_attachment"."version" IS '1 for the first row; higher for each change.';
COMMENT ON COLUMN "claim_attachment"."is_current" IS '1 on the latest version. Counts use current rows only.';
COMMENT ON COLUMN "claim_attachment"."previous_claim_attachment_id" IS 'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.';
COMMENT ON COLUMN "claim_attachment"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "claim_attachment"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "claim_attachment"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "claim_attachment"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "claim_attachment"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "claim_attachment"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "claim_attachment"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "claim_attachment"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "claim_attachment"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "claim_attachment"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "bill_line" IS 'One row per charge line on a bill.';
COMMENT ON COLUMN "bill_line"."bill_line_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "bill_line"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "bill_line"."bill_id" IS 'Ties the charge to its bill.';
COMMENT ON COLUMN "bill_line"."line_number" IS 'Position within the bill.';
COMMENT ON COLUMN "bill_line"."practice_id" IS 'Copied from the header, so reports by practice never join up.';
COMMENT ON COLUMN "bill_line"."patient_id" IS 'Copied from the header.';
COMMENT ON COLUMN "bill_line"."payer_id" IS 'Copied from the header, as of this stage.';
COMMENT ON COLUMN "bill_line"."provider_id" IS 'Copied from the header.';
COMMENT ON COLUMN "bill_line"."specialty_id" IS 'Copied from the provider''s specialty; fast specialty reports.';
COMMENT ON COLUMN "bill_line"."cpt_code_id" IS 'The final billed code that will be claimed.';
COMMENT ON COLUMN "bill_line"."units" IS 'Quantity billed.';
COMMENT ON COLUMN "bill_line"."fee_per_unit" IS 'The fee used, saved on the line. Fee lists change, so history must not move.';
COMMENT ON COLUMN "bill_line"."billed_amount" IS 'Units x fee. Base of every charge metric.';
COMMENT ON COLUMN "bill_line"."line_status" IS 'Drafted, held, ready, claimed, patient_billed, written_off, voided. Worked out, not typed.';
COMMENT ON COLUMN "bill_line"."service_date" IS 'Per-line date.';
COMMENT ON COLUMN "bill_line"."modifier_1_id" IS 'Final billed modifier.';
COMMENT ON COLUMN "bill_line"."modifier_2_id" IS 'Second modifier.';
COMMENT ON COLUMN "bill_line"."modifier_3_id" IS 'Third modifier.';
COMMENT ON COLUMN "bill_line"."modifier_4_id" IS 'Fourth modifier.';
COMMENT ON COLUMN "bill_line"."diagnosis_1_id" IS 'Final supporting diagnosis.';
COMMENT ON COLUMN "bill_line"."diagnosis_2_id" IS 'Second diagnosis.';
COMMENT ON COLUMN "bill_line"."diagnosis_3_id" IS 'Third diagnosis.';
COMMENT ON COLUMN "bill_line"."diagnosis_4_id" IS 'Fourth diagnosis.';
COMMENT ON COLUMN "bill_line"."rendering_provider_id" IS 'When different from the bill.';
COMMENT ON COLUMN "bill_line"."encounter_line_id" IS 'Performed-to-billed traceability; missed-charge detection.';
COMMENT ON COLUMN "bill_line"."charge_entered_date" IS 'Detects late charges.';
COMMENT ON COLUMN "bill_line"."cpt_as_entered_id" IS 'The code before coding review: the audit trail.';
COMMENT ON COLUMN "bill_line"."code_changed" IS '1 if coding changed the code.';
COMMENT ON COLUMN "bill_line"."change_approved_by_staff_id" IS 'Pseudonymous approver of a code change. A change with no approver is flagged (codes change only with a named approval). Holds the staff_id of the pseudonymous person.';
COMMENT ON COLUMN "bill_line"."fee_schedule_id" IS 'Which fee schedule (and version) priced the line. The per-unit fee used is saved on the line.';
COMMENT ON COLUMN "bill_line"."expected_allowed" IS 'Contract allowed for the line; expected revenue and underpayment check.';
COMMENT ON COLUMN "bill_line"."hold_reason" IS 'One line can be stuck while the others go.';
COMMENT ON COLUMN "bill_line"."authorization_id" IS 'Authorization on the line.';
COMMENT ON COLUMN "bill_line"."claims_on" IS 'Claim rollup: how many claims carry the line. Rebuilt from claim_line.';
COMMENT ON COLUMN "bill_line"."latest_claim_line_status" IS 'Claim rollup.';
COMMENT ON COLUMN "bill_line"."claimed_date" IS 'First claimed.';
COMMENT ON COLUMN "bill_line"."drug_code" IS 'Drug-billing specialties.';
COMMENT ON COLUMN "bill_line"."ndc_code_id" IS 'Reference row for drug_code.';
COMMENT ON COLUMN "bill_line"."drug_units" IS 'Drug units.';
COMMENT ON COLUMN "bill_line"."drug_unit_measure" IS 'Unit of the drug quantity: UN, ML, GR, F2.';
COMMENT ON COLUMN "bill_line"."place_of_service_id" IS 'When different from the bill.';
COMMENT ON COLUMN "bill_line"."entered_by_role" IS 'Productivity.';
COMMENT ON COLUMN "bill_line"."no_charge_amount" IS 'Courtesy or write-off before a claim.';
COMMENT ON COLUMN "bill_line"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "bill_line"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "bill_line"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "bill_line"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "bill_line"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "bill_line"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "bill_line"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "bill_line"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "bill_line"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "bill_line"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "claim_line" IS 'One row per service line on a claim submission.';
COMMENT ON COLUMN "claim_line"."claim_line_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "claim_line"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "claim_line"."claim_id" IS 'Ties the line to its claim.';
COMMENT ON COLUMN "claim_line"."line_number" IS 'The same procedure can appear twice with different modifiers or sides.';
COMMENT ON COLUMN "claim_line"."practice_id" IS 'Copied from the claim.';
COMMENT ON COLUMN "claim_line"."payer_id" IS 'Copied from the claim; procedure-by-payer reports skip the join.';
COMMENT ON COLUMN "claim_line"."patient_id" IS 'Copied from the claim.';
COMMENT ON COLUMN "claim_line"."billing_provider_id" IS 'Copied from the claim.';
COMMENT ON COLUMN "claim_line"."specialty_id" IS 'Copied from the provider.';
COMMENT ON COLUMN "claim_line"."cpt_code_id" IS 'Procedure level: denials, contract pricing, coding review.';
COMMENT ON COLUMN "claim_line"."units" IS 'Pricing and unit-limit checks.';
COMMENT ON COLUMN "claim_line"."charge_amount" IS 'Base for line realisation and denial rates.';
COMMENT ON COLUMN "claim_line"."line_status" IS 'Submitted, rejected, pending, paid, partly_paid, denied, adjusted. Worked out from events.';
COMMENT ON COLUMN "claim_line"."paid_amount" IS 'Collections. Required once line_status is paid, partly_paid or adjusted (CHECK).';
COMMENT ON COLUMN "claim_line"."service_date" IS 'Matches the 835 line; multi-day services.';
COMMENT ON COLUMN "claim_line"."service_date_to" IS 'Last date of a multi-day line.';
COMMENT ON COLUMN "claim_line"."place_of_service_id" IS 'When the line differs from the claim.';
COMMENT ON COLUMN "claim_line"."modifier_1_id" IS 'Pricing and denial causes.';
COMMENT ON COLUMN "claim_line"."modifier_2_id" IS 'Second modifier.';
COMMENT ON COLUMN "claim_line"."modifier_3_id" IS 'Third modifier.';
COMMENT ON COLUMN "claim_line"."modifier_4_id" IS 'Fourth modifier.';
COMMENT ON COLUMN "claim_line"."diagnosis_pointers" IS 'Which claim diagnoses support this line.';
COMMENT ON COLUMN "claim_line"."primary_diagnosis_code_id" IS 'The diagnosis the first pointer points to, saved on the line.';
COMMENT ON COLUMN "claim_line"."rendering_provider_id" IS 'Procedure productivity; line-level in the 837.';
COMMENT ON COLUMN "claim_line"."ordering_provider_id" IS 'Ordering provider (2420E), required for labs, imaging and DME.';
COMMENT ON COLUMN "claim_line"."supervising_provider_id" IS 'Line-level supervising provider (2420D) when it differs from the claim.';
COMMENT ON COLUMN "claim_line"."allowed_amount" IS 'What the payer will pay for the line; underpayment and realisation.';
COMMENT ON COLUMN "claim_line"."patient_responsibility" IS 'Patient balance and statements.';
COMMENT ON COLUMN "claim_line"."contractual_adjustment" IS 'Write-down to the contract rate.';
COMMENT ON COLUMN "claim_line"."denied_amount" IS 'Denial rate by procedure.';
COMMENT ON COLUMN "claim_line"."primary_denial_reason_id" IS 'First denial reason; the full list is in the denial records.';
COMMENT ON COLUMN "claim_line"."expected_allowed" IS 'Contract allowed at submission; underpayment is a subtraction.';
COMMENT ON COLUMN "claim_line"."bill_line_id" IS 'Traces the line back to the charge; bill lag and missed charges.';
COMMENT ON COLUMN "claim_line"."line_control_number" IS 'The practice''s own line ID; matches 835 lines when the payer reorders or splits lines. Restricted.';
COMMENT ON COLUMN "claim_line"."drug_code" IS 'Drug-billing specialties.';
COMMENT ON COLUMN "claim_line"."ndc_code_id" IS 'Reference row for drug_code.';
COMMENT ON COLUMN "claim_line"."drug_units" IS 'Drug units.';
COMMENT ON COLUMN "claim_line"."drug_unit_measure" IS 'Unit of the drug quantity: UN, ML, GR, F2.';
COMMENT ON COLUMN "claim_line"."line_flags" IS 'Emergency, family planning, EPSDT.';
COMMENT ON COLUMN "claim_line"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "claim_line"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "claim_line"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "claim_line"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "claim_line"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "claim_line"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "claim_line"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "claim_line"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "claim_line"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "claim_line"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "claim_status_history" IS 'One row per status event on a claim submission: sent, acknowledged, rejected, status answer, adjudicated, resubmitted, voided.';
COMMENT ON COLUMN "claim_status_history"."claim_status_history_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "claim_status_history"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "claim_status_history"."claim_id" IS 'The claim submission the event is about.';
COMMENT ON COLUMN "claim_status_history"."claim_line_id" IS 'The line, when the 277CA rejects one line rather than the claim.';
COMMENT ON COLUMN "claim_status_history"."event_type" IS 'Submitted, ack_999, ack_277ca, status_inquiry, status_response, adjudicated, resubmitted, voided.';
COMMENT ON COLUMN "claim_status_history"."event_date" IS 'When it happened.';
COMMENT ON COLUMN "claim_status_history"."status_after" IS 'The claim status after this event.';
COMMENT ON COLUMN "claim_status_history"."practice_id" IS 'Copied from the claim.';
COMMENT ON COLUMN "claim_status_history"."payer_id" IS 'Copied from the claim.';
COMMENT ON COLUMN "claim_status_history"."patient_id" IS 'Copied from the claim.';
COMMENT ON COLUMN "claim_status_history"."event_ts" IS 'Exact time, for turnaround in hours.';
COMMENT ON COLUMN "claim_status_history"."response_sequence" IS 'Order of responses; the first acknowledgement decides first-pass acceptance.';
COMMENT ON COLUMN "claim_status_history"."status_category" IS 'Payer status category from the 277.';
COMMENT ON COLUMN "claim_status_history"."status_category_code_id" IS 'Reference row for status_category.';
COMMENT ON COLUMN "claim_status_history"."status_code" IS 'Payer status code from the 277. For ack_999 events it holds the AK9/IK5 code: A, E, P, M, R, W or X.';
COMMENT ON COLUMN "claim_status_history"."status_code_id" IS 'Reference row for status_code.';
COMMENT ON COLUMN "claim_status_history"."is_rejection" IS 'A technical bounce, before the payer judged the claim.';
COMMENT ON COLUMN "claim_status_history"."rejection_reason" IS 'Error or reason code from the 999 or 277CA.';
COMMENT ON COLUMN "claim_status_history"."rejection_category" IS 'Member ID, provider ID, diagnosis, missing information, duplicate, payer ID.';
COMMENT ON COLUMN "claim_status_history"."is_technical" IS 'Fixable without a clinical decision.';
COMMENT ON COLUMN "claim_status_history"."owner_role" IS 'Who fixes it.';
COMMENT ON COLUMN "claim_status_history"."fix_by_date" IS 'Target to fix and resend.';
COMMENT ON COLUMN "claim_status_history"."channel" IS 'Clearinghouse, payer portal, phone, fax.';
COMMENT ON COLUMN "claim_status_history"."payer_claim_number" IS 'Payer''s number, assigned on acceptance. Restricted.';
COMMENT ON COLUMN "claim_status_history"."billing_provider_id" IS 'Copied from the claim.';
COMMENT ON COLUMN "claim_status_history"."specialty_id" IS 'Copied.';
COMMENT ON COLUMN "claim_status_history"."reported_paid_amount" IS 'Paid amount stated on a status answer before the remittance arrives.';
COMMENT ON COLUMN "claim_status_history"."acked_control_number" IS 'Control number a 999 or 277CA acknowledges.';
COMMENT ON COLUMN "claim_status_history"."clearinghouse_batch_number" IS 'Batch the claim travelled in.';
COMMENT ON COLUMN "claim_status_history"."edi_file_id" IS 'The acknowledgement or status file the event came in.';
COMMENT ON COLUMN "claim_status_history"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "claim_status_history"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "claim_status_history"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "claim_status_history"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "claim_status_history"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "claim_status_history"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "claim_status_history"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "claim_status_history"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "claim_status_history"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "claim_status_history"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "claim_diagnosis" IS 'One diagnosis on a claim, in its HI position (1 to 12).';
COMMENT ON COLUMN "claim_diagnosis"."claim_diagnosis_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "claim_diagnosis"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "claim_diagnosis"."claim_id" IS 'The claim (stable ID).';
COMMENT ON COLUMN "claim_diagnosis"."diagnosis_sequence" IS 'Position 1 to 12 in HI order. The number claim_line.diagnosis_pointers uses.';
COMMENT ON COLUMN "claim_diagnosis"."diagnosis_code_id" IS 'The ICD-10-CM code.';
COMMENT ON COLUMN "claim_diagnosis"."is_principal" IS '1 on position 1.';
COMMENT ON COLUMN "claim_diagnosis"."poa_indicator" IS 'Present on admission: Y, N, U, W, 1. Institutional only; blank on professional claims.';
COMMENT ON COLUMN "claim_diagnosis"."practice_id" IS 'Copied, so reports skip the join.';
COMMENT ON COLUMN "claim_diagnosis"."payer_id" IS 'Copied, so reports skip the join.';
COMMENT ON COLUMN "claim_diagnosis"."patient_id" IS 'Copied, so reports skip the join.';
COMMENT ON COLUMN "claim_diagnosis"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "claim_diagnosis"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "claim_diagnosis"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "claim_diagnosis"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "claim_diagnosis"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "claim_diagnosis"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "claim_diagnosis"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "claim_diagnosis"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "claim_diagnosis"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "claim_diagnosis"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "claim_attachment_document" IS 'One document type asked for in a records request, and the document sent for it.';
COMMENT ON COLUMN "claim_attachment_document"."claim_attachment_document_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "claim_attachment_document"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "claim_attachment_document"."claim_attachment_id" IS 'The request (stable ID).';
COMMENT ON COLUMN "claim_attachment_document"."document_type" IS 'Type asked for; same values as document.document_type.';
COMMENT ON COLUMN "claim_attachment_document"."document_id" IS 'The document sent for it.';
COMMENT ON COLUMN "claim_attachment_document"."item_status" IS 'requested, found, missing, sent.';
COMMENT ON COLUMN "claim_attachment_document"."page_count" IS 'Pages sent.';
COMMENT ON COLUMN "claim_attachment_document"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "claim_attachment_document"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "claim_attachment_document"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "claim_attachment_document"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "claim_attachment_document"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "claim_attachment_document"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "claim_attachment_document"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "claim_attachment_document"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "claim_attachment_document"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "claim_attachment_document"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "claim_edit" IS 'One edit raised on a claim (or line) before it reached the payer: PM scrubber, clearinghouse edit or our own agent check.';
COMMENT ON COLUMN "claim_edit"."claim_edit_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "claim_edit"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "claim_edit"."claim_id" IS 'The claim (stable ID).';
COMMENT ON COLUMN "claim_edit"."claim_line_id" IS 'The line, for line-level edits.';
COMMENT ON COLUMN "claim_edit"."edit_source" IS 'pm_scrubber, clearinghouse, agent, payer_front_end.';
COMMENT ON COLUMN "claim_edit"."edit_code" IS 'The vendor''s edit code.';
COMMENT ON COLUMN "claim_edit"."edit_category" IS 'Our grouping: demographics, eligibility, coding, ncci, mue, lcd_ncd, authorization, provider, format.';
COMMENT ON COLUMN "claim_edit"."severity" IS 'error, warning, info.';
COMMENT ON COLUMN "claim_edit"."edit_ts" IS 'When raised.';
COMMENT ON COLUMN "claim_edit"."edit_status" IS 'open, fixed, overridden, voided.';
COMMENT ON COLUMN "claim_edit"."resolved_ts" IS 'When fixed or overridden.';
COMMENT ON COLUMN "claim_edit"."resolved_by_staff_id" IS 'Who fixed or overrode it.';
COMMENT ON COLUMN "claim_edit"."fix_field_code" IS 'Which claim field was changed to fix it.';
COMMENT ON COLUMN "claim_edit"."payer_rule_id" IS 'Our rule behind the edit, when the source is an agent.';
COMMENT ON COLUMN "claim_edit"."agent_decision_id" IS 'Agent decision that raised it.';
COMMENT ON COLUMN "claim_edit"."edi_file_id" IS 'Clearinghouse report file.';
COMMENT ON COLUMN "claim_edit"."practice_id" IS 'Copied, so reports skip the join.';
COMMENT ON COLUMN "claim_edit"."payer_id" IS 'Copied, so reports skip the join.';
COMMENT ON COLUMN "claim_edit"."patient_id" IS 'Copied, so reports skip the join.';
COMMENT ON COLUMN "claim_edit"."billing_provider_id" IS 'Copied, so reports skip the join.';
COMMENT ON COLUMN "claim_edit"."cpt_code_id" IS 'Line code, copied for edit analysis.';
COMMENT ON COLUMN "claim_edit"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "claim_edit"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "claim_edit"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "claim_edit"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "claim_edit"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "claim_edit"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "claim_edit"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "claim_edit"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "claim_edit"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "claim_edit"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "ledger_entry" IS 'One row per money movement on a charge line: charge, payment, adjustment, write-off, refund, transfer, opening balance.';
COMMENT ON COLUMN "ledger_entry"."ledger_entry_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "ledger_entry"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "ledger_entry"."transaction_number" IS 'The client''s posting ID. Makes loads repeatable. Restricted.';
COMMENT ON COLUMN "ledger_entry"."practice_id" IS 'Reports by practice.';
COMMENT ON COLUMN "ledger_entry"."patient_id" IS 'Patient accounts.';
COMMENT ON COLUMN "ledger_entry"."bill_line_id" IS 'The charge line the money acts on.';
COMMENT ON COLUMN "ledger_entry"."transaction_type" IS 'Charge, payment, adjustment, write_off, refund, transfer, opening_balance.';
COMMENT ON COLUMN "ledger_entry"."amount" IS 'Amount as posted.';
COMMENT ON COLUMN "ledger_entry"."balance_effect" IS 'Signed effect on the balance, so balance = a simple sum.';
COMMENT ON COLUMN "ledger_entry"."transaction_date" IS 'Business date of the event.';
COMMENT ON COLUMN "ledger_entry"."responsible_party" IS 'Payer or patient: the AR split.';
COMMENT ON COLUMN "ledger_entry"."from_party" IS 'On transfer rows: who owed before (payer, patient).';
COMMENT ON COLUMN "ledger_entry"."to_party" IS 'On transfer rows: who owes after.';
COMMENT ON COLUMN "ledger_entry"."to_payer_id" IS 'On a transfer to another payer: that payer.';
COMMENT ON COLUMN "ledger_entry"."claim_line_id" IS 'Payer-side tracing. Blank for self-pay.';
COMMENT ON COLUMN "ledger_entry"."claim_id" IS 'Payer-side tracing.';
COMMENT ON COLUMN "ledger_entry"."transaction_subtype" IS 'Contractual, denial, bad debt, charity, overpayment recoupment, patient refund and so on.';
COMMENT ON COLUMN "ledger_entry"."posted_date" IS 'When posted; backdating and posting lag.';
COMMENT ON COLUMN "ledger_entry"."payer_id" IS 'Copied from the charge.';
COMMENT ON COLUMN "ledger_entry"."provider_id" IS 'Copied from the charge.';
COMMENT ON COLUMN "ledger_entry"."specialty_id" IS 'Copied from the provider.';
COMMENT ON COLUMN "ledger_entry"."cpt_code_id" IS 'Copied from the charge.';
COMMENT ON COLUMN "ledger_entry"."adjustment_reason_id" IS 'Reason for an adjustment: contractual, patient, other.';
COMMENT ON COLUMN "ledger_entry"."group_code" IS 'CO, PR, OA, PI, CR.';
COMMENT ON COLUMN "ledger_entry"."payment_id" IS 'The payment (EFT, check, card) the money came in.';
COMMENT ON COLUMN "ledger_entry"."payment_method" IS 'EFT, check, virtual card, card, cash.';
COMMENT ON COLUMN "ledger_entry"."payment_number" IS 'Trace or check number. Restricted.';
COMMENT ON COLUMN "ledger_entry"."approved_by_staff_id" IS 'Pseudonymous approver. Write-offs and refunds need a named approver; one without is flagged. Holds the staff_id of the pseudonymous person.';
COMMENT ON COLUMN "ledger_entry"."approved_date" IS 'When approved.';
COMMENT ON COLUMN "ledger_entry"."reverses_ledger_entry_id" IS 'The row this reverses.';
COMMENT ON COLUMN "ledger_entry"."is_reversal" IS '1 on a reversing row.';
COMMENT ON COLUMN "ledger_entry"."batch_number" IS 'Posting batch.';
COMMENT ON COLUMN "ledger_entry"."posted_by_role" IS 'Posting analysis.';
COMMENT ON COLUMN "ledger_entry"."refund_reason" IS 'Why refunded.';
COMMENT ON COLUMN "ledger_entry"."remark_code_id" IS 'Remark (RARC) that explains an adjustment or denial further.';
COMMENT ON COLUMN "ledger_entry"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "ledger_entry"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "ledger_entry"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "ledger_entry"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "ledger_entry"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "ledger_entry"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "ledger_entry"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "ledger_entry"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "ledger_entry"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "ledger_entry"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "denial" IS 'One row per denied amount on one claim line, per remittance. Status changes are kept as versions.';
COMMENT ON COLUMN "denial"."denial_id" IS 'Stable ID of the record: the same on every version. The primary key is (denial_id, version). Every link from another table uses denial_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.';
COMMENT ON COLUMN "denial"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "denial"."claim_id" IS 'The claim submission that was denied.';
COMMENT ON COLUMN "denial"."claim_line_id" IS 'The line. A whole-claim denial is spread over its lines.';
COMMENT ON COLUMN "denial"."practice_id" IS 'Copied from the claim.';
COMMENT ON COLUMN "denial"."patient_id" IS 'Copied from the claim.';
COMMENT ON COLUMN "denial"."payer_id" IS 'Copied from the claim.';
COMMENT ON COLUMN "denial"."denial_date" IS 'The payer''s decision date.';
COMMENT ON COLUMN "denial"."denied_amount" IS 'Base of the denial rate.';
COMMENT ON COLUMN "denial"."adjustment_reason_id" IS 'Main reason code: denial by reason without joining the details.';
COMMENT ON COLUMN "denial"."denial_status" IS 'Open, corrected_resubmitted, appealed, written_off, recovered, closed, expired.';
COMMENT ON COLUMN "denial"."ledger_entry_id" IS 'The ledger row that carried the denial.';
COMMENT ON COLUMN "denial"."bill_line_id" IS 'The charge line behind it.';
COMMENT ON COLUMN "denial"."group_code" IS 'CO, PR, OA, PI, CR.';
COMMENT ON COLUMN "denial"."reason_category" IS 'Eligibility, authorization, coding, documentation, billing, medical necessity, timely filing, duplicate, coordination of benefits.';
COMMENT ON COLUMN "denial"."clock_start_date" IS 'Appeal clock starts (denial notice).';
COMMENT ON COLUMN "denial"."appeal_deadline" IS 'Deadline and money at risk.';
COMMENT ON COLUMN "denial"."root_cause" IS 'Why it happened.';
COMMENT ON COLUMN "denial"."upstream_stage" IS 'Which journey stage could have caught it.';
COMMENT ON COLUMN "denial"."is_preventable" IS 'Could have been caught before sending.';
COMMENT ON COLUMN "denial"."is_technical" IS 'Fixable without a clinical decision.';
COMMENT ON COLUMN "denial"."owner_role" IS 'Billing, coding, front desk, provider.';
COMMENT ON COLUMN "denial"."resolved_date" IS 'Days to resolve.';
COMMENT ON COLUMN "denial"."outcome" IS 'Overturned, corrected, written off, accepted.';
COMMENT ON COLUMN "denial"."recovered_amount" IS 'Recovery. Rebuilt from the ledger.';
COMMENT ON COLUMN "denial"."is_repeat" IS 'Same line denied again.';
COMMENT ON COLUMN "denial"."denial_count_on_line" IS 'Times this line has been denied.';
COMMENT ON COLUMN "denial"."resubmitted_claim_id" IS 'The replacement claim.';
COMMENT ON COLUMN "denial"."cpt_code_id" IS 'Copied for reports.';
COMMENT ON COLUMN "denial"."provider_id" IS 'Copied for reports.';
COMMENT ON COLUMN "denial"."specialty_id" IS 'Copied for reports.';
COMMENT ON COLUMN "denial"."is_claim_level" IS 'Spread from a whole-claim denial.';
COMMENT ON COLUMN "denial"."units_denied" IS 'Partial-unit denials.';
COMMENT ON COLUMN "denial"."authorization_id" IS 'Authorization denials.';
COMMENT ON COLUMN "denial"."version" IS '1 for the first row; higher for each change.';
COMMENT ON COLUMN "denial"."is_current" IS '1 on the latest version. Counts use current rows only.';
COMMENT ON COLUMN "denial"."previous_denial_id" IS 'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.';
COMMENT ON COLUMN "denial"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "denial"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "denial"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "denial"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "denial"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "denial"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "denial"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "denial"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "denial"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "denial"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "payment" IS 'One row per payment received: payer EFT, check or virtual card, or a patient payment. A reissue or void is a new version.';
COMMENT ON COLUMN "payment"."payment_id" IS 'Stable ID of the record: the same on every version. The primary key is (payment_id, version). Every link from another table uses payment_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.';
COMMENT ON COLUMN "payment"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "payment"."payment_number" IS 'Trace or check number. Restricted.';
COMMENT ON COLUMN "payment"."practice_id" IS 'Reports by practice.';
COMMENT ON COLUMN "payment"."payment_source" IS 'Payer or patient.';
COMMENT ON COLUMN "payment"."payment_date" IS 'Payment effective date.';
COMMENT ON COLUMN "payment"."payment_amount" IS 'Total of the payment.';
COMMENT ON COLUMN "payment"."payment_method" IS 'EFT, check, virtual card, card, cash, other.';
COMMENT ON COLUMN "payment"."payer_id" IS 'Blank for patient payments.';
COMMENT ON COLUMN "payment"."patient_id" IS 'On patient payments: the patient paid for.';
COMMENT ON COLUMN "payment"."guarantor_id" IS 'On patient payments: the guarantor who paid.';
COMMENT ON COLUMN "payment"."appointment_id" IS 'Visit the payment was collected for (point-of-service copay, prepayment).';
COMMENT ON COLUMN "payment"."collection_point" IS 'pre_visit, check_in, check_out, statement, portal, phone, payment_plan, collections.';
COMMENT ON COLUMN "payment"."payment_type" IS 'Payment, takeback, refund.';
COMMENT ON COLUMN "payment"."received_date" IS 'When the money or remittance arrived.';
COMMENT ON COLUMN "payment"."posted_date" IS 'When posted; posting lag.';
COMMENT ON COLUMN "payment"."credit_debit" IS 'C for money in; D for a takeback.';
COMMENT ON COLUMN "payment"."has_remittance" IS 'Electronic remittance received (vs paper explanation).';
COMMENT ON COLUMN "payment"."edi_file_id" IS 'The 835 file the payment came in.';
COMMENT ON COLUMN "payment"."claim_count" IS 'Claims covered.';
COMMENT ON COLUMN "payment"."posted_amount" IS 'Rollup of linked ledger_entry.';
COMMENT ON COLUMN "payment"."unapplied_amount" IS 'Payment minus posted. Includes patient prepayments and copays held until the charge exists (ledger rows always need a charge line).';
COMMENT ON COLUMN "payment"."plb_amount" IS 'Provider-level adjustments on the payment (takebacks, interest).';
COMMENT ON COLUMN "payment"."reconciles" IS '1 when posted equals the payment total.';
COMMENT ON COLUMN "payment"."is_void" IS 'Voided or bounced.';
COMMENT ON COLUMN "payment"."payee_provider_id" IS 'Payee.';
COMMENT ON COLUMN "payment"."version" IS '1 for the first row; higher for each change.';
COMMENT ON COLUMN "payment"."is_current" IS '1 on the latest version. Counts use current rows only.';
COMMENT ON COLUMN "payment"."previous_payment_id" IS 'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.';
COMMENT ON COLUMN "payment"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "payment"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "payment"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "payment"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "payment"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "payment"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "payment"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "payment"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "payment"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "payment"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "payment_plan" IS 'One payment plan agreed with a patient: total, instalment size, how many instalments are missed and whether autopay is on. A change is a new version.';
COMMENT ON COLUMN "payment_plan"."payment_plan_id" IS 'Stable ID of the record: the same on every version. The primary key is (payment_plan_id, version). Every link from another table uses payment_plan_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.';
COMMENT ON COLUMN "payment_plan"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "payment_plan"."payment_plan_number" IS 'The practice''s own plan number. Restricted.';
COMMENT ON COLUMN "payment_plan"."patient_id" IS 'The patient who owns the plan.';
COMMENT ON COLUMN "payment_plan"."guarantor_id" IS 'The guarantor account responsible for the patient balance.';
COMMENT ON COLUMN "payment_plan"."plan_status" IS 'Active, completed, defaulted or cancelled.';
COMMENT ON COLUMN "payment_plan"."start_date" IS 'First instalment date or agreement date.';
COMMENT ON COLUMN "payment_plan"."total_amount" IS 'Balance put on the plan.';
COMMENT ON COLUMN "payment_plan"."practice_id" IS 'Copied, for reports by practice.';
COMMENT ON COLUMN "payment_plan"."instalment_amount" IS 'Agreed amount per instalment.';
COMMENT ON COLUMN "payment_plan"."instalment_count" IS 'Number of instalments agreed.';
COMMENT ON COLUMN "payment_plan"."frequency" IS 'Weekly, biweekly or monthly.';
COMMENT ON COLUMN "payment_plan"."next_due_date" IS 'Next instalment due date. The AR forecast reads it.';
COMMENT ON COLUMN "payment_plan"."missed_instalments" IS 'Instalments missed as known on the row date. Kept because it depends on what was known then.';
COMMENT ON COLUMN "payment_plan"."last_missed_date" IS 'Due date of the latest missed instalment.';
COMMENT ON COLUMN "payment_plan"."autopay_enrolled" IS 'Whether recurring payment is set up. A flag only; card or bank details are never stored.';
COMMENT ON COLUMN "payment_plan"."end_date" IS 'Date the plan completed, defaulted or was cancelled.';
COMMENT ON COLUMN "payment_plan"."version" IS '1 for the first row; higher for each change.';
COMMENT ON COLUMN "payment_plan"."is_current" IS '1 on the latest version. Counts use current rows only.';
COMMENT ON COLUMN "payment_plan"."previous_payment_plan_id" IS 'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.';
COMMENT ON COLUMN "payment_plan"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "payment_plan"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "payment_plan"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "payment_plan"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "payment_plan"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "payment_plan"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "payment_plan"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "payment_plan"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "payment_plan"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "payment_plan"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "patient_contact_preference" IS 'The contact consent and preferences of one patient, as flags only. No phone numbers, emails or addresses. A change (new consent, opt-out) is a new version, so consent history is kept.';
COMMENT ON COLUMN "patient_contact_preference"."patient_contact_preference_id" IS 'Stable ID of the record: the same on every version. The primary key is (patient_contact_preference_id, version). Every link from another table uses patient_contact_preference_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.';
COMMENT ON COLUMN "patient_contact_preference"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "patient_contact_preference"."patient_id" IS 'The patient these preferences belong to.';
COMMENT ON COLUMN "patient_contact_preference"."opt_out" IS '1 if the patient asked not to be contacted. Stops all outreach.';
COMMENT ON COLUMN "patient_contact_preference"."text_consent" IS '1 if the patient agreed to be texted.';
COMMENT ON COLUMN "patient_contact_preference"."preferred_channel" IS 'Mail, portal, sms or phone.';
COMMENT ON COLUMN "patient_contact_preference"."quiet_hours_start" IS 'Hour of the day (0 to 23) when contact must stop.';
COMMENT ON COLUMN "patient_contact_preference"."quiet_hours_end" IS 'Hour of the day (0 to 23) when contact may resume.';
COMMENT ON COLUMN "patient_contact_preference"."contact_time_zone" IS 'Time zone the quiet hours are in (the patient''s, not the practice''s).';
COMMENT ON COLUMN "patient_contact_preference"."address_status" IS 'Valid, returned or unknown: whether mail reaches the patient. The address itself is not stored.';
COMMENT ON COLUMN "patient_contact_preference"."has_phone" IS '1 if a phone number or email is on file. The value is not stored.';
COMMENT ON COLUMN "patient_contact_preference"."autodial_consent" IS '1 if the patient agreed to auto-dialed or recorded calls.';
COMMENT ON COLUMN "patient_contact_preference"."consent_date" IS 'Date the latest consent was given.';
COMMENT ON COLUMN "patient_contact_preference"."consent_source" IS 'Where consent was captured: form, portal, verbal.';
COMMENT ON COLUMN "patient_contact_preference"."consent_wording_version" IS 'Version of the consent wording shown. Needed to prove what the patient agreed to.';
COMMENT ON COLUMN "patient_contact_preference"."opt_out_date" IS 'Date the patient opted out.';
COMMENT ON COLUMN "patient_contact_preference"."has_authorized_rep" IS '1 if the patient allows us to talk to a family member or other representative.';
COMMENT ON COLUMN "patient_contact_preference"."guarantor_hash" IS 'Kept for matching; the account is guarantor_id.';
COMMENT ON COLUMN "patient_contact_preference"."guarantor_id" IS 'The guarantor these preferences belong to, when not the patient.';
COMMENT ON COLUMN "patient_contact_preference"."version" IS '1 for the first row; higher for each change.';
COMMENT ON COLUMN "patient_contact_preference"."is_current" IS '1 on the latest version. Counts use current rows only.';
COMMENT ON COLUMN "patient_contact_preference"."previous_patient_contact_preference_id" IS 'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.';
COMMENT ON COLUMN "patient_contact_preference"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "patient_contact_preference"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "patient_contact_preference"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "patient_contact_preference"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "patient_contact_preference"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "patient_contact_preference"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "patient_contact_preference"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "patient_contact_preference"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "patient_contact_preference"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "patient_contact_preference"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "denial_reason" IS 'One row per reason code or remark code behind a denial.';
COMMENT ON COLUMN "denial_reason"."denial_reason_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "denial_reason"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "denial_reason"."denial_id" IS 'The denial it explains (stable ID).';
COMMENT ON COLUMN "denial_reason"."detail_seq" IS 'Order within the denial.';
COMMENT ON COLUMN "denial_reason"."detail_type" IS 'Reason or remark.';
COMMENT ON COLUMN "denial_reason"."adjustment_reason_id" IS 'The reason code. Required when detail_type = reason (CHECK).';
COMMENT ON COLUMN "denial_reason"."remark_code_id" IS 'The remark code. Required when detail_type = remark (CHECK).';
COMMENT ON COLUMN "denial_reason"."group_code" IS 'CO, PR, OA, PI, CR.';
COMMENT ON COLUMN "denial_reason"."reason_amount" IS 'Amount tied to this reason; sums to the denial amount.';
COMMENT ON COLUMN "denial_reason"."is_amount_allocated" IS '1 if we assigned the amount because the payer gave one total.';
COMMENT ON COLUMN "denial_reason"."reason_units" IS 'Units tied to the reason.';
COMMENT ON COLUMN "denial_reason"."is_primary" IS 'The main reason.';
COMMENT ON COLUMN "denial_reason"."reason_category" IS 'Copied from the reason.';
COMMENT ON COLUMN "denial_reason"."is_appealable" IS 'Rule output.';
COMMENT ON COLUMN "denial_reason"."suggested_action" IS 'Fix and resubmit, appeal, write-off review, bill patient, informational. A proposal only.';
COMMENT ON COLUMN "denial_reason"."denial_date" IS 'Copied for reports.';
COMMENT ON COLUMN "denial_reason"."practice_id" IS 'Copied.';
COMMENT ON COLUMN "denial_reason"."payer_id" IS 'Copied.';
COMMENT ON COLUMN "denial_reason"."cpt_code_id" IS 'Copied.';
COMMENT ON COLUMN "denial_reason"."claim_line_id" IS 'Copied.';
COMMENT ON COLUMN "denial_reason"."provider_id" IS 'Copied.';
COMMENT ON COLUMN "denial_reason"."specialty_id" IS 'Copied.';
COMMENT ON COLUMN "denial_reason"."patient_id" IS 'Copied.';
COMMENT ON COLUMN "denial_reason"."payer_reason_code" IS 'Payer-specific code.';
COMMENT ON COLUMN "denial_reason"."remark_qualifier" IS 'Which code list.';
COMMENT ON COLUMN "denial_reason"."documents_needed" IS 'What proof is needed.';
COMMENT ON COLUMN "denial_reason"."reason_corrected" IS 'Which reason was fixed.';
COMMENT ON COLUMN "denial_reason"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "denial_reason"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "denial_reason"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "denial_reason"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "denial_reason"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "denial_reason"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "denial_reason"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "denial_reason"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "denial_reason"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "denial_reason"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "ar_interval" IS 'One row per charge line per period (month by default).';
COMMENT ON COLUMN "ar_interval"."ar_interval_id" IS 'Stable ID of the record: the same on every version. The primary key is (ar_interval_id, version). Every link from another table uses ar_interval_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.';
COMMENT ON COLUMN "ar_interval"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "ar_interval"."bill_line_id" IS 'The charge line (the account).';
COMMENT ON COLUMN "ar_interval"."period_start_date" IS 'Start of the period.';
COMMENT ON COLUMN "ar_interval"."period_end_date" IS 'End of the period.';
COMMENT ON COLUMN "ar_interval"."period_type" IS 'Month or week.';
COMMENT ON COLUMN "ar_interval"."practice_id" IS 'Reports by practice.';
COMMENT ON COLUMN "ar_interval"."patient_id" IS 'Patient accounts.';
COMMENT ON COLUMN "ar_interval"."guarantor_id" IS 'The guarantor account responsible for the patient balance.';
COMMENT ON COLUMN "ar_interval"."opening_balance" IS 'Prior period''s closing; the first period starts from the charge or an opening-balance row.';
COMMENT ON COLUMN "ar_interval"."charges" IS 'Charges posted in the period.';
COMMENT ON COLUMN "ar_interval"."payments" IS 'Payments in the period.';
COMMENT ON COLUMN "ar_interval"."adjustments" IS 'Adjustments in the period.';
COMMENT ON COLUMN "ar_interval"."write_offs" IS 'Write-offs in the period.';
COMMENT ON COLUMN "ar_interval"."refunds" IS 'Refunds in the period.';
COMMENT ON COLUMN "ar_interval"."closing_balance" IS 'Opening plus movements.';
COMMENT ON COLUMN "ar_interval"."payer_balance" IS 'Closing owed by the payer.';
COMMENT ON COLUMN "ar_interval"."patient_balance" IS 'Closing owed by the patient.';
COMMENT ON COLUMN "ar_interval"."payer_bucket" IS 'Same buckets as ar_snapshot.aging_bucket: 0-30, 31-60, 61-90, 91-120, 121+.';
COMMENT ON COLUMN "ar_interval"."patient_bucket" IS 'Same buckets as ar_snapshot.aging_bucket: 0-30, 31-60, 61-90, 91-120, 121+.';
COMMENT ON COLUMN "ar_interval"."aging_basis" IS 'What the aging clock started from, so the definition never changes silently.';
COMMENT ON COLUMN "ar_interval"."reconciles" IS '1 when closing equals the ledger sum.';
COMMENT ON COLUMN "ar_interval"."prior_period_ar_interval_id" IS 'Links the roll-forward chain.';
COMMENT ON COLUMN "ar_interval"."payer_days" IS 'Days the payer balance has aged.';
COMMENT ON COLUMN "ar_interval"."patient_days" IS 'Days the patient balance has aged; the clock restarts at transfer.';
COMMENT ON COLUMN "ar_interval"."payer_aging_date" IS 'Payer clock start.';
COMMENT ON COLUMN "ar_interval"."patient_aging_date" IS 'Patient clock start.';
COMMENT ON COLUMN "ar_interval"."unbilled_balance" IS 'Charges not yet on a claim.';
COMMENT ON COLUMN "ar_interval"."payments_payer" IS 'Movement split.';
COMMENT ON COLUMN "ar_interval"."payments_patient" IS 'Movement split.';
COMMENT ON COLUMN "ar_interval"."adjustments_contractual" IS 'Movement split.';
COMMENT ON COLUMN "ar_interval"."adjustments_denial" IS 'Movement split.';
COMMENT ON COLUMN "ar_interval"."adjustments_other" IS 'Movement split.';
COMMENT ON COLUMN "ar_interval"."transfers_to_patient" IS 'Moved from payer to patient.';
COMMENT ON COLUMN "ar_interval"."transfers_to_secondary" IS 'Moved to a secondary payer.';
COMMENT ON COLUMN "ar_interval"."claim_id" IS 'Current claim.';
COMMENT ON COLUMN "ar_interval"."claim_line_id" IS 'Current claim line.';
COMMENT ON COLUMN "ar_interval"."claim_status" IS 'Status at period end.';
COMMENT ON COLUMN "ar_interval"."payer_id" IS 'Payer responsible at period end.';
COMMENT ON COLUMN "ar_interval"."open_denied_amount" IS 'Denial-related AR.';
COMMENT ON COLUMN "ar_interval"."is_in_denial" IS 'An open denial exists.';
COMMENT ON COLUMN "ar_interval"."expected_collectible" IS 'Net AR: contract expected minus paid.';
COMMENT ON COLUMN "ar_interval"."last_payment_date" IS 'Stalled accounts.';
COMMENT ON COLUMN "ar_interval"."last_activity_date" IS 'Stalled accounts.';
COMMENT ON COLUMN "ar_interval"."last_statement_date" IS 'Statement timing.';
COMMENT ON COLUMN "ar_interval"."is_credit" IS 'Closing below zero: refund candidates.';
COMMENT ON COLUMN "ar_interval"."ledger_balance" IS 'Ledger sum to period end (visible check).';
COMMENT ON COLUMN "ar_interval"."variance_amount" IS 'Closing minus ledger.';
COMMENT ON COLUMN "ar_interval"."is_restated" IS 'Rebuilt after a backdated posting.';
COMMENT ON COLUMN "ar_interval"."period_status" IS 'Open or closed.';
COMMENT ON COLUMN "ar_interval"."provider_id" IS 'Copied.';
COMMENT ON COLUMN "ar_interval"."specialty_id" IS 'Copied.';
COMMENT ON COLUMN "ar_interval"."cpt_code_id" IS 'Copied.';
COMMENT ON COLUMN "ar_interval"."facility_id" IS 'Copied.';
COMMENT ON COLUMN "ar_interval"."service_date" IS 'Copied.';
COMMENT ON COLUMN "ar_interval"."collections_agency_flag" IS '1 while the balance is placed with an agency (rebuilt from collection_placement).';
COMMENT ON COLUMN "ar_interval"."statement_count" IS 'Statements sent.';
COMMENT ON COLUMN "ar_interval"."version" IS '1 for the first row; higher for each change.';
COMMENT ON COLUMN "ar_interval"."is_current" IS '1 on the latest version. Counts use current rows only.';
COMMENT ON COLUMN "ar_interval"."previous_ar_interval_id" IS 'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.';
COMMENT ON COLUMN "ar_interval"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "ar_interval"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "ar_interval"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "ar_interval"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "ar_interval"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "ar_interval"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "ar_interval"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "ar_interval"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "ar_interval"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "ar_interval"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "ar_snapshot" IS 'One row per open balance, per owner (payer, patient, unbilled), per as-of date.';
COMMENT ON COLUMN "ar_snapshot"."ar_snapshot_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "ar_snapshot"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "ar_snapshot"."as_of_date" IS 'The snapshot date.';
COMMENT ON COLUMN "ar_snapshot"."snapshot_type" IS 'Daily, weekly, month_end.';
COMMENT ON COLUMN "ar_snapshot"."bill_id" IS 'The account''s visit.';
COMMENT ON COLUMN "ar_snapshot"."balance_owner" IS 'Payer, patient or unbilled.';
COMMENT ON COLUMN "ar_snapshot"."balance" IS 'Open amount for that owner.';
COMMENT ON COLUMN "ar_snapshot"."practice_id" IS 'Reports by practice.';
COMMENT ON COLUMN "ar_snapshot"."patient_id" IS 'Patient accounts.';
COMMENT ON COLUMN "ar_snapshot"."guarantor_id" IS 'The guarantor account responsible for the patient balance.';
COMMENT ON COLUMN "ar_snapshot"."aging_date" IS 'When this row''s clock started.';
COMMENT ON COLUMN "ar_snapshot"."days_outstanding" IS 'Age of the balance.';
COMMENT ON COLUMN "ar_snapshot"."aging_bucket" IS '0-30, 31-60, 61-90, 91-120 or 121+ days from aging_date.';
COMMENT ON COLUMN "ar_snapshot"."aging_basis" IS 'What the clock started from.';
COMMENT ON COLUMN "ar_snapshot"."claim_id" IS 'The claim on payer rows; blank for unbilled and self-pay.';
COMMENT ON COLUMN "ar_snapshot"."payer_id" IS 'Who owes, or the expected payer on unbilled rows.';
COMMENT ON COLUMN "ar_snapshot"."claim_status" IS 'Where the claim stands.';
COMMENT ON COLUMN "ar_snapshot"."claim_sequence" IS 'Primary or secondary.';
COMMENT ON COLUMN "ar_snapshot"."submitted_date" IS 'Date sent.';
COMMENT ON COLUMN "ar_snapshot"."expected_collectible" IS 'Net AR.';
COMMENT ON COLUMN "ar_snapshot"."last_payment_date" IS 'Stalled accounts.';
COMMENT ON COLUMN "ar_snapshot"."last_activity_date" IS 'Stalled accounts.';
COMMENT ON COLUMN "ar_snapshot"."days_since_activity" IS 'Follow-up queue.';
COMMENT ON COLUMN "ar_snapshot"."last_statement_date" IS 'Patient statement timing.';
COMMENT ON COLUMN "ar_snapshot"."open_denied_amount" IS 'Denial-related AR.';
COMMENT ON COLUMN "ar_snapshot"."is_in_denial" IS 'Open denial exists.';
COMMENT ON COLUMN "ar_snapshot"."is_credit" IS 'Balance below zero.';
COMMENT ON COLUMN "ar_snapshot"."overpayment_identified_date" IS 'When a credit balance was identified as an overpayment. Starts the 60-day refund clock for Medicare and Medicaid.';
COMMENT ON COLUMN "ar_snapshot"."refund_due_date" IS 'Refund deadline: identified date + 60 days for government payers, contract or state rule for others.';
COMMENT ON COLUMN "ar_snapshot"."filing_deadline" IS 'Service date plus the payer''s filing limit.';
COMMENT ON COLUMN "ar_snapshot"."provider_id" IS 'Copied.';
COMMENT ON COLUMN "ar_snapshot"."specialty_id" IS 'Copied.';
COMMENT ON COLUMN "ar_snapshot"."facility_id" IS 'Copied.';
COMMENT ON COLUMN "ar_snapshot"."service_date" IS 'Copied.';
COMMENT ON COLUMN "ar_snapshot"."primary_cpt_code_id" IS 'Procedure view.';
COMMENT ON COLUMN "ar_snapshot"."change_since_last_snapshot" IS 'Trend.';
COMMENT ON COLUMN "ar_snapshot"."collections_agency_flag" IS '1 while the balance is placed with an agency (rebuilt from collection_placement).';
COMMENT ON COLUMN "ar_snapshot"."next_action_date" IS 'Worklists.';
COMMENT ON COLUMN "ar_snapshot"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "ar_snapshot"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "ar_snapshot"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "ar_snapshot"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "ar_snapshot"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "ar_snapshot"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "ar_snapshot"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "ar_snapshot"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "ar_snapshot"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "ar_snapshot"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "appeal" IS 'One appeal filed (or being prepared) against one denial at one level: first appeal, second appeal or external review. A status change is a new version.';
COMMENT ON COLUMN "appeal"."appeal_id" IS 'Stable ID of the record: the same on every version. The primary key is (appeal_id, version). Every link from another table uses appeal_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.';
COMMENT ON COLUMN "appeal"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "appeal"."appeal_number" IS 'The practice''s own appeal tracking number, if it has one. Restricted.';
COMMENT ON COLUMN "appeal"."denial_id" IS 'The denial being appealed. Every appeal belongs to one denial.';
COMMENT ON COLUMN "appeal"."appeal_level" IS 'First, second or external_review.';
COMMENT ON COLUMN "appeal"."appeal_status" IS 'Drafted, approved, sent, answered, closed.';
COMMENT ON COLUMN "appeal"."clock_start_date" IS 'Date the payer told the practice about the denial (or the decision on the earlier round). The appeal clock starts here.';
COMMENT ON COLUMN "appeal"."deadline_date" IS 'Last day to file this appeal, from the payer rule or contract.';
COMMENT ON COLUMN "appeal"."claim_id" IS 'Claim behind the denial, for quick reports.';
COMMENT ON COLUMN "appeal"."submitted_date" IS 'Date the appeal went out. Blank while still a draft.';
COMMENT ON COLUMN "appeal"."submission_channel" IS 'Portal, fax, mail, 275 or FHIR.';
COMMENT ON COLUMN "appeal"."amount_disputed" IS 'Dollars actually disputed in this round. Can be less than the denied amount.';
COMMENT ON COLUMN "appeal"."evidence_count" IS 'How many documents were attached (note, authorization, EOB, policy). A count only, never the documents.';
COMMENT ON COLUMN "appeal"."letter_hash" IS 'Fingerprint of the final letter after human edits. Proves which letter went out without storing it.';
COMMENT ON COLUMN "appeal"."payer_reference" IS 'The payer''s case or reference number for the appeal. Restricted.';
COMMENT ON COLUMN "appeal"."decision_date" IS 'Date the payer answered.';
COMMENT ON COLUMN "appeal"."payer_decision" IS 'Overturned, partly_overturned, upheld or no_answer.';
COMMENT ON COLUMN "appeal"."is_overturned" IS '1 if the denial was overturned in this round (fully or partly). Yes/no outcome used in overturn rate.';
COMMENT ON COLUMN "appeal"."recovered_amount" IS 'Dollars recovered from this round, from the ledger.';
COMMENT ON COLUMN "appeal"."agent_decision_id" IS 'The agent decision that drafted the appeal.';
COMMENT ON COLUMN "appeal"."agent_approval_id" IS 'The human review that approved the appeal or the write-off instead.';
COMMENT ON COLUMN "appeal"."practice_id" IS 'Copied, so reports by practice never join up.';
COMMENT ON COLUMN "appeal"."patient_id" IS 'Copied from the denial.';
COMMENT ON COLUMN "appeal"."payer_id" IS 'Copied, so win rates by payer need no join.';
COMMENT ON COLUMN "appeal"."version" IS '1 for the first row; higher for each change.';
COMMENT ON COLUMN "appeal"."is_current" IS '1 on the latest version. Counts use current rows only.';
COMMENT ON COLUMN "appeal"."previous_appeal_id" IS 'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.';
COMMENT ON COLUMN "appeal"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "appeal"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "appeal"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "appeal"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "appeal"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "appeal"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "appeal"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "appeal"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "appeal"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "appeal"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "patient_statement" IS 'One statement or patient balance notice sent (or tried) to one patient: date, amount shown, channel, dunning level and delivery status. A status change is a new version.';
COMMENT ON COLUMN "patient_statement"."patient_statement_id" IS 'Stable ID of the record: the same on every version. The primary key is (patient_statement_id, version). Every link from another table uses patient_statement_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.';
COMMENT ON COLUMN "patient_statement"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "patient_statement"."statement_number" IS 'The number printed on the statement, if the practice has one. Restricted.';
COMMENT ON COLUMN "patient_statement"."patient_id" IS 'The patient who got the statement.';
COMMENT ON COLUMN "patient_statement"."guarantor_id" IS 'The guarantor account responsible for the patient balance.';
COMMENT ON COLUMN "patient_statement"."statement_date" IS 'Date printed on the statement.';
COMMENT ON COLUMN "patient_statement"."statement_amount" IS 'Balance shown on the statement.';
COMMENT ON COLUMN "patient_statement"."channel" IS 'Mail, portal, sms, phone or none.';
COMMENT ON COLUMN "patient_statement"."statement_status" IS 'Sent, delivered, bounced, returned, disputed, plan or hardship.';
COMMENT ON COLUMN "patient_statement"."practice_id" IS 'Copied, for reports by practice.';
COMMENT ON COLUMN "patient_statement"."bill_id" IS 'The bill the balance mostly belongs to. Blank for an account-level statement.';
COMMENT ON COLUMN "patient_statement"."claim_id" IS 'Claim the statement refers to, when the feed gives one.';
COMMENT ON COLUMN "patient_statement"."due_date" IS 'Payment due date printed.';
COMMENT ON COLUMN "patient_statement"."sent_at" IS 'When the message actually went out (channel and send time).';
COMMENT ON COLUMN "patient_statement"."status_date" IS 'Date of the latest status (delivered, returned, disputed).';
COMMENT ON COLUMN "patient_statement"."dunning_level" IS '0 first statement, then 1, 2, 3 for each firmer reminder.';
COMMENT ON COLUMN "patient_statement"."validation_notice_date" IS 'Date of the Reg F validation notice, if this statement carried one. Only when the balance is placed with a third-party collector (collection_placement.is_third_party = 1).';
COMMENT ON COLUMN "patient_statement"."dispute_window_end_date" IS 'Last day the patient may dispute the debt (Reg F). Only when the balance is placed with a third-party collector (collection_placement.is_third_party = 1).';
COMMENT ON COLUMN "patient_statement"."collection_placement_id" IS 'Placement the notice belongs to.';
COMMENT ON COLUMN "patient_statement"."payment_plan_id" IS 'The payment plan the patient is on, if any.';
COMMENT ON COLUMN "patient_statement"."version" IS '1 for the first row; higher for each change.';
COMMENT ON COLUMN "patient_statement"."is_current" IS '1 on the latest version. Counts use current rows only.';
COMMENT ON COLUMN "patient_statement"."previous_patient_statement_id" IS 'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.';
COMMENT ON COLUMN "patient_statement"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "patient_statement"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "patient_statement"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "patient_statement"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "patient_statement"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "patient_statement"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "patient_statement"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "patient_statement"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "patient_statement"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "patient_statement"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "payment_adjustment" IS 'One provider-level adjustment on a payment that is not tied to a claim: a takeback, interest, recoupment or penalty (the 835 PLB segment).';
COMMENT ON COLUMN "payment_adjustment"."payment_adjustment_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "payment_adjustment"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "payment_adjustment"."payment_id" IS 'The payment (EFT or check) the adjustment came in.';
COMMENT ON COLUMN "payment_adjustment"."adjustment_type" IS 'Takeback, recoupment, interest, penalty, bonus or other.';
COMMENT ON COLUMN "payment_adjustment"."amount" IS 'Signed amount: negative takes money away from the deposit.';
COMMENT ON COLUMN "payment_adjustment"."adjustment_date" IS 'Date of the adjustment (payment date if the source gives none).';
COMMENT ON COLUMN "payment_adjustment"."plb_reason_code" IS 'The 835 PLB reason code (for example WO for overpayment recovery, L6 for interest).';
COMMENT ON COLUMN "payment_adjustment"."practice_id" IS 'Copied from the payment.';
COMMENT ON COLUMN "payment_adjustment"."payer_id" IS 'Copied from the payment, for takebacks by payer.';
COMMENT ON COLUMN "payment_adjustment"."payee_provider_id" IS 'Provider the adjustment applies to, when the payer names one.';
COMMENT ON COLUMN "payment_adjustment"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "payment_adjustment"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "payment_adjustment"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "payment_adjustment"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "payment_adjustment"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "payment_adjustment"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "payment_adjustment"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "payment_adjustment"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "payment_adjustment"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "payment_adjustment"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "remittance_claim" IS 'One claim as the payer adjudicated it on one remittance (835 CLP loop).';
COMMENT ON COLUMN "remittance_claim"."remittance_claim_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "remittance_claim"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "remittance_claim"."payment_id" IS 'The payment (ERA) it came on.';
COMMENT ON COLUMN "remittance_claim"."claim_id" IS 'The matched claim. Blank until matched.';
COMMENT ON COLUMN "remittance_claim"."patient_control_number" IS 'CLP01: our claim number as the payer echoes it. Restricted.';
COMMENT ON COLUMN "remittance_claim"."claim_status_code" IS 'CLP02: 1, 2, 3 processed as primary/secondary/tertiary, 4 denied, 19-23 forwarded or reversal (22).';
COMMENT ON COLUMN "remittance_claim"."is_reversal" IS '1 when CLP02 = 22.';
COMMENT ON COLUMN "remittance_claim"."charge_amount" IS 'CLP03.';
COMMENT ON COLUMN "remittance_claim"."paid_amount" IS 'CLP04.';
COMMENT ON COLUMN "remittance_claim"."patient_responsibility" IS 'CLP05.';
COMMENT ON COLUMN "remittance_claim"."claim_filing_indicator" IS 'CLP06.';
COMMENT ON COLUMN "remittance_claim"."payer_claim_number" IS 'CLP07. Restricted.';
COMMENT ON COLUMN "remittance_claim"."claim_level_adjustment" IS 'Sum of claim-level CAS amounts.';
COMMENT ON COLUMN "remittance_claim"."remark_code_id" IS 'First MIA/MOA remark.';
COMMENT ON COLUMN "remittance_claim"."is_crossover" IS '1 when the payer forwarded the claim (NM1*TT).';
COMMENT ON COLUMN "remittance_claim"."crossover_payer_id" IS 'Payer it was forwarded to.';
COMMENT ON COLUMN "remittance_claim"."match_method" IS 'claim_number, payer_claim_number or fuzzy.';
COMMENT ON COLUMN "remittance_claim"."payer_id" IS 'Copied, so reports skip the join.';
COMMENT ON COLUMN "remittance_claim"."practice_id" IS 'Copied, so reports skip the join.';
COMMENT ON COLUMN "remittance_claim"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "remittance_claim"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "remittance_claim"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "remittance_claim"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "remittance_claim"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "remittance_claim"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "remittance_claim"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "remittance_claim"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "remittance_claim"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "remittance_claim"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "bank_deposit" IS 'One deposit into the practice bank account: EFT, check batch, lockbox or card settlement.';
COMMENT ON COLUMN "bank_deposit"."bank_deposit_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "bank_deposit"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "bank_deposit"."practice_id" IS 'Account owner.';
COMMENT ON COLUMN "bank_deposit"."deposit_date" IS 'Bank date.';
COMMENT ON COLUMN "bank_deposit"."deposit_amount" IS 'Amount deposited.';
COMMENT ON COLUMN "bank_deposit"."deposit_method" IS 'eft, check, lockbox, card_settlement.';
COMMENT ON COLUMN "bank_deposit"."trace_number" IS 'ACH trace / TRN02 used to match the ERA. Restricted.';
COMMENT ON COLUMN "bank_deposit"."payer_id" IS 'Payer, when known.';
COMMENT ON COLUMN "bank_deposit"."payment_id" IS 'The matched ERA payment.';
COMMENT ON COLUMN "bank_deposit"."match_status" IS 'matched, unmatched, partial, multiple.';
COMMENT ON COLUMN "bank_deposit"."matched_date" IS 'When matched.';
COMMENT ON COLUMN "bank_deposit"."variance_amount" IS 'Deposit minus matched payments.';
COMMENT ON COLUMN "bank_deposit"."bank_account_label" IS 'Label of the account. Never the account number.';
COMMENT ON COLUMN "bank_deposit"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "bank_deposit"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "bank_deposit"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "bank_deposit"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "bank_deposit"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "bank_deposit"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "bank_deposit"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "bank_deposit"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "bank_deposit"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "bank_deposit"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "collection_placement" IS 'One placement of a guarantor balance with a collection agency, through recall or close.';
COMMENT ON COLUMN "collection_placement"."collection_placement_id" IS 'Stable ID of the record: the same on every version. The primary key is (collection_placement_id, version). Every link from another table uses collection_placement_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.';
COMMENT ON COLUMN "collection_placement"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "collection_placement"."placement_number" IS 'Agency account number. Restricted.';
COMMENT ON COLUMN "collection_placement"."guarantor_id" IS 'The guarantor account placed.';
COMMENT ON COLUMN "collection_placement"."patient_id" IS 'When placement is per patient.';
COMMENT ON COLUMN "collection_placement"."agency_code" IS 'The collection agency.';
COMMENT ON COLUMN "collection_placement"."placement_type" IS 'early_out (first-party, our name), bad_debt (third-party).';
COMMENT ON COLUMN "collection_placement"."is_third_party" IS '1 when the agency collects in its own name; switches on Reg F fields on statements.';
COMMENT ON COLUMN "collection_placement"."placed_date" IS 'Date placed.';
COMMENT ON COLUMN "collection_placement"."placed_amount" IS 'Balance placed.';
COMMENT ON COLUMN "collection_placement"."recovered_amount" IS 'Collected by the agency so far.';
COMMENT ON COLUMN "collection_placement"."agency_fee_amount" IS 'Fee kept by the agency.';
COMMENT ON COLUMN "collection_placement"."placement_status" IS 'placed, paying, recalled, closed_paid, closed_uncollectible, disputed.';
COMMENT ON COLUMN "collection_placement"."recall_date" IS 'When pulled back.';
COMMENT ON COLUMN "collection_placement"."recall_reason" IS 'insurance_found, dispute, charity, error, paid.';
COMMENT ON COLUMN "collection_placement"."closed_date" IS 'When closed.';
COMMENT ON COLUMN "collection_placement"."credit_reported" IS '1 if reported to a credit bureau (medical-debt reporting rules).';
COMMENT ON COLUMN "collection_placement"."practice_id" IS 'Copied, so reports skip the join.';
COMMENT ON COLUMN "collection_placement"."version" IS '1 for the first row; higher for each change.';
COMMENT ON COLUMN "collection_placement"."is_current" IS '1 on the latest version. Counts use current rows only.';
COMMENT ON COLUMN "collection_placement"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "collection_placement"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "collection_placement"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "collection_placement"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "collection_placement"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "collection_placement"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "collection_placement"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "collection_placement"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "collection_placement"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "collection_placement"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "agent_decision" IS 'One row per decision an agent reached about one entity (claim, appointment, authorization and so on).';
COMMENT ON COLUMN "agent_decision"."agent_decision_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "agent_decision"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "agent_decision"."agent_run_id" IS 'The run that made it.';
COMMENT ON COLUMN "agent_decision"."agent_code" IS 'Copied from the run.';
COMMENT ON COLUMN "agent_decision"."decision_type" IS 'Eligibility_ok, needs_auth, hold_claim, appeal, code_change, write_off_review and so on.';
COMMENT ON COLUMN "agent_decision"."entity_type" IS 'Which table the decision is about. Must agree with the typed link of the same entity (CHECK).';
COMMENT ON COLUMN "agent_decision"."entity_id" IS 'Internal ID in that table.';
COMMENT ON COLUMN "agent_decision"."outcome" IS 'Proceed, hold, flag, propose_change, no_action, needs_human.';
COMMENT ON COLUMN "agent_decision"."decided_at" IS 'When decided.';
COMMENT ON COLUMN "agent_decision"."run_mode" IS 'Copied: shadow decisions are never acted on.';
COMMENT ON COLUMN "agent_decision"."confidence" IS '0 to 1. Blank when the agent is rule-based only.';
COMMENT ON COLUMN "agent_decision"."reason_summary" IS 'Short plain reason; never patient text. Scanned for identifiers at write time; a value that fails is refused.';
COMMENT ON COLUMN "agent_decision"."rules_checked" IS 'Rules evaluated (the details hold each one).';
COMMENT ON COLUMN "agent_decision"."rules_failed" IS 'Rules that failed.';
COMMENT ON COLUMN "agent_decision"."amount_at_stake" IS 'Dollars the decision protects or affects.';
COMMENT ON COLUMN "agent_decision"."data_fallback_level" IS 'Lowest fallback step of any input used: tells readers how reliable it was.';
COMMENT ON COLUMN "agent_decision"."human_outcome" IS 'Accepted, changed, rejected, ignored: agreement with staff.';
COMMENT ON COLUMN "agent_decision"."human_outcome_date" IS 'When staff answered.';
COMMENT ON COLUMN "agent_decision"."supersedes_decision_id" IS 'A newer decision replaces an older one; the old row stays.';
COMMENT ON COLUMN "agent_decision"."is_current" IS '1 on the latest decision for the entity and type.';
COMMENT ON COLUMN "agent_decision"."input_hash" IS 'Hash of the inputs, so a replay can prove it saw the same data.';
COMMENT ON COLUMN "agent_decision"."practice_id" IS 'Reports by practice.';
COMMENT ON COLUMN "agent_decision"."patient_id" IS 'Patient level view.';
COMMENT ON COLUMN "agent_decision"."payer_id" IS 'Reports by payer.';
COMMENT ON COLUMN "agent_decision"."provider_id" IS 'Reports by provider.';
COMMENT ON COLUMN "agent_decision"."specialty_id" IS 'Reports by specialty.';
COMMENT ON COLUMN "agent_decision"."appointment_id" IS 'The appointment concerned, when there is one.';
COMMENT ON COLUMN "agent_decision"."encounter_id" IS 'The visit concerned.';
COMMENT ON COLUMN "agent_decision"."bill_id" IS 'The bill concerned.';
COMMENT ON COLUMN "agent_decision"."claim_id" IS 'The claim concerned.';
COMMENT ON COLUMN "agent_decision"."denial_id" IS 'The denial concerned.';
COMMENT ON COLUMN "agent_decision"."authorization_id" IS 'The authorization concerned.';
COMMENT ON COLUMN "agent_decision"."recheck_condition" IS 'What must be true for this decision to count as closed (for example task done and the rules pass again).';
COMMENT ON COLUMN "agent_decision"."recheck_result" IS 'Result of the re-check: passed, failed or pending.';
COMMENT ON COLUMN "agent_decision"."prompt_hash" IS 'Hash of the prompt sent to the model for this decision. Blank when no model was used.';
COMMENT ON COLUMN "agent_decision"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "agent_decision"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "agent_value" IS 'One row per dollar event an agent can claim: dollars detected, worked, submitted, accepted, recovered or avoided on one entity.';
COMMENT ON COLUMN "agent_value"."agent_value_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "agent_value"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "agent_value"."agent_code" IS 'Which agent gets the credit, A1 to A15.';
COMMENT ON COLUMN "agent_value"."value_stage" IS 'Detected, worked, submitted, accepted, recovered, avoided. Lets one finding be followed from found to paid.';
COMMENT ON COLUMN "agent_value"."amount" IS 'Dollars at this stage. Never negative; a payer takeback is a new row with value_kind = reversal.';
COMMENT ON COLUMN "agent_value"."signed_amount" IS 'amount with a sign: negative on value_kind = reversal. Reports sum this, never amount.';
COMMENT ON COLUMN "agent_value"."value_date" IS 'Date of the event: detection date for detected, payment date for recovered.';
COMMENT ON COLUMN "agent_value"."entity_type" IS 'Table the dollars belong to (claim, denial, claim_line and so on). Must agree with the typed link of the same entity (CHECK).';
COMMENT ON COLUMN "agent_value"."entity_id" IS 'Internal ID in that table.';
COMMENT ON COLUMN "agent_value"."agent_finding_id" IS 'The finding behind it. Follow the chain from detected to recovered.';
COMMENT ON COLUMN "agent_value"."agent_decision_id" IS 'The decision that produced it.';
COMMENT ON COLUMN "agent_value"."practice_id" IS 'Reports by practice.';
COMMENT ON COLUMN "agent_value"."claim_id" IS 'The claim concerned.';
COMMENT ON COLUMN "agent_value"."denial_id" IS 'The denial concerned (appeal and overturn value).';
COMMENT ON COLUMN "agent_value"."payer_id" IS 'Value by payer, and the payer slice of a leak.';
COMMENT ON COLUMN "agent_value"."provider_id" IS 'Value by rendering provider.';
COMMENT ON COLUMN "agent_value"."specialty_id" IS 'Value by specialty.';
COMMENT ON COLUMN "agent_value"."cpt_code_id" IS 'Value by procedure; blank for a payer total.';
COMMENT ON COLUMN "agent_value"."ledger_entry_id" IS 'Proof: the 835 payment row that confirms recovered dollars. One payment is counted once.';
COMMENT ON COLUMN "agent_value"."is_holdout" IS '1 for a control group claim held back for measurement; the base of incremental value.';
COMMENT ON COLUMN "agent_value"."incremental_amount" IS 'Dollars above what would have happened anyway, measured against holdout rows.';
COMMENT ON COLUMN "agent_value"."value_kind" IS 'Short type: underpayment, denial_overturn, rejection_fix, missed_charge, avoided_denial and so on.';
COMMENT ON COLUMN "agent_value"."is_estimate" IS '1 when no payment proves the amount (ladder step 2 or 3).';
COMMENT ON COLUMN "agent_value"."attribution_share" IS 'Share of the dollars credited to this agent when several agents helped; 0 to 1.';
COMMENT ON COLUMN "agent_value"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "agent_value"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "agent_run" IS 'One row per execution of one agent: what started it, how it ended and what it cost.';
COMMENT ON COLUMN "agent_run"."agent_run_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "agent_run"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "agent_run"."agent_code" IS 'Which agent, A1 to A15.';
COMMENT ON COLUMN "agent_run"."agent_name" IS 'Display name.';
COMMENT ON COLUMN "agent_run"."run_mode" IS 'Shadow (proposals only), assisted or live.';
COMMENT ON COLUMN "agent_run"."trigger_type" IS 'Schedule, event, manual, retry.';
COMMENT ON COLUMN "agent_run"."started_at" IS 'Start time.';
COMMENT ON COLUMN "agent_run"."ended_at" IS 'End time.';
COMMENT ON COLUMN "agent_run"."run_status" IS 'Running, succeeded, partial, failed, cancelled.';
COMMENT ON COLUMN "agent_run"."practice_id" IS 'Blank for a run across practices.';
COMMENT ON COLUMN "agent_run"."items_in" IS 'Entities the run looked at.';
COMMENT ON COLUMN "agent_run"."decisions_made" IS 'Decisions written.';
COMMENT ON COLUMN "agent_run"."error_count" IS 'Entities that failed.';
COMMENT ON COLUMN "agent_run"."error_summary" IS 'Short error class, never raw data.';
COMMENT ON COLUMN "agent_run"."model_name" IS 'Model used, if any.';
COMMENT ON COLUMN "agent_run"."input_tokens" IS 'For cost.';
COMMENT ON COLUMN "agent_run"."output_tokens" IS 'For cost.';
COMMENT ON COLUMN "agent_run"."cost_amount" IS 'Cost of the run, in dollars.';
COMMENT ON COLUMN "agent_run"."trigger_run_id" IS 'The run that started this one.';
COMMENT ON COLUMN "agent_run"."code_version" IS 'Agent version, for replay.';
COMMENT ON COLUMN "agent_run"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "agent_run"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "agent_decision_check" IS 'One row per rule or check evaluated inside a decision.';
COMMENT ON COLUMN "agent_decision_check"."agent_decision_check_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "agent_decision_check"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "agent_decision_check"."agent_decision_id" IS 'The decision it explains.';
COMMENT ON COLUMN "agent_decision_check"."check_seq" IS 'Order within the decision.';
COMMENT ON COLUMN "agent_decision_check"."rule_code" IS 'Rule or check evaluated.';
COMMENT ON COLUMN "agent_decision_check"."check_result" IS 'Pass, fail, warn, skipped, unknown.';
COMMENT ON COLUMN "agent_decision_check"."agent_code" IS 'Copied.';
COMMENT ON COLUMN "agent_decision_check"."rule_version" IS 'Version of the rule at the time.';
COMMENT ON COLUMN "agent_decision_check"."rule_source" IS 'Payer policy, public rule, client rule, learned.';
COMMENT ON COLUMN "agent_decision_check"."severity" IS 'Block, review, info.';
COMMENT ON COLUMN "agent_decision_check"."observed_value" IS 'What was seen, as short text. Never a name, date of birth or raw member number. Scanned for identifiers at write time; a value that fails is refused.';
COMMENT ON COLUMN "agent_decision_check"."expected_value" IS 'What the rule wanted. Scanned for identifiers at write time; a value that fails is refused.';
COMMENT ON COLUMN "agent_decision_check"."input_table" IS 'Canonical table the input came from.';
COMMENT ON COLUMN "agent_decision_check"."input_fallback_level" IS 'Fallback step of that input (matches data_feed).';
COMMENT ON COLUMN "agent_decision_check"."practice_id" IS 'Copied.';
COMMENT ON COLUMN "agent_decision_check"."payer_id" IS 'Copied.';
COMMENT ON COLUMN "agent_decision_check"."cpt_code_id" IS 'Copied when relevant.';
COMMENT ON COLUMN "agent_decision_check"."evidence_ref" IS 'Pointer to evidence, never its content.';
COMMENT ON COLUMN "agent_decision_check"."payer_rule_id" IS 'The exact version of the payer rule this check ran against.';
COMMENT ON COLUMN "agent_decision_check"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "agent_decision_check"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "agent_finding" IS 'One issue an agent found: a missed charge, underpayment, preventable denial, coding gap, document gap and so on.';
COMMENT ON COLUMN "agent_finding"."agent_finding_id" IS 'Stable ID of the record: the same on every version. The primary key is (agent_finding_id, version). Every link from another table uses agent_finding_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.';
COMMENT ON COLUMN "agent_finding"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "agent_finding"."agent_run_id" IS 'The run that found it.';
COMMENT ON COLUMN "agent_finding"."agent_code" IS 'Which agent.';
COMMENT ON COLUMN "agent_finding"."finding_type" IS 'Missed_charge, underpayment, preventable_denial, coding_gap, documentation_gap, eligibility_gap, auth_gap, timely_filing_risk and so on.';
COMMENT ON COLUMN "agent_finding"."entity_type" IS 'Table the issue is about. Must agree with the typed link of the same entity (CHECK).';
COMMENT ON COLUMN "agent_finding"."entity_id" IS 'Internal ID in that table.';
COMMENT ON COLUMN "agent_finding"."found_date" IS 'When found.';
COMMENT ON COLUMN "agent_finding"."finding_status" IS 'Open, accepted, fixed, dismissed, expired.';
COMMENT ON COLUMN "agent_finding"."amount_at_risk" IS 'Dollars at risk if left.';
COMMENT ON COLUMN "agent_finding"."amount_recovered" IS 'Dollars recovered or avoided, from the ledger.';
COMMENT ON COLUMN "agent_finding"."upstream_stage" IS 'Journey stage that could have caught it.';
COMMENT ON COLUMN "agent_finding"."is_preventable" IS 'Could have been caught earlier.';
COMMENT ON COLUMN "agent_finding"."severity" IS 'High, medium, low.';
COMMENT ON COLUMN "agent_finding"."deadline_date" IS 'Filing or appeal limit.';
COMMENT ON COLUMN "agent_finding"."resolved_date" IS 'Time to fix.';
COMMENT ON COLUMN "agent_finding"."resolution" IS 'Fixed, written_off, not_an_issue, expired.';
COMMENT ON COLUMN "agent_finding"."agent_decision_id" IS 'The decision that raised it.';
COMMENT ON COLUMN "agent_finding"."finding_hash" IS 'Same issue seen again maps to the same hash: no duplicates.';
COMMENT ON COLUMN "agent_finding"."summary" IS 'Short plain description; no patient text. Scanned for identifiers at write time; a value that fails is refused.';
COMMENT ON COLUMN "agent_finding"."practice_id" IS 'Reports by practice.';
COMMENT ON COLUMN "agent_finding"."patient_id" IS 'Patient level view.';
COMMENT ON COLUMN "agent_finding"."payer_id" IS 'Reports by payer.';
COMMENT ON COLUMN "agent_finding"."provider_id" IS 'Reports by provider.';
COMMENT ON COLUMN "agent_finding"."specialty_id" IS 'Reports by specialty.';
COMMENT ON COLUMN "agent_finding"."appointment_id" IS 'The appointment concerned, when there is one.';
COMMENT ON COLUMN "agent_finding"."encounter_id" IS 'The visit concerned.';
COMMENT ON COLUMN "agent_finding"."bill_id" IS 'The bill concerned.';
COMMENT ON COLUMN "agent_finding"."claim_id" IS 'The claim concerned.';
COMMENT ON COLUMN "agent_finding"."denial_id" IS 'The denial concerned.';
COMMENT ON COLUMN "agent_finding"."authorization_id" IS 'The authorization concerned.';
COMMENT ON COLUMN "agent_finding"."suggested_value" IS 'What the agent suggests (for example a visit code and diagnoses).';
COMMENT ON COLUMN "agent_finding"."final_value" IS 'What the person finally approved.';
COMMENT ON COLUMN "agent_finding"."value_difference" IS 'Dollar difference at the contract rate between what was billed and what is suggested.';
COMMENT ON COLUMN "agent_finding"."is_compliance_risk" IS '1 when the finding is an over-coding risk; 0 when it is an opportunity.';
COMMENT ON COLUMN "agent_finding"."predicted_probability" IS 'Predicted chance that the claim is denied.';
COMMENT ON COLUMN "agent_finding"."predicted_reason_category" IS 'Most likely denial reason group.';
COMMENT ON COLUMN "agent_finding"."predicted_allowed_amount" IS 'Allowed amount the twin expects.';
COMMENT ON COLUMN "agent_finding"."predicted_patient_responsibility" IS 'Copay, coinsurance and deductible the twin expects the patient to owe.';
COMMENT ON COLUMN "agent_finding"."version" IS '1 for the first row; higher for each change.';
COMMENT ON COLUMN "agent_finding"."is_current" IS '1 on the latest version. Counts use current rows only.';
COMMENT ON COLUMN "agent_finding"."previous_agent_finding_id" IS 'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.';
COMMENT ON COLUMN "agent_finding"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "agent_finding"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "agent_task" IS 'One work item for a person or another agent. A status change is a new version.';
COMMENT ON COLUMN "agent_task"."agent_task_id" IS 'Stable ID of the record: the same on every version. The primary key is (agent_task_id, version). Every link from another table uses agent_task_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.';
COMMENT ON COLUMN "agent_task"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "agent_task"."task_type" IS 'Fix_claim, appeal, chase_note, verify_coverage, request_auth, review_write_off and so on.';
COMMENT ON COLUMN "agent_task"."owner_role" IS 'Billing, coding, front desk, provider, manager, or an agent.';
COMMENT ON COLUMN "agent_task"."task_status" IS 'Open, in_progress, done, cancelled, blocked.';
COMMENT ON COLUMN "agent_task"."created_date" IS 'When raised.';
COMMENT ON COLUMN "agent_task"."agent_code" IS 'Raising agent.';
COMMENT ON COLUMN "agent_task"."entity_type" IS 'Table the task is about. Must agree with the typed link of the same entity (CHECK).';
COMMENT ON COLUMN "agent_task"."entity_id" IS 'Internal ID in that table.';
COMMENT ON COLUMN "agent_task"."agent_decision_id" IS 'The decision that raised it.';
COMMENT ON COLUMN "agent_task"."agent_finding_id" IS 'The finding that raised it.';
COMMENT ON COLUMN "agent_task"."priority" IS 'High, normal, low.';
COMMENT ON COLUMN "agent_task"."due_date" IS 'Target date.';
COMMENT ON COLUMN "agent_task"."completed_date" IS 'Time to complete.';
COMMENT ON COLUMN "agent_task"."assigned_to_staff_id" IS 'Pseudonymous assignee, never a name. Holds the staff_id of the pseudonymous person.';
COMMENT ON COLUMN "agent_task"."amount_at_stake" IS 'Dollars involved.';
COMMENT ON COLUMN "agent_task"."outcome" IS 'Done, no_action_needed, declined.';
COMMENT ON COLUMN "agent_task"."title" IS 'Short label; no patient text. Scanned for identifiers at write time; a value that fails is refused.';
COMMENT ON COLUMN "agent_task"."practice_id" IS 'Reports by practice.';
COMMENT ON COLUMN "agent_task"."patient_id" IS 'Patient level view.';
COMMENT ON COLUMN "agent_task"."payer_id" IS 'Reports by payer.';
COMMENT ON COLUMN "agent_task"."provider_id" IS 'Reports by provider.';
COMMENT ON COLUMN "agent_task"."specialty_id" IS 'Reports by specialty.';
COMMENT ON COLUMN "agent_task"."appointment_id" IS 'The appointment concerned, when there is one.';
COMMENT ON COLUMN "agent_task"."encounter_id" IS 'The visit concerned.';
COMMENT ON COLUMN "agent_task"."bill_id" IS 'The bill concerned.';
COMMENT ON COLUMN "agent_task"."claim_id" IS 'The claim concerned.';
COMMENT ON COLUMN "agent_task"."denial_id" IS 'The denial concerned.';
COMMENT ON COLUMN "agent_task"."authorization_id" IS 'The authorization concerned.';
COMMENT ON COLUMN "agent_task"."minutes_spent" IS 'Minutes a person spent on the item.';
COMMENT ON COLUMN "agent_task"."contact_channel" IS 'How the payer was reached: portal, phone, fax, clearinghouse, EMR inbox.';
COMMENT ON COLUMN "agent_task"."escalation_level" IS '0 provider, 1 provider again, 2 practice manager, 3 medical director.';
COMMENT ON COLUMN "agent_task"."reminder_count" IS 'How many reminders were sent for the item.';
COMMENT ON COLUMN "agent_task"."version" IS '1 for the first row; higher for each change.';
COMMENT ON COLUMN "agent_task"."is_current" IS '1 on the latest version. Counts use current rows only.';
COMMENT ON COLUMN "agent_task"."previous_agent_task_id" IS 'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.';
COMMENT ON COLUMN "agent_task"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "agent_task"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "agent_approval" IS 'One row per approval or rejection of a proposed change. Append-only.';
COMMENT ON COLUMN "agent_approval"."agent_approval_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "agent_approval"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "agent_approval"."agent_decision_id" IS 'The proposal being approved.';
COMMENT ON COLUMN "agent_approval"."approval_type" IS 'Write_off, refund, claim_change, code_change, send_to_payer, setting_change.';
COMMENT ON COLUMN "agent_approval"."approval_status" IS 'Approved, rejected, expired.';
COMMENT ON COLUMN "agent_approval"."approved_by_staff_id" IS 'Pseudonymous approver (staff_id). Required when approval_status = approved (CHECK); blank on rejected or expired rows.';
COMMENT ON COLUMN "agent_approval"."approver_role" IS 'Role at the time.';
COMMENT ON COLUMN "agent_approval"."approval_date" IS 'When answered.';
COMMENT ON COLUMN "agent_approval"."agent_task_id" IS 'The task it closed.';
COMMENT ON COLUMN "agent_approval"."amount_approved" IS 'Dollars approved.';
COMMENT ON COLUMN "agent_approval"."limit_checked" IS 'Within the approver''s limit.';
COMMENT ON COLUMN "agent_approval"."reason_code" IS 'Why approved or rejected.';
COMMENT ON COLUMN "agent_approval"."entity_type" IS 'Table affected.';
COMMENT ON COLUMN "agent_approval"."entity_id" IS 'Internal ID affected.';
COMMENT ON COLUMN "agent_approval"."practice_id" IS 'Copied.';
COMMENT ON COLUMN "agent_approval"."approval_ts" IS 'Exact time.';
COMMENT ON COLUMN "agent_approval"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "agent_approval"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "agent_writeback" IS 'One row per thing sent out to the PM, EHR, clearinghouse or payer, and what came back. A retry is a new version.';
COMMENT ON COLUMN "agent_writeback"."agent_writeback_id" IS 'Stable ID of the record: the same on every version. The primary key is (agent_writeback_id, version). Every link from another table uses agent_writeback_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.';
COMMENT ON COLUMN "agent_writeback"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "agent_writeback"."agent_decision_id" IS 'The decision it carries out.';
COMMENT ON COLUMN "agent_writeback"."target_system" IS 'Pm, ehr, clearinghouse, payer_portal, scheduler.';
COMMENT ON COLUMN "agent_writeback"."writeback_type" IS 'Note, task, 270, 278, 837_correction, status_update, appeal_packet and so on.';
COMMENT ON COLUMN "agent_writeback"."send_status" IS 'Not_sent_shadow, queued, sent, acknowledged, failed.';
COMMENT ON COLUMN "agent_writeback"."attempted_at" IS 'Time of the attempt.';
COMMENT ON COLUMN "agent_writeback"."agent_approval_id" IS 'Required for money or record changes.';
COMMENT ON COLUMN "agent_writeback"."agent_code" IS 'Copied.';
COMMENT ON COLUMN "agent_writeback"."entity_type" IS 'Table concerned.';
COMMENT ON COLUMN "agent_writeback"."entity_id" IS 'Internal ID concerned.';
COMMENT ON COLUMN "agent_writeback"."attempt_no" IS 'Retry count.';
COMMENT ON COLUMN "agent_writeback"."response_code" IS 'Acknowledgement or error class.';
COMMENT ON COLUMN "agent_writeback"."response_at" IS 'Time of the reply.';
COMMENT ON COLUMN "agent_writeback"."external_ref" IS 'The target system''s reference. Restricted.';
COMMENT ON COLUMN "agent_writeback"."payload_hash" IS 'Hash of what was sent. Payloads themselves are not stored.';
COMMENT ON COLUMN "agent_writeback"."practice_id" IS 'Copied.';
COMMENT ON COLUMN "agent_writeback"."claim_id" IS 'Copied when relevant.';
COMMENT ON COLUMN "agent_writeback"."appointment_id" IS 'Copied when relevant.';
COMMENT ON COLUMN "agent_writeback"."version" IS '1 for the first row; higher for each change.';
COMMENT ON COLUMN "agent_writeback"."is_current" IS '1 on the latest version. Counts use current rows only.';
COMMENT ON COLUMN "agent_writeback"."previous_agent_writeback_id" IS 'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.';
COMMENT ON COLUMN "agent_writeback"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "agent_writeback"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "agent_forecast" IS 'One row per stored prediction: a cash, recoverable or claim payment forecast, with its range and, later, what actually happened.';
COMMENT ON COLUMN "agent_forecast"."agent_forecast_id" IS 'Stable ID of the record: the same on every version. The primary key is (agent_forecast_id, version). Every link from another table uses agent_forecast_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.';
COMMENT ON COLUMN "agent_forecast"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "agent_forecast"."forecast_type" IS 'Cash_week, cash_28d, cash_later, claim_week_chance, recoverable_month.';
COMMENT ON COLUMN "agent_forecast"."as_of_date" IS 'Date the forecast was made. Each day''s forecast is kept, so later scoring uses what was known then.';
COMMENT ON COLUMN "agent_forecast"."target_start_date" IS 'First day of the period predicted.';
COMMENT ON COLUMN "agent_forecast"."target_end_date" IS 'Last day of the period predicted. For cash_later, as-of date plus 365 days.';
COMMENT ON COLUMN "agent_forecast"."expected_amount" IS 'Expected dollars in the period (chance times balance for one claim).';
COMMENT ON COLUMN "agent_forecast"."low_amount" IS 'Low end of the range (80% by default).';
COMMENT ON COLUMN "agent_forecast"."high_amount" IS 'High end of the range.';
COMMENT ON COLUMN "agent_forecast"."probability" IS 'Chance a claim is paid in the period, 0 to 1. Blank for dollar-only rows.';
COMMENT ON COLUMN "agent_forecast"."claim_count" IS 'Open claims behind the row.';
COMMENT ON COLUMN "agent_forecast"."practice_id" IS 'Reports by practice.';
COMMENT ON COLUMN "agent_forecast"."payer_id" IS 'Forecast by payer; blank for all payers.';
COMMENT ON COLUMN "agent_forecast"."entity_type" IS 'Claim for a claim chance; practice or payer for a total.';
COMMENT ON COLUMN "agent_forecast"."entity_id" IS 'Internal ID of the claim for a claim chance; blank for totals.';
COMMENT ON COLUMN "agent_forecast"."actual_amount" IS 'What was really paid in the period (835 payments in ledger_entry). Filled when the period closes.';
COMMENT ON COLUMN "agent_forecast"."actual_known_date" IS 'Date the actual was filled in.';
COMMENT ON COLUMN "agent_forecast"."within_range" IS '1 when the actual landed inside low and high; coverage is the share of 1s.';
COMMENT ON COLUMN "agent_forecast"."interval_level" IS 'Confidence level of the range, 0.80 by default.';
COMMENT ON COLUMN "agent_forecast"."model_name" IS 'Model or method used.';
COMMENT ON COLUMN "agent_forecast"."code_version" IS 'Agent version, for replay.';
COMMENT ON COLUMN "agent_forecast"."version" IS '1 for the first row; higher for each change.';
COMMENT ON COLUMN "agent_forecast"."is_current" IS '1 on the latest version. Counts use current rows only.';
COMMENT ON COLUMN "agent_forecast"."previous_agent_forecast_id" IS 'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.';
COMMENT ON COLUMN "agent_forecast"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "agent_forecast"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "patient" IS 'A patient. No names, birth dates, addresses or raw member numbers are stored.';
COMMENT ON COLUMN "patient"."patient_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "patient"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "patient"."patient_number_hash" IS 'Salted hash of the client''s patient number. The only link back to the source. Restricted.';
COMMENT ON COLUMN "patient"."master_patient_hash" IS 'The same person across member IDs or practices.';
COMMENT ON COLUMN "patient"."merged_into_patient_id" IS 'Duplicate records merged at the source.';
COMMENT ON COLUMN "patient"."birth_year" IS 'Year only; age at service.';
COMMENT ON COLUMN "patient"."is_age_90_plus" IS 'Ages above 89 are grouped as 90+.';
COMMENT ON COLUMN "patient"."sex" IS 'M, F, U. Gender-specific procedure edits.';
COMMENT ON COLUMN "patient"."state" IS 'State rules and regional reports.';
COMMENT ON COLUMN "patient"."primary_practice_id" IS 'Home practice.';
COMMENT ON COLUMN "patient"."first_seen_date" IS 'New vs established.';
COMMENT ON COLUMN "patient"."last_seen_date" IS 'Lapsed patients.';
COMMENT ON COLUMN "patient"."primary_coverage_id" IS 'Current primary coverage.';
COMMENT ON COLUMN "patient"."guarantor_id" IS 'The guarantor account responsible for the patient balance.';
COMMENT ON COLUMN "patient"."is_self_pay" IS 'No active coverage.';
COMMENT ON COLUMN "patient"."zip3" IS 'Geography. Stored as 000 for the 3-digit zips with fewer than 20,000 people (HIPAA Safe Harbor).';
COMMENT ON COLUMN "patient"."language" IS 'Communication.';
COMMENT ON COLUMN "patient"."is_deceased" IS 'Stops statements.';
COMMENT ON COLUMN "patient"."is_active" IS 'Lifecycle: 0 once retired.';
COMMENT ON COLUMN "patient"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "patient"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "patient"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "patient"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "patient"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "patient"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "patient"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "patient"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "patient"."source" IS 'Where the row came from.';
COMMENT ON COLUMN "patient"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "coverage" IS 'One insurance policy for a patient, per period. A change closes the old row and adds a new one.';
COMMENT ON COLUMN "coverage"."coverage_id" IS 'Stable ID of the record: the same on every version. The primary key is (coverage_id, version). Every link from another table uses coverage_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.';
COMMENT ON COLUMN "coverage"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "coverage"."patient_id" IS 'Whose policy.';
COMMENT ON COLUMN "coverage"."payer_id" IS 'The insurer.';
COMMENT ON COLUMN "coverage"."payer_plan_id" IS 'The plan (product) under the payer.';
COMMENT ON COLUMN "coverage"."member_number_hash" IS 'Hash of the member ID. The raw ID is never stored; eligibility reads it from the source at send time. Restricted.';
COMMENT ON COLUMN "coverage"."coverage_order" IS '1 primary, 2 secondary, 3 tertiary.';
COMMENT ON COLUMN "coverage"."effective_date" IS 'Policy start.';
COMMENT ON COLUMN "coverage"."termination_date" IS 'Policy end; blank while open.';
COMMENT ON COLUMN "coverage"."plan_type" IS 'PPO, HMO, EPO, POS, Medicare Advantage, traditional Medicare, Medicaid managed care.';
COMMENT ON COLUMN "coverage"."plan_name" IS 'Display.';
COMMENT ON COLUMN "coverage"."group_number_hash" IS 'Group identification. Restricted.';
COMMENT ON COLUMN "coverage"."relationship_to_holder" IS 'Self, spouse, child, other: sets the dependent level.';
COMMENT ON COLUMN "coverage"."last_verified_date" IS 'When coverage was last checked.';
COMMENT ON COLUMN "coverage"."last_verified_status" IS 'Active, inactive, not found.';
COMMENT ON COLUMN "coverage"."requires_referral" IS 'HMO referral rules.';
COMMENT ON COLUMN "coverage"."pcp_provider_id" IS 'HMO primary care provider.';
COMMENT ON COLUMN "coverage"."copay_amount" IS 'Latest verified benefit.';
COMMENT ON COLUMN "coverage"."coinsurance_pct" IS 'Latest verified benefit, as a fraction 0 to 1. Cache of the latest eligibility_check; never edited directly.';
COMMENT ON COLUMN "coverage"."deductible_remaining" IS 'Latest verified benefit.';
COMMENT ON COLUMN "coverage"."subscriber_hash" IS 'Links family members under one subscriber. Restricted.';
COMMENT ON COLUMN "coverage"."version" IS '1 for the first row; higher for each change.';
COMMENT ON COLUMN "coverage"."is_current" IS '1 on the latest version. Counts use current rows only.';
COMMENT ON COLUMN "coverage"."previous_coverage_id" IS 'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.';
COMMENT ON COLUMN "coverage"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "coverage"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "coverage"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "coverage"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "coverage"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "coverage"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "coverage"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "coverage"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "coverage"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "coverage"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "authorization" IS 'A prior authorization as the payer issued it. An extension or revision closes the old row and adds a new one.';
COMMENT ON COLUMN "authorization"."authorization_id" IS 'Stable ID of the record: the same on every version. The primary key is (authorization_id, version). Every link from another table uses authorization_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.';
COMMENT ON COLUMN "authorization"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "authorization"."authorization_number" IS 'The payer''s number; a pending request uses our request reference. Restricted.';
COMMENT ON COLUMN "authorization"."patient_id" IS 'Whose authorization.';
COMMENT ON COLUMN "authorization"."payer_id" IS 'With which payer.';
COMMENT ON COLUMN "authorization"."practice_id" IS 'Reports by practice.';
COMMENT ON COLUMN "authorization"."authorization_status" IS 'Requested, pended, certified, modified, not_certified, cancelled, expired.';
COMMENT ON COLUMN "authorization"."coverage_id" IS 'The policy it applies to.';
COMMENT ON COLUMN "authorization"."primary_cpt_code_id" IS 'The main procedure, for quick reports. Every authorized code and its units are in authorization_line.';
COMMENT ON COLUMN "authorization"."units_approved" IS 'Overuse and remaining units. Header total; per-code units are on authorization_line.';
COMMENT ON COLUMN "authorization"."units_used" IS 'Rebuilt from claims. Header total; per-code units are on authorization_line.';
COMMENT ON COLUMN "authorization"."valid_from" IS 'The approved window.';
COMMENT ON COLUMN "authorization"."valid_to" IS 'The approved window.';
COMMENT ON COLUMN "authorization"."request_date" IS 'Turnaround time.';
COMMENT ON COLUMN "authorization"."decision_date" IS 'Turnaround time.';
COMMENT ON COLUMN "authorization"."authorization_type" IS 'Outpatient, inpatient, referral, predetermination, retro.';
COMMENT ON COLUMN "authorization"."requesting_provider_id" IS 'Who asked.';
COMMENT ON COLUMN "authorization"."rendering_provider_id" IS 'Who will perform.';
COMMENT ON COLUMN "authorization"."urgency" IS 'Standard or expedited.';
COMMENT ON COLUMN "authorization"."request_channel" IS 'X12, portal, phone, fax.';
COMMENT ON COLUMN "authorization"."decision_reason_code" IS 'Reason the payer gave.';
COMMENT ON COLUMN "authorization"."diagnosis_code_id" IS 'Diagnosis on the request.';
COMMENT ON COLUMN "authorization"."facility_id" IS 'Location.';
COMMENT ON COLUMN "authorization"."units_requested" IS 'Units or visits the practice asked for. Header total; per-code units are on authorization_line.';
COMMENT ON COLUMN "authorization"."place_of_service_id" IS 'Place-of-service code on the request (for example 11 office, 22 outpatient hospital).';
COMMENT ON COLUMN "authorization"."version" IS '1 for the first row; higher for each change.';
COMMENT ON COLUMN "authorization"."is_current" IS '1 on the latest version. Counts use current rows only.';
COMMENT ON COLUMN "authorization"."previous_authorization_id" IS 'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.';
COMMENT ON COLUMN "authorization"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "authorization"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "authorization"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "authorization"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "authorization"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "authorization"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "authorization"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "authorization"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "authorization"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "authorization"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "authorization_line" IS 'One authorized service on an authorization: code, units and decision.';
COMMENT ON COLUMN "authorization_line"."authorization_line_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "authorization_line"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "authorization_line"."authorization_id" IS 'The authorization (stable ID).';
COMMENT ON COLUMN "authorization_line"."line_number" IS 'Position within the authorization.';
COMMENT ON COLUMN "authorization_line"."cpt_code_id" IS 'Code authorized, or the first code of a range.';
COMMENT ON COLUMN "authorization_line"."cpt_code_to_id" IS 'Last code of a range.';
COMMENT ON COLUMN "authorization_line"."modifier_id" IS 'Modifier the approval is tied to.';
COMMENT ON COLUMN "authorization_line"."unit_type" IS 'units, visits or days.';
COMMENT ON COLUMN "authorization_line"."units_requested" IS 'Asked for.';
COMMENT ON COLUMN "authorization_line"."units_approved" IS 'Approved.';
COMMENT ON COLUMN "authorization_line"."units_used" IS 'Used so far, rebuilt from claim lines.';
COMMENT ON COLUMN "authorization_line"."line_status" IS 'certified, modified, not_certified or pended.';
COMMENT ON COLUMN "authorization_line"."valid_from" IS 'When different from the header.';
COMMENT ON COLUMN "authorization_line"."valid_to" IS 'When different from the header.';
COMMENT ON COLUMN "authorization_line"."practice_id" IS 'Copied, so reports skip the join.';
COMMENT ON COLUMN "authorization_line"."patient_id" IS 'Copied, so reports skip the join.';
COMMENT ON COLUMN "authorization_line"."payer_id" IS 'Copied, so reports skip the join.';
COMMENT ON COLUMN "authorization_line"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "authorization_line"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "authorization_line"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "authorization_line"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "authorization_line"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "authorization_line"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "authorization_line"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "authorization_line"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "authorization_line"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "authorization_line"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "guarantor" IS 'One guarantor account: the person (or patient) financially responsible for patient balances. Pseudonymous.';
COMMENT ON COLUMN "guarantor"."guarantor_id" IS 'Stable ID of the record: the same on every version. The primary key is (guarantor_id, version). Every link from another table uses guarantor_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.';
COMMENT ON COLUMN "guarantor"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "guarantor"."guarantor_number" IS 'The PM guarantor account number. Restricted.';
COMMENT ON COLUMN "guarantor"."guarantor_hash" IS 'Salted hash of the guarantor identity, for matching across loads. Never the name.';
COMMENT ON COLUMN "guarantor"."guarantor_type" IS 'self, parent, spouse, legal_guardian, other_person, organization.';
COMMENT ON COLUMN "guarantor"."practice_id" IS 'Practice that owns the account (blank when shared across practices).';
COMMENT ON COLUMN "guarantor"."state" IS 'State of the guarantor (statement and collection rules).';
COMMENT ON COLUMN "guarantor"."zip3" IS 'Same Safe Harbor rule as patient.zip3.';
COMMENT ON COLUMN "guarantor"."account_status" IS 'active, collections, bad_debt, closed.';
COMMENT ON COLUMN "guarantor"."is_inferred" IS '1 when built as a self-guarantor account because the source sent none.';
COMMENT ON COLUMN "guarantor"."has_portal_account" IS 'Guarantor uses the patient portal (statement channel).';
COMMENT ON COLUMN "guarantor"."is_active" IS 'Lifecycle: 0 once closed.';
COMMENT ON COLUMN "guarantor"."version" IS '1 for the first row; higher for each change.';
COMMENT ON COLUMN "guarantor"."is_current" IS '1 on the latest version. Counts use current rows only.';
COMMENT ON COLUMN "guarantor"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "guarantor"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "guarantor"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "guarantor"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "guarantor"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "guarantor"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "guarantor"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "guarantor"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "guarantor"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "guarantor"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "staff" IS 'One pseudonymous staff member who approves changes or owns tasks. Never a name.';
COMMENT ON COLUMN "staff"."staff_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "staff"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "staff"."staff_number" IS 'Pseudonymous code of the person, for example B01 or C03. Restricted so it is not shown in analytics.';
COMMENT ON COLUMN "staff"."practice_id" IS 'Practice the person works for.';
COMMENT ON COLUMN "staff"."staff_role" IS 'Job role: billing specialist, denial specialist, coder, manager.';
COMMENT ON COLUMN "staff"."team" IS 'Team: billing or coding.';
COMMENT ON COLUMN "staff"."weekly_hours" IS 'Working hours per week; capacity is hours times handling time.';
COMMENT ON COLUMN "staff"."start_date" IS 'First day in the role.';
COMMENT ON COLUMN "staff"."end_date" IS 'Last day in the role. Blank while active.';
COMMENT ON COLUMN "staff"."is_active" IS '1 while the person can be assigned work.';
COMMENT ON COLUMN "staff"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "staff"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "staff"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "staff"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "staff"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "staff"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "staff"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "staff"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "staff"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "staff"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "enrollment" IS 'One enrollment or screening event for a provider: a status change with a payer, or one exclusion-list check.';
COMMENT ON COLUMN "enrollment"."enrollment_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "enrollment"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "enrollment"."enrollment_number" IS 'The credentialing system''s own number for the status row or screening result. Restricted.';
COMMENT ON COLUMN "enrollment"."provider_id" IS 'Provider enrolled or screened. NPI is read from provider.npi.';
COMMENT ON COLUMN "enrollment"."payer_id" IS 'Payer enrolled with. Blank for a screening event.';
COMMENT ON COLUMN "enrollment"."practice_id" IS 'Practice the provider bills under.';
COMMENT ON COLUMN "enrollment"."facility_id" IS 'Site where the provider works for this payer.';
COMMENT ON COLUMN "enrollment"."event_type" IS 'status for an enrollment change, screening for an exclusion-list check.';
COMMENT ON COLUMN "enrollment"."event_date" IS 'Day the status was recorded, or the day the list was checked.';
COMMENT ON COLUMN "enrollment"."enrollment_status" IS 'pending, active, expired, denied or terminated. Blank on a screening event.';
COMMENT ON COLUMN "enrollment"."enrollment_type" IS 'New application, renewal, revalidation, change or termination.';
COMMENT ON COLUMN "enrollment"."plan_program_code" IS 'Program the enrollment covers: Medicare, Medicaid, commercial, EDI (electronic claims with the clearinghouse).';
COMMENT ON COLUMN "enrollment"."submitted_date" IS 'Day the application went in. Gives enrollment cycle time.';
COMMENT ON COLUMN "enrollment"."effective_date" IS 'Day the enrollment became active.';
COMMENT ON COLUMN "enrollment"."expires_date" IS 'Day it lapses. Blank means no expiry on file.';
COMMENT ON COLUMN "enrollment"."revalidation_due_date" IS 'Date the payer requires revalidation.';
COMMENT ON COLUMN "enrollment"."last_revalidated_date" IS 'Date of the last revalidation.';
COMMENT ON COLUMN "enrollment"."payer_provider_number" IS 'Number the payer gave the provider. Restricted.';
COMMENT ON COLUMN "enrollment"."application_number" IS 'Payer or portal tracking number of the application. Restricted.';
COMMENT ON COLUMN "enrollment"."end_reason_code" IS 'Code for why the payer refused or ended the enrollment. No free text.';
COMMENT ON COLUMN "enrollment"."screening_source" IS 'List checked: OIG, SAM, STATE. Blank on a status event.';
COMMENT ON COLUMN "enrollment"."screening_result" IS 'clear or excluded. Blank on a status event.';
COMMENT ON COLUMN "enrollment"."screening_list_date" IS 'Release date of the list used, so a later list can be told apart.';
COMMENT ON COLUMN "enrollment"."exclusion_type" IS 'Type of exclusion, as a list code.';
COMMENT ON COLUMN "enrollment"."excluded_date" IS 'Day the provider was excluded.';
COMMENT ON COLUMN "enrollment"."reinstated_date" IS 'Day the provider was reinstated.';
COMMENT ON COLUMN "enrollment"."match_method" IS 'How the provider was matched on the list: npi, name_dob, name. Weaker methods need review.';
COMMENT ON COLUMN "enrollment"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "enrollment"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "enrollment"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "enrollment"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "enrollment"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "enrollment"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "enrollment"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "enrollment"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "enrollment"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "enrollment"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "provider_identifier" IS 'One identifier a provider holds besides the NPI: PTAN, Medicaid ID, state license, DEA ...';
COMMENT ON COLUMN "provider_identifier"."provider_identifier_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "provider_identifier"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "provider_identifier"."provider_id" IS 'The provider.';
COMMENT ON COLUMN "provider_identifier"."identifier_type" IS 'ptan, medicaid_id, state_license, dea, caqh, payer_specific.';
COMMENT ON COLUMN "provider_identifier"."identifier_value" IS 'The identifier. Restricted.';
COMMENT ON COLUMN "provider_identifier"."issuing_state" IS 'For licenses and Medicaid IDs.';
COMMENT ON COLUMN "provider_identifier"."payer_id" IS 'For payer-issued IDs.';
COMMENT ON COLUMN "provider_identifier"."effective_from" IS 'Issued.';
COMMENT ON COLUMN "provider_identifier"."effective_to" IS 'Expires. 9999-12-31 when it does not.';
COMMENT ON COLUMN "provider_identifier"."verified_date" IS 'Last checked against the issuer.';
COMMENT ON COLUMN "provider_identifier"."is_active" IS 'Lifecycle: 0 once retired.';
COMMENT ON COLUMN "provider_identifier"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "provider_identifier"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "provider_identifier"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "provider_identifier"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "provider_identifier"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "provider_identifier"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "provider_identifier"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "provider_identifier"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "provider_identifier"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "provider_identifier"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "provider_practice" IS 'One provider working at one practice (and optionally a facility) for a period.';
COMMENT ON COLUMN "provider_practice"."provider_practice_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "provider_practice"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "provider_practice"."provider_id" IS 'The provider.';
COMMENT ON COLUMN "provider_practice"."practice_id" IS 'The practice.';
COMMENT ON COLUMN "provider_practice"."facility_id" IS 'Site, when it matters.';
COMMENT ON COLUMN "provider_practice"."affiliation_role" IS 'rendering, billing, supervising.';
COMMENT ON COLUMN "provider_practice"."is_primary" IS '1 on the home practice.';
COMMENT ON COLUMN "provider_practice"."start_date" IS 'Start.';
COMMENT ON COLUMN "provider_practice"."end_date" IS '9999-12-31 while active.';
COMMENT ON COLUMN "provider_practice"."fte" IS 'Share of full time.';
COMMENT ON COLUMN "provider_practice"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "provider_practice"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "provider_practice"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "provider_practice"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "provider_practice"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "provider_practice"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "provider_practice"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "provider_practice"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "provider_practice"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "provider_practice"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "edi_enrollment" IS 'One EDI enrollment of a practice or provider with a payer for one transaction: ERA, EFT, claims, eligibility, claim status or attachments.';
COMMENT ON COLUMN "edi_enrollment"."edi_enrollment_id" IS 'Stable ID of the record: the same on every version. The primary key is (edi_enrollment_id, version). Every link from another table uses edi_enrollment_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.';
COMMENT ON COLUMN "edi_enrollment"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "edi_enrollment"."practice_id" IS 'Enrolling practice.';
COMMENT ON COLUMN "edi_enrollment"."provider_id" IS 'When enrolled per provider.';
COMMENT ON COLUMN "edi_enrollment"."payer_id" IS 'Payer.';
COMMENT ON COLUMN "edi_enrollment"."transaction_type" IS 'era_835, eft, claim_837, elig_270, status_276, attach_275.';
COMMENT ON COLUMN "edi_enrollment"."clearinghouse_code" IS 'Clearinghouse the enrollment runs through.';
COMMENT ON COLUMN "edi_enrollment"."enrollment_status" IS 'not_enrolled, submitted, pending, enrolled, rejected, terminated.';
COMMENT ON COLUMN "edi_enrollment"."submitted_date" IS 'When submitted.';
COMMENT ON COLUMN "edi_enrollment"."effective_date" IS 'When live.';
COMMENT ON COLUMN "edi_enrollment"."terminated_date" IS 'When ended.';
COMMENT ON COLUMN "edi_enrollment"."is_inferred" IS '1 when deduced from files seen.';
COMMENT ON COLUMN "edi_enrollment"."payer_identifier_id" IS 'Payer ID used for this transaction.';
COMMENT ON COLUMN "edi_enrollment"."version" IS '1 for the first row; higher for each change.';
COMMENT ON COLUMN "edi_enrollment"."is_current" IS '1 on the latest version. Counts use current rows only.';
COMMENT ON COLUMN "edi_enrollment"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "edi_enrollment"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "edi_enrollment"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "edi_enrollment"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "edi_enrollment"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "edi_enrollment"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "edi_enrollment"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "edi_enrollment"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "edi_enrollment"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "edi_enrollment"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "practice" IS 'A billing entity inside a client.';
COMMENT ON COLUMN "practice"."practice_id" IS 'Stable ID of the record: the same on every version. The primary key is (practice_id, version). Every link from another table uses practice_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.';
COMMENT ON COLUMN "practice"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "practice"."practice_number" IS 'The client''s code for the practice.';
COMMENT ON COLUMN "practice"."practice_name" IS 'Display.';
COMMENT ON COLUMN "practice"."tax_id" IS 'Billing entity on claims and contracts. Restricted.';
COMMENT ON COLUMN "practice"."group_npi" IS 'Billing NPI for group claims.';
COMMENT ON COLUMN "practice"."time_zone" IS 'Day cut-offs for aging, lag and snapshots.';
COMMENT ON COLUMN "practice"."fiscal_year_start_month" IS 'Fiscal reporting.';
COMMENT ON COLUMN "practice"."go_live_date" IS 'Where history starts and opening balances apply.';
COMMENT ON COLUMN "practice"."is_active" IS 'Lifecycle: 0 once retired.';
COMMENT ON COLUMN "practice"."version" IS '1 for the first row; higher for each change.';
COMMENT ON COLUMN "practice"."is_current" IS '1 on the latest version. Counts use current rows only.';
COMMENT ON COLUMN "practice"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "practice"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "practice"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "practice"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "practice"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "practice"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "practice"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "practice"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "practice"."source" IS 'Where the row came from.';
COMMENT ON COLUMN "practice"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "provider" IS 'A clinician or group.';
COMMENT ON COLUMN "provider"."provider_id" IS 'Stable ID of the record: the same on every version. The primary key is (provider_id, version). Every link from another table uses provider_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.';
COMMENT ON COLUMN "provider"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "provider"."npi" IS 'National provider ID; links scheduler, EHR, claims and payer.';
COMMENT ON COLUMN "provider"."provider_number" IS 'The scheduler or EHR''s own provider code.';
COMMENT ON COLUMN "provider"."provider_type" IS 'Individual or group.';
COMMENT ON COLUMN "provider"."specialty_id" IS 'Main specialty.';
COMMENT ON COLUMN "provider"."taxonomy_code" IS 'Enrollment and specialty mapping.';
COMMENT ON COLUMN "provider"."credential" IS 'MD, DO, NP, PA.';
COMMENT ON COLUMN "provider"."provider_name" IS 'Display.';
COMMENT ON COLUMN "provider"."practice_id" IS 'Home practice; each transaction still carries the practice billed.';
COMMENT ON COLUMN "provider"."start_date" IS 'Productivity window.';
COMMENT ON COLUMN "provider"."end_date" IS 'Productivity window.';
COMMENT ON COLUMN "provider"."supervising_provider_id" IS 'Supervised clinicians.';
COMMENT ON COLUMN "provider"."is_active" IS 'Lifecycle: 0 once retired.';
COMMENT ON COLUMN "provider"."version" IS '1 for the first row; higher for each change.';
COMMENT ON COLUMN "provider"."is_current" IS '1 on the latest version. Counts use current rows only.';
COMMENT ON COLUMN "provider"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "provider"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "provider"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "provider"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "provider"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "provider"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "provider"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "provider"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "provider"."source" IS 'Where the row came from.';
COMMENT ON COLUMN "provider"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "payer" IS 'An insurer.';
COMMENT ON COLUMN "payer"."payer_id" IS 'Stable ID of the record: the same on every version. The primary key is (payer_id, version). Every link from another table uses payer_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.';
COMMENT ON COLUMN "payer"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "payer"."payer_code" IS 'Public payer ID used by the clearinghouse.';
COMMENT ON COLUMN "payer"."payer_name" IS 'Display.';
COMMENT ON COLUMN "payer"."payer_number" IS 'The PM''s own payer code.';
COMMENT ON COLUMN "payer"."payer_type" IS 'Commercial, medicare, medicaid, tricare, workers_comp, auto, self_pay.';
COMMENT ON COLUMN "payer"."parent_payer" IS 'Rolls plans up to an organisation.';
COMMENT ON COLUMN "payer"."filing_days" IS 'Timely-filing limit (default). payer_contract or payer_plan overrides it when set.';
COMMENT ON COLUMN "payer"."corrected_claim_days" IS 'Window for corrected claims (default). payer_contract or payer_plan overrides it when set.';
COMMENT ON COLUMN "payer"."appeal_days" IS 'Appeal deadline (default). payer_contract or payer_plan overrides it when set.';
COMMENT ON COLUMN "payer"."standard_turnaround_days" IS 'Authorization planning.';
COMMENT ON COLUMN "payer"."supports_electronic_auth" IS 'Authorization planning.';
COMMENT ON COLUMN "payer"."state" IS 'Regional rules.';
COMMENT ON COLUMN "payer"."dispute_contact" IS 'Role mailbox or portal, never a person.';
COMMENT ON COLUMN "payer"."is_active" IS 'Lifecycle: 0 once retired.';
COMMENT ON COLUMN "payer"."filing_clock_basis" IS 'Which date starts the timely-filing clock: service date, discharge date, claim received and so on.';
COMMENT ON COLUMN "payer"."version" IS '1 for the first row; higher for each change.';
COMMENT ON COLUMN "payer"."is_current" IS '1 on the latest version. Counts use current rows only.';
COMMENT ON COLUMN "payer"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "payer"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "payer"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "payer"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "payer"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "payer"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "payer"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "payer"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "payer"."source" IS 'Where the row came from.';
COMMENT ON COLUMN "payer"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "cpt_code" IS 'A procedure code (CPT or HCPCS). Effective-dated.';
COMMENT ON COLUMN "cpt_code"."cpt_code_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "cpt_code"."tenant_id" IS 'Blank on the shared national row; set only on a tenant override row (for example a client''s own CARC classification or holidays). Lookups take the tenant row first, then the shared row.';
COMMENT ON COLUMN "cpt_code"."code" IS 'The 5-character code.';
COMMENT ON COLUMN "cpt_code"."code_type" IS 'CPT or HCPCS.';
COMMENT ON COLUMN "cpt_code"."effective_from" IS 'Which year''s meaning applies.';
COMMENT ON COLUMN "cpt_code"."effective_to" IS 'End of validity. 9999-12-31 while open, so range joins need no NULL handling.';
COMMENT ON COLUMN "cpt_code"."short_label" IS 'Our own words.';
COMMENT ON COLUMN "cpt_code"."category" IS 'E/M, radiology, lab, therapy, surgery, anesthesia, medicine, drug.';
COMMENT ON COLUMN "cpt_code"."em_level" IS 'Visit level 1 to 5.';
COMMENT ON COLUMN "cpt_code"."is_add_on" IS 'Needs a primary code.';
COMMENT ON COLUMN "cpt_code"."is_timed" IS 'Units come from time.';
COMMENT ON COLUMN "cpt_code"."unit_limit_per_day" IS 'CMS unit limit.';
COMMENT ON COLUMN "cpt_code"."laterality_required" IS 'Needs left or right.';
COMMENT ON COLUMN "cpt_code"."work_rvu" IS 'Provider productivity.';
COMMENT ON COLUMN "cpt_code"."global_period_days" IS 'Surgical bundling denials.';
COMMENT ON COLUMN "cpt_code"."is_unrecognized" IS 'Flagged placeholder for an unknown code.';
COMMENT ON COLUMN "cpt_code"."is_active" IS 'Lifecycle: 0 once retired.';
COMMENT ON COLUMN "cpt_code"."unit_limit_basis" IS 'How the unit limit applies: per line, per day or per date of service.';
COMMENT ON COLUMN "cpt_code"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "cpt_code"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "cpt_code"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "cpt_code"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "cpt_code"."source" IS 'Where the row came from.';
COMMENT ON COLUMN "cpt_code"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "diagnosis_code" IS 'An ICD-10-CM diagnosis code. Effective-dated.';
COMMENT ON COLUMN "diagnosis_code"."diagnosis_code_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "diagnosis_code"."tenant_id" IS 'Blank on the shared national row; set only on a tenant override row (for example a client''s own CARC classification or holidays). Lookups take the tenant row first, then the shared row.';
COMMENT ON COLUMN "diagnosis_code"."icd10_code" IS 'Saved without the dot.';
COMMENT ON COLUMN "diagnosis_code"."effective_from" IS 'Updated each October 1.';
COMMENT ON COLUMN "diagnosis_code"."effective_to" IS 'End of validity. 9999-12-31 while open, so range joins need no NULL handling.';
COMMENT ON COLUMN "diagnosis_code"."description" IS 'Public description.';
COMMENT ON COLUMN "diagnosis_code"."category" IS 'Chapter and block.';
COMMENT ON COLUMN "diagnosis_code"."is_billable" IS 'Header codes cause rejections.';
COMMENT ON COLUMN "diagnosis_code"."is_chronic" IS 'Condition analysis.';
COMMENT ON COLUMN "diagnosis_code"."is_unspecified" IS 'Coding specificity.';
COMMENT ON COLUMN "diagnosis_code"."parent_code" IS 'Less specific parent.';
COMMENT ON COLUMN "diagnosis_code"."hcc_category" IS 'Risk adjustment.';
COMMENT ON COLUMN "diagnosis_code"."is_unrecognized" IS 'Flagged placeholder.';
COMMENT ON COLUMN "diagnosis_code"."is_active" IS 'Lifecycle: 0 once retired.';
COMMENT ON COLUMN "diagnosis_code"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "diagnosis_code"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "diagnosis_code"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "diagnosis_code"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "diagnosis_code"."source" IS 'Where the row came from.';
COMMENT ON COLUMN "diagnosis_code"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "modifier" IS 'A procedure modifier.';
COMMENT ON COLUMN "modifier"."modifier_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "modifier"."tenant_id" IS 'Blank on the shared national row; set only on a tenant override row (for example a client''s own CARC classification or holidays). Lookups take the tenant row first, then the shared row.';
COMMENT ON COLUMN "modifier"."modifier_code" IS 'The 2-character modifier.';
COMMENT ON COLUMN "modifier"."modifier_group" IS 'Pricing, anatomical, telehealth, anesthesia, informational.';
COMMENT ON COLUMN "modifier"."affects_payment" IS 'Whether it changes payment.';
COMMENT ON COLUMN "modifier"."payment_adjustment_pct" IS 'For example 50% for a reduced service.';
COMMENT ON COLUMN "modifier"."short_label" IS 'Our own words.';
COMMENT ON COLUMN "modifier"."effective_from" IS 'Lifecycle.';
COMMENT ON COLUMN "modifier"."effective_to" IS 'Lifecycle. 9999-12-31 while open, so range joins need no NULL handling.';
COMMENT ON COLUMN "modifier"."is_active" IS 'Lifecycle: 0 once retired.';
COMMENT ON COLUMN "modifier"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "modifier"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "modifier"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "modifier"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "modifier"."source" IS 'Where the row came from.';
COMMENT ON COLUMN "modifier"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "place_of_service" IS 'A CMS place-of-service code.';
COMMENT ON COLUMN "place_of_service"."place_of_service_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "place_of_service"."tenant_id" IS 'Blank on the shared national row; set only on a tenant override row (for example a client''s own CARC classification or holidays). Lookups take the tenant row first, then the shared row.';
COMMENT ON COLUMN "place_of_service"."pos_code" IS 'CMS 2-digit code.';
COMMENT ON COLUMN "place_of_service"."pos_name" IS 'Public name.';
COMMENT ON COLUMN "place_of_service"."setting" IS 'Office, outpatient, inpatient, ER, home, telehealth.';
COMMENT ON COLUMN "place_of_service"."is_facility" IS 'Rate differences.';
COMMENT ON COLUMN "place_of_service"."is_telehealth" IS 'Rule differences.';
COMMENT ON COLUMN "place_of_service"."effective_from" IS 'Lifecycle.';
COMMENT ON COLUMN "place_of_service"."effective_to" IS 'Lifecycle. 9999-12-31 while open, so range joins need no NULL handling.';
COMMENT ON COLUMN "place_of_service"."is_active" IS 'Lifecycle: 0 once retired.';
COMMENT ON COLUMN "place_of_service"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "place_of_service"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "place_of_service"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "place_of_service"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "place_of_service"."source" IS 'Where the row came from.';
COMMENT ON COLUMN "place_of_service"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "specialty" IS 'A clinical specialty.';
COMMENT ON COLUMN "specialty"."specialty_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "specialty"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "specialty"."specialty_code" IS 'A short standard code.';
COMMENT ON COLUMN "specialty"."specialty_name" IS 'Display.';
COMMENT ON COLUMN "specialty"."specialty_group" IS 'Primary care, medical, surgical, behavioral, therapy, diagnostic.';
COMMENT ON COLUMN "specialty"."is_primary_care" IS 'Benchmarks and HMO rules.';
COMMENT ON COLUMN "specialty"."cms_specialty_code" IS 'Medicare list.';
COMMENT ON COLUMN "specialty"."taxonomy_prefix" IS 'Maps a taxonomy to the specialty.';
COMMENT ON COLUMN "specialty"."is_active" IS 'Lifecycle: 0 once retired.';
COMMENT ON COLUMN "specialty"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "specialty"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "specialty"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "specialty"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "specialty"."source" IS 'Where the row came from.';
COMMENT ON COLUMN "specialty"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "facility" IS 'A location where service happens.';
COMMENT ON COLUMN "facility"."facility_id" IS 'Stable ID of the record: the same on every version. The primary key is (facility_id, version). Every link from another table uses facility_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.';
COMMENT ON COLUMN "facility"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "facility"."facility_number" IS 'The client''s location code.';
COMMENT ON COLUMN "facility"."facility_name" IS 'Display.';
COMMENT ON COLUMN "facility"."practice_id" IS 'Owning practice.';
COMMENT ON COLUMN "facility"."facility_type" IS 'Office, clinic, hospital outpatient, surgery center, urgent care, lab, imaging, home, telehealth.';
COMMENT ON COLUMN "facility"."default_place_of_service_id" IS 'Usual place-of-service code.';
COMMENT ON COLUMN "facility"."facility_npi" IS 'Service facility NPI.';
COMMENT ON COLUMN "facility"."state" IS 'State rules.';
COMMENT ON COLUMN "facility"."open_date" IS 'Site history.';
COMMENT ON COLUMN "facility"."close_date" IS 'Site history.';
COMMENT ON COLUMN "facility"."zip" IS 'Location detail.';
COMMENT ON COLUMN "facility"."rooms" IS 'Capacity.';
COMMENT ON COLUMN "facility"."time_zone" IS 'Inherits the practice''s.';
COMMENT ON COLUMN "facility"."is_active" IS 'Lifecycle: 0 once retired.';
COMMENT ON COLUMN "facility"."version" IS '1 for the first row; higher for each change.';
COMMENT ON COLUMN "facility"."is_current" IS '1 on the latest version. Counts use current rows only.';
COMMENT ON COLUMN "facility"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "facility"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "facility"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "facility"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "facility"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "facility"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "facility"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "facility"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "facility"."source" IS 'Where the row came from.';
COMMENT ON COLUMN "facility"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "fee_schedule" IS 'One fee schedule of a practice (standard, self-pay ...), per version.';
COMMENT ON COLUMN "fee_schedule"."fee_schedule_id" IS 'Stable ID of the record: the same on every version. The primary key is (fee_schedule_id, version). Every link from another table uses fee_schedule_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.';
COMMENT ON COLUMN "fee_schedule"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "fee_schedule"."practice_id" IS 'Owning practice.';
COMMENT ON COLUMN "fee_schedule"."fee_schedule_name" IS 'standard, self_pay, hospital_based ...';
COMMENT ON COLUMN "fee_schedule"."facility_id" IS 'Location-specific schedule.';
COMMENT ON COLUMN "fee_schedule"."fee_basis" IS 'flat, or a multiple of Medicare.';
COMMENT ON COLUMN "fee_schedule"."is_default" IS 'Used when none is named.';
COMMENT ON COLUMN "fee_schedule"."is_inferred" IS '1 when rebuilt from bill lines.';
COMMENT ON COLUMN "fee_schedule"."effective_from" IS 'Start.';
COMMENT ON COLUMN "fee_schedule"."effective_to" IS '9999-12-31 while open.';
COMMENT ON COLUMN "fee_schedule"."is_active" IS 'Lifecycle: 0 once retired.';
COMMENT ON COLUMN "fee_schedule"."version" IS '1 for the first row; higher for each change.';
COMMENT ON COLUMN "fee_schedule"."is_current" IS '1 on the latest version. Counts use current rows only.';
COMMENT ON COLUMN "fee_schedule"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "fee_schedule"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "fee_schedule"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "fee_schedule"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "fee_schedule"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "fee_schedule"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "fee_schedule"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "fee_schedule"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "fee_schedule"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "fee_schedule"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "fee_schedule_line" IS 'One fee per procedure (and modifier) on one fee schedule. Billed amount = units x this fee. Effective-dated.';
COMMENT ON COLUMN "fee_schedule_line"."fee_schedule_line_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "fee_schedule_line"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "fee_schedule_line"."fee_schedule_id" IS 'The fee schedule (version) this line belongs to.';
COMMENT ON COLUMN "fee_schedule_line"."cpt_code_id" IS 'The procedure.';
COMMENT ON COLUMN "fee_schedule_line"."fee_per_unit" IS 'The charge per unit.';
COMMENT ON COLUMN "fee_schedule_line"."effective_from" IS 'When the fee took effect.';
COMMENT ON COLUMN "fee_schedule_line"."is_inferred" IS '1 when estimated.';
COMMENT ON COLUMN "fee_schedule_line"."effective_to" IS 'Blank while open. 9999-12-31 while open, so range joins need no NULL handling.';
COMMENT ON COLUMN "fee_schedule_line"."modifier_id" IS 'For fees that depend on the modifier.';
COMMENT ON COLUMN "fee_schedule_line"."is_active" IS 'Lifecycle: 0 once retired.';
COMMENT ON COLUMN "fee_schedule_line"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "fee_schedule_line"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "fee_schedule_line"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "fee_schedule_line"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "fee_schedule_line"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "fee_schedule_line"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "fee_schedule_line"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "fee_schedule_line"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "fee_schedule_line"."source" IS 'Where the row came from.';
COMMENT ON COLUMN "fee_schedule_line"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "contract_rate" IS 'What a payer has agreed to allow per unit. Effective-dated.';
COMMENT ON COLUMN "contract_rate"."contract_rate_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "contract_rate"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "contract_rate"."practice_id" IS 'Whose contract.';
COMMENT ON COLUMN "contract_rate"."payer_id" IS 'Whose contract.';
COMMENT ON COLUMN "contract_rate"."payer_contract_id" IS 'The contract this rate belongs to.';
COMMENT ON COLUMN "contract_rate"."cpt_code_id" IS 'The procedure.';
COMMENT ON COLUMN "contract_rate"."allowed_per_unit" IS 'The allowed dollars per unit.';
COMMENT ON COLUMN "contract_rate"."effective_from" IS 'When the rate applies from.';
COMMENT ON COLUMN "contract_rate"."rate_source" IS 'Contract, payer_fee_schedule, medicare_schedule, learned: a learned estimate is never presented as the contract.';
COMMENT ON COLUMN "contract_rate"."is_inferred" IS '1 when we estimated the rate.';
COMMENT ON COLUMN "contract_rate"."effective_to" IS 'Blank while open. 9999-12-31 while open, so range joins need no NULL handling.';
COMMENT ON COLUMN "contract_rate"."modifier_id" IS 'Modifier-dependent rates.';
COMMENT ON COLUMN "contract_rate"."rate_setting" IS 'Facility or non-facility.';
COMMENT ON COLUMN "contract_rate"."contract_number" IS 'Kept for loads that only send a number; the contract is payer_contract_id.';
COMMENT ON COLUMN "contract_rate"."rate_basis" IS 'Fixed, percent of Medicare, percent of billed, per diem.';
COMMENT ON COLUMN "contract_rate"."lesser_of_billed" IS 'Payer pays the lesser of billed and allowed.';
COMMENT ON COLUMN "contract_rate"."confidence" IS 'For learned rates: reliability.';
COMMENT ON COLUMN "contract_rate"."sample_size" IS 'For learned rates: lines used.';
COMMENT ON COLUMN "contract_rate"."plan_type" IS 'Plan-specific rates.';
COMMENT ON COLUMN "contract_rate"."provider_id" IS 'Provider-specific rates.';
COMMENT ON COLUMN "contract_rate"."specialty_id" IS 'Specialty-specific rates.';
COMMENT ON COLUMN "contract_rate"."multi_procedure_reduction_pct" IS 'Multiple-procedure reduction.';
COMMENT ON COLUMN "contract_rate"."dispute_days" IS 'Dispute window.';
COMMENT ON COLUMN "contract_rate"."is_active" IS 'Lifecycle: 0 once retired.';
COMMENT ON COLUMN "contract_rate"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "contract_rate"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "contract_rate"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "contract_rate"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "contract_rate"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "contract_rate"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "contract_rate"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "contract_rate"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "contract_rate"."source" IS 'Where the row came from.';
COMMENT ON COLUMN "contract_rate"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "adjustment_reason" IS 'A payer adjustment or denial reason code (CARC). Effective-dated.';
COMMENT ON COLUMN "adjustment_reason"."adjustment_reason_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "adjustment_reason"."tenant_id" IS 'Blank on the shared national row; set only on a tenant override row (for example a client''s own CARC classification or holidays). Lookups take the tenant row first, then the shared row.';
COMMENT ON COLUMN "adjustment_reason"."carc_code" IS 'The reason code.';
COMMENT ON COLUMN "adjustment_reason"."effective_from" IS 'The list changes during the year.';
COMMENT ON COLUMN "adjustment_reason"."effective_to" IS 'End of validity. 9999-12-31 while open, so range joins need no NULL handling.';
COMMENT ON COLUMN "adjustment_reason"."reason_class" IS 'Denial, contractual, patient_responsibility, other_adjustment, informational. A PR group always means patient responsibility.';
COMMENT ON COLUMN "adjustment_reason"."short_label" IS 'Our own words.';
COMMENT ON COLUMN "adjustment_reason"."reason_category" IS 'Eligibility, authorization, coding, documentation, timely filing, duplicate, coordination of benefits, bundling, technical.';
COMMENT ON COLUMN "adjustment_reason"."suggested_action" IS 'Fix and resubmit, appeal, write-off review, bill patient, informational. A proposal only.';
COMMENT ON COLUMN "adjustment_reason"."owner_role" IS 'Billing, coding, front desk, provider, patient.';
COMMENT ON COLUMN "adjustment_reason"."upstream_stage" IS 'Which journey stage could have caught it.';
COMMENT ON COLUMN "adjustment_reason"."is_appealable" IS 'Default.';
COMMENT ON COLUMN "adjustment_reason"."is_technical" IS 'Default.';
COMMENT ON COLUMN "adjustment_reason"."is_preventable_default" IS 'Default.';
COMMENT ON COLUMN "adjustment_reason"."typical_group" IS 'Usual group code.';
COMMENT ON COLUMN "adjustment_reason"."is_unrecognized" IS 'Flagged placeholder for an unknown code.';
COMMENT ON COLUMN "adjustment_reason"."is_active" IS 'Lifecycle: 0 once retired.';
COMMENT ON COLUMN "adjustment_reason"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "adjustment_reason"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "adjustment_reason"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "adjustment_reason"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "adjustment_reason"."source" IS 'Where the row came from.';
COMMENT ON COLUMN "adjustment_reason"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "remark_code" IS 'A remittance remark (RARC). Effective-dated.';
COMMENT ON COLUMN "remark_code"."remark_code_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "remark_code"."tenant_id" IS 'Blank on the shared national row; set only on a tenant override row (for example a client''s own CARC classification or holidays). Lookups take the tenant row first, then the shared row.';
COMMENT ON COLUMN "remark_code"."rarc_code" IS 'The remark code.';
COMMENT ON COLUMN "remark_code"."effective_from" IS 'The list is updated regularly.';
COMMENT ON COLUMN "remark_code"."effective_to" IS 'End of validity. 9999-12-31 while open, so range joins need no NULL handling.';
COMMENT ON COLUMN "remark_code"."code_qualifier" IS 'Which code list.';
COMMENT ON COLUMN "remark_code"."short_label" IS 'Our own words.';
COMMENT ON COLUMN "remark_code"."remark_type" IS 'Alert, informational, supplemental, action required.';
COMMENT ON COLUMN "remark_code"."suggests_action" IS 'Documentation needed, correct and resubmit, appeal, none. A proposal only.';
COMMENT ON COLUMN "remark_code"."documents_needed" IS 'Which records the remark implies.';
COMMENT ON COLUMN "remark_code"."related_reason_code" IS 'Common pairing with a reason.';
COMMENT ON COLUMN "remark_code"."is_unrecognized" IS 'Flagged placeholder.';
COMMENT ON COLUMN "remark_code"."is_active" IS 'Lifecycle: 0 once retired.';
COMMENT ON COLUMN "remark_code"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "remark_code"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "remark_code"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "remark_code"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "remark_code"."source" IS 'Where the row came from.';
COMMENT ON COLUMN "remark_code"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "practice_settings" IS 'One row per setting, effective-dated. Tenant-wide default overridable per practice.';
COMMENT ON COLUMN "practice_settings"."practice_settings_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "practice_settings"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "practice_settings"."practice_id" IS 'Blank means the client-wide default.';
COMMENT ON COLUMN "practice_settings"."setting_key" IS 'The setting.';
COMMENT ON COLUMN "practice_settings"."setting_value" IS 'Its value.';
COMMENT ON COLUMN "practice_settings"."value_type" IS 'Number, days, percent, text, list.';
COMMENT ON COLUMN "practice_settings"."effective_from" IS 'History of changes.';
COMMENT ON COLUMN "practice_settings"."effective_to" IS 'Blank while current. 9999-12-31 while open, so range joins need no NULL handling.';
COMMENT ON COLUMN "practice_settings"."set_by_role" IS 'Who set it.';
COMMENT ON COLUMN "practice_settings"."approved_by_staff_id" IS 'Pseudonymous approver for changes that affect reporting. Holds the staff_id of the pseudonymous person.';
COMMENT ON COLUMN "practice_settings"."is_active" IS 'Lifecycle: 0 once retired.';
COMMENT ON COLUMN "practice_settings"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "practice_settings"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "practice_settings"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "practice_settings"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "practice_settings"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "practice_settings"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "practice_settings"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "practice_settings"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "practice_settings"."source" IS 'Where the row came from.';
COMMENT ON COLUMN "practice_settings"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "payer_rule" IS 'One version of one rule: an authorization requirement, a bundling pair, a medical-necessity pair, a unit limit, a payer claim edit, a learned denial pattern or an agent detection rule, with the dates it applied.';
COMMENT ON COLUMN "payer_rule"."payer_rule_id" IS 'Stable ID of the record: the same on every version. The primary key is (payer_rule_id, version). Every link from another table uses payer_rule_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.';
COMMENT ON COLUMN "payer_rule"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "payer_rule"."payer_rule_number" IS 'The payer''s own policy or rule number, when one exists. Restricted.';
COMMENT ON COLUMN "payer_rule"."rule_code" IS 'Stable key shared by every version of the rule. Decision details and findings quote it as rule_code.';
COMMENT ON COLUMN "payer_rule"."rule_family" IS 'Kind of rule: authorization, bundling, medical_necessity, unit_limit, modifier, timely_filing, attachment, payer_edit, enrollment, multiple_procedure, learned_denial, detection.';
COMMENT ON COLUMN "payer_rule"."rule_action" IS 'What happens when the rule applies: require_auth, deny_pair, require_modifier, require_diagnosis, cap_units, require_attachment, flag_denial_risk, detect.';
COMMENT ON COLUMN "payer_rule"."rule_source_code" IS 'Where the rule comes from, as a code: payer_manual, contract, ncci, mue, lcd, learned, practice, scout. Never free text.';
COMMENT ON COLUMN "payer_rule"."rule_source_ref" IS 'Document, section or table number inside that source, as a code, so the rule can be checked again.';
COMMENT ON COLUMN "payer_rule"."payer_id" IS 'Payer the rule applies to. Blank means every payer (CMS pairs, detection rules).';
COMMENT ON COLUMN "payer_rule"."plan_type" IS 'Plan type the rule applies to (HMO, PPO, Medicare Advantage ...).';
COMMENT ON COLUMN "payer_rule"."place_of_service_id" IS 'Place of service the rule applies to.';
COMMENT ON COLUMN "payer_rule"."practice_id" IS 'Set when the rule row is a practice-specific switch or override. Blank means the rule is for all practices.';
COMMENT ON COLUMN "payer_rule"."cpt_code_id" IS 'Procedure code the rule is about, or the first code of a range.';
COMMENT ON COLUMN "payer_rule"."cpt_code_to_id" IS 'Last code of a range, when the payer lists a range.';
COMMENT ON COLUMN "payer_rule"."paired_cpt_code_id" IS 'Second code of a bundling pair.';
COMMENT ON COLUMN "payer_rule"."modifier_id" IS 'Modifier that is required, accepted or that lifts a bundling pair.';
COMMENT ON COLUMN "payer_rule"."diagnosis_code_id" IS 'Diagnosis in a medical-necessity pair.';
COMMENT ON COLUMN "payer_rule"."adjustment_reason_id" IS 'Denial reason (CARC) of a learned denial pattern.';
COMMENT ON COLUMN "payer_rule"."edit_field_code" IS 'Claim field a payer edit looks at (a code such as rendering_npi).';
COMMENT ON COLUMN "payer_rule"."requirement_code" IS 'What the payer wants in that field: required, forbidden, must_match.';
COMMENT ON COLUMN "payer_rule"."unit_limit" IS 'Most units allowed for the code.';
COMMENT ON COLUMN "payer_rule"."unit_limit_basis" IS 'Per line, per day or per date of service. Same values as cpt_code.unit_limit_basis.';
COMMENT ON COLUMN "payer_rule"."evidence_claim_count" IS 'Learned rules: claim lines seen for this payer, code and reason when the pattern was learned. Rates are computed, not stored.';
COMMENT ON COLUMN "payer_rule"."evidence_denied_count" IS 'Learned rules: how many of those lines were denied with this reason.';
COMMENT ON COLUMN "payer_rule"."evidence_denied_amount" IS 'Learned rules: billed amount of the denied lines; ranks the rule by money.';
COMMENT ON COLUMN "payer_rule"."evidence_from_date" IS 'Learned rules: first date of service in the evidence window.';
COMMENT ON COLUMN "payer_rule"."evidence_to_date" IS 'Learned rules: last date of service in the evidence window.';
COMMENT ON COLUMN "payer_rule"."owner_role" IS 'Team that fixes a failure of this rule: registration, authorization, coding, billing.';
COMMENT ON COLUMN "payer_rule"."severity" IS 'Block or warn when the rule fails.';
COMMENT ON COLUMN "payer_rule"."is_enabled" IS 'Switch. A disabled rule is skipped and the skip is logged.';
COMMENT ON COLUMN "payer_rule"."is_synthetic" IS '1 for a placeholder rule used for demos or tests; kept out of real results.';
COMMENT ON COLUMN "payer_rule"."approval_status" IS 'proposed, approved, rejected or retired. Only approved rows take effect.';
COMMENT ON COLUMN "payer_rule"."approved_by_staff_id" IS 'Pseudonymous approver of a learned or practice rule. Never a name.';
COMMENT ON COLUMN "payer_rule"."approved_date" IS 'Date of approval.';
COMMENT ON COLUMN "payer_rule"."last_confirmed_date" IS 'Last date someone checked the rule against its source. Old confirmation lowers trust.';
COMMENT ON COLUMN "payer_rule"."effective_from" IS 'First date of service the rule version applies to.';
COMMENT ON COLUMN "payer_rule"."effective_to" IS 'Last date of service it applies to. Blank while open. 9999-12-31 while open, so range joins need no NULL handling.';
COMMENT ON COLUMN "payer_rule"."retire_reason_code" IS 'Why the rule ended: superseded, payer_changed, wrong, low_hit_rate.';
COMMENT ON COLUMN "payer_rule"."version" IS '1 for the first row; higher for each change.';
COMMENT ON COLUMN "payer_rule"."is_current" IS '1 on the latest version. Counts use current rows only.';
COMMENT ON COLUMN "payer_rule"."previous_payer_rule_id" IS 'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.';
COMMENT ON COLUMN "payer_rule"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "payer_rule"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "payer_rule"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "payer_rule"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "payer_rule"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "payer_rule"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "payer_rule"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "payer_rule"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "payer_rule"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "payer_rule"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "calendar" IS 'One date, with whether it is a business day or a holiday.';
COMMENT ON COLUMN "calendar"."calendar_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "calendar"."tenant_id" IS 'Blank on the shared national row; set only on a tenant override row (for example a client''s own CARC classification or holidays). Lookups take the tenant row first, then the shared row.';
COMMENT ON COLUMN "calendar"."practice_id" IS 'Set when a practice closes on a day the tenant does not.';
COMMENT ON COLUMN "calendar"."calendar_date" IS 'The date.';
COMMENT ON COLUMN "calendar"."is_business_day" IS '1 when the practice and payers work that day.';
COMMENT ON COLUMN "calendar"."is_holiday" IS '1 on a holiday.';
COMMENT ON COLUMN "calendar"."holiday_code" IS 'Code of the holiday (NEW_YEAR, THANKSGIVING).';
COMMENT ON COLUMN "calendar"."business_day_number" IS 'Running count of business days, so lag in business days is one subtraction.';
COMMENT ON COLUMN "calendar"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "calendar"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "calendar"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "calendar"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "calendar"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "calendar"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "payer_identifier" IS 'One ID a payer is known by in one channel (claims, remittances, eligibility, a given clearinghouse).';
COMMENT ON COLUMN "payer_identifier"."payer_identifier_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "payer_identifier"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "payer_identifier"."payer_id" IS 'The payer.';
COMMENT ON COLUMN "payer_identifier"."identifier_value" IS 'The payer ID as used in that channel.';
COMMENT ON COLUMN "payer_identifier"."identifier_type" IS 'claim_837, era_835, eligibility_270, status_276, auth_278, attachment_275, portal.';
COMMENT ON COLUMN "payer_identifier"."clearinghouse_code" IS 'Clearinghouse that uses this ID. Blank: all.';
COMMENT ON COLUMN "payer_identifier"."effective_from" IS 'First day the ID is valid.';
COMMENT ON COLUMN "payer_identifier"."effective_to" IS 'Last day. 9999-12-31 while open.';
COMMENT ON COLUMN "payer_identifier"."is_active" IS 'Lifecycle: 0 once retired.';
COMMENT ON COLUMN "payer_identifier"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "payer_identifier"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "payer_identifier"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "payer_identifier"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "payer_identifier"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "payer_identifier"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "payer_identifier"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "payer_identifier"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "payer_identifier"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "payer_identifier"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "payer_plan" IS 'One plan or product a payer sells (an HMO, a Medicare Advantage plan ...).';
COMMENT ON COLUMN "payer_plan"."payer_plan_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "payer_plan"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "payer_plan"."payer_id" IS 'The payer.';
COMMENT ON COLUMN "payer_plan"."plan_code" IS 'The payer''s plan or product code.';
COMMENT ON COLUMN "payer_plan"."plan_name" IS 'Display.';
COMMENT ON COLUMN "payer_plan"."plan_type" IS 'Same values as coverage.plan_type.';
COMMENT ON COLUMN "payer_plan"."product_line" IS 'commercial, medicare_advantage, medicaid_managed, exchange.';
COMMENT ON COLUMN "payer_plan"."requires_referral" IS 'Plan needs a referral.';
COMMENT ON COLUMN "payer_plan"."filing_days" IS 'Overrides payer.filing_days when set.';
COMMENT ON COLUMN "payer_plan"."appeal_days" IS 'Overrides payer.appeal_days when set.';
COMMENT ON COLUMN "payer_plan"."state" IS 'State the plan is sold in.';
COMMENT ON COLUMN "payer_plan"."effective_from" IS 'First day.';
COMMENT ON COLUMN "payer_plan"."effective_to" IS '9999-12-31 while open.';
COMMENT ON COLUMN "payer_plan"."is_active" IS 'Lifecycle: 0 once retired.';
COMMENT ON COLUMN "payer_plan"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "payer_plan"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "payer_plan"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "payer_plan"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "payer_plan"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "payer_plan"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "payer_plan"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "payer_plan"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "payer_plan"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "payer_plan"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "payer_contract" IS 'One contract between a practice and a payer (or plan), per version.';
COMMENT ON COLUMN "payer_contract"."payer_contract_id" IS 'Stable ID of the record: the same on every version. The primary key is (payer_contract_id, version). Every link from another table uses payer_contract_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.';
COMMENT ON COLUMN "payer_contract"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "payer_contract"."practice_id" IS 'Contracting practice.';
COMMENT ON COLUMN "payer_contract"."payer_id" IS 'The payer.';
COMMENT ON COLUMN "payer_contract"."payer_plan_id" IS 'When the contract covers one plan only.';
COMMENT ON COLUMN "payer_contract"."contract_number" IS 'Contract reference.';
COMMENT ON COLUMN "payer_contract"."contract_status" IS 'draft, active, expired, terminated.';
COMMENT ON COLUMN "payer_contract"."effective_from" IS 'Start.';
COMMENT ON COLUMN "payer_contract"."effective_to" IS '9999-12-31 while open.';
COMMENT ON COLUMN "payer_contract"."filing_days" IS 'Overrides payer.filing_days.';
COMMENT ON COLUMN "payer_contract"."corrected_claim_days" IS 'Overrides payer.corrected_claim_days.';
COMMENT ON COLUMN "payer_contract"."appeal_days" IS 'Overrides payer.appeal_days.';
COMMENT ON COLUMN "payer_contract"."lesser_of_billed" IS 'Payer pays the lesser of billed and allowed.';
COMMENT ON COLUMN "payer_contract"."default_rate_basis" IS 'fixed, pct_of_medicare, pct_of_billed, per_diem.';
COMMENT ON COLUMN "payer_contract"."default_pct_of_medicare" IS 'For pct_of_medicare contracts.';
COMMENT ON COLUMN "payer_contract"."escalator_pct" IS 'Annual increase.';
COMMENT ON COLUMN "payer_contract"."renewal_notice_days" IS 'Notice needed before renewal.';
COMMENT ON COLUMN "payer_contract"."document_hash" IS 'Hash of the signed contract file.';
COMMENT ON COLUMN "payer_contract"."version" IS '1 for the first row; higher for each change.';
COMMENT ON COLUMN "payer_contract"."is_current" IS '1 on the latest version. Counts use current rows only.';
COMMENT ON COLUMN "payer_contract"."created_at" IS 'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.';
COMMENT ON COLUMN "payer_contract"."created_by_staff_id" IS 'Who created it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "payer_contract"."modified_at" IS 'When the record was last changed in the source system. On versioned tables, the change that produced this version.';
COMMENT ON COLUMN "payer_contract"."modified_by_staff_id" IS 'Who last changed it in the source system (pseudonymous staff_id).';
COMMENT ON COLUMN "payer_contract"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "payer_contract"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "payer_contract"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "payer_contract"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "payer_contract"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "payer_contract"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "claim_status_code" IS 'One X12 claim status category code (STC01-1) or status code (STC01-2), effective-dated.';
COMMENT ON COLUMN "claim_status_code"."claim_status_code_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "claim_status_code"."tenant_id" IS 'Blank on the shared national row; set only on a tenant override row.';
COMMENT ON COLUMN "claim_status_code"."code_set" IS 'category (STC01-1) or status (STC01-2).';
COMMENT ON COLUMN "claim_status_code"."code" IS 'The code (A0-A8, F0-F4, P0-P5, R0-R16, E0-E4 ... or a status number).';
COMMENT ON COLUMN "claim_status_code"."short_label" IS 'Short description.';
COMMENT ON COLUMN "claim_status_code"."status_group" IS 'acknowledged, rejected, pended, finalized, request, error.';
COMMENT ON COLUMN "claim_status_code"."is_rejection" IS '1 for A3, A6, A7, A8 and similar.';
COMMENT ON COLUMN "claim_status_code"."effective_from" IS 'First day.';
COMMENT ON COLUMN "claim_status_code"."effective_to" IS '9999-12-31 while open.';
COMMENT ON COLUMN "claim_status_code"."is_unrecognized" IS '1 on a placeholder for a code seen but not in the list.';
COMMENT ON COLUMN "claim_status_code"."is_active" IS 'Lifecycle.';
COMMENT ON COLUMN "claim_status_code"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "claim_status_code"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "claim_status_code"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "claim_status_code"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "claim_status_code"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "claim_status_code"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "ndc_code" IS 'One National Drug Code (11-digit, 5-4-2), with its HCPCS crosswalk and billing unit.';
COMMENT ON COLUMN "ndc_code"."ndc_code_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "ndc_code"."tenant_id" IS 'Blank on the shared national row; set only on a tenant override row.';
COMMENT ON COLUMN "ndc_code"."ndc_11" IS 'NDC in 5-4-2 format without dashes.';
COMMENT ON COLUMN "ndc_code"."product_label" IS 'Drug name and strength.';
COMMENT ON COLUMN "ndc_code"."hcpcs_cpt_code_id" IS 'HCPCS code it bills under.';
COMMENT ON COLUMN "ndc_code"."billing_unit" IS 'UN, ML, GR, F2.';
COMMENT ON COLUMN "ndc_code"."package_quantity" IS 'Units in the package.';
COMMENT ON COLUMN "ndc_code"."hcpcs_units_per_package" IS 'HCPCS billing units per package (crosswalk bill units).';
COMMENT ON COLUMN "ndc_code"."effective_from" IS 'First day.';
COMMENT ON COLUMN "ndc_code"."effective_to" IS '9999-12-31 while open.';
COMMENT ON COLUMN "ndc_code"."is_unrecognized" IS '1 on a placeholder for a code seen but not in the list.';
COMMENT ON COLUMN "ndc_code"."is_active" IS 'Lifecycle.';
COMMENT ON COLUMN "ndc_code"."load_batch_id" IS 'The load that wrote the row: lineage, and rollback of a bad load.';
COMMENT ON COLUMN "ndc_code"."source_record_hash" IS 'Hash of the source record''s fields; an unchanged hash means no new version on the next load.';
COMMENT ON COLUMN "ndc_code"."is_source_deleted" IS '1 when the record was deleted in the source system. The row is kept and left out of counts.';
COMMENT ON COLUMN "ndc_code"."source_deleted_at" IS 'When the deletion was detected.';
COMMENT ON COLUMN "ndc_code"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "ndc_code"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "tenant" IS 'One client organisation.';
COMMENT ON COLUMN "tenant"."tenant_id" IS 'Identity of the client organisation. Every table''s tenant_id holds this value.';
COMMENT ON COLUMN "tenant"."tenant_code" IS 'Short code for the client.';
COMMENT ON COLUMN "tenant"."tenant_name" IS 'Display.';
COMMENT ON COLUMN "tenant"."tenant_status" IS 'onboarding, active, suspended, offboarded.';
COMMENT ON COLUMN "tenant"."baa_signed_date" IS 'Date the business associate agreement was signed. No data loads before it.';
COMMENT ON COLUMN "tenant"."salt_key_ref" IS 'Name of the key-vault secret holding the per-client hashing salt. Never the salt itself. The salt keeps patients from matching across clients, by design.';
COMMENT ON COLUMN "tenant"."data_region" IS 'Where the client''s data is stored.';
COMMENT ON COLUMN "tenant"."go_live_date" IS 'First production load.';
COMMENT ON COLUMN "tenant"."retention_years" IS 'How long rows are kept after offboarding rules apply.';
COMMENT ON COLUMN "tenant"."offboard_date" IS 'Date the client left; deletion clock starts.';
COMMENT ON COLUMN "tenant"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "tenant"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "data_feed" IS 'One row per feed a client provides (or does not): which canonical table it fills, from where, how often, how complete.';
COMMENT ON COLUMN "data_feed"."data_feed_id" IS 'Stable ID of the record: the same on every version. The primary key is (data_feed_id, version). Every link from another table uses data_feed_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.';
COMMENT ON COLUMN "data_feed"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "data_feed"."table_name" IS 'The canonical table the feed fills.';
COMMENT ON COLUMN "data_feed"."feed_name" IS 'Plain name, e.g. ''PM claims export''.';
COMMENT ON COLUMN "data_feed"."source_system" IS 'Scheduler, ehr, pm, clearinghouse, payer_portal, manual, public_list.';
COMMENT ON COLUMN "data_feed"."feed_status" IS 'Active, paused, failed, not_provided.';
COMMENT ON COLUMN "data_feed"."fallback_level" IS '0 = primary source; 1 and up = the fallback step in use (see each table''s ladder).';
COMMENT ON COLUMN "data_feed"."practice_id" IS 'Blank = whole client.';
COMMENT ON COLUMN "data_feed"."source_kind" IS 'Api, hl7, file_drop, database_view, upload, public.';
COMMENT ON COLUMN "data_feed"."load_frequency" IS 'Realtime, hourly, daily, weekly, monthly, one_time.';
COMMENT ON COLUMN "data_feed"."first_data_date" IS 'Earliest business date loaded.';
COMMENT ON COLUMN "data_feed"."last_data_date" IS 'Latest business date loaded.';
COMMENT ON COLUMN "data_feed"."last_load_at" IS 'Last successful load.';
COMMENT ON COLUMN "data_feed"."rows_loaded" IS 'Rows loaded to date.';
COMMENT ON COLUMN "data_feed"."completeness_pct" IS 'Loaded versus a control total at the source.';
COMMENT ON COLUMN "data_feed"."freshness_hours" IS 'Hours since the last load.';
COMMENT ON COLUMN "data_feed"."reliability_default" IS 'Confidence of rows from this feed (1.0 primary; lower for rebuilt).';
COMMENT ON COLUMN "data_feed"."expected_row_count" IS 'Control total.';
COMMENT ON COLUMN "data_feed"."version" IS '1 for the first row; higher for each change.';
COMMENT ON COLUMN "data_feed"."is_current" IS '1 on the latest version. Counts use current rows only.';
COMMENT ON COLUMN "data_feed"."previous_data_feed_id" IS 'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.';
COMMENT ON COLUMN "data_feed"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "data_feed"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "edi_file" IS 'One X12 file received or sent.';
COMMENT ON COLUMN "edi_file"."edi_file_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "edi_file"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "edi_file"."data_feed_id" IS 'The feed it belongs to.';
COMMENT ON COLUMN "edi_file"."load_batch_id" IS 'The load that parsed it.';
COMMENT ON COLUMN "edi_file"."transaction_set" IS '837, 835, 999, 277, 270, 271, 278, 275.';
COMMENT ON COLUMN "edi_file"."direction" IS 'I inbound, O outbound.';
COMMENT ON COLUMN "edi_file"."interchange_control_number" IS 'ISA13.';
COMMENT ON COLUMN "edi_file"."group_control_number" IS 'GS06.';
COMMENT ON COLUMN "edi_file"."clearinghouse_code" IS 'Which clearinghouse.';
COMMENT ON COLUMN "edi_file"."file_hash" IS 'SHA-256 of the file; detects duplicates.';
COMMENT ON COLUMN "edi_file"."file_name_hash" IS 'Hash of the file name, never the name.';
COMMENT ON COLUMN "edi_file"."received_at" IS 'When it arrived or was sent.';
COMMENT ON COLUMN "edi_file"."transaction_count" IS 'ST/SE sets in the file.';
COMMENT ON COLUMN "edi_file"."file_status" IS 'received, parsed, partial, failed, reprocessed.';
COMMENT ON COLUMN "edi_file"."parse_error_count" IS 'Sets that failed to parse.';
COMMENT ON COLUMN "edi_file"."replaced_by_edi_file_id" IS 'The corrected file that replaced it.';
COMMENT ON COLUMN "edi_file"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "edi_file"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "load_batch" IS 'One run of the loader for one feed.';
COMMENT ON COLUMN "load_batch"."load_batch_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "load_batch"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "load_batch"."data_feed_id" IS 'The feed loaded.';
COMMENT ON COLUMN "load_batch"."started_at" IS 'Start.';
COMMENT ON COLUMN "load_batch"."ended_at" IS 'End. Blank while running.';
COMMENT ON COLUMN "load_batch"."batch_status" IS 'running, succeeded, partial, failed, rolled_back.';
COMMENT ON COLUMN "load_batch"."rows_read" IS 'Rows read from the source.';
COMMENT ON COLUMN "load_batch"."rows_inserted" IS 'New rows or versions.';
COMMENT ON COLUMN "load_batch"."rows_unchanged" IS 'Skipped because source_record_hash was unchanged.';
COMMENT ON COLUMN "load_batch"."rows_rejected" IS 'Failed validation.';
COMMENT ON COLUMN "load_batch"."source_watermark" IS 'Highest source timestamp or file sequence loaded; the next run starts after it.';
COMMENT ON COLUMN "load_batch"."code_version" IS 'Loader version.';
COMMENT ON COLUMN "load_batch"."rolled_back_at" IS 'When rolled back.';
COMMENT ON COLUMN "load_batch"."error_summary" IS 'Error class, never data.';
COMMENT ON COLUMN "load_batch"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "load_batch"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "data_quality_result" IS 'One data-quality rule evaluated on one load.';
COMMENT ON COLUMN "data_quality_result"."data_quality_result_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "data_quality_result"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "data_quality_result"."load_batch_id" IS 'The load checked.';
COMMENT ON COLUMN "data_quality_result"."dq_rule_code" IS 'The rule (for example claim_total_equals_lines).';
COMMENT ON COLUMN "data_quality_result"."table_name" IS 'Table checked.';
COMMENT ON COLUMN "data_quality_result"."column_name" IS 'Column, when the rule is about one.';
COMMENT ON COLUMN "data_quality_result"."severity" IS 'block, warn, info.';
COMMENT ON COLUMN "data_quality_result"."rows_checked" IS 'Rows evaluated.';
COMMENT ON COLUMN "data_quality_result"."rows_failed" IS 'Rows that failed.';
COMMENT ON COLUMN "data_quality_result"."sample_ref" IS 'Pointer to failed row IDs, never values.';
COMMENT ON COLUMN "data_quality_result"."run_at" IS 'When run.';
COMMENT ON COLUMN "data_quality_result"."dq_status" IS 'open, accepted, fixed.';
COMMENT ON COLUMN "data_quality_result"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "data_quality_result"."loaded_at" IS 'When the row was loaded.';
COMMENT ON TABLE "access_audit" IS 'One access to data: who or what read or exported which table, and whether restricted columns were touched.';
COMMENT ON COLUMN "access_audit"."access_audit_id" IS 'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.';
COMMENT ON COLUMN "access_audit"."tenant_id" IS 'The client organisation the row belongs to.';
COMMENT ON COLUMN "access_audit"."accessed_at" IS 'When.';
COMMENT ON COLUMN "access_audit"."actor_type" IS 'staff, agent, service, support.';
COMMENT ON COLUMN "access_audit"."staff_id" IS 'The person.';
COMMENT ON COLUMN "access_audit"."agent_run_id" IS 'The agent run.';
COMMENT ON COLUMN "access_audit"."action" IS 'view, query, export, unmask.';
COMMENT ON COLUMN "access_audit"."table_name" IS 'Table read.';
COMMENT ON COLUMN "access_audit"."row_count" IS 'Rows returned.';
COMMENT ON COLUMN "access_audit"."touched_restricted" IS '1 if any restricted column was read.';
COMMENT ON COLUMN "access_audit"."purpose_code" IS 'operations, support, audit, analytics.';
COMMENT ON COLUMN "access_audit"."query_hash" IS 'Hash of the query text.';
COMMENT ON COLUMN "access_audit"."source" IS 'Where the row came from: feed, API, PM export, rebuilt from another record.';
COMMENT ON COLUMN "access_audit"."loaded_at" IS 'When the row was loaded.';
