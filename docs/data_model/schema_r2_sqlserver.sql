-- KrisnnAI R2 (SQL Server). Generated from docs/data_model/r2_model.json by tools/data_model/build_r2_sql.py. Do not edit by hand.
SET NOCOUNT ON;

CREATE TABLE [appointment] (
    [appointment_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [appointment_number] VARCHAR(50) NOT NULL,
    [practice_id] INT NOT NULL,
    [patient_id] BIGINT NOT NULL,
    [appointment_date] DATE NOT NULL,
    [appointment_status] VARCHAR(20) NOT NULL,
    [provider_id] INT NULL,
    [payer_id] INT NULL,
    [coverage_id] BIGINT NULL,
    [facility_id] INT NULL,
    [start_time] TIME(0) NULL,
    [booked_date] DATE NULL,
    [appointment_type] VARCHAR(20) NULL,
    [booked_via] VARCHAR(20) NULL,
    [referring_provider_id] INT NULL,
    [referral_id] BIGINT NULL,
    [version] SMALLINT NOT NULL,
    [is_current] BIT NOT NULL,
    [previous_appointment_id] BIGINT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_appointment] PRIMARY KEY ([appointment_id], [version])
);
GO
CREATE TABLE [appointment_status_log] (
    [appointment_status_log_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [appointment_id] BIGINT NOT NULL,
    [from_status] VARCHAR(20) NULL,
    [to_status] VARCHAR(20) NOT NULL,
    [status_changed_at] DATETIME2(0) NOT NULL,
    [changed_by_staff_id] INT NULL,
    [change_channel] VARCHAR(15) NULL,
    [reason_code] VARCHAR(30) NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_appointment_status_log] PRIMARY KEY ([appointment_status_log_id])
);
GO
CREATE TABLE [referral] (
    [referral_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [referral_number] VARCHAR(50) NOT NULL,
    [practice_id] INT NULL,
    [patient_id] BIGINT NOT NULL,
    [coverage_id] BIGINT NULL,
    [payer_id] INT NULL,
    [referring_provider_id] INT NOT NULL,
    [referred_to_provider_id] INT NULL,
    [specialty_id] INT NULL,
    [referral_status] VARCHAR(15) NOT NULL,
    [request_date] DATE NULL,
    [received_date] DATE NULL,
    [valid_from] DATE NULL,
    [valid_to] DATE NULL,
    [visits_allowed] SMALLINT NULL,
    [visits_used] SMALLINT NULL,
    [diagnosis_code_id] INT NULL,
    [cpt_code_id] INT NULL,
    [authorization_id] BIGINT NULL,
    [document_id] BIGINT NULL,
    [version] SMALLINT NOT NULL,
    [is_current] BIT NOT NULL,
    [previous_referral_id] BIGINT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_referral] PRIMARY KEY ([referral_id], [version])
);
GO
CREATE TABLE [appointment_line] (
    [appointment_line_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [appointment_id] BIGINT NOT NULL,
    [line_number] SMALLINT NOT NULL,
    [practice_id] INT NULL,
    [patient_id] BIGINT NULL,
    [payer_id] INT NULL,
    [provider_id] INT NULL,
    [specialty_id] INT NULL,
    [planned_cpt_code_id] INT NULL,
    [is_inferred] BIT NOT NULL,
    [planned_units] DECIMAL(7,2) NULL,
    [expected_charge] DECIMAL(12,2) NULL,
    [expected_allowed] DECIMAL(12,2) NULL,
    [auth_required] VARCHAR(10) NULL,
    [authorization_id] BIGINT NULL,
    [planned_diagnosis_code_id] INT NULL,
    [planned_provider_id] INT NULL,
    [room_or_equipment] VARCHAR(50) NULL,
    [duration_minutes] SMALLINT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_appointment_line] PRIMARY KEY ([appointment_line_id])
);
GO
CREATE TABLE [appointment_slot] (
    [appointment_slot_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [practice_id] INT NOT NULL,
    [provider_id] INT NOT NULL,
    [slot_date] DATE NOT NULL,
    [start_time] TIME(0) NOT NULL,
    [duration_minutes] SMALLINT NOT NULL,
    [slot_status] VARCHAR(10) NOT NULL,
    [slot_number] VARCHAR(50) NULL,
    [facility_id] INT NULL,
    [specialty_id] INT NULL,
    [slot_type] VARCHAR(15) NULL,
    [appointment_id] BIGINT NULL,
    [created_date] DATE NULL,
    [room_or_resource] VARCHAR(50) NULL,
    [is_overbook] BIT NULL,
    [version] SMALLINT NOT NULL,
    [is_current] BIT NOT NULL,
    [previous_appointment_slot_id] BIGINT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_appointment_slot] PRIMARY KEY ([appointment_slot_id], [version])
);
GO
CREATE TABLE [eligibility_check] (
    [eligibility_check_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [trace_number] VARCHAR(30) NOT NULL,
    [check_sequence] SMALLINT NOT NULL,
    [appointment_id] BIGINT NULL,
    [coverage_id] BIGINT NOT NULL,
    [patient_id] BIGINT NULL,
    [payer_id] INT NULL,
    [practice_id] INT NULL,
    [is_secondary] BIT NULL,
    [check_date] DATE NOT NULL,
    [check_ts] DATETIME2(0) NULL,
    [service_date] DATE NOT NULL,
    [service_type_code] VARCHAR(5) NULL,
    [is_active] BIT NULL,
    [is_aaa_reject] BIT NOT NULL,
    [aaa_reason_code] VARCHAR(5) NULL,
    [plan_begin_date] DATE NULL,
    [plan_end_date] DATE NULL,
    [copay_amount] DECIMAL(12,2) NULL,
    [coinsurance_pct] DECIMAL(5,4) NULL,
    [coverage_level] VARCHAR(20) NULL,
    [network_indicator] CHAR(1) NULL,
    [deductible_remaining] DECIMAL(12,2) NULL,
    [deductible_total] DECIMAL(12,2) NULL,
    [oop_max] DECIMAL(12,2) NULL,
    [oop_remaining] DECIMAL(12,2) NULL,
    [other_payer_id] INT NULL,
    [auth_required_hint] BIT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_eligibility_check] PRIMARY KEY ([eligibility_check_id])
);
GO
CREATE TABLE [patient_estimate] (
    [patient_estimate_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [estimate_number] VARCHAR(50) NULL,
    [patient_id] BIGINT NOT NULL,
    [appointment_id] BIGINT NULL,
    [coverage_id] BIGINT NULL,
    [estimate_type] VARCHAR(20) NOT NULL,
    [estimate_date] DATE NOT NULL,
    [service_date] DATE NULL,
    [estimated_total] DECIMAL(12,2) NOT NULL,
    [estimated_patient_amount] DECIMAL(12,2) NOT NULL,
    [delivered_channel] VARCHAR(10) NULL,
    [delivered_date] DATE NULL,
    [actual_billed_amount] DECIMAL(12,2) NULL,
    [exceeds_gfe_by_400] BIT NULL,
    [practice_id] INT NULL,
    [version] SMALLINT NOT NULL,
    [is_current] BIT NOT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_patient_estimate] PRIMARY KEY ([patient_estimate_id], [version])
);
GO
CREATE TABLE [eligibility_benefit] (
    [eligibility_benefit_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [eligibility_check_id] BIGINT NOT NULL,
    [benefit_sequence] SMALLINT NOT NULL,
    [eligibility_code] VARCHAR(2) NOT NULL,
    [coverage_level] VARCHAR(20) NULL,
    [service_type_code] VARCHAR(3) NULL,
    [insurance_type_code] VARCHAR(3) NULL,
    [plan_description] VARCHAR(50) NULL,
    [time_period_code] VARCHAR(2) NULL,
    [benefit_amount] DECIMAL(12,2) NULL,
    [benefit_pct] DECIMAL(5,4) NULL,
    [quantity_qualifier] VARCHAR(2) NULL,
    [quantity] DECIMAL(9,2) NULL,
    [auth_required] VARCHAR(10) NULL,
    [network_indicator] CHAR(1) NULL,
    [cpt_code_id] INT NULL,
    [patient_id] BIGINT NULL,
    [payer_id] INT NULL,
    [practice_id] INT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_eligibility_benefit] PRIMARY KEY ([eligibility_benefit_id])
);
GO
CREATE TABLE [patient_estimate_line] (
    [patient_estimate_line_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [patient_estimate_id] BIGINT NOT NULL,
    [line_number] SMALLINT NOT NULL,
    [cpt_code_id] INT NOT NULL,
    [modifier_id] INT NULL,
    [diagnosis_code_id] INT NULL,
    [provider_id] INT NULL,
    [facility_id] INT NULL,
    [is_co_provider_item] BIT NULL,
    [units] DECIMAL(9,2) NOT NULL,
    [expected_charge] DECIMAL(12,2) NOT NULL,
    [expected_patient_amount] DECIMAL(12,2) NULL,
    [appointment_line_id] BIGINT NULL,
    [billed_amount] DECIMAL(12,2) NULL,
    [practice_id] INT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_patient_estimate_line] PRIMARY KEY ([patient_estimate_line_id])
);
GO
CREATE TABLE [encounter] (
    [encounter_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [encounter_number] VARCHAR(50) NOT NULL,
    [practice_id] INT NOT NULL,
    [patient_id] BIGINT NOT NULL,
    [encounter_date] DATE NOT NULL,
    [rendering_provider_id] INT NOT NULL,
    [encounter_status] VARCHAR(20) NOT NULL,
    [appointment_id] BIGINT NULL,
    [payer_id] INT NULL,
    [coverage_id] BIGINT NULL,
    [facility_id] INT NULL,
    [place_of_service_id] INT NULL,
    [specialty_id] INT NULL,
    [encounter_type] VARCHAR(20) NULL,
    [visit_minutes] SMALLINT NULL,
    [note_status] VARCHAR(20) NULL,
    [note_signed_date] DATE NULL,
    [signature_lag_days] SMALLINT NULL,
    [elements_documented_count] TINYINT NULL,
    [charge_status] VARCHAR(20) NULL,
    [coding_status] VARCHAR(20) NULL,
    [principal_diagnosis_code_id] INT NULL,
    [authorization_id] BIGINT NULL,
    [supervising_provider_id] INT NULL,
    [referring_provider_id] INT NULL,
    [referral_id] BIGINT NULL,
    [version] SMALLINT NOT NULL,
    [is_current] BIT NOT NULL,
    [previous_encounter_id] BIGINT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_encounter] PRIMARY KEY ([encounter_id], [version])
);
GO
CREATE TABLE [document] (
    [document_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [document_number] VARCHAR(50) NOT NULL,
    [practice_id] INT NULL,
    [patient_id] BIGINT NULL,
    [document_class] VARCHAR(20) NOT NULL,
    [document_type] VARCHAR(30) NOT NULL,
    [document_status] VARCHAR(20) NOT NULL,
    [encounter_id] BIGINT NULL,
    [authorization_id] BIGINT NULL,
    [claim_id] BIGINT NULL,
    [author_provider_id] INT NULL,
    [signer_role] VARCHAR(20) NULL,
    [document_date] DATE NULL,
    [signed_at] DATETIME2(0) NULL,
    [is_late_entry] BIT NULL,
    [is_addendum] BIT NULL,
    [addendum_of_document_id] BIGINT NULL,
    [is_locked] BIT NULL,
    [cosign_required] BIT NULL,
    [cosign_status] VARCHAR(10) NULL,
    [cosigned_at] DATETIME2(0) NULL,
    [expiry_date] DATE NULL,
    [minutes_documented] SMALLINT NULL,
    [hpi_component_count] TINYINT NULL,
    [ros_system_count] TINYINT NULL,
    [mdm_problem_level] VARCHAR(10) NULL,
    [mdm_data_level] VARCHAR(10) NULL,
    [mdm_risk_level] VARCHAR(10) NULL,
    [content_hash] BINARY(32) NULL,
    [page_count] SMALLINT NULL,
    [document_type_code] VARCHAR(20) NULL,
    [source_quality] VARCHAR(20) NULL,
    [version] SMALLINT NOT NULL,
    [is_current] BIT NOT NULL,
    [previous_document_id] BIGINT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_document] PRIMARY KEY ([document_id], [version])
);
GO
CREATE TABLE [clinical_order] (
    [clinical_order_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [order_number] VARCHAR(50) NOT NULL,
    [practice_id] INT NULL,
    [patient_id] BIGINT NULL,
    [encounter_id] BIGINT NULL,
    [encounter_line_id] BIGINT NULL,
    [ordering_provider_id] INT NULL,
    [order_type] VARCHAR(20) NOT NULL,
    [order_status] VARCHAR(15) NOT NULL,
    [order_date] DATE NULL,
    [signed_date] DATE NULL,
    [cpt_code_id] INT NULL,
    [diagnosis_code_id] INT NULL,
    [authorization_id] BIGINT NULL,
    [auth_required] VARCHAR(7) NULL,
    [document_id] BIGINT NULL,
    [result_status] VARCHAR(10) NULL,
    [result_received_date] DATE NULL,
    [result_document_id] BIGINT NULL,
    [version] SMALLINT NOT NULL,
    [is_current] BIT NOT NULL,
    [previous_clinical_order_id] BIGINT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_clinical_order] PRIMARY KEY ([clinical_order_id], [version])
);
GO
CREATE TABLE [encounter_line] (
    [encounter_line_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [encounter_id] BIGINT NOT NULL,
    [line_number] SMALLINT NOT NULL,
    [practice_id] INT NULL,
    [patient_id] BIGINT NULL,
    [payer_id] INT NULL,
    [provider_id] INT NULL,
    [specialty_id] INT NULL,
    [cpt_code_id] INT NOT NULL,
    [units] DECIMAL(7,2) NOT NULL,
    [service_date] DATE NULL,
    [rendering_provider_id] INT NULL,
    [diagnosis_1_id] INT NULL,
    [diagnosis_2_id] INT NULL,
    [diagnosis_3_id] INT NULL,
    [diagnosis_4_id] INT NULL,
    [modifier_1_id] INT NULL,
    [modifier_2_id] INT NULL,
    [modifier_3_id] INT NULL,
    [modifier_4_id] INT NULL,
    [laterality] CHAR(1) NULL,
    [procedure_documented] BIT NULL,
    [documented_level] TINYINT NULL,
    [time_minutes] SMALLINT NULL,
    [authorization_id] BIGINT NULL,
    [auth_required] VARCHAR(10) NULL,
    [line_status] VARCHAR(20) NULL,
    [expected_charge] DECIMAL(12,2) NULL,
    [place_of_service_id] INT NULL,
    [ordering_provider_id] INT NULL,
    [drug_code] VARCHAR(11) NULL,
    [ndc_code_id] INT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_encounter_line] PRIMARY KEY ([encounter_line_id])
);
GO
CREATE TABLE [encounter_diagnosis] (
    [encounter_diagnosis_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [encounter_id] BIGINT NOT NULL,
    [diagnosis_sequence] SMALLINT NOT NULL,
    [diagnosis_code_id] INT NOT NULL,
    [is_principal] BIT NOT NULL,
    [diagnosis_role] VARCHAR(15) NULL,
    [practice_id] INT NULL,
    [patient_id] BIGINT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_encounter_diagnosis] PRIMARY KEY ([encounter_diagnosis_id])
);
GO
CREATE TABLE [document_element] (
    [document_element_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [document_id] BIGINT NOT NULL,
    [element_code] VARCHAR(30) NOT NULL,
    [is_present] BIT NOT NULL,
    [practice_id] INT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_document_element] PRIMARY KEY ([document_element_id])
);
GO
CREATE TABLE [bill] (
    [bill_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [bill_number] VARCHAR(50) NOT NULL,
    [practice_id] INT NOT NULL,
    [patient_id] BIGINT NOT NULL,
    [encounter_id] BIGINT NOT NULL,
    [service_date] DATE NOT NULL,
    [charge_entered_date] DATE NOT NULL,
    [bill_status] VARCHAR(20) NOT NULL,
    [bill_type] VARCHAR(20) NOT NULL,
    [total_billed] DECIMAL(12,2) NOT NULL,
    [billing_provider_id] INT NULL,
    [rendering_provider_id] INT NULL,
    [specialty_id] INT NULL,
    [payer_id] INT NULL,
    [coverage_id] BIGINT NULL,
    [facility_id] INT NULL,
    [place_of_service_id] INT NULL,
    [ready_to_bill_date] DATE NULL,
    [hold_reason] VARCHAR(30) NULL,
    [hold_date] DATE NULL,
    [last_charge_date] DATE NULL,
    [claims_created] SMALLINT NULL,
    [latest_claim_status] VARCHAR(20) NULL,
    [first_claim_submitted_date] DATE NULL,
    [expected_allowed] DECIMAL(12,2) NULL,
    [entered_by_role] VARCHAR(30) NULL,
    [no_charge_amount] DECIMAL(12,2) NULL,
    [patient_statement_flag] BIT NULL,
    [version] SMALLINT NOT NULL,
    [is_current] BIT NOT NULL,
    [previous_bill_id] BIGINT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_bill] PRIMARY KEY ([bill_id], [version])
);
GO
CREATE TABLE [claim] (
    [claim_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [claim_number] VARCHAR(50) NOT NULL,
    [practice_id] INT NOT NULL,
    [payer_id] INT NOT NULL,
    [patient_id] BIGINT NOT NULL,
    [billing_provider_id] INT NOT NULL,
    [service_date_from] DATE NOT NULL,
    [service_date_to] DATE NOT NULL,
    [submitted_date] DATE NOT NULL,
    [total_charge] DECIMAL(12,2) NOT NULL,
    [claim_status] VARCHAR(20) NOT NULL,
    [rendering_provider_id] INT NULL,
    [supervising_provider_id] INT NULL,
    [facility_id] INT NULL,
    [place_of_service_id] INT NULL,
    [specialty_id] INT NULL,
    [coverage_id] BIGINT NULL,
    [claim_sequence] VARCHAR(10) NULL,
    [primary_claim_id] BIGINT NULL,
    [other_payer_paid_amount] DECIMAL(12,2) NULL,
    [claim_filing_indicator] VARCHAR(2) NULL,
    [frequency_code] CHAR(1) NULL,
    [accept_assignment] CHAR(1) NULL,
    [benefits_assigned] CHAR(1) NULL,
    [release_of_info] CHAR(1) NULL,
    [payer_claim_number] VARCHAR(50) NULL,
    [original_payer_claim_number] VARCHAR(50) NULL,
    [bill_id] BIGINT NULL,
    [encounter_id] BIGINT NULL,
    [principal_diagnosis_code_id] INT NULL,
    [prior_auth_number] VARCHAR(50) NULL,
    [authorization_id] BIGINT NULL,
    [paid_amount] DECIMAL(12,2) NULL,
    [patient_responsibility] DECIMAL(12,2) NULL,
    [adjusted_amount] DECIMAL(12,2) NULL,
    [denied_amount] DECIMAL(12,2) NULL,
    [balance] DECIMAL(12,2) NULL,
    [last_payment_date] DATE NULL,
    [last_status_date] DATE NULL,
    [claim_type] VARCHAR(15) NULL,
    [accident_related] VARCHAR(10) NULL,
    [referring_provider_id] INT NULL,
    [referral_id] BIGINT NULL,
    [referral_number] VARCHAR(50) NULL,
    [batch_control_number] VARCHAR(20) NULL,
    [edi_file_id] BIGINT NULL,
    [signature_on_file] CHAR(1) NULL,
    [onset_date] DATE NULL,
    [late_filing_reason] VARCHAR(30) NULL,
    [delay_reason_code] VARCHAR(2) NULL,
    [version] SMALLINT NOT NULL,
    [is_current] BIT NOT NULL,
    [previous_claim_id] BIGINT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_claim] PRIMARY KEY ([claim_id], [version])
);
GO
CREATE TABLE [claim_attachment] (
    [claim_attachment_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [claim_attachment_number] VARCHAR(50) NOT NULL,
    [practice_id] INT NULL,
    [patient_id] BIGINT NULL,
    [claim_id] BIGINT NOT NULL,
    [payer_id] INT NOT NULL,
    [request_type] VARCHAR(30) NOT NULL,
    [payer_reference_number] VARCHAR(50) NULL,
    [requesting_unit] VARCHAR(30) NULL,
    [request_received_date] DATE NULL,
    [request_channel] VARCHAR(15) NULL,
    [due_date] DATE NULL,
    [extended_due_date] DATE NULL,
    [request_text_hash] BINARY(32) NULL,
    [response_status] VARCHAR(20) NOT NULL,
    [response_sent_date] DATE NULL,
    [response_method] VARCHAR(15) NULL,
    [response_tracking_number] VARCHAR(50) NULL,
    [page_count] SMALLINT NULL,
    [payer_acknowledgement] VARCHAR(15) NULL,
    [attachment_report_type_code] VARCHAR(10) NULL,
    [attachment_transmission_code] VARCHAR(5) NULL,
    [attachment_control_number] VARCHAR(50) NULL,
    [document_id] BIGINT NULL,
    [version] SMALLINT NOT NULL,
    [is_current] BIT NOT NULL,
    [previous_claim_attachment_id] BIGINT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_claim_attachment] PRIMARY KEY ([claim_attachment_id], [version])
);
GO
CREATE TABLE [bill_line] (
    [bill_line_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [bill_id] BIGINT NOT NULL,
    [line_number] SMALLINT NOT NULL,
    [practice_id] INT NULL,
    [patient_id] BIGINT NULL,
    [payer_id] INT NULL,
    [provider_id] INT NULL,
    [specialty_id] INT NULL,
    [cpt_code_id] INT NOT NULL,
    [units] DECIMAL(7,2) NOT NULL,
    [fee_per_unit] DECIMAL(12,2) NOT NULL,
    [billed_amount] DECIMAL(12,2) NOT NULL,
    [line_status] VARCHAR(20) NOT NULL,
    [service_date] DATE NULL,
    [modifier_1_id] INT NULL,
    [modifier_2_id] INT NULL,
    [modifier_3_id] INT NULL,
    [modifier_4_id] INT NULL,
    [diagnosis_1_id] INT NULL,
    [diagnosis_2_id] INT NULL,
    [diagnosis_3_id] INT NULL,
    [diagnosis_4_id] INT NULL,
    [rendering_provider_id] INT NULL,
    [encounter_line_id] BIGINT NULL,
    [charge_entered_date] DATE NULL,
    [cpt_as_entered_id] INT NULL,
    [code_changed] BIT NULL,
    [change_approved_by_staff_id] INT NULL,
    [fee_schedule_id] INT NULL,
    [expected_allowed] DECIMAL(12,2) NULL,
    [hold_reason] VARCHAR(30) NULL,
    [authorization_id] BIGINT NULL,
    [claims_on] SMALLINT NULL,
    [latest_claim_line_status] VARCHAR(20) NULL,
    [claimed_date] DATE NULL,
    [drug_code] VARCHAR(11) NULL,
    [ndc_code_id] INT NULL,
    [drug_units] DECIMAL(12,3) NULL,
    [drug_unit_measure] CHAR(2) NULL,
    [place_of_service_id] INT NULL,
    [entered_by_role] VARCHAR(30) NULL,
    [no_charge_amount] DECIMAL(12,2) NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_bill_line] PRIMARY KEY ([bill_line_id])
);
GO
CREATE TABLE [claim_line] (
    [claim_line_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [claim_id] BIGINT NOT NULL,
    [line_number] SMALLINT NOT NULL,
    [practice_id] INT NULL,
    [payer_id] INT NULL,
    [patient_id] BIGINT NULL,
    [billing_provider_id] INT NULL,
    [specialty_id] INT NULL,
    [cpt_code_id] INT NOT NULL,
    [units] DECIMAL(7,2) NOT NULL,
    [charge_amount] DECIMAL(12,2) NOT NULL,
    [line_status] VARCHAR(20) NOT NULL,
    [paid_amount] DECIMAL(12,2) NULL,
    [service_date] DATE NULL,
    [service_date_to] DATE NULL,
    [place_of_service_id] INT NULL,
    [modifier_1_id] INT NULL,
    [modifier_2_id] INT NULL,
    [modifier_3_id] INT NULL,
    [modifier_4_id] INT NULL,
    [diagnosis_pointers] VARCHAR(4) NULL,
    [primary_diagnosis_code_id] INT NULL,
    [rendering_provider_id] INT NULL,
    [ordering_provider_id] INT NULL,
    [supervising_provider_id] INT NULL,
    [allowed_amount] DECIMAL(12,2) NULL,
    [patient_responsibility] DECIMAL(12,2) NULL,
    [contractual_adjustment] DECIMAL(12,2) NULL,
    [denied_amount] DECIMAL(12,2) NULL,
    [primary_denial_reason_id] INT NULL,
    [expected_allowed] DECIMAL(12,2) NULL,
    [bill_line_id] BIGINT NULL,
    [line_control_number] VARCHAR(30) NULL,
    [drug_code] VARCHAR(11) NULL,
    [ndc_code_id] INT NULL,
    [drug_units] DECIMAL(12,3) NULL,
    [drug_unit_measure] CHAR(2) NULL,
    [line_flags] VARCHAR(30) NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_claim_line] PRIMARY KEY ([claim_line_id])
);
GO
CREATE TABLE [claim_status_history] (
    [claim_status_history_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [claim_id] BIGINT NOT NULL,
    [claim_line_id] BIGINT NULL,
    [event_type] VARCHAR(20) NOT NULL,
    [event_date] DATE NOT NULL,
    [status_after] VARCHAR(20) NOT NULL,
    [practice_id] INT NOT NULL,
    [payer_id] INT NOT NULL,
    [patient_id] BIGINT NOT NULL,
    [event_ts] DATETIME2(0) NULL,
    [response_sequence] SMALLINT NULL,
    [status_category] VARCHAR(10) NULL,
    [status_category_code_id] INT NULL,
    [status_code] VARCHAR(10) NULL,
    [status_code_id] INT NULL,
    [is_rejection] BIT NULL,
    [rejection_reason] VARCHAR(20) NULL,
    [rejection_category] VARCHAR(30) NULL,
    [is_technical] BIT NULL,
    [owner_role] VARCHAR(20) NULL,
    [fix_by_date] DATE NULL,
    [channel] VARCHAR(20) NULL,
    [payer_claim_number] VARCHAR(50) NULL,
    [billing_provider_id] INT NULL,
    [specialty_id] INT NULL,
    [reported_paid_amount] DECIMAL(12,2) NULL,
    [acked_control_number] VARCHAR(30) NULL,
    [clearinghouse_batch_number] VARCHAR(30) NULL,
    [edi_file_id] BIGINT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_claim_status_history] PRIMARY KEY ([claim_status_history_id])
);
GO
CREATE TABLE [claim_diagnosis] (
    [claim_diagnosis_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [claim_id] BIGINT NOT NULL,
    [diagnosis_sequence] TINYINT NOT NULL,
    [diagnosis_code_id] INT NOT NULL,
    [is_principal] BIT NOT NULL,
    [poa_indicator] CHAR(1) NULL,
    [practice_id] INT NULL,
    [payer_id] INT NULL,
    [patient_id] BIGINT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_claim_diagnosis] PRIMARY KEY ([claim_diagnosis_id])
);
GO
CREATE TABLE [claim_attachment_document] (
    [claim_attachment_document_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [claim_attachment_id] BIGINT NOT NULL,
    [document_type] VARCHAR(30) NOT NULL,
    [document_id] BIGINT NULL,
    [item_status] VARCHAR(12) NOT NULL,
    [page_count] SMALLINT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_claim_attachment_document] PRIMARY KEY ([claim_attachment_document_id])
);
GO
CREATE TABLE [claim_edit] (
    [claim_edit_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [claim_id] BIGINT NOT NULL,
    [claim_line_id] BIGINT NULL,
    [edit_source] VARCHAR(15) NOT NULL,
    [edit_code] VARCHAR(50) NOT NULL,
    [edit_category] VARCHAR(30) NULL,
    [severity] VARCHAR(10) NOT NULL,
    [edit_ts] DATETIME2(0) NOT NULL,
    [edit_status] VARCHAR(12) NOT NULL,
    [resolved_ts] DATETIME2(0) NULL,
    [resolved_by_staff_id] INT NULL,
    [fix_field_code] VARCHAR(40) NULL,
    [payer_rule_id] BIGINT NULL,
    [agent_decision_id] BIGINT NULL,
    [edi_file_id] BIGINT NULL,
    [practice_id] INT NULL,
    [payer_id] INT NULL,
    [patient_id] BIGINT NULL,
    [billing_provider_id] INT NULL,
    [cpt_code_id] INT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_claim_edit] PRIMARY KEY ([claim_edit_id])
);
GO
CREATE TABLE [ledger_entry] (
    [ledger_entry_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [transaction_number] VARCHAR(50) NOT NULL,
    [practice_id] INT NOT NULL,
    [patient_id] BIGINT NOT NULL,
    [bill_line_id] BIGINT NOT NULL,
    [transaction_type] VARCHAR(20) NOT NULL,
    [amount] DECIMAL(12,2) NOT NULL,
    [balance_effect] DECIMAL(12,2) NOT NULL,
    [transaction_date] DATE NOT NULL,
    [responsible_party] VARCHAR(10) NOT NULL,
    [from_party] VARCHAR(10) NULL,
    [to_party] VARCHAR(10) NULL,
    [to_payer_id] INT NULL,
    [claim_line_id] BIGINT NULL,
    [claim_id] BIGINT NULL,
    [transaction_subtype] VARCHAR(30) NULL,
    [posted_date] DATE NULL,
    [payer_id] INT NULL,
    [provider_id] INT NULL,
    [specialty_id] INT NULL,
    [cpt_code_id] INT NULL,
    [adjustment_reason_id] INT NULL,
    [group_code] CHAR(2) NULL,
    [payment_id] BIGINT NULL,
    [payment_method] VARCHAR(15) NULL,
    [payment_number] VARCHAR(50) NULL,
    [approved_by_staff_id] INT NULL,
    [approved_date] DATE NULL,
    [reverses_ledger_entry_id] BIGINT NULL,
    [is_reversal] BIT NULL,
    [batch_number] VARCHAR(30) NULL,
    [posted_by_role] VARCHAR(30) NULL,
    [refund_reason] VARCHAR(30) NULL,
    [remark_code_id] INT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_ledger_entry] PRIMARY KEY ([ledger_entry_id])
);
GO
CREATE TABLE [denial] (
    [denial_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [claim_id] BIGINT NOT NULL,
    [claim_line_id] BIGINT NOT NULL,
    [practice_id] INT NOT NULL,
    [patient_id] BIGINT NOT NULL,
    [payer_id] INT NOT NULL,
    [denial_date] DATE NOT NULL,
    [denied_amount] DECIMAL(12,2) NOT NULL,
    [adjustment_reason_id] INT NOT NULL,
    [denial_status] VARCHAR(25) NOT NULL,
    [ledger_entry_id] BIGINT NULL,
    [bill_line_id] BIGINT NULL,
    [group_code] CHAR(2) NULL,
    [reason_category] VARCHAR(30) NULL,
    [clock_start_date] DATE NULL,
    [appeal_deadline] DATE NULL,
    [root_cause] VARCHAR(30) NULL,
    [upstream_stage] VARCHAR(15) NULL,
    [is_preventable] BIT NULL,
    [is_technical] BIT NULL,
    [owner_role] VARCHAR(20) NULL,
    [resolved_date] DATE NULL,
    [outcome] VARCHAR(20) NULL,
    [recovered_amount] DECIMAL(12,2) NULL,
    [is_repeat] BIT NULL,
    [denial_count_on_line] SMALLINT NULL,
    [resubmitted_claim_id] BIGINT NULL,
    [cpt_code_id] INT NULL,
    [provider_id] INT NULL,
    [specialty_id] INT NULL,
    [is_claim_level] BIT NULL,
    [units_denied] DECIMAL(7,2) NULL,
    [authorization_id] BIGINT NULL,
    [version] SMALLINT NOT NULL,
    [is_current] BIT NOT NULL,
    [previous_denial_id] BIGINT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_denial] PRIMARY KEY ([denial_id], [version])
);
GO
CREATE TABLE [payment] (
    [payment_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [payment_number] VARCHAR(50) NOT NULL,
    [practice_id] INT NOT NULL,
    [payment_source] VARCHAR(10) NOT NULL,
    [payment_date] DATE NOT NULL,
    [payment_amount] DECIMAL(12,2) NOT NULL,
    [payment_method] VARCHAR(15) NOT NULL,
    [payer_id] INT NULL,
    [patient_id] BIGINT NULL,
    [guarantor_id] BIGINT NULL,
    [appointment_id] BIGINT NULL,
    [collection_point] VARCHAR(15) NULL,
    [payment_type] VARCHAR(10) NULL,
    [received_date] DATE NULL,
    [posted_date] DATE NULL,
    [credit_debit] CHAR(1) NULL,
    [has_remittance] BIT NULL,
    [edi_file_id] BIGINT NULL,
    [claim_count] SMALLINT NULL,
    [posted_amount] DECIMAL(12,2) NULL,
    [unapplied_amount] DECIMAL(12,2) NULL,
    [plb_amount] DECIMAL(12,2) NULL,
    [reconciles] BIT NULL,
    [is_void] BIT NULL,
    [payee_provider_id] INT NULL,
    [version] SMALLINT NOT NULL,
    [is_current] BIT NOT NULL,
    [previous_payment_id] BIGINT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_payment] PRIMARY KEY ([payment_id], [version])
);
GO
CREATE TABLE [payment_plan] (
    [payment_plan_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [payment_plan_number] VARCHAR(50) NULL,
    [patient_id] BIGINT NOT NULL,
    [guarantor_id] BIGINT NULL,
    [plan_status] VARCHAR(10) NOT NULL,
    [start_date] DATE NOT NULL,
    [total_amount] DECIMAL(12,2) NOT NULL,
    [practice_id] INT NULL,
    [instalment_amount] DECIMAL(12,2) NULL,
    [instalment_count] SMALLINT NULL,
    [frequency] VARCHAR(10) NULL,
    [next_due_date] DATE NULL,
    [missed_instalments] SMALLINT NULL,
    [last_missed_date] DATE NULL,
    [autopay_enrolled] BIT NULL,
    [end_date] DATE NULL,
    [version] SMALLINT NOT NULL,
    [is_current] BIT NOT NULL,
    [previous_payment_plan_id] BIGINT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_payment_plan] PRIMARY KEY ([payment_plan_id], [version])
);
GO
CREATE TABLE [patient_contact_preference] (
    [patient_contact_preference_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [patient_id] BIGINT NOT NULL,
    [opt_out] BIT NOT NULL,
    [text_consent] BIT NOT NULL,
    [preferred_channel] VARCHAR(10) NULL,
    [quiet_hours_start] TINYINT NULL,
    [quiet_hours_end] TINYINT NULL,
    [contact_time_zone] VARCHAR(40) NULL,
    [address_status] VARCHAR(10) NULL,
    [has_phone] BIT NULL,
    [autodial_consent] BIT NULL,
    [consent_date] DATE NULL,
    [consent_source] VARCHAR(20) NULL,
    [consent_wording_version] VARCHAR(10) NULL,
    [opt_out_date] DATE NULL,
    [has_authorized_rep] BIT NULL,
    [guarantor_hash] BINARY(32) NULL,
    [guarantor_id] BIGINT NULL,
    [version] SMALLINT NOT NULL,
    [is_current] BIT NOT NULL,
    [previous_patient_contact_preference_id] BIGINT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_patient_contact_preference] PRIMARY KEY ([patient_contact_preference_id], [version])
);
GO
CREATE TABLE [denial_reason] (
    [denial_reason_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [denial_id] BIGINT NOT NULL,
    [detail_seq] SMALLINT NOT NULL,
    [detail_type] VARCHAR(10) NOT NULL,
    [adjustment_reason_id] INT NULL,
    [remark_code_id] INT NULL,
    [group_code] CHAR(2) NULL,
    [reason_amount] DECIMAL(12,2) NULL,
    [is_amount_allocated] BIT NULL,
    [reason_units] DECIMAL(7,2) NULL,
    [is_primary] BIT NULL,
    [reason_category] VARCHAR(30) NULL,
    [is_appealable] BIT NULL,
    [suggested_action] VARCHAR(25) NULL,
    [denial_date] DATE NULL,
    [practice_id] INT NULL,
    [payer_id] INT NULL,
    [cpt_code_id] INT NULL,
    [claim_line_id] BIGINT NULL,
    [provider_id] INT NULL,
    [specialty_id] INT NULL,
    [patient_id] BIGINT NULL,
    [payer_reason_code] VARCHAR(20) NULL,
    [remark_qualifier] VARCHAR(5) NULL,
    [documents_needed] VARCHAR(30) NULL,
    [reason_corrected] BIT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_denial_reason] PRIMARY KEY ([denial_reason_id])
);
GO
CREATE TABLE [ar_interval] (
    [ar_interval_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [bill_line_id] BIGINT NOT NULL,
    [period_start_date] DATE NOT NULL,
    [period_end_date] DATE NOT NULL,
    [period_type] VARCHAR(10) NOT NULL,
    [practice_id] INT NOT NULL,
    [patient_id] BIGINT NOT NULL,
    [guarantor_id] BIGINT NULL,
    [opening_balance] DECIMAL(12,2) NOT NULL,
    [charges] DECIMAL(12,2) NOT NULL,
    [payments] DECIMAL(12,2) NOT NULL,
    [adjustments] DECIMAL(12,2) NOT NULL,
    [write_offs] DECIMAL(12,2) NOT NULL,
    [refunds] DECIMAL(12,2) NOT NULL,
    [closing_balance] DECIMAL(12,2) NOT NULL,
    [payer_balance] DECIMAL(12,2) NOT NULL,
    [patient_balance] DECIMAL(12,2) NOT NULL,
    [payer_bucket] VARCHAR(10) NOT NULL,
    [patient_bucket] VARCHAR(10) NOT NULL,
    [aging_basis] VARCHAR(20) NOT NULL,
    [reconciles] BIT NOT NULL,
    [prior_period_ar_interval_id] BIGINT NULL,
    [payer_days] SMALLINT NULL,
    [patient_days] SMALLINT NULL,
    [payer_aging_date] DATE NULL,
    [patient_aging_date] DATE NULL,
    [unbilled_balance] DECIMAL(12,2) NULL,
    [payments_payer] DECIMAL(12,2) NULL,
    [payments_patient] DECIMAL(12,2) NULL,
    [adjustments_contractual] DECIMAL(12,2) NULL,
    [adjustments_denial] DECIMAL(12,2) NULL,
    [adjustments_other] DECIMAL(12,2) NULL,
    [transfers_to_patient] DECIMAL(12,2) NULL,
    [transfers_to_secondary] DECIMAL(12,2) NULL,
    [claim_id] BIGINT NULL,
    [claim_line_id] BIGINT NULL,
    [claim_status] VARCHAR(20) NULL,
    [payer_id] INT NULL,
    [open_denied_amount] DECIMAL(12,2) NULL,
    [is_in_denial] BIT NULL,
    [expected_collectible] DECIMAL(12,2) NULL,
    [last_payment_date] DATE NULL,
    [last_activity_date] DATE NULL,
    [last_statement_date] DATE NULL,
    [is_credit] BIT NULL,
    [ledger_balance] DECIMAL(12,2) NULL,
    [variance_amount] DECIMAL(12,2) NULL,
    [is_restated] BIT NULL,
    [period_status] VARCHAR(10) NULL,
    [provider_id] INT NULL,
    [specialty_id] INT NULL,
    [cpt_code_id] INT NULL,
    [facility_id] INT NULL,
    [service_date] DATE NULL,
    [collections_agency_flag] BIT NULL,
    [statement_count] SMALLINT NULL,
    [version] SMALLINT NOT NULL,
    [is_current] BIT NOT NULL,
    [previous_ar_interval_id] BIGINT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_ar_interval] PRIMARY KEY ([ar_interval_id], [version])
);
GO
CREATE TABLE [ar_snapshot] (
    [ar_snapshot_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [as_of_date] DATE NOT NULL,
    [snapshot_type] VARCHAR(10) NOT NULL,
    [bill_id] BIGINT NOT NULL,
    [balance_owner] VARCHAR(10) NOT NULL,
    [balance] DECIMAL(12,2) NOT NULL,
    [practice_id] INT NOT NULL,
    [patient_id] BIGINT NOT NULL,
    [guarantor_id] BIGINT NULL,
    [aging_date] DATE NOT NULL,
    [days_outstanding] SMALLINT NOT NULL,
    [aging_bucket] VARCHAR(10) NOT NULL,
    [aging_basis] VARCHAR(20) NOT NULL,
    [claim_id] BIGINT NULL,
    [payer_id] INT NULL,
    [claim_status] VARCHAR(20) NULL,
    [claim_sequence] VARCHAR(10) NULL,
    [submitted_date] DATE NULL,
    [expected_collectible] DECIMAL(12,2) NULL,
    [last_payment_date] DATE NULL,
    [last_activity_date] DATE NULL,
    [days_since_activity] SMALLINT NULL,
    [last_statement_date] DATE NULL,
    [open_denied_amount] DECIMAL(12,2) NULL,
    [is_in_denial] BIT NULL,
    [is_credit] BIT NULL,
    [overpayment_identified_date] DATE NULL,
    [refund_due_date] DATE NULL,
    [filing_deadline] DATE NULL,
    [provider_id] INT NULL,
    [specialty_id] INT NULL,
    [facility_id] INT NULL,
    [service_date] DATE NULL,
    [primary_cpt_code_id] INT NULL,
    [change_since_last_snapshot] DECIMAL(12,2) NULL,
    [collections_agency_flag] BIT NULL,
    [next_action_date] DATE NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_ar_snapshot] PRIMARY KEY ([ar_snapshot_id])
);
GO
CREATE TABLE [appeal] (
    [appeal_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [appeal_number] VARCHAR(50) NULL,
    [denial_id] BIGINT NOT NULL,
    [appeal_level] VARCHAR(15) NOT NULL,
    [appeal_status] VARCHAR(12) NOT NULL,
    [clock_start_date] DATE NOT NULL,
    [deadline_date] DATE NOT NULL,
    [claim_id] BIGINT NULL,
    [submitted_date] DATE NULL,
    [submission_channel] VARCHAR(10) NULL,
    [amount_disputed] DECIMAL(12,2) NULL,
    [evidence_count] SMALLINT NULL,
    [letter_hash] BINARY(32) NULL,
    [payer_reference] VARCHAR(50) NULL,
    [decision_date] DATE NULL,
    [payer_decision] VARCHAR(20) NULL,
    [is_overturned] BIT NULL,
    [recovered_amount] DECIMAL(12,2) NULL,
    [agent_decision_id] BIGINT NULL,
    [agent_approval_id] BIGINT NULL,
    [practice_id] INT NULL,
    [patient_id] BIGINT NULL,
    [payer_id] INT NULL,
    [version] SMALLINT NOT NULL,
    [is_current] BIT NOT NULL,
    [previous_appeal_id] BIGINT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_appeal] PRIMARY KEY ([appeal_id], [version])
);
GO
CREATE TABLE [patient_statement] (
    [patient_statement_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [statement_number] VARCHAR(50) NULL,
    [patient_id] BIGINT NOT NULL,
    [guarantor_id] BIGINT NOT NULL,
    [statement_date] DATE NOT NULL,
    [statement_amount] DECIMAL(12,2) NOT NULL,
    [channel] VARCHAR(10) NOT NULL,
    [statement_status] VARCHAR(12) NOT NULL,
    [practice_id] INT NULL,
    [bill_id] BIGINT NULL,
    [claim_id] BIGINT NULL,
    [due_date] DATE NULL,
    [sent_at] DATETIME2(0) NULL,
    [status_date] DATE NULL,
    [dunning_level] TINYINT NULL,
    [validation_notice_date] DATE NULL,
    [dispute_window_end_date] DATE NULL,
    [collection_placement_id] BIGINT NULL,
    [payment_plan_id] BIGINT NULL,
    [version] SMALLINT NOT NULL,
    [is_current] BIT NOT NULL,
    [previous_patient_statement_id] BIGINT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_patient_statement] PRIMARY KEY ([patient_statement_id], [version])
);
GO
CREATE TABLE [payment_adjustment] (
    [payment_adjustment_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [payment_id] BIGINT NOT NULL,
    [adjustment_type] VARCHAR(15) NOT NULL,
    [amount] DECIMAL(12,2) NOT NULL,
    [adjustment_date] DATE NOT NULL,
    [plb_reason_code] VARCHAR(5) NULL,
    [practice_id] INT NULL,
    [payer_id] INT NULL,
    [payee_provider_id] INT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_payment_adjustment] PRIMARY KEY ([payment_adjustment_id])
);
GO
CREATE TABLE [remittance_claim] (
    [remittance_claim_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [payment_id] BIGINT NOT NULL,
    [claim_id] BIGINT NULL,
    [patient_control_number] VARCHAR(50) NOT NULL,
    [claim_status_code] VARCHAR(3) NOT NULL,
    [is_reversal] BIT NOT NULL,
    [charge_amount] DECIMAL(12,2) NOT NULL,
    [paid_amount] DECIMAL(12,2) NOT NULL,
    [patient_responsibility] DECIMAL(12,2) NULL,
    [claim_filing_indicator] VARCHAR(2) NULL,
    [payer_claim_number] VARCHAR(50) NULL,
    [claim_level_adjustment] DECIMAL(12,2) NULL,
    [remark_code_id] INT NULL,
    [is_crossover] BIT NULL,
    [crossover_payer_id] INT NULL,
    [match_method] VARCHAR(20) NULL,
    [payer_id] INT NULL,
    [practice_id] INT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_remittance_claim] PRIMARY KEY ([remittance_claim_id])
);
GO
CREATE TABLE [bank_deposit] (
    [bank_deposit_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [practice_id] INT NOT NULL,
    [deposit_date] DATE NOT NULL,
    [deposit_amount] DECIMAL(12,2) NOT NULL,
    [deposit_method] VARCHAR(15) NOT NULL,
    [trace_number] VARCHAR(50) NULL,
    [payer_id] INT NULL,
    [payment_id] BIGINT NULL,
    [match_status] VARCHAR(12) NOT NULL,
    [matched_date] DATE NULL,
    [variance_amount] DECIMAL(12,2) NULL,
    [bank_account_label] VARCHAR(30) NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_bank_deposit] PRIMARY KEY ([bank_deposit_id])
);
GO
CREATE TABLE [collection_placement] (
    [collection_placement_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [placement_number] VARCHAR(50) NULL,
    [guarantor_id] BIGINT NOT NULL,
    [patient_id] BIGINT NULL,
    [agency_code] VARCHAR(30) NOT NULL,
    [placement_type] VARCHAR(15) NOT NULL,
    [is_third_party] BIT NOT NULL,
    [placed_date] DATE NOT NULL,
    [placed_amount] DECIMAL(12,2) NOT NULL,
    [recovered_amount] DECIMAL(12,2) NULL,
    [agency_fee_amount] DECIMAL(12,2) NULL,
    [placement_status] VARCHAR(25) NOT NULL,
    [recall_date] DATE NULL,
    [recall_reason] VARCHAR(20) NULL,
    [closed_date] DATE NULL,
    [credit_reported] BIT NULL,
    [practice_id] INT NULL,
    [version] SMALLINT NOT NULL,
    [is_current] BIT NOT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_collection_placement] PRIMARY KEY ([collection_placement_id], [version])
);
GO
CREATE TABLE [agent_decision] (
    [agent_decision_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [agent_run_id] BIGINT NOT NULL,
    [agent_code] VARCHAR(5) NOT NULL,
    [decision_type] VARCHAR(30) NOT NULL,
    [entity_type] VARCHAR(20) NOT NULL,
    [entity_id] BIGINT NOT NULL,
    [outcome] VARCHAR(15) NOT NULL,
    [decided_at] DATETIME2(0) NOT NULL,
    [run_mode] VARCHAR(10) NOT NULL,
    [confidence] DECIMAL(5,4) NULL,
    [reason_summary] VARCHAR(300) NULL,
    [rules_checked] SMALLINT NULL,
    [rules_failed] SMALLINT NULL,
    [amount_at_stake] DECIMAL(12,2) NULL,
    [data_fallback_level] TINYINT NULL,
    [human_outcome] VARCHAR(15) NULL,
    [human_outcome_date] DATE NULL,
    [supersedes_decision_id] BIGINT NULL,
    [is_current] BIT NULL,
    [input_hash] BINARY(32) NULL,
    [practice_id] INT NULL,
    [patient_id] BIGINT NULL,
    [payer_id] INT NULL,
    [provider_id] INT NULL,
    [specialty_id] INT NULL,
    [appointment_id] BIGINT NULL,
    [encounter_id] BIGINT NULL,
    [bill_id] BIGINT NULL,
    [claim_id] BIGINT NULL,
    [denial_id] BIGINT NULL,
    [authorization_id] BIGINT NULL,
    [recheck_condition] VARCHAR(100) NULL,
    [recheck_result] VARCHAR(20) NULL,
    [prompt_hash] BINARY(32) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_agent_decision] PRIMARY KEY ([agent_decision_id])
);
GO
CREATE TABLE [agent_value] (
    [agent_value_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [agent_code] VARCHAR(5) NOT NULL,
    [value_stage] VARCHAR(10) NOT NULL,
    [amount] DECIMAL(12,2) NOT NULL,
    [signed_amount] DECIMAL(12,2) NOT NULL,
    [value_date] DATE NOT NULL,
    [entity_type] VARCHAR(20) NOT NULL,
    [entity_id] BIGINT NOT NULL,
    [agent_finding_id] BIGINT NULL,
    [agent_decision_id] BIGINT NULL,
    [practice_id] INT NULL,
    [claim_id] BIGINT NULL,
    [denial_id] BIGINT NULL,
    [payer_id] INT NULL,
    [provider_id] INT NULL,
    [specialty_id] INT NULL,
    [cpt_code_id] INT NULL,
    [ledger_entry_id] BIGINT NULL,
    [is_holdout] BIT NULL,
    [incremental_amount] DECIMAL(12,2) NULL,
    [value_kind] VARCHAR(30) NULL,
    [is_estimate] BIT NULL,
    [attribution_share] DECIMAL(5,4) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_agent_value] PRIMARY KEY ([agent_value_id])
);
GO
CREATE TABLE [agent_run] (
    [agent_run_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [agent_code] VARCHAR(5) NOT NULL,
    [agent_name] VARCHAR(40) NULL,
    [run_mode] VARCHAR(10) NOT NULL,
    [trigger_type] VARCHAR(15) NOT NULL,
    [started_at] DATETIME2(0) NOT NULL,
    [ended_at] DATETIME2(0) NULL,
    [run_status] VARCHAR(12) NOT NULL,
    [practice_id] INT NULL,
    [items_in] INT NULL,
    [decisions_made] INT NULL,
    [error_count] INT NULL,
    [error_summary] VARCHAR(200) NULL,
    [model_name] VARCHAR(40) NULL,
    [input_tokens] BIGINT NULL,
    [output_tokens] BIGINT NULL,
    [cost_amount] DECIMAL(12,4) NULL,
    [trigger_run_id] BIGINT NULL,
    [code_version] VARCHAR(30) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_agent_run] PRIMARY KEY ([agent_run_id])
);
GO
CREATE TABLE [agent_decision_check] (
    [agent_decision_check_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [agent_decision_id] BIGINT NOT NULL,
    [check_seq] SMALLINT NOT NULL,
    [rule_code] VARCHAR(40) NOT NULL,
    [check_result] VARCHAR(10) NOT NULL,
    [agent_code] VARCHAR(5) NULL,
    [rule_version] VARCHAR(20) NULL,
    [rule_source] VARCHAR(20) NULL,
    [severity] VARCHAR(10) NULL,
    [observed_value] VARCHAR(100) NULL,
    [expected_value] VARCHAR(100) NULL,
    [input_table] VARCHAR(40) NULL,
    [input_fallback_level] TINYINT NULL,
    [practice_id] INT NULL,
    [payer_id] INT NULL,
    [cpt_code_id] INT NULL,
    [evidence_ref] VARCHAR(100) NULL,
    [payer_rule_id] BIGINT NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_agent_decision_check] PRIMARY KEY ([agent_decision_check_id])
);
GO
CREATE TABLE [agent_finding] (
    [agent_finding_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [agent_run_id] BIGINT NOT NULL,
    [agent_code] VARCHAR(5) NOT NULL,
    [finding_type] VARCHAR(30) NOT NULL,
    [entity_type] VARCHAR(20) NOT NULL,
    [entity_id] BIGINT NOT NULL,
    [found_date] DATE NOT NULL,
    [finding_status] VARCHAR(12) NOT NULL,
    [amount_at_risk] DECIMAL(12,2) NULL,
    [amount_recovered] DECIMAL(12,2) NULL,
    [upstream_stage] VARCHAR(15) NULL,
    [is_preventable] BIT NULL,
    [severity] VARCHAR(10) NULL,
    [deadline_date] DATE NULL,
    [resolved_date] DATE NULL,
    [resolution] VARCHAR(20) NULL,
    [agent_decision_id] BIGINT NULL,
    [finding_hash] BINARY(32) NULL,
    [summary] VARCHAR(300) NULL,
    [practice_id] INT NULL,
    [patient_id] BIGINT NULL,
    [payer_id] INT NULL,
    [provider_id] INT NULL,
    [specialty_id] INT NULL,
    [appointment_id] BIGINT NULL,
    [encounter_id] BIGINT NULL,
    [bill_id] BIGINT NULL,
    [claim_id] BIGINT NULL,
    [denial_id] BIGINT NULL,
    [authorization_id] BIGINT NULL,
    [suggested_value] VARCHAR(100) NULL,
    [final_value] VARCHAR(100) NULL,
    [value_difference] DECIMAL(12,2) NULL,
    [is_compliance_risk] BIT NULL,
    [predicted_probability] DECIMAL(5,4) NULL,
    [predicted_reason_category] VARCHAR(30) NULL,
    [predicted_allowed_amount] DECIMAL(12,2) NULL,
    [predicted_patient_responsibility] DECIMAL(12,2) NULL,
    [version] SMALLINT NOT NULL,
    [is_current] BIT NOT NULL,
    [previous_agent_finding_id] BIGINT NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_agent_finding] PRIMARY KEY ([agent_finding_id], [version])
);
GO
CREATE TABLE [agent_task] (
    [agent_task_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [task_type] VARCHAR(30) NOT NULL,
    [owner_role] VARCHAR(20) NOT NULL,
    [task_status] VARCHAR(12) NOT NULL,
    [created_date] DATE NOT NULL,
    [agent_code] VARCHAR(5) NOT NULL,
    [entity_type] VARCHAR(20) NOT NULL,
    [entity_id] BIGINT NOT NULL,
    [agent_decision_id] BIGINT NULL,
    [agent_finding_id] BIGINT NULL,
    [priority] VARCHAR(8) NULL,
    [due_date] DATE NULL,
    [completed_date] DATE NULL,
    [assigned_to_staff_id] INT NULL,
    [amount_at_stake] DECIMAL(12,2) NULL,
    [outcome] VARCHAR(20) NULL,
    [title] VARCHAR(100) NULL,
    [practice_id] INT NULL,
    [patient_id] BIGINT NULL,
    [payer_id] INT NULL,
    [provider_id] INT NULL,
    [specialty_id] INT NULL,
    [appointment_id] BIGINT NULL,
    [encounter_id] BIGINT NULL,
    [bill_id] BIGINT NULL,
    [claim_id] BIGINT NULL,
    [denial_id] BIGINT NULL,
    [authorization_id] BIGINT NULL,
    [minutes_spent] INT NULL,
    [contact_channel] VARCHAR(30) NULL,
    [escalation_level] SMALLINT NULL,
    [reminder_count] SMALLINT NULL,
    [version] SMALLINT NOT NULL,
    [is_current] BIT NOT NULL,
    [previous_agent_task_id] BIGINT NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_agent_task] PRIMARY KEY ([agent_task_id], [version])
);
GO
CREATE TABLE [agent_approval] (
    [agent_approval_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [agent_decision_id] BIGINT NOT NULL,
    [approval_type] VARCHAR(25) NOT NULL,
    [approval_status] VARCHAR(10) NOT NULL,
    [approved_by_staff_id] INT NULL,
    [approver_role] VARCHAR(20) NOT NULL,
    [approval_date] DATE NOT NULL,
    [agent_task_id] BIGINT NULL,
    [amount_approved] DECIMAL(12,2) NULL,
    [limit_checked] BIT NULL,
    [reason_code] VARCHAR(20) NULL,
    [entity_type] VARCHAR(20) NULL,
    [entity_id] BIGINT NULL,
    [practice_id] INT NULL,
    [approval_ts] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_agent_approval] PRIMARY KEY ([agent_approval_id])
);
GO
CREATE TABLE [agent_writeback] (
    [agent_writeback_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [agent_decision_id] BIGINT NOT NULL,
    [target_system] VARCHAR(15) NOT NULL,
    [writeback_type] VARCHAR(30) NOT NULL,
    [send_status] VARCHAR(20) NOT NULL,
    [attempted_at] DATETIME2(0) NOT NULL,
    [agent_approval_id] BIGINT NULL,
    [agent_code] VARCHAR(5) NULL,
    [entity_type] VARCHAR(20) NULL,
    [entity_id] BIGINT NULL,
    [attempt_no] SMALLINT NULL,
    [response_code] VARCHAR(20) NULL,
    [response_at] DATETIME2(0) NULL,
    [external_ref] VARCHAR(50) NULL,
    [payload_hash] BINARY(32) NULL,
    [practice_id] INT NULL,
    [claim_id] BIGINT NULL,
    [appointment_id] BIGINT NULL,
    [version] SMALLINT NOT NULL,
    [is_current] BIT NOT NULL,
    [previous_agent_writeback_id] BIGINT NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_agent_writeback] PRIMARY KEY ([agent_writeback_id], [version])
);
GO
CREATE TABLE [agent_forecast] (
    [agent_forecast_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [forecast_type] VARCHAR(20) NOT NULL,
    [as_of_date] DATE NOT NULL,
    [target_start_date] DATE NOT NULL,
    [target_end_date] DATE NOT NULL,
    [expected_amount] DECIMAL(12,2) NOT NULL,
    [low_amount] DECIMAL(12,2) NULL,
    [high_amount] DECIMAL(12,2) NULL,
    [probability] DECIMAL(5,4) NULL,
    [claim_count] INT NULL,
    [practice_id] INT NULL,
    [payer_id] INT NULL,
    [entity_type] VARCHAR(20) NULL,
    [entity_id] BIGINT NULL,
    [actual_amount] DECIMAL(12,2) NULL,
    [actual_known_date] DATE NULL,
    [within_range] BIT NULL,
    [interval_level] DECIMAL(3,2) NULL,
    [model_name] VARCHAR(40) NULL,
    [code_version] VARCHAR(30) NULL,
    [version] SMALLINT NOT NULL,
    [is_current] BIT NOT NULL,
    [previous_agent_forecast_id] BIGINT NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_agent_forecast] PRIMARY KEY ([agent_forecast_id], [version])
);
GO
CREATE TABLE [patient] (
    [patient_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [patient_number_hash] BINARY(32) NOT NULL,
    [master_patient_hash] BINARY(32) NULL,
    [merged_into_patient_id] BIGINT NULL,
    [birth_year] SMALLINT NULL,
    [is_age_90_plus] BIT NULL,
    [sex] CHAR(1) NULL,
    [state] CHAR(2) NULL,
    [primary_practice_id] INT NULL,
    [first_seen_date] DATE NULL,
    [last_seen_date] DATE NULL,
    [primary_coverage_id] BIGINT NULL,
    [guarantor_id] BIGINT NULL,
    [is_self_pay] BIT NULL,
    [zip3] CHAR(3) NULL,
    [language] VARCHAR(20) NULL,
    [is_deceased] BIT NULL,
    [is_active] BIT NOT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_patient] PRIMARY KEY ([patient_id])
);
GO
CREATE TABLE [coverage] (
    [coverage_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [patient_id] BIGINT NOT NULL,
    [payer_id] INT NOT NULL,
    [payer_plan_id] INT NULL,
    [member_number_hash] BINARY(32) NOT NULL,
    [coverage_order] TINYINT NOT NULL,
    [effective_date] DATE NOT NULL,
    [termination_date] DATE NULL,
    [plan_type] VARCHAR(25) NULL,
    [plan_name] NVARCHAR(100) NULL,
    [group_number_hash] BINARY(32) NULL,
    [relationship_to_holder] VARCHAR(10) NULL,
    [last_verified_date] DATE NULL,
    [last_verified_status] VARCHAR(12) NULL,
    [requires_referral] BIT NULL,
    [pcp_provider_id] INT NULL,
    [copay_amount] DECIMAL(12,2) NULL,
    [coinsurance_pct] DECIMAL(5,4) NULL,
    [deductible_remaining] DECIMAL(12,2) NULL,
    [subscriber_hash] BINARY(32) NULL,
    [version] SMALLINT NOT NULL,
    [is_current] BIT NOT NULL,
    [previous_coverage_id] BIGINT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_coverage] PRIMARY KEY ([coverage_id], [version])
);
GO
CREATE TABLE [authorization] (
    [authorization_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [authorization_number] VARCHAR(50) NOT NULL,
    [patient_id] BIGINT NOT NULL,
    [payer_id] INT NOT NULL,
    [practice_id] INT NOT NULL,
    [authorization_status] VARCHAR(15) NOT NULL,
    [coverage_id] BIGINT NULL,
    [primary_cpt_code_id] INT NULL,
    [units_approved] INT NULL,
    [units_used] INT NULL,
    [valid_from] DATE NULL,
    [valid_to] DATE NULL,
    [request_date] DATE NULL,
    [decision_date] DATE NULL,
    [authorization_type] VARCHAR(15) NULL,
    [requesting_provider_id] INT NULL,
    [rendering_provider_id] INT NULL,
    [urgency] VARCHAR(10) NULL,
    [request_channel] VARCHAR(10) NULL,
    [decision_reason_code] VARCHAR(20) NULL,
    [diagnosis_code_id] INT NULL,
    [facility_id] INT NULL,
    [units_requested] INT NULL,
    [place_of_service_id] INT NULL,
    [version] SMALLINT NOT NULL,
    [is_current] BIT NOT NULL,
    [previous_authorization_id] BIGINT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_authorization] PRIMARY KEY ([authorization_id], [version])
);
GO
CREATE TABLE [authorization_line] (
    [authorization_line_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [authorization_id] BIGINT NOT NULL,
    [line_number] SMALLINT NOT NULL,
    [cpt_code_id] INT NOT NULL,
    [cpt_code_to_id] INT NULL,
    [modifier_id] INT NULL,
    [unit_type] VARCHAR(10) NULL,
    [units_requested] INT NULL,
    [units_approved] INT NULL,
    [units_used] INT NULL,
    [line_status] VARCHAR(15) NOT NULL,
    [valid_from] DATE NULL,
    [valid_to] DATE NULL,
    [practice_id] INT NULL,
    [patient_id] BIGINT NULL,
    [payer_id] INT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_authorization_line] PRIMARY KEY ([authorization_line_id])
);
GO
CREATE TABLE [guarantor] (
    [guarantor_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [guarantor_number] VARCHAR(50) NULL,
    [guarantor_hash] BINARY(32) NOT NULL,
    [guarantor_type] VARCHAR(15) NOT NULL,
    [practice_id] INT NULL,
    [state] CHAR(2) NULL,
    [zip3] CHAR(3) NULL,
    [account_status] VARCHAR(15) NOT NULL,
    [is_inferred] BIT NOT NULL,
    [has_portal_account] BIT NULL,
    [is_active] BIT NOT NULL,
    [version] SMALLINT NOT NULL,
    [is_current] BIT NOT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_guarantor] PRIMARY KEY ([guarantor_id], [version])
);
GO
CREATE TABLE [staff] (
    [staff_id] INT NOT NULL,
    [tenant_id] INT NOT NULL,
    [staff_number] VARCHAR(30) NOT NULL,
    [practice_id] INT NULL,
    [staff_role] VARCHAR(30) NOT NULL,
    [team] VARCHAR(15) NOT NULL,
    [weekly_hours] DECIMAL(4,1) NULL,
    [start_date] DATE NULL,
    [end_date] DATE NULL,
    [is_active] BIT NOT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_staff] PRIMARY KEY ([staff_id])
);
GO
CREATE TABLE [enrollment] (
    [enrollment_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [enrollment_number] VARCHAR(50) NULL,
    [provider_id] INT NOT NULL,
    [payer_id] INT NULL,
    [practice_id] INT NULL,
    [facility_id] INT NULL,
    [event_type] VARCHAR(15) NOT NULL,
    [event_date] DATE NOT NULL,
    [enrollment_status] VARCHAR(15) NULL,
    [enrollment_type] VARCHAR(15) NULL,
    [plan_program_code] VARCHAR(15) NULL,
    [submitted_date] DATE NULL,
    [effective_date] DATE NULL,
    [expires_date] DATE NULL,
    [revalidation_due_date] DATE NULL,
    [last_revalidated_date] DATE NULL,
    [payer_provider_number] VARCHAR(30) NULL,
    [application_number] VARCHAR(30) NULL,
    [end_reason_code] VARCHAR(20) NULL,
    [screening_source] VARCHAR(10) NULL,
    [screening_result] VARCHAR(10) NULL,
    [screening_list_date] DATE NULL,
    [exclusion_type] VARCHAR(15) NULL,
    [excluded_date] DATE NULL,
    [reinstated_date] DATE NULL,
    [match_method] VARCHAR(10) NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_enrollment] PRIMARY KEY ([enrollment_id])
);
GO
CREATE TABLE [provider_identifier] (
    [provider_identifier_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [provider_id] INT NOT NULL,
    [identifier_type] VARCHAR(20) NOT NULL,
    [identifier_value] VARCHAR(50) NOT NULL,
    [issuing_state] CHAR(2) NULL,
    [payer_id] INT NULL,
    [effective_from] DATE NOT NULL,
    [effective_to] DATE NOT NULL,
    [verified_date] DATE NULL,
    [is_active] BIT NOT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_provider_identifier] PRIMARY KEY ([provider_identifier_id])
);
GO
CREATE TABLE [provider_practice] (
    [provider_practice_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [provider_id] INT NOT NULL,
    [practice_id] INT NOT NULL,
    [facility_id] INT NULL,
    [affiliation_role] VARCHAR(15) NULL,
    [is_primary] BIT NULL,
    [start_date] DATE NOT NULL,
    [end_date] DATE NOT NULL,
    [fte] DECIMAL(3,2) NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_provider_practice] PRIMARY KEY ([provider_practice_id])
);
GO
CREATE TABLE [edi_enrollment] (
    [edi_enrollment_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [practice_id] INT NOT NULL,
    [provider_id] INT NULL,
    [payer_id] INT NOT NULL,
    [transaction_type] VARCHAR(10) NOT NULL,
    [clearinghouse_code] VARCHAR(30) NULL,
    [enrollment_status] VARCHAR(12) NOT NULL,
    [submitted_date] DATE NULL,
    [effective_date] DATE NULL,
    [terminated_date] DATE NULL,
    [is_inferred] BIT NOT NULL,
    [payer_identifier_id] INT NULL,
    [version] SMALLINT NOT NULL,
    [is_current] BIT NOT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_edi_enrollment] PRIMARY KEY ([edi_enrollment_id], [version])
);
GO
CREATE TABLE [practice] (
    [practice_id] INT NOT NULL,
    [tenant_id] INT NOT NULL,
    [practice_number] VARCHAR(50) NOT NULL,
    [practice_name] NVARCHAR(200) NULL,
    [tax_id] CHAR(9) NULL,
    [group_npi] CHAR(10) NULL,
    [time_zone] VARCHAR(40) NULL,
    [fiscal_year_start_month] TINYINT NULL,
    [go_live_date] DATE NULL,
    [is_active] BIT NOT NULL,
    [version] SMALLINT NOT NULL,
    [is_current] BIT NOT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_practice] PRIMARY KEY ([practice_id], [version])
);
GO
CREATE TABLE [provider] (
    [provider_id] INT NOT NULL,
    [tenant_id] INT NOT NULL,
    [npi] CHAR(10) NOT NULL,
    [provider_number] VARCHAR(50) NULL,
    [provider_type] VARCHAR(12) NULL,
    [specialty_id] INT NULL,
    [taxonomy_code] VARCHAR(12) NULL,
    [credential] VARCHAR(10) NULL,
    [provider_name] NVARCHAR(200) NULL,
    [practice_id] INT NULL,
    [start_date] DATE NULL,
    [end_date] DATE NULL,
    [supervising_provider_id] INT NULL,
    [is_active] BIT NOT NULL,
    [version] SMALLINT NOT NULL,
    [is_current] BIT NOT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_provider] PRIMARY KEY ([provider_id], [version])
);
GO
CREATE TABLE [payer] (
    [payer_id] INT NOT NULL,
    [tenant_id] INT NOT NULL,
    [payer_code] VARCHAR(50) NOT NULL,
    [payer_name] NVARCHAR(200) NOT NULL,
    [payer_number] VARCHAR(50) NULL,
    [payer_type] VARCHAR(20) NOT NULL,
    [parent_payer] NVARCHAR(200) NULL,
    [filing_days] SMALLINT NULL,
    [corrected_claim_days] SMALLINT NULL,
    [appeal_days] SMALLINT NULL,
    [standard_turnaround_days] SMALLINT NULL,
    [supports_electronic_auth] BIT NULL,
    [state] CHAR(2) NULL,
    [dispute_contact] NVARCHAR(200) NULL,
    [is_active] BIT NOT NULL,
    [filing_clock_basis] VARCHAR(30) NULL,
    [version] SMALLINT NOT NULL,
    [is_current] BIT NOT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_payer] PRIMARY KEY ([payer_id], [version])
);
GO
CREATE TABLE [cpt_code] (
    [cpt_code_id] INT NOT NULL,
    [tenant_id] INT NULL,
    [code] VARCHAR(5) NOT NULL,
    [code_type] VARCHAR(5) NOT NULL,
    [effective_from] DATE NOT NULL,
    [effective_to] DATE NOT NULL,
    [short_label] VARCHAR(60) NULL,
    [category] VARCHAR(20) NULL,
    [em_level] TINYINT NULL,
    [is_add_on] BIT NULL,
    [is_timed] BIT NULL,
    [unit_limit_per_day] SMALLINT NULL,
    [laterality_required] BIT NULL,
    [work_rvu] DECIMAL(8,2) NULL,
    [global_period_days] SMALLINT NULL,
    [is_unrecognized] BIT NULL,
    [is_active] BIT NOT NULL,
    [unit_limit_basis] VARCHAR(20) NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_cpt_code] PRIMARY KEY ([cpt_code_id])
);
GO
CREATE TABLE [diagnosis_code] (
    [diagnosis_code_id] INT NOT NULL,
    [tenant_id] INT NULL,
    [icd10_code] VARCHAR(8) NOT NULL,
    [effective_from] DATE NOT NULL,
    [effective_to] DATE NOT NULL,
    [description] VARCHAR(255) NULL,
    [category] VARCHAR(30) NULL,
    [is_billable] BIT NULL,
    [is_chronic] BIT NULL,
    [is_unspecified] BIT NULL,
    [parent_code] VARCHAR(8) NULL,
    [hcc_category] VARCHAR(10) NULL,
    [is_unrecognized] BIT NULL,
    [is_active] BIT NOT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_diagnosis_code] PRIMARY KEY ([diagnosis_code_id])
);
GO
CREATE TABLE [modifier] (
    [modifier_id] INT NOT NULL,
    [tenant_id] INT NULL,
    [modifier_code] CHAR(2) NOT NULL,
    [modifier_group] VARCHAR(20) NULL,
    [affects_payment] BIT NULL,
    [payment_adjustment_pct] DECIMAL(5,2) NULL,
    [short_label] VARCHAR(60) NULL,
    [effective_from] DATE NULL,
    [effective_to] DATE NULL,
    [is_active] BIT NOT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_modifier] PRIMARY KEY ([modifier_id])
);
GO
CREATE TABLE [place_of_service] (
    [place_of_service_id] INT NOT NULL,
    [tenant_id] INT NULL,
    [pos_code] CHAR(2) NOT NULL,
    [pos_name] VARCHAR(80) NULL,
    [setting] VARCHAR(15) NULL,
    [is_facility] BIT NULL,
    [is_telehealth] BIT NULL,
    [effective_from] DATE NULL,
    [effective_to] DATE NULL,
    [is_active] BIT NOT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_place_of_service] PRIMARY KEY ([place_of_service_id])
);
GO
CREATE TABLE [specialty] (
    [specialty_id] INT NOT NULL,
    [tenant_id] INT NOT NULL,
    [specialty_code] VARCHAR(20) NOT NULL,
    [specialty_name] NVARCHAR(100) NOT NULL,
    [specialty_group] VARCHAR(15) NULL,
    [is_primary_care] BIT NULL,
    [cms_specialty_code] VARCHAR(5) NULL,
    [taxonomy_prefix] VARCHAR(12) NULL,
    [is_active] BIT NOT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_specialty] PRIMARY KEY ([specialty_id])
);
GO
CREATE TABLE [facility] (
    [facility_id] INT NOT NULL,
    [tenant_id] INT NOT NULL,
    [facility_number] VARCHAR(50) NOT NULL,
    [facility_name] NVARCHAR(200) NULL,
    [practice_id] INT NULL,
    [facility_type] VARCHAR(20) NULL,
    [default_place_of_service_id] INT NULL,
    [facility_npi] CHAR(10) NULL,
    [state] CHAR(2) NULL,
    [open_date] DATE NULL,
    [close_date] DATE NULL,
    [zip] VARCHAR(5) NULL,
    [rooms] SMALLINT NULL,
    [time_zone] VARCHAR(40) NULL,
    [is_active] BIT NOT NULL,
    [version] SMALLINT NOT NULL,
    [is_current] BIT NOT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_facility] PRIMARY KEY ([facility_id], [version])
);
GO
CREATE TABLE [fee_schedule] (
    [fee_schedule_id] INT NOT NULL,
    [tenant_id] INT NOT NULL,
    [practice_id] INT NOT NULL,
    [fee_schedule_name] VARCHAR(50) NOT NULL,
    [facility_id] INT NULL,
    [fee_basis] VARCHAR(15) NULL,
    [is_default] BIT NULL,
    [is_inferred] BIT NOT NULL,
    [effective_from] DATE NOT NULL,
    [effective_to] DATE NOT NULL,
    [is_active] BIT NOT NULL,
    [version] SMALLINT NOT NULL,
    [is_current] BIT NOT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_fee_schedule] PRIMARY KEY ([fee_schedule_id], [version])
);
GO
CREATE TABLE [fee_schedule_line] (
    [fee_schedule_line_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [fee_schedule_id] INT NOT NULL,
    [cpt_code_id] INT NOT NULL,
    [fee_per_unit] DECIMAL(12,2) NOT NULL,
    [effective_from] DATE NOT NULL,
    [is_inferred] BIT NOT NULL,
    [effective_to] DATE NULL,
    [modifier_id] INT NULL,
    [is_active] BIT NOT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_fee_schedule_line] PRIMARY KEY ([fee_schedule_line_id])
);
GO
CREATE TABLE [contract_rate] (
    [contract_rate_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [practice_id] INT NOT NULL,
    [payer_id] INT NOT NULL,
    [payer_contract_id] INT NULL,
    [cpt_code_id] INT NOT NULL,
    [allowed_per_unit] DECIMAL(12,2) NOT NULL,
    [effective_from] DATE NOT NULL,
    [rate_source] VARCHAR(20) NOT NULL,
    [is_inferred] BIT NOT NULL,
    [effective_to] DATE NULL,
    [modifier_id] INT NULL,
    [rate_setting] VARCHAR(12) NULL,
    [contract_number] VARCHAR(50) NULL,
    [rate_basis] VARCHAR(20) NULL,
    [lesser_of_billed] BIT NULL,
    [confidence] DECIMAL(5,4) NULL,
    [sample_size] INT NULL,
    [plan_type] VARCHAR(25) NULL,
    [provider_id] INT NULL,
    [specialty_id] INT NULL,
    [multi_procedure_reduction_pct] DECIMAL(5,2) NULL,
    [dispute_days] SMALLINT NULL,
    [is_active] BIT NOT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_contract_rate] PRIMARY KEY ([contract_rate_id])
);
GO
CREATE TABLE [adjustment_reason] (
    [adjustment_reason_id] INT NOT NULL,
    [tenant_id] INT NULL,
    [carc_code] VARCHAR(10) NOT NULL,
    [effective_from] DATE NOT NULL,
    [effective_to] DATE NOT NULL,
    [reason_class] VARCHAR(25) NOT NULL,
    [short_label] VARCHAR(60) NULL,
    [reason_category] VARCHAR(30) NULL,
    [suggested_action] VARCHAR(25) NULL,
    [owner_role] VARCHAR(20) NULL,
    [upstream_stage] VARCHAR(15) NULL,
    [is_appealable] BIT NULL,
    [is_technical] BIT NULL,
    [is_preventable_default] BIT NULL,
    [typical_group] CHAR(2) NULL,
    [is_unrecognized] BIT NOT NULL,
    [is_active] BIT NOT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_adjustment_reason] PRIMARY KEY ([adjustment_reason_id])
);
GO
CREATE TABLE [remark_code] (
    [remark_code_id] INT NOT NULL,
    [tenant_id] INT NULL,
    [rarc_code] VARCHAR(10) NOT NULL,
    [effective_from] DATE NOT NULL,
    [effective_to] DATE NOT NULL,
    [code_qualifier] VARCHAR(5) NULL,
    [short_label] VARCHAR(60) NULL,
    [remark_type] VARCHAR(15) NULL,
    [suggests_action] VARCHAR(25) NULL,
    [documents_needed] VARCHAR(30) NULL,
    [related_reason_code] VARCHAR(10) NULL,
    [is_unrecognized] BIT NOT NULL,
    [is_active] BIT NOT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_remark_code] PRIMARY KEY ([remark_code_id])
);
GO
CREATE TABLE [practice_settings] (
    [practice_settings_id] INT NOT NULL,
    [tenant_id] INT NOT NULL,
    [practice_id] INT NULL,
    [setting_key] VARCHAR(50) NOT NULL,
    [setting_value] VARCHAR(100) NOT NULL,
    [value_type] VARCHAR(10) NOT NULL,
    [effective_from] DATE NOT NULL,
    [effective_to] DATE NOT NULL,
    [set_by_role] VARCHAR(20) NULL,
    [approved_by_staff_id] INT NULL,
    [is_active] BIT NOT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_practice_settings] PRIMARY KEY ([practice_settings_id])
);
GO
CREATE TABLE [payer_rule] (
    [payer_rule_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [payer_rule_number] VARCHAR(50) NULL,
    [rule_code] VARCHAR(50) NOT NULL,
    [rule_family] VARCHAR(30) NOT NULL,
    [rule_action] VARCHAR(25) NOT NULL,
    [rule_source_code] VARCHAR(20) NOT NULL,
    [rule_source_ref] VARCHAR(50) NULL,
    [payer_id] INT NULL,
    [plan_type] VARCHAR(25) NULL,
    [place_of_service_id] INT NULL,
    [practice_id] INT NULL,
    [cpt_code_id] INT NULL,
    [cpt_code_to_id] INT NULL,
    [paired_cpt_code_id] INT NULL,
    [modifier_id] INT NULL,
    [diagnosis_code_id] INT NULL,
    [adjustment_reason_id] INT NULL,
    [edit_field_code] VARCHAR(30) NULL,
    [requirement_code] VARCHAR(20) NULL,
    [unit_limit] SMALLINT NULL,
    [unit_limit_basis] VARCHAR(20) NULL,
    [evidence_claim_count] INT NULL,
    [evidence_denied_count] INT NULL,
    [evidence_denied_amount] DECIMAL(12,2) NULL,
    [evidence_from_date] DATE NULL,
    [evidence_to_date] DATE NULL,
    [owner_role] VARCHAR(20) NULL,
    [severity] VARCHAR(10) NULL,
    [is_enabled] BIT NOT NULL,
    [is_synthetic] BIT NOT NULL,
    [approval_status] VARCHAR(15) NOT NULL,
    [approved_by_staff_id] INT NULL,
    [approved_date] DATE NULL,
    [last_confirmed_date] DATE NULL,
    [effective_from] DATE NOT NULL,
    [effective_to] DATE NULL,
    [retire_reason_code] VARCHAR(20) NULL,
    [version] SMALLINT NOT NULL,
    [is_current] BIT NOT NULL,
    [previous_payer_rule_id] BIGINT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_payer_rule] PRIMARY KEY ([payer_rule_id], [version])
);
GO
CREATE TABLE [calendar] (
    [calendar_id] INT NOT NULL,
    [tenant_id] INT NULL,
    [practice_id] INT NULL,
    [calendar_date] DATE NOT NULL,
    [is_business_day] BIT NOT NULL,
    [is_holiday] BIT NOT NULL,
    [holiday_code] VARCHAR(20) NULL,
    [business_day_number] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_calendar] PRIMARY KEY ([calendar_id])
);
GO
CREATE TABLE [payer_identifier] (
    [payer_identifier_id] INT NOT NULL,
    [tenant_id] INT NOT NULL,
    [payer_id] INT NOT NULL,
    [identifier_value] VARCHAR(50) NOT NULL,
    [identifier_type] VARCHAR(20) NOT NULL,
    [clearinghouse_code] VARCHAR(30) NULL,
    [effective_from] DATE NOT NULL,
    [effective_to] DATE NOT NULL,
    [is_active] BIT NOT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_payer_identifier] PRIMARY KEY ([payer_identifier_id])
);
GO
CREATE TABLE [payer_plan] (
    [payer_plan_id] INT NOT NULL,
    [tenant_id] INT NOT NULL,
    [payer_id] INT NOT NULL,
    [plan_code] VARCHAR(50) NOT NULL,
    [plan_name] NVARCHAR(100) NULL,
    [plan_type] VARCHAR(25) NULL,
    [product_line] VARCHAR(20) NULL,
    [requires_referral] BIT NULL,
    [filing_days] SMALLINT NULL,
    [appeal_days] SMALLINT NULL,
    [state] CHAR(2) NULL,
    [effective_from] DATE NOT NULL,
    [effective_to] DATE NOT NULL,
    [is_active] BIT NOT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_payer_plan] PRIMARY KEY ([payer_plan_id])
);
GO
CREATE TABLE [payer_contract] (
    [payer_contract_id] INT NOT NULL,
    [tenant_id] INT NOT NULL,
    [practice_id] INT NOT NULL,
    [payer_id] INT NOT NULL,
    [payer_plan_id] INT NULL,
    [contract_number] VARCHAR(50) NULL,
    [contract_status] VARCHAR(12) NOT NULL,
    [effective_from] DATE NOT NULL,
    [effective_to] DATE NOT NULL,
    [filing_days] SMALLINT NULL,
    [corrected_claim_days] SMALLINT NULL,
    [appeal_days] SMALLINT NULL,
    [lesser_of_billed] BIT NULL,
    [default_rate_basis] VARCHAR(20) NULL,
    [default_pct_of_medicare] DECIMAL(6,2) NULL,
    [escalator_pct] DECIMAL(5,2) NULL,
    [renewal_notice_days] SMALLINT NULL,
    [document_hash] BINARY(32) NULL,
    [version] SMALLINT NOT NULL,
    [is_current] BIT NOT NULL,
    [created_at] DATETIME2(0) NULL,
    [created_by_staff_id] INT NULL,
    [modified_at] DATETIME2(0) NULL,
    [modified_by_staff_id] INT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_payer_contract] PRIMARY KEY ([payer_contract_id], [version])
);
GO
CREATE TABLE [claim_status_code] (
    [claim_status_code_id] INT NOT NULL,
    [tenant_id] INT NULL,
    [code_set] VARCHAR(10) NOT NULL,
    [code] VARCHAR(5) NOT NULL,
    [short_label] VARCHAR(100) NOT NULL,
    [status_group] VARCHAR(15) NULL,
    [is_rejection] BIT NULL,
    [effective_from] DATE NOT NULL,
    [effective_to] DATE NOT NULL,
    [is_unrecognized] BIT NOT NULL,
    [is_active] BIT NOT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_claim_status_code] PRIMARY KEY ([claim_status_code_id])
);
GO
CREATE TABLE [ndc_code] (
    [ndc_code_id] INT NOT NULL,
    [tenant_id] INT NULL,
    [ndc_11] CHAR(11) NOT NULL,
    [product_label] VARCHAR(100) NULL,
    [hcpcs_cpt_code_id] INT NULL,
    [billing_unit] CHAR(2) NULL,
    [package_quantity] DECIMAL(12,3) NULL,
    [hcpcs_units_per_package] DECIMAL(12,3) NULL,
    [effective_from] DATE NOT NULL,
    [effective_to] DATE NOT NULL,
    [is_unrecognized] BIT NOT NULL,
    [is_active] BIT NOT NULL,
    [load_batch_id] BIGINT NOT NULL,
    [source_record_hash] BINARY(32) NULL,
    [is_source_deleted] BIT NOT NULL,
    [source_deleted_at] DATETIME2(0) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_ndc_code] PRIMARY KEY ([ndc_code_id])
);
GO
CREATE TABLE [tenant] (
    [tenant_id] INT NOT NULL,
    [tenant_code] VARCHAR(30) NOT NULL,
    [tenant_name] NVARCHAR(200) NOT NULL,
    [tenant_status] VARCHAR(12) NOT NULL,
    [baa_signed_date] DATE NOT NULL,
    [salt_key_ref] VARCHAR(100) NOT NULL,
    [data_region] VARCHAR(20) NULL,
    [go_live_date] DATE NULL,
    [retention_years] TINYINT NULL,
    [offboard_date] DATE NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_tenant] PRIMARY KEY ([tenant_id])
);
GO
CREATE TABLE [data_feed] (
    [data_feed_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [table_name] VARCHAR(40) NOT NULL,
    [feed_name] VARCHAR(80) NOT NULL,
    [source_system] VARCHAR(20) NOT NULL,
    [feed_status] VARCHAR(15) NOT NULL,
    [fallback_level] TINYINT NOT NULL,
    [practice_id] INT NULL,
    [source_kind] VARCHAR(15) NULL,
    [load_frequency] VARCHAR(10) NULL,
    [first_data_date] DATE NULL,
    [last_data_date] DATE NULL,
    [last_load_at] DATETIME2(0) NULL,
    [rows_loaded] BIGINT NULL,
    [completeness_pct] DECIMAL(5,2) NULL,
    [freshness_hours] SMALLINT NULL,
    [reliability_default] DECIMAL(3,2) NULL,
    [expected_row_count] BIGINT NULL,
    [version] SMALLINT NOT NULL,
    [is_current] BIT NOT NULL,
    [previous_data_feed_id] BIGINT NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_data_feed] PRIMARY KEY ([data_feed_id], [version])
);
GO
CREATE TABLE [edi_file] (
    [edi_file_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [data_feed_id] BIGINT NULL,
    [load_batch_id] BIGINT NULL,
    [transaction_set] VARCHAR(5) NOT NULL,
    [direction] CHAR(1) NOT NULL,
    [interchange_control_number] VARCHAR(9) NOT NULL,
    [group_control_number] VARCHAR(9) NULL,
    [clearinghouse_code] VARCHAR(30) NULL,
    [file_hash] BINARY(32) NOT NULL,
    [file_name_hash] BINARY(32) NULL,
    [received_at] DATETIME2(0) NOT NULL,
    [transaction_count] INT NULL,
    [file_status] VARCHAR(12) NOT NULL,
    [parse_error_count] INT NULL,
    [replaced_by_edi_file_id] BIGINT NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_edi_file] PRIMARY KEY ([edi_file_id])
);
GO
CREATE TABLE [load_batch] (
    [load_batch_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [data_feed_id] BIGINT NOT NULL,
    [started_at] DATETIME2(0) NOT NULL,
    [ended_at] DATETIME2(0) NULL,
    [batch_status] VARCHAR(12) NOT NULL,
    [rows_read] BIGINT NULL,
    [rows_inserted] BIGINT NULL,
    [rows_unchanged] BIGINT NULL,
    [rows_rejected] BIGINT NULL,
    [source_watermark] VARCHAR(50) NULL,
    [code_version] VARCHAR(30) NULL,
    [rolled_back_at] DATETIME2(0) NULL,
    [error_summary] VARCHAR(200) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_load_batch] PRIMARY KEY ([load_batch_id])
);
GO
CREATE TABLE [data_quality_result] (
    [data_quality_result_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [load_batch_id] BIGINT NULL,
    [dq_rule_code] VARCHAR(50) NOT NULL,
    [table_name] VARCHAR(40) NOT NULL,
    [column_name] VARCHAR(60) NULL,
    [severity] VARCHAR(10) NOT NULL,
    [rows_checked] BIGINT NULL,
    [rows_failed] BIGINT NOT NULL,
    [sample_ref] VARCHAR(100) NULL,
    [run_at] DATETIME2(0) NOT NULL,
    [dq_status] VARCHAR(12) NOT NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_data_quality_result] PRIMARY KEY ([data_quality_result_id])
);
GO
CREATE TABLE [access_audit] (
    [access_audit_id] BIGINT NOT NULL,
    [tenant_id] INT NOT NULL,
    [accessed_at] DATETIME2(0) NOT NULL,
    [actor_type] VARCHAR(10) NOT NULL,
    [staff_id] INT NULL,
    [agent_run_id] BIGINT NULL,
    [action] VARCHAR(15) NOT NULL,
    [table_name] VARCHAR(40) NOT NULL,
    [row_count] INT NULL,
    [touched_restricted] BIT NOT NULL,
    [purpose_code] VARCHAR(20) NULL,
    [query_hash] BINARY(32) NULL,
    [source] VARCHAR(30) NOT NULL,
    [loaded_at] DATETIME2(0) NOT NULL,
    CONSTRAINT [PK_access_audit] PRIMARY KEY ([access_audit_id])
);
GO

-- foreign keys
ALTER TABLE [appointment] ADD CONSTRAINT [FK_appointment_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [appointment] ADD CONSTRAINT [FK_appointment_patient_id] FOREIGN KEY ([patient_id]) REFERENCES [patient] ([patient_id]);
ALTER TABLE [appointment] ADD CONSTRAINT [FK_appointment_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [appointment] ADD CONSTRAINT [FK_appointment_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [appointment] ADD CONSTRAINT [FK_appointment_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [appointment_status_log] ADD CONSTRAINT [FK_appointment_status_log_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [appointment_status_log] ADD CONSTRAINT [FK_appointment_status_log_changed_by_staff_id] FOREIGN KEY ([changed_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [appointment_status_log] ADD CONSTRAINT [FK_appointment_status_log_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [referral] ADD CONSTRAINT [FK_referral_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [referral] ADD CONSTRAINT [FK_referral_patient_id] FOREIGN KEY ([patient_id]) REFERENCES [patient] ([patient_id]);
ALTER TABLE [referral] ADD CONSTRAINT [FK_referral_specialty_id] FOREIGN KEY ([specialty_id]) REFERENCES [specialty] ([specialty_id]);
ALTER TABLE [referral] ADD CONSTRAINT [FK_referral_diagnosis_code_id] FOREIGN KEY ([diagnosis_code_id]) REFERENCES [diagnosis_code] ([diagnosis_code_id]);
ALTER TABLE [referral] ADD CONSTRAINT [FK_referral_cpt_code_id] FOREIGN KEY ([cpt_code_id]) REFERENCES [cpt_code] ([cpt_code_id]);
ALTER TABLE [referral] ADD CONSTRAINT [FK_referral_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [referral] ADD CONSTRAINT [FK_referral_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [referral] ADD CONSTRAINT [FK_referral_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [appointment_line] ADD CONSTRAINT [FK_appointment_line_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [appointment_line] ADD CONSTRAINT [FK_appointment_line_patient_id] FOREIGN KEY ([patient_id]) REFERENCES [patient] ([patient_id]);
ALTER TABLE [appointment_line] ADD CONSTRAINT [FK_appointment_line_specialty_id] FOREIGN KEY ([specialty_id]) REFERENCES [specialty] ([specialty_id]);
ALTER TABLE [appointment_line] ADD CONSTRAINT [FK_appointment_line_planned_cpt_code_id] FOREIGN KEY ([planned_cpt_code_id]) REFERENCES [cpt_code] ([cpt_code_id]);
ALTER TABLE [appointment_line] ADD CONSTRAINT [FK_appointment_line_planned_diagnosis_code_id] FOREIGN KEY ([planned_diagnosis_code_id]) REFERENCES [diagnosis_code] ([diagnosis_code_id]);
ALTER TABLE [appointment_line] ADD CONSTRAINT [FK_appointment_line_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [appointment_line] ADD CONSTRAINT [FK_appointment_line_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [appointment_line] ADD CONSTRAINT [FK_appointment_line_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [appointment_slot] ADD CONSTRAINT [FK_appointment_slot_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [appointment_slot] ADD CONSTRAINT [FK_appointment_slot_specialty_id] FOREIGN KEY ([specialty_id]) REFERENCES [specialty] ([specialty_id]);
ALTER TABLE [appointment_slot] ADD CONSTRAINT [FK_appointment_slot_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [appointment_slot] ADD CONSTRAINT [FK_appointment_slot_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [appointment_slot] ADD CONSTRAINT [FK_appointment_slot_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [eligibility_check] ADD CONSTRAINT [FK_eligibility_check_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [eligibility_check] ADD CONSTRAINT [FK_eligibility_check_patient_id] FOREIGN KEY ([patient_id]) REFERENCES [patient] ([patient_id]);
ALTER TABLE [eligibility_check] ADD CONSTRAINT [FK_eligibility_check_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [eligibility_check] ADD CONSTRAINT [FK_eligibility_check_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [eligibility_check] ADD CONSTRAINT [FK_eligibility_check_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [patient_estimate] ADD CONSTRAINT [FK_patient_estimate_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [patient_estimate] ADD CONSTRAINT [FK_patient_estimate_patient_id] FOREIGN KEY ([patient_id]) REFERENCES [patient] ([patient_id]);
ALTER TABLE [patient_estimate] ADD CONSTRAINT [FK_patient_estimate_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [patient_estimate] ADD CONSTRAINT [FK_patient_estimate_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [patient_estimate] ADD CONSTRAINT [FK_patient_estimate_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [eligibility_benefit] ADD CONSTRAINT [FK_eligibility_benefit_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [eligibility_benefit] ADD CONSTRAINT [FK_eligibility_benefit_eligibility_check_id] FOREIGN KEY ([eligibility_check_id]) REFERENCES [eligibility_check] ([eligibility_check_id]);
ALTER TABLE [eligibility_benefit] ADD CONSTRAINT [FK_eligibility_benefit_cpt_code_id] FOREIGN KEY ([cpt_code_id]) REFERENCES [cpt_code] ([cpt_code_id]);
ALTER TABLE [eligibility_benefit] ADD CONSTRAINT [FK_eligibility_benefit_patient_id] FOREIGN KEY ([patient_id]) REFERENCES [patient] ([patient_id]);
ALTER TABLE [eligibility_benefit] ADD CONSTRAINT [FK_eligibility_benefit_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [eligibility_benefit] ADD CONSTRAINT [FK_eligibility_benefit_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [eligibility_benefit] ADD CONSTRAINT [FK_eligibility_benefit_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [patient_estimate_line] ADD CONSTRAINT [FK_patient_estimate_line_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [patient_estimate_line] ADD CONSTRAINT [FK_patient_estimate_line_cpt_code_id] FOREIGN KEY ([cpt_code_id]) REFERENCES [cpt_code] ([cpt_code_id]);
ALTER TABLE [patient_estimate_line] ADD CONSTRAINT [FK_patient_estimate_line_modifier_id] FOREIGN KEY ([modifier_id]) REFERENCES [modifier] ([modifier_id]);
ALTER TABLE [patient_estimate_line] ADD CONSTRAINT [FK_patient_estimate_line_diagnosis_code_id] FOREIGN KEY ([diagnosis_code_id]) REFERENCES [diagnosis_code] ([diagnosis_code_id]);
ALTER TABLE [patient_estimate_line] ADD CONSTRAINT [FK_patient_estimate_line_appointment_line_id] FOREIGN KEY ([appointment_line_id]) REFERENCES [appointment_line] ([appointment_line_id]);
ALTER TABLE [patient_estimate_line] ADD CONSTRAINT [FK_patient_estimate_line_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [patient_estimate_line] ADD CONSTRAINT [FK_patient_estimate_line_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [patient_estimate_line] ADD CONSTRAINT [FK_patient_estimate_line_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [encounter] ADD CONSTRAINT [FK_encounter_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [encounter] ADD CONSTRAINT [FK_encounter_patient_id] FOREIGN KEY ([patient_id]) REFERENCES [patient] ([patient_id]);
ALTER TABLE [encounter] ADD CONSTRAINT [FK_encounter_place_of_service_id] FOREIGN KEY ([place_of_service_id]) REFERENCES [place_of_service] ([place_of_service_id]);
ALTER TABLE [encounter] ADD CONSTRAINT [FK_encounter_specialty_id] FOREIGN KEY ([specialty_id]) REFERENCES [specialty] ([specialty_id]);
ALTER TABLE [encounter] ADD CONSTRAINT [FK_encounter_principal_diagnosis_code_id] FOREIGN KEY ([principal_diagnosis_code_id]) REFERENCES [diagnosis_code] ([diagnosis_code_id]);
ALTER TABLE [encounter] ADD CONSTRAINT [FK_encounter_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [encounter] ADD CONSTRAINT [FK_encounter_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [encounter] ADD CONSTRAINT [FK_encounter_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [document] ADD CONSTRAINT [FK_document_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [document] ADD CONSTRAINT [FK_document_patient_id] FOREIGN KEY ([patient_id]) REFERENCES [patient] ([patient_id]);
ALTER TABLE [document] ADD CONSTRAINT [FK_document_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [document] ADD CONSTRAINT [FK_document_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [document] ADD CONSTRAINT [FK_document_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [clinical_order] ADD CONSTRAINT [FK_clinical_order_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [clinical_order] ADD CONSTRAINT [FK_clinical_order_patient_id] FOREIGN KEY ([patient_id]) REFERENCES [patient] ([patient_id]);
ALTER TABLE [clinical_order] ADD CONSTRAINT [FK_clinical_order_encounter_line_id] FOREIGN KEY ([encounter_line_id]) REFERENCES [encounter_line] ([encounter_line_id]);
ALTER TABLE [clinical_order] ADD CONSTRAINT [FK_clinical_order_cpt_code_id] FOREIGN KEY ([cpt_code_id]) REFERENCES [cpt_code] ([cpt_code_id]);
ALTER TABLE [clinical_order] ADD CONSTRAINT [FK_clinical_order_diagnosis_code_id] FOREIGN KEY ([diagnosis_code_id]) REFERENCES [diagnosis_code] ([diagnosis_code_id]);
ALTER TABLE [clinical_order] ADD CONSTRAINT [FK_clinical_order_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [clinical_order] ADD CONSTRAINT [FK_clinical_order_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [clinical_order] ADD CONSTRAINT [FK_clinical_order_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [encounter_line] ADD CONSTRAINT [FK_encounter_line_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [encounter_line] ADD CONSTRAINT [FK_encounter_line_patient_id] FOREIGN KEY ([patient_id]) REFERENCES [patient] ([patient_id]);
ALTER TABLE [encounter_line] ADD CONSTRAINT [FK_encounter_line_specialty_id] FOREIGN KEY ([specialty_id]) REFERENCES [specialty] ([specialty_id]);
ALTER TABLE [encounter_line] ADD CONSTRAINT [FK_encounter_line_cpt_code_id] FOREIGN KEY ([cpt_code_id]) REFERENCES [cpt_code] ([cpt_code_id]);
ALTER TABLE [encounter_line] ADD CONSTRAINT [FK_encounter_line_diagnosis_1_id] FOREIGN KEY ([diagnosis_1_id]) REFERENCES [diagnosis_code] ([diagnosis_code_id]);
ALTER TABLE [encounter_line] ADD CONSTRAINT [FK_encounter_line_diagnosis_2_id] FOREIGN KEY ([diagnosis_2_id]) REFERENCES [diagnosis_code] ([diagnosis_code_id]);
ALTER TABLE [encounter_line] ADD CONSTRAINT [FK_encounter_line_diagnosis_3_id] FOREIGN KEY ([diagnosis_3_id]) REFERENCES [diagnosis_code] ([diagnosis_code_id]);
ALTER TABLE [encounter_line] ADD CONSTRAINT [FK_encounter_line_diagnosis_4_id] FOREIGN KEY ([diagnosis_4_id]) REFERENCES [diagnosis_code] ([diagnosis_code_id]);
ALTER TABLE [encounter_line] ADD CONSTRAINT [FK_encounter_line_modifier_1_id] FOREIGN KEY ([modifier_1_id]) REFERENCES [modifier] ([modifier_id]);
ALTER TABLE [encounter_line] ADD CONSTRAINT [FK_encounter_line_modifier_2_id] FOREIGN KEY ([modifier_2_id]) REFERENCES [modifier] ([modifier_id]);
ALTER TABLE [encounter_line] ADD CONSTRAINT [FK_encounter_line_modifier_3_id] FOREIGN KEY ([modifier_3_id]) REFERENCES [modifier] ([modifier_id]);
ALTER TABLE [encounter_line] ADD CONSTRAINT [FK_encounter_line_modifier_4_id] FOREIGN KEY ([modifier_4_id]) REFERENCES [modifier] ([modifier_id]);
ALTER TABLE [encounter_line] ADD CONSTRAINT [FK_encounter_line_place_of_service_id] FOREIGN KEY ([place_of_service_id]) REFERENCES [place_of_service] ([place_of_service_id]);
ALTER TABLE [encounter_line] ADD CONSTRAINT [FK_encounter_line_ndc_code_id] FOREIGN KEY ([ndc_code_id]) REFERENCES [ndc_code] ([ndc_code_id]);
ALTER TABLE [encounter_line] ADD CONSTRAINT [FK_encounter_line_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [encounter_line] ADD CONSTRAINT [FK_encounter_line_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [encounter_line] ADD CONSTRAINT [FK_encounter_line_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [encounter_diagnosis] ADD CONSTRAINT [FK_encounter_diagnosis_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [encounter_diagnosis] ADD CONSTRAINT [FK_encounter_diagnosis_diagnosis_code_id] FOREIGN KEY ([diagnosis_code_id]) REFERENCES [diagnosis_code] ([diagnosis_code_id]);
ALTER TABLE [encounter_diagnosis] ADD CONSTRAINT [FK_encounter_diagnosis_patient_id] FOREIGN KEY ([patient_id]) REFERENCES [patient] ([patient_id]);
ALTER TABLE [encounter_diagnosis] ADD CONSTRAINT [FK_encounter_diagnosis_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [encounter_diagnosis] ADD CONSTRAINT [FK_encounter_diagnosis_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [encounter_diagnosis] ADD CONSTRAINT [FK_encounter_diagnosis_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [document_element] ADD CONSTRAINT [FK_document_element_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [document_element] ADD CONSTRAINT [FK_document_element_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [document_element] ADD CONSTRAINT [FK_document_element_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [document_element] ADD CONSTRAINT [FK_document_element_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [bill] ADD CONSTRAINT [FK_bill_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [bill] ADD CONSTRAINT [FK_bill_patient_id] FOREIGN KEY ([patient_id]) REFERENCES [patient] ([patient_id]);
ALTER TABLE [bill] ADD CONSTRAINT [FK_bill_specialty_id] FOREIGN KEY ([specialty_id]) REFERENCES [specialty] ([specialty_id]);
ALTER TABLE [bill] ADD CONSTRAINT [FK_bill_place_of_service_id] FOREIGN KEY ([place_of_service_id]) REFERENCES [place_of_service] ([place_of_service_id]);
ALTER TABLE [bill] ADD CONSTRAINT [FK_bill_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [bill] ADD CONSTRAINT [FK_bill_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [bill] ADD CONSTRAINT [FK_bill_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [claim] ADD CONSTRAINT [FK_claim_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [claim] ADD CONSTRAINT [FK_claim_patient_id] FOREIGN KEY ([patient_id]) REFERENCES [patient] ([patient_id]);
ALTER TABLE [claim] ADD CONSTRAINT [FK_claim_place_of_service_id] FOREIGN KEY ([place_of_service_id]) REFERENCES [place_of_service] ([place_of_service_id]);
ALTER TABLE [claim] ADD CONSTRAINT [FK_claim_specialty_id] FOREIGN KEY ([specialty_id]) REFERENCES [specialty] ([specialty_id]);
ALTER TABLE [claim] ADD CONSTRAINT [FK_claim_principal_diagnosis_code_id] FOREIGN KEY ([principal_diagnosis_code_id]) REFERENCES [diagnosis_code] ([diagnosis_code_id]);
ALTER TABLE [claim] ADD CONSTRAINT [FK_claim_edi_file_id] FOREIGN KEY ([edi_file_id]) REFERENCES [edi_file] ([edi_file_id]);
ALTER TABLE [claim] ADD CONSTRAINT [FK_claim_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [claim] ADD CONSTRAINT [FK_claim_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [claim] ADD CONSTRAINT [FK_claim_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [claim_attachment] ADD CONSTRAINT [FK_claim_attachment_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [claim_attachment] ADD CONSTRAINT [FK_claim_attachment_patient_id] FOREIGN KEY ([patient_id]) REFERENCES [patient] ([patient_id]);
ALTER TABLE [claim_attachment] ADD CONSTRAINT [FK_claim_attachment_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [claim_attachment] ADD CONSTRAINT [FK_claim_attachment_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [claim_attachment] ADD CONSTRAINT [FK_claim_attachment_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [bill_line] ADD CONSTRAINT [FK_bill_line_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [bill_line] ADD CONSTRAINT [FK_bill_line_patient_id] FOREIGN KEY ([patient_id]) REFERENCES [patient] ([patient_id]);
ALTER TABLE [bill_line] ADD CONSTRAINT [FK_bill_line_specialty_id] FOREIGN KEY ([specialty_id]) REFERENCES [specialty] ([specialty_id]);
ALTER TABLE [bill_line] ADD CONSTRAINT [FK_bill_line_cpt_code_id] FOREIGN KEY ([cpt_code_id]) REFERENCES [cpt_code] ([cpt_code_id]);
ALTER TABLE [bill_line] ADD CONSTRAINT [FK_bill_line_modifier_1_id] FOREIGN KEY ([modifier_1_id]) REFERENCES [modifier] ([modifier_id]);
ALTER TABLE [bill_line] ADD CONSTRAINT [FK_bill_line_modifier_2_id] FOREIGN KEY ([modifier_2_id]) REFERENCES [modifier] ([modifier_id]);
ALTER TABLE [bill_line] ADD CONSTRAINT [FK_bill_line_modifier_3_id] FOREIGN KEY ([modifier_3_id]) REFERENCES [modifier] ([modifier_id]);
ALTER TABLE [bill_line] ADD CONSTRAINT [FK_bill_line_modifier_4_id] FOREIGN KEY ([modifier_4_id]) REFERENCES [modifier] ([modifier_id]);
ALTER TABLE [bill_line] ADD CONSTRAINT [FK_bill_line_diagnosis_1_id] FOREIGN KEY ([diagnosis_1_id]) REFERENCES [diagnosis_code] ([diagnosis_code_id]);
ALTER TABLE [bill_line] ADD CONSTRAINT [FK_bill_line_diagnosis_2_id] FOREIGN KEY ([diagnosis_2_id]) REFERENCES [diagnosis_code] ([diagnosis_code_id]);
ALTER TABLE [bill_line] ADD CONSTRAINT [FK_bill_line_diagnosis_3_id] FOREIGN KEY ([diagnosis_3_id]) REFERENCES [diagnosis_code] ([diagnosis_code_id]);
ALTER TABLE [bill_line] ADD CONSTRAINT [FK_bill_line_diagnosis_4_id] FOREIGN KEY ([diagnosis_4_id]) REFERENCES [diagnosis_code] ([diagnosis_code_id]);
ALTER TABLE [bill_line] ADD CONSTRAINT [FK_bill_line_encounter_line_id] FOREIGN KEY ([encounter_line_id]) REFERENCES [encounter_line] ([encounter_line_id]);
ALTER TABLE [bill_line] ADD CONSTRAINT [FK_bill_line_cpt_as_entered_id] FOREIGN KEY ([cpt_as_entered_id]) REFERENCES [cpt_code] ([cpt_code_id]);
ALTER TABLE [bill_line] ADD CONSTRAINT [FK_bill_line_change_approved_by_staff_id] FOREIGN KEY ([change_approved_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [bill_line] ADD CONSTRAINT [FK_bill_line_ndc_code_id] FOREIGN KEY ([ndc_code_id]) REFERENCES [ndc_code] ([ndc_code_id]);
ALTER TABLE [bill_line] ADD CONSTRAINT [FK_bill_line_place_of_service_id] FOREIGN KEY ([place_of_service_id]) REFERENCES [place_of_service] ([place_of_service_id]);
ALTER TABLE [bill_line] ADD CONSTRAINT [FK_bill_line_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [bill_line] ADD CONSTRAINT [FK_bill_line_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [bill_line] ADD CONSTRAINT [FK_bill_line_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [claim_line] ADD CONSTRAINT [FK_claim_line_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [claim_line] ADD CONSTRAINT [FK_claim_line_patient_id] FOREIGN KEY ([patient_id]) REFERENCES [patient] ([patient_id]);
ALTER TABLE [claim_line] ADD CONSTRAINT [FK_claim_line_specialty_id] FOREIGN KEY ([specialty_id]) REFERENCES [specialty] ([specialty_id]);
ALTER TABLE [claim_line] ADD CONSTRAINT [FK_claim_line_cpt_code_id] FOREIGN KEY ([cpt_code_id]) REFERENCES [cpt_code] ([cpt_code_id]);
ALTER TABLE [claim_line] ADD CONSTRAINT [FK_claim_line_place_of_service_id] FOREIGN KEY ([place_of_service_id]) REFERENCES [place_of_service] ([place_of_service_id]);
ALTER TABLE [claim_line] ADD CONSTRAINT [FK_claim_line_modifier_1_id] FOREIGN KEY ([modifier_1_id]) REFERENCES [modifier] ([modifier_id]);
ALTER TABLE [claim_line] ADD CONSTRAINT [FK_claim_line_modifier_2_id] FOREIGN KEY ([modifier_2_id]) REFERENCES [modifier] ([modifier_id]);
ALTER TABLE [claim_line] ADD CONSTRAINT [FK_claim_line_modifier_3_id] FOREIGN KEY ([modifier_3_id]) REFERENCES [modifier] ([modifier_id]);
ALTER TABLE [claim_line] ADD CONSTRAINT [FK_claim_line_modifier_4_id] FOREIGN KEY ([modifier_4_id]) REFERENCES [modifier] ([modifier_id]);
ALTER TABLE [claim_line] ADD CONSTRAINT [FK_claim_line_primary_diagnosis_code_id] FOREIGN KEY ([primary_diagnosis_code_id]) REFERENCES [diagnosis_code] ([diagnosis_code_id]);
ALTER TABLE [claim_line] ADD CONSTRAINT [FK_claim_line_primary_denial_reason_id] FOREIGN KEY ([primary_denial_reason_id]) REFERENCES [adjustment_reason] ([adjustment_reason_id]);
ALTER TABLE [claim_line] ADD CONSTRAINT [FK_claim_line_bill_line_id] FOREIGN KEY ([bill_line_id]) REFERENCES [bill_line] ([bill_line_id]);
ALTER TABLE [claim_line] ADD CONSTRAINT [FK_claim_line_ndc_code_id] FOREIGN KEY ([ndc_code_id]) REFERENCES [ndc_code] ([ndc_code_id]);
ALTER TABLE [claim_line] ADD CONSTRAINT [FK_claim_line_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [claim_line] ADD CONSTRAINT [FK_claim_line_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [claim_line] ADD CONSTRAINT [FK_claim_line_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [claim_status_history] ADD CONSTRAINT [FK_claim_status_history_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [claim_status_history] ADD CONSTRAINT [FK_claim_status_history_claim_line_id] FOREIGN KEY ([claim_line_id]) REFERENCES [claim_line] ([claim_line_id]);
ALTER TABLE [claim_status_history] ADD CONSTRAINT [FK_claim_status_history_patient_id] FOREIGN KEY ([patient_id]) REFERENCES [patient] ([patient_id]);
ALTER TABLE [claim_status_history] ADD CONSTRAINT [FK_claim_status_history_status_category_code_id] FOREIGN KEY ([status_category_code_id]) REFERENCES [claim_status_code] ([claim_status_code_id]);
ALTER TABLE [claim_status_history] ADD CONSTRAINT [FK_claim_status_history_status_code_id] FOREIGN KEY ([status_code_id]) REFERENCES [claim_status_code] ([claim_status_code_id]);
ALTER TABLE [claim_status_history] ADD CONSTRAINT [FK_claim_status_history_specialty_id] FOREIGN KEY ([specialty_id]) REFERENCES [specialty] ([specialty_id]);
ALTER TABLE [claim_status_history] ADD CONSTRAINT [FK_claim_status_history_edi_file_id] FOREIGN KEY ([edi_file_id]) REFERENCES [edi_file] ([edi_file_id]);
ALTER TABLE [claim_status_history] ADD CONSTRAINT [FK_claim_status_history_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [claim_status_history] ADD CONSTRAINT [FK_claim_status_history_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [claim_status_history] ADD CONSTRAINT [FK_claim_status_history_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [claim_diagnosis] ADD CONSTRAINT [FK_claim_diagnosis_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [claim_diagnosis] ADD CONSTRAINT [FK_claim_diagnosis_diagnosis_code_id] FOREIGN KEY ([diagnosis_code_id]) REFERENCES [diagnosis_code] ([diagnosis_code_id]);
ALTER TABLE [claim_diagnosis] ADD CONSTRAINT [FK_claim_diagnosis_patient_id] FOREIGN KEY ([patient_id]) REFERENCES [patient] ([patient_id]);
ALTER TABLE [claim_diagnosis] ADD CONSTRAINT [FK_claim_diagnosis_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [claim_diagnosis] ADD CONSTRAINT [FK_claim_diagnosis_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [claim_diagnosis] ADD CONSTRAINT [FK_claim_diagnosis_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [claim_attachment_document] ADD CONSTRAINT [FK_claim_attachment_document_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [claim_attachment_document] ADD CONSTRAINT [FK_claim_attachment_document_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [claim_attachment_document] ADD CONSTRAINT [FK_claim_attachment_document_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [claim_attachment_document] ADD CONSTRAINT [FK_claim_attachment_document_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [claim_edit] ADD CONSTRAINT [FK_claim_edit_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [claim_edit] ADD CONSTRAINT [FK_claim_edit_claim_line_id] FOREIGN KEY ([claim_line_id]) REFERENCES [claim_line] ([claim_line_id]);
ALTER TABLE [claim_edit] ADD CONSTRAINT [FK_claim_edit_resolved_by_staff_id] FOREIGN KEY ([resolved_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [claim_edit] ADD CONSTRAINT [FK_claim_edit_agent_decision_id] FOREIGN KEY ([agent_decision_id]) REFERENCES [agent_decision] ([agent_decision_id]);
ALTER TABLE [claim_edit] ADD CONSTRAINT [FK_claim_edit_edi_file_id] FOREIGN KEY ([edi_file_id]) REFERENCES [edi_file] ([edi_file_id]);
ALTER TABLE [claim_edit] ADD CONSTRAINT [FK_claim_edit_patient_id] FOREIGN KEY ([patient_id]) REFERENCES [patient] ([patient_id]);
ALTER TABLE [claim_edit] ADD CONSTRAINT [FK_claim_edit_cpt_code_id] FOREIGN KEY ([cpt_code_id]) REFERENCES [cpt_code] ([cpt_code_id]);
ALTER TABLE [claim_edit] ADD CONSTRAINT [FK_claim_edit_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [claim_edit] ADD CONSTRAINT [FK_claim_edit_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [claim_edit] ADD CONSTRAINT [FK_claim_edit_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [ledger_entry] ADD CONSTRAINT [FK_ledger_entry_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [ledger_entry] ADD CONSTRAINT [FK_ledger_entry_patient_id] FOREIGN KEY ([patient_id]) REFERENCES [patient] ([patient_id]);
ALTER TABLE [ledger_entry] ADD CONSTRAINT [FK_ledger_entry_bill_line_id] FOREIGN KEY ([bill_line_id]) REFERENCES [bill_line] ([bill_line_id]);
ALTER TABLE [ledger_entry] ADD CONSTRAINT [FK_ledger_entry_claim_line_id] FOREIGN KEY ([claim_line_id]) REFERENCES [claim_line] ([claim_line_id]);
ALTER TABLE [ledger_entry] ADD CONSTRAINT [FK_ledger_entry_specialty_id] FOREIGN KEY ([specialty_id]) REFERENCES [specialty] ([specialty_id]);
ALTER TABLE [ledger_entry] ADD CONSTRAINT [FK_ledger_entry_cpt_code_id] FOREIGN KEY ([cpt_code_id]) REFERENCES [cpt_code] ([cpt_code_id]);
ALTER TABLE [ledger_entry] ADD CONSTRAINT [FK_ledger_entry_adjustment_reason_id] FOREIGN KEY ([adjustment_reason_id]) REFERENCES [adjustment_reason] ([adjustment_reason_id]);
ALTER TABLE [ledger_entry] ADD CONSTRAINT [FK_ledger_entry_approved_by_staff_id] FOREIGN KEY ([approved_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [ledger_entry] ADD CONSTRAINT [FK_ledger_entry_reverses_ledger_entry_id] FOREIGN KEY ([reverses_ledger_entry_id]) REFERENCES [ledger_entry] ([ledger_entry_id]);
ALTER TABLE [ledger_entry] ADD CONSTRAINT [FK_ledger_entry_remark_code_id] FOREIGN KEY ([remark_code_id]) REFERENCES [remark_code] ([remark_code_id]);
ALTER TABLE [ledger_entry] ADD CONSTRAINT [FK_ledger_entry_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [ledger_entry] ADD CONSTRAINT [FK_ledger_entry_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [ledger_entry] ADD CONSTRAINT [FK_ledger_entry_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [denial] ADD CONSTRAINT [FK_denial_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [denial] ADD CONSTRAINT [FK_denial_claim_line_id] FOREIGN KEY ([claim_line_id]) REFERENCES [claim_line] ([claim_line_id]);
ALTER TABLE [denial] ADD CONSTRAINT [FK_denial_patient_id] FOREIGN KEY ([patient_id]) REFERENCES [patient] ([patient_id]);
ALTER TABLE [denial] ADD CONSTRAINT [FK_denial_adjustment_reason_id] FOREIGN KEY ([adjustment_reason_id]) REFERENCES [adjustment_reason] ([adjustment_reason_id]);
ALTER TABLE [denial] ADD CONSTRAINT [FK_denial_ledger_entry_id] FOREIGN KEY ([ledger_entry_id]) REFERENCES [ledger_entry] ([ledger_entry_id]);
ALTER TABLE [denial] ADD CONSTRAINT [FK_denial_bill_line_id] FOREIGN KEY ([bill_line_id]) REFERENCES [bill_line] ([bill_line_id]);
ALTER TABLE [denial] ADD CONSTRAINT [FK_denial_cpt_code_id] FOREIGN KEY ([cpt_code_id]) REFERENCES [cpt_code] ([cpt_code_id]);
ALTER TABLE [denial] ADD CONSTRAINT [FK_denial_specialty_id] FOREIGN KEY ([specialty_id]) REFERENCES [specialty] ([specialty_id]);
ALTER TABLE [denial] ADD CONSTRAINT [FK_denial_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [denial] ADD CONSTRAINT [FK_denial_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [denial] ADD CONSTRAINT [FK_denial_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [payment] ADD CONSTRAINT [FK_payment_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [payment] ADD CONSTRAINT [FK_payment_patient_id] FOREIGN KEY ([patient_id]) REFERENCES [patient] ([patient_id]);
ALTER TABLE [payment] ADD CONSTRAINT [FK_payment_edi_file_id] FOREIGN KEY ([edi_file_id]) REFERENCES [edi_file] ([edi_file_id]);
ALTER TABLE [payment] ADD CONSTRAINT [FK_payment_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [payment] ADD CONSTRAINT [FK_payment_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [payment] ADD CONSTRAINT [FK_payment_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [payment_plan] ADD CONSTRAINT [FK_payment_plan_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [payment_plan] ADD CONSTRAINT [FK_payment_plan_patient_id] FOREIGN KEY ([patient_id]) REFERENCES [patient] ([patient_id]);
ALTER TABLE [payment_plan] ADD CONSTRAINT [FK_payment_plan_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [payment_plan] ADD CONSTRAINT [FK_payment_plan_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [payment_plan] ADD CONSTRAINT [FK_payment_plan_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [patient_contact_preference] ADD CONSTRAINT [FK_patient_contact_preference_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [patient_contact_preference] ADD CONSTRAINT [FK_patient_contact_preference_patient_id] FOREIGN KEY ([patient_id]) REFERENCES [patient] ([patient_id]);
ALTER TABLE [patient_contact_preference] ADD CONSTRAINT [FK_patient_contact_preference_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [patient_contact_preference] ADD CONSTRAINT [FK_patient_contact_preference_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [patient_contact_preference] ADD CONSTRAINT [FK_patient_contact_preference_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [denial_reason] ADD CONSTRAINT [FK_denial_reason_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [denial_reason] ADD CONSTRAINT [FK_denial_reason_adjustment_reason_id] FOREIGN KEY ([adjustment_reason_id]) REFERENCES [adjustment_reason] ([adjustment_reason_id]);
ALTER TABLE [denial_reason] ADD CONSTRAINT [FK_denial_reason_remark_code_id] FOREIGN KEY ([remark_code_id]) REFERENCES [remark_code] ([remark_code_id]);
ALTER TABLE [denial_reason] ADD CONSTRAINT [FK_denial_reason_cpt_code_id] FOREIGN KEY ([cpt_code_id]) REFERENCES [cpt_code] ([cpt_code_id]);
ALTER TABLE [denial_reason] ADD CONSTRAINT [FK_denial_reason_claim_line_id] FOREIGN KEY ([claim_line_id]) REFERENCES [claim_line] ([claim_line_id]);
ALTER TABLE [denial_reason] ADD CONSTRAINT [FK_denial_reason_specialty_id] FOREIGN KEY ([specialty_id]) REFERENCES [specialty] ([specialty_id]);
ALTER TABLE [denial_reason] ADD CONSTRAINT [FK_denial_reason_patient_id] FOREIGN KEY ([patient_id]) REFERENCES [patient] ([patient_id]);
ALTER TABLE [denial_reason] ADD CONSTRAINT [FK_denial_reason_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [denial_reason] ADD CONSTRAINT [FK_denial_reason_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [denial_reason] ADD CONSTRAINT [FK_denial_reason_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [ar_interval] ADD CONSTRAINT [FK_ar_interval_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [ar_interval] ADD CONSTRAINT [FK_ar_interval_bill_line_id] FOREIGN KEY ([bill_line_id]) REFERENCES [bill_line] ([bill_line_id]);
ALTER TABLE [ar_interval] ADD CONSTRAINT [FK_ar_interval_patient_id] FOREIGN KEY ([patient_id]) REFERENCES [patient] ([patient_id]);
ALTER TABLE [ar_interval] ADD CONSTRAINT [FK_ar_interval_claim_line_id] FOREIGN KEY ([claim_line_id]) REFERENCES [claim_line] ([claim_line_id]);
ALTER TABLE [ar_interval] ADD CONSTRAINT [FK_ar_interval_specialty_id] FOREIGN KEY ([specialty_id]) REFERENCES [specialty] ([specialty_id]);
ALTER TABLE [ar_interval] ADD CONSTRAINT [FK_ar_interval_cpt_code_id] FOREIGN KEY ([cpt_code_id]) REFERENCES [cpt_code] ([cpt_code_id]);
ALTER TABLE [ar_interval] ADD CONSTRAINT [FK_ar_interval_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [ar_interval] ADD CONSTRAINT [FK_ar_interval_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [ar_interval] ADD CONSTRAINT [FK_ar_interval_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [ar_snapshot] ADD CONSTRAINT [FK_ar_snapshot_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [ar_snapshot] ADD CONSTRAINT [FK_ar_snapshot_patient_id] FOREIGN KEY ([patient_id]) REFERENCES [patient] ([patient_id]);
ALTER TABLE [ar_snapshot] ADD CONSTRAINT [FK_ar_snapshot_specialty_id] FOREIGN KEY ([specialty_id]) REFERENCES [specialty] ([specialty_id]);
ALTER TABLE [ar_snapshot] ADD CONSTRAINT [FK_ar_snapshot_primary_cpt_code_id] FOREIGN KEY ([primary_cpt_code_id]) REFERENCES [cpt_code] ([cpt_code_id]);
ALTER TABLE [ar_snapshot] ADD CONSTRAINT [FK_ar_snapshot_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [ar_snapshot] ADD CONSTRAINT [FK_ar_snapshot_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [ar_snapshot] ADD CONSTRAINT [FK_ar_snapshot_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [appeal] ADD CONSTRAINT [FK_appeal_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [appeal] ADD CONSTRAINT [FK_appeal_agent_decision_id] FOREIGN KEY ([agent_decision_id]) REFERENCES [agent_decision] ([agent_decision_id]);
ALTER TABLE [appeal] ADD CONSTRAINT [FK_appeal_agent_approval_id] FOREIGN KEY ([agent_approval_id]) REFERENCES [agent_approval] ([agent_approval_id]);
ALTER TABLE [appeal] ADD CONSTRAINT [FK_appeal_patient_id] FOREIGN KEY ([patient_id]) REFERENCES [patient] ([patient_id]);
ALTER TABLE [appeal] ADD CONSTRAINT [FK_appeal_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [appeal] ADD CONSTRAINT [FK_appeal_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [appeal] ADD CONSTRAINT [FK_appeal_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [patient_statement] ADD CONSTRAINT [FK_patient_statement_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [patient_statement] ADD CONSTRAINT [FK_patient_statement_patient_id] FOREIGN KEY ([patient_id]) REFERENCES [patient] ([patient_id]);
ALTER TABLE [patient_statement] ADD CONSTRAINT [FK_patient_statement_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [patient_statement] ADD CONSTRAINT [FK_patient_statement_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [patient_statement] ADD CONSTRAINT [FK_patient_statement_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [payment_adjustment] ADD CONSTRAINT [FK_payment_adjustment_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [payment_adjustment] ADD CONSTRAINT [FK_payment_adjustment_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [payment_adjustment] ADD CONSTRAINT [FK_payment_adjustment_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [payment_adjustment] ADD CONSTRAINT [FK_payment_adjustment_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [remittance_claim] ADD CONSTRAINT [FK_remittance_claim_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [remittance_claim] ADD CONSTRAINT [FK_remittance_claim_remark_code_id] FOREIGN KEY ([remark_code_id]) REFERENCES [remark_code] ([remark_code_id]);
ALTER TABLE [remittance_claim] ADD CONSTRAINT [FK_remittance_claim_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [remittance_claim] ADD CONSTRAINT [FK_remittance_claim_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [remittance_claim] ADD CONSTRAINT [FK_remittance_claim_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [bank_deposit] ADD CONSTRAINT [FK_bank_deposit_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [bank_deposit] ADD CONSTRAINT [FK_bank_deposit_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [bank_deposit] ADD CONSTRAINT [FK_bank_deposit_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [bank_deposit] ADD CONSTRAINT [FK_bank_deposit_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [collection_placement] ADD CONSTRAINT [FK_collection_placement_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [collection_placement] ADD CONSTRAINT [FK_collection_placement_patient_id] FOREIGN KEY ([patient_id]) REFERENCES [patient] ([patient_id]);
ALTER TABLE [collection_placement] ADD CONSTRAINT [FK_collection_placement_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [collection_placement] ADD CONSTRAINT [FK_collection_placement_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [collection_placement] ADD CONSTRAINT [FK_collection_placement_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [agent_decision] ADD CONSTRAINT [FK_agent_decision_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [agent_decision] ADD CONSTRAINT [FK_agent_decision_agent_run_id] FOREIGN KEY ([agent_run_id]) REFERENCES [agent_run] ([agent_run_id]);
ALTER TABLE [agent_decision] ADD CONSTRAINT [FK_agent_decision_supersedes_decision_id] FOREIGN KEY ([supersedes_decision_id]) REFERENCES [agent_decision] ([agent_decision_id]);
ALTER TABLE [agent_decision] ADD CONSTRAINT [FK_agent_decision_patient_id] FOREIGN KEY ([patient_id]) REFERENCES [patient] ([patient_id]);
ALTER TABLE [agent_decision] ADD CONSTRAINT [FK_agent_decision_specialty_id] FOREIGN KEY ([specialty_id]) REFERENCES [specialty] ([specialty_id]);
ALTER TABLE [agent_value] ADD CONSTRAINT [FK_agent_value_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [agent_value] ADD CONSTRAINT [FK_agent_value_agent_decision_id] FOREIGN KEY ([agent_decision_id]) REFERENCES [agent_decision] ([agent_decision_id]);
ALTER TABLE [agent_value] ADD CONSTRAINT [FK_agent_value_specialty_id] FOREIGN KEY ([specialty_id]) REFERENCES [specialty] ([specialty_id]);
ALTER TABLE [agent_value] ADD CONSTRAINT [FK_agent_value_cpt_code_id] FOREIGN KEY ([cpt_code_id]) REFERENCES [cpt_code] ([cpt_code_id]);
ALTER TABLE [agent_value] ADD CONSTRAINT [FK_agent_value_ledger_entry_id] FOREIGN KEY ([ledger_entry_id]) REFERENCES [ledger_entry] ([ledger_entry_id]);
ALTER TABLE [agent_run] ADD CONSTRAINT [FK_agent_run_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [agent_run] ADD CONSTRAINT [FK_agent_run_trigger_run_id] FOREIGN KEY ([trigger_run_id]) REFERENCES [agent_run] ([agent_run_id]);
ALTER TABLE [agent_decision_check] ADD CONSTRAINT [FK_agent_decision_check_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [agent_decision_check] ADD CONSTRAINT [FK_agent_decision_check_agent_decision_id] FOREIGN KEY ([agent_decision_id]) REFERENCES [agent_decision] ([agent_decision_id]);
ALTER TABLE [agent_decision_check] ADD CONSTRAINT [FK_agent_decision_check_cpt_code_id] FOREIGN KEY ([cpt_code_id]) REFERENCES [cpt_code] ([cpt_code_id]);
ALTER TABLE [agent_finding] ADD CONSTRAINT [FK_agent_finding_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [agent_finding] ADD CONSTRAINT [FK_agent_finding_agent_run_id] FOREIGN KEY ([agent_run_id]) REFERENCES [agent_run] ([agent_run_id]);
ALTER TABLE [agent_finding] ADD CONSTRAINT [FK_agent_finding_agent_decision_id] FOREIGN KEY ([agent_decision_id]) REFERENCES [agent_decision] ([agent_decision_id]);
ALTER TABLE [agent_finding] ADD CONSTRAINT [FK_agent_finding_patient_id] FOREIGN KEY ([patient_id]) REFERENCES [patient] ([patient_id]);
ALTER TABLE [agent_finding] ADD CONSTRAINT [FK_agent_finding_specialty_id] FOREIGN KEY ([specialty_id]) REFERENCES [specialty] ([specialty_id]);
ALTER TABLE [agent_task] ADD CONSTRAINT [FK_agent_task_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [agent_task] ADD CONSTRAINT [FK_agent_task_agent_decision_id] FOREIGN KEY ([agent_decision_id]) REFERENCES [agent_decision] ([agent_decision_id]);
ALTER TABLE [agent_task] ADD CONSTRAINT [FK_agent_task_assigned_to_staff_id] FOREIGN KEY ([assigned_to_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [agent_task] ADD CONSTRAINT [FK_agent_task_patient_id] FOREIGN KEY ([patient_id]) REFERENCES [patient] ([patient_id]);
ALTER TABLE [agent_task] ADD CONSTRAINT [FK_agent_task_specialty_id] FOREIGN KEY ([specialty_id]) REFERENCES [specialty] ([specialty_id]);
ALTER TABLE [agent_approval] ADD CONSTRAINT [FK_agent_approval_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [agent_approval] ADD CONSTRAINT [FK_agent_approval_agent_decision_id] FOREIGN KEY ([agent_decision_id]) REFERENCES [agent_decision] ([agent_decision_id]);
ALTER TABLE [agent_approval] ADD CONSTRAINT [FK_agent_approval_approved_by_staff_id] FOREIGN KEY ([approved_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [agent_writeback] ADD CONSTRAINT [FK_agent_writeback_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [agent_writeback] ADD CONSTRAINT [FK_agent_writeback_agent_decision_id] FOREIGN KEY ([agent_decision_id]) REFERENCES [agent_decision] ([agent_decision_id]);
ALTER TABLE [agent_writeback] ADD CONSTRAINT [FK_agent_writeback_agent_approval_id] FOREIGN KEY ([agent_approval_id]) REFERENCES [agent_approval] ([agent_approval_id]);
ALTER TABLE [agent_forecast] ADD CONSTRAINT [FK_agent_forecast_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [patient] ADD CONSTRAINT [FK_patient_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [patient] ADD CONSTRAINT [FK_patient_merged_into_patient_id] FOREIGN KEY ([merged_into_patient_id]) REFERENCES [patient] ([patient_id]);
ALTER TABLE [patient] ADD CONSTRAINT [FK_patient_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [patient] ADD CONSTRAINT [FK_patient_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [patient] ADD CONSTRAINT [FK_patient_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [coverage] ADD CONSTRAINT [FK_coverage_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [coverage] ADD CONSTRAINT [FK_coverage_patient_id] FOREIGN KEY ([patient_id]) REFERENCES [patient] ([patient_id]);
ALTER TABLE [coverage] ADD CONSTRAINT [FK_coverage_payer_plan_id] FOREIGN KEY ([payer_plan_id]) REFERENCES [payer_plan] ([payer_plan_id]);
ALTER TABLE [coverage] ADD CONSTRAINT [FK_coverage_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [coverage] ADD CONSTRAINT [FK_coverage_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [coverage] ADD CONSTRAINT [FK_coverage_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [authorization] ADD CONSTRAINT [FK_authorization_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [authorization] ADD CONSTRAINT [FK_authorization_patient_id] FOREIGN KEY ([patient_id]) REFERENCES [patient] ([patient_id]);
ALTER TABLE [authorization] ADD CONSTRAINT [FK_authorization_primary_cpt_code_id] FOREIGN KEY ([primary_cpt_code_id]) REFERENCES [cpt_code] ([cpt_code_id]);
ALTER TABLE [authorization] ADD CONSTRAINT [FK_authorization_diagnosis_code_id] FOREIGN KEY ([diagnosis_code_id]) REFERENCES [diagnosis_code] ([diagnosis_code_id]);
ALTER TABLE [authorization] ADD CONSTRAINT [FK_authorization_place_of_service_id] FOREIGN KEY ([place_of_service_id]) REFERENCES [place_of_service] ([place_of_service_id]);
ALTER TABLE [authorization] ADD CONSTRAINT [FK_authorization_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [authorization] ADD CONSTRAINT [FK_authorization_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [authorization] ADD CONSTRAINT [FK_authorization_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [authorization_line] ADD CONSTRAINT [FK_authorization_line_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [authorization_line] ADD CONSTRAINT [FK_authorization_line_cpt_code_id] FOREIGN KEY ([cpt_code_id]) REFERENCES [cpt_code] ([cpt_code_id]);
ALTER TABLE [authorization_line] ADD CONSTRAINT [FK_authorization_line_cpt_code_to_id] FOREIGN KEY ([cpt_code_to_id]) REFERENCES [cpt_code] ([cpt_code_id]);
ALTER TABLE [authorization_line] ADD CONSTRAINT [FK_authorization_line_modifier_id] FOREIGN KEY ([modifier_id]) REFERENCES [modifier] ([modifier_id]);
ALTER TABLE [authorization_line] ADD CONSTRAINT [FK_authorization_line_patient_id] FOREIGN KEY ([patient_id]) REFERENCES [patient] ([patient_id]);
ALTER TABLE [authorization_line] ADD CONSTRAINT [FK_authorization_line_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [authorization_line] ADD CONSTRAINT [FK_authorization_line_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [authorization_line] ADD CONSTRAINT [FK_authorization_line_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [guarantor] ADD CONSTRAINT [FK_guarantor_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [guarantor] ADD CONSTRAINT [FK_guarantor_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [guarantor] ADD CONSTRAINT [FK_guarantor_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [guarantor] ADD CONSTRAINT [FK_guarantor_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [staff] ADD CONSTRAINT [FK_staff_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [staff] ADD CONSTRAINT [FK_staff_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [staff] ADD CONSTRAINT [FK_staff_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [staff] ADD CONSTRAINT [FK_staff_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [enrollment] ADD CONSTRAINT [FK_enrollment_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [enrollment] ADD CONSTRAINT [FK_enrollment_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [enrollment] ADD CONSTRAINT [FK_enrollment_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [enrollment] ADD CONSTRAINT [FK_enrollment_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [provider_identifier] ADD CONSTRAINT [FK_provider_identifier_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [provider_identifier] ADD CONSTRAINT [FK_provider_identifier_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [provider_identifier] ADD CONSTRAINT [FK_provider_identifier_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [provider_identifier] ADD CONSTRAINT [FK_provider_identifier_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [provider_practice] ADD CONSTRAINT [FK_provider_practice_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [provider_practice] ADD CONSTRAINT [FK_provider_practice_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [provider_practice] ADD CONSTRAINT [FK_provider_practice_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [provider_practice] ADD CONSTRAINT [FK_provider_practice_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [edi_enrollment] ADD CONSTRAINT [FK_edi_enrollment_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [edi_enrollment] ADD CONSTRAINT [FK_edi_enrollment_payer_identifier_id] FOREIGN KEY ([payer_identifier_id]) REFERENCES [payer_identifier] ([payer_identifier_id]);
ALTER TABLE [edi_enrollment] ADD CONSTRAINT [FK_edi_enrollment_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [edi_enrollment] ADD CONSTRAINT [FK_edi_enrollment_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [edi_enrollment] ADD CONSTRAINT [FK_edi_enrollment_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [practice] ADD CONSTRAINT [FK_practice_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [practice] ADD CONSTRAINT [FK_practice_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [practice] ADD CONSTRAINT [FK_practice_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [practice] ADD CONSTRAINT [FK_practice_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [provider] ADD CONSTRAINT [FK_provider_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [provider] ADD CONSTRAINT [FK_provider_specialty_id] FOREIGN KEY ([specialty_id]) REFERENCES [specialty] ([specialty_id]);
ALTER TABLE [provider] ADD CONSTRAINT [FK_provider_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [provider] ADD CONSTRAINT [FK_provider_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [provider] ADD CONSTRAINT [FK_provider_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [payer] ADD CONSTRAINT [FK_payer_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [payer] ADD CONSTRAINT [FK_payer_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [payer] ADD CONSTRAINT [FK_payer_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [payer] ADD CONSTRAINT [FK_payer_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [cpt_code] ADD CONSTRAINT [FK_cpt_code_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [cpt_code] ADD CONSTRAINT [FK_cpt_code_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [diagnosis_code] ADD CONSTRAINT [FK_diagnosis_code_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [diagnosis_code] ADD CONSTRAINT [FK_diagnosis_code_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [modifier] ADD CONSTRAINT [FK_modifier_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [modifier] ADD CONSTRAINT [FK_modifier_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [place_of_service] ADD CONSTRAINT [FK_place_of_service_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [place_of_service] ADD CONSTRAINT [FK_place_of_service_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [specialty] ADD CONSTRAINT [FK_specialty_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [specialty] ADD CONSTRAINT [FK_specialty_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [facility] ADD CONSTRAINT [FK_facility_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [facility] ADD CONSTRAINT [FK_facility_default_place_of_service_id] FOREIGN KEY ([default_place_of_service_id]) REFERENCES [place_of_service] ([place_of_service_id]);
ALTER TABLE [facility] ADD CONSTRAINT [FK_facility_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [facility] ADD CONSTRAINT [FK_facility_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [facility] ADD CONSTRAINT [FK_facility_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [fee_schedule] ADD CONSTRAINT [FK_fee_schedule_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [fee_schedule] ADD CONSTRAINT [FK_fee_schedule_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [fee_schedule] ADD CONSTRAINT [FK_fee_schedule_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [fee_schedule] ADD CONSTRAINT [FK_fee_schedule_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [fee_schedule_line] ADD CONSTRAINT [FK_fee_schedule_line_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [fee_schedule_line] ADD CONSTRAINT [FK_fee_schedule_line_cpt_code_id] FOREIGN KEY ([cpt_code_id]) REFERENCES [cpt_code] ([cpt_code_id]);
ALTER TABLE [fee_schedule_line] ADD CONSTRAINT [FK_fee_schedule_line_modifier_id] FOREIGN KEY ([modifier_id]) REFERENCES [modifier] ([modifier_id]);
ALTER TABLE [fee_schedule_line] ADD CONSTRAINT [FK_fee_schedule_line_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [fee_schedule_line] ADD CONSTRAINT [FK_fee_schedule_line_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [fee_schedule_line] ADD CONSTRAINT [FK_fee_schedule_line_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [contract_rate] ADD CONSTRAINT [FK_contract_rate_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [contract_rate] ADD CONSTRAINT [FK_contract_rate_cpt_code_id] FOREIGN KEY ([cpt_code_id]) REFERENCES [cpt_code] ([cpt_code_id]);
ALTER TABLE [contract_rate] ADD CONSTRAINT [FK_contract_rate_modifier_id] FOREIGN KEY ([modifier_id]) REFERENCES [modifier] ([modifier_id]);
ALTER TABLE [contract_rate] ADD CONSTRAINT [FK_contract_rate_specialty_id] FOREIGN KEY ([specialty_id]) REFERENCES [specialty] ([specialty_id]);
ALTER TABLE [contract_rate] ADD CONSTRAINT [FK_contract_rate_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [contract_rate] ADD CONSTRAINT [FK_contract_rate_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [contract_rate] ADD CONSTRAINT [FK_contract_rate_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [adjustment_reason] ADD CONSTRAINT [FK_adjustment_reason_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [adjustment_reason] ADD CONSTRAINT [FK_adjustment_reason_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [remark_code] ADD CONSTRAINT [FK_remark_code_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [remark_code] ADD CONSTRAINT [FK_remark_code_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [practice_settings] ADD CONSTRAINT [FK_practice_settings_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [practice_settings] ADD CONSTRAINT [FK_practice_settings_approved_by_staff_id] FOREIGN KEY ([approved_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [practice_settings] ADD CONSTRAINT [FK_practice_settings_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [practice_settings] ADD CONSTRAINT [FK_practice_settings_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [practice_settings] ADD CONSTRAINT [FK_practice_settings_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [payer_rule] ADD CONSTRAINT [FK_payer_rule_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [payer_rule] ADD CONSTRAINT [FK_payer_rule_place_of_service_id] FOREIGN KEY ([place_of_service_id]) REFERENCES [place_of_service] ([place_of_service_id]);
ALTER TABLE [payer_rule] ADD CONSTRAINT [FK_payer_rule_cpt_code_id] FOREIGN KEY ([cpt_code_id]) REFERENCES [cpt_code] ([cpt_code_id]);
ALTER TABLE [payer_rule] ADD CONSTRAINT [FK_payer_rule_cpt_code_to_id] FOREIGN KEY ([cpt_code_to_id]) REFERENCES [cpt_code] ([cpt_code_id]);
ALTER TABLE [payer_rule] ADD CONSTRAINT [FK_payer_rule_paired_cpt_code_id] FOREIGN KEY ([paired_cpt_code_id]) REFERENCES [cpt_code] ([cpt_code_id]);
ALTER TABLE [payer_rule] ADD CONSTRAINT [FK_payer_rule_modifier_id] FOREIGN KEY ([modifier_id]) REFERENCES [modifier] ([modifier_id]);
ALTER TABLE [payer_rule] ADD CONSTRAINT [FK_payer_rule_diagnosis_code_id] FOREIGN KEY ([diagnosis_code_id]) REFERENCES [diagnosis_code] ([diagnosis_code_id]);
ALTER TABLE [payer_rule] ADD CONSTRAINT [FK_payer_rule_adjustment_reason_id] FOREIGN KEY ([adjustment_reason_id]) REFERENCES [adjustment_reason] ([adjustment_reason_id]);
ALTER TABLE [payer_rule] ADD CONSTRAINT [FK_payer_rule_approved_by_staff_id] FOREIGN KEY ([approved_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [payer_rule] ADD CONSTRAINT [FK_payer_rule_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [payer_rule] ADD CONSTRAINT [FK_payer_rule_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [payer_rule] ADD CONSTRAINT [FK_payer_rule_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [calendar] ADD CONSTRAINT [FK_calendar_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [calendar] ADD CONSTRAINT [FK_calendar_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [payer_identifier] ADD CONSTRAINT [FK_payer_identifier_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [payer_identifier] ADD CONSTRAINT [FK_payer_identifier_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [payer_identifier] ADD CONSTRAINT [FK_payer_identifier_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [payer_identifier] ADD CONSTRAINT [FK_payer_identifier_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [payer_plan] ADD CONSTRAINT [FK_payer_plan_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [payer_plan] ADD CONSTRAINT [FK_payer_plan_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [payer_plan] ADD CONSTRAINT [FK_payer_plan_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [payer_plan] ADD CONSTRAINT [FK_payer_plan_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [payer_contract] ADD CONSTRAINT [FK_payer_contract_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [payer_contract] ADD CONSTRAINT [FK_payer_contract_payer_plan_id] FOREIGN KEY ([payer_plan_id]) REFERENCES [payer_plan] ([payer_plan_id]);
ALTER TABLE [payer_contract] ADD CONSTRAINT [FK_payer_contract_created_by_staff_id] FOREIGN KEY ([created_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [payer_contract] ADD CONSTRAINT [FK_payer_contract_modified_by_staff_id] FOREIGN KEY ([modified_by_staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [payer_contract] ADD CONSTRAINT [FK_payer_contract_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [claim_status_code] ADD CONSTRAINT [FK_claim_status_code_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [claim_status_code] ADD CONSTRAINT [FK_claim_status_code_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [ndc_code] ADD CONSTRAINT [FK_ndc_code_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [ndc_code] ADD CONSTRAINT [FK_ndc_code_hcpcs_cpt_code_id] FOREIGN KEY ([hcpcs_cpt_code_id]) REFERENCES [cpt_code] ([cpt_code_id]);
ALTER TABLE [ndc_code] ADD CONSTRAINT [FK_ndc_code_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [data_feed] ADD CONSTRAINT [FK_data_feed_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [edi_file] ADD CONSTRAINT [FK_edi_file_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [edi_file] ADD CONSTRAINT [FK_edi_file_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [edi_file] ADD CONSTRAINT [FK_edi_file_replaced_by_edi_file_id] FOREIGN KEY ([replaced_by_edi_file_id]) REFERENCES [edi_file] ([edi_file_id]);
ALTER TABLE [load_batch] ADD CONSTRAINT [FK_load_batch_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [data_quality_result] ADD CONSTRAINT [FK_data_quality_result_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [data_quality_result] ADD CONSTRAINT [FK_data_quality_result_load_batch_id] FOREIGN KEY ([load_batch_id]) REFERENCES [load_batch] ([load_batch_id]);
ALTER TABLE [access_audit] ADD CONSTRAINT [FK_access_audit_tenant_id] FOREIGN KEY ([tenant_id]) REFERENCES [tenant] ([tenant_id]);
ALTER TABLE [access_audit] ADD CONSTRAINT [FK_access_audit_staff_id] FOREIGN KEY ([staff_id]) REFERENCES [staff] ([staff_id]);
ALTER TABLE [access_audit] ADD CONSTRAINT [FK_access_audit_agent_run_id] FOREIGN KEY ([agent_run_id]) REFERENCES [agent_run] ([agent_run_id]);
GO

-- descriptions
EXEC sp_addextendedproperty N'MS_Description', N'One row per appointment version (a cancel or reschedule keeps the old row and adds a new one).', N'SCHEMA', N'dbo', N'TABLE', N'appointment';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of the record: the same on every version. The primary key is (appointment_id, version). Every link from another table uses appointment_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.', N'SCHEMA', N'dbo', N'TABLE', N'appointment', N'COLUMN', N'appointment_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'appointment', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client''s own appointment ID. Restricted: used only to match the source system.', N'SCHEMA', N'dbo', N'TABLE', N'appointment', N'COLUMN', N'appointment_number';
EXEC sp_addextendedproperty N'MS_Description', N'Billing entity.', N'SCHEMA', N'dbo', N'TABLE', N'appointment', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'The patient.', N'SCHEMA', N'dbo', N'TABLE', N'appointment', N'COLUMN', N'patient_id';
EXEC sp_addextendedproperty N'MS_Description', N'Visit date; sets the 3-day and 1-day check timing.', N'SCHEMA', N'dbo', N'TABLE', N'appointment', N'COLUMN', N'appointment_date';
EXEC sp_addextendedproperty N'MS_Description', N'Booked, confirmed, arrived, completed, cancelled, no_show, rescheduled.', N'SCHEMA', N'dbo', N'TABLE', N'appointment', N'COLUMN', N'appointment_status';
EXEC sp_addextendedproperty N'MS_Description', N'Scheduled provider; utilization and no-shows by provider.', N'SCHEMA', N'dbo', N'TABLE', N'appointment', N'COLUMN', N'provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'Insurer on file at booking. Not borrowed from the claim: no claim exists yet, and none ever will for a no-show.', N'SCHEMA', N'dbo', N'TABLE', N'appointment', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'The policy the eligibility check will test.', N'SCHEMA', N'dbo', N'TABLE', N'appointment', N'COLUMN', N'coverage_id';
EXEC sp_addextendedproperty N'MS_Description', N'Site capacity.', N'SCHEMA', N'dbo', N'TABLE', N'appointment', N'COLUMN', N'facility_id';
EXEC sp_addextendedproperty N'MS_Description', N'Day utilization and ordering.', N'SCHEMA', N'dbo', N'TABLE', N'appointment', N'COLUMN', N'start_time';
EXEC sp_addextendedproperty N'MS_Description', N'Lead time; the pre-visit checks key off it.', N'SCHEMA', N'dbo', N'TABLE', N'appointment', N'COLUMN', N'booked_date';
EXEC sp_addextendedproperty N'MS_Description', N'New, follow_up, procedure, preventive, telehealth, emergency.', N'SCHEMA', N'dbo', N'TABLE', N'appointment', N'COLUMN', N'appointment_type';
EXEC sp_addextendedproperty N'MS_Description', N'Phone, portal, walk-in, referral.', N'SCHEMA', N'dbo', N'TABLE', N'appointment', N'COLUMN', N'booked_via';
EXEC sp_addextendedproperty N'MS_Description', N'HMO referrals.', N'SCHEMA', N'dbo', N'TABLE', N'appointment', N'COLUMN', N'referring_provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'The referral this visit was booked under, when there is one.', N'SCHEMA', N'dbo', N'TABLE', N'appointment', N'COLUMN', N'referral_id';
EXEC sp_addextendedproperty N'MS_Description', N'1 for the first row; higher for each change.', N'SCHEMA', N'dbo', N'TABLE', N'appointment', N'COLUMN', N'version';
EXEC sp_addextendedproperty N'MS_Description', N'1 on the latest version. Counts use current rows only.', N'SCHEMA', N'dbo', N'TABLE', N'appointment', N'COLUMN', N'is_current';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.', N'SCHEMA', N'dbo', N'TABLE', N'appointment', N'COLUMN', N'previous_appointment_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'appointment', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'appointment', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'appointment', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'appointment', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'appointment', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'appointment', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'appointment', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'appointment', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'appointment', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'appointment', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One status change of an appointment: from which status to which, when, by whom and why.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_status_log';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_status_log', N'COLUMN', N'appointment_status_log_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_status_log', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The appointment (stable ID).', N'SCHEMA', N'dbo', N'TABLE', N'appointment_status_log', N'COLUMN', N'appointment_id';
EXEC sp_addextendedproperty N'MS_Description', N'Status before the change. Blank on the first row.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_status_log', N'COLUMN', N'from_status';
EXEC sp_addextendedproperty N'MS_Description', N'Status after the change (same values as appointment.appointment_status).', N'SCHEMA', N'dbo', N'TABLE', N'appointment_status_log', N'COLUMN', N'to_status';
EXEC sp_addextendedproperty N'MS_Description', N'When the change happened in the source system (practice local time).', N'SCHEMA', N'dbo', N'TABLE', N'appointment_status_log', N'COLUMN', N'status_changed_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who made the change (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'appointment_status_log', N'COLUMN', N'changed_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'front_desk, phone, portal, online_booking, text_reply, interface, agent.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_status_log', N'COLUMN', N'change_channel';
EXEC sp_addextendedproperty N'MS_Description', N'Coded reason on a cancel, reschedule or no-show. Never free text.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_status_log', N'COLUMN', N'reason_code';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_status_log', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_status_log', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_status_log', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One row per referral into the practice: who referred, which payer and plan, valid dates, visits allowed and used.', N'SCHEMA', N'dbo', N'TABLE', N'referral';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of the record: the same on every version. The primary key is (referral_id, version). Every link from another table uses referral_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.', N'SCHEMA', N'dbo', N'TABLE', N'referral', N'COLUMN', N'referral_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'referral', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The referral number in the EMR or on the payer side. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'referral', N'COLUMN', N'referral_number';
EXEC sp_addextendedproperty N'MS_Description', N'Reports by practice.', N'SCHEMA', N'dbo', N'TABLE', N'referral', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Which patient. Hashed identity only.', N'SCHEMA', N'dbo', N'TABLE', N'referral', N'COLUMN', N'patient_id';
EXEC sp_addextendedproperty N'MS_Description', N'The plan that requires the referral.', N'SCHEMA', N'dbo', N'TABLE', N'referral', N'COLUMN', N'coverage_id';
EXEC sp_addextendedproperty N'MS_Description', N'The payer that issued or requires the referral.', N'SCHEMA', N'dbo', N'TABLE', N'referral', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'The referring clinician (internal provider; the NPI sits on the provider row).', N'SCHEMA', N'dbo', N'TABLE', N'referral', N'COLUMN', N'referring_provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'The clinician in our practice the patient is referred to.', N'SCHEMA', N'dbo', N'TABLE', N'referral', N'COLUMN', N'referred_to_provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'Specialty the referral is for.', N'SCHEMA', N'dbo', N'TABLE', N'referral', N'COLUMN', N'specialty_id';
EXEC sp_addextendedproperty N'MS_Description', N'needed, requested, received, expired, used_up, cancelled.', N'SCHEMA', N'dbo', N'TABLE', N'referral', N'COLUMN', N'referral_status';
EXEC sp_addextendedproperty N'MS_Description', N'When the referral was requested. Request-to-receipt lag.', N'SCHEMA', N'dbo', N'TABLE', N'referral', N'COLUMN', N'request_date';
EXEC sp_addextendedproperty N'MS_Description', N'When the referral arrived.', N'SCHEMA', N'dbo', N'TABLE', N'referral', N'COLUMN', N'received_date';
EXEC sp_addextendedproperty N'MS_Description', N'First date the referral covers.', N'SCHEMA', N'dbo', N'TABLE', N'referral', N'COLUMN', N'valid_from';
EXEC sp_addextendedproperty N'MS_Description', N'Last date the referral covers. Expiry warnings.', N'SCHEMA', N'dbo', N'TABLE', N'referral', N'COLUMN', N'valid_to';
EXEC sp_addextendedproperty N'MS_Description', N'Visits approved.', N'SCHEMA', N'dbo', N'TABLE', N'referral', N'COLUMN', N'visits_allowed';
EXEC sp_addextendedproperty N'MS_Description', N'Visits already used. Visits remaining = allowed - used.', N'SCHEMA', N'dbo', N'TABLE', N'referral', N'COLUMN', N'visits_used';
EXEC sp_addextendedproperty N'MS_Description', N'Diagnosis on the referral.', N'SCHEMA', N'dbo', N'TABLE', N'referral', N'COLUMN', N'diagnosis_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'Service the referral names, when it names one.', N'SCHEMA', N'dbo', N'TABLE', N'referral', N'COLUMN', N'cpt_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'Linked authorization, when the plan needs both.', N'SCHEMA', N'dbo', N'TABLE', N'referral', N'COLUMN', N'authorization_id';
EXEC sp_addextendedproperty N'MS_Description', N'The signed referral document (metadata row).', N'SCHEMA', N'dbo', N'TABLE', N'referral', N'COLUMN', N'document_id';
EXEC sp_addextendedproperty N'MS_Description', N'1 for the first row; higher for each change.', N'SCHEMA', N'dbo', N'TABLE', N'referral', N'COLUMN', N'version';
EXEC sp_addextendedproperty N'MS_Description', N'1 on the latest version. Counts use current rows only.', N'SCHEMA', N'dbo', N'TABLE', N'referral', N'COLUMN', N'is_current';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.', N'SCHEMA', N'dbo', N'TABLE', N'referral', N'COLUMN', N'previous_referral_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'referral', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'referral', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'referral', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'referral', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'referral', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'referral', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'referral', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'referral', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'referral', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'referral', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One row per service planned for the appointment.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_line';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_line', N'COLUMN', N'appointment_line_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_line', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'Ties the planned service to its appointment.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_line', N'COLUMN', N'appointment_id';
EXEC sp_addextendedproperty N'MS_Description', N'Position within the appointment.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_line', N'COLUMN', N'line_number';
EXEC sp_addextendedproperty N'MS_Description', N'Copied from the header, so reports by practice never join up.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_line', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied from the header.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_line', N'COLUMN', N'patient_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied from the header, as of this stage.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_line', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied from the header.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_line', N'COLUMN', N'provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied from the provider''s specialty; fast specialty reports.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_line', N'COLUMN', N'specialty_id';
EXEC sp_addextendedproperty N'MS_Description', N'Drives the authorization check, patient estimate and eligibility service type.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_line', N'COLUMN', N'planned_cpt_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'Whether the planned code was given or guessed, so a guess is never treated as known.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_line', N'COLUMN', N'is_inferred';
EXEC sp_addextendedproperty N'MS_Description', N'Units for the estimate.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_line', N'COLUMN', N'planned_units';
EXEC sp_addextendedproperty N'MS_Description', N'Units x the fee list; estimate and forecast.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_line', N'COLUMN', N'expected_charge';
EXEC sp_addextendedproperty N'MS_Description', N'Contract rate; estimates the patient''s share.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_line', N'COLUMN', N'expected_allowed';
EXEC sp_addextendedproperty N'MS_Description', N'Yes, no, unknown. Unknown is never read as no.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_line', N'COLUMN', N'auth_required';
EXEC sp_addextendedproperty N'MS_Description', N'Authorization on file.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_line', N'COLUMN', N'authorization_id';
EXEC sp_addextendedproperty N'MS_Description', N'Some referrals and authorizations need it.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_line', N'COLUMN', N'planned_diagnosis_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'When a different provider performs the service.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_line', N'COLUMN', N'planned_provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'Capacity planning.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_line', N'COLUMN', N'room_or_equipment';
EXEC sp_addextendedproperty N'MS_Description', N'Slot length.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_line', N'COLUMN', N'duration_minutes';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_line', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'appointment_line', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_line', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'appointment_line', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_line', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_line', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_line', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_line', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_line', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_line', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One row per slot: provider, day, start time, length, type and status. A change of state is a new version.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_slot';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of the record: the same on every version. The primary key is (appointment_slot_id, version). Every link from another table uses appointment_slot_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_slot', N'COLUMN', N'appointment_slot_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_slot', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'Reports by practice.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_slot', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Whose schedule.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_slot', N'COLUMN', N'provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'Slot day.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_slot', N'COLUMN', N'slot_date';
EXEC sp_addextendedproperty N'MS_Description', N'Slot start.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_slot', N'COLUMN', N'start_time';
EXEC sp_addextendedproperty N'MS_Description', N'Slot length.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_slot', N'COLUMN', N'duration_minutes';
EXEC sp_addextendedproperty N'MS_Description', N'Open, booked, held, blocked.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_slot', N'COLUMN', N'slot_status';
EXEC sp_addextendedproperty N'MS_Description', N'The scheduler''s slot ID. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_slot', N'COLUMN', N'slot_number';
EXEC sp_addextendedproperty N'MS_Description', N'Site capacity.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_slot', N'COLUMN', N'facility_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied from the provider.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_slot', N'COLUMN', N'specialty_id';
EXEC sp_addextendedproperty N'MS_Description', N'New_patient, follow_up, procedure, telehealth, any, block.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_slot', N'COLUMN', N'slot_type';
EXEC sp_addextendedproperty N'MS_Description', N'The appointment filling the slot.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_slot', N'COLUMN', N'appointment_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the slot was opened for booking; time to next available.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_slot', N'COLUMN', N'created_date';
EXEC sp_addextendedproperty N'MS_Description', N'Room or equipment.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_slot', N'COLUMN', N'room_or_resource';
EXEC sp_addextendedproperty N'MS_Description', N'Overbooked slot.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_slot', N'COLUMN', N'is_overbook';
EXEC sp_addextendedproperty N'MS_Description', N'1 for the first row; higher for each change.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_slot', N'COLUMN', N'version';
EXEC sp_addextendedproperty N'MS_Description', N'1 on the latest version. Counts use current rows only.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_slot', N'COLUMN', N'is_current';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_slot', N'COLUMN', N'previous_appointment_slot_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_slot', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'appointment_slot', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_slot', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'appointment_slot', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_slot', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_slot', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_slot', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_slot', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_slot', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'appointment_slot', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One 270/271 exchange: the question asked of a payer about a patient''s coverage for a service date, and the answer that came back.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check', N'COLUMN', N'eligibility_check_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'Reference that ties the 270 to its 271 (TRN02). Unique per request: TRG + appointment id + check_sequence (+ -2 on the secondary payer).', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check', N'COLUMN', N'trace_number';
EXEC sp_addextendedproperty N'MS_Description', N'Order of checks for the same appointment and coverage (1, 2, 3 ...). Makes trace_number unique.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check', N'COLUMN', N'check_sequence';
EXEC sp_addextendedproperty N'MS_Description', N'Visit the check was done for.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check', N'COLUMN', N'appointment_id';
EXEC sp_addextendedproperty N'MS_Description', N'Coverage that was checked.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check', N'COLUMN', N'coverage_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied from the coverage so patient history needs no join.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check', N'COLUMN', N'patient_id';
EXEC sp_addextendedproperty N'MS_Description', N'Payer asked.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'Reports by practice.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the check was for the secondary coverage.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check', N'COLUMN', N'is_secondary';
EXEC sp_addextendedproperty N'MS_Description', N'Day the 271 was obtained; age of the check is service date minus this.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check', N'COLUMN', N'check_date';
EXEC sp_addextendedproperty N'MS_Description', N'Exact time of the answer, to tell same-day repeats apart.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check', N'COLUMN', N'check_ts';
EXEC sp_addextendedproperty N'MS_Description', N'Date of service asked about (DTP 291).', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check', N'COLUMN', N'service_date';
EXEC sp_addextendedproperty N'MS_Description', N'Service type asked about (EQ01).', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check', N'COLUMN', N'service_type_code';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the payer says coverage is active (EB 1), 0 when not active (EB 6). Blank when the payer rejected the request; CHECK: is_active is set or is_aaa_reject = 1.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check', N'COLUMN', N'is_active';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the payer answered with an AAA error, for example member not found.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check', N'COLUMN', N'is_aaa_reject';
EXEC sp_addextendedproperty N'MS_Description', N'AAA reason code (43, 72, 75 ...). Tells a typing error from no coverage.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check', N'COLUMN', N'aaa_reason_code';
EXEC sp_addextendedproperty N'MS_Description', N'Plan start date from the answer (DTP 346).', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check', N'COLUMN', N'plan_begin_date';
EXEC sp_addextendedproperty N'MS_Description', N'Plan end date from the answer (DTP 347).', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check', N'COLUMN', N'plan_end_date';
EXEC sp_addextendedproperty N'MS_Description', N'Copay in the answer (EB B). Summary for the checked service type; every benefit line is in eligibility_benefit.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check', N'COLUMN', N'copay_amount';
EXEC sp_addextendedproperty N'MS_Description', N'Coinsurance in the answer (EB A), as a fraction 0 to 1 (0.2000 = 20%).', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check', N'COLUMN', N'coinsurance_pct';
EXEC sp_addextendedproperty N'MS_Description', N'Benefit level of the amounts (EB02): individual, family, employee_spouse.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check', N'COLUMN', N'coverage_level';
EXEC sp_addextendedproperty N'MS_Description', N'In-network Y, out-of-network N, not applicable W (EB12).', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check', N'COLUMN', N'network_indicator';
EXEC sp_addextendedproperty N'MS_Description', N'Deductible left in the answer (EB C).', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check', N'COLUMN', N'deductible_remaining';
EXEC sp_addextendedproperty N'MS_Description', N'Deductible for the plan year (EB C, period 23).', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check', N'COLUMN', N'deductible_total';
EXEC sp_addextendedproperty N'MS_Description', N'Out-of-pocket maximum (EB G).', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check', N'COLUMN', N'oop_max';
EXEC sp_addextendedproperty N'MS_Description', N'Out-of-pocket left (EB G, period 29).', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check', N'COLUMN', N'oop_remaining';
EXEC sp_addextendedproperty N'MS_Description', N'Another payer the answer says is primary (EB R).', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check', N'COLUMN', N'other_payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'1 when a benefit line implies prior authorization for the service type; evidence for the authorization rule.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check', N'COLUMN', N'auth_required_hint';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_check', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One cost estimate given to a patient before service: a good faith estimate (self-pay) or an insured estimate.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of the record: the same on every version. The primary key is (patient_estimate_id, version). Every link from another table uses patient_estimate_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate', N'COLUMN', N'patient_estimate_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The practice''s estimate number. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate', N'COLUMN', N'estimate_number';
EXEC sp_addextendedproperty N'MS_Description', N'The patient.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate', N'COLUMN', N'patient_id';
EXEC sp_addextendedproperty N'MS_Description', N'The visit estimated.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate', N'COLUMN', N'appointment_id';
EXEC sp_addextendedproperty N'MS_Description', N'Coverage used, blank for self-pay.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate', N'COLUMN', N'coverage_id';
EXEC sp_addextendedproperty N'MS_Description', N'gfe_self_pay, insured_estimate, advance_eob.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate', N'COLUMN', N'estimate_type';
EXEC sp_addextendedproperty N'MS_Description', N'When given.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate', N'COLUMN', N'estimate_date';
EXEC sp_addextendedproperty N'MS_Description', N'Planned service date.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate', N'COLUMN', N'service_date';
EXEC sp_addextendedproperty N'MS_Description', N'Total expected charges.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate', N'COLUMN', N'estimated_total';
EXEC sp_addextendedproperty N'MS_Description', N'Patient share expected.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate', N'COLUMN', N'estimated_patient_amount';
EXEC sp_addextendedproperty N'MS_Description', N'mail, portal, email, in_person.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate', N'COLUMN', N'delivered_channel';
EXEC sp_addextendedproperty N'MS_Description', N'When delivered (GFE timing rules).', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate', N'COLUMN', N'delivered_date';
EXEC sp_addextendedproperty N'MS_Description', N'What was billed, rebuilt from bills.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate', N'COLUMN', N'actual_billed_amount';
EXEC sp_addextendedproperty N'MS_Description', N'1 when billed exceeds the good faith estimate by $400 or more (patient may dispute).', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate', N'COLUMN', N'exceeds_gfe_by_400';
EXEC sp_addextendedproperty N'MS_Description', N'Copied, so reports skip the join.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'1 for the first row; higher for each change.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate', N'COLUMN', N'version';
EXEC sp_addextendedproperty N'MS_Description', N'1 on the latest version. Counts use current rows only.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate', N'COLUMN', N'is_current';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One benefit line (EB segment) in a 271 answer: service type, coverage level, network, time period and amount or percent.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_benefit';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_benefit', N'COLUMN', N'eligibility_benefit_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_benefit', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The check it belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_benefit', N'COLUMN', N'eligibility_check_id';
EXEC sp_addextendedproperty N'MS_Description', N'Order in the 271.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_benefit', N'COLUMN', N'benefit_sequence';
EXEC sp_addextendedproperty N'MS_Description', N'EB01: 1 active, 6 inactive, A coinsurance, B copay, C deductible, F limitation, G out-of-pocket, CB coverage basis ...', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_benefit', N'COLUMN', N'eligibility_code';
EXEC sp_addextendedproperty N'MS_Description', N'EB02, same values as eligibility_check.coverage_level.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_benefit', N'COLUMN', N'coverage_level';
EXEC sp_addextendedproperty N'MS_Description', N'EB03 service type (30 health plan, 98 office visit, AL vision, PT physical therapy ...).', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_benefit', N'COLUMN', N'service_type_code';
EXEC sp_addextendedproperty N'MS_Description', N'EB04.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_benefit', N'COLUMN', N'insurance_type_code';
EXEC sp_addextendedproperty N'MS_Description', N'EB05 plan coverage description; no patient text.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_benefit', N'COLUMN', N'plan_description';
EXEC sp_addextendedproperty N'MS_Description', N'EB06: 23 calendar year, 29 remaining, 27 visit, 7 day ...', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_benefit', N'COLUMN', N'time_period_code';
EXEC sp_addextendedproperty N'MS_Description', N'EB07.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_benefit', N'COLUMN', N'benefit_amount';
EXEC sp_addextendedproperty N'MS_Description', N'EB08 as a fraction 0 to 1.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_benefit', N'COLUMN', N'benefit_pct';
EXEC sp_addextendedproperty N'MS_Description', N'EB09: VS visits, DY days ...', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_benefit', N'COLUMN', N'quantity_qualifier';
EXEC sp_addextendedproperty N'MS_Description', N'EB10.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_benefit', N'COLUMN', N'quantity';
EXEC sp_addextendedproperty N'MS_Description', N'EB11 mapped to yes, no, unknown.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_benefit', N'COLUMN', N'auth_required';
EXEC sp_addextendedproperty N'MS_Description', N'EB12: Y, N, W.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_benefit', N'COLUMN', N'network_indicator';
EXEC sp_addextendedproperty N'MS_Description', N'When the benefit is for one procedure (EB13).', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_benefit', N'COLUMN', N'cpt_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied, so reports skip the join.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_benefit', N'COLUMN', N'patient_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied, so reports skip the join.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_benefit', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied, so reports skip the join.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_benefit', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_benefit', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_benefit', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_benefit', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_benefit', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_benefit', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_benefit', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_benefit', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_benefit', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_benefit', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'eligibility_benefit', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One item on a patient estimate: code, diagnosis, provider or facility, units and expected charge.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate_line';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate_line', N'COLUMN', N'patient_estimate_line_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate_line', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The estimate (stable ID).', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate_line', N'COLUMN', N'patient_estimate_id';
EXEC sp_addextendedproperty N'MS_Description', N'Position.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate_line', N'COLUMN', N'line_number';
EXEC sp_addextendedproperty N'MS_Description', N'Service code.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate_line', N'COLUMN', N'cpt_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'Modifier.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate_line', N'COLUMN', N'modifier_id';
EXEC sp_addextendedproperty N'MS_Description', N'Expected diagnosis (required on a GFE).', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate_line', N'COLUMN', N'diagnosis_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'Provider expected to perform it.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate_line', N'COLUMN', N'provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'Facility, for facility items.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate_line', N'COLUMN', N'facility_id';
EXEC sp_addextendedproperty N'MS_Description', N'1 when another provider or facility supplied the item (co-provider GFE).', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate_line', N'COLUMN', N'is_co_provider_item';
EXEC sp_addextendedproperty N'MS_Description', N'Expected units.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate_line', N'COLUMN', N'units';
EXEC sp_addextendedproperty N'MS_Description', N'Expected charge.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate_line', N'COLUMN', N'expected_charge';
EXEC sp_addextendedproperty N'MS_Description', N'Patient share for the line.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate_line', N'COLUMN', N'expected_patient_amount';
EXEC sp_addextendedproperty N'MS_Description', N'The planned service it came from.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate_line', N'COLUMN', N'appointment_line_id';
EXEC sp_addextendedproperty N'MS_Description', N'What was billed for the item, rebuilt from bill lines.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate_line', N'COLUMN', N'billed_amount';
EXEC sp_addextendedproperty N'MS_Description', N'Copied, so reports skip the join.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate_line', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate_line', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate_line', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate_line', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate_line', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate_line', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate_line', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate_line', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate_line', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate_line', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'patient_estimate_line', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One row per visit version.', N'SCHEMA', N'dbo', N'TABLE', N'encounter';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of the record: the same on every version. The primary key is (encounter_id, version). Every link from another table uses encounter_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'encounter_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client''s own visit ID. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'encounter_number';
EXEC sp_addextendedproperty N'MS_Description', N'Billing entity.', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'The patient.', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'patient_id';
EXEC sp_addextendedproperty N'MS_Description', N'Date of service; bill lag and timely filing start here.', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'encounter_date';
EXEC sp_addextendedproperty N'MS_Description', N'Who saw the patient; productivity and documentation owner.', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'rendering_provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'In progress, completed, note pending, signed, charge ready.', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'encounter_status';
EXEC sp_addextendedproperty N'MS_Description', N'Appointment-to-visit conversion. Blank for walk-ins.', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'appointment_id';
EXEC sp_addextendedproperty N'MS_Description', N'Insurer at the visit; eligibility on the date of service.', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'The policy in force at the visit.', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'coverage_id';
EXEC sp_addextendedproperty N'MS_Description', N'Site reporting.', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'facility_id';
EXEC sp_addextendedproperty N'MS_Description', N'Pricing differences.', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'place_of_service_id';
EXEC sp_addextendedproperty N'MS_Description', N'Specialty reports.', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'specialty_id';
EXEC sp_addextendedproperty N'MS_Description', N'New, established, preventive, emergency, telehealth; sets the expected visit level.', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'encounter_type';
EXEC sp_addextendedproperty N'MS_Description', N'Time-based coding; productivity.', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'visit_minutes';
EXEC sp_addextendedproperty N'MS_Description', N'None, draft, signed, amended. Counts only, never note text. Rebuilt from the note records.', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'note_status';
EXEC sp_addextendedproperty N'MS_Description', N'Signature timing.', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'note_signed_date';
EXEC sp_addextendedproperty N'MS_Description', N'Visit to signed note.', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'signature_lag_days';
EXEC sp_addextendedproperty N'MS_Description', N'Count of note elements present (rows in document_element); documentation completeness.', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'elements_documented_count';
EXEC sp_addextendedproperty N'MS_Description', N'Not entered, entered, held, billed. Detects bill lag and missed charges.', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'charge_status';
EXEC sp_addextendedproperty N'MS_Description', N'Not reviewed, suggested, accepted, changed.', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'coding_status';
EXEC sp_addextendedproperty N'MS_Description', N'Condition-level analysis; the line-level diagnoses are in the details.', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'principal_diagnosis_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'Ties the visit to its authorization.', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'authorization_id';
EXEC sp_addextendedproperty N'MS_Description', N'Supervised visits.', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'supervising_provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'HMO referrals.', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'referring_provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'The referral this visit was performed under, when there is one.', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'referral_id';
EXEC sp_addextendedproperty N'MS_Description', N'1 for the first row; higher for each change.', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'version';
EXEC sp_addextendedproperty N'MS_Description', N'1 on the latest version. Counts use current rows only.', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'is_current';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'previous_encounter_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'encounter', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One row per clinical or administrative document in the EMR (visit note, consent, advance notice, plan of care, result, letter, document pack): who, when, status, signatures. Never the content.', N'SCHEMA', N'dbo', N'TABLE', N'document';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of the record: the same on every version. The primary key is (document_id, version). Every link from another table uses document_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'document_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The EMR''s own ID for the note or document. Makes loads repeatable. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'document_number';
EXEC sp_addextendedproperty N'MS_Description', N'Reports by practice.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Which patient''s chart. Hashed identity only.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'patient_id';
EXEC sp_addextendedproperty N'MS_Description', N'Broad family: note, consent, notice, plan_of_care, order_document, referral_document, result, letter, pack. Lets agents ask for all notes or all consents.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'document_class';
EXEC sp_addextendedproperty N'MS_Description', N'Specific type: progress_note, procedure_note, consult, discharge, telephone, addendum, treatment_consent, telehealth_consent, financial_consent, release_of_information, advance_notice, lab_result, imaging_result, letter_of_medical_necessity, cover_note and so on.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'document_type';
EXEC sp_addextendedproperty N'MS_Description', N'Where the document stands: not_started, draft, pended, signed, locked, amended, entered_in_error; for consents and notices on_file, missing, expired, withdrawn; for results received, reviewed. Drives the chase list.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'document_status';
EXEC sp_addextendedproperty N'MS_Description', N'The visit the document belongs to. Blank for a standing consent.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'encounter_id';
EXEC sp_addextendedproperty N'MS_Description', N'The authorization request the document supports (the supporting-information link). Blank otherwise.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'authorization_id';
EXEC sp_addextendedproperty N'MS_Description', N'The claim the document supports, for attachments and records requests. Blank otherwise.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'claim_id';
EXEC sp_addextendedproperty N'MS_Description', N'The clinician who wrote or signed it (internal provider, never a name).', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'author_provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'Role of the signer: physician, nurse_practitioner, physician_assistant, resident, therapist, other. Supervision and incident-to rules depend on it.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'signer_role';
EXEC sp_addextendedproperty N'MS_Description', N'Date the document was started (note date, consent date). Late entries are measured against the visit date.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'document_date';
EXEC sp_addextendedproperty N'MS_Description', N'Date and time of the signature. Signature lag and the time of day a note is signed.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'signed_at';
EXEC sp_addextendedproperty N'MS_Description', N'1 if written well after the visit. Payers question late notes.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'is_late_entry';
EXEC sp_addextendedproperty N'MS_Description', N'1 if this row is a later addition to a signed note. The date of the addendum is its signed_at.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'is_addendum';
EXEC sp_addextendedproperty N'MS_Description', N'The original note this addendum adds to.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'addendum_of_document_id';
EXEC sp_addextendedproperty N'MS_Description', N'1 if the document is locked and cannot be edited. A locked unsigned note is a different fix.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'is_locked';
EXEC sp_addextendedproperty N'MS_Description', N'1 if a second signature is needed (supervision rule).', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'cosign_required';
EXEC sp_addextendedproperty N'MS_Description', N'not_needed, pending or done.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'cosign_status';
EXEC sp_addextendedproperty N'MS_Description', N'When the co-signature was added.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'cosigned_at';
EXEC sp_addextendedproperty N'MS_Description', N'When a consent or plan of care stops being valid.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'expiry_date';
EXEC sp_addextendedproperty N'MS_Description', N'Minutes written in the note; compared with visit minutes for time-based codes.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'minutes_documented';
EXEC sp_addextendedproperty N'MS_Description', N'Number of history-of-present-illness details found; supports the code-level check.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'hpi_component_count';
EXEC sp_addextendedproperty N'MS_Description', N'Number of body systems reviewed; supports the code-level check.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'ros_system_count';
EXEC sp_addextendedproperty N'MS_Description', N'Problems addressed: minimal, low, moderate or high (decision-making input).', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'mdm_problem_level';
EXEC sp_addextendedproperty N'MS_Description', N'Data reviewed: minimal, limited, moderate or extensive.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'mdm_data_level';
EXEC sp_addextendedproperty N'MS_Description', N'Risk of management: minimal, low, moderate or high.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'mdm_risk_level';
EXEC sp_addextendedproperty N'MS_Description', N'SHA-256 hash of the document. Proves the same text was signed, sent or changed, without keeping it.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'content_hash';
EXEC sp_addextendedproperty N'MS_Description', N'Pages in the document or pack.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'page_count';
EXEC sp_addextendedproperty N'MS_Description', N'Standard code for the type (LOINC or the claim-attachment report type) when the payer needs it.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'document_type_code';
EXEC sp_addextendedproperty N'MS_Description', N'How readable the source is: structured, free_text, scanned_image, dictation. Scanned notes cannot be checked for elements.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'source_quality';
EXEC sp_addextendedproperty N'MS_Description', N'1 for the first row; higher for each change.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'version';
EXEC sp_addextendedproperty N'MS_Description', N'1 on the latest version. Counts use current rows only.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'is_current';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'previous_document_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'document', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One row per clinical order (lab, imaging, procedure, equipment, therapy, referral out), with its status and the result status. Reserved word in SQL: always quoted.', N'SCHEMA', N'dbo', N'TABLE', N'clinical_order';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of the record: the same on every version. The primary key is (clinical_order_id, version). Every link from another table uses clinical_order_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.', N'SCHEMA', N'dbo', N'TABLE', N'clinical_order', N'COLUMN', N'clinical_order_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'clinical_order', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The order number in the EMR. Makes loads repeatable. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'clinical_order', N'COLUMN', N'order_number';
EXEC sp_addextendedproperty N'MS_Description', N'Reports by practice.', N'SCHEMA', N'dbo', N'TABLE', N'clinical_order', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Which patient. Hashed identity only.', N'SCHEMA', N'dbo', N'TABLE', N'clinical_order', N'COLUMN', N'patient_id';
EXEC sp_addextendedproperty N'MS_Description', N'The visit the order came from.', N'SCHEMA', N'dbo', N'TABLE', N'clinical_order', N'COLUMN', N'encounter_id';
EXEC sp_addextendedproperty N'MS_Description', N'The visit line that records the order (line_status = ordered). From here, billing lines show whether a charge followed.', N'SCHEMA', N'dbo', N'TABLE', N'clinical_order', N'COLUMN', N'encounter_line_id';
EXEC sp_addextendedproperty N'MS_Description', N'Who ordered (internal provider, never a name).', N'SCHEMA', N'dbo', N'TABLE', N'clinical_order', N'COLUMN', N'ordering_provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'lab, imaging, procedure, equipment, therapy, referral.', N'SCHEMA', N'dbo', N'TABLE', N'clinical_order', N'COLUMN', N'order_type';
EXEC sp_addextendedproperty N'MS_Description', N'draft, active, signed, completed, cancelled.', N'SCHEMA', N'dbo', N'TABLE', N'clinical_order', N'COLUMN', N'order_status';
EXEC sp_addextendedproperty N'MS_Description', N'Date the order was placed.', N'SCHEMA', N'dbo', N'TABLE', N'clinical_order', N'COLUMN', N'order_date';
EXEC sp_addextendedproperty N'MS_Description', N'When the order was signed. Unsigned orders are often not payable.', N'SCHEMA', N'dbo', N'TABLE', N'clinical_order', N'COLUMN', N'signed_date';
EXEC sp_addextendedproperty N'MS_Description', N'What was ordered, when a code is known.', N'SCHEMA', N'dbo', N'TABLE', N'clinical_order', N'COLUMN', N'cpt_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'Main diagnosis written on the order (medical necessity).', N'SCHEMA', N'dbo', N'TABLE', N'clinical_order', N'COLUMN', N'diagnosis_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'The authorization that covers the order, if one was needed.', N'SCHEMA', N'dbo', N'TABLE', N'clinical_order', N'COLUMN', N'authorization_id';
EXEC sp_addextendedproperty N'MS_Description', N'yes, no or unknown: whether the order needs an authorization.', N'SCHEMA', N'dbo', N'TABLE', N'clinical_order', N'COLUMN', N'auth_required';
EXEC sp_addextendedproperty N'MS_Description', N'The signed order document (metadata row).', N'SCHEMA', N'dbo', N'TABLE', N'clinical_order', N'COLUMN', N'document_id';
EXEC sp_addextendedproperty N'MS_Description', N'pending, received or reviewed. Orders without a reviewed result may need a follow-up.', N'SCHEMA', N'dbo', N'TABLE', N'clinical_order', N'COLUMN', N'result_status';
EXEC sp_addextendedproperty N'MS_Description', N'When the result came back.', N'SCHEMA', N'dbo', N'TABLE', N'clinical_order', N'COLUMN', N'result_received_date';
EXEC sp_addextendedproperty N'MS_Description', N'The result document (metadata row).', N'SCHEMA', N'dbo', N'TABLE', N'clinical_order', N'COLUMN', N'result_document_id';
EXEC sp_addextendedproperty N'MS_Description', N'1 for the first row; higher for each change.', N'SCHEMA', N'dbo', N'TABLE', N'clinical_order', N'COLUMN', N'version';
EXEC sp_addextendedproperty N'MS_Description', N'1 on the latest version. Counts use current rows only.', N'SCHEMA', N'dbo', N'TABLE', N'clinical_order', N'COLUMN', N'is_current';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.', N'SCHEMA', N'dbo', N'TABLE', N'clinical_order', N'COLUMN', N'previous_clinical_order_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'clinical_order', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'clinical_order', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'clinical_order', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'clinical_order', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'clinical_order', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'clinical_order', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'clinical_order', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'clinical_order', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'clinical_order', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'clinical_order', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One row per service performed at the visit.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'encounter_line_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'Ties each performed service to its visit.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'encounter_id';
EXEC sp_addextendedproperty N'MS_Description', N'Position within the visit.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'line_number';
EXEC sp_addextendedproperty N'MS_Description', N'Copied from the header, so reports by practice never join up.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied from the header.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'patient_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied from the header, as of this stage.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied from the header.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied from the provider''s specialty; fast specialty reports.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'specialty_id';
EXEC sp_addextendedproperty N'MS_Description', N'The service performed, as entered. The coder''s suggestion lives in the coding review records; the final code sits on the bill line.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'cpt_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'Quantity performed.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'units';
EXEC sp_addextendedproperty N'MS_Description', N'Per-line date for multi-day services.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'service_date';
EXEC sp_addextendedproperty N'MS_Description', N'When another clinician performed this line.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'rendering_provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'Main diagnosis supporting this service; medical-necessity checks.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'diagnosis_1_id';
EXEC sp_addextendedproperty N'MS_Description', N'Second diagnosis.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'diagnosis_2_id';
EXEC sp_addextendedproperty N'MS_Description', N'Third diagnosis.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'diagnosis_3_id';
EXEC sp_addextendedproperty N'MS_Description', N'Fourth diagnosis.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'diagnosis_4_id';
EXEC sp_addextendedproperty N'MS_Description', N'Pricing and common denial causes.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'modifier_1_id';
EXEC sp_addextendedproperty N'MS_Description', N'Second modifier.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'modifier_2_id';
EXEC sp_addextendedproperty N'MS_Description', N'Third modifier.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'modifier_3_id';
EXEC sp_addextendedproperty N'MS_Description', N'Fourth modifier.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'modifier_4_id';
EXEC sp_addextendedproperty N'MS_Description', N'Left, right, both. Required for many codes; a common denial.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'laterality';
EXEC sp_addextendedproperty N'MS_Description', N'Whether the note supports the procedure. Worked out from the note records.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'procedure_documented';
EXEC sp_addextendedproperty N'MS_Description', N'Visit level (1 to 5) the note supports; compared with the level entered. A number only.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'documented_level';
EXEC sp_addextendedproperty N'MS_Description', N'Units for timed codes.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'time_minutes';
EXEC sp_addextendedproperty N'MS_Description', N'Authorization coverage per service.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'authorization_id';
EXEC sp_addextendedproperty N'MS_Description', N'Yes, no, unknown.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'auth_required';
EXEC sp_addextendedproperty N'MS_Description', N'Performed, ordered, not done.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'line_status';
EXEC sp_addextendedproperty N'MS_Description', N'Units x fee list; the missed-charge value.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'expected_charge';
EXEC sp_addextendedproperty N'MS_Description', N'When different from the visit.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'place_of_service_id';
EXEC sp_addextendedproperty N'MS_Description', N'Who ordered it.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'ordering_provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'Drug-billing specialties.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'drug_code';
EXEC sp_addextendedproperty N'MS_Description', N'Reference row for drug_code.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'ndc_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_line', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One diagnosis recorded for a visit.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_diagnosis';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_diagnosis', N'COLUMN', N'encounter_diagnosis_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_diagnosis', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The visit (stable ID).', N'SCHEMA', N'dbo', N'TABLE', N'encounter_diagnosis', N'COLUMN', N'encounter_id';
EXEC sp_addextendedproperty N'MS_Description', N'Order on the visit.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_diagnosis', N'COLUMN', N'diagnosis_sequence';
EXEC sp_addextendedproperty N'MS_Description', N'The ICD-10-CM code.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_diagnosis', N'COLUMN', N'diagnosis_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'1 on the principal diagnosis.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_diagnosis', N'COLUMN', N'is_principal';
EXEC sp_addextendedproperty N'MS_Description', N'billing, chief_complaint, comorbidity, admitting.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_diagnosis', N'COLUMN', N'diagnosis_role';
EXEC sp_addextendedproperty N'MS_Description', N'Copied, so reports skip the join.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_diagnosis', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied, so reports skip the join.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_diagnosis', N'COLUMN', N'patient_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_diagnosis', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'encounter_diagnosis', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_diagnosis', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'encounter_diagnosis', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_diagnosis', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_diagnosis', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_diagnosis', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_diagnosis', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_diagnosis', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'encounter_diagnosis', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One named element checked in one document: present or not.', N'SCHEMA', N'dbo', N'TABLE', N'document_element';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'document_element', N'COLUMN', N'document_element_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'document_element', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The document (stable ID).', N'SCHEMA', N'dbo', N'TABLE', N'document_element', N'COLUMN', N'document_id';
EXEC sp_addextendedproperty N'MS_Description', N'chief_complaint, history_present, exam, assessment, plan, diagnosis_linked, procedure_note, laterality, result, medical_necessity, mdm, telehealth_statements.', N'SCHEMA', N'dbo', N'TABLE', N'document_element', N'COLUMN', N'element_code';
EXEC sp_addextendedproperty N'MS_Description', N'1 if found.', N'SCHEMA', N'dbo', N'TABLE', N'document_element', N'COLUMN', N'is_present';
EXEC sp_addextendedproperty N'MS_Description', N'Copied, so reports skip the join.', N'SCHEMA', N'dbo', N'TABLE', N'document_element', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'document_element', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'document_element', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'document_element', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'document_element', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'document_element', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'document_element', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'document_element', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'document_element', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'document_element', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'document_element', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One row per bill, normally one per visit. Late charges are added as lines.', N'SCHEMA', N'dbo', N'TABLE', N'bill';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of the record: the same on every version. The primary key is (bill_id, version). Every link from another table uses bill_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'bill_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client''s own charge or bill ID. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'bill_number';
EXEC sp_addextendedproperty N'MS_Description', N'Billing entity.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'The patient.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'patient_id';
EXEC sp_addextendedproperty N'MS_Description', N'Ties the bill to the visit.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'encounter_id';
EXEC sp_addextendedproperty N'MS_Description', N'Start of bill lag and timely filing.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'service_date';
EXEC sp_addextendedproperty N'MS_Description', N'First entry. Bill lag is this minus the service date.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'charge_entered_date';
EXEC sp_addextendedproperty N'MS_Description', N'Drafted, held, ready, billed, partly_billed, patient_billed, written_off, voided. Worked out, not typed.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'bill_status';
EXEC sp_addextendedproperty N'MS_Description', N'Insurance, self_pay, courtesy, workers_comp_or_auto. Explains why some bills never become a claim.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'bill_type';
EXEC sp_addextendedproperty N'MS_Description', N'Gross charges: sum of lines.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'total_billed';
EXEC sp_addextendedproperty N'MS_Description', N'Billing enrollment; charges by provider.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'billing_provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'Who performed the service.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'rendering_provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'Specialty reports.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'specialty_id';
EXEC sp_addextendedproperty N'MS_Description', N'Where the bill will go first.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'Policy to bill.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'coverage_id';
EXEC sp_addextendedproperty N'MS_Description', N'Site reporting.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'facility_id';
EXEC sp_addextendedproperty N'MS_Description', N'Pricing.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'place_of_service_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the note is signed and coding is done. Splits bill lag into documentation delay and billing delay.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'ready_to_bill_date';
EXEC sp_addextendedproperty N'MS_Description', N'Missing note, authorization, coding or diagnosis.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'hold_reason';
EXEC sp_addextendedproperty N'MS_Description', N'When the hold began.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'hold_date';
EXEC sp_addextendedproperty N'MS_Description', N'Late charges added after the first entry.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'last_charge_date';
EXEC sp_addextendedproperty N'MS_Description', N'Claim rollup: shows billed-but-not-claimed. Rebuilt from the claim table.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'claims_created';
EXEC sp_addextendedproperty N'MS_Description', N'Claim rollup.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'latest_claim_status';
EXEC sp_addextendedproperty N'MS_Description', N'Bill-to-claim lag.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'first_claim_submitted_date';
EXEC sp_addextendedproperty N'MS_Description', N'Expected revenue before payment.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'expected_allowed';
EXEC sp_addextendedproperty N'MS_Description', N'Productivity by role.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'entered_by_role';
EXEC sp_addextendedproperty N'MS_Description', N'Courtesy or write-off before a claim.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'no_charge_amount';
EXEC sp_addextendedproperty N'MS_Description', N'Billed to the patient.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'patient_statement_flag';
EXEC sp_addextendedproperty N'MS_Description', N'1 for the first row; higher for each change.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'version';
EXEC sp_addextendedproperty N'MS_Description', N'1 on the latest version. Counts use current rows only.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'is_current';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'previous_bill_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'bill', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One row per claim submission to a payer (a replacement is a new row).', N'SCHEMA', N'dbo', N'TABLE', N'claim';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of the record: the same on every version. The primary key is (claim_id, version). Every link from another table uses claim_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'claim_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client''s claim ID (CLM01). Joins the 837, 277CA, 835 and PM. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'claim_number';
EXEC sp_addextendedproperty N'MS_Description', N'All reports by practice.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Who we billed.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'Duplicates; patient-level balances.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'patient_id';
EXEC sp_addextendedproperty N'MS_Description', N'Whose NPI and tax ID billed; enrollment problems.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'billing_provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'Timely filing, aging.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'service_date_from';
EXEC sp_addextendedproperty N'MS_Description', N'Last date of service on the claim (multi-day services).', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'service_date_to';
EXEC sp_addextendedproperty N'MS_Description', N'Claim lag, days in AR.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'submitted_date';
EXEC sp_addextendedproperty N'MS_Description', N'Base for denial and collection rates. Must equal the sum of the lines.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'total_charge';
EXEC sp_addextendedproperty N'MS_Description', N'Submitted, accepted, rejected, pending, paid, partly_paid, denied, closed, voided. The work queue filter.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'claim_status';
EXEC sp_addextendedproperty N'MS_Description', N'Denials and productivity by provider.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'rendering_provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'Supervising provider (2310D), for incident-to and mid-level billing.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'supervising_provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'Site reporting.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'facility_id';
EXEC sp_addextendedproperty N'MS_Description', N'Pricing differences.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'place_of_service_id';
EXEC sp_addextendedproperty N'MS_Description', N'Specialty reports.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'specialty_id';
EXEC sp_addextendedproperty N'MS_Description', N'Policy billed.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'coverage_id';
EXEC sp_addextendedproperty N'MS_Description', N'Primary, secondary, tertiary: secondary billing and coordination of benefits.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'claim_sequence';
EXEC sp_addextendedproperty N'MS_Description', N'For a secondary or tertiary claim: the claim to the payer before it.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'primary_claim_id';
EXEC sp_addextendedproperty N'MS_Description', N'What earlier payers paid (2320 AMT*D), sent on secondary claims.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'other_payer_paid_amount';
EXEC sp_addextendedproperty N'MS_Description', N'Insurance type on the claim (SBR09: CI commercial, MB Medicare Part B, MC Medicaid, HM HMO ...).', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'claim_filing_indicator';
EXEC sp_addextendedproperty N'MS_Description', N'1 original, 7 replacement, 8 void: so resubmits do not double-count.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'frequency_code';
EXEC sp_addextendedproperty N'MS_Description', N'Provider accepts assignment (CLM07: A, B, C).', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'accept_assignment';
EXEC sp_addextendedproperty N'MS_Description', N'Patient assigned benefits to the provider (CLM08: Y, N, W).', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'benefits_assigned';
EXEC sp_addextendedproperty N'MS_Description', N'Release of information code (CLM09: I, Y).', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'release_of_info';
EXEC sp_addextendedproperty N'MS_Description', N'Payer''s claim number (ICN). Matches appeals and resubmits. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'payer_claim_number';
EXEC sp_addextendedproperty N'MS_Description', N'Payer claim number of the claim being replaced or voided (REF*F8). Required on frequency 7 and 8.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'original_payer_claim_number';
EXEC sp_addextendedproperty N'MS_Description', N'Traces the claim back to the charge.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'bill_id';
EXEC sp_addextendedproperty N'MS_Description', N'Traces the claim back to the visit.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'encounter_id';
EXEC sp_addextendedproperty N'MS_Description', N'Condition-level analysis.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'principal_diagnosis_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'REF*G1: ties an authorization to the claim; reason code 197 denials. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'prior_auth_number';
EXEC sp_addextendedproperty N'MS_Description', N'Internal link to the authorization.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'authorization_id';
EXEC sp_addextendedproperty N'MS_Description', N'Rollup of payments. Rebuilt nightly; never the source of truth.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'paid_amount';
EXEC sp_addextendedproperty N'MS_Description', N'Rollup: patient share.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'patient_responsibility';
EXEC sp_addextendedproperty N'MS_Description', N'Rollup: contractual write-downs.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'adjusted_amount';
EXEC sp_addextendedproperty N'MS_Description', N'Rollup: denied.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'denied_amount';
EXEC sp_addextendedproperty N'MS_Description', N'Rollup: still open.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'balance';
EXEC sp_addextendedproperty N'MS_Description', N'Rollup: latest payment.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'last_payment_date';
EXEC sp_addextendedproperty N'MS_Description', N'Rollup: latest status event.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'last_status_date';
EXEC sp_addextendedproperty N'MS_Description', N'Professional (837P). Institutional (837I) is out of scope in this version; the value is reserved until its fields are added.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'claim_type';
EXEC sp_addextendedproperty N'MS_Description', N'Accident indicator; some specialties.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'accident_related';
EXEC sp_addextendedproperty N'MS_Description', N'Referral; some specialties.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'referring_provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'The referral the claim is billed under.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'referral_id';
EXEC sp_addextendedproperty N'MS_Description', N'Referral number sent on the claim (REF*9F). Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'referral_number';
EXEC sp_addextendedproperty N'MS_Description', N'Batch control number as sent; the file is edi_file_id.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'batch_control_number';
EXEC sp_addextendedproperty N'MS_Description', N'The 837 file the claim went out in.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'edi_file_id';
EXEC sp_addextendedproperty N'MS_Description', N'Y, N or U (unknown): the provider''s signature is on file, as the 837 states.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'signature_on_file';
EXEC sp_addextendedproperty N'MS_Description', N'Date the condition began, when the claim states one.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'onset_date';
EXEC sp_addextendedproperty N'MS_Description', N'Our internal reason a late claim is still acceptable (payer error, coverage dispute). The coded value sent on the claim is delay_reason_code.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'late_filing_reason';
EXEC sp_addextendedproperty N'MS_Description', N'X12 delay reason code (CLM20) sent on a late claim.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'delay_reason_code';
EXEC sp_addextendedproperty N'MS_Description', N'1 for the first row; higher for each change.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'version';
EXEC sp_addextendedproperty N'MS_Description', N'1 on the latest version. Counts use current rows only.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'is_current';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'previous_claim_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'claim', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One row per payer records request or attachment announcement for one claim: what was asked, when it is due, what we sent, and the payer''s answer.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of the record: the same on every version. The primary key is (claim_attachment_id, version). Every link from another table uses claim_attachment_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment', N'COLUMN', N'claim_attachment_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'Our ID for this request or attachment row. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment', N'COLUMN', N'claim_attachment_number';
EXEC sp_addextendedproperty N'MS_Description', N'Reports by practice.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Which patient. Hashed identity only.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment', N'COLUMN', N'patient_id';
EXEC sp_addextendedproperty N'MS_Description', N'The claim the request or attachment is about.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment', N'COLUMN', N'claim_id';
EXEC sp_addextendedproperty N'MS_Description', N'The payer that asked for the records or receives the attachment.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'pre_payment_review, post_payment_audit, attachment_request, medical_review, attachment_announcement (sent with the claim), other.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment', N'COLUMN', N'request_type';
EXEC sp_addextendedproperty N'MS_Description', N'The payer''s reference for the request; groups rows from one request. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment', N'COLUMN', N'payer_reference_number';
EXEC sp_addextendedproperty N'MS_Description', N'Review unit or audit vendor, for example medical_review, audit_vendor.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment', N'COLUMN', N'requesting_unit';
EXEC sp_addextendedproperty N'MS_Description', N'Date the request arrived.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment', N'COLUMN', N'request_received_date';
EXEC sp_addextendedproperty N'MS_Description', N'How it arrived: mail, fax, portal, 277, emr_inbox, phone.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment', N'COLUMN', N'request_channel';
EXEC sp_addextendedproperty N'MS_Description', N'Date the answer is due. Misses are lost money.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment', N'COLUMN', N'due_date';
EXEC sp_addextendedproperty N'MS_Description', N'Extension date, if the payer gave one.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment', N'COLUMN', N'extended_due_date';
EXEC sp_addextendedproperty N'MS_Description', N'SHA-256 hash of the request letter, not the letter.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment', N'COLUMN', N'request_text_hash';
EXEC sp_addextendedproperty N'MS_Description', N'not_started, collecting, ready_for_review, sent, acknowledged, closed.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment', N'COLUMN', N'response_status';
EXEC sp_addextendedproperty N'MS_Description', N'When our answer went out.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment', N'COLUMN', N'response_sent_date';
EXEC sp_addextendedproperty N'MS_Description', N'electronic, fax, mail, portal or courier.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment', N'COLUMN', N'response_method';
EXEC sp_addextendedproperty N'MS_Description', N'Fax confirmation, portal receipt, courier number or 275 transaction number. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment', N'COLUMN', N'response_tracking_number';
EXEC sp_addextendedproperty N'MS_Description', N'Pages sent or announced.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment', N'COLUMN', N'page_count';
EXEC sp_addextendedproperty N'MS_Description', N'received, incomplete, accepted, rejected.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment', N'COLUMN', N'payer_acknowledgement';
EXEC sp_addextendedproperty N'MS_Description', N'What kind of document (report type on the claim announcement).', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment', N'COLUMN', N'attachment_report_type_code';
EXEC sp_addextendedproperty N'MS_Description', N'How it is sent: electronic, fax or mail (transmission code).', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment', N'COLUMN', N'attachment_transmission_code';
EXEC sp_addextendedproperty N'MS_Description', N'ID tying the claim to the later attachment. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment', N'COLUMN', N'attachment_control_number';
EXEC sp_addextendedproperty N'MS_Description', N'The document or pack that went out (metadata row; hash and pages live there).', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment', N'COLUMN', N'document_id';
EXEC sp_addextendedproperty N'MS_Description', N'1 for the first row; higher for each change.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment', N'COLUMN', N'version';
EXEC sp_addextendedproperty N'MS_Description', N'1 on the latest version. Counts use current rows only.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment', N'COLUMN', N'is_current';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment', N'COLUMN', N'previous_claim_attachment_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One row per charge line on a bill.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'bill_line_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'Ties the charge to its bill.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'bill_id';
EXEC sp_addextendedproperty N'MS_Description', N'Position within the bill.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'line_number';
EXEC sp_addextendedproperty N'MS_Description', N'Copied from the header, so reports by practice never join up.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied from the header.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'patient_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied from the header, as of this stage.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied from the header.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied from the provider''s specialty; fast specialty reports.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'specialty_id';
EXEC sp_addextendedproperty N'MS_Description', N'The final billed code that will be claimed.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'cpt_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'Quantity billed.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'units';
EXEC sp_addextendedproperty N'MS_Description', N'The fee used, saved on the line. Fee lists change, so history must not move.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'fee_per_unit';
EXEC sp_addextendedproperty N'MS_Description', N'Units x fee. Base of every charge metric.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'billed_amount';
EXEC sp_addextendedproperty N'MS_Description', N'Drafted, held, ready, claimed, patient_billed, written_off, voided. Worked out, not typed.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'line_status';
EXEC sp_addextendedproperty N'MS_Description', N'Per-line date.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'service_date';
EXEC sp_addextendedproperty N'MS_Description', N'Final billed modifier.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'modifier_1_id';
EXEC sp_addextendedproperty N'MS_Description', N'Second modifier.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'modifier_2_id';
EXEC sp_addextendedproperty N'MS_Description', N'Third modifier.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'modifier_3_id';
EXEC sp_addextendedproperty N'MS_Description', N'Fourth modifier.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'modifier_4_id';
EXEC sp_addextendedproperty N'MS_Description', N'Final supporting diagnosis.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'diagnosis_1_id';
EXEC sp_addextendedproperty N'MS_Description', N'Second diagnosis.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'diagnosis_2_id';
EXEC sp_addextendedproperty N'MS_Description', N'Third diagnosis.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'diagnosis_3_id';
EXEC sp_addextendedproperty N'MS_Description', N'Fourth diagnosis.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'diagnosis_4_id';
EXEC sp_addextendedproperty N'MS_Description', N'When different from the bill.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'rendering_provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'Performed-to-billed traceability; missed-charge detection.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'encounter_line_id';
EXEC sp_addextendedproperty N'MS_Description', N'Detects late charges.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'charge_entered_date';
EXEC sp_addextendedproperty N'MS_Description', N'The code before coding review: the audit trail.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'cpt_as_entered_id';
EXEC sp_addextendedproperty N'MS_Description', N'1 if coding changed the code.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'code_changed';
EXEC sp_addextendedproperty N'MS_Description', N'Pseudonymous approver of a code change. A change with no approver is flagged (codes change only with a named approval). Holds the staff_id of the pseudonymous person.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'change_approved_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'Which fee schedule (and version) priced the line. The per-unit fee used is saved on the line.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'fee_schedule_id';
EXEC sp_addextendedproperty N'MS_Description', N'Contract allowed for the line; expected revenue and underpayment check.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'expected_allowed';
EXEC sp_addextendedproperty N'MS_Description', N'One line can be stuck while the others go.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'hold_reason';
EXEC sp_addextendedproperty N'MS_Description', N'Authorization on the line.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'authorization_id';
EXEC sp_addextendedproperty N'MS_Description', N'Claim rollup: how many claims carry the line. Rebuilt from claim_line.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'claims_on';
EXEC sp_addextendedproperty N'MS_Description', N'Claim rollup.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'latest_claim_line_status';
EXEC sp_addextendedproperty N'MS_Description', N'First claimed.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'claimed_date';
EXEC sp_addextendedproperty N'MS_Description', N'Drug-billing specialties.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'drug_code';
EXEC sp_addextendedproperty N'MS_Description', N'Reference row for drug_code.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'ndc_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'Drug units.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'drug_units';
EXEC sp_addextendedproperty N'MS_Description', N'Unit of the drug quantity: UN, ML, GR, F2.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'drug_unit_measure';
EXEC sp_addextendedproperty N'MS_Description', N'When different from the bill.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'place_of_service_id';
EXEC sp_addextendedproperty N'MS_Description', N'Productivity.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'entered_by_role';
EXEC sp_addextendedproperty N'MS_Description', N'Courtesy or write-off before a claim.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'no_charge_amount';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'bill_line', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One row per service line on a claim submission.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'claim_line_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'Ties the line to its claim.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'claim_id';
EXEC sp_addextendedproperty N'MS_Description', N'The same procedure can appear twice with different modifiers or sides.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'line_number';
EXEC sp_addextendedproperty N'MS_Description', N'Copied from the claim.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied from the claim; procedure-by-payer reports skip the join.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied from the claim.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'patient_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied from the claim.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'billing_provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied from the provider.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'specialty_id';
EXEC sp_addextendedproperty N'MS_Description', N'Procedure level: denials, contract pricing, coding review.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'cpt_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'Pricing and unit-limit checks.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'units';
EXEC sp_addextendedproperty N'MS_Description', N'Base for line realisation and denial rates.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'charge_amount';
EXEC sp_addextendedproperty N'MS_Description', N'Submitted, rejected, pending, paid, partly_paid, denied, adjusted. Worked out from events.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'line_status';
EXEC sp_addextendedproperty N'MS_Description', N'Collections. Required once line_status is paid, partly_paid or adjusted (CHECK).', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'paid_amount';
EXEC sp_addextendedproperty N'MS_Description', N'Matches the 835 line; multi-day services.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'service_date';
EXEC sp_addextendedproperty N'MS_Description', N'Last date of a multi-day line.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'service_date_to';
EXEC sp_addextendedproperty N'MS_Description', N'When the line differs from the claim.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'place_of_service_id';
EXEC sp_addextendedproperty N'MS_Description', N'Pricing and denial causes.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'modifier_1_id';
EXEC sp_addextendedproperty N'MS_Description', N'Second modifier.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'modifier_2_id';
EXEC sp_addextendedproperty N'MS_Description', N'Third modifier.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'modifier_3_id';
EXEC sp_addextendedproperty N'MS_Description', N'Fourth modifier.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'modifier_4_id';
EXEC sp_addextendedproperty N'MS_Description', N'Which claim diagnoses support this line.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'diagnosis_pointers';
EXEC sp_addextendedproperty N'MS_Description', N'The diagnosis the first pointer points to, saved on the line.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'primary_diagnosis_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'Procedure productivity; line-level in the 837.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'rendering_provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'Ordering provider (2420E), required for labs, imaging and DME.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'ordering_provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'Line-level supervising provider (2420D) when it differs from the claim.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'supervising_provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'What the payer will pay for the line; underpayment and realisation.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'allowed_amount';
EXEC sp_addextendedproperty N'MS_Description', N'Patient balance and statements.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'patient_responsibility';
EXEC sp_addextendedproperty N'MS_Description', N'Write-down to the contract rate.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'contractual_adjustment';
EXEC sp_addextendedproperty N'MS_Description', N'Denial rate by procedure.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'denied_amount';
EXEC sp_addextendedproperty N'MS_Description', N'First denial reason; the full list is in the denial records.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'primary_denial_reason_id';
EXEC sp_addextendedproperty N'MS_Description', N'Contract allowed at submission; underpayment is a subtraction.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'expected_allowed';
EXEC sp_addextendedproperty N'MS_Description', N'Traces the line back to the charge; bill lag and missed charges.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'bill_line_id';
EXEC sp_addextendedproperty N'MS_Description', N'The practice''s own line ID; matches 835 lines when the payer reorders or splits lines. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'line_control_number';
EXEC sp_addextendedproperty N'MS_Description', N'Drug-billing specialties.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'drug_code';
EXEC sp_addextendedproperty N'MS_Description', N'Reference row for drug_code.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'ndc_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'Drug units.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'drug_units';
EXEC sp_addextendedproperty N'MS_Description', N'Unit of the drug quantity: UN, ML, GR, F2.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'drug_unit_measure';
EXEC sp_addextendedproperty N'MS_Description', N'Emergency, family planning, EPSDT.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'line_flags';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'claim_line', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One row per status event on a claim submission: sent, acknowledged, rejected, status answer, adjudicated, resubmitted, voided.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'claim_status_history_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The claim submission the event is about.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'claim_id';
EXEC sp_addextendedproperty N'MS_Description', N'The line, when the 277CA rejects one line rather than the claim.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'claim_line_id';
EXEC sp_addextendedproperty N'MS_Description', N'Submitted, ack_999, ack_277ca, status_inquiry, status_response, adjudicated, resubmitted, voided.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'event_type';
EXEC sp_addextendedproperty N'MS_Description', N'When it happened.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'event_date';
EXEC sp_addextendedproperty N'MS_Description', N'The claim status after this event.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'status_after';
EXEC sp_addextendedproperty N'MS_Description', N'Copied from the claim.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied from the claim.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied from the claim.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'patient_id';
EXEC sp_addextendedproperty N'MS_Description', N'Exact time, for turnaround in hours.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'event_ts';
EXEC sp_addextendedproperty N'MS_Description', N'Order of responses; the first acknowledgement decides first-pass acceptance.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'response_sequence';
EXEC sp_addextendedproperty N'MS_Description', N'Payer status category from the 277.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'status_category';
EXEC sp_addextendedproperty N'MS_Description', N'Reference row for status_category.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'status_category_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'Payer status code from the 277. For ack_999 events it holds the AK9/IK5 code: A, E, P, M, R, W or X.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'status_code';
EXEC sp_addextendedproperty N'MS_Description', N'Reference row for status_code.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'status_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'A technical bounce, before the payer judged the claim.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'is_rejection';
EXEC sp_addextendedproperty N'MS_Description', N'Error or reason code from the 999 or 277CA.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'rejection_reason';
EXEC sp_addextendedproperty N'MS_Description', N'Member ID, provider ID, diagnosis, missing information, duplicate, payer ID.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'rejection_category';
EXEC sp_addextendedproperty N'MS_Description', N'Fixable without a clinical decision.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'is_technical';
EXEC sp_addextendedproperty N'MS_Description', N'Who fixes it.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'owner_role';
EXEC sp_addextendedproperty N'MS_Description', N'Target to fix and resend.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'fix_by_date';
EXEC sp_addextendedproperty N'MS_Description', N'Clearinghouse, payer portal, phone, fax.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'channel';
EXEC sp_addextendedproperty N'MS_Description', N'Payer''s number, assigned on acceptance. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'payer_claim_number';
EXEC sp_addextendedproperty N'MS_Description', N'Copied from the claim.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'billing_provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'specialty_id';
EXEC sp_addextendedproperty N'MS_Description', N'Paid amount stated on a status answer before the remittance arrives.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'reported_paid_amount';
EXEC sp_addextendedproperty N'MS_Description', N'Control number a 999 or 277CA acknowledges.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'acked_control_number';
EXEC sp_addextendedproperty N'MS_Description', N'Batch the claim travelled in.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'clearinghouse_batch_number';
EXEC sp_addextendedproperty N'MS_Description', N'The acknowledgement or status file the event came in.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'edi_file_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_history', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One diagnosis on a claim, in its HI position (1 to 12).', N'SCHEMA', N'dbo', N'TABLE', N'claim_diagnosis';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'claim_diagnosis', N'COLUMN', N'claim_diagnosis_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'claim_diagnosis', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The claim (stable ID).', N'SCHEMA', N'dbo', N'TABLE', N'claim_diagnosis', N'COLUMN', N'claim_id';
EXEC sp_addextendedproperty N'MS_Description', N'Position 1 to 12 in HI order. The number claim_line.diagnosis_pointers uses.', N'SCHEMA', N'dbo', N'TABLE', N'claim_diagnosis', N'COLUMN', N'diagnosis_sequence';
EXEC sp_addextendedproperty N'MS_Description', N'The ICD-10-CM code.', N'SCHEMA', N'dbo', N'TABLE', N'claim_diagnosis', N'COLUMN', N'diagnosis_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'1 on position 1.', N'SCHEMA', N'dbo', N'TABLE', N'claim_diagnosis', N'COLUMN', N'is_principal';
EXEC sp_addextendedproperty N'MS_Description', N'Present on admission: Y, N, U, W, 1. Institutional only; blank on professional claims.', N'SCHEMA', N'dbo', N'TABLE', N'claim_diagnosis', N'COLUMN', N'poa_indicator';
EXEC sp_addextendedproperty N'MS_Description', N'Copied, so reports skip the join.', N'SCHEMA', N'dbo', N'TABLE', N'claim_diagnosis', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied, so reports skip the join.', N'SCHEMA', N'dbo', N'TABLE', N'claim_diagnosis', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied, so reports skip the join.', N'SCHEMA', N'dbo', N'TABLE', N'claim_diagnosis', N'COLUMN', N'patient_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'claim_diagnosis', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'claim_diagnosis', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'claim_diagnosis', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'claim_diagnosis', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'claim_diagnosis', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'claim_diagnosis', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'claim_diagnosis', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'claim_diagnosis', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'claim_diagnosis', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'claim_diagnosis', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One document type asked for in a records request, and the document sent for it.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment_document';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment_document', N'COLUMN', N'claim_attachment_document_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment_document', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The request (stable ID).', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment_document', N'COLUMN', N'claim_attachment_id';
EXEC sp_addextendedproperty N'MS_Description', N'Type asked for; same values as document.document_type.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment_document', N'COLUMN', N'document_type';
EXEC sp_addextendedproperty N'MS_Description', N'The document sent for it.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment_document', N'COLUMN', N'document_id';
EXEC sp_addextendedproperty N'MS_Description', N'requested, found, missing, sent.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment_document', N'COLUMN', N'item_status';
EXEC sp_addextendedproperty N'MS_Description', N'Pages sent.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment_document', N'COLUMN', N'page_count';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment_document', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment_document', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment_document', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment_document', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment_document', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment_document', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment_document', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment_document', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment_document', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'claim_attachment_document', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One edit raised on a claim (or line) before it reached the payer: PM scrubber, clearinghouse edit or our own agent check.', N'SCHEMA', N'dbo', N'TABLE', N'claim_edit';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'claim_edit', N'COLUMN', N'claim_edit_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'claim_edit', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The claim (stable ID).', N'SCHEMA', N'dbo', N'TABLE', N'claim_edit', N'COLUMN', N'claim_id';
EXEC sp_addextendedproperty N'MS_Description', N'The line, for line-level edits.', N'SCHEMA', N'dbo', N'TABLE', N'claim_edit', N'COLUMN', N'claim_line_id';
EXEC sp_addextendedproperty N'MS_Description', N'pm_scrubber, clearinghouse, agent, payer_front_end.', N'SCHEMA', N'dbo', N'TABLE', N'claim_edit', N'COLUMN', N'edit_source';
EXEC sp_addextendedproperty N'MS_Description', N'The vendor''s edit code.', N'SCHEMA', N'dbo', N'TABLE', N'claim_edit', N'COLUMN', N'edit_code';
EXEC sp_addextendedproperty N'MS_Description', N'Our grouping: demographics, eligibility, coding, ncci, mue, lcd_ncd, authorization, provider, format.', N'SCHEMA', N'dbo', N'TABLE', N'claim_edit', N'COLUMN', N'edit_category';
EXEC sp_addextendedproperty N'MS_Description', N'error, warning, info.', N'SCHEMA', N'dbo', N'TABLE', N'claim_edit', N'COLUMN', N'severity';
EXEC sp_addextendedproperty N'MS_Description', N'When raised.', N'SCHEMA', N'dbo', N'TABLE', N'claim_edit', N'COLUMN', N'edit_ts';
EXEC sp_addextendedproperty N'MS_Description', N'open, fixed, overridden, voided.', N'SCHEMA', N'dbo', N'TABLE', N'claim_edit', N'COLUMN', N'edit_status';
EXEC sp_addextendedproperty N'MS_Description', N'When fixed or overridden.', N'SCHEMA', N'dbo', N'TABLE', N'claim_edit', N'COLUMN', N'resolved_ts';
EXEC sp_addextendedproperty N'MS_Description', N'Who fixed or overrode it.', N'SCHEMA', N'dbo', N'TABLE', N'claim_edit', N'COLUMN', N'resolved_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'Which claim field was changed to fix it.', N'SCHEMA', N'dbo', N'TABLE', N'claim_edit', N'COLUMN', N'fix_field_code';
EXEC sp_addextendedproperty N'MS_Description', N'Our rule behind the edit, when the source is an agent.', N'SCHEMA', N'dbo', N'TABLE', N'claim_edit', N'COLUMN', N'payer_rule_id';
EXEC sp_addextendedproperty N'MS_Description', N'Agent decision that raised it.', N'SCHEMA', N'dbo', N'TABLE', N'claim_edit', N'COLUMN', N'agent_decision_id';
EXEC sp_addextendedproperty N'MS_Description', N'Clearinghouse report file.', N'SCHEMA', N'dbo', N'TABLE', N'claim_edit', N'COLUMN', N'edi_file_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied, so reports skip the join.', N'SCHEMA', N'dbo', N'TABLE', N'claim_edit', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied, so reports skip the join.', N'SCHEMA', N'dbo', N'TABLE', N'claim_edit', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied, so reports skip the join.', N'SCHEMA', N'dbo', N'TABLE', N'claim_edit', N'COLUMN', N'patient_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied, so reports skip the join.', N'SCHEMA', N'dbo', N'TABLE', N'claim_edit', N'COLUMN', N'billing_provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'Line code, copied for edit analysis.', N'SCHEMA', N'dbo', N'TABLE', N'claim_edit', N'COLUMN', N'cpt_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'claim_edit', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'claim_edit', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'claim_edit', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'claim_edit', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'claim_edit', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'claim_edit', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'claim_edit', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'claim_edit', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'claim_edit', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'claim_edit', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One row per money movement on a charge line: charge, payment, adjustment, write-off, refund, transfer, opening balance.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'ledger_entry_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client''s posting ID. Makes loads repeatable. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'transaction_number';
EXEC sp_addextendedproperty N'MS_Description', N'Reports by practice.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Patient accounts.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'patient_id';
EXEC sp_addextendedproperty N'MS_Description', N'The charge line the money acts on.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'bill_line_id';
EXEC sp_addextendedproperty N'MS_Description', N'Charge, payment, adjustment, write_off, refund, transfer, opening_balance.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'transaction_type';
EXEC sp_addextendedproperty N'MS_Description', N'Amount as posted.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'amount';
EXEC sp_addextendedproperty N'MS_Description', N'Signed effect on the balance, so balance = a simple sum.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'balance_effect';
EXEC sp_addextendedproperty N'MS_Description', N'Business date of the event.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'transaction_date';
EXEC sp_addextendedproperty N'MS_Description', N'Payer or patient: the AR split.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'responsible_party';
EXEC sp_addextendedproperty N'MS_Description', N'On transfer rows: who owed before (payer, patient).', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'from_party';
EXEC sp_addextendedproperty N'MS_Description', N'On transfer rows: who owes after.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'to_party';
EXEC sp_addextendedproperty N'MS_Description', N'On a transfer to another payer: that payer.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'to_payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'Payer-side tracing. Blank for self-pay.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'claim_line_id';
EXEC sp_addextendedproperty N'MS_Description', N'Payer-side tracing.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'claim_id';
EXEC sp_addextendedproperty N'MS_Description', N'Contractual, denial, bad debt, charity, overpayment recoupment, patient refund and so on.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'transaction_subtype';
EXEC sp_addextendedproperty N'MS_Description', N'When posted; backdating and posting lag.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'posted_date';
EXEC sp_addextendedproperty N'MS_Description', N'Copied from the charge.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied from the charge.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied from the provider.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'specialty_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied from the charge.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'cpt_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'Reason for an adjustment: contractual, patient, other.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'adjustment_reason_id';
EXEC sp_addextendedproperty N'MS_Description', N'CO, PR, OA, PI, CR.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'group_code';
EXEC sp_addextendedproperty N'MS_Description', N'The payment (EFT, check, card) the money came in.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'payment_id';
EXEC sp_addextendedproperty N'MS_Description', N'EFT, check, virtual card, card, cash.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'payment_method';
EXEC sp_addextendedproperty N'MS_Description', N'Trace or check number. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'payment_number';
EXEC sp_addextendedproperty N'MS_Description', N'Pseudonymous approver. Write-offs and refunds need a named approver; one without is flagged. Holds the staff_id of the pseudonymous person.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'approved_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When approved.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'approved_date';
EXEC sp_addextendedproperty N'MS_Description', N'The row this reverses.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'reverses_ledger_entry_id';
EXEC sp_addextendedproperty N'MS_Description', N'1 on a reversing row.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'is_reversal';
EXEC sp_addextendedproperty N'MS_Description', N'Posting batch.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'batch_number';
EXEC sp_addextendedproperty N'MS_Description', N'Posting analysis.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'posted_by_role';
EXEC sp_addextendedproperty N'MS_Description', N'Why refunded.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'refund_reason';
EXEC sp_addextendedproperty N'MS_Description', N'Remark (RARC) that explains an adjustment or denial further.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'remark_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'ledger_entry', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One row per denied amount on one claim line, per remittance. Status changes are kept as versions.', N'SCHEMA', N'dbo', N'TABLE', N'denial';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of the record: the same on every version. The primary key is (denial_id, version). Every link from another table uses denial_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'denial_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The claim submission that was denied.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'claim_id';
EXEC sp_addextendedproperty N'MS_Description', N'The line. A whole-claim denial is spread over its lines.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'claim_line_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied from the claim.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied from the claim.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'patient_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied from the claim.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'The payer''s decision date.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'denial_date';
EXEC sp_addextendedproperty N'MS_Description', N'Base of the denial rate.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'denied_amount';
EXEC sp_addextendedproperty N'MS_Description', N'Main reason code: denial by reason without joining the details.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'adjustment_reason_id';
EXEC sp_addextendedproperty N'MS_Description', N'Open, corrected_resubmitted, appealed, written_off, recovered, closed, expired.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'denial_status';
EXEC sp_addextendedproperty N'MS_Description', N'The ledger row that carried the denial.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'ledger_entry_id';
EXEC sp_addextendedproperty N'MS_Description', N'The charge line behind it.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'bill_line_id';
EXEC sp_addextendedproperty N'MS_Description', N'CO, PR, OA, PI, CR.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'group_code';
EXEC sp_addextendedproperty N'MS_Description', N'Eligibility, authorization, coding, documentation, billing, medical necessity, timely filing, duplicate, coordination of benefits.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'reason_category';
EXEC sp_addextendedproperty N'MS_Description', N'Appeal clock starts (denial notice).', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'clock_start_date';
EXEC sp_addextendedproperty N'MS_Description', N'Deadline and money at risk.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'appeal_deadline';
EXEC sp_addextendedproperty N'MS_Description', N'Why it happened.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'root_cause';
EXEC sp_addextendedproperty N'MS_Description', N'Which journey stage could have caught it.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'upstream_stage';
EXEC sp_addextendedproperty N'MS_Description', N'Could have been caught before sending.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'is_preventable';
EXEC sp_addextendedproperty N'MS_Description', N'Fixable without a clinical decision.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'is_technical';
EXEC sp_addextendedproperty N'MS_Description', N'Billing, coding, front desk, provider.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'owner_role';
EXEC sp_addextendedproperty N'MS_Description', N'Days to resolve.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'resolved_date';
EXEC sp_addextendedproperty N'MS_Description', N'Overturned, corrected, written off, accepted.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'outcome';
EXEC sp_addextendedproperty N'MS_Description', N'Recovery. Rebuilt from the ledger.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'recovered_amount';
EXEC sp_addextendedproperty N'MS_Description', N'Same line denied again.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'is_repeat';
EXEC sp_addextendedproperty N'MS_Description', N'Times this line has been denied.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'denial_count_on_line';
EXEC sp_addextendedproperty N'MS_Description', N'The replacement claim.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'resubmitted_claim_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied for reports.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'cpt_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied for reports.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied for reports.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'specialty_id';
EXEC sp_addextendedproperty N'MS_Description', N'Spread from a whole-claim denial.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'is_claim_level';
EXEC sp_addextendedproperty N'MS_Description', N'Partial-unit denials.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'units_denied';
EXEC sp_addextendedproperty N'MS_Description', N'Authorization denials.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'authorization_id';
EXEC sp_addextendedproperty N'MS_Description', N'1 for the first row; higher for each change.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'version';
EXEC sp_addextendedproperty N'MS_Description', N'1 on the latest version. Counts use current rows only.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'is_current';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'previous_denial_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'denial', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One row per payment received: payer EFT, check or virtual card, or a patient payment. A reissue or void is a new version.', N'SCHEMA', N'dbo', N'TABLE', N'payment';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of the record: the same on every version. The primary key is (payment_id, version). Every link from another table uses payment_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.', N'SCHEMA', N'dbo', N'TABLE', N'payment', N'COLUMN', N'payment_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'payment', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'Trace or check number. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'payment', N'COLUMN', N'payment_number';
EXEC sp_addextendedproperty N'MS_Description', N'Reports by practice.', N'SCHEMA', N'dbo', N'TABLE', N'payment', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Payer or patient.', N'SCHEMA', N'dbo', N'TABLE', N'payment', N'COLUMN', N'payment_source';
EXEC sp_addextendedproperty N'MS_Description', N'Payment effective date.', N'SCHEMA', N'dbo', N'TABLE', N'payment', N'COLUMN', N'payment_date';
EXEC sp_addextendedproperty N'MS_Description', N'Total of the payment.', N'SCHEMA', N'dbo', N'TABLE', N'payment', N'COLUMN', N'payment_amount';
EXEC sp_addextendedproperty N'MS_Description', N'EFT, check, virtual card, card, cash, other.', N'SCHEMA', N'dbo', N'TABLE', N'payment', N'COLUMN', N'payment_method';
EXEC sp_addextendedproperty N'MS_Description', N'Blank for patient payments.', N'SCHEMA', N'dbo', N'TABLE', N'payment', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'On patient payments: the patient paid for.', N'SCHEMA', N'dbo', N'TABLE', N'payment', N'COLUMN', N'patient_id';
EXEC sp_addextendedproperty N'MS_Description', N'On patient payments: the guarantor who paid.', N'SCHEMA', N'dbo', N'TABLE', N'payment', N'COLUMN', N'guarantor_id';
EXEC sp_addextendedproperty N'MS_Description', N'Visit the payment was collected for (point-of-service copay, prepayment).', N'SCHEMA', N'dbo', N'TABLE', N'payment', N'COLUMN', N'appointment_id';
EXEC sp_addextendedproperty N'MS_Description', N'pre_visit, check_in, check_out, statement, portal, phone, payment_plan, collections.', N'SCHEMA', N'dbo', N'TABLE', N'payment', N'COLUMN', N'collection_point';
EXEC sp_addextendedproperty N'MS_Description', N'Payment, takeback, refund.', N'SCHEMA', N'dbo', N'TABLE', N'payment', N'COLUMN', N'payment_type';
EXEC sp_addextendedproperty N'MS_Description', N'When the money or remittance arrived.', N'SCHEMA', N'dbo', N'TABLE', N'payment', N'COLUMN', N'received_date';
EXEC sp_addextendedproperty N'MS_Description', N'When posted; posting lag.', N'SCHEMA', N'dbo', N'TABLE', N'payment', N'COLUMN', N'posted_date';
EXEC sp_addextendedproperty N'MS_Description', N'C for money in; D for a takeback.', N'SCHEMA', N'dbo', N'TABLE', N'payment', N'COLUMN', N'credit_debit';
EXEC sp_addextendedproperty N'MS_Description', N'Electronic remittance received (vs paper explanation).', N'SCHEMA', N'dbo', N'TABLE', N'payment', N'COLUMN', N'has_remittance';
EXEC sp_addextendedproperty N'MS_Description', N'The 835 file the payment came in.', N'SCHEMA', N'dbo', N'TABLE', N'payment', N'COLUMN', N'edi_file_id';
EXEC sp_addextendedproperty N'MS_Description', N'Claims covered.', N'SCHEMA', N'dbo', N'TABLE', N'payment', N'COLUMN', N'claim_count';
EXEC sp_addextendedproperty N'MS_Description', N'Rollup of linked ledger_entry.', N'SCHEMA', N'dbo', N'TABLE', N'payment', N'COLUMN', N'posted_amount';
EXEC sp_addextendedproperty N'MS_Description', N'Payment minus posted. Includes patient prepayments and copays held until the charge exists (ledger rows always need a charge line).', N'SCHEMA', N'dbo', N'TABLE', N'payment', N'COLUMN', N'unapplied_amount';
EXEC sp_addextendedproperty N'MS_Description', N'Provider-level adjustments on the payment (takebacks, interest).', N'SCHEMA', N'dbo', N'TABLE', N'payment', N'COLUMN', N'plb_amount';
EXEC sp_addextendedproperty N'MS_Description', N'1 when posted equals the payment total.', N'SCHEMA', N'dbo', N'TABLE', N'payment', N'COLUMN', N'reconciles';
EXEC sp_addextendedproperty N'MS_Description', N'Voided or bounced.', N'SCHEMA', N'dbo', N'TABLE', N'payment', N'COLUMN', N'is_void';
EXEC sp_addextendedproperty N'MS_Description', N'Payee.', N'SCHEMA', N'dbo', N'TABLE', N'payment', N'COLUMN', N'payee_provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'1 for the first row; higher for each change.', N'SCHEMA', N'dbo', N'TABLE', N'payment', N'COLUMN', N'version';
EXEC sp_addextendedproperty N'MS_Description', N'1 on the latest version. Counts use current rows only.', N'SCHEMA', N'dbo', N'TABLE', N'payment', N'COLUMN', N'is_current';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.', N'SCHEMA', N'dbo', N'TABLE', N'payment', N'COLUMN', N'previous_payment_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'payment', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'payment', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'payment', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'payment', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'payment', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'payment', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'payment', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'payment', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'payment', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'payment', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One payment plan agreed with a patient: total, instalment size, how many instalments are missed and whether autopay is on. A change is a new version.', N'SCHEMA', N'dbo', N'TABLE', N'payment_plan';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of the record: the same on every version. The primary key is (payment_plan_id, version). Every link from another table uses payment_plan_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.', N'SCHEMA', N'dbo', N'TABLE', N'payment_plan', N'COLUMN', N'payment_plan_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'payment_plan', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The practice''s own plan number. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'payment_plan', N'COLUMN', N'payment_plan_number';
EXEC sp_addextendedproperty N'MS_Description', N'The patient who owns the plan.', N'SCHEMA', N'dbo', N'TABLE', N'payment_plan', N'COLUMN', N'patient_id';
EXEC sp_addextendedproperty N'MS_Description', N'The guarantor account responsible for the patient balance.', N'SCHEMA', N'dbo', N'TABLE', N'payment_plan', N'COLUMN', N'guarantor_id';
EXEC sp_addextendedproperty N'MS_Description', N'Active, completed, defaulted or cancelled.', N'SCHEMA', N'dbo', N'TABLE', N'payment_plan', N'COLUMN', N'plan_status';
EXEC sp_addextendedproperty N'MS_Description', N'First instalment date or agreement date.', N'SCHEMA', N'dbo', N'TABLE', N'payment_plan', N'COLUMN', N'start_date';
EXEC sp_addextendedproperty N'MS_Description', N'Balance put on the plan.', N'SCHEMA', N'dbo', N'TABLE', N'payment_plan', N'COLUMN', N'total_amount';
EXEC sp_addextendedproperty N'MS_Description', N'Copied, for reports by practice.', N'SCHEMA', N'dbo', N'TABLE', N'payment_plan', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Agreed amount per instalment.', N'SCHEMA', N'dbo', N'TABLE', N'payment_plan', N'COLUMN', N'instalment_amount';
EXEC sp_addextendedproperty N'MS_Description', N'Number of instalments agreed.', N'SCHEMA', N'dbo', N'TABLE', N'payment_plan', N'COLUMN', N'instalment_count';
EXEC sp_addextendedproperty N'MS_Description', N'Weekly, biweekly or monthly.', N'SCHEMA', N'dbo', N'TABLE', N'payment_plan', N'COLUMN', N'frequency';
EXEC sp_addextendedproperty N'MS_Description', N'Next instalment due date. The AR forecast reads it.', N'SCHEMA', N'dbo', N'TABLE', N'payment_plan', N'COLUMN', N'next_due_date';
EXEC sp_addextendedproperty N'MS_Description', N'Instalments missed as known on the row date. Kept because it depends on what was known then.', N'SCHEMA', N'dbo', N'TABLE', N'payment_plan', N'COLUMN', N'missed_instalments';
EXEC sp_addextendedproperty N'MS_Description', N'Due date of the latest missed instalment.', N'SCHEMA', N'dbo', N'TABLE', N'payment_plan', N'COLUMN', N'last_missed_date';
EXEC sp_addextendedproperty N'MS_Description', N'Whether recurring payment is set up. A flag only; card or bank details are never stored.', N'SCHEMA', N'dbo', N'TABLE', N'payment_plan', N'COLUMN', N'autopay_enrolled';
EXEC sp_addextendedproperty N'MS_Description', N'Date the plan completed, defaulted or was cancelled.', N'SCHEMA', N'dbo', N'TABLE', N'payment_plan', N'COLUMN', N'end_date';
EXEC sp_addextendedproperty N'MS_Description', N'1 for the first row; higher for each change.', N'SCHEMA', N'dbo', N'TABLE', N'payment_plan', N'COLUMN', N'version';
EXEC sp_addextendedproperty N'MS_Description', N'1 on the latest version. Counts use current rows only.', N'SCHEMA', N'dbo', N'TABLE', N'payment_plan', N'COLUMN', N'is_current';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.', N'SCHEMA', N'dbo', N'TABLE', N'payment_plan', N'COLUMN', N'previous_payment_plan_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'payment_plan', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'payment_plan', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'payment_plan', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'payment_plan', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'payment_plan', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'payment_plan', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'payment_plan', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'payment_plan', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'payment_plan', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'payment_plan', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'The contact consent and preferences of one patient, as flags only. No phone numbers, emails or addresses. A change (new consent, opt-out) is a new version, so consent history is kept.', N'SCHEMA', N'dbo', N'TABLE', N'patient_contact_preference';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of the record: the same on every version. The primary key is (patient_contact_preference_id, version). Every link from another table uses patient_contact_preference_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.', N'SCHEMA', N'dbo', N'TABLE', N'patient_contact_preference', N'COLUMN', N'patient_contact_preference_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'patient_contact_preference', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The patient these preferences belong to.', N'SCHEMA', N'dbo', N'TABLE', N'patient_contact_preference', N'COLUMN', N'patient_id';
EXEC sp_addextendedproperty N'MS_Description', N'1 if the patient asked not to be contacted. Stops all outreach.', N'SCHEMA', N'dbo', N'TABLE', N'patient_contact_preference', N'COLUMN', N'opt_out';
EXEC sp_addextendedproperty N'MS_Description', N'1 if the patient agreed to be texted.', N'SCHEMA', N'dbo', N'TABLE', N'patient_contact_preference', N'COLUMN', N'text_consent';
EXEC sp_addextendedproperty N'MS_Description', N'Mail, portal, sms or phone.', N'SCHEMA', N'dbo', N'TABLE', N'patient_contact_preference', N'COLUMN', N'preferred_channel';
EXEC sp_addextendedproperty N'MS_Description', N'Hour of the day (0 to 23) when contact must stop.', N'SCHEMA', N'dbo', N'TABLE', N'patient_contact_preference', N'COLUMN', N'quiet_hours_start';
EXEC sp_addextendedproperty N'MS_Description', N'Hour of the day (0 to 23) when contact may resume.', N'SCHEMA', N'dbo', N'TABLE', N'patient_contact_preference', N'COLUMN', N'quiet_hours_end';
EXEC sp_addextendedproperty N'MS_Description', N'Time zone the quiet hours are in (the patient''s, not the practice''s).', N'SCHEMA', N'dbo', N'TABLE', N'patient_contact_preference', N'COLUMN', N'contact_time_zone';
EXEC sp_addextendedproperty N'MS_Description', N'Valid, returned or unknown: whether mail reaches the patient. The address itself is not stored.', N'SCHEMA', N'dbo', N'TABLE', N'patient_contact_preference', N'COLUMN', N'address_status';
EXEC sp_addextendedproperty N'MS_Description', N'1 if a phone number or email is on file. The value is not stored.', N'SCHEMA', N'dbo', N'TABLE', N'patient_contact_preference', N'COLUMN', N'has_phone';
EXEC sp_addextendedproperty N'MS_Description', N'1 if the patient agreed to auto-dialed or recorded calls.', N'SCHEMA', N'dbo', N'TABLE', N'patient_contact_preference', N'COLUMN', N'autodial_consent';
EXEC sp_addextendedproperty N'MS_Description', N'Date the latest consent was given.', N'SCHEMA', N'dbo', N'TABLE', N'patient_contact_preference', N'COLUMN', N'consent_date';
EXEC sp_addextendedproperty N'MS_Description', N'Where consent was captured: form, portal, verbal.', N'SCHEMA', N'dbo', N'TABLE', N'patient_contact_preference', N'COLUMN', N'consent_source';
EXEC sp_addextendedproperty N'MS_Description', N'Version of the consent wording shown. Needed to prove what the patient agreed to.', N'SCHEMA', N'dbo', N'TABLE', N'patient_contact_preference', N'COLUMN', N'consent_wording_version';
EXEC sp_addextendedproperty N'MS_Description', N'Date the patient opted out.', N'SCHEMA', N'dbo', N'TABLE', N'patient_contact_preference', N'COLUMN', N'opt_out_date';
EXEC sp_addextendedproperty N'MS_Description', N'1 if the patient allows us to talk to a family member or other representative.', N'SCHEMA', N'dbo', N'TABLE', N'patient_contact_preference', N'COLUMN', N'has_authorized_rep';
EXEC sp_addextendedproperty N'MS_Description', N'Kept for matching; the account is guarantor_id.', N'SCHEMA', N'dbo', N'TABLE', N'patient_contact_preference', N'COLUMN', N'guarantor_hash';
EXEC sp_addextendedproperty N'MS_Description', N'The guarantor these preferences belong to, when not the patient.', N'SCHEMA', N'dbo', N'TABLE', N'patient_contact_preference', N'COLUMN', N'guarantor_id';
EXEC sp_addextendedproperty N'MS_Description', N'1 for the first row; higher for each change.', N'SCHEMA', N'dbo', N'TABLE', N'patient_contact_preference', N'COLUMN', N'version';
EXEC sp_addextendedproperty N'MS_Description', N'1 on the latest version. Counts use current rows only.', N'SCHEMA', N'dbo', N'TABLE', N'patient_contact_preference', N'COLUMN', N'is_current';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.', N'SCHEMA', N'dbo', N'TABLE', N'patient_contact_preference', N'COLUMN', N'previous_patient_contact_preference_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'patient_contact_preference', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'patient_contact_preference', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'patient_contact_preference', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'patient_contact_preference', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'patient_contact_preference', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'patient_contact_preference', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'patient_contact_preference', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'patient_contact_preference', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'patient_contact_preference', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'patient_contact_preference', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One row per reason code or remark code behind a denial.', N'SCHEMA', N'dbo', N'TABLE', N'denial_reason';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'denial_reason', N'COLUMN', N'denial_reason_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'denial_reason', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The denial it explains (stable ID).', N'SCHEMA', N'dbo', N'TABLE', N'denial_reason', N'COLUMN', N'denial_id';
EXEC sp_addextendedproperty N'MS_Description', N'Order within the denial.', N'SCHEMA', N'dbo', N'TABLE', N'denial_reason', N'COLUMN', N'detail_seq';
EXEC sp_addextendedproperty N'MS_Description', N'Reason or remark.', N'SCHEMA', N'dbo', N'TABLE', N'denial_reason', N'COLUMN', N'detail_type';
EXEC sp_addextendedproperty N'MS_Description', N'The reason code. Required when detail_type = reason (CHECK).', N'SCHEMA', N'dbo', N'TABLE', N'denial_reason', N'COLUMN', N'adjustment_reason_id';
EXEC sp_addextendedproperty N'MS_Description', N'The remark code. Required when detail_type = remark (CHECK).', N'SCHEMA', N'dbo', N'TABLE', N'denial_reason', N'COLUMN', N'remark_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'CO, PR, OA, PI, CR.', N'SCHEMA', N'dbo', N'TABLE', N'denial_reason', N'COLUMN', N'group_code';
EXEC sp_addextendedproperty N'MS_Description', N'Amount tied to this reason; sums to the denial amount.', N'SCHEMA', N'dbo', N'TABLE', N'denial_reason', N'COLUMN', N'reason_amount';
EXEC sp_addextendedproperty N'MS_Description', N'1 if we assigned the amount because the payer gave one total.', N'SCHEMA', N'dbo', N'TABLE', N'denial_reason', N'COLUMN', N'is_amount_allocated';
EXEC sp_addextendedproperty N'MS_Description', N'Units tied to the reason.', N'SCHEMA', N'dbo', N'TABLE', N'denial_reason', N'COLUMN', N'reason_units';
EXEC sp_addextendedproperty N'MS_Description', N'The main reason.', N'SCHEMA', N'dbo', N'TABLE', N'denial_reason', N'COLUMN', N'is_primary';
EXEC sp_addextendedproperty N'MS_Description', N'Copied from the reason.', N'SCHEMA', N'dbo', N'TABLE', N'denial_reason', N'COLUMN', N'reason_category';
EXEC sp_addextendedproperty N'MS_Description', N'Rule output.', N'SCHEMA', N'dbo', N'TABLE', N'denial_reason', N'COLUMN', N'is_appealable';
EXEC sp_addextendedproperty N'MS_Description', N'Fix and resubmit, appeal, write-off review, bill patient, informational. A proposal only.', N'SCHEMA', N'dbo', N'TABLE', N'denial_reason', N'COLUMN', N'suggested_action';
EXEC sp_addextendedproperty N'MS_Description', N'Copied for reports.', N'SCHEMA', N'dbo', N'TABLE', N'denial_reason', N'COLUMN', N'denial_date';
EXEC sp_addextendedproperty N'MS_Description', N'Copied.', N'SCHEMA', N'dbo', N'TABLE', N'denial_reason', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied.', N'SCHEMA', N'dbo', N'TABLE', N'denial_reason', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied.', N'SCHEMA', N'dbo', N'TABLE', N'denial_reason', N'COLUMN', N'cpt_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied.', N'SCHEMA', N'dbo', N'TABLE', N'denial_reason', N'COLUMN', N'claim_line_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied.', N'SCHEMA', N'dbo', N'TABLE', N'denial_reason', N'COLUMN', N'provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied.', N'SCHEMA', N'dbo', N'TABLE', N'denial_reason', N'COLUMN', N'specialty_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied.', N'SCHEMA', N'dbo', N'TABLE', N'denial_reason', N'COLUMN', N'patient_id';
EXEC sp_addextendedproperty N'MS_Description', N'Payer-specific code.', N'SCHEMA', N'dbo', N'TABLE', N'denial_reason', N'COLUMN', N'payer_reason_code';
EXEC sp_addextendedproperty N'MS_Description', N'Which code list.', N'SCHEMA', N'dbo', N'TABLE', N'denial_reason', N'COLUMN', N'remark_qualifier';
EXEC sp_addextendedproperty N'MS_Description', N'What proof is needed.', N'SCHEMA', N'dbo', N'TABLE', N'denial_reason', N'COLUMN', N'documents_needed';
EXEC sp_addextendedproperty N'MS_Description', N'Which reason was fixed.', N'SCHEMA', N'dbo', N'TABLE', N'denial_reason', N'COLUMN', N'reason_corrected';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'denial_reason', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'denial_reason', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'denial_reason', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'denial_reason', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'denial_reason', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'denial_reason', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'denial_reason', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'denial_reason', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'denial_reason', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'denial_reason', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One row per charge line per period (month by default).', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of the record: the same on every version. The primary key is (ar_interval_id, version). Every link from another table uses ar_interval_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'ar_interval_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The charge line (the account).', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'bill_line_id';
EXEC sp_addextendedproperty N'MS_Description', N'Start of the period.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'period_start_date';
EXEC sp_addextendedproperty N'MS_Description', N'End of the period.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'period_end_date';
EXEC sp_addextendedproperty N'MS_Description', N'Month or week.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'period_type';
EXEC sp_addextendedproperty N'MS_Description', N'Reports by practice.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Patient accounts.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'patient_id';
EXEC sp_addextendedproperty N'MS_Description', N'The guarantor account responsible for the patient balance.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'guarantor_id';
EXEC sp_addextendedproperty N'MS_Description', N'Prior period''s closing; the first period starts from the charge or an opening-balance row.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'opening_balance';
EXEC sp_addextendedproperty N'MS_Description', N'Charges posted in the period.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'charges';
EXEC sp_addextendedproperty N'MS_Description', N'Payments in the period.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'payments';
EXEC sp_addextendedproperty N'MS_Description', N'Adjustments in the period.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'adjustments';
EXEC sp_addextendedproperty N'MS_Description', N'Write-offs in the period.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'write_offs';
EXEC sp_addextendedproperty N'MS_Description', N'Refunds in the period.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'refunds';
EXEC sp_addextendedproperty N'MS_Description', N'Opening plus movements.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'closing_balance';
EXEC sp_addextendedproperty N'MS_Description', N'Closing owed by the payer.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'payer_balance';
EXEC sp_addextendedproperty N'MS_Description', N'Closing owed by the patient.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'patient_balance';
EXEC sp_addextendedproperty N'MS_Description', N'Same buckets as ar_snapshot.aging_bucket: 0-30, 31-60, 61-90, 91-120, 121+.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'payer_bucket';
EXEC sp_addextendedproperty N'MS_Description', N'Same buckets as ar_snapshot.aging_bucket: 0-30, 31-60, 61-90, 91-120, 121+.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'patient_bucket';
EXEC sp_addextendedproperty N'MS_Description', N'What the aging clock started from, so the definition never changes silently.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'aging_basis';
EXEC sp_addextendedproperty N'MS_Description', N'1 when closing equals the ledger sum.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'reconciles';
EXEC sp_addextendedproperty N'MS_Description', N'Links the roll-forward chain.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'prior_period_ar_interval_id';
EXEC sp_addextendedproperty N'MS_Description', N'Days the payer balance has aged.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'payer_days';
EXEC sp_addextendedproperty N'MS_Description', N'Days the patient balance has aged; the clock restarts at transfer.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'patient_days';
EXEC sp_addextendedproperty N'MS_Description', N'Payer clock start.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'payer_aging_date';
EXEC sp_addextendedproperty N'MS_Description', N'Patient clock start.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'patient_aging_date';
EXEC sp_addextendedproperty N'MS_Description', N'Charges not yet on a claim.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'unbilled_balance';
EXEC sp_addextendedproperty N'MS_Description', N'Movement split.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'payments_payer';
EXEC sp_addextendedproperty N'MS_Description', N'Movement split.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'payments_patient';
EXEC sp_addextendedproperty N'MS_Description', N'Movement split.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'adjustments_contractual';
EXEC sp_addextendedproperty N'MS_Description', N'Movement split.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'adjustments_denial';
EXEC sp_addextendedproperty N'MS_Description', N'Movement split.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'adjustments_other';
EXEC sp_addextendedproperty N'MS_Description', N'Moved from payer to patient.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'transfers_to_patient';
EXEC sp_addextendedproperty N'MS_Description', N'Moved to a secondary payer.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'transfers_to_secondary';
EXEC sp_addextendedproperty N'MS_Description', N'Current claim.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'claim_id';
EXEC sp_addextendedproperty N'MS_Description', N'Current claim line.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'claim_line_id';
EXEC sp_addextendedproperty N'MS_Description', N'Status at period end.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'claim_status';
EXEC sp_addextendedproperty N'MS_Description', N'Payer responsible at period end.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'Denial-related AR.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'open_denied_amount';
EXEC sp_addextendedproperty N'MS_Description', N'An open denial exists.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'is_in_denial';
EXEC sp_addextendedproperty N'MS_Description', N'Net AR: contract expected minus paid.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'expected_collectible';
EXEC sp_addextendedproperty N'MS_Description', N'Stalled accounts.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'last_payment_date';
EXEC sp_addextendedproperty N'MS_Description', N'Stalled accounts.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'last_activity_date';
EXEC sp_addextendedproperty N'MS_Description', N'Statement timing.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'last_statement_date';
EXEC sp_addextendedproperty N'MS_Description', N'Closing below zero: refund candidates.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'is_credit';
EXEC sp_addextendedproperty N'MS_Description', N'Ledger sum to period end (visible check).', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'ledger_balance';
EXEC sp_addextendedproperty N'MS_Description', N'Closing minus ledger.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'variance_amount';
EXEC sp_addextendedproperty N'MS_Description', N'Rebuilt after a backdated posting.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'is_restated';
EXEC sp_addextendedproperty N'MS_Description', N'Open or closed.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'period_status';
EXEC sp_addextendedproperty N'MS_Description', N'Copied.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'specialty_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'cpt_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'facility_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'service_date';
EXEC sp_addextendedproperty N'MS_Description', N'1 while the balance is placed with an agency (rebuilt from collection_placement).', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'collections_agency_flag';
EXEC sp_addextendedproperty N'MS_Description', N'Statements sent.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'statement_count';
EXEC sp_addextendedproperty N'MS_Description', N'1 for the first row; higher for each change.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'version';
EXEC sp_addextendedproperty N'MS_Description', N'1 on the latest version. Counts use current rows only.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'is_current';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'previous_ar_interval_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'ar_interval', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One row per open balance, per owner (payer, patient, unbilled), per as-of date.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'ar_snapshot_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The snapshot date.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'as_of_date';
EXEC sp_addextendedproperty N'MS_Description', N'Daily, weekly, month_end.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'snapshot_type';
EXEC sp_addextendedproperty N'MS_Description', N'The account''s visit.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'bill_id';
EXEC sp_addextendedproperty N'MS_Description', N'Payer, patient or unbilled.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'balance_owner';
EXEC sp_addextendedproperty N'MS_Description', N'Open amount for that owner.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'balance';
EXEC sp_addextendedproperty N'MS_Description', N'Reports by practice.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Patient accounts.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'patient_id';
EXEC sp_addextendedproperty N'MS_Description', N'The guarantor account responsible for the patient balance.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'guarantor_id';
EXEC sp_addextendedproperty N'MS_Description', N'When this row''s clock started.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'aging_date';
EXEC sp_addextendedproperty N'MS_Description', N'Age of the balance.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'days_outstanding';
EXEC sp_addextendedproperty N'MS_Description', N'0-30, 31-60, 61-90, 91-120 or 121+ days from aging_date.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'aging_bucket';
EXEC sp_addextendedproperty N'MS_Description', N'What the clock started from.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'aging_basis';
EXEC sp_addextendedproperty N'MS_Description', N'The claim on payer rows; blank for unbilled and self-pay.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'claim_id';
EXEC sp_addextendedproperty N'MS_Description', N'Who owes, or the expected payer on unbilled rows.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'Where the claim stands.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'claim_status';
EXEC sp_addextendedproperty N'MS_Description', N'Primary or secondary.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'claim_sequence';
EXEC sp_addextendedproperty N'MS_Description', N'Date sent.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'submitted_date';
EXEC sp_addextendedproperty N'MS_Description', N'Net AR.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'expected_collectible';
EXEC sp_addextendedproperty N'MS_Description', N'Stalled accounts.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'last_payment_date';
EXEC sp_addextendedproperty N'MS_Description', N'Stalled accounts.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'last_activity_date';
EXEC sp_addextendedproperty N'MS_Description', N'Follow-up queue.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'days_since_activity';
EXEC sp_addextendedproperty N'MS_Description', N'Patient statement timing.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'last_statement_date';
EXEC sp_addextendedproperty N'MS_Description', N'Denial-related AR.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'open_denied_amount';
EXEC sp_addextendedproperty N'MS_Description', N'Open denial exists.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'is_in_denial';
EXEC sp_addextendedproperty N'MS_Description', N'Balance below zero.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'is_credit';
EXEC sp_addextendedproperty N'MS_Description', N'When a credit balance was identified as an overpayment. Starts the 60-day refund clock for Medicare and Medicaid.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'overpayment_identified_date';
EXEC sp_addextendedproperty N'MS_Description', N'Refund deadline: identified date + 60 days for government payers, contract or state rule for others.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'refund_due_date';
EXEC sp_addextendedproperty N'MS_Description', N'Service date plus the payer''s filing limit.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'filing_deadline';
EXEC sp_addextendedproperty N'MS_Description', N'Copied.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'specialty_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'facility_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'service_date';
EXEC sp_addextendedproperty N'MS_Description', N'Procedure view.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'primary_cpt_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'Trend.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'change_since_last_snapshot';
EXEC sp_addextendedproperty N'MS_Description', N'1 while the balance is placed with an agency (rebuilt from collection_placement).', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'collections_agency_flag';
EXEC sp_addextendedproperty N'MS_Description', N'Worklists.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'next_action_date';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'ar_snapshot', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One appeal filed (or being prepared) against one denial at one level: first appeal, second appeal or external review. A status change is a new version.', N'SCHEMA', N'dbo', N'TABLE', N'appeal';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of the record: the same on every version. The primary key is (appeal_id, version). Every link from another table uses appeal_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.', N'SCHEMA', N'dbo', N'TABLE', N'appeal', N'COLUMN', N'appeal_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'appeal', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The practice''s own appeal tracking number, if it has one. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'appeal', N'COLUMN', N'appeal_number';
EXEC sp_addextendedproperty N'MS_Description', N'The denial being appealed. Every appeal belongs to one denial.', N'SCHEMA', N'dbo', N'TABLE', N'appeal', N'COLUMN', N'denial_id';
EXEC sp_addextendedproperty N'MS_Description', N'First, second or external_review.', N'SCHEMA', N'dbo', N'TABLE', N'appeal', N'COLUMN', N'appeal_level';
EXEC sp_addextendedproperty N'MS_Description', N'Drafted, approved, sent, answered, closed.', N'SCHEMA', N'dbo', N'TABLE', N'appeal', N'COLUMN', N'appeal_status';
EXEC sp_addextendedproperty N'MS_Description', N'Date the payer told the practice about the denial (or the decision on the earlier round). The appeal clock starts here.', N'SCHEMA', N'dbo', N'TABLE', N'appeal', N'COLUMN', N'clock_start_date';
EXEC sp_addextendedproperty N'MS_Description', N'Last day to file this appeal, from the payer rule or contract.', N'SCHEMA', N'dbo', N'TABLE', N'appeal', N'COLUMN', N'deadline_date';
EXEC sp_addextendedproperty N'MS_Description', N'Claim behind the denial, for quick reports.', N'SCHEMA', N'dbo', N'TABLE', N'appeal', N'COLUMN', N'claim_id';
EXEC sp_addextendedproperty N'MS_Description', N'Date the appeal went out. Blank while still a draft.', N'SCHEMA', N'dbo', N'TABLE', N'appeal', N'COLUMN', N'submitted_date';
EXEC sp_addextendedproperty N'MS_Description', N'Portal, fax, mail, 275 or FHIR.', N'SCHEMA', N'dbo', N'TABLE', N'appeal', N'COLUMN', N'submission_channel';
EXEC sp_addextendedproperty N'MS_Description', N'Dollars actually disputed in this round. Can be less than the denied amount.', N'SCHEMA', N'dbo', N'TABLE', N'appeal', N'COLUMN', N'amount_disputed';
EXEC sp_addextendedproperty N'MS_Description', N'How many documents were attached (note, authorization, EOB, policy). A count only, never the documents.', N'SCHEMA', N'dbo', N'TABLE', N'appeal', N'COLUMN', N'evidence_count';
EXEC sp_addextendedproperty N'MS_Description', N'Fingerprint of the final letter after human edits. Proves which letter went out without storing it.', N'SCHEMA', N'dbo', N'TABLE', N'appeal', N'COLUMN', N'letter_hash';
EXEC sp_addextendedproperty N'MS_Description', N'The payer''s case or reference number for the appeal. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'appeal', N'COLUMN', N'payer_reference';
EXEC sp_addextendedproperty N'MS_Description', N'Date the payer answered.', N'SCHEMA', N'dbo', N'TABLE', N'appeal', N'COLUMN', N'decision_date';
EXEC sp_addextendedproperty N'MS_Description', N'Overturned, partly_overturned, upheld or no_answer.', N'SCHEMA', N'dbo', N'TABLE', N'appeal', N'COLUMN', N'payer_decision';
EXEC sp_addextendedproperty N'MS_Description', N'1 if the denial was overturned in this round (fully or partly). Yes/no outcome used in overturn rate.', N'SCHEMA', N'dbo', N'TABLE', N'appeal', N'COLUMN', N'is_overturned';
EXEC sp_addextendedproperty N'MS_Description', N'Dollars recovered from this round, from the ledger.', N'SCHEMA', N'dbo', N'TABLE', N'appeal', N'COLUMN', N'recovered_amount';
EXEC sp_addextendedproperty N'MS_Description', N'The agent decision that drafted the appeal.', N'SCHEMA', N'dbo', N'TABLE', N'appeal', N'COLUMN', N'agent_decision_id';
EXEC sp_addextendedproperty N'MS_Description', N'The human review that approved the appeal or the write-off instead.', N'SCHEMA', N'dbo', N'TABLE', N'appeal', N'COLUMN', N'agent_approval_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied, so reports by practice never join up.', N'SCHEMA', N'dbo', N'TABLE', N'appeal', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied from the denial.', N'SCHEMA', N'dbo', N'TABLE', N'appeal', N'COLUMN', N'patient_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied, so win rates by payer need no join.', N'SCHEMA', N'dbo', N'TABLE', N'appeal', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'1 for the first row; higher for each change.', N'SCHEMA', N'dbo', N'TABLE', N'appeal', N'COLUMN', N'version';
EXEC sp_addextendedproperty N'MS_Description', N'1 on the latest version. Counts use current rows only.', N'SCHEMA', N'dbo', N'TABLE', N'appeal', N'COLUMN', N'is_current';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.', N'SCHEMA', N'dbo', N'TABLE', N'appeal', N'COLUMN', N'previous_appeal_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'appeal', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'appeal', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'appeal', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'appeal', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'appeal', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'appeal', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'appeal', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'appeal', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'appeal', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'appeal', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One statement or patient balance notice sent (or tried) to one patient: date, amount shown, channel, dunning level and delivery status. A status change is a new version.', N'SCHEMA', N'dbo', N'TABLE', N'patient_statement';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of the record: the same on every version. The primary key is (patient_statement_id, version). Every link from another table uses patient_statement_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.', N'SCHEMA', N'dbo', N'TABLE', N'patient_statement', N'COLUMN', N'patient_statement_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'patient_statement', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The number printed on the statement, if the practice has one. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'patient_statement', N'COLUMN', N'statement_number';
EXEC sp_addextendedproperty N'MS_Description', N'The patient who got the statement.', N'SCHEMA', N'dbo', N'TABLE', N'patient_statement', N'COLUMN', N'patient_id';
EXEC sp_addextendedproperty N'MS_Description', N'The guarantor account responsible for the patient balance.', N'SCHEMA', N'dbo', N'TABLE', N'patient_statement', N'COLUMN', N'guarantor_id';
EXEC sp_addextendedproperty N'MS_Description', N'Date printed on the statement.', N'SCHEMA', N'dbo', N'TABLE', N'patient_statement', N'COLUMN', N'statement_date';
EXEC sp_addextendedproperty N'MS_Description', N'Balance shown on the statement.', N'SCHEMA', N'dbo', N'TABLE', N'patient_statement', N'COLUMN', N'statement_amount';
EXEC sp_addextendedproperty N'MS_Description', N'Mail, portal, sms, phone or none.', N'SCHEMA', N'dbo', N'TABLE', N'patient_statement', N'COLUMN', N'channel';
EXEC sp_addextendedproperty N'MS_Description', N'Sent, delivered, bounced, returned, disputed, plan or hardship.', N'SCHEMA', N'dbo', N'TABLE', N'patient_statement', N'COLUMN', N'statement_status';
EXEC sp_addextendedproperty N'MS_Description', N'Copied, for reports by practice.', N'SCHEMA', N'dbo', N'TABLE', N'patient_statement', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'The bill the balance mostly belongs to. Blank for an account-level statement.', N'SCHEMA', N'dbo', N'TABLE', N'patient_statement', N'COLUMN', N'bill_id';
EXEC sp_addextendedproperty N'MS_Description', N'Claim the statement refers to, when the feed gives one.', N'SCHEMA', N'dbo', N'TABLE', N'patient_statement', N'COLUMN', N'claim_id';
EXEC sp_addextendedproperty N'MS_Description', N'Payment due date printed.', N'SCHEMA', N'dbo', N'TABLE', N'patient_statement', N'COLUMN', N'due_date';
EXEC sp_addextendedproperty N'MS_Description', N'When the message actually went out (channel and send time).', N'SCHEMA', N'dbo', N'TABLE', N'patient_statement', N'COLUMN', N'sent_at';
EXEC sp_addextendedproperty N'MS_Description', N'Date of the latest status (delivered, returned, disputed).', N'SCHEMA', N'dbo', N'TABLE', N'patient_statement', N'COLUMN', N'status_date';
EXEC sp_addextendedproperty N'MS_Description', N'0 first statement, then 1, 2, 3 for each firmer reminder.', N'SCHEMA', N'dbo', N'TABLE', N'patient_statement', N'COLUMN', N'dunning_level';
EXEC sp_addextendedproperty N'MS_Description', N'Date of the Reg F validation notice, if this statement carried one. Only when the balance is placed with a third-party collector (collection_placement.is_third_party = 1).', N'SCHEMA', N'dbo', N'TABLE', N'patient_statement', N'COLUMN', N'validation_notice_date';
EXEC sp_addextendedproperty N'MS_Description', N'Last day the patient may dispute the debt (Reg F). Only when the balance is placed with a third-party collector (collection_placement.is_third_party = 1).', N'SCHEMA', N'dbo', N'TABLE', N'patient_statement', N'COLUMN', N'dispute_window_end_date';
EXEC sp_addextendedproperty N'MS_Description', N'Placement the notice belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'patient_statement', N'COLUMN', N'collection_placement_id';
EXEC sp_addextendedproperty N'MS_Description', N'The payment plan the patient is on, if any.', N'SCHEMA', N'dbo', N'TABLE', N'patient_statement', N'COLUMN', N'payment_plan_id';
EXEC sp_addextendedproperty N'MS_Description', N'1 for the first row; higher for each change.', N'SCHEMA', N'dbo', N'TABLE', N'patient_statement', N'COLUMN', N'version';
EXEC sp_addextendedproperty N'MS_Description', N'1 on the latest version. Counts use current rows only.', N'SCHEMA', N'dbo', N'TABLE', N'patient_statement', N'COLUMN', N'is_current';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.', N'SCHEMA', N'dbo', N'TABLE', N'patient_statement', N'COLUMN', N'previous_patient_statement_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'patient_statement', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'patient_statement', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'patient_statement', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'patient_statement', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'patient_statement', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'patient_statement', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'patient_statement', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'patient_statement', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'patient_statement', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'patient_statement', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One provider-level adjustment on a payment that is not tied to a claim: a takeback, interest, recoupment or penalty (the 835 PLB segment).', N'SCHEMA', N'dbo', N'TABLE', N'payment_adjustment';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'payment_adjustment', N'COLUMN', N'payment_adjustment_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'payment_adjustment', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The payment (EFT or check) the adjustment came in.', N'SCHEMA', N'dbo', N'TABLE', N'payment_adjustment', N'COLUMN', N'payment_id';
EXEC sp_addextendedproperty N'MS_Description', N'Takeback, recoupment, interest, penalty, bonus or other.', N'SCHEMA', N'dbo', N'TABLE', N'payment_adjustment', N'COLUMN', N'adjustment_type';
EXEC sp_addextendedproperty N'MS_Description', N'Signed amount: negative takes money away from the deposit.', N'SCHEMA', N'dbo', N'TABLE', N'payment_adjustment', N'COLUMN', N'amount';
EXEC sp_addextendedproperty N'MS_Description', N'Date of the adjustment (payment date if the source gives none).', N'SCHEMA', N'dbo', N'TABLE', N'payment_adjustment', N'COLUMN', N'adjustment_date';
EXEC sp_addextendedproperty N'MS_Description', N'The 835 PLB reason code (for example WO for overpayment recovery, L6 for interest).', N'SCHEMA', N'dbo', N'TABLE', N'payment_adjustment', N'COLUMN', N'plb_reason_code';
EXEC sp_addextendedproperty N'MS_Description', N'Copied from the payment.', N'SCHEMA', N'dbo', N'TABLE', N'payment_adjustment', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied from the payment, for takebacks by payer.', N'SCHEMA', N'dbo', N'TABLE', N'payment_adjustment', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'Provider the adjustment applies to, when the payer names one.', N'SCHEMA', N'dbo', N'TABLE', N'payment_adjustment', N'COLUMN', N'payee_provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'payment_adjustment', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'payment_adjustment', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'payment_adjustment', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'payment_adjustment', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'payment_adjustment', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'payment_adjustment', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'payment_adjustment', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'payment_adjustment', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'payment_adjustment', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'payment_adjustment', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One claim as the payer adjudicated it on one remittance (835 CLP loop).', N'SCHEMA', N'dbo', N'TABLE', N'remittance_claim';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'remittance_claim', N'COLUMN', N'remittance_claim_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'remittance_claim', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The payment (ERA) it came on.', N'SCHEMA', N'dbo', N'TABLE', N'remittance_claim', N'COLUMN', N'payment_id';
EXEC sp_addextendedproperty N'MS_Description', N'The matched claim. Blank until matched.', N'SCHEMA', N'dbo', N'TABLE', N'remittance_claim', N'COLUMN', N'claim_id';
EXEC sp_addextendedproperty N'MS_Description', N'CLP01: our claim number as the payer echoes it. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'remittance_claim', N'COLUMN', N'patient_control_number';
EXEC sp_addextendedproperty N'MS_Description', N'CLP02: 1, 2, 3 processed as primary/secondary/tertiary, 4 denied, 19-23 forwarded or reversal (22).', N'SCHEMA', N'dbo', N'TABLE', N'remittance_claim', N'COLUMN', N'claim_status_code';
EXEC sp_addextendedproperty N'MS_Description', N'1 when CLP02 = 22.', N'SCHEMA', N'dbo', N'TABLE', N'remittance_claim', N'COLUMN', N'is_reversal';
EXEC sp_addextendedproperty N'MS_Description', N'CLP03.', N'SCHEMA', N'dbo', N'TABLE', N'remittance_claim', N'COLUMN', N'charge_amount';
EXEC sp_addextendedproperty N'MS_Description', N'CLP04.', N'SCHEMA', N'dbo', N'TABLE', N'remittance_claim', N'COLUMN', N'paid_amount';
EXEC sp_addextendedproperty N'MS_Description', N'CLP05.', N'SCHEMA', N'dbo', N'TABLE', N'remittance_claim', N'COLUMN', N'patient_responsibility';
EXEC sp_addextendedproperty N'MS_Description', N'CLP06.', N'SCHEMA', N'dbo', N'TABLE', N'remittance_claim', N'COLUMN', N'claim_filing_indicator';
EXEC sp_addextendedproperty N'MS_Description', N'CLP07. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'remittance_claim', N'COLUMN', N'payer_claim_number';
EXEC sp_addextendedproperty N'MS_Description', N'Sum of claim-level CAS amounts.', N'SCHEMA', N'dbo', N'TABLE', N'remittance_claim', N'COLUMN', N'claim_level_adjustment';
EXEC sp_addextendedproperty N'MS_Description', N'First MIA/MOA remark.', N'SCHEMA', N'dbo', N'TABLE', N'remittance_claim', N'COLUMN', N'remark_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the payer forwarded the claim (NM1*TT).', N'SCHEMA', N'dbo', N'TABLE', N'remittance_claim', N'COLUMN', N'is_crossover';
EXEC sp_addextendedproperty N'MS_Description', N'Payer it was forwarded to.', N'SCHEMA', N'dbo', N'TABLE', N'remittance_claim', N'COLUMN', N'crossover_payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'claim_number, payer_claim_number or fuzzy.', N'SCHEMA', N'dbo', N'TABLE', N'remittance_claim', N'COLUMN', N'match_method';
EXEC sp_addextendedproperty N'MS_Description', N'Copied, so reports skip the join.', N'SCHEMA', N'dbo', N'TABLE', N'remittance_claim', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied, so reports skip the join.', N'SCHEMA', N'dbo', N'TABLE', N'remittance_claim', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'remittance_claim', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'remittance_claim', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'remittance_claim', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'remittance_claim', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'remittance_claim', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'remittance_claim', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'remittance_claim', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'remittance_claim', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'remittance_claim', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'remittance_claim', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One deposit into the practice bank account: EFT, check batch, lockbox or card settlement.', N'SCHEMA', N'dbo', N'TABLE', N'bank_deposit';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'bank_deposit', N'COLUMN', N'bank_deposit_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'bank_deposit', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'Account owner.', N'SCHEMA', N'dbo', N'TABLE', N'bank_deposit', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Bank date.', N'SCHEMA', N'dbo', N'TABLE', N'bank_deposit', N'COLUMN', N'deposit_date';
EXEC sp_addextendedproperty N'MS_Description', N'Amount deposited.', N'SCHEMA', N'dbo', N'TABLE', N'bank_deposit', N'COLUMN', N'deposit_amount';
EXEC sp_addextendedproperty N'MS_Description', N'eft, check, lockbox, card_settlement.', N'SCHEMA', N'dbo', N'TABLE', N'bank_deposit', N'COLUMN', N'deposit_method';
EXEC sp_addextendedproperty N'MS_Description', N'ACH trace / TRN02 used to match the ERA. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'bank_deposit', N'COLUMN', N'trace_number';
EXEC sp_addextendedproperty N'MS_Description', N'Payer, when known.', N'SCHEMA', N'dbo', N'TABLE', N'bank_deposit', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'The matched ERA payment.', N'SCHEMA', N'dbo', N'TABLE', N'bank_deposit', N'COLUMN', N'payment_id';
EXEC sp_addextendedproperty N'MS_Description', N'matched, unmatched, partial, multiple.', N'SCHEMA', N'dbo', N'TABLE', N'bank_deposit', N'COLUMN', N'match_status';
EXEC sp_addextendedproperty N'MS_Description', N'When matched.', N'SCHEMA', N'dbo', N'TABLE', N'bank_deposit', N'COLUMN', N'matched_date';
EXEC sp_addextendedproperty N'MS_Description', N'Deposit minus matched payments.', N'SCHEMA', N'dbo', N'TABLE', N'bank_deposit', N'COLUMN', N'variance_amount';
EXEC sp_addextendedproperty N'MS_Description', N'Label of the account. Never the account number.', N'SCHEMA', N'dbo', N'TABLE', N'bank_deposit', N'COLUMN', N'bank_account_label';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'bank_deposit', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'bank_deposit', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'bank_deposit', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'bank_deposit', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'bank_deposit', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'bank_deposit', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'bank_deposit', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'bank_deposit', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'bank_deposit', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'bank_deposit', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One placement of a guarantor balance with a collection agency, through recall or close.', N'SCHEMA', N'dbo', N'TABLE', N'collection_placement';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of the record: the same on every version. The primary key is (collection_placement_id, version). Every link from another table uses collection_placement_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.', N'SCHEMA', N'dbo', N'TABLE', N'collection_placement', N'COLUMN', N'collection_placement_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'collection_placement', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'Agency account number. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'collection_placement', N'COLUMN', N'placement_number';
EXEC sp_addextendedproperty N'MS_Description', N'The guarantor account placed.', N'SCHEMA', N'dbo', N'TABLE', N'collection_placement', N'COLUMN', N'guarantor_id';
EXEC sp_addextendedproperty N'MS_Description', N'When placement is per patient.', N'SCHEMA', N'dbo', N'TABLE', N'collection_placement', N'COLUMN', N'patient_id';
EXEC sp_addextendedproperty N'MS_Description', N'The collection agency.', N'SCHEMA', N'dbo', N'TABLE', N'collection_placement', N'COLUMN', N'agency_code';
EXEC sp_addextendedproperty N'MS_Description', N'early_out (first-party, our name), bad_debt (third-party).', N'SCHEMA', N'dbo', N'TABLE', N'collection_placement', N'COLUMN', N'placement_type';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the agency collects in its own name; switches on Reg F fields on statements.', N'SCHEMA', N'dbo', N'TABLE', N'collection_placement', N'COLUMN', N'is_third_party';
EXEC sp_addextendedproperty N'MS_Description', N'Date placed.', N'SCHEMA', N'dbo', N'TABLE', N'collection_placement', N'COLUMN', N'placed_date';
EXEC sp_addextendedproperty N'MS_Description', N'Balance placed.', N'SCHEMA', N'dbo', N'TABLE', N'collection_placement', N'COLUMN', N'placed_amount';
EXEC sp_addextendedproperty N'MS_Description', N'Collected by the agency so far.', N'SCHEMA', N'dbo', N'TABLE', N'collection_placement', N'COLUMN', N'recovered_amount';
EXEC sp_addextendedproperty N'MS_Description', N'Fee kept by the agency.', N'SCHEMA', N'dbo', N'TABLE', N'collection_placement', N'COLUMN', N'agency_fee_amount';
EXEC sp_addextendedproperty N'MS_Description', N'placed, paying, recalled, closed_paid, closed_uncollectible, disputed.', N'SCHEMA', N'dbo', N'TABLE', N'collection_placement', N'COLUMN', N'placement_status';
EXEC sp_addextendedproperty N'MS_Description', N'When pulled back.', N'SCHEMA', N'dbo', N'TABLE', N'collection_placement', N'COLUMN', N'recall_date';
EXEC sp_addextendedproperty N'MS_Description', N'insurance_found, dispute, charity, error, paid.', N'SCHEMA', N'dbo', N'TABLE', N'collection_placement', N'COLUMN', N'recall_reason';
EXEC sp_addextendedproperty N'MS_Description', N'When closed.', N'SCHEMA', N'dbo', N'TABLE', N'collection_placement', N'COLUMN', N'closed_date';
EXEC sp_addextendedproperty N'MS_Description', N'1 if reported to a credit bureau (medical-debt reporting rules).', N'SCHEMA', N'dbo', N'TABLE', N'collection_placement', N'COLUMN', N'credit_reported';
EXEC sp_addextendedproperty N'MS_Description', N'Copied, so reports skip the join.', N'SCHEMA', N'dbo', N'TABLE', N'collection_placement', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'1 for the first row; higher for each change.', N'SCHEMA', N'dbo', N'TABLE', N'collection_placement', N'COLUMN', N'version';
EXEC sp_addextendedproperty N'MS_Description', N'1 on the latest version. Counts use current rows only.', N'SCHEMA', N'dbo', N'TABLE', N'collection_placement', N'COLUMN', N'is_current';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'collection_placement', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'collection_placement', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'collection_placement', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'collection_placement', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'collection_placement', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'collection_placement', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'collection_placement', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'collection_placement', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'collection_placement', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'collection_placement', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One row per decision an agent reached about one entity (claim, appointment, authorization and so on).', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision', N'COLUMN', N'agent_decision_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The run that made it.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision', N'COLUMN', N'agent_run_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied from the run.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision', N'COLUMN', N'agent_code';
EXEC sp_addextendedproperty N'MS_Description', N'Eligibility_ok, needs_auth, hold_claim, appeal, code_change, write_off_review and so on.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision', N'COLUMN', N'decision_type';
EXEC sp_addextendedproperty N'MS_Description', N'Which table the decision is about. Must agree with the typed link of the same entity (CHECK).', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision', N'COLUMN', N'entity_type';
EXEC sp_addextendedproperty N'MS_Description', N'Internal ID in that table.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision', N'COLUMN', N'entity_id';
EXEC sp_addextendedproperty N'MS_Description', N'Proceed, hold, flag, propose_change, no_action, needs_human.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision', N'COLUMN', N'outcome';
EXEC sp_addextendedproperty N'MS_Description', N'When decided.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision', N'COLUMN', N'decided_at';
EXEC sp_addextendedproperty N'MS_Description', N'Copied: shadow decisions are never acted on.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision', N'COLUMN', N'run_mode';
EXEC sp_addextendedproperty N'MS_Description', N'0 to 1. Blank when the agent is rule-based only.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision', N'COLUMN', N'confidence';
EXEC sp_addextendedproperty N'MS_Description', N'Short plain reason; never patient text. Scanned for identifiers at write time; a value that fails is refused.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision', N'COLUMN', N'reason_summary';
EXEC sp_addextendedproperty N'MS_Description', N'Rules evaluated (the details hold each one).', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision', N'COLUMN', N'rules_checked';
EXEC sp_addextendedproperty N'MS_Description', N'Rules that failed.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision', N'COLUMN', N'rules_failed';
EXEC sp_addextendedproperty N'MS_Description', N'Dollars the decision protects or affects.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision', N'COLUMN', N'amount_at_stake';
EXEC sp_addextendedproperty N'MS_Description', N'Lowest fallback step of any input used: tells readers how reliable it was.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision', N'COLUMN', N'data_fallback_level';
EXEC sp_addextendedproperty N'MS_Description', N'Accepted, changed, rejected, ignored: agreement with staff.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision', N'COLUMN', N'human_outcome';
EXEC sp_addextendedproperty N'MS_Description', N'When staff answered.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision', N'COLUMN', N'human_outcome_date';
EXEC sp_addextendedproperty N'MS_Description', N'A newer decision replaces an older one; the old row stays.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision', N'COLUMN', N'supersedes_decision_id';
EXEC sp_addextendedproperty N'MS_Description', N'1 on the latest decision for the entity and type.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision', N'COLUMN', N'is_current';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the inputs, so a replay can prove it saw the same data.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision', N'COLUMN', N'input_hash';
EXEC sp_addextendedproperty N'MS_Description', N'Reports by practice.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Patient level view.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision', N'COLUMN', N'patient_id';
EXEC sp_addextendedproperty N'MS_Description', N'Reports by payer.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'Reports by provider.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision', N'COLUMN', N'provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'Reports by specialty.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision', N'COLUMN', N'specialty_id';
EXEC sp_addextendedproperty N'MS_Description', N'The appointment concerned, when there is one.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision', N'COLUMN', N'appointment_id';
EXEC sp_addextendedproperty N'MS_Description', N'The visit concerned.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision', N'COLUMN', N'encounter_id';
EXEC sp_addextendedproperty N'MS_Description', N'The bill concerned.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision', N'COLUMN', N'bill_id';
EXEC sp_addextendedproperty N'MS_Description', N'The claim concerned.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision', N'COLUMN', N'claim_id';
EXEC sp_addextendedproperty N'MS_Description', N'The denial concerned.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision', N'COLUMN', N'denial_id';
EXEC sp_addextendedproperty N'MS_Description', N'The authorization concerned.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision', N'COLUMN', N'authorization_id';
EXEC sp_addextendedproperty N'MS_Description', N'What must be true for this decision to count as closed (for example task done and the rules pass again).', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision', N'COLUMN', N'recheck_condition';
EXEC sp_addextendedproperty N'MS_Description', N'Result of the re-check: passed, failed or pending.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision', N'COLUMN', N'recheck_result';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the prompt sent to the model for this decision. Blank when no model was used.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision', N'COLUMN', N'prompt_hash';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One row per dollar event an agent can claim: dollars detected, worked, submitted, accepted, recovered or avoided on one entity.', N'SCHEMA', N'dbo', N'TABLE', N'agent_value';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'agent_value', N'COLUMN', N'agent_value_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'agent_value', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'Which agent gets the credit, A1 to A15.', N'SCHEMA', N'dbo', N'TABLE', N'agent_value', N'COLUMN', N'agent_code';
EXEC sp_addextendedproperty N'MS_Description', N'Detected, worked, submitted, accepted, recovered, avoided. Lets one finding be followed from found to paid.', N'SCHEMA', N'dbo', N'TABLE', N'agent_value', N'COLUMN', N'value_stage';
EXEC sp_addextendedproperty N'MS_Description', N'Dollars at this stage. Never negative; a payer takeback is a new row with value_kind = reversal.', N'SCHEMA', N'dbo', N'TABLE', N'agent_value', N'COLUMN', N'amount';
EXEC sp_addextendedproperty N'MS_Description', N'amount with a sign: negative on value_kind = reversal. Reports sum this, never amount.', N'SCHEMA', N'dbo', N'TABLE', N'agent_value', N'COLUMN', N'signed_amount';
EXEC sp_addextendedproperty N'MS_Description', N'Date of the event: detection date for detected, payment date for recovered.', N'SCHEMA', N'dbo', N'TABLE', N'agent_value', N'COLUMN', N'value_date';
EXEC sp_addextendedproperty N'MS_Description', N'Table the dollars belong to (claim, denial, claim_line and so on). Must agree with the typed link of the same entity (CHECK).', N'SCHEMA', N'dbo', N'TABLE', N'agent_value', N'COLUMN', N'entity_type';
EXEC sp_addextendedproperty N'MS_Description', N'Internal ID in that table.', N'SCHEMA', N'dbo', N'TABLE', N'agent_value', N'COLUMN', N'entity_id';
EXEC sp_addextendedproperty N'MS_Description', N'The finding behind it. Follow the chain from detected to recovered.', N'SCHEMA', N'dbo', N'TABLE', N'agent_value', N'COLUMN', N'agent_finding_id';
EXEC sp_addextendedproperty N'MS_Description', N'The decision that produced it.', N'SCHEMA', N'dbo', N'TABLE', N'agent_value', N'COLUMN', N'agent_decision_id';
EXEC sp_addextendedproperty N'MS_Description', N'Reports by practice.', N'SCHEMA', N'dbo', N'TABLE', N'agent_value', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'The claim concerned.', N'SCHEMA', N'dbo', N'TABLE', N'agent_value', N'COLUMN', N'claim_id';
EXEC sp_addextendedproperty N'MS_Description', N'The denial concerned (appeal and overturn value).', N'SCHEMA', N'dbo', N'TABLE', N'agent_value', N'COLUMN', N'denial_id';
EXEC sp_addextendedproperty N'MS_Description', N'Value by payer, and the payer slice of a leak.', N'SCHEMA', N'dbo', N'TABLE', N'agent_value', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'Value by rendering provider.', N'SCHEMA', N'dbo', N'TABLE', N'agent_value', N'COLUMN', N'provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'Value by specialty.', N'SCHEMA', N'dbo', N'TABLE', N'agent_value', N'COLUMN', N'specialty_id';
EXEC sp_addextendedproperty N'MS_Description', N'Value by procedure; blank for a payer total.', N'SCHEMA', N'dbo', N'TABLE', N'agent_value', N'COLUMN', N'cpt_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'Proof: the 835 payment row that confirms recovered dollars. One payment is counted once.', N'SCHEMA', N'dbo', N'TABLE', N'agent_value', N'COLUMN', N'ledger_entry_id';
EXEC sp_addextendedproperty N'MS_Description', N'1 for a control group claim held back for measurement; the base of incremental value.', N'SCHEMA', N'dbo', N'TABLE', N'agent_value', N'COLUMN', N'is_holdout';
EXEC sp_addextendedproperty N'MS_Description', N'Dollars above what would have happened anyway, measured against holdout rows.', N'SCHEMA', N'dbo', N'TABLE', N'agent_value', N'COLUMN', N'incremental_amount';
EXEC sp_addextendedproperty N'MS_Description', N'Short type: underpayment, denial_overturn, rejection_fix, missed_charge, avoided_denial and so on.', N'SCHEMA', N'dbo', N'TABLE', N'agent_value', N'COLUMN', N'value_kind';
EXEC sp_addextendedproperty N'MS_Description', N'1 when no payment proves the amount (ladder step 2 or 3).', N'SCHEMA', N'dbo', N'TABLE', N'agent_value', N'COLUMN', N'is_estimate';
EXEC sp_addextendedproperty N'MS_Description', N'Share of the dollars credited to this agent when several agents helped; 0 to 1.', N'SCHEMA', N'dbo', N'TABLE', N'agent_value', N'COLUMN', N'attribution_share';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'agent_value', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'agent_value', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One row per execution of one agent: what started it, how it ended and what it cost.', N'SCHEMA', N'dbo', N'TABLE', N'agent_run';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'agent_run', N'COLUMN', N'agent_run_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'agent_run', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'Which agent, A1 to A15.', N'SCHEMA', N'dbo', N'TABLE', N'agent_run', N'COLUMN', N'agent_code';
EXEC sp_addextendedproperty N'MS_Description', N'Display name.', N'SCHEMA', N'dbo', N'TABLE', N'agent_run', N'COLUMN', N'agent_name';
EXEC sp_addextendedproperty N'MS_Description', N'Shadow (proposals only), assisted or live.', N'SCHEMA', N'dbo', N'TABLE', N'agent_run', N'COLUMN', N'run_mode';
EXEC sp_addextendedproperty N'MS_Description', N'Schedule, event, manual, retry.', N'SCHEMA', N'dbo', N'TABLE', N'agent_run', N'COLUMN', N'trigger_type';
EXEC sp_addextendedproperty N'MS_Description', N'Start time.', N'SCHEMA', N'dbo', N'TABLE', N'agent_run', N'COLUMN', N'started_at';
EXEC sp_addextendedproperty N'MS_Description', N'End time.', N'SCHEMA', N'dbo', N'TABLE', N'agent_run', N'COLUMN', N'ended_at';
EXEC sp_addextendedproperty N'MS_Description', N'Running, succeeded, partial, failed, cancelled.', N'SCHEMA', N'dbo', N'TABLE', N'agent_run', N'COLUMN', N'run_status';
EXEC sp_addextendedproperty N'MS_Description', N'Blank for a run across practices.', N'SCHEMA', N'dbo', N'TABLE', N'agent_run', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Entities the run looked at.', N'SCHEMA', N'dbo', N'TABLE', N'agent_run', N'COLUMN', N'items_in';
EXEC sp_addextendedproperty N'MS_Description', N'Decisions written.', N'SCHEMA', N'dbo', N'TABLE', N'agent_run', N'COLUMN', N'decisions_made';
EXEC sp_addextendedproperty N'MS_Description', N'Entities that failed.', N'SCHEMA', N'dbo', N'TABLE', N'agent_run', N'COLUMN', N'error_count';
EXEC sp_addextendedproperty N'MS_Description', N'Short error class, never raw data.', N'SCHEMA', N'dbo', N'TABLE', N'agent_run', N'COLUMN', N'error_summary';
EXEC sp_addextendedproperty N'MS_Description', N'Model used, if any.', N'SCHEMA', N'dbo', N'TABLE', N'agent_run', N'COLUMN', N'model_name';
EXEC sp_addextendedproperty N'MS_Description', N'For cost.', N'SCHEMA', N'dbo', N'TABLE', N'agent_run', N'COLUMN', N'input_tokens';
EXEC sp_addextendedproperty N'MS_Description', N'For cost.', N'SCHEMA', N'dbo', N'TABLE', N'agent_run', N'COLUMN', N'output_tokens';
EXEC sp_addextendedproperty N'MS_Description', N'Cost of the run, in dollars.', N'SCHEMA', N'dbo', N'TABLE', N'agent_run', N'COLUMN', N'cost_amount';
EXEC sp_addextendedproperty N'MS_Description', N'The run that started this one.', N'SCHEMA', N'dbo', N'TABLE', N'agent_run', N'COLUMN', N'trigger_run_id';
EXEC sp_addextendedproperty N'MS_Description', N'Agent version, for replay.', N'SCHEMA', N'dbo', N'TABLE', N'agent_run', N'COLUMN', N'code_version';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'agent_run', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'agent_run', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One row per rule or check evaluated inside a decision.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision_check';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision_check', N'COLUMN', N'agent_decision_check_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision_check', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The decision it explains.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision_check', N'COLUMN', N'agent_decision_id';
EXEC sp_addextendedproperty N'MS_Description', N'Order within the decision.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision_check', N'COLUMN', N'check_seq';
EXEC sp_addextendedproperty N'MS_Description', N'Rule or check evaluated.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision_check', N'COLUMN', N'rule_code';
EXEC sp_addextendedproperty N'MS_Description', N'Pass, fail, warn, skipped, unknown.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision_check', N'COLUMN', N'check_result';
EXEC sp_addextendedproperty N'MS_Description', N'Copied.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision_check', N'COLUMN', N'agent_code';
EXEC sp_addextendedproperty N'MS_Description', N'Version of the rule at the time.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision_check', N'COLUMN', N'rule_version';
EXEC sp_addextendedproperty N'MS_Description', N'Payer policy, public rule, client rule, learned.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision_check', N'COLUMN', N'rule_source';
EXEC sp_addextendedproperty N'MS_Description', N'Block, review, info.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision_check', N'COLUMN', N'severity';
EXEC sp_addextendedproperty N'MS_Description', N'What was seen, as short text. Never a name, date of birth or raw member number. Scanned for identifiers at write time; a value that fails is refused.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision_check', N'COLUMN', N'observed_value';
EXEC sp_addextendedproperty N'MS_Description', N'What the rule wanted. Scanned for identifiers at write time; a value that fails is refused.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision_check', N'COLUMN', N'expected_value';
EXEC sp_addextendedproperty N'MS_Description', N'Canonical table the input came from.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision_check', N'COLUMN', N'input_table';
EXEC sp_addextendedproperty N'MS_Description', N'Fallback step of that input (matches data_feed).', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision_check', N'COLUMN', N'input_fallback_level';
EXEC sp_addextendedproperty N'MS_Description', N'Copied.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision_check', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision_check', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied when relevant.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision_check', N'COLUMN', N'cpt_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'Pointer to evidence, never its content.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision_check', N'COLUMN', N'evidence_ref';
EXEC sp_addextendedproperty N'MS_Description', N'The exact version of the payer rule this check ran against.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision_check', N'COLUMN', N'payer_rule_id';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision_check', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'agent_decision_check', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One issue an agent found: a missed charge, underpayment, preventable denial, coding gap, document gap and so on.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of the record: the same on every version. The primary key is (agent_finding_id, version). Every link from another table uses agent_finding_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'agent_finding_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The run that found it.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'agent_run_id';
EXEC sp_addextendedproperty N'MS_Description', N'Which agent.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'agent_code';
EXEC sp_addextendedproperty N'MS_Description', N'Missed_charge, underpayment, preventable_denial, coding_gap, documentation_gap, eligibility_gap, auth_gap, timely_filing_risk and so on.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'finding_type';
EXEC sp_addextendedproperty N'MS_Description', N'Table the issue is about. Must agree with the typed link of the same entity (CHECK).', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'entity_type';
EXEC sp_addextendedproperty N'MS_Description', N'Internal ID in that table.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'entity_id';
EXEC sp_addextendedproperty N'MS_Description', N'When found.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'found_date';
EXEC sp_addextendedproperty N'MS_Description', N'Open, accepted, fixed, dismissed, expired.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'finding_status';
EXEC sp_addextendedproperty N'MS_Description', N'Dollars at risk if left.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'amount_at_risk';
EXEC sp_addextendedproperty N'MS_Description', N'Dollars recovered or avoided, from the ledger.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'amount_recovered';
EXEC sp_addextendedproperty N'MS_Description', N'Journey stage that could have caught it.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'upstream_stage';
EXEC sp_addextendedproperty N'MS_Description', N'Could have been caught earlier.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'is_preventable';
EXEC sp_addextendedproperty N'MS_Description', N'High, medium, low.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'severity';
EXEC sp_addextendedproperty N'MS_Description', N'Filing or appeal limit.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'deadline_date';
EXEC sp_addextendedproperty N'MS_Description', N'Time to fix.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'resolved_date';
EXEC sp_addextendedproperty N'MS_Description', N'Fixed, written_off, not_an_issue, expired.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'resolution';
EXEC sp_addextendedproperty N'MS_Description', N'The decision that raised it.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'agent_decision_id';
EXEC sp_addextendedproperty N'MS_Description', N'Same issue seen again maps to the same hash: no duplicates.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'finding_hash';
EXEC sp_addextendedproperty N'MS_Description', N'Short plain description; no patient text. Scanned for identifiers at write time; a value that fails is refused.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'summary';
EXEC sp_addextendedproperty N'MS_Description', N'Reports by practice.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Patient level view.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'patient_id';
EXEC sp_addextendedproperty N'MS_Description', N'Reports by payer.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'Reports by provider.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'Reports by specialty.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'specialty_id';
EXEC sp_addextendedproperty N'MS_Description', N'The appointment concerned, when there is one.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'appointment_id';
EXEC sp_addextendedproperty N'MS_Description', N'The visit concerned.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'encounter_id';
EXEC sp_addextendedproperty N'MS_Description', N'The bill concerned.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'bill_id';
EXEC sp_addextendedproperty N'MS_Description', N'The claim concerned.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'claim_id';
EXEC sp_addextendedproperty N'MS_Description', N'The denial concerned.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'denial_id';
EXEC sp_addextendedproperty N'MS_Description', N'The authorization concerned.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'authorization_id';
EXEC sp_addextendedproperty N'MS_Description', N'What the agent suggests (for example a visit code and diagnoses).', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'suggested_value';
EXEC sp_addextendedproperty N'MS_Description', N'What the person finally approved.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'final_value';
EXEC sp_addextendedproperty N'MS_Description', N'Dollar difference at the contract rate between what was billed and what is suggested.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'value_difference';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the finding is an over-coding risk; 0 when it is an opportunity.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'is_compliance_risk';
EXEC sp_addextendedproperty N'MS_Description', N'Predicted chance that the claim is denied.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'predicted_probability';
EXEC sp_addextendedproperty N'MS_Description', N'Most likely denial reason group.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'predicted_reason_category';
EXEC sp_addextendedproperty N'MS_Description', N'Allowed amount the twin expects.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'predicted_allowed_amount';
EXEC sp_addextendedproperty N'MS_Description', N'Copay, coinsurance and deductible the twin expects the patient to owe.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'predicted_patient_responsibility';
EXEC sp_addextendedproperty N'MS_Description', N'1 for the first row; higher for each change.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'version';
EXEC sp_addextendedproperty N'MS_Description', N'1 on the latest version. Counts use current rows only.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'is_current';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'previous_agent_finding_id';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'agent_finding', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One work item for a person or another agent. A status change is a new version.', N'SCHEMA', N'dbo', N'TABLE', N'agent_task';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of the record: the same on every version. The primary key is (agent_task_id, version). Every link from another table uses agent_task_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.', N'SCHEMA', N'dbo', N'TABLE', N'agent_task', N'COLUMN', N'agent_task_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'agent_task', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'Fix_claim, appeal, chase_note, verify_coverage, request_auth, review_write_off and so on.', N'SCHEMA', N'dbo', N'TABLE', N'agent_task', N'COLUMN', N'task_type';
EXEC sp_addextendedproperty N'MS_Description', N'Billing, coding, front desk, provider, manager, or an agent.', N'SCHEMA', N'dbo', N'TABLE', N'agent_task', N'COLUMN', N'owner_role';
EXEC sp_addextendedproperty N'MS_Description', N'Open, in_progress, done, cancelled, blocked.', N'SCHEMA', N'dbo', N'TABLE', N'agent_task', N'COLUMN', N'task_status';
EXEC sp_addextendedproperty N'MS_Description', N'When raised.', N'SCHEMA', N'dbo', N'TABLE', N'agent_task', N'COLUMN', N'created_date';
EXEC sp_addextendedproperty N'MS_Description', N'Raising agent.', N'SCHEMA', N'dbo', N'TABLE', N'agent_task', N'COLUMN', N'agent_code';
EXEC sp_addextendedproperty N'MS_Description', N'Table the task is about. Must agree with the typed link of the same entity (CHECK).', N'SCHEMA', N'dbo', N'TABLE', N'agent_task', N'COLUMN', N'entity_type';
EXEC sp_addextendedproperty N'MS_Description', N'Internal ID in that table.', N'SCHEMA', N'dbo', N'TABLE', N'agent_task', N'COLUMN', N'entity_id';
EXEC sp_addextendedproperty N'MS_Description', N'The decision that raised it.', N'SCHEMA', N'dbo', N'TABLE', N'agent_task', N'COLUMN', N'agent_decision_id';
EXEC sp_addextendedproperty N'MS_Description', N'The finding that raised it.', N'SCHEMA', N'dbo', N'TABLE', N'agent_task', N'COLUMN', N'agent_finding_id';
EXEC sp_addextendedproperty N'MS_Description', N'High, normal, low.', N'SCHEMA', N'dbo', N'TABLE', N'agent_task', N'COLUMN', N'priority';
EXEC sp_addextendedproperty N'MS_Description', N'Target date.', N'SCHEMA', N'dbo', N'TABLE', N'agent_task', N'COLUMN', N'due_date';
EXEC sp_addextendedproperty N'MS_Description', N'Time to complete.', N'SCHEMA', N'dbo', N'TABLE', N'agent_task', N'COLUMN', N'completed_date';
EXEC sp_addextendedproperty N'MS_Description', N'Pseudonymous assignee, never a name. Holds the staff_id of the pseudonymous person.', N'SCHEMA', N'dbo', N'TABLE', N'agent_task', N'COLUMN', N'assigned_to_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'Dollars involved.', N'SCHEMA', N'dbo', N'TABLE', N'agent_task', N'COLUMN', N'amount_at_stake';
EXEC sp_addextendedproperty N'MS_Description', N'Done, no_action_needed, declined.', N'SCHEMA', N'dbo', N'TABLE', N'agent_task', N'COLUMN', N'outcome';
EXEC sp_addextendedproperty N'MS_Description', N'Short label; no patient text. Scanned for identifiers at write time; a value that fails is refused.', N'SCHEMA', N'dbo', N'TABLE', N'agent_task', N'COLUMN', N'title';
EXEC sp_addextendedproperty N'MS_Description', N'Reports by practice.', N'SCHEMA', N'dbo', N'TABLE', N'agent_task', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Patient level view.', N'SCHEMA', N'dbo', N'TABLE', N'agent_task', N'COLUMN', N'patient_id';
EXEC sp_addextendedproperty N'MS_Description', N'Reports by payer.', N'SCHEMA', N'dbo', N'TABLE', N'agent_task', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'Reports by provider.', N'SCHEMA', N'dbo', N'TABLE', N'agent_task', N'COLUMN', N'provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'Reports by specialty.', N'SCHEMA', N'dbo', N'TABLE', N'agent_task', N'COLUMN', N'specialty_id';
EXEC sp_addextendedproperty N'MS_Description', N'The appointment concerned, when there is one.', N'SCHEMA', N'dbo', N'TABLE', N'agent_task', N'COLUMN', N'appointment_id';
EXEC sp_addextendedproperty N'MS_Description', N'The visit concerned.', N'SCHEMA', N'dbo', N'TABLE', N'agent_task', N'COLUMN', N'encounter_id';
EXEC sp_addextendedproperty N'MS_Description', N'The bill concerned.', N'SCHEMA', N'dbo', N'TABLE', N'agent_task', N'COLUMN', N'bill_id';
EXEC sp_addextendedproperty N'MS_Description', N'The claim concerned.', N'SCHEMA', N'dbo', N'TABLE', N'agent_task', N'COLUMN', N'claim_id';
EXEC sp_addextendedproperty N'MS_Description', N'The denial concerned.', N'SCHEMA', N'dbo', N'TABLE', N'agent_task', N'COLUMN', N'denial_id';
EXEC sp_addextendedproperty N'MS_Description', N'The authorization concerned.', N'SCHEMA', N'dbo', N'TABLE', N'agent_task', N'COLUMN', N'authorization_id';
EXEC sp_addextendedproperty N'MS_Description', N'Minutes a person spent on the item.', N'SCHEMA', N'dbo', N'TABLE', N'agent_task', N'COLUMN', N'minutes_spent';
EXEC sp_addextendedproperty N'MS_Description', N'How the payer was reached: portal, phone, fax, clearinghouse, EMR inbox.', N'SCHEMA', N'dbo', N'TABLE', N'agent_task', N'COLUMN', N'contact_channel';
EXEC sp_addextendedproperty N'MS_Description', N'0 provider, 1 provider again, 2 practice manager, 3 medical director.', N'SCHEMA', N'dbo', N'TABLE', N'agent_task', N'COLUMN', N'escalation_level';
EXEC sp_addextendedproperty N'MS_Description', N'How many reminders were sent for the item.', N'SCHEMA', N'dbo', N'TABLE', N'agent_task', N'COLUMN', N'reminder_count';
EXEC sp_addextendedproperty N'MS_Description', N'1 for the first row; higher for each change.', N'SCHEMA', N'dbo', N'TABLE', N'agent_task', N'COLUMN', N'version';
EXEC sp_addextendedproperty N'MS_Description', N'1 on the latest version. Counts use current rows only.', N'SCHEMA', N'dbo', N'TABLE', N'agent_task', N'COLUMN', N'is_current';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.', N'SCHEMA', N'dbo', N'TABLE', N'agent_task', N'COLUMN', N'previous_agent_task_id';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'agent_task', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'agent_task', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One row per approval or rejection of a proposed change. Append-only.', N'SCHEMA', N'dbo', N'TABLE', N'agent_approval';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'agent_approval', N'COLUMN', N'agent_approval_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'agent_approval', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The proposal being approved.', N'SCHEMA', N'dbo', N'TABLE', N'agent_approval', N'COLUMN', N'agent_decision_id';
EXEC sp_addextendedproperty N'MS_Description', N'Write_off, refund, claim_change, code_change, send_to_payer, setting_change.', N'SCHEMA', N'dbo', N'TABLE', N'agent_approval', N'COLUMN', N'approval_type';
EXEC sp_addextendedproperty N'MS_Description', N'Approved, rejected, expired.', N'SCHEMA', N'dbo', N'TABLE', N'agent_approval', N'COLUMN', N'approval_status';
EXEC sp_addextendedproperty N'MS_Description', N'Pseudonymous approver (staff_id). Required when approval_status = approved (CHECK); blank on rejected or expired rows.', N'SCHEMA', N'dbo', N'TABLE', N'agent_approval', N'COLUMN', N'approved_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'Role at the time.', N'SCHEMA', N'dbo', N'TABLE', N'agent_approval', N'COLUMN', N'approver_role';
EXEC sp_addextendedproperty N'MS_Description', N'When answered.', N'SCHEMA', N'dbo', N'TABLE', N'agent_approval', N'COLUMN', N'approval_date';
EXEC sp_addextendedproperty N'MS_Description', N'The task it closed.', N'SCHEMA', N'dbo', N'TABLE', N'agent_approval', N'COLUMN', N'agent_task_id';
EXEC sp_addextendedproperty N'MS_Description', N'Dollars approved.', N'SCHEMA', N'dbo', N'TABLE', N'agent_approval', N'COLUMN', N'amount_approved';
EXEC sp_addextendedproperty N'MS_Description', N'Within the approver''s limit.', N'SCHEMA', N'dbo', N'TABLE', N'agent_approval', N'COLUMN', N'limit_checked';
EXEC sp_addextendedproperty N'MS_Description', N'Why approved or rejected.', N'SCHEMA', N'dbo', N'TABLE', N'agent_approval', N'COLUMN', N'reason_code';
EXEC sp_addextendedproperty N'MS_Description', N'Table affected.', N'SCHEMA', N'dbo', N'TABLE', N'agent_approval', N'COLUMN', N'entity_type';
EXEC sp_addextendedproperty N'MS_Description', N'Internal ID affected.', N'SCHEMA', N'dbo', N'TABLE', N'agent_approval', N'COLUMN', N'entity_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied.', N'SCHEMA', N'dbo', N'TABLE', N'agent_approval', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Exact time.', N'SCHEMA', N'dbo', N'TABLE', N'agent_approval', N'COLUMN', N'approval_ts';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'agent_approval', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'agent_approval', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One row per thing sent out to the PM, EHR, clearinghouse or payer, and what came back. A retry is a new version.', N'SCHEMA', N'dbo', N'TABLE', N'agent_writeback';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of the record: the same on every version. The primary key is (agent_writeback_id, version). Every link from another table uses agent_writeback_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.', N'SCHEMA', N'dbo', N'TABLE', N'agent_writeback', N'COLUMN', N'agent_writeback_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'agent_writeback', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The decision it carries out.', N'SCHEMA', N'dbo', N'TABLE', N'agent_writeback', N'COLUMN', N'agent_decision_id';
EXEC sp_addextendedproperty N'MS_Description', N'Pm, ehr, clearinghouse, payer_portal, scheduler.', N'SCHEMA', N'dbo', N'TABLE', N'agent_writeback', N'COLUMN', N'target_system';
EXEC sp_addextendedproperty N'MS_Description', N'Note, task, 270, 278, 837_correction, status_update, appeal_packet and so on.', N'SCHEMA', N'dbo', N'TABLE', N'agent_writeback', N'COLUMN', N'writeback_type';
EXEC sp_addextendedproperty N'MS_Description', N'Not_sent_shadow, queued, sent, acknowledged, failed.', N'SCHEMA', N'dbo', N'TABLE', N'agent_writeback', N'COLUMN', N'send_status';
EXEC sp_addextendedproperty N'MS_Description', N'Time of the attempt.', N'SCHEMA', N'dbo', N'TABLE', N'agent_writeback', N'COLUMN', N'attempted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Required for money or record changes.', N'SCHEMA', N'dbo', N'TABLE', N'agent_writeback', N'COLUMN', N'agent_approval_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied.', N'SCHEMA', N'dbo', N'TABLE', N'agent_writeback', N'COLUMN', N'agent_code';
EXEC sp_addextendedproperty N'MS_Description', N'Table concerned.', N'SCHEMA', N'dbo', N'TABLE', N'agent_writeback', N'COLUMN', N'entity_type';
EXEC sp_addextendedproperty N'MS_Description', N'Internal ID concerned.', N'SCHEMA', N'dbo', N'TABLE', N'agent_writeback', N'COLUMN', N'entity_id';
EXEC sp_addextendedproperty N'MS_Description', N'Retry count.', N'SCHEMA', N'dbo', N'TABLE', N'agent_writeback', N'COLUMN', N'attempt_no';
EXEC sp_addextendedproperty N'MS_Description', N'Acknowledgement or error class.', N'SCHEMA', N'dbo', N'TABLE', N'agent_writeback', N'COLUMN', N'response_code';
EXEC sp_addextendedproperty N'MS_Description', N'Time of the reply.', N'SCHEMA', N'dbo', N'TABLE', N'agent_writeback', N'COLUMN', N'response_at';
EXEC sp_addextendedproperty N'MS_Description', N'The target system''s reference. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'agent_writeback', N'COLUMN', N'external_ref';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of what was sent. Payloads themselves are not stored.', N'SCHEMA', N'dbo', N'TABLE', N'agent_writeback', N'COLUMN', N'payload_hash';
EXEC sp_addextendedproperty N'MS_Description', N'Copied.', N'SCHEMA', N'dbo', N'TABLE', N'agent_writeback', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied when relevant.', N'SCHEMA', N'dbo', N'TABLE', N'agent_writeback', N'COLUMN', N'claim_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied when relevant.', N'SCHEMA', N'dbo', N'TABLE', N'agent_writeback', N'COLUMN', N'appointment_id';
EXEC sp_addextendedproperty N'MS_Description', N'1 for the first row; higher for each change.', N'SCHEMA', N'dbo', N'TABLE', N'agent_writeback', N'COLUMN', N'version';
EXEC sp_addextendedproperty N'MS_Description', N'1 on the latest version. Counts use current rows only.', N'SCHEMA', N'dbo', N'TABLE', N'agent_writeback', N'COLUMN', N'is_current';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.', N'SCHEMA', N'dbo', N'TABLE', N'agent_writeback', N'COLUMN', N'previous_agent_writeback_id';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'agent_writeback', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'agent_writeback', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One row per stored prediction: a cash, recoverable or claim payment forecast, with its range and, later, what actually happened.', N'SCHEMA', N'dbo', N'TABLE', N'agent_forecast';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of the record: the same on every version. The primary key is (agent_forecast_id, version). Every link from another table uses agent_forecast_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.', N'SCHEMA', N'dbo', N'TABLE', N'agent_forecast', N'COLUMN', N'agent_forecast_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'agent_forecast', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'Cash_week, cash_28d, cash_later, claim_week_chance, recoverable_month.', N'SCHEMA', N'dbo', N'TABLE', N'agent_forecast', N'COLUMN', N'forecast_type';
EXEC sp_addextendedproperty N'MS_Description', N'Date the forecast was made. Each day''s forecast is kept, so later scoring uses what was known then.', N'SCHEMA', N'dbo', N'TABLE', N'agent_forecast', N'COLUMN', N'as_of_date';
EXEC sp_addextendedproperty N'MS_Description', N'First day of the period predicted.', N'SCHEMA', N'dbo', N'TABLE', N'agent_forecast', N'COLUMN', N'target_start_date';
EXEC sp_addextendedproperty N'MS_Description', N'Last day of the period predicted. For cash_later, as-of date plus 365 days.', N'SCHEMA', N'dbo', N'TABLE', N'agent_forecast', N'COLUMN', N'target_end_date';
EXEC sp_addextendedproperty N'MS_Description', N'Expected dollars in the period (chance times balance for one claim).', N'SCHEMA', N'dbo', N'TABLE', N'agent_forecast', N'COLUMN', N'expected_amount';
EXEC sp_addextendedproperty N'MS_Description', N'Low end of the range (80% by default).', N'SCHEMA', N'dbo', N'TABLE', N'agent_forecast', N'COLUMN', N'low_amount';
EXEC sp_addextendedproperty N'MS_Description', N'High end of the range.', N'SCHEMA', N'dbo', N'TABLE', N'agent_forecast', N'COLUMN', N'high_amount';
EXEC sp_addextendedproperty N'MS_Description', N'Chance a claim is paid in the period, 0 to 1. Blank for dollar-only rows.', N'SCHEMA', N'dbo', N'TABLE', N'agent_forecast', N'COLUMN', N'probability';
EXEC sp_addextendedproperty N'MS_Description', N'Open claims behind the row.', N'SCHEMA', N'dbo', N'TABLE', N'agent_forecast', N'COLUMN', N'claim_count';
EXEC sp_addextendedproperty N'MS_Description', N'Reports by practice.', N'SCHEMA', N'dbo', N'TABLE', N'agent_forecast', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Forecast by payer; blank for all payers.', N'SCHEMA', N'dbo', N'TABLE', N'agent_forecast', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'Claim for a claim chance; practice or payer for a total.', N'SCHEMA', N'dbo', N'TABLE', N'agent_forecast', N'COLUMN', N'entity_type';
EXEC sp_addextendedproperty N'MS_Description', N'Internal ID of the claim for a claim chance; blank for totals.', N'SCHEMA', N'dbo', N'TABLE', N'agent_forecast', N'COLUMN', N'entity_id';
EXEC sp_addextendedproperty N'MS_Description', N'What was really paid in the period (835 payments in ledger_entry). Filled when the period closes.', N'SCHEMA', N'dbo', N'TABLE', N'agent_forecast', N'COLUMN', N'actual_amount';
EXEC sp_addextendedproperty N'MS_Description', N'Date the actual was filled in.', N'SCHEMA', N'dbo', N'TABLE', N'agent_forecast', N'COLUMN', N'actual_known_date';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the actual landed inside low and high; coverage is the share of 1s.', N'SCHEMA', N'dbo', N'TABLE', N'agent_forecast', N'COLUMN', N'within_range';
EXEC sp_addextendedproperty N'MS_Description', N'Confidence level of the range, 0.80 by default.', N'SCHEMA', N'dbo', N'TABLE', N'agent_forecast', N'COLUMN', N'interval_level';
EXEC sp_addextendedproperty N'MS_Description', N'Model or method used.', N'SCHEMA', N'dbo', N'TABLE', N'agent_forecast', N'COLUMN', N'model_name';
EXEC sp_addextendedproperty N'MS_Description', N'Agent version, for replay.', N'SCHEMA', N'dbo', N'TABLE', N'agent_forecast', N'COLUMN', N'code_version';
EXEC sp_addextendedproperty N'MS_Description', N'1 for the first row; higher for each change.', N'SCHEMA', N'dbo', N'TABLE', N'agent_forecast', N'COLUMN', N'version';
EXEC sp_addextendedproperty N'MS_Description', N'1 on the latest version. Counts use current rows only.', N'SCHEMA', N'dbo', N'TABLE', N'agent_forecast', N'COLUMN', N'is_current';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.', N'SCHEMA', N'dbo', N'TABLE', N'agent_forecast', N'COLUMN', N'previous_agent_forecast_id';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'agent_forecast', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'agent_forecast', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'A patient. No names, birth dates, addresses or raw member numbers are stored.', N'SCHEMA', N'dbo', N'TABLE', N'patient';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'patient', N'COLUMN', N'patient_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'patient', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'Salted hash of the client''s patient number. The only link back to the source. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'patient', N'COLUMN', N'patient_number_hash';
EXEC sp_addextendedproperty N'MS_Description', N'The same person across member IDs or practices.', N'SCHEMA', N'dbo', N'TABLE', N'patient', N'COLUMN', N'master_patient_hash';
EXEC sp_addextendedproperty N'MS_Description', N'Duplicate records merged at the source.', N'SCHEMA', N'dbo', N'TABLE', N'patient', N'COLUMN', N'merged_into_patient_id';
EXEC sp_addextendedproperty N'MS_Description', N'Year only; age at service.', N'SCHEMA', N'dbo', N'TABLE', N'patient', N'COLUMN', N'birth_year';
EXEC sp_addextendedproperty N'MS_Description', N'Ages above 89 are grouped as 90+.', N'SCHEMA', N'dbo', N'TABLE', N'patient', N'COLUMN', N'is_age_90_plus';
EXEC sp_addextendedproperty N'MS_Description', N'M, F, U. Gender-specific procedure edits.', N'SCHEMA', N'dbo', N'TABLE', N'patient', N'COLUMN', N'sex';
EXEC sp_addextendedproperty N'MS_Description', N'State rules and regional reports.', N'SCHEMA', N'dbo', N'TABLE', N'patient', N'COLUMN', N'state';
EXEC sp_addextendedproperty N'MS_Description', N'Home practice.', N'SCHEMA', N'dbo', N'TABLE', N'patient', N'COLUMN', N'primary_practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'New vs established.', N'SCHEMA', N'dbo', N'TABLE', N'patient', N'COLUMN', N'first_seen_date';
EXEC sp_addextendedproperty N'MS_Description', N'Lapsed patients.', N'SCHEMA', N'dbo', N'TABLE', N'patient', N'COLUMN', N'last_seen_date';
EXEC sp_addextendedproperty N'MS_Description', N'Current primary coverage.', N'SCHEMA', N'dbo', N'TABLE', N'patient', N'COLUMN', N'primary_coverage_id';
EXEC sp_addextendedproperty N'MS_Description', N'The guarantor account responsible for the patient balance.', N'SCHEMA', N'dbo', N'TABLE', N'patient', N'COLUMN', N'guarantor_id';
EXEC sp_addextendedproperty N'MS_Description', N'No active coverage.', N'SCHEMA', N'dbo', N'TABLE', N'patient', N'COLUMN', N'is_self_pay';
EXEC sp_addextendedproperty N'MS_Description', N'Geography. Stored as 000 for the 3-digit zips with fewer than 20,000 people (HIPAA Safe Harbor).', N'SCHEMA', N'dbo', N'TABLE', N'patient', N'COLUMN', N'zip3';
EXEC sp_addextendedproperty N'MS_Description', N'Communication.', N'SCHEMA', N'dbo', N'TABLE', N'patient', N'COLUMN', N'language';
EXEC sp_addextendedproperty N'MS_Description', N'Stops statements.', N'SCHEMA', N'dbo', N'TABLE', N'patient', N'COLUMN', N'is_deceased';
EXEC sp_addextendedproperty N'MS_Description', N'Lifecycle: 0 once retired.', N'SCHEMA', N'dbo', N'TABLE', N'patient', N'COLUMN', N'is_active';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'patient', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'patient', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'patient', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'patient', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'patient', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'patient', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'patient', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'patient', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from.', N'SCHEMA', N'dbo', N'TABLE', N'patient', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'patient', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One insurance policy for a patient, per period. A change closes the old row and adds a new one.', N'SCHEMA', N'dbo', N'TABLE', N'coverage';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of the record: the same on every version. The primary key is (coverage_id, version). Every link from another table uses coverage_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.', N'SCHEMA', N'dbo', N'TABLE', N'coverage', N'COLUMN', N'coverage_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'coverage', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'Whose policy.', N'SCHEMA', N'dbo', N'TABLE', N'coverage', N'COLUMN', N'patient_id';
EXEC sp_addextendedproperty N'MS_Description', N'The insurer.', N'SCHEMA', N'dbo', N'TABLE', N'coverage', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'The plan (product) under the payer.', N'SCHEMA', N'dbo', N'TABLE', N'coverage', N'COLUMN', N'payer_plan_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the member ID. The raw ID is never stored; eligibility reads it from the source at send time. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'coverage', N'COLUMN', N'member_number_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 primary, 2 secondary, 3 tertiary.', N'SCHEMA', N'dbo', N'TABLE', N'coverage', N'COLUMN', N'coverage_order';
EXEC sp_addextendedproperty N'MS_Description', N'Policy start.', N'SCHEMA', N'dbo', N'TABLE', N'coverage', N'COLUMN', N'effective_date';
EXEC sp_addextendedproperty N'MS_Description', N'Policy end; blank while open.', N'SCHEMA', N'dbo', N'TABLE', N'coverage', N'COLUMN', N'termination_date';
EXEC sp_addextendedproperty N'MS_Description', N'PPO, HMO, EPO, POS, Medicare Advantage, traditional Medicare, Medicaid managed care.', N'SCHEMA', N'dbo', N'TABLE', N'coverage', N'COLUMN', N'plan_type';
EXEC sp_addextendedproperty N'MS_Description', N'Display.', N'SCHEMA', N'dbo', N'TABLE', N'coverage', N'COLUMN', N'plan_name';
EXEC sp_addextendedproperty N'MS_Description', N'Group identification. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'coverage', N'COLUMN', N'group_number_hash';
EXEC sp_addextendedproperty N'MS_Description', N'Self, spouse, child, other: sets the dependent level.', N'SCHEMA', N'dbo', N'TABLE', N'coverage', N'COLUMN', N'relationship_to_holder';
EXEC sp_addextendedproperty N'MS_Description', N'When coverage was last checked.', N'SCHEMA', N'dbo', N'TABLE', N'coverage', N'COLUMN', N'last_verified_date';
EXEC sp_addextendedproperty N'MS_Description', N'Active, inactive, not found.', N'SCHEMA', N'dbo', N'TABLE', N'coverage', N'COLUMN', N'last_verified_status';
EXEC sp_addextendedproperty N'MS_Description', N'HMO referral rules.', N'SCHEMA', N'dbo', N'TABLE', N'coverage', N'COLUMN', N'requires_referral';
EXEC sp_addextendedproperty N'MS_Description', N'HMO primary care provider.', N'SCHEMA', N'dbo', N'TABLE', N'coverage', N'COLUMN', N'pcp_provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'Latest verified benefit.', N'SCHEMA', N'dbo', N'TABLE', N'coverage', N'COLUMN', N'copay_amount';
EXEC sp_addextendedproperty N'MS_Description', N'Latest verified benefit, as a fraction 0 to 1. Cache of the latest eligibility_check; never edited directly.', N'SCHEMA', N'dbo', N'TABLE', N'coverage', N'COLUMN', N'coinsurance_pct';
EXEC sp_addextendedproperty N'MS_Description', N'Latest verified benefit.', N'SCHEMA', N'dbo', N'TABLE', N'coverage', N'COLUMN', N'deductible_remaining';
EXEC sp_addextendedproperty N'MS_Description', N'Links family members under one subscriber. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'coverage', N'COLUMN', N'subscriber_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 for the first row; higher for each change.', N'SCHEMA', N'dbo', N'TABLE', N'coverage', N'COLUMN', N'version';
EXEC sp_addextendedproperty N'MS_Description', N'1 on the latest version. Counts use current rows only.', N'SCHEMA', N'dbo', N'TABLE', N'coverage', N'COLUMN', N'is_current';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.', N'SCHEMA', N'dbo', N'TABLE', N'coverage', N'COLUMN', N'previous_coverage_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'coverage', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'coverage', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'coverage', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'coverage', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'coverage', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'coverage', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'coverage', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'coverage', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'coverage', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'coverage', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'A prior authorization as the payer issued it. An extension or revision closes the old row and adds a new one.', N'SCHEMA', N'dbo', N'TABLE', N'authorization';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of the record: the same on every version. The primary key is (authorization_id, version). Every link from another table uses authorization_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.', N'SCHEMA', N'dbo', N'TABLE', N'authorization', N'COLUMN', N'authorization_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'authorization', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The payer''s number; a pending request uses our request reference. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'authorization', N'COLUMN', N'authorization_number';
EXEC sp_addextendedproperty N'MS_Description', N'Whose authorization.', N'SCHEMA', N'dbo', N'TABLE', N'authorization', N'COLUMN', N'patient_id';
EXEC sp_addextendedproperty N'MS_Description', N'With which payer.', N'SCHEMA', N'dbo', N'TABLE', N'authorization', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'Reports by practice.', N'SCHEMA', N'dbo', N'TABLE', N'authorization', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Requested, pended, certified, modified, not_certified, cancelled, expired.', N'SCHEMA', N'dbo', N'TABLE', N'authorization', N'COLUMN', N'authorization_status';
EXEC sp_addextendedproperty N'MS_Description', N'The policy it applies to.', N'SCHEMA', N'dbo', N'TABLE', N'authorization', N'COLUMN', N'coverage_id';
EXEC sp_addextendedproperty N'MS_Description', N'The main procedure, for quick reports. Every authorized code and its units are in authorization_line.', N'SCHEMA', N'dbo', N'TABLE', N'authorization', N'COLUMN', N'primary_cpt_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'Overuse and remaining units. Header total; per-code units are on authorization_line.', N'SCHEMA', N'dbo', N'TABLE', N'authorization', N'COLUMN', N'units_approved';
EXEC sp_addextendedproperty N'MS_Description', N'Rebuilt from claims. Header total; per-code units are on authorization_line.', N'SCHEMA', N'dbo', N'TABLE', N'authorization', N'COLUMN', N'units_used';
EXEC sp_addextendedproperty N'MS_Description', N'The approved window.', N'SCHEMA', N'dbo', N'TABLE', N'authorization', N'COLUMN', N'valid_from';
EXEC sp_addextendedproperty N'MS_Description', N'The approved window.', N'SCHEMA', N'dbo', N'TABLE', N'authorization', N'COLUMN', N'valid_to';
EXEC sp_addextendedproperty N'MS_Description', N'Turnaround time.', N'SCHEMA', N'dbo', N'TABLE', N'authorization', N'COLUMN', N'request_date';
EXEC sp_addextendedproperty N'MS_Description', N'Turnaround time.', N'SCHEMA', N'dbo', N'TABLE', N'authorization', N'COLUMN', N'decision_date';
EXEC sp_addextendedproperty N'MS_Description', N'Outpatient, inpatient, referral, predetermination, retro.', N'SCHEMA', N'dbo', N'TABLE', N'authorization', N'COLUMN', N'authorization_type';
EXEC sp_addextendedproperty N'MS_Description', N'Who asked.', N'SCHEMA', N'dbo', N'TABLE', N'authorization', N'COLUMN', N'requesting_provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'Who will perform.', N'SCHEMA', N'dbo', N'TABLE', N'authorization', N'COLUMN', N'rendering_provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'Standard or expedited.', N'SCHEMA', N'dbo', N'TABLE', N'authorization', N'COLUMN', N'urgency';
EXEC sp_addextendedproperty N'MS_Description', N'X12, portal, phone, fax.', N'SCHEMA', N'dbo', N'TABLE', N'authorization', N'COLUMN', N'request_channel';
EXEC sp_addextendedproperty N'MS_Description', N'Reason the payer gave.', N'SCHEMA', N'dbo', N'TABLE', N'authorization', N'COLUMN', N'decision_reason_code';
EXEC sp_addextendedproperty N'MS_Description', N'Diagnosis on the request.', N'SCHEMA', N'dbo', N'TABLE', N'authorization', N'COLUMN', N'diagnosis_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'Location.', N'SCHEMA', N'dbo', N'TABLE', N'authorization', N'COLUMN', N'facility_id';
EXEC sp_addextendedproperty N'MS_Description', N'Units or visits the practice asked for. Header total; per-code units are on authorization_line.', N'SCHEMA', N'dbo', N'TABLE', N'authorization', N'COLUMN', N'units_requested';
EXEC sp_addextendedproperty N'MS_Description', N'Place-of-service code on the request (for example 11 office, 22 outpatient hospital).', N'SCHEMA', N'dbo', N'TABLE', N'authorization', N'COLUMN', N'place_of_service_id';
EXEC sp_addextendedproperty N'MS_Description', N'1 for the first row; higher for each change.', N'SCHEMA', N'dbo', N'TABLE', N'authorization', N'COLUMN', N'version';
EXEC sp_addextendedproperty N'MS_Description', N'1 on the latest version. Counts use current rows only.', N'SCHEMA', N'dbo', N'TABLE', N'authorization', N'COLUMN', N'is_current';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.', N'SCHEMA', N'dbo', N'TABLE', N'authorization', N'COLUMN', N'previous_authorization_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'authorization', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'authorization', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'authorization', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'authorization', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'authorization', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'authorization', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'authorization', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'authorization', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'authorization', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'authorization', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One authorized service on an authorization: code, units and decision.', N'SCHEMA', N'dbo', N'TABLE', N'authorization_line';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'authorization_line', N'COLUMN', N'authorization_line_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'authorization_line', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The authorization (stable ID).', N'SCHEMA', N'dbo', N'TABLE', N'authorization_line', N'COLUMN', N'authorization_id';
EXEC sp_addextendedproperty N'MS_Description', N'Position within the authorization.', N'SCHEMA', N'dbo', N'TABLE', N'authorization_line', N'COLUMN', N'line_number';
EXEC sp_addextendedproperty N'MS_Description', N'Code authorized, or the first code of a range.', N'SCHEMA', N'dbo', N'TABLE', N'authorization_line', N'COLUMN', N'cpt_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'Last code of a range.', N'SCHEMA', N'dbo', N'TABLE', N'authorization_line', N'COLUMN', N'cpt_code_to_id';
EXEC sp_addextendedproperty N'MS_Description', N'Modifier the approval is tied to.', N'SCHEMA', N'dbo', N'TABLE', N'authorization_line', N'COLUMN', N'modifier_id';
EXEC sp_addextendedproperty N'MS_Description', N'units, visits or days.', N'SCHEMA', N'dbo', N'TABLE', N'authorization_line', N'COLUMN', N'unit_type';
EXEC sp_addextendedproperty N'MS_Description', N'Asked for.', N'SCHEMA', N'dbo', N'TABLE', N'authorization_line', N'COLUMN', N'units_requested';
EXEC sp_addextendedproperty N'MS_Description', N'Approved.', N'SCHEMA', N'dbo', N'TABLE', N'authorization_line', N'COLUMN', N'units_approved';
EXEC sp_addextendedproperty N'MS_Description', N'Used so far, rebuilt from claim lines.', N'SCHEMA', N'dbo', N'TABLE', N'authorization_line', N'COLUMN', N'units_used';
EXEC sp_addextendedproperty N'MS_Description', N'certified, modified, not_certified or pended.', N'SCHEMA', N'dbo', N'TABLE', N'authorization_line', N'COLUMN', N'line_status';
EXEC sp_addextendedproperty N'MS_Description', N'When different from the header.', N'SCHEMA', N'dbo', N'TABLE', N'authorization_line', N'COLUMN', N'valid_from';
EXEC sp_addextendedproperty N'MS_Description', N'When different from the header.', N'SCHEMA', N'dbo', N'TABLE', N'authorization_line', N'COLUMN', N'valid_to';
EXEC sp_addextendedproperty N'MS_Description', N'Copied, so reports skip the join.', N'SCHEMA', N'dbo', N'TABLE', N'authorization_line', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied, so reports skip the join.', N'SCHEMA', N'dbo', N'TABLE', N'authorization_line', N'COLUMN', N'patient_id';
EXEC sp_addextendedproperty N'MS_Description', N'Copied, so reports skip the join.', N'SCHEMA', N'dbo', N'TABLE', N'authorization_line', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'authorization_line', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'authorization_line', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'authorization_line', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'authorization_line', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'authorization_line', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'authorization_line', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'authorization_line', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'authorization_line', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'authorization_line', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'authorization_line', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One guarantor account: the person (or patient) financially responsible for patient balances. Pseudonymous.', N'SCHEMA', N'dbo', N'TABLE', N'guarantor';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of the record: the same on every version. The primary key is (guarantor_id, version). Every link from another table uses guarantor_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.', N'SCHEMA', N'dbo', N'TABLE', N'guarantor', N'COLUMN', N'guarantor_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'guarantor', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The PM guarantor account number. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'guarantor', N'COLUMN', N'guarantor_number';
EXEC sp_addextendedproperty N'MS_Description', N'Salted hash of the guarantor identity, for matching across loads. Never the name.', N'SCHEMA', N'dbo', N'TABLE', N'guarantor', N'COLUMN', N'guarantor_hash';
EXEC sp_addextendedproperty N'MS_Description', N'self, parent, spouse, legal_guardian, other_person, organization.', N'SCHEMA', N'dbo', N'TABLE', N'guarantor', N'COLUMN', N'guarantor_type';
EXEC sp_addextendedproperty N'MS_Description', N'Practice that owns the account (blank when shared across practices).', N'SCHEMA', N'dbo', N'TABLE', N'guarantor', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'State of the guarantor (statement and collection rules).', N'SCHEMA', N'dbo', N'TABLE', N'guarantor', N'COLUMN', N'state';
EXEC sp_addextendedproperty N'MS_Description', N'Same Safe Harbor rule as patient.zip3.', N'SCHEMA', N'dbo', N'TABLE', N'guarantor', N'COLUMN', N'zip3';
EXEC sp_addextendedproperty N'MS_Description', N'active, collections, bad_debt, closed.', N'SCHEMA', N'dbo', N'TABLE', N'guarantor', N'COLUMN', N'account_status';
EXEC sp_addextendedproperty N'MS_Description', N'1 when built as a self-guarantor account because the source sent none.', N'SCHEMA', N'dbo', N'TABLE', N'guarantor', N'COLUMN', N'is_inferred';
EXEC sp_addextendedproperty N'MS_Description', N'Guarantor uses the patient portal (statement channel).', N'SCHEMA', N'dbo', N'TABLE', N'guarantor', N'COLUMN', N'has_portal_account';
EXEC sp_addextendedproperty N'MS_Description', N'Lifecycle: 0 once closed.', N'SCHEMA', N'dbo', N'TABLE', N'guarantor', N'COLUMN', N'is_active';
EXEC sp_addextendedproperty N'MS_Description', N'1 for the first row; higher for each change.', N'SCHEMA', N'dbo', N'TABLE', N'guarantor', N'COLUMN', N'version';
EXEC sp_addextendedproperty N'MS_Description', N'1 on the latest version. Counts use current rows only.', N'SCHEMA', N'dbo', N'TABLE', N'guarantor', N'COLUMN', N'is_current';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'guarantor', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'guarantor', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'guarantor', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'guarantor', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'guarantor', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'guarantor', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'guarantor', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'guarantor', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'guarantor', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'guarantor', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One pseudonymous staff member who approves changes or owns tasks. Never a name.', N'SCHEMA', N'dbo', N'TABLE', N'staff';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'staff', N'COLUMN', N'staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'staff', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'Pseudonymous code of the person, for example B01 or C03. Restricted so it is not shown in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'staff', N'COLUMN', N'staff_number';
EXEC sp_addextendedproperty N'MS_Description', N'Practice the person works for.', N'SCHEMA', N'dbo', N'TABLE', N'staff', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Job role: billing specialist, denial specialist, coder, manager.', N'SCHEMA', N'dbo', N'TABLE', N'staff', N'COLUMN', N'staff_role';
EXEC sp_addextendedproperty N'MS_Description', N'Team: billing or coding.', N'SCHEMA', N'dbo', N'TABLE', N'staff', N'COLUMN', N'team';
EXEC sp_addextendedproperty N'MS_Description', N'Working hours per week; capacity is hours times handling time.', N'SCHEMA', N'dbo', N'TABLE', N'staff', N'COLUMN', N'weekly_hours';
EXEC sp_addextendedproperty N'MS_Description', N'First day in the role.', N'SCHEMA', N'dbo', N'TABLE', N'staff', N'COLUMN', N'start_date';
EXEC sp_addextendedproperty N'MS_Description', N'Last day in the role. Blank while active.', N'SCHEMA', N'dbo', N'TABLE', N'staff', N'COLUMN', N'end_date';
EXEC sp_addextendedproperty N'MS_Description', N'1 while the person can be assigned work.', N'SCHEMA', N'dbo', N'TABLE', N'staff', N'COLUMN', N'is_active';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'staff', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'staff', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'staff', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'staff', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'staff', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'staff', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'staff', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'staff', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'staff', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'staff', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One enrollment or screening event for a provider: a status change with a payer, or one exclusion-list check.', N'SCHEMA', N'dbo', N'TABLE', N'enrollment';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'enrollment', N'COLUMN', N'enrollment_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'enrollment', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The credentialing system''s own number for the status row or screening result. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'enrollment', N'COLUMN', N'enrollment_number';
EXEC sp_addextendedproperty N'MS_Description', N'Provider enrolled or screened. NPI is read from provider.npi.', N'SCHEMA', N'dbo', N'TABLE', N'enrollment', N'COLUMN', N'provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'Payer enrolled with. Blank for a screening event.', N'SCHEMA', N'dbo', N'TABLE', N'enrollment', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'Practice the provider bills under.', N'SCHEMA', N'dbo', N'TABLE', N'enrollment', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Site where the provider works for this payer.', N'SCHEMA', N'dbo', N'TABLE', N'enrollment', N'COLUMN', N'facility_id';
EXEC sp_addextendedproperty N'MS_Description', N'status for an enrollment change, screening for an exclusion-list check.', N'SCHEMA', N'dbo', N'TABLE', N'enrollment', N'COLUMN', N'event_type';
EXEC sp_addextendedproperty N'MS_Description', N'Day the status was recorded, or the day the list was checked.', N'SCHEMA', N'dbo', N'TABLE', N'enrollment', N'COLUMN', N'event_date';
EXEC sp_addextendedproperty N'MS_Description', N'pending, active, expired, denied or terminated. Blank on a screening event.', N'SCHEMA', N'dbo', N'TABLE', N'enrollment', N'COLUMN', N'enrollment_status';
EXEC sp_addextendedproperty N'MS_Description', N'New application, renewal, revalidation, change or termination.', N'SCHEMA', N'dbo', N'TABLE', N'enrollment', N'COLUMN', N'enrollment_type';
EXEC sp_addextendedproperty N'MS_Description', N'Program the enrollment covers: Medicare, Medicaid, commercial, EDI (electronic claims with the clearinghouse).', N'SCHEMA', N'dbo', N'TABLE', N'enrollment', N'COLUMN', N'plan_program_code';
EXEC sp_addextendedproperty N'MS_Description', N'Day the application went in. Gives enrollment cycle time.', N'SCHEMA', N'dbo', N'TABLE', N'enrollment', N'COLUMN', N'submitted_date';
EXEC sp_addextendedproperty N'MS_Description', N'Day the enrollment became active.', N'SCHEMA', N'dbo', N'TABLE', N'enrollment', N'COLUMN', N'effective_date';
EXEC sp_addextendedproperty N'MS_Description', N'Day it lapses. Blank means no expiry on file.', N'SCHEMA', N'dbo', N'TABLE', N'enrollment', N'COLUMN', N'expires_date';
EXEC sp_addextendedproperty N'MS_Description', N'Date the payer requires revalidation.', N'SCHEMA', N'dbo', N'TABLE', N'enrollment', N'COLUMN', N'revalidation_due_date';
EXEC sp_addextendedproperty N'MS_Description', N'Date of the last revalidation.', N'SCHEMA', N'dbo', N'TABLE', N'enrollment', N'COLUMN', N'last_revalidated_date';
EXEC sp_addextendedproperty N'MS_Description', N'Number the payer gave the provider. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'enrollment', N'COLUMN', N'payer_provider_number';
EXEC sp_addextendedproperty N'MS_Description', N'Payer or portal tracking number of the application. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'enrollment', N'COLUMN', N'application_number';
EXEC sp_addextendedproperty N'MS_Description', N'Code for why the payer refused or ended the enrollment. No free text.', N'SCHEMA', N'dbo', N'TABLE', N'enrollment', N'COLUMN', N'end_reason_code';
EXEC sp_addextendedproperty N'MS_Description', N'List checked: OIG, SAM, STATE. Blank on a status event.', N'SCHEMA', N'dbo', N'TABLE', N'enrollment', N'COLUMN', N'screening_source';
EXEC sp_addextendedproperty N'MS_Description', N'clear or excluded. Blank on a status event.', N'SCHEMA', N'dbo', N'TABLE', N'enrollment', N'COLUMN', N'screening_result';
EXEC sp_addextendedproperty N'MS_Description', N'Release date of the list used, so a later list can be told apart.', N'SCHEMA', N'dbo', N'TABLE', N'enrollment', N'COLUMN', N'screening_list_date';
EXEC sp_addextendedproperty N'MS_Description', N'Type of exclusion, as a list code.', N'SCHEMA', N'dbo', N'TABLE', N'enrollment', N'COLUMN', N'exclusion_type';
EXEC sp_addextendedproperty N'MS_Description', N'Day the provider was excluded.', N'SCHEMA', N'dbo', N'TABLE', N'enrollment', N'COLUMN', N'excluded_date';
EXEC sp_addextendedproperty N'MS_Description', N'Day the provider was reinstated.', N'SCHEMA', N'dbo', N'TABLE', N'enrollment', N'COLUMN', N'reinstated_date';
EXEC sp_addextendedproperty N'MS_Description', N'How the provider was matched on the list: npi, name_dob, name. Weaker methods need review.', N'SCHEMA', N'dbo', N'TABLE', N'enrollment', N'COLUMN', N'match_method';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'enrollment', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'enrollment', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'enrollment', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'enrollment', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'enrollment', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'enrollment', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'enrollment', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'enrollment', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'enrollment', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'enrollment', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One identifier a provider holds besides the NPI: PTAN, Medicaid ID, state license, DEA ...', N'SCHEMA', N'dbo', N'TABLE', N'provider_identifier';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'provider_identifier', N'COLUMN', N'provider_identifier_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'provider_identifier', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The provider.', N'SCHEMA', N'dbo', N'TABLE', N'provider_identifier', N'COLUMN', N'provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'ptan, medicaid_id, state_license, dea, caqh, payer_specific.', N'SCHEMA', N'dbo', N'TABLE', N'provider_identifier', N'COLUMN', N'identifier_type';
EXEC sp_addextendedproperty N'MS_Description', N'The identifier. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'provider_identifier', N'COLUMN', N'identifier_value';
EXEC sp_addextendedproperty N'MS_Description', N'For licenses and Medicaid IDs.', N'SCHEMA', N'dbo', N'TABLE', N'provider_identifier', N'COLUMN', N'issuing_state';
EXEC sp_addextendedproperty N'MS_Description', N'For payer-issued IDs.', N'SCHEMA', N'dbo', N'TABLE', N'provider_identifier', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'Issued.', N'SCHEMA', N'dbo', N'TABLE', N'provider_identifier', N'COLUMN', N'effective_from';
EXEC sp_addextendedproperty N'MS_Description', N'Expires. 9999-12-31 when it does not.', N'SCHEMA', N'dbo', N'TABLE', N'provider_identifier', N'COLUMN', N'effective_to';
EXEC sp_addextendedproperty N'MS_Description', N'Last checked against the issuer.', N'SCHEMA', N'dbo', N'TABLE', N'provider_identifier', N'COLUMN', N'verified_date';
EXEC sp_addextendedproperty N'MS_Description', N'Lifecycle: 0 once retired.', N'SCHEMA', N'dbo', N'TABLE', N'provider_identifier', N'COLUMN', N'is_active';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'provider_identifier', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'provider_identifier', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'provider_identifier', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'provider_identifier', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'provider_identifier', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'provider_identifier', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'provider_identifier', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'provider_identifier', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'provider_identifier', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'provider_identifier', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One provider working at one practice (and optionally a facility) for a period.', N'SCHEMA', N'dbo', N'TABLE', N'provider_practice';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'provider_practice', N'COLUMN', N'provider_practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'provider_practice', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The provider.', N'SCHEMA', N'dbo', N'TABLE', N'provider_practice', N'COLUMN', N'provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'The practice.', N'SCHEMA', N'dbo', N'TABLE', N'provider_practice', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Site, when it matters.', N'SCHEMA', N'dbo', N'TABLE', N'provider_practice', N'COLUMN', N'facility_id';
EXEC sp_addextendedproperty N'MS_Description', N'rendering, billing, supervising.', N'SCHEMA', N'dbo', N'TABLE', N'provider_practice', N'COLUMN', N'affiliation_role';
EXEC sp_addextendedproperty N'MS_Description', N'1 on the home practice.', N'SCHEMA', N'dbo', N'TABLE', N'provider_practice', N'COLUMN', N'is_primary';
EXEC sp_addextendedproperty N'MS_Description', N'Start.', N'SCHEMA', N'dbo', N'TABLE', N'provider_practice', N'COLUMN', N'start_date';
EXEC sp_addextendedproperty N'MS_Description', N'9999-12-31 while active.', N'SCHEMA', N'dbo', N'TABLE', N'provider_practice', N'COLUMN', N'end_date';
EXEC sp_addextendedproperty N'MS_Description', N'Share of full time.', N'SCHEMA', N'dbo', N'TABLE', N'provider_practice', N'COLUMN', N'fte';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'provider_practice', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'provider_practice', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'provider_practice', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'provider_practice', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'provider_practice', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'provider_practice', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'provider_practice', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'provider_practice', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'provider_practice', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'provider_practice', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One EDI enrollment of a practice or provider with a payer for one transaction: ERA, EFT, claims, eligibility, claim status or attachments.', N'SCHEMA', N'dbo', N'TABLE', N'edi_enrollment';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of the record: the same on every version. The primary key is (edi_enrollment_id, version). Every link from another table uses edi_enrollment_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.', N'SCHEMA', N'dbo', N'TABLE', N'edi_enrollment', N'COLUMN', N'edi_enrollment_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'edi_enrollment', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'Enrolling practice.', N'SCHEMA', N'dbo', N'TABLE', N'edi_enrollment', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'When enrolled per provider.', N'SCHEMA', N'dbo', N'TABLE', N'edi_enrollment', N'COLUMN', N'provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'Payer.', N'SCHEMA', N'dbo', N'TABLE', N'edi_enrollment', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'era_835, eft, claim_837, elig_270, status_276, attach_275.', N'SCHEMA', N'dbo', N'TABLE', N'edi_enrollment', N'COLUMN', N'transaction_type';
EXEC sp_addextendedproperty N'MS_Description', N'Clearinghouse the enrollment runs through.', N'SCHEMA', N'dbo', N'TABLE', N'edi_enrollment', N'COLUMN', N'clearinghouse_code';
EXEC sp_addextendedproperty N'MS_Description', N'not_enrolled, submitted, pending, enrolled, rejected, terminated.', N'SCHEMA', N'dbo', N'TABLE', N'edi_enrollment', N'COLUMN', N'enrollment_status';
EXEC sp_addextendedproperty N'MS_Description', N'When submitted.', N'SCHEMA', N'dbo', N'TABLE', N'edi_enrollment', N'COLUMN', N'submitted_date';
EXEC sp_addextendedproperty N'MS_Description', N'When live.', N'SCHEMA', N'dbo', N'TABLE', N'edi_enrollment', N'COLUMN', N'effective_date';
EXEC sp_addextendedproperty N'MS_Description', N'When ended.', N'SCHEMA', N'dbo', N'TABLE', N'edi_enrollment', N'COLUMN', N'terminated_date';
EXEC sp_addextendedproperty N'MS_Description', N'1 when deduced from files seen.', N'SCHEMA', N'dbo', N'TABLE', N'edi_enrollment', N'COLUMN', N'is_inferred';
EXEC sp_addextendedproperty N'MS_Description', N'Payer ID used for this transaction.', N'SCHEMA', N'dbo', N'TABLE', N'edi_enrollment', N'COLUMN', N'payer_identifier_id';
EXEC sp_addextendedproperty N'MS_Description', N'1 for the first row; higher for each change.', N'SCHEMA', N'dbo', N'TABLE', N'edi_enrollment', N'COLUMN', N'version';
EXEC sp_addextendedproperty N'MS_Description', N'1 on the latest version. Counts use current rows only.', N'SCHEMA', N'dbo', N'TABLE', N'edi_enrollment', N'COLUMN', N'is_current';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'edi_enrollment', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'edi_enrollment', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'edi_enrollment', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'edi_enrollment', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'edi_enrollment', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'edi_enrollment', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'edi_enrollment', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'edi_enrollment', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'edi_enrollment', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'edi_enrollment', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'A billing entity inside a client.', N'SCHEMA', N'dbo', N'TABLE', N'practice';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of the record: the same on every version. The primary key is (practice_id, version). Every link from another table uses practice_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.', N'SCHEMA', N'dbo', N'TABLE', N'practice', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'practice', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client''s code for the practice.', N'SCHEMA', N'dbo', N'TABLE', N'practice', N'COLUMN', N'practice_number';
EXEC sp_addextendedproperty N'MS_Description', N'Display.', N'SCHEMA', N'dbo', N'TABLE', N'practice', N'COLUMN', N'practice_name';
EXEC sp_addextendedproperty N'MS_Description', N'Billing entity on claims and contracts. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'practice', N'COLUMN', N'tax_id';
EXEC sp_addextendedproperty N'MS_Description', N'Billing NPI for group claims.', N'SCHEMA', N'dbo', N'TABLE', N'practice', N'COLUMN', N'group_npi';
EXEC sp_addextendedproperty N'MS_Description', N'Day cut-offs for aging, lag and snapshots.', N'SCHEMA', N'dbo', N'TABLE', N'practice', N'COLUMN', N'time_zone';
EXEC sp_addextendedproperty N'MS_Description', N'Fiscal reporting.', N'SCHEMA', N'dbo', N'TABLE', N'practice', N'COLUMN', N'fiscal_year_start_month';
EXEC sp_addextendedproperty N'MS_Description', N'Where history starts and opening balances apply.', N'SCHEMA', N'dbo', N'TABLE', N'practice', N'COLUMN', N'go_live_date';
EXEC sp_addextendedproperty N'MS_Description', N'Lifecycle: 0 once retired.', N'SCHEMA', N'dbo', N'TABLE', N'practice', N'COLUMN', N'is_active';
EXEC sp_addextendedproperty N'MS_Description', N'1 for the first row; higher for each change.', N'SCHEMA', N'dbo', N'TABLE', N'practice', N'COLUMN', N'version';
EXEC sp_addextendedproperty N'MS_Description', N'1 on the latest version. Counts use current rows only.', N'SCHEMA', N'dbo', N'TABLE', N'practice', N'COLUMN', N'is_current';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'practice', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'practice', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'practice', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'practice', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'practice', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'practice', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'practice', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'practice', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from.', N'SCHEMA', N'dbo', N'TABLE', N'practice', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'practice', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'A clinician or group.', N'SCHEMA', N'dbo', N'TABLE', N'provider';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of the record: the same on every version. The primary key is (provider_id, version). Every link from another table uses provider_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.', N'SCHEMA', N'dbo', N'TABLE', N'provider', N'COLUMN', N'provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'provider', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'National provider ID; links scheduler, EHR, claims and payer.', N'SCHEMA', N'dbo', N'TABLE', N'provider', N'COLUMN', N'npi';
EXEC sp_addextendedproperty N'MS_Description', N'The scheduler or EHR''s own provider code.', N'SCHEMA', N'dbo', N'TABLE', N'provider', N'COLUMN', N'provider_number';
EXEC sp_addextendedproperty N'MS_Description', N'Individual or group.', N'SCHEMA', N'dbo', N'TABLE', N'provider', N'COLUMN', N'provider_type';
EXEC sp_addextendedproperty N'MS_Description', N'Main specialty.', N'SCHEMA', N'dbo', N'TABLE', N'provider', N'COLUMN', N'specialty_id';
EXEC sp_addextendedproperty N'MS_Description', N'Enrollment and specialty mapping.', N'SCHEMA', N'dbo', N'TABLE', N'provider', N'COLUMN', N'taxonomy_code';
EXEC sp_addextendedproperty N'MS_Description', N'MD, DO, NP, PA.', N'SCHEMA', N'dbo', N'TABLE', N'provider', N'COLUMN', N'credential';
EXEC sp_addextendedproperty N'MS_Description', N'Display.', N'SCHEMA', N'dbo', N'TABLE', N'provider', N'COLUMN', N'provider_name';
EXEC sp_addextendedproperty N'MS_Description', N'Home practice; each transaction still carries the practice billed.', N'SCHEMA', N'dbo', N'TABLE', N'provider', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Productivity window.', N'SCHEMA', N'dbo', N'TABLE', N'provider', N'COLUMN', N'start_date';
EXEC sp_addextendedproperty N'MS_Description', N'Productivity window.', N'SCHEMA', N'dbo', N'TABLE', N'provider', N'COLUMN', N'end_date';
EXEC sp_addextendedproperty N'MS_Description', N'Supervised clinicians.', N'SCHEMA', N'dbo', N'TABLE', N'provider', N'COLUMN', N'supervising_provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'Lifecycle: 0 once retired.', N'SCHEMA', N'dbo', N'TABLE', N'provider', N'COLUMN', N'is_active';
EXEC sp_addextendedproperty N'MS_Description', N'1 for the first row; higher for each change.', N'SCHEMA', N'dbo', N'TABLE', N'provider', N'COLUMN', N'version';
EXEC sp_addextendedproperty N'MS_Description', N'1 on the latest version. Counts use current rows only.', N'SCHEMA', N'dbo', N'TABLE', N'provider', N'COLUMN', N'is_current';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'provider', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'provider', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'provider', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'provider', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'provider', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'provider', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'provider', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'provider', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from.', N'SCHEMA', N'dbo', N'TABLE', N'provider', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'provider', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'An insurer.', N'SCHEMA', N'dbo', N'TABLE', N'payer';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of the record: the same on every version. The primary key is (payer_id, version). Every link from another table uses payer_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.', N'SCHEMA', N'dbo', N'TABLE', N'payer', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'payer', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'Public payer ID used by the clearinghouse.', N'SCHEMA', N'dbo', N'TABLE', N'payer', N'COLUMN', N'payer_code';
EXEC sp_addextendedproperty N'MS_Description', N'Display.', N'SCHEMA', N'dbo', N'TABLE', N'payer', N'COLUMN', N'payer_name';
EXEC sp_addextendedproperty N'MS_Description', N'The PM''s own payer code.', N'SCHEMA', N'dbo', N'TABLE', N'payer', N'COLUMN', N'payer_number';
EXEC sp_addextendedproperty N'MS_Description', N'Commercial, medicare, medicaid, tricare, workers_comp, auto, self_pay.', N'SCHEMA', N'dbo', N'TABLE', N'payer', N'COLUMN', N'payer_type';
EXEC sp_addextendedproperty N'MS_Description', N'Rolls plans up to an organisation.', N'SCHEMA', N'dbo', N'TABLE', N'payer', N'COLUMN', N'parent_payer';
EXEC sp_addextendedproperty N'MS_Description', N'Timely-filing limit (default). payer_contract or payer_plan overrides it when set.', N'SCHEMA', N'dbo', N'TABLE', N'payer', N'COLUMN', N'filing_days';
EXEC sp_addextendedproperty N'MS_Description', N'Window for corrected claims (default). payer_contract or payer_plan overrides it when set.', N'SCHEMA', N'dbo', N'TABLE', N'payer', N'COLUMN', N'corrected_claim_days';
EXEC sp_addextendedproperty N'MS_Description', N'Appeal deadline (default). payer_contract or payer_plan overrides it when set.', N'SCHEMA', N'dbo', N'TABLE', N'payer', N'COLUMN', N'appeal_days';
EXEC sp_addextendedproperty N'MS_Description', N'Authorization planning.', N'SCHEMA', N'dbo', N'TABLE', N'payer', N'COLUMN', N'standard_turnaround_days';
EXEC sp_addextendedproperty N'MS_Description', N'Authorization planning.', N'SCHEMA', N'dbo', N'TABLE', N'payer', N'COLUMN', N'supports_electronic_auth';
EXEC sp_addextendedproperty N'MS_Description', N'Regional rules.', N'SCHEMA', N'dbo', N'TABLE', N'payer', N'COLUMN', N'state';
EXEC sp_addextendedproperty N'MS_Description', N'Role mailbox or portal, never a person.', N'SCHEMA', N'dbo', N'TABLE', N'payer', N'COLUMN', N'dispute_contact';
EXEC sp_addextendedproperty N'MS_Description', N'Lifecycle: 0 once retired.', N'SCHEMA', N'dbo', N'TABLE', N'payer', N'COLUMN', N'is_active';
EXEC sp_addextendedproperty N'MS_Description', N'Which date starts the timely-filing clock: service date, discharge date, claim received and so on.', N'SCHEMA', N'dbo', N'TABLE', N'payer', N'COLUMN', N'filing_clock_basis';
EXEC sp_addextendedproperty N'MS_Description', N'1 for the first row; higher for each change.', N'SCHEMA', N'dbo', N'TABLE', N'payer', N'COLUMN', N'version';
EXEC sp_addextendedproperty N'MS_Description', N'1 on the latest version. Counts use current rows only.', N'SCHEMA', N'dbo', N'TABLE', N'payer', N'COLUMN', N'is_current';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'payer', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'payer', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'payer', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'payer', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'payer', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'payer', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'payer', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'payer', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from.', N'SCHEMA', N'dbo', N'TABLE', N'payer', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'payer', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'A procedure code (CPT or HCPCS). Effective-dated.', N'SCHEMA', N'dbo', N'TABLE', N'cpt_code';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'cpt_code', N'COLUMN', N'cpt_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'Blank on the shared national row; set only on a tenant override row (for example a client''s own CARC classification or holidays). Lookups take the tenant row first, then the shared row.', N'SCHEMA', N'dbo', N'TABLE', N'cpt_code', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The 5-character code.', N'SCHEMA', N'dbo', N'TABLE', N'cpt_code', N'COLUMN', N'code';
EXEC sp_addextendedproperty N'MS_Description', N'CPT or HCPCS.', N'SCHEMA', N'dbo', N'TABLE', N'cpt_code', N'COLUMN', N'code_type';
EXEC sp_addextendedproperty N'MS_Description', N'Which year''s meaning applies.', N'SCHEMA', N'dbo', N'TABLE', N'cpt_code', N'COLUMN', N'effective_from';
EXEC sp_addextendedproperty N'MS_Description', N'End of validity. 9999-12-31 while open, so range joins need no NULL handling.', N'SCHEMA', N'dbo', N'TABLE', N'cpt_code', N'COLUMN', N'effective_to';
EXEC sp_addextendedproperty N'MS_Description', N'Our own words.', N'SCHEMA', N'dbo', N'TABLE', N'cpt_code', N'COLUMN', N'short_label';
EXEC sp_addextendedproperty N'MS_Description', N'E/M, radiology, lab, therapy, surgery, anesthesia, medicine, drug.', N'SCHEMA', N'dbo', N'TABLE', N'cpt_code', N'COLUMN', N'category';
EXEC sp_addextendedproperty N'MS_Description', N'Visit level 1 to 5.', N'SCHEMA', N'dbo', N'TABLE', N'cpt_code', N'COLUMN', N'em_level';
EXEC sp_addextendedproperty N'MS_Description', N'Needs a primary code.', N'SCHEMA', N'dbo', N'TABLE', N'cpt_code', N'COLUMN', N'is_add_on';
EXEC sp_addextendedproperty N'MS_Description', N'Units come from time.', N'SCHEMA', N'dbo', N'TABLE', N'cpt_code', N'COLUMN', N'is_timed';
EXEC sp_addextendedproperty N'MS_Description', N'CMS unit limit.', N'SCHEMA', N'dbo', N'TABLE', N'cpt_code', N'COLUMN', N'unit_limit_per_day';
EXEC sp_addextendedproperty N'MS_Description', N'Needs left or right.', N'SCHEMA', N'dbo', N'TABLE', N'cpt_code', N'COLUMN', N'laterality_required';
EXEC sp_addextendedproperty N'MS_Description', N'Provider productivity.', N'SCHEMA', N'dbo', N'TABLE', N'cpt_code', N'COLUMN', N'work_rvu';
EXEC sp_addextendedproperty N'MS_Description', N'Surgical bundling denials.', N'SCHEMA', N'dbo', N'TABLE', N'cpt_code', N'COLUMN', N'global_period_days';
EXEC sp_addextendedproperty N'MS_Description', N'Flagged placeholder for an unknown code.', N'SCHEMA', N'dbo', N'TABLE', N'cpt_code', N'COLUMN', N'is_unrecognized';
EXEC sp_addextendedproperty N'MS_Description', N'Lifecycle: 0 once retired.', N'SCHEMA', N'dbo', N'TABLE', N'cpt_code', N'COLUMN', N'is_active';
EXEC sp_addextendedproperty N'MS_Description', N'How the unit limit applies: per line, per day or per date of service.', N'SCHEMA', N'dbo', N'TABLE', N'cpt_code', N'COLUMN', N'unit_limit_basis';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'cpt_code', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'cpt_code', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'cpt_code', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'cpt_code', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from.', N'SCHEMA', N'dbo', N'TABLE', N'cpt_code', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'cpt_code', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'An ICD-10-CM diagnosis code. Effective-dated.', N'SCHEMA', N'dbo', N'TABLE', N'diagnosis_code';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'diagnosis_code', N'COLUMN', N'diagnosis_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'Blank on the shared national row; set only on a tenant override row (for example a client''s own CARC classification or holidays). Lookups take the tenant row first, then the shared row.', N'SCHEMA', N'dbo', N'TABLE', N'diagnosis_code', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'Saved without the dot.', N'SCHEMA', N'dbo', N'TABLE', N'diagnosis_code', N'COLUMN', N'icd10_code';
EXEC sp_addextendedproperty N'MS_Description', N'Updated each October 1.', N'SCHEMA', N'dbo', N'TABLE', N'diagnosis_code', N'COLUMN', N'effective_from';
EXEC sp_addextendedproperty N'MS_Description', N'End of validity. 9999-12-31 while open, so range joins need no NULL handling.', N'SCHEMA', N'dbo', N'TABLE', N'diagnosis_code', N'COLUMN', N'effective_to';
EXEC sp_addextendedproperty N'MS_Description', N'Public description.', N'SCHEMA', N'dbo', N'TABLE', N'diagnosis_code', N'COLUMN', N'description';
EXEC sp_addextendedproperty N'MS_Description', N'Chapter and block.', N'SCHEMA', N'dbo', N'TABLE', N'diagnosis_code', N'COLUMN', N'category';
EXEC sp_addextendedproperty N'MS_Description', N'Header codes cause rejections.', N'SCHEMA', N'dbo', N'TABLE', N'diagnosis_code', N'COLUMN', N'is_billable';
EXEC sp_addextendedproperty N'MS_Description', N'Condition analysis.', N'SCHEMA', N'dbo', N'TABLE', N'diagnosis_code', N'COLUMN', N'is_chronic';
EXEC sp_addextendedproperty N'MS_Description', N'Coding specificity.', N'SCHEMA', N'dbo', N'TABLE', N'diagnosis_code', N'COLUMN', N'is_unspecified';
EXEC sp_addextendedproperty N'MS_Description', N'Less specific parent.', N'SCHEMA', N'dbo', N'TABLE', N'diagnosis_code', N'COLUMN', N'parent_code';
EXEC sp_addextendedproperty N'MS_Description', N'Risk adjustment.', N'SCHEMA', N'dbo', N'TABLE', N'diagnosis_code', N'COLUMN', N'hcc_category';
EXEC sp_addextendedproperty N'MS_Description', N'Flagged placeholder.', N'SCHEMA', N'dbo', N'TABLE', N'diagnosis_code', N'COLUMN', N'is_unrecognized';
EXEC sp_addextendedproperty N'MS_Description', N'Lifecycle: 0 once retired.', N'SCHEMA', N'dbo', N'TABLE', N'diagnosis_code', N'COLUMN', N'is_active';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'diagnosis_code', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'diagnosis_code', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'diagnosis_code', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'diagnosis_code', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from.', N'SCHEMA', N'dbo', N'TABLE', N'diagnosis_code', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'diagnosis_code', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'A procedure modifier.', N'SCHEMA', N'dbo', N'TABLE', N'modifier';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'modifier', N'COLUMN', N'modifier_id';
EXEC sp_addextendedproperty N'MS_Description', N'Blank on the shared national row; set only on a tenant override row (for example a client''s own CARC classification or holidays). Lookups take the tenant row first, then the shared row.', N'SCHEMA', N'dbo', N'TABLE', N'modifier', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The 2-character modifier.', N'SCHEMA', N'dbo', N'TABLE', N'modifier', N'COLUMN', N'modifier_code';
EXEC sp_addextendedproperty N'MS_Description', N'Pricing, anatomical, telehealth, anesthesia, informational.', N'SCHEMA', N'dbo', N'TABLE', N'modifier', N'COLUMN', N'modifier_group';
EXEC sp_addextendedproperty N'MS_Description', N'Whether it changes payment.', N'SCHEMA', N'dbo', N'TABLE', N'modifier', N'COLUMN', N'affects_payment';
EXEC sp_addextendedproperty N'MS_Description', N'For example 50% for a reduced service.', N'SCHEMA', N'dbo', N'TABLE', N'modifier', N'COLUMN', N'payment_adjustment_pct';
EXEC sp_addextendedproperty N'MS_Description', N'Our own words.', N'SCHEMA', N'dbo', N'TABLE', N'modifier', N'COLUMN', N'short_label';
EXEC sp_addextendedproperty N'MS_Description', N'Lifecycle.', N'SCHEMA', N'dbo', N'TABLE', N'modifier', N'COLUMN', N'effective_from';
EXEC sp_addextendedproperty N'MS_Description', N'Lifecycle. 9999-12-31 while open, so range joins need no NULL handling.', N'SCHEMA', N'dbo', N'TABLE', N'modifier', N'COLUMN', N'effective_to';
EXEC sp_addextendedproperty N'MS_Description', N'Lifecycle: 0 once retired.', N'SCHEMA', N'dbo', N'TABLE', N'modifier', N'COLUMN', N'is_active';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'modifier', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'modifier', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'modifier', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'modifier', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from.', N'SCHEMA', N'dbo', N'TABLE', N'modifier', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'modifier', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'A CMS place-of-service code.', N'SCHEMA', N'dbo', N'TABLE', N'place_of_service';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'place_of_service', N'COLUMN', N'place_of_service_id';
EXEC sp_addextendedproperty N'MS_Description', N'Blank on the shared national row; set only on a tenant override row (for example a client''s own CARC classification or holidays). Lookups take the tenant row first, then the shared row.', N'SCHEMA', N'dbo', N'TABLE', N'place_of_service', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'CMS 2-digit code.', N'SCHEMA', N'dbo', N'TABLE', N'place_of_service', N'COLUMN', N'pos_code';
EXEC sp_addextendedproperty N'MS_Description', N'Public name.', N'SCHEMA', N'dbo', N'TABLE', N'place_of_service', N'COLUMN', N'pos_name';
EXEC sp_addextendedproperty N'MS_Description', N'Office, outpatient, inpatient, ER, home, telehealth.', N'SCHEMA', N'dbo', N'TABLE', N'place_of_service', N'COLUMN', N'setting';
EXEC sp_addextendedproperty N'MS_Description', N'Rate differences.', N'SCHEMA', N'dbo', N'TABLE', N'place_of_service', N'COLUMN', N'is_facility';
EXEC sp_addextendedproperty N'MS_Description', N'Rule differences.', N'SCHEMA', N'dbo', N'TABLE', N'place_of_service', N'COLUMN', N'is_telehealth';
EXEC sp_addextendedproperty N'MS_Description', N'Lifecycle.', N'SCHEMA', N'dbo', N'TABLE', N'place_of_service', N'COLUMN', N'effective_from';
EXEC sp_addextendedproperty N'MS_Description', N'Lifecycle. 9999-12-31 while open, so range joins need no NULL handling.', N'SCHEMA', N'dbo', N'TABLE', N'place_of_service', N'COLUMN', N'effective_to';
EXEC sp_addextendedproperty N'MS_Description', N'Lifecycle: 0 once retired.', N'SCHEMA', N'dbo', N'TABLE', N'place_of_service', N'COLUMN', N'is_active';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'place_of_service', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'place_of_service', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'place_of_service', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'place_of_service', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from.', N'SCHEMA', N'dbo', N'TABLE', N'place_of_service', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'place_of_service', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'A clinical specialty.', N'SCHEMA', N'dbo', N'TABLE', N'specialty';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'specialty', N'COLUMN', N'specialty_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'specialty', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'A short standard code.', N'SCHEMA', N'dbo', N'TABLE', N'specialty', N'COLUMN', N'specialty_code';
EXEC sp_addextendedproperty N'MS_Description', N'Display.', N'SCHEMA', N'dbo', N'TABLE', N'specialty', N'COLUMN', N'specialty_name';
EXEC sp_addextendedproperty N'MS_Description', N'Primary care, medical, surgical, behavioral, therapy, diagnostic.', N'SCHEMA', N'dbo', N'TABLE', N'specialty', N'COLUMN', N'specialty_group';
EXEC sp_addextendedproperty N'MS_Description', N'Benchmarks and HMO rules.', N'SCHEMA', N'dbo', N'TABLE', N'specialty', N'COLUMN', N'is_primary_care';
EXEC sp_addextendedproperty N'MS_Description', N'Medicare list.', N'SCHEMA', N'dbo', N'TABLE', N'specialty', N'COLUMN', N'cms_specialty_code';
EXEC sp_addextendedproperty N'MS_Description', N'Maps a taxonomy to the specialty.', N'SCHEMA', N'dbo', N'TABLE', N'specialty', N'COLUMN', N'taxonomy_prefix';
EXEC sp_addextendedproperty N'MS_Description', N'Lifecycle: 0 once retired.', N'SCHEMA', N'dbo', N'TABLE', N'specialty', N'COLUMN', N'is_active';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'specialty', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'specialty', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'specialty', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'specialty', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from.', N'SCHEMA', N'dbo', N'TABLE', N'specialty', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'specialty', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'A location where service happens.', N'SCHEMA', N'dbo', N'TABLE', N'facility';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of the record: the same on every version. The primary key is (facility_id, version). Every link from another table uses facility_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.', N'SCHEMA', N'dbo', N'TABLE', N'facility', N'COLUMN', N'facility_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'facility', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client''s location code.', N'SCHEMA', N'dbo', N'TABLE', N'facility', N'COLUMN', N'facility_number';
EXEC sp_addextendedproperty N'MS_Description', N'Display.', N'SCHEMA', N'dbo', N'TABLE', N'facility', N'COLUMN', N'facility_name';
EXEC sp_addextendedproperty N'MS_Description', N'Owning practice.', N'SCHEMA', N'dbo', N'TABLE', N'facility', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Office, clinic, hospital outpatient, surgery center, urgent care, lab, imaging, home, telehealth.', N'SCHEMA', N'dbo', N'TABLE', N'facility', N'COLUMN', N'facility_type';
EXEC sp_addextendedproperty N'MS_Description', N'Usual place-of-service code.', N'SCHEMA', N'dbo', N'TABLE', N'facility', N'COLUMN', N'default_place_of_service_id';
EXEC sp_addextendedproperty N'MS_Description', N'Service facility NPI.', N'SCHEMA', N'dbo', N'TABLE', N'facility', N'COLUMN', N'facility_npi';
EXEC sp_addextendedproperty N'MS_Description', N'State rules.', N'SCHEMA', N'dbo', N'TABLE', N'facility', N'COLUMN', N'state';
EXEC sp_addextendedproperty N'MS_Description', N'Site history.', N'SCHEMA', N'dbo', N'TABLE', N'facility', N'COLUMN', N'open_date';
EXEC sp_addextendedproperty N'MS_Description', N'Site history.', N'SCHEMA', N'dbo', N'TABLE', N'facility', N'COLUMN', N'close_date';
EXEC sp_addextendedproperty N'MS_Description', N'Location detail.', N'SCHEMA', N'dbo', N'TABLE', N'facility', N'COLUMN', N'zip';
EXEC sp_addextendedproperty N'MS_Description', N'Capacity.', N'SCHEMA', N'dbo', N'TABLE', N'facility', N'COLUMN', N'rooms';
EXEC sp_addextendedproperty N'MS_Description', N'Inherits the practice''s.', N'SCHEMA', N'dbo', N'TABLE', N'facility', N'COLUMN', N'time_zone';
EXEC sp_addextendedproperty N'MS_Description', N'Lifecycle: 0 once retired.', N'SCHEMA', N'dbo', N'TABLE', N'facility', N'COLUMN', N'is_active';
EXEC sp_addextendedproperty N'MS_Description', N'1 for the first row; higher for each change.', N'SCHEMA', N'dbo', N'TABLE', N'facility', N'COLUMN', N'version';
EXEC sp_addextendedproperty N'MS_Description', N'1 on the latest version. Counts use current rows only.', N'SCHEMA', N'dbo', N'TABLE', N'facility', N'COLUMN', N'is_current';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'facility', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'facility', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'facility', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'facility', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'facility', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'facility', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'facility', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'facility', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from.', N'SCHEMA', N'dbo', N'TABLE', N'facility', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'facility', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One fee schedule of a practice (standard, self-pay ...), per version.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of the record: the same on every version. The primary key is (fee_schedule_id, version). Every link from another table uses fee_schedule_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule', N'COLUMN', N'fee_schedule_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'Owning practice.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'standard, self_pay, hospital_based ...', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule', N'COLUMN', N'fee_schedule_name';
EXEC sp_addextendedproperty N'MS_Description', N'Location-specific schedule.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule', N'COLUMN', N'facility_id';
EXEC sp_addextendedproperty N'MS_Description', N'flat, or a multiple of Medicare.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule', N'COLUMN', N'fee_basis';
EXEC sp_addextendedproperty N'MS_Description', N'Used when none is named.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule', N'COLUMN', N'is_default';
EXEC sp_addextendedproperty N'MS_Description', N'1 when rebuilt from bill lines.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule', N'COLUMN', N'is_inferred';
EXEC sp_addextendedproperty N'MS_Description', N'Start.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule', N'COLUMN', N'effective_from';
EXEC sp_addextendedproperty N'MS_Description', N'9999-12-31 while open.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule', N'COLUMN', N'effective_to';
EXEC sp_addextendedproperty N'MS_Description', N'Lifecycle: 0 once retired.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule', N'COLUMN', N'is_active';
EXEC sp_addextendedproperty N'MS_Description', N'1 for the first row; higher for each change.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule', N'COLUMN', N'version';
EXEC sp_addextendedproperty N'MS_Description', N'1 on the latest version. Counts use current rows only.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule', N'COLUMN', N'is_current';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One fee per procedure (and modifier) on one fee schedule. Billed amount = units x this fee. Effective-dated.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule_line';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule_line', N'COLUMN', N'fee_schedule_line_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule_line', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The fee schedule (version) this line belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule_line', N'COLUMN', N'fee_schedule_id';
EXEC sp_addextendedproperty N'MS_Description', N'The procedure.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule_line', N'COLUMN', N'cpt_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'The charge per unit.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule_line', N'COLUMN', N'fee_per_unit';
EXEC sp_addextendedproperty N'MS_Description', N'When the fee took effect.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule_line', N'COLUMN', N'effective_from';
EXEC sp_addextendedproperty N'MS_Description', N'1 when estimated.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule_line', N'COLUMN', N'is_inferred';
EXEC sp_addextendedproperty N'MS_Description', N'Blank while open. 9999-12-31 while open, so range joins need no NULL handling.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule_line', N'COLUMN', N'effective_to';
EXEC sp_addextendedproperty N'MS_Description', N'For fees that depend on the modifier.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule_line', N'COLUMN', N'modifier_id';
EXEC sp_addextendedproperty N'MS_Description', N'Lifecycle: 0 once retired.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule_line', N'COLUMN', N'is_active';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule_line', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule_line', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule_line', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule_line', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule_line', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule_line', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule_line', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule_line', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule_line', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'fee_schedule_line', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'What a payer has agreed to allow per unit. Effective-dated.', N'SCHEMA', N'dbo', N'TABLE', N'contract_rate';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'contract_rate', N'COLUMN', N'contract_rate_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'contract_rate', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'Whose contract.', N'SCHEMA', N'dbo', N'TABLE', N'contract_rate', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Whose contract.', N'SCHEMA', N'dbo', N'TABLE', N'contract_rate', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'The contract this rate belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'contract_rate', N'COLUMN', N'payer_contract_id';
EXEC sp_addextendedproperty N'MS_Description', N'The procedure.', N'SCHEMA', N'dbo', N'TABLE', N'contract_rate', N'COLUMN', N'cpt_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'The allowed dollars per unit.', N'SCHEMA', N'dbo', N'TABLE', N'contract_rate', N'COLUMN', N'allowed_per_unit';
EXEC sp_addextendedproperty N'MS_Description', N'When the rate applies from.', N'SCHEMA', N'dbo', N'TABLE', N'contract_rate', N'COLUMN', N'effective_from';
EXEC sp_addextendedproperty N'MS_Description', N'Contract, payer_fee_schedule, medicare_schedule, learned: a learned estimate is never presented as the contract.', N'SCHEMA', N'dbo', N'TABLE', N'contract_rate', N'COLUMN', N'rate_source';
EXEC sp_addextendedproperty N'MS_Description', N'1 when we estimated the rate.', N'SCHEMA', N'dbo', N'TABLE', N'contract_rate', N'COLUMN', N'is_inferred';
EXEC sp_addextendedproperty N'MS_Description', N'Blank while open. 9999-12-31 while open, so range joins need no NULL handling.', N'SCHEMA', N'dbo', N'TABLE', N'contract_rate', N'COLUMN', N'effective_to';
EXEC sp_addextendedproperty N'MS_Description', N'Modifier-dependent rates.', N'SCHEMA', N'dbo', N'TABLE', N'contract_rate', N'COLUMN', N'modifier_id';
EXEC sp_addextendedproperty N'MS_Description', N'Facility or non-facility.', N'SCHEMA', N'dbo', N'TABLE', N'contract_rate', N'COLUMN', N'rate_setting';
EXEC sp_addextendedproperty N'MS_Description', N'Kept for loads that only send a number; the contract is payer_contract_id.', N'SCHEMA', N'dbo', N'TABLE', N'contract_rate', N'COLUMN', N'contract_number';
EXEC sp_addextendedproperty N'MS_Description', N'Fixed, percent of Medicare, percent of billed, per diem.', N'SCHEMA', N'dbo', N'TABLE', N'contract_rate', N'COLUMN', N'rate_basis';
EXEC sp_addextendedproperty N'MS_Description', N'Payer pays the lesser of billed and allowed.', N'SCHEMA', N'dbo', N'TABLE', N'contract_rate', N'COLUMN', N'lesser_of_billed';
EXEC sp_addextendedproperty N'MS_Description', N'For learned rates: reliability.', N'SCHEMA', N'dbo', N'TABLE', N'contract_rate', N'COLUMN', N'confidence';
EXEC sp_addextendedproperty N'MS_Description', N'For learned rates: lines used.', N'SCHEMA', N'dbo', N'TABLE', N'contract_rate', N'COLUMN', N'sample_size';
EXEC sp_addextendedproperty N'MS_Description', N'Plan-specific rates.', N'SCHEMA', N'dbo', N'TABLE', N'contract_rate', N'COLUMN', N'plan_type';
EXEC sp_addextendedproperty N'MS_Description', N'Provider-specific rates.', N'SCHEMA', N'dbo', N'TABLE', N'contract_rate', N'COLUMN', N'provider_id';
EXEC sp_addextendedproperty N'MS_Description', N'Specialty-specific rates.', N'SCHEMA', N'dbo', N'TABLE', N'contract_rate', N'COLUMN', N'specialty_id';
EXEC sp_addextendedproperty N'MS_Description', N'Multiple-procedure reduction.', N'SCHEMA', N'dbo', N'TABLE', N'contract_rate', N'COLUMN', N'multi_procedure_reduction_pct';
EXEC sp_addextendedproperty N'MS_Description', N'Dispute window.', N'SCHEMA', N'dbo', N'TABLE', N'contract_rate', N'COLUMN', N'dispute_days';
EXEC sp_addextendedproperty N'MS_Description', N'Lifecycle: 0 once retired.', N'SCHEMA', N'dbo', N'TABLE', N'contract_rate', N'COLUMN', N'is_active';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'contract_rate', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'contract_rate', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'contract_rate', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'contract_rate', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'contract_rate', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'contract_rate', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'contract_rate', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'contract_rate', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from.', N'SCHEMA', N'dbo', N'TABLE', N'contract_rate', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'contract_rate', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'A payer adjustment or denial reason code (CARC). Effective-dated.', N'SCHEMA', N'dbo', N'TABLE', N'adjustment_reason';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'adjustment_reason', N'COLUMN', N'adjustment_reason_id';
EXEC sp_addextendedproperty N'MS_Description', N'Blank on the shared national row; set only on a tenant override row (for example a client''s own CARC classification or holidays). Lookups take the tenant row first, then the shared row.', N'SCHEMA', N'dbo', N'TABLE', N'adjustment_reason', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The reason code.', N'SCHEMA', N'dbo', N'TABLE', N'adjustment_reason', N'COLUMN', N'carc_code';
EXEC sp_addextendedproperty N'MS_Description', N'The list changes during the year.', N'SCHEMA', N'dbo', N'TABLE', N'adjustment_reason', N'COLUMN', N'effective_from';
EXEC sp_addextendedproperty N'MS_Description', N'End of validity. 9999-12-31 while open, so range joins need no NULL handling.', N'SCHEMA', N'dbo', N'TABLE', N'adjustment_reason', N'COLUMN', N'effective_to';
EXEC sp_addextendedproperty N'MS_Description', N'Denial, contractual, patient_responsibility, other_adjustment, informational. A PR group always means patient responsibility.', N'SCHEMA', N'dbo', N'TABLE', N'adjustment_reason', N'COLUMN', N'reason_class';
EXEC sp_addextendedproperty N'MS_Description', N'Our own words.', N'SCHEMA', N'dbo', N'TABLE', N'adjustment_reason', N'COLUMN', N'short_label';
EXEC sp_addextendedproperty N'MS_Description', N'Eligibility, authorization, coding, documentation, timely filing, duplicate, coordination of benefits, bundling, technical.', N'SCHEMA', N'dbo', N'TABLE', N'adjustment_reason', N'COLUMN', N'reason_category';
EXEC sp_addextendedproperty N'MS_Description', N'Fix and resubmit, appeal, write-off review, bill patient, informational. A proposal only.', N'SCHEMA', N'dbo', N'TABLE', N'adjustment_reason', N'COLUMN', N'suggested_action';
EXEC sp_addextendedproperty N'MS_Description', N'Billing, coding, front desk, provider, patient.', N'SCHEMA', N'dbo', N'TABLE', N'adjustment_reason', N'COLUMN', N'owner_role';
EXEC sp_addextendedproperty N'MS_Description', N'Which journey stage could have caught it.', N'SCHEMA', N'dbo', N'TABLE', N'adjustment_reason', N'COLUMN', N'upstream_stage';
EXEC sp_addextendedproperty N'MS_Description', N'Default.', N'SCHEMA', N'dbo', N'TABLE', N'adjustment_reason', N'COLUMN', N'is_appealable';
EXEC sp_addextendedproperty N'MS_Description', N'Default.', N'SCHEMA', N'dbo', N'TABLE', N'adjustment_reason', N'COLUMN', N'is_technical';
EXEC sp_addextendedproperty N'MS_Description', N'Default.', N'SCHEMA', N'dbo', N'TABLE', N'adjustment_reason', N'COLUMN', N'is_preventable_default';
EXEC sp_addextendedproperty N'MS_Description', N'Usual group code.', N'SCHEMA', N'dbo', N'TABLE', N'adjustment_reason', N'COLUMN', N'typical_group';
EXEC sp_addextendedproperty N'MS_Description', N'Flagged placeholder for an unknown code.', N'SCHEMA', N'dbo', N'TABLE', N'adjustment_reason', N'COLUMN', N'is_unrecognized';
EXEC sp_addextendedproperty N'MS_Description', N'Lifecycle: 0 once retired.', N'SCHEMA', N'dbo', N'TABLE', N'adjustment_reason', N'COLUMN', N'is_active';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'adjustment_reason', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'adjustment_reason', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'adjustment_reason', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'adjustment_reason', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from.', N'SCHEMA', N'dbo', N'TABLE', N'adjustment_reason', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'adjustment_reason', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'A remittance remark (RARC). Effective-dated.', N'SCHEMA', N'dbo', N'TABLE', N'remark_code';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'remark_code', N'COLUMN', N'remark_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'Blank on the shared national row; set only on a tenant override row (for example a client''s own CARC classification or holidays). Lookups take the tenant row first, then the shared row.', N'SCHEMA', N'dbo', N'TABLE', N'remark_code', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The remark code.', N'SCHEMA', N'dbo', N'TABLE', N'remark_code', N'COLUMN', N'rarc_code';
EXEC sp_addextendedproperty N'MS_Description', N'The list is updated regularly.', N'SCHEMA', N'dbo', N'TABLE', N'remark_code', N'COLUMN', N'effective_from';
EXEC sp_addextendedproperty N'MS_Description', N'End of validity. 9999-12-31 while open, so range joins need no NULL handling.', N'SCHEMA', N'dbo', N'TABLE', N'remark_code', N'COLUMN', N'effective_to';
EXEC sp_addextendedproperty N'MS_Description', N'Which code list.', N'SCHEMA', N'dbo', N'TABLE', N'remark_code', N'COLUMN', N'code_qualifier';
EXEC sp_addextendedproperty N'MS_Description', N'Our own words.', N'SCHEMA', N'dbo', N'TABLE', N'remark_code', N'COLUMN', N'short_label';
EXEC sp_addextendedproperty N'MS_Description', N'Alert, informational, supplemental, action required.', N'SCHEMA', N'dbo', N'TABLE', N'remark_code', N'COLUMN', N'remark_type';
EXEC sp_addextendedproperty N'MS_Description', N'Documentation needed, correct and resubmit, appeal, none. A proposal only.', N'SCHEMA', N'dbo', N'TABLE', N'remark_code', N'COLUMN', N'suggests_action';
EXEC sp_addextendedproperty N'MS_Description', N'Which records the remark implies.', N'SCHEMA', N'dbo', N'TABLE', N'remark_code', N'COLUMN', N'documents_needed';
EXEC sp_addextendedproperty N'MS_Description', N'Common pairing with a reason.', N'SCHEMA', N'dbo', N'TABLE', N'remark_code', N'COLUMN', N'related_reason_code';
EXEC sp_addextendedproperty N'MS_Description', N'Flagged placeholder.', N'SCHEMA', N'dbo', N'TABLE', N'remark_code', N'COLUMN', N'is_unrecognized';
EXEC sp_addextendedproperty N'MS_Description', N'Lifecycle: 0 once retired.', N'SCHEMA', N'dbo', N'TABLE', N'remark_code', N'COLUMN', N'is_active';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'remark_code', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'remark_code', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'remark_code', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'remark_code', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from.', N'SCHEMA', N'dbo', N'TABLE', N'remark_code', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'remark_code', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One row per setting, effective-dated. Tenant-wide default overridable per practice.', N'SCHEMA', N'dbo', N'TABLE', N'practice_settings';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'practice_settings', N'COLUMN', N'practice_settings_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'practice_settings', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'Blank means the client-wide default.', N'SCHEMA', N'dbo', N'TABLE', N'practice_settings', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'The setting.', N'SCHEMA', N'dbo', N'TABLE', N'practice_settings', N'COLUMN', N'setting_key';
EXEC sp_addextendedproperty N'MS_Description', N'Its value.', N'SCHEMA', N'dbo', N'TABLE', N'practice_settings', N'COLUMN', N'setting_value';
EXEC sp_addextendedproperty N'MS_Description', N'Number, days, percent, text, list.', N'SCHEMA', N'dbo', N'TABLE', N'practice_settings', N'COLUMN', N'value_type';
EXEC sp_addextendedproperty N'MS_Description', N'History of changes.', N'SCHEMA', N'dbo', N'TABLE', N'practice_settings', N'COLUMN', N'effective_from';
EXEC sp_addextendedproperty N'MS_Description', N'Blank while current. 9999-12-31 while open, so range joins need no NULL handling.', N'SCHEMA', N'dbo', N'TABLE', N'practice_settings', N'COLUMN', N'effective_to';
EXEC sp_addextendedproperty N'MS_Description', N'Who set it.', N'SCHEMA', N'dbo', N'TABLE', N'practice_settings', N'COLUMN', N'set_by_role';
EXEC sp_addextendedproperty N'MS_Description', N'Pseudonymous approver for changes that affect reporting. Holds the staff_id of the pseudonymous person.', N'SCHEMA', N'dbo', N'TABLE', N'practice_settings', N'COLUMN', N'approved_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'Lifecycle: 0 once retired.', N'SCHEMA', N'dbo', N'TABLE', N'practice_settings', N'COLUMN', N'is_active';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'practice_settings', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'practice_settings', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'practice_settings', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'practice_settings', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'practice_settings', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'practice_settings', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'practice_settings', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'practice_settings', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from.', N'SCHEMA', N'dbo', N'TABLE', N'practice_settings', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'practice_settings', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One version of one rule: an authorization requirement, a bundling pair, a medical-necessity pair, a unit limit, a payer claim edit, a learned denial pattern or an agent detection rule, with the dates it applied.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of the record: the same on every version. The primary key is (payer_rule_id, version). Every link from another table uses payer_rule_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'payer_rule_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The payer''s own policy or rule number, when one exists. Restricted.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'payer_rule_number';
EXEC sp_addextendedproperty N'MS_Description', N'Stable key shared by every version of the rule. Decision details and findings quote it as rule_code.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'rule_code';
EXEC sp_addextendedproperty N'MS_Description', N'Kind of rule: authorization, bundling, medical_necessity, unit_limit, modifier, timely_filing, attachment, payer_edit, enrollment, multiple_procedure, learned_denial, detection.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'rule_family';
EXEC sp_addextendedproperty N'MS_Description', N'What happens when the rule applies: require_auth, deny_pair, require_modifier, require_diagnosis, cap_units, require_attachment, flag_denial_risk, detect.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'rule_action';
EXEC sp_addextendedproperty N'MS_Description', N'Where the rule comes from, as a code: payer_manual, contract, ncci, mue, lcd, learned, practice, scout. Never free text.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'rule_source_code';
EXEC sp_addextendedproperty N'MS_Description', N'Document, section or table number inside that source, as a code, so the rule can be checked again.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'rule_source_ref';
EXEC sp_addextendedproperty N'MS_Description', N'Payer the rule applies to. Blank means every payer (CMS pairs, detection rules).', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'Plan type the rule applies to (HMO, PPO, Medicare Advantage ...).', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'plan_type';
EXEC sp_addextendedproperty N'MS_Description', N'Place of service the rule applies to.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'place_of_service_id';
EXEC sp_addextendedproperty N'MS_Description', N'Set when the rule row is a practice-specific switch or override. Blank means the rule is for all practices.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Procedure code the rule is about, or the first code of a range.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'cpt_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'Last code of a range, when the payer lists a range.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'cpt_code_to_id';
EXEC sp_addextendedproperty N'MS_Description', N'Second code of a bundling pair.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'paired_cpt_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'Modifier that is required, accepted or that lifts a bundling pair.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'modifier_id';
EXEC sp_addextendedproperty N'MS_Description', N'Diagnosis in a medical-necessity pair.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'diagnosis_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'Denial reason (CARC) of a learned denial pattern.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'adjustment_reason_id';
EXEC sp_addextendedproperty N'MS_Description', N'Claim field a payer edit looks at (a code such as rendering_npi).', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'edit_field_code';
EXEC sp_addextendedproperty N'MS_Description', N'What the payer wants in that field: required, forbidden, must_match.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'requirement_code';
EXEC sp_addextendedproperty N'MS_Description', N'Most units allowed for the code.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'unit_limit';
EXEC sp_addextendedproperty N'MS_Description', N'Per line, per day or per date of service. Same values as cpt_code.unit_limit_basis.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'unit_limit_basis';
EXEC sp_addextendedproperty N'MS_Description', N'Learned rules: claim lines seen for this payer, code and reason when the pattern was learned. Rates are computed, not stored.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'evidence_claim_count';
EXEC sp_addextendedproperty N'MS_Description', N'Learned rules: how many of those lines were denied with this reason.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'evidence_denied_count';
EXEC sp_addextendedproperty N'MS_Description', N'Learned rules: billed amount of the denied lines; ranks the rule by money.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'evidence_denied_amount';
EXEC sp_addextendedproperty N'MS_Description', N'Learned rules: first date of service in the evidence window.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'evidence_from_date';
EXEC sp_addextendedproperty N'MS_Description', N'Learned rules: last date of service in the evidence window.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'evidence_to_date';
EXEC sp_addextendedproperty N'MS_Description', N'Team that fixes a failure of this rule: registration, authorization, coding, billing.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'owner_role';
EXEC sp_addextendedproperty N'MS_Description', N'Block or warn when the rule fails.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'severity';
EXEC sp_addextendedproperty N'MS_Description', N'Switch. A disabled rule is skipped and the skip is logged.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'is_enabled';
EXEC sp_addextendedproperty N'MS_Description', N'1 for a placeholder rule used for demos or tests; kept out of real results.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'is_synthetic';
EXEC sp_addextendedproperty N'MS_Description', N'proposed, approved, rejected or retired. Only approved rows take effect.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'approval_status';
EXEC sp_addextendedproperty N'MS_Description', N'Pseudonymous approver of a learned or practice rule. Never a name.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'approved_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'Date of approval.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'approved_date';
EXEC sp_addextendedproperty N'MS_Description', N'Last date someone checked the rule against its source. Old confirmation lowers trust.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'last_confirmed_date';
EXEC sp_addextendedproperty N'MS_Description', N'First date of service the rule version applies to.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'effective_from';
EXEC sp_addextendedproperty N'MS_Description', N'Last date of service it applies to. Blank while open. 9999-12-31 while open, so range joins need no NULL handling.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'effective_to';
EXEC sp_addextendedproperty N'MS_Description', N'Why the rule ended: superseded, payer_changed, wrong, low_hit_rate.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'retire_reason_code';
EXEC sp_addextendedproperty N'MS_Description', N'1 for the first row; higher for each change.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'version';
EXEC sp_addextendedproperty N'MS_Description', N'1 on the latest version. Counts use current rows only.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'is_current';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'previous_payer_rule_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'payer_rule', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One date, with whether it is a business day or a holiday.', N'SCHEMA', N'dbo', N'TABLE', N'calendar';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'calendar', N'COLUMN', N'calendar_id';
EXEC sp_addextendedproperty N'MS_Description', N'Blank on the shared national row; set only on a tenant override row (for example a client''s own CARC classification or holidays). Lookups take the tenant row first, then the shared row.', N'SCHEMA', N'dbo', N'TABLE', N'calendar', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'Set when a practice closes on a day the tenant does not.', N'SCHEMA', N'dbo', N'TABLE', N'calendar', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'The date.', N'SCHEMA', N'dbo', N'TABLE', N'calendar', N'COLUMN', N'calendar_date';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the practice and payers work that day.', N'SCHEMA', N'dbo', N'TABLE', N'calendar', N'COLUMN', N'is_business_day';
EXEC sp_addextendedproperty N'MS_Description', N'1 on a holiday.', N'SCHEMA', N'dbo', N'TABLE', N'calendar', N'COLUMN', N'is_holiday';
EXEC sp_addextendedproperty N'MS_Description', N'Code of the holiday (NEW_YEAR, THANKSGIVING).', N'SCHEMA', N'dbo', N'TABLE', N'calendar', N'COLUMN', N'holiday_code';
EXEC sp_addextendedproperty N'MS_Description', N'Running count of business days, so lag in business days is one subtraction.', N'SCHEMA', N'dbo', N'TABLE', N'calendar', N'COLUMN', N'business_day_number';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'calendar', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'calendar', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'calendar', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'calendar', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'calendar', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'calendar', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One ID a payer is known by in one channel (claims, remittances, eligibility, a given clearinghouse).', N'SCHEMA', N'dbo', N'TABLE', N'payer_identifier';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'payer_identifier', N'COLUMN', N'payer_identifier_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'payer_identifier', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The payer.', N'SCHEMA', N'dbo', N'TABLE', N'payer_identifier', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'The payer ID as used in that channel.', N'SCHEMA', N'dbo', N'TABLE', N'payer_identifier', N'COLUMN', N'identifier_value';
EXEC sp_addextendedproperty N'MS_Description', N'claim_837, era_835, eligibility_270, status_276, auth_278, attachment_275, portal.', N'SCHEMA', N'dbo', N'TABLE', N'payer_identifier', N'COLUMN', N'identifier_type';
EXEC sp_addextendedproperty N'MS_Description', N'Clearinghouse that uses this ID. Blank: all.', N'SCHEMA', N'dbo', N'TABLE', N'payer_identifier', N'COLUMN', N'clearinghouse_code';
EXEC sp_addextendedproperty N'MS_Description', N'First day the ID is valid.', N'SCHEMA', N'dbo', N'TABLE', N'payer_identifier', N'COLUMN', N'effective_from';
EXEC sp_addextendedproperty N'MS_Description', N'Last day. 9999-12-31 while open.', N'SCHEMA', N'dbo', N'TABLE', N'payer_identifier', N'COLUMN', N'effective_to';
EXEC sp_addextendedproperty N'MS_Description', N'Lifecycle: 0 once retired.', N'SCHEMA', N'dbo', N'TABLE', N'payer_identifier', N'COLUMN', N'is_active';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'payer_identifier', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'payer_identifier', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'payer_identifier', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'payer_identifier', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'payer_identifier', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'payer_identifier', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'payer_identifier', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'payer_identifier', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'payer_identifier', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'payer_identifier', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One plan or product a payer sells (an HMO, a Medicare Advantage plan ...).', N'SCHEMA', N'dbo', N'TABLE', N'payer_plan';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'payer_plan', N'COLUMN', N'payer_plan_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'payer_plan', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The payer.', N'SCHEMA', N'dbo', N'TABLE', N'payer_plan', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'The payer''s plan or product code.', N'SCHEMA', N'dbo', N'TABLE', N'payer_plan', N'COLUMN', N'plan_code';
EXEC sp_addextendedproperty N'MS_Description', N'Display.', N'SCHEMA', N'dbo', N'TABLE', N'payer_plan', N'COLUMN', N'plan_name';
EXEC sp_addextendedproperty N'MS_Description', N'Same values as coverage.plan_type.', N'SCHEMA', N'dbo', N'TABLE', N'payer_plan', N'COLUMN', N'plan_type';
EXEC sp_addextendedproperty N'MS_Description', N'commercial, medicare_advantage, medicaid_managed, exchange.', N'SCHEMA', N'dbo', N'TABLE', N'payer_plan', N'COLUMN', N'product_line';
EXEC sp_addextendedproperty N'MS_Description', N'Plan needs a referral.', N'SCHEMA', N'dbo', N'TABLE', N'payer_plan', N'COLUMN', N'requires_referral';
EXEC sp_addextendedproperty N'MS_Description', N'Overrides payer.filing_days when set.', N'SCHEMA', N'dbo', N'TABLE', N'payer_plan', N'COLUMN', N'filing_days';
EXEC sp_addextendedproperty N'MS_Description', N'Overrides payer.appeal_days when set.', N'SCHEMA', N'dbo', N'TABLE', N'payer_plan', N'COLUMN', N'appeal_days';
EXEC sp_addextendedproperty N'MS_Description', N'State the plan is sold in.', N'SCHEMA', N'dbo', N'TABLE', N'payer_plan', N'COLUMN', N'state';
EXEC sp_addextendedproperty N'MS_Description', N'First day.', N'SCHEMA', N'dbo', N'TABLE', N'payer_plan', N'COLUMN', N'effective_from';
EXEC sp_addextendedproperty N'MS_Description', N'9999-12-31 while open.', N'SCHEMA', N'dbo', N'TABLE', N'payer_plan', N'COLUMN', N'effective_to';
EXEC sp_addextendedproperty N'MS_Description', N'Lifecycle: 0 once retired.', N'SCHEMA', N'dbo', N'TABLE', N'payer_plan', N'COLUMN', N'is_active';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'payer_plan', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'payer_plan', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'payer_plan', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'payer_plan', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'payer_plan', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'payer_plan', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'payer_plan', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'payer_plan', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'payer_plan', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'payer_plan', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One contract between a practice and a payer (or plan), per version.', N'SCHEMA', N'dbo', N'TABLE', N'payer_contract';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of the record: the same on every version. The primary key is (payer_contract_id, version). Every link from another table uses payer_contract_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.', N'SCHEMA', N'dbo', N'TABLE', N'payer_contract', N'COLUMN', N'payer_contract_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'payer_contract', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'Contracting practice.', N'SCHEMA', N'dbo', N'TABLE', N'payer_contract', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'The payer.', N'SCHEMA', N'dbo', N'TABLE', N'payer_contract', N'COLUMN', N'payer_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the contract covers one plan only.', N'SCHEMA', N'dbo', N'TABLE', N'payer_contract', N'COLUMN', N'payer_plan_id';
EXEC sp_addextendedproperty N'MS_Description', N'Contract reference.', N'SCHEMA', N'dbo', N'TABLE', N'payer_contract', N'COLUMN', N'contract_number';
EXEC sp_addextendedproperty N'MS_Description', N'draft, active, expired, terminated.', N'SCHEMA', N'dbo', N'TABLE', N'payer_contract', N'COLUMN', N'contract_status';
EXEC sp_addextendedproperty N'MS_Description', N'Start.', N'SCHEMA', N'dbo', N'TABLE', N'payer_contract', N'COLUMN', N'effective_from';
EXEC sp_addextendedproperty N'MS_Description', N'9999-12-31 while open.', N'SCHEMA', N'dbo', N'TABLE', N'payer_contract', N'COLUMN', N'effective_to';
EXEC sp_addextendedproperty N'MS_Description', N'Overrides payer.filing_days.', N'SCHEMA', N'dbo', N'TABLE', N'payer_contract', N'COLUMN', N'filing_days';
EXEC sp_addextendedproperty N'MS_Description', N'Overrides payer.corrected_claim_days.', N'SCHEMA', N'dbo', N'TABLE', N'payer_contract', N'COLUMN', N'corrected_claim_days';
EXEC sp_addextendedproperty N'MS_Description', N'Overrides payer.appeal_days.', N'SCHEMA', N'dbo', N'TABLE', N'payer_contract', N'COLUMN', N'appeal_days';
EXEC sp_addextendedproperty N'MS_Description', N'Payer pays the lesser of billed and allowed.', N'SCHEMA', N'dbo', N'TABLE', N'payer_contract', N'COLUMN', N'lesser_of_billed';
EXEC sp_addextendedproperty N'MS_Description', N'fixed, pct_of_medicare, pct_of_billed, per_diem.', N'SCHEMA', N'dbo', N'TABLE', N'payer_contract', N'COLUMN', N'default_rate_basis';
EXEC sp_addextendedproperty N'MS_Description', N'For pct_of_medicare contracts.', N'SCHEMA', N'dbo', N'TABLE', N'payer_contract', N'COLUMN', N'default_pct_of_medicare';
EXEC sp_addextendedproperty N'MS_Description', N'Annual increase.', N'SCHEMA', N'dbo', N'TABLE', N'payer_contract', N'COLUMN', N'escalator_pct';
EXEC sp_addextendedproperty N'MS_Description', N'Notice needed before renewal.', N'SCHEMA', N'dbo', N'TABLE', N'payer_contract', N'COLUMN', N'renewal_notice_days';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the signed contract file.', N'SCHEMA', N'dbo', N'TABLE', N'payer_contract', N'COLUMN', N'document_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 for the first row; higher for each change.', N'SCHEMA', N'dbo', N'TABLE', N'payer_contract', N'COLUMN', N'version';
EXEC sp_addextendedproperty N'MS_Description', N'1 on the latest version. Counts use current rows only.', N'SCHEMA', N'dbo', N'TABLE', N'payer_contract', N'COLUMN', N'is_current';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was created in the source system (EHR, PM, clearinghouse), not when we loaded it.', N'SCHEMA', N'dbo', N'TABLE', N'payer_contract', N'COLUMN', N'created_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who created it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'payer_contract', N'COLUMN', N'created_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'When the record was last changed in the source system. On versioned tables, the change that produced this version.', N'SCHEMA', N'dbo', N'TABLE', N'payer_contract', N'COLUMN', N'modified_at';
EXEC sp_addextendedproperty N'MS_Description', N'Who last changed it in the source system (pseudonymous staff_id).', N'SCHEMA', N'dbo', N'TABLE', N'payer_contract', N'COLUMN', N'modified_by_staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'payer_contract', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'payer_contract', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'payer_contract', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'payer_contract', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'payer_contract', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'payer_contract', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One X12 claim status category code (STC01-1) or status code (STC01-2), effective-dated.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_code';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_code', N'COLUMN', N'claim_status_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'Blank on the shared national row; set only on a tenant override row.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_code', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'category (STC01-1) or status (STC01-2).', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_code', N'COLUMN', N'code_set';
EXEC sp_addextendedproperty N'MS_Description', N'The code (A0-A8, F0-F4, P0-P5, R0-R16, E0-E4 ... or a status number).', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_code', N'COLUMN', N'code';
EXEC sp_addextendedproperty N'MS_Description', N'Short description.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_code', N'COLUMN', N'short_label';
EXEC sp_addextendedproperty N'MS_Description', N'acknowledged, rejected, pended, finalized, request, error.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_code', N'COLUMN', N'status_group';
EXEC sp_addextendedproperty N'MS_Description', N'1 for A3, A6, A7, A8 and similar.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_code', N'COLUMN', N'is_rejection';
EXEC sp_addextendedproperty N'MS_Description', N'First day.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_code', N'COLUMN', N'effective_from';
EXEC sp_addextendedproperty N'MS_Description', N'9999-12-31 while open.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_code', N'COLUMN', N'effective_to';
EXEC sp_addextendedproperty N'MS_Description', N'1 on a placeholder for a code seen but not in the list.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_code', N'COLUMN', N'is_unrecognized';
EXEC sp_addextendedproperty N'MS_Description', N'Lifecycle.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_code', N'COLUMN', N'is_active';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_code', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_code', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_code', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_code', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_code', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'claim_status_code', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One National Drug Code (11-digit, 5-4-2), with its HCPCS crosswalk and billing unit.', N'SCHEMA', N'dbo', N'TABLE', N'ndc_code';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'ndc_code', N'COLUMN', N'ndc_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'Blank on the shared national row; set only on a tenant override row.', N'SCHEMA', N'dbo', N'TABLE', N'ndc_code', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'NDC in 5-4-2 format without dashes.', N'SCHEMA', N'dbo', N'TABLE', N'ndc_code', N'COLUMN', N'ndc_11';
EXEC sp_addextendedproperty N'MS_Description', N'Drug name and strength.', N'SCHEMA', N'dbo', N'TABLE', N'ndc_code', N'COLUMN', N'product_label';
EXEC sp_addextendedproperty N'MS_Description', N'HCPCS code it bills under.', N'SCHEMA', N'dbo', N'TABLE', N'ndc_code', N'COLUMN', N'hcpcs_cpt_code_id';
EXEC sp_addextendedproperty N'MS_Description', N'UN, ML, GR, F2.', N'SCHEMA', N'dbo', N'TABLE', N'ndc_code', N'COLUMN', N'billing_unit';
EXEC sp_addextendedproperty N'MS_Description', N'Units in the package.', N'SCHEMA', N'dbo', N'TABLE', N'ndc_code', N'COLUMN', N'package_quantity';
EXEC sp_addextendedproperty N'MS_Description', N'HCPCS billing units per package (crosswalk bill units).', N'SCHEMA', N'dbo', N'TABLE', N'ndc_code', N'COLUMN', N'hcpcs_units_per_package';
EXEC sp_addextendedproperty N'MS_Description', N'First day.', N'SCHEMA', N'dbo', N'TABLE', N'ndc_code', N'COLUMN', N'effective_from';
EXEC sp_addextendedproperty N'MS_Description', N'9999-12-31 while open.', N'SCHEMA', N'dbo', N'TABLE', N'ndc_code', N'COLUMN', N'effective_to';
EXEC sp_addextendedproperty N'MS_Description', N'1 on a placeholder for a code seen but not in the list.', N'SCHEMA', N'dbo', N'TABLE', N'ndc_code', N'COLUMN', N'is_unrecognized';
EXEC sp_addextendedproperty N'MS_Description', N'Lifecycle.', N'SCHEMA', N'dbo', N'TABLE', N'ndc_code', N'COLUMN', N'is_active';
EXEC sp_addextendedproperty N'MS_Description', N'The load that wrote the row: lineage, and rollback of a bad load.', N'SCHEMA', N'dbo', N'TABLE', N'ndc_code', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the source record''s fields; an unchanged hash means no new version on the next load.', N'SCHEMA', N'dbo', N'TABLE', N'ndc_code', N'COLUMN', N'source_record_hash';
EXEC sp_addextendedproperty N'MS_Description', N'1 when the record was deleted in the source system. The row is kept and left out of counts.', N'SCHEMA', N'dbo', N'TABLE', N'ndc_code', N'COLUMN', N'is_source_deleted';
EXEC sp_addextendedproperty N'MS_Description', N'When the deletion was detected.', N'SCHEMA', N'dbo', N'TABLE', N'ndc_code', N'COLUMN', N'source_deleted_at';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'ndc_code', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'ndc_code', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One client organisation.', N'SCHEMA', N'dbo', N'TABLE', N'tenant';
EXEC sp_addextendedproperty N'MS_Description', N'Identity of the client organisation. Every table''s tenant_id holds this value.', N'SCHEMA', N'dbo', N'TABLE', N'tenant', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'Short code for the client.', N'SCHEMA', N'dbo', N'TABLE', N'tenant', N'COLUMN', N'tenant_code';
EXEC sp_addextendedproperty N'MS_Description', N'Display.', N'SCHEMA', N'dbo', N'TABLE', N'tenant', N'COLUMN', N'tenant_name';
EXEC sp_addextendedproperty N'MS_Description', N'onboarding, active, suspended, offboarded.', N'SCHEMA', N'dbo', N'TABLE', N'tenant', N'COLUMN', N'tenant_status';
EXEC sp_addextendedproperty N'MS_Description', N'Date the business associate agreement was signed. No data loads before it.', N'SCHEMA', N'dbo', N'TABLE', N'tenant', N'COLUMN', N'baa_signed_date';
EXEC sp_addextendedproperty N'MS_Description', N'Name of the key-vault secret holding the per-client hashing salt. Never the salt itself. The salt keeps patients from matching across clients, by design.', N'SCHEMA', N'dbo', N'TABLE', N'tenant', N'COLUMN', N'salt_key_ref';
EXEC sp_addextendedproperty N'MS_Description', N'Where the client''s data is stored.', N'SCHEMA', N'dbo', N'TABLE', N'tenant', N'COLUMN', N'data_region';
EXEC sp_addextendedproperty N'MS_Description', N'First production load.', N'SCHEMA', N'dbo', N'TABLE', N'tenant', N'COLUMN', N'go_live_date';
EXEC sp_addextendedproperty N'MS_Description', N'How long rows are kept after offboarding rules apply.', N'SCHEMA', N'dbo', N'TABLE', N'tenant', N'COLUMN', N'retention_years';
EXEC sp_addextendedproperty N'MS_Description', N'Date the client left; deletion clock starts.', N'SCHEMA', N'dbo', N'TABLE', N'tenant', N'COLUMN', N'offboard_date';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'tenant', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'tenant', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One row per feed a client provides (or does not): which canonical table it fills, from where, how often, how complete.', N'SCHEMA', N'dbo', N'TABLE', N'data_feed';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of the record: the same on every version. The primary key is (data_feed_id, version). Every link from another table uses data_feed_id alone and takes the row with is_current = 1; an as-of view takes the highest version with modified_at (or loaded_at) on or before the date.', N'SCHEMA', N'dbo', N'TABLE', N'data_feed', N'COLUMN', N'data_feed_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'data_feed', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The canonical table the feed fills.', N'SCHEMA', N'dbo', N'TABLE', N'data_feed', N'COLUMN', N'table_name';
EXEC sp_addextendedproperty N'MS_Description', N'Plain name, e.g. ''PM claims export''.', N'SCHEMA', N'dbo', N'TABLE', N'data_feed', N'COLUMN', N'feed_name';
EXEC sp_addextendedproperty N'MS_Description', N'Scheduler, ehr, pm, clearinghouse, payer_portal, manual, public_list.', N'SCHEMA', N'dbo', N'TABLE', N'data_feed', N'COLUMN', N'source_system';
EXEC sp_addextendedproperty N'MS_Description', N'Active, paused, failed, not_provided.', N'SCHEMA', N'dbo', N'TABLE', N'data_feed', N'COLUMN', N'feed_status';
EXEC sp_addextendedproperty N'MS_Description', N'0 = primary source; 1 and up = the fallback step in use (see each table''s ladder).', N'SCHEMA', N'dbo', N'TABLE', N'data_feed', N'COLUMN', N'fallback_level';
EXEC sp_addextendedproperty N'MS_Description', N'Blank = whole client.', N'SCHEMA', N'dbo', N'TABLE', N'data_feed', N'COLUMN', N'practice_id';
EXEC sp_addextendedproperty N'MS_Description', N'Api, hl7, file_drop, database_view, upload, public.', N'SCHEMA', N'dbo', N'TABLE', N'data_feed', N'COLUMN', N'source_kind';
EXEC sp_addextendedproperty N'MS_Description', N'Realtime, hourly, daily, weekly, monthly, one_time.', N'SCHEMA', N'dbo', N'TABLE', N'data_feed', N'COLUMN', N'load_frequency';
EXEC sp_addextendedproperty N'MS_Description', N'Earliest business date loaded.', N'SCHEMA', N'dbo', N'TABLE', N'data_feed', N'COLUMN', N'first_data_date';
EXEC sp_addextendedproperty N'MS_Description', N'Latest business date loaded.', N'SCHEMA', N'dbo', N'TABLE', N'data_feed', N'COLUMN', N'last_data_date';
EXEC sp_addextendedproperty N'MS_Description', N'Last successful load.', N'SCHEMA', N'dbo', N'TABLE', N'data_feed', N'COLUMN', N'last_load_at';
EXEC sp_addextendedproperty N'MS_Description', N'Rows loaded to date.', N'SCHEMA', N'dbo', N'TABLE', N'data_feed', N'COLUMN', N'rows_loaded';
EXEC sp_addextendedproperty N'MS_Description', N'Loaded versus a control total at the source.', N'SCHEMA', N'dbo', N'TABLE', N'data_feed', N'COLUMN', N'completeness_pct';
EXEC sp_addextendedproperty N'MS_Description', N'Hours since the last load.', N'SCHEMA', N'dbo', N'TABLE', N'data_feed', N'COLUMN', N'freshness_hours';
EXEC sp_addextendedproperty N'MS_Description', N'Confidence of rows from this feed (1.0 primary; lower for rebuilt).', N'SCHEMA', N'dbo', N'TABLE', N'data_feed', N'COLUMN', N'reliability_default';
EXEC sp_addextendedproperty N'MS_Description', N'Control total.', N'SCHEMA', N'dbo', N'TABLE', N'data_feed', N'COLUMN', N'expected_row_count';
EXEC sp_addextendedproperty N'MS_Description', N'1 for the first row; higher for each change.', N'SCHEMA', N'dbo', N'TABLE', N'data_feed', N'COLUMN', N'version';
EXEC sp_addextendedproperty N'MS_Description', N'1 on the latest version. Counts use current rows only.', N'SCHEMA', N'dbo', N'TABLE', N'data_feed', N'COLUMN', N'is_current';
EXEC sp_addextendedproperty N'MS_Description', N'Stable ID of a different record this one replaced (a reschedule booked as a new appointment, a replacement claim). Blank for ordinary version changes, which keep the same ID.', N'SCHEMA', N'dbo', N'TABLE', N'data_feed', N'COLUMN', N'previous_data_feed_id';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'data_feed', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'data_feed', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One X12 file received or sent.', N'SCHEMA', N'dbo', N'TABLE', N'edi_file';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'edi_file', N'COLUMN', N'edi_file_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'edi_file', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The feed it belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'edi_file', N'COLUMN', N'data_feed_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load that parsed it.', N'SCHEMA', N'dbo', N'TABLE', N'edi_file', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'837, 835, 999, 277, 270, 271, 278, 275.', N'SCHEMA', N'dbo', N'TABLE', N'edi_file', N'COLUMN', N'transaction_set';
EXEC sp_addextendedproperty N'MS_Description', N'I inbound, O outbound.', N'SCHEMA', N'dbo', N'TABLE', N'edi_file', N'COLUMN', N'direction';
EXEC sp_addextendedproperty N'MS_Description', N'ISA13.', N'SCHEMA', N'dbo', N'TABLE', N'edi_file', N'COLUMN', N'interchange_control_number';
EXEC sp_addextendedproperty N'MS_Description', N'GS06.', N'SCHEMA', N'dbo', N'TABLE', N'edi_file', N'COLUMN', N'group_control_number';
EXEC sp_addextendedproperty N'MS_Description', N'Which clearinghouse.', N'SCHEMA', N'dbo', N'TABLE', N'edi_file', N'COLUMN', N'clearinghouse_code';
EXEC sp_addextendedproperty N'MS_Description', N'SHA-256 of the file; detects duplicates.', N'SCHEMA', N'dbo', N'TABLE', N'edi_file', N'COLUMN', N'file_hash';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the file name, never the name.', N'SCHEMA', N'dbo', N'TABLE', N'edi_file', N'COLUMN', N'file_name_hash';
EXEC sp_addextendedproperty N'MS_Description', N'When it arrived or was sent.', N'SCHEMA', N'dbo', N'TABLE', N'edi_file', N'COLUMN', N'received_at';
EXEC sp_addextendedproperty N'MS_Description', N'ST/SE sets in the file.', N'SCHEMA', N'dbo', N'TABLE', N'edi_file', N'COLUMN', N'transaction_count';
EXEC sp_addextendedproperty N'MS_Description', N'received, parsed, partial, failed, reprocessed.', N'SCHEMA', N'dbo', N'TABLE', N'edi_file', N'COLUMN', N'file_status';
EXEC sp_addextendedproperty N'MS_Description', N'Sets that failed to parse.', N'SCHEMA', N'dbo', N'TABLE', N'edi_file', N'COLUMN', N'parse_error_count';
EXEC sp_addextendedproperty N'MS_Description', N'The corrected file that replaced it.', N'SCHEMA', N'dbo', N'TABLE', N'edi_file', N'COLUMN', N'replaced_by_edi_file_id';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'edi_file', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'edi_file', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One run of the loader for one feed.', N'SCHEMA', N'dbo', N'TABLE', N'load_batch';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'load_batch', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'load_batch', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The feed loaded.', N'SCHEMA', N'dbo', N'TABLE', N'load_batch', N'COLUMN', N'data_feed_id';
EXEC sp_addextendedproperty N'MS_Description', N'Start.', N'SCHEMA', N'dbo', N'TABLE', N'load_batch', N'COLUMN', N'started_at';
EXEC sp_addextendedproperty N'MS_Description', N'End. Blank while running.', N'SCHEMA', N'dbo', N'TABLE', N'load_batch', N'COLUMN', N'ended_at';
EXEC sp_addextendedproperty N'MS_Description', N'running, succeeded, partial, failed, rolled_back.', N'SCHEMA', N'dbo', N'TABLE', N'load_batch', N'COLUMN', N'batch_status';
EXEC sp_addextendedproperty N'MS_Description', N'Rows read from the source.', N'SCHEMA', N'dbo', N'TABLE', N'load_batch', N'COLUMN', N'rows_read';
EXEC sp_addextendedproperty N'MS_Description', N'New rows or versions.', N'SCHEMA', N'dbo', N'TABLE', N'load_batch', N'COLUMN', N'rows_inserted';
EXEC sp_addextendedproperty N'MS_Description', N'Skipped because source_record_hash was unchanged.', N'SCHEMA', N'dbo', N'TABLE', N'load_batch', N'COLUMN', N'rows_unchanged';
EXEC sp_addextendedproperty N'MS_Description', N'Failed validation.', N'SCHEMA', N'dbo', N'TABLE', N'load_batch', N'COLUMN', N'rows_rejected';
EXEC sp_addextendedproperty N'MS_Description', N'Highest source timestamp or file sequence loaded; the next run starts after it.', N'SCHEMA', N'dbo', N'TABLE', N'load_batch', N'COLUMN', N'source_watermark';
EXEC sp_addextendedproperty N'MS_Description', N'Loader version.', N'SCHEMA', N'dbo', N'TABLE', N'load_batch', N'COLUMN', N'code_version';
EXEC sp_addextendedproperty N'MS_Description', N'When rolled back.', N'SCHEMA', N'dbo', N'TABLE', N'load_batch', N'COLUMN', N'rolled_back_at';
EXEC sp_addextendedproperty N'MS_Description', N'Error class, never data.', N'SCHEMA', N'dbo', N'TABLE', N'load_batch', N'COLUMN', N'error_summary';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'load_batch', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'load_batch', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One data-quality rule evaluated on one load.', N'SCHEMA', N'dbo', N'TABLE', N'data_quality_result';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'data_quality_result', N'COLUMN', N'data_quality_result_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'data_quality_result', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'The load checked.', N'SCHEMA', N'dbo', N'TABLE', N'data_quality_result', N'COLUMN', N'load_batch_id';
EXEC sp_addextendedproperty N'MS_Description', N'The rule (for example claim_total_equals_lines).', N'SCHEMA', N'dbo', N'TABLE', N'data_quality_result', N'COLUMN', N'dq_rule_code';
EXEC sp_addextendedproperty N'MS_Description', N'Table checked.', N'SCHEMA', N'dbo', N'TABLE', N'data_quality_result', N'COLUMN', N'table_name';
EXEC sp_addextendedproperty N'MS_Description', N'Column, when the rule is about one.', N'SCHEMA', N'dbo', N'TABLE', N'data_quality_result', N'COLUMN', N'column_name';
EXEC sp_addextendedproperty N'MS_Description', N'block, warn, info.', N'SCHEMA', N'dbo', N'TABLE', N'data_quality_result', N'COLUMN', N'severity';
EXEC sp_addextendedproperty N'MS_Description', N'Rows evaluated.', N'SCHEMA', N'dbo', N'TABLE', N'data_quality_result', N'COLUMN', N'rows_checked';
EXEC sp_addextendedproperty N'MS_Description', N'Rows that failed.', N'SCHEMA', N'dbo', N'TABLE', N'data_quality_result', N'COLUMN', N'rows_failed';
EXEC sp_addextendedproperty N'MS_Description', N'Pointer to failed row IDs, never values.', N'SCHEMA', N'dbo', N'TABLE', N'data_quality_result', N'COLUMN', N'sample_ref';
EXEC sp_addextendedproperty N'MS_Description', N'When run.', N'SCHEMA', N'dbo', N'TABLE', N'data_quality_result', N'COLUMN', N'run_at';
EXEC sp_addextendedproperty N'MS_Description', N'open, accepted, fixed.', N'SCHEMA', N'dbo', N'TABLE', N'data_quality_result', N'COLUMN', N'dq_status';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'data_quality_result', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'data_quality_result', N'COLUMN', N'loaded_at';
EXEC sp_addextendedproperty N'MS_Description', N'One access to data: who or what read or exported which table, and whether restricted columns were touched.', N'SCHEMA', N'dbo', N'TABLE', N'access_audit';
EXEC sp_addextendedproperty N'MS_Description', N'Internal identity ID. Every join and link between tables uses this, so the client''s number never has to be shown or masked in analytics.', N'SCHEMA', N'dbo', N'TABLE', N'access_audit', N'COLUMN', N'access_audit_id';
EXEC sp_addextendedproperty N'MS_Description', N'The client organisation the row belongs to.', N'SCHEMA', N'dbo', N'TABLE', N'access_audit', N'COLUMN', N'tenant_id';
EXEC sp_addextendedproperty N'MS_Description', N'When.', N'SCHEMA', N'dbo', N'TABLE', N'access_audit', N'COLUMN', N'accessed_at';
EXEC sp_addextendedproperty N'MS_Description', N'staff, agent, service, support.', N'SCHEMA', N'dbo', N'TABLE', N'access_audit', N'COLUMN', N'actor_type';
EXEC sp_addextendedproperty N'MS_Description', N'The person.', N'SCHEMA', N'dbo', N'TABLE', N'access_audit', N'COLUMN', N'staff_id';
EXEC sp_addextendedproperty N'MS_Description', N'The agent run.', N'SCHEMA', N'dbo', N'TABLE', N'access_audit', N'COLUMN', N'agent_run_id';
EXEC sp_addextendedproperty N'MS_Description', N'view, query, export, unmask.', N'SCHEMA', N'dbo', N'TABLE', N'access_audit', N'COLUMN', N'action';
EXEC sp_addextendedproperty N'MS_Description', N'Table read.', N'SCHEMA', N'dbo', N'TABLE', N'access_audit', N'COLUMN', N'table_name';
EXEC sp_addextendedproperty N'MS_Description', N'Rows returned.', N'SCHEMA', N'dbo', N'TABLE', N'access_audit', N'COLUMN', N'row_count';
EXEC sp_addextendedproperty N'MS_Description', N'1 if any restricted column was read.', N'SCHEMA', N'dbo', N'TABLE', N'access_audit', N'COLUMN', N'touched_restricted';
EXEC sp_addextendedproperty N'MS_Description', N'operations, support, audit, analytics.', N'SCHEMA', N'dbo', N'TABLE', N'access_audit', N'COLUMN', N'purpose_code';
EXEC sp_addextendedproperty N'MS_Description', N'Hash of the query text.', N'SCHEMA', N'dbo', N'TABLE', N'access_audit', N'COLUMN', N'query_hash';
EXEC sp_addextendedproperty N'MS_Description', N'Where the row came from: feed, API, PM export, rebuilt from another record.', N'SCHEMA', N'dbo', N'TABLE', N'access_audit', N'COLUMN', N'source';
EXEC sp_addextendedproperty N'MS_Description', N'When the row was loaded.', N'SCHEMA', N'dbo', N'TABLE', N'access_audit', N'COLUMN', N'loaded_at';
GO
