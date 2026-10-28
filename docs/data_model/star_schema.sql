-- KrisnAI RCM dimensional model v2 (SQL Server): the claim journey in four phases. Generated from model_spec_v2.py: edit the spec, not this file.
-- PHASE 1 Appointment -> PHASE 2 Encounter -> PHASE 3 Bill -> PHASE 4 Transactions, denials and AR. Linked by appointment_ref, encounter_ref, claim_ref.
-- Rules honoured: tenant_id on every table (8); patients only as salted hashes (1); money DECIMAL(12,2) and dates DATE (10);
-- known_at on every fact for point-in-time replay (9); a unique natural key per fact makes loads idempotent (7); event_key = lineage to the append-only event.
-- An 'Unknown' member (key 0) per dimension is added by the load job. DRAFT FOR REVIEW: not applied to any database.

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'dw') EXEC('CREATE SCHEMA dw');
GO

-- A 999 or TA1 acknowledgement result and error code.
CREATE TABLE dw.dim_ack_code (
    ack_code_key INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_dim_ack_code PRIMARY KEY,
    tenant_id INT NOT NULL,
    transaction_set NVARCHAR(20) NOT NULL,  -- 999, TA1
    ack_code NVARCHAR(20) NOT NULL,  -- Status or error code
    ack_label NVARCHAR(200) NULL,  -- Plain meaning
    is_accepted BIT NULL,  -- Accepted or accepted with errors
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_dim_ack_code_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_dim_ack_code_bk UNIQUE (tenant_id, transaction_set, ack_code)
);
GO

-- One of the 15 agents.
CREATE TABLE dw.dim_agent (
    agent_key INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_dim_agent PRIMARY KEY,
    tenant_id INT NOT NULL,
    agent_id NVARCHAR(50) NOT NULL,  -- a1_clearance ... a15_investigator
    agent_code NVARCHAR(20) NULL,  -- A1 ... A15
    agent_name NVARCHAR(100) NULL,  -- Gatekeeper, Permit Clerk ...
    lifecycle_stage NVARCHAR(20) NULL,  -- front end, mid cycle, back end, control
    agent_version NVARCHAR(20) NULL,  -- Current version
    valid_from DATE NOT NULL CONSTRAINT DF_dim_agent_vf DEFAULT '19000101',
    valid_to DATE NULL,
    is_current BIT NOT NULL CONSTRAINT DF_dim_agent_cur DEFAULT 1,
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_dim_agent_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_dim_agent_bk UNIQUE (tenant_id, agent_id, valid_from)
);
GO

-- Why the patient is coming: visit kind, length and whether it needs an eligibility or authorization check.
CREATE TABLE dw.dim_appointment_type (
    appointment_type_key INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_dim_appointment_type PRIMARY KEY,
    tenant_id INT NOT NULL,
    appointment_type_code NVARCHAR(50) NOT NULL,  -- Code
    label NVARCHAR(100) NULL,  -- Plain name
    visit_kind NVARCHAR(20) NULL,  -- new, established, follow_up, procedure, preventive, emergency, telehealth
    default_duration_min SMALLINT NULL,  -- Planned minutes
    is_telehealth BIT NULL,  -- Virtual visit
    needs_auth_check BIT NULL,  -- Usually needs an authorization check
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_dim_appointment_type_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_dim_appointment_type_bk UNIQUE (tenant_id, appointment_type_code)
);
GO

-- A bank account on either side of a payment. Account numbers are kept as a hash only.
CREATE TABLE dw.dim_bank_account (
    bank_account_key INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_dim_bank_account PRIMARY KEY,
    tenant_id INT NOT NULL,
    bank_account_ref NVARCHAR(50) NOT NULL,  -- Account reference
    routing_number CHAR(9) NULL,  -- Institution routing number
    account_type NVARCHAR(20) NULL,  -- checking, savings, lockbox
    account_ref_hash BINARY(32) NULL,  -- Hash of the account number
    owner_side NVARCHAR(20) NULL,  -- payer, practice
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_dim_bank_account_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_dim_bank_account_bk UNIQUE (tenant_id, bank_account_ref)
);
GO

-- How something is sent or received.
CREATE TABLE dw.dim_channel (
    channel_key INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_dim_channel PRIMARY KEY,
    tenant_id INT NOT NULL,
    channel_code NVARCHAR(50) NOT NULL,  -- x12_edi, fhir_api, portal, phone, fax, emr_task, emr_message, email, sms, mail, drop_folder, hl7, db_view, upload
    direction NVARCHAR(20) NULL,  -- in, out, both
    is_electronic BIT NULL,  -- Machine to machine
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_dim_channel_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_dim_channel_bk UNIQUE (tenant_id, channel_code)
);
GO

-- Calendar. Role-played by every date on every fact (appointment, service, request, decision, payment ...).
CREATE TABLE dw.dim_date (
    date_key INT NOT NULL CONSTRAINT PK_dim_date PRIMARY KEY,
    tenant_id INT NOT NULL,
    full_date DATE NOT NULL,  -- The date
    year SMALLINT NULL,  -- Calendar year
    quarter TINYINT NULL,  -- 1-4
    month TINYINT NULL,  -- 1-12
    month_name NVARCHAR(20) NULL,  -- January ...
    week_of_year TINYINT NULL,  -- ISO week
    day_of_week TINYINT NULL,  -- 1 Monday ... 7 Sunday
    is_weekend BIT NULL,  -- Saturday or Sunday
    is_business_day BIT NULL,  -- Not a weekend or a practice holiday
    fiscal_year SMALLINT NULL,  -- Practice fiscal year
    fiscal_period TINYINT NULL,  -- Practice fiscal period
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_dim_date_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_dim_date_bk UNIQUE (tenant_id, full_date)
);
GO

-- Junk dimension: the small set of flags on every agent decision.
CREATE TABLE dw.dim_decision_context (
    decision_context_key INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_dim_decision_context PRIMARY KEY,
    tenant_id INT NOT NULL,
    autonomy_level TINYINT NOT NULL,  -- 0 observe to 4 bounded autonomous
    run_mode NVARCHAR(20) NOT NULL,  -- shadow, live
    outcome NVARCHAR(50) NOT NULL,  -- denied, shadow, observed, pending_approval, executed ...
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_dim_decision_context_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_dim_decision_context_bk UNIQUE (tenant_id, autonomy_level, run_mode, outcome)
);
GO

-- An ICD-10-CM diagnosis code.
CREATE TABLE dw.dim_diagnosis (
    diagnosis_key INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_dim_diagnosis PRIMARY KEY,
    tenant_id INT NOT NULL,
    icd10_code VARCHAR(8) NOT NULL,  -- ICD-10-CM code
    code_set_version NVARCHAR(20) NOT NULL,  -- Code set year
    chapter NVARCHAR(100) NULL,  -- ICD chapter group
    is_chronic BIT NULL,  -- Chronic condition
    is_unspecified BIT NULL,  -- Unspecified code
    parent_icd10_code VARCHAR(8) NULL,  -- Less specific parent code
    valid_from DATE NOT NULL CONSTRAINT DF_dim_diagnosis_vf DEFAULT '19000101',
    valid_to DATE NULL,
    is_current BIT NOT NULL CONSTRAINT DF_dim_diagnosis_cur DEFAULT 1,
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_dim_diagnosis_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_dim_diagnosis_bk UNIQUE (tenant_id, icd10_code, code_set_version, valid_from)
);
GO

-- A kind of document, order or attachment.
CREATE TABLE dw.dim_document_type (
    document_type_key INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_dim_document_type PRIMARY KEY,
    tenant_id INT NOT NULL,
    doc_type_code NVARCHAR(50) NOT NULL,  -- progress_note, order, referral, consent, result, letter, attachment, records_pack ...
    category NVARCHAR(100) NULL,  -- clinical, administrative, financial
    requires_signature BIT NULL,  -- Must be signed
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_dim_document_type_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_dim_document_type_bk UNIQUE (tenant_id, doc_type_code)
);
GO

-- A claim-line modifier.
CREATE TABLE dw.dim_modifier (
    modifier_key INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_dim_modifier PRIMARY KEY,
    tenant_id INT NOT NULL,
    modifier_code CHAR(2) NOT NULL,  -- Modifier
    modifier_group NVARCHAR(100) NULL,  -- pricing, laterality, anatomical, informational
    internal_label NVARCHAR(100) NULL,  -- Own-words label
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_dim_modifier_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_dim_modifier_bk UNIQUE (tenant_id, modifier_code)
);
GO

-- A patient as a salted hash only (rule 1). No name, date of birth or member id is ever stored.
CREATE TABLE dw.dim_patient (
    patient_key INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_dim_patient PRIMARY KEY,
    tenant_id INT NOT NULL,
    patient_ref_hash BINARY(32) NOT NULL,  -- Salted SHA-256 of the patient identifier
    master_patient_hash BINARY(32) NULL,  -- Same person across member ids
    age_band NVARCHAR(20) NULL,  -- 0-17, 18-39, 40-64, 65+ (no exact age)
    sex_code CHAR(1) NULL,  -- M, F, U
    first_seen_date DATE NULL,  -- First appointment or claim seen
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_dim_patient_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_dim_patient_bk UNIQUE (tenant_id, patient_ref_hash)
);
GO

-- An insurer. Filing and appeal limits live here as attributes because they change slowly.
CREATE TABLE dw.dim_payer (
    payer_key INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_dim_payer PRIMARY KEY,
    tenant_id INT NOT NULL,
    payer_id_code NVARCHAR(50) NOT NULL,  -- Payer id used by the clearinghouse (NM1*PR)
    payer_name NVARCHAR(200) NULL,  -- Name
    payer_type NVARCHAR(20) NULL,  -- commercial, medicare, medicaid, tricare, workers_comp, auto, self_pay
    parent_payer NVARCHAR(200) NULL,  -- Owning organisation
    filing_days SMALLINT NULL,  -- Timely filing limit
    appeal_days SMALLINT NULL,  -- Appeal window
    standard_turnaround_days SMALLINT NULL,  -- Usual authorization turnaround
    supports_electronic_auth BIT NULL,  -- Accepts electronic prior authorization
    allows_retro_effective BIT NULL,  -- Payer backdates effective dates
    corrected_claim_days SMALLINT NULL,  -- Corrected-claim filing window
    filing_clock_start NVARCHAR(20) NULL,  -- service_date or discharge_date
    dispute_contact NVARCHAR(200) NULL,  -- Role mailbox or portal for disputes (no personal name)
    enrollment_contact NVARCHAR(200) NULL,  -- Role mailbox or portal for enrollment
    valid_from DATE NOT NULL CONSTRAINT DF_dim_payer_vf DEFAULT '19000101',
    valid_to DATE NULL,
    is_current BIT NOT NULL CONSTRAINT DF_dim_payer_cur DEFAULT 1,
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_dim_payer_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_dim_payer_bk UNIQUE (tenant_id, payer_id_code, valid_from)
);
GO

-- CMS place-of-service code.
CREATE TABLE dw.dim_place_of_service (
    place_of_service_key INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_dim_place_of_service PRIMARY KEY,
    tenant_id INT NOT NULL,
    pos_code CHAR(2) NOT NULL,  -- POS code
    pos_name NVARCHAR(100) NULL,  -- Name
    setting NVARCHAR(20) NULL,  -- office, facility, home, telehealth ...
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_dim_place_of_service_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_dim_place_of_service_bk UNIQUE (tenant_id, pos_code)
);
GO

-- A clinician or group. Roles (rendering, requesting, billing, referring) are played by the fact, not stored here.
CREATE TABLE dw.dim_provider (
    provider_key INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_dim_provider PRIMARY KEY,
    tenant_id INT NOT NULL,
    npi CHAR(10) NOT NULL,  -- National provider id
    provider_name NVARCHAR(200) NULL,  -- Name or group name
    tax_id CHAR(9) NULL,  -- EIN
    taxonomy_code NVARCHAR(20) NULL,  -- Specialty taxonomy
    specialty NVARCHAR(100) NULL,  -- Specialty group
    is_group BIT NULL,  -- Group (type 2) rather than individual
    credential NVARCHAR(20) NULL,  -- MD, DO, NP, PA ...
    provider_type NVARCHAR(100) NULL,  -- individual, group, facility
    start_date DATE NULL,  -- Joined
    end_date DATE NULL,  -- Left
    group_provider_key INT NULL,  -- Group the provider bills under
    valid_from DATE NOT NULL CONSTRAINT DF_dim_provider_vf DEFAULT '19000101',
    valid_to DATE NULL,
    is_current BIT NOT NULL CONSTRAINT DF_dim_provider_cur DEFAULT 1,
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_dim_provider_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_dim_provider_bk UNIQUE (tenant_id, npi, valid_from),
    CONSTRAINT FK_dim_provider_group_provider_key FOREIGN KEY (group_provider_key) REFERENCES dw.dim_provider(provider_key)
);
GO

-- A remittance remark (RARC).
CREATE TABLE dw.dim_remark_code (
    remark_code_key INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_dim_remark_code PRIMARY KEY,
    tenant_id INT NOT NULL,
    rarc_code NVARCHAR(20) NOT NULL,  -- RARC code
    remark_category NVARCHAR(100) NULL,  -- Category
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_dim_remark_code_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_dim_remark_code_bk UNIQUE (tenant_id, rarc_code)
);
GO

-- A job role that owns work.
CREATE TABLE dw.dim_role (
    role_key INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_dim_role PRIMARY KEY,
    tenant_id INT NOT NULL,
    role_code NVARCHAR(50) NOT NULL,  -- front_desk, billing, coding, ar_lead, finance, provider, compliance, practice_manager
    role_name NVARCHAR(100) NULL,  -- Name
    approval_limit_amount DECIMAL(12,2) NULL,  -- Largest amount the role may approve
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_dim_role_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_dim_role_bk UNIQUE (tenant_id, role_code)
);
GO

-- A procedure code (CPT or HCPCS). Code numbers and own-words labels only: CPT descriptor text is AMA-licensed and is not stored.
CREATE TABLE dw.dim_service_code (
    service_code_key INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_dim_service_code PRIMARY KEY,
    tenant_id INT NOT NULL,
    code VARCHAR(5) NOT NULL,  -- CPT or HCPCS code
    code_set_version NVARCHAR(20) NOT NULL,  -- Code set year
    code_type NVARCHAR(20) NULL,  -- CPT, HCPCS
    category NVARCHAR(100) NULL,  -- E/M, radiology, therapy, lab, procedure ...
    em_level TINYINT NULL,  -- Level 1-5 for E/M codes
    is_add_on BIT NULL,  -- Add-on code
    is_timed BIT NULL,  -- Billed per time unit
    laterality_required BIT NULL,  -- Needs LT / RT / 50
    mue_units_per_day SMALLINT NULL,  -- Maximum units per day
    internal_label NVARCHAR(100) NULL,  -- Short label in the practice's own words
    mue_adjudication_indicator TINYINT NULL,  -- How the unit limit is adjudicated
    valid_from DATE NOT NULL CONSTRAINT DF_dim_service_code_vf DEFAULT '19000101',
    valid_to DATE NULL,
    is_current BIT NOT NULL CONSTRAINT DF_dim_service_code_cur DEFAULT 1,
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_dim_service_code_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_dim_service_code_bk UNIQUE (tenant_id, code, code_set_version, valid_from)
);
GO

-- Where data came from.
CREATE TABLE dw.dim_source_system (
    source_system_key INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_dim_source_system PRIMARY KEY,
    tenant_id INT NOT NULL,
    system_code NVARCHAR(50) NOT NULL,  -- openemr, hl7_feed, csv_drop, db_view, clearinghouse, payer_sim, pm_extract, bank, manual
    system_kind NVARCHAR(20) NULL,  -- emr, pm, clearinghouse, bank, file, manual
    vendor NVARCHAR(100) NULL,  -- Vendor
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_dim_source_system_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_dim_source_system_bk UNIQUE (tenant_id, system_code)
);
GO

-- Any other status, kept by domain (appointment, auth, charge, note, task, approval, writeback, enrollment, order, consent ...).
CREATE TABLE dw.dim_status (
    status_key INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_dim_status PRIMARY KEY,
    tenant_id INT NOT NULL,
    status_domain NVARCHAR(50) NOT NULL,  -- Which kind of status
    status_code NVARCHAR(50) NOT NULL,  -- Code
    status_label NVARCHAR(100) NULL,  -- Plain meaning
    is_terminal BIT NULL,  -- Final
    sort_order TINYINT NULL,  -- Display order
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_dim_status_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_dim_status_bk UNIQUE (tenant_id, status_domain, status_code)
);
GO

-- An action an agent can propose (a1_cob_review, a2_auth_request_task ...).
CREATE TABLE dw.dim_action_type (
    action_type_key INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_dim_action_type PRIMARY KEY,
    tenant_id INT NOT NULL,
    action_type NVARCHAR(50) NOT NULL,  -- Action type code
    agent_key INT NULL,  -- Owning agent
    owner_role_key INT NULL,  -- Role that does it
    requires_approval BIT NULL,  -- Needs a named human
    reversibility_class NVARCHAR(20) NULL,  -- Reversible, hard to reverse, irreversible
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_dim_action_type_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_dim_action_type_bk UNIQUE (tenant_id, action_type),
    CONSTRAINT FK_dim_action_type_agent_key FOREIGN KEY (agent_key) REFERENCES dw.dim_agent(agent_key),
    CONSTRAINT FK_dim_action_type_owner_role_key FOREIGN KEY (owner_role_key) REFERENCES dw.dim_role(role_key)
);
GO

-- A claim adjustment reason (CARC) with how the practice routes it.
CREATE TABLE dw.dim_adjustment_reason (
    adjustment_reason_key INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_dim_adjustment_reason PRIMARY KEY,
    tenant_id INT NOT NULL,
    carc_code NVARCHAR(20) NOT NULL,  -- CARC code
    reason_category NVARCHAR(100) NULL,  -- Routing category
    owner_role_key INT NULL,  -- Role that works it
    disposition NVARCHAR(100) NULL,  -- fix, appeal, write-off review, patient, informational
    is_denial BIT NULL,  -- A denial rather than a contractual or patient adjustment
    is_patient_responsibility BIT NULL,  -- Shifts to the patient
    description NVARCHAR(500) NULL,  -- Plain meaning of the CARC
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_dim_adjustment_reason_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_dim_adjustment_reason_bk UNIQUE (tenant_id, carc_code),
    CONSTRAINT FK_dim_adjustment_reason_owner_role_key FOREIGN KEY (owner_role_key) REFERENCES dw.dim_role(role_key)
);
GO

-- A claim status from an acknowledgement or a status answer (999, 277CA, 276/277) or the claim's own lifecycle.
CREATE TABLE dw.dim_claim_status (
    claim_status_key INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_dim_claim_status PRIMARY KEY,
    tenant_id INT NOT NULL,
    status_domain NVARCHAR(20) NOT NULL,  -- 999, 277CA, 277, lifecycle
    category_code NVARCHAR(20) NOT NULL,  -- Status category
    status_code NVARCHAR(20) NOT NULL,  -- Status code
    entity_code NVARCHAR(20) NULL,  -- Entity the status is about
    status_label NVARCHAR(200) NULL,  -- Plain meaning
    is_technical_reject BIT NULL,  -- Fixable without a clinical decision
    is_terminal BIT NULL,  -- No further movement expected
    owner_role_key INT NULL,  -- Role that works it
    rejection_category NVARCHAR(100) NULL,  -- Routing category of a rejection
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_dim_claim_status_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_dim_claim_status_bk UNIQUE (tenant_id, status_domain, category_code, status_code),
    CONSTRAINT FK_dim_claim_status_owner_role_key FOREIGN KEY (owner_role_key) REFERENCES dw.dim_role(role_key)
);
GO

-- Two codes that interact: NCCI bundle pairs and add-on to primary links.
CREATE TABLE dw.dim_code_pair (
    code_pair_key INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_dim_code_pair PRIMARY KEY,
    tenant_id INT NOT NULL,
    code_a_key INT NOT NULL,  -- First code
    code_b_key INT NOT NULL,  -- Second code
    pair_type NVARCHAR(20) NOT NULL,  -- ncci_bundle, add_on_primary
    modifier_indicator CHAR(1) NULL,  -- 0, 1 or 9
    valid_from DATE NOT NULL,  -- From
    valid_to DATE NULL,  -- To
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_dim_code_pair_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_dim_code_pair_bk UNIQUE (tenant_id, code_a_key, code_b_key, pair_type, valid_from),
    CONSTRAINT FK_dim_code_pair_code_a_key FOREIGN KEY (code_a_key) REFERENCES dw.dim_service_code(service_code_key),
    CONSTRAINT FK_dim_code_pair_code_b_key FOREIGN KEY (code_b_key) REFERENCES dw.dim_service_code(service_code_key)
);
GO

-- What the payer contracts to allow per unit: the base for expected allowed and underpayment.
CREATE TABLE dw.dim_contract_rate (
    contract_rate_key INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_dim_contract_rate PRIMARY KEY,
    tenant_id INT NOT NULL,
    contract_ref NVARCHAR(50) NOT NULL,  -- Contract id
    payer_key INT NOT NULL,  -- Payer
    service_code_key INT NOT NULL,  -- Procedure
    modifier_code CHAR(2) NOT NULL,  -- Modifier, blank when none
    allowed_per_unit DECIMAL(12,2) NULL,  -- Allowed per unit
    effective_from DATE NOT NULL,  -- From
    effective_to DATE NULL,  -- To
    rate_basis NVARCHAR(20) NULL,  -- fixed, percent_of_medicare ...
    multi_proc_reduction_pct DECIMAL(5,2) NULL,  -- Multiple-procedure reduction
    lesser_of_billed BIT NULL,  -- Pays the lesser of billed and allowed
    dispute_days SMALLINT NULL,  -- Days allowed to dispute
    extraction_confidence DECIMAL(5,4) NULL,  -- Confidence when read from a contract document
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_dim_contract_rate_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_dim_contract_rate_bk UNIQUE (tenant_id, contract_ref, payer_key, service_code_key, modifier_code, effective_from),
    CONSTRAINT FK_dim_contract_rate_payer_key FOREIGN KEY (payer_key) REFERENCES dw.dim_payer(payer_key),
    CONSTRAINT FK_dim_contract_rate_service_code_key FOREIGN KEY (service_code_key) REFERENCES dw.dim_service_code(service_code_key)
);
GO

-- One insurance policy for one patient: the plan, its order and the policyholder relationship.
CREATE TABLE dw.dim_coverage (
    coverage_key INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_dim_coverage PRIMARY KEY,
    tenant_id INT NOT NULL,
    coverage_ref NVARCHAR(50) NOT NULL,  -- Policy id in the source system (hashed if it identifies a person)
    payer_key INT NULL,  -- Insurer
    plan_name NVARCHAR(100) NULL,  -- Plan
    plan_type NVARCHAR(20) NULL,  -- PPO, HMO, EPO, POS, Medicare Advantage ...
    group_ref NVARCHAR(50) NULL,  -- Group number (hashed)
    coverage_order TINYINT NULL,  -- 1 primary, 2 secondary, 3 tertiary
    relationship_to_holder NVARCHAR(20) NULL,  -- self, spouse, child, other
    holder_ref_hash BINARY(32) NULL,  -- Policyholder as a hash
    effective_date DATE NULL,  -- Policy start
    termination_date DATE NULL,  -- Policy end, null = open
    valid_from DATE NOT NULL CONSTRAINT DF_dim_coverage_vf DEFAULT '19000101',
    valid_to DATE NULL,
    is_current BIT NOT NULL CONSTRAINT DF_dim_coverage_cur DEFAULT 1,
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_dim_coverage_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_dim_coverage_bk UNIQUE (tenant_id, coverage_ref, valid_from),
    CONSTRAINT FK_dim_coverage_payer_key FOREIGN KEY (payer_key) REFERENCES dw.dim_payer(payer_key)
);
GO

-- A location where the service happens.
CREATE TABLE dw.dim_facility (
    facility_key INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_dim_facility PRIMARY KEY,
    tenant_id INT NOT NULL,
    facility_ref NVARCHAR(50) NOT NULL,  -- Facility id or NPI
    facility_name NVARCHAR(200) NULL,  -- Name
    default_pos_key INT NULL,  -- Usual place of service
    state CHAR(2) NULL,  -- State
    region NVARCHAR(100) NULL,  -- Practice region
    valid_from DATE NOT NULL CONSTRAINT DF_dim_facility_vf DEFAULT '19000101',
    valid_to DATE NULL,
    is_current BIT NOT NULL CONSTRAINT DF_dim_facility_cur DEFAULT 1,
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_dim_facility_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_dim_facility_bk UNIQUE (tenant_id, facility_ref, valid_from),
    CONSTRAINT FK_dim_facility_default_pos_key FOREIGN KEY (default_pos_key) REFERENCES dw.dim_place_of_service(place_of_service_key)
);
GO

-- The reusable metric catalog: one row per defined metric, so every dashboard uses the same definition.
CREATE TABLE dw.dim_metric (
    metric_key INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_dim_metric PRIMARY KEY,
    tenant_id INT NOT NULL,
    metric_code NVARCHAR(50) NOT NULL,  -- e.g. first_pass_acceptance_rate
    metric_name NVARCHAR(100) NULL,  -- Name
    definition NVARCHAR(500) NULL,  -- Plain definition
    numerator NVARCHAR(200) NULL,  -- Fact.measure or expression
    denominator NVARCHAR(200) NULL,  -- Fact.measure or expression
    unit NVARCHAR(20) NULL,  -- percent, dollars, days, count
    higher_is_better BIT NULL,  -- Direction
    owner_agent_key INT NULL,  -- Agent that owns it
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_dim_metric_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_dim_metric_bk UNIQUE (tenant_id, metric_code),
    CONSTRAINT FK_dim_metric_owner_agent_key FOREIGN KEY (owner_agent_key) REFERENCES dw.dim_agent(agent_key)
);
GO

-- A diagnosis that supports a procedure (medical necessity pairing).
CREATE TABLE dw.dim_necessity_pair (
    necessity_pair_key INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_dim_necessity_pair PRIMARY KEY,
    tenant_id INT NOT NULL,
    service_code_key INT NOT NULL,  -- Procedure
    diagnosis_key INT NOT NULL,  -- Supporting diagnosis
    source NVARCHAR(50) NOT NULL,  -- Coverage policy or list
    region NVARCHAR(50) NULL,  -- Region or contractor
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_dim_necessity_pair_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_dim_necessity_pair_bk UNIQUE (tenant_id, service_code_key, diagnosis_key, source),
    CONSTRAINT FK_dim_necessity_pair_service_code_key FOREIGN KEY (service_code_key) REFERENCES dw.dim_service_code(service_code_key),
    CONSTRAINT FK_dim_necessity_pair_diagnosis_key FOREIGN KEY (diagnosis_key) REFERENCES dw.dim_diagnosis(diagnosis_key)
);
GO

-- The documentation of an encounter: one row per note version. Descriptive only; the text is never stored, only a hash.
CREATE TABLE dw.dim_note (
    note_key INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_dim_note PRIMARY KEY,
    tenant_id INT NOT NULL,
    note_ref NVARCHAR(50) NOT NULL,  -- Note id
    note_version SMALLINT NOT NULL,  -- Original 1, addenda higher
    doc_type_key INT NULL,  -- Note type
    author_provider_key INT NULL,  -- Author
    note_date DATE NULL,  -- Note started
    signed_date DATE NULL,  -- Signed
    cosign_date DATE NULL,  -- Cosigned
    status_key INT NULL,  -- draft, signed, cosign_needed, amended
    is_late_entry BIT NULL,  -- Late entry
    is_addendum BIT NULL,  -- Addendum
    source_format NVARCHAR(20) NULL,  -- structured, free_text, scanned
    text_hash CHAR(64) NULL,  -- Hash only
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_dim_note_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_dim_note_bk UNIQUE (tenant_id, note_ref, note_version),
    CONSTRAINT FK_dim_note_doc_type_key FOREIGN KEY (doc_type_key) REFERENCES dw.dim_document_type(document_type_key),
    CONSTRAINT FK_dim_note_author_provider_key FOREIGN KEY (author_provider_key) REFERENCES dw.dim_provider(provider_key),
    CONSTRAINT FK_dim_note_status_key FOREIGN KEY (status_key) REFERENCES dw.dim_status(status_key)
);
GO

-- How the patient may be contacted: preferences and consent flags only. No phone number, email or address is stored.
CREATE TABLE dw.dim_patient_contact (
    patient_contact_key INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_dim_patient_contact PRIMARY KEY,
    tenant_id INT NOT NULL,
    patient_key INT NOT NULL,  -- Patient
    preferred_channel_key INT NULL,  -- Preferred channel
    preferred_language NVARCHAR(20) NULL,  -- Language
    quiet_hours NVARCHAR(50) NULL,  -- Do not contact between
    address_status NVARCHAR(20) NULL,  -- valid, returned_mail, unknown
    has_phone BIT NULL,  -- A phone is on file
    has_email BIT NULL,  -- An email is on file
    text_consent BIT NULL,  -- Consent to text
    text_consent_date DATE NULL,  -- Consent date
    opt_out BIT NULL,  -- Opted out
    opt_out_date DATE NULL,  -- Opt-out date
    authorized_rep BIT NULL,  -- An authorized representative is on file
    autopay_enrolled BIT NULL,  -- Autopay
    guarantor_ref_hash BINARY(32) NULL,  -- Guarantor as a hash
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_dim_patient_contact_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_dim_patient_contact_bk UNIQUE (tenant_id, patient_key),
    CONSTRAINT FK_dim_patient_contact_patient_key FOREIGN KEY (patient_key) REFERENCES dw.dim_patient(patient_key),
    CONSTRAINT FK_dim_patient_contact_preferred_channel_key FOREIGN KEY (preferred_channel_key) REFERENCES dw.dim_channel(channel_key)
);
GO

-- A deterministic rule that can fire: code rules, Knowledge Book rules, learned rules.
CREATE TABLE dw.dim_rule (
    rule_key INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_dim_rule PRIMARY KEY,
    tenant_id INT NOT NULL,
    rule_id NVARCHAR(50) NOT NULL,  -- Rule id
    rule_version SMALLINT NOT NULL,  -- Version
    rule_family NVARCHAR(100) NULL,  -- prior_auth, coverage, bundling, necessity, filing, appeal, code ...
    agent_key INT NULL,  -- Agent that applies it
    rule_source NVARCHAR(20) NULL,  -- code, knowledge_book, learned
    effective_from DATE NULL,  -- Rule effective from
    effective_to DATE NULL,  -- Rule effective to
    description NVARCHAR(200) NULL,  -- Plain meaning
    rule_scope NVARCHAR(500) NULL,  -- Codes, modifiers, place of service, reason codes or documents the rule covers
    payer_key INT NULL,  -- Payer the rule belongs to
    last_confirmed_date DATE NULL,  -- When a person last confirmed it
    is_enabled BIT NULL,  -- On or off
    is_synthetic BIT NULL,  -- Demo rule, not a real payer policy
    owner_role_key INT NULL,  -- Role that owns it
    approval_status NVARCHAR(20) NULL,  -- proposed, approved, retired
    retire_reason NVARCHAR(100) NULL,  -- Why it was retired
    valid_from DATE NOT NULL CONSTRAINT DF_dim_rule_vf DEFAULT '19000101',
    valid_to DATE NULL,
    is_current BIT NOT NULL CONSTRAINT DF_dim_rule_cur DEFAULT 1,
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_dim_rule_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_dim_rule_bk UNIQUE (tenant_id, rule_id, rule_version, valid_from),
    CONSTRAINT FK_dim_rule_agent_key FOREIGN KEY (agent_key) REFERENCES dw.dim_agent(agent_key),
    CONSTRAINT FK_dim_rule_payer_key FOREIGN KEY (payer_key) REFERENCES dw.dim_payer(payer_key),
    CONSTRAINT FK_dim_rule_owner_role_key FOREIGN KEY (owner_role_key) REFERENCES dw.dim_role(role_key)
);
GO

-- A staff member as a pseudonymous reference. Individual performance measures need the client's sign-off.
CREATE TABLE dw.dim_staff (
    staff_key INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_dim_staff PRIMARY KEY,
    tenant_id INT NOT NULL,
    staff_ref NVARCHAR(50) NOT NULL,  -- Pseudonymous id
    role_key INT NULL,  -- Role
    team NVARCHAR(100) NULL,  -- Team or queue
    weekly_hours DECIMAL(4,1) NULL,  -- Hours per week
    skill_tags NVARCHAR(200) NULL,  -- Skills used for allocation
    working_days VARCHAR(7) NULL,  -- Days worked, e.g. MTWTF
    valid_from DATE NOT NULL CONSTRAINT DF_dim_staff_vf DEFAULT '19000101',
    valid_to DATE NULL,
    is_current BIT NOT NULL CONSTRAINT DF_dim_staff_cur DEFAULT 1,
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_dim_staff_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_dim_staff_bk UNIQUE (tenant_id, staff_ref, valid_from),
    CONSTRAINT FK_dim_staff_role_key FOREIGN KEY (role_key) REFERENCES dw.dim_role(role_key)
);
GO

-- A prior authorization as the payer issued it: number, window, units and status. Supports the encounter and the bill.
CREATE TABLE dw.dim_authorization (
    authorization_key INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_dim_authorization PRIMARY KEY,
    tenant_id INT NOT NULL,
    auth_number NVARCHAR(50) NOT NULL,  -- Number the payer issued
    payer_key INT NOT NULL,  -- Payer
    authorized_service_code_key INT NULL,  -- Procedure authorized
    request_type NVARCHAR(20) NULL,  -- initial, extension, revision, cancel
    status_key INT NULL,  -- requested, pended, certified, modified, not_certified, cancelled, expired
    review_action_code NVARCHAR(20) NULL,  -- HCR01 action: A1, A3, A4, A6
    issued_date DATE NULL,  -- Decision date
    valid_from DATE NULL,  -- Approved from
    valid_to DATE NULL,  -- Approved to
    units_approved INT NULL,  -- Units certified
    rule_key INT NULL,  -- Rule that said authorization was required
    valid_from DATE NOT NULL CONSTRAINT DF_dim_authorization_vf DEFAULT '19000101',
    valid_to DATE NULL,
    is_current BIT NOT NULL CONSTRAINT DF_dim_authorization_cur DEFAULT 1,
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_dim_authorization_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_dim_authorization_bk UNIQUE (tenant_id, auth_number, payer_key, valid_from),
    CONSTRAINT FK_dim_authorization_payer_key FOREIGN KEY (payer_key) REFERENCES dw.dim_payer(payer_key),
    CONSTRAINT FK_dim_authorization_authorized_service_code_key FOREIGN KEY (authorized_service_code_key) REFERENCES dw.dim_service_code(service_code_key),
    CONSTRAINT FK_dim_authorization_status_key FOREIGN KEY (status_key) REFERENCES dw.dim_status(status_key),
    CONSTRAINT FK_dim_authorization_rule_key FOREIGN KEY (rule_key) REFERENCES dw.dim_rule(rule_key)
);
GO

-- The practice's own fee list: what the provider charges per unit. Billed amount = units x this fee.
CREATE TABLE dw.dim_charge_master (
    charge_master_key INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_dim_charge_master PRIMARY KEY,
    tenant_id INT NOT NULL,
    fee_schedule_ref NVARCHAR(50) NOT NULL,  -- Name of the fee list
    service_code_key INT NOT NULL,  -- Procedure
    modifier_code CHAR(2) NOT NULL,  -- Modifier, blank when none
    facility_key INT NULL,  -- Location-specific fee, null = all
    fee_per_unit DECIMAL(12,2) NULL,  -- Charge per unit
    effective_from DATE NOT NULL,  -- From
    effective_to DATE NULL,  -- To, null = open
    source NVARCHAR(100) NULL,  -- Where the list came from
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_dim_charge_master_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_dim_charge_master_bk UNIQUE (tenant_id, fee_schedule_ref, service_code_key, modifier_code, effective_from),
    CONSTRAINT FK_dim_charge_master_service_code_key FOREIGN KEY (service_code_key) REFERENCES dw.dim_service_code(service_code_key),
    CONSTRAINT FK_dim_charge_master_facility_key FOREIGN KEY (facility_key) REFERENCES dw.dim_facility(facility_key)
);
GO

-- A kind of gap or finding (coverage_inactive, unsigned_note, no_authorization ...).
CREATE TABLE dw.dim_finding_type (
    finding_type_key INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_dim_finding_type PRIMARY KEY,
    tenant_id INT NOT NULL,
    finding_code NVARCHAR(50) NOT NULL,  -- Gap kind
    agent_key INT NULL,  -- Agent that raises it
    category NVARCHAR(100) NULL,  -- eligibility, authorization, documentation, coding, claim, payment, patient, enrollment
    severity_rank TINYINT NULL,  -- 1 worst
    default_action_type_key INT NULL,  -- Usual action
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_dim_finding_type_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_dim_finding_type_bk UNIQUE (tenant_id, finding_code),
    CONSTRAINT FK_dim_finding_type_agent_key FOREIGN KEY (agent_key) REFERENCES dw.dim_agent(agent_key),
    CONSTRAINT FK_dim_finding_type_default_action_type_key FOREIGN KEY (default_action_type_key) REFERENCES dw.dim_action_type(action_type_key)
);
GO

-- 1 APPOINTMENT | Journey solo fact | build tier 1
-- GRAIN: One appointment version (a move or reschedule makes a new row).
-- Built from: appointment
CREATE TABLE dw.fact_appointment (
    appointment_fact_key BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_fact_appointment PRIMARY KEY,
    tenant_id INT NOT NULL,
    appointment_ref NVARCHAR(50) NOT NULL,  -- The practice system's appointment id
    version_seq SMALLINT NOT NULL,  -- 1, 2 ... for each reschedule
    appointment_date_key INT NULL,  -- Visit date
    booked_date_key INT NULL,  -- Date booked
    patient_key INT NULL,  -- Patient (hash)
    provider_key INT NULL,  -- Scheduled provider
    facility_key INT NULL,  -- Location
    primary_payer_key INT NULL,  -- Payer on the booking
    status_key INT NULL,  -- Appointment status
    source_system_key INT NULL,  -- How it reached us
    planned_service_key INT NULL,  -- Planned procedure
    start_time TIME(0) NULL,  -- Start time
    lead_days SMALLINT NULL,  -- Booked-to-visit days
    appointment_count TINYINT NULL,  -- Always 1
    appointment_type_key INT NULL,  -- Why the patient is coming
    primary_coverage_key INT NULL,  -- Primary policy on the booking
    cancel_reason_key INT NULL,  -- Cancellation reason (domain cancel_reason)
    cancelled_date_key INT NULL,  -- Date cancelled
    is_cancelled BIT NULL,  -- Cancelled
    is_no_show BIT NULL,  -- Did not attend
    booked_via NVARCHAR(20) NULL,  -- phone, portal, walk_in, referral
    event_key BIGINT NULL,  -- lineage: event.id
    known_at DATETIME2(0) NOT NULL,  -- point in time
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_fact_appointment_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_appointment_nk UNIQUE (tenant_id, appointment_ref, version_seq),
    CONSTRAINT FK_fact_appointment_appointment_date_key FOREIGN KEY (appointment_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_appointment_booked_date_key FOREIGN KEY (booked_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_appointment_patient_key FOREIGN KEY (patient_key) REFERENCES dw.dim_patient(patient_key),
    CONSTRAINT FK_fact_appointment_provider_key FOREIGN KEY (provider_key) REFERENCES dw.dim_provider(provider_key),
    CONSTRAINT FK_fact_appointment_facility_key FOREIGN KEY (facility_key) REFERENCES dw.dim_facility(facility_key),
    CONSTRAINT FK_fact_appointment_primary_payer_key FOREIGN KEY (primary_payer_key) REFERENCES dw.dim_payer(payer_key),
    CONSTRAINT FK_fact_appointment_status_key FOREIGN KEY (status_key) REFERENCES dw.dim_status(status_key),
    CONSTRAINT FK_fact_appointment_source_system_key FOREIGN KEY (source_system_key) REFERENCES dw.dim_source_system(source_system_key),
    CONSTRAINT FK_fact_appointment_planned_service_key FOREIGN KEY (planned_service_key) REFERENCES dw.dim_service_code(service_code_key),
    CONSTRAINT FK_fact_appointment_appointment_type_key FOREIGN KEY (appointment_type_key) REFERENCES dw.dim_appointment_type(appointment_type_key),
    CONSTRAINT FK_fact_appointment_primary_coverage_key FOREIGN KEY (primary_coverage_key) REFERENCES dw.dim_coverage(coverage_key),
    CONSTRAINT FK_fact_appointment_cancel_reason_key FOREIGN KEY (cancel_reason_key) REFERENCES dw.dim_status(status_key),
    CONSTRAINT FK_fact_appointment_cancelled_date_key FOREIGN KEY (cancelled_date_key) REFERENCES dw.dim_date(date_key)
);
GO

-- 1 APPOINTMENT | Agent table A1 Gatekeeper | build tier 1
-- GRAIN: One eligibility inquiry (270/271) for one coverage on one appointment at one check (booking, 3-day, 1-day).
-- Built from: eligibility_response
CREATE TABLE dw.fact_eligibility_check (
    eligibility_check_fact_key BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_fact_eligibility_check PRIMARY KEY,
    tenant_id INT NOT NULL,
    appointment_ref NVARCHAR(50) NOT NULL,  -- Appointment checked
    check_kind NVARCHAR(20) NOT NULL,  -- booking, recheck_3d, recheck_1d, manual
    check_seq SMALLINT NOT NULL,  -- Repeat counter
    trace_number NVARCHAR(50) NOT NULL,  -- TRN of the 270/271
    check_date_key INT NULL,  -- Date asked
    service_date_key INT NULL,  -- Date of service asked about
    patient_key INT NULL,  -- Patient
    coverage_key INT NOT NULL,  -- Policy checked
    payer_key INT NULL,  -- Payer asked
    other_payer_key INT NULL,  -- Payer the answer says is primary
    plan_begin_date_key INT NULL,  -- Plan start
    plan_end_date_key INT NULL,  -- Plan end
    channel_key INT NULL,  -- x12_edi, portal ...
    is_active BIT NULL,  -- Coverage active
    is_dependent_query BIT NULL,  -- Asked at dependent level (HL 23)
    is_aaa_reject BIT NULL,  -- Payer could not find the member
    copay_amount DECIMAL(12,2) NULL,  -- EB*B copay
    coinsurance_pct DECIMAL(5,4) NULL,  -- EB*A coinsurance as a fraction
    deductible_remaining DECIMAL(12,2) NULL,  -- EB*C deductible left
    response_ms INT NULL,  -- 270 to 271 round trip
    auth_required_flag BIT NULL,  -- Answer says authorization is required
    source_system_key INT NULL,  -- where the row came from
    event_key BIGINT NULL,  -- lineage: event.id
    known_at DATETIME2(0) NOT NULL,  -- point in time
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_fact_eligibility_check_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_eligibility_check_nk UNIQUE (tenant_id, appointment_ref, coverage_key, check_kind, check_seq),
    CONSTRAINT FK_fact_eligibility_check_check_date_key FOREIGN KEY (check_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_eligibility_check_service_date_key FOREIGN KEY (service_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_eligibility_check_patient_key FOREIGN KEY (patient_key) REFERENCES dw.dim_patient(patient_key),
    CONSTRAINT FK_fact_eligibility_check_coverage_key FOREIGN KEY (coverage_key) REFERENCES dw.dim_coverage(coverage_key),
    CONSTRAINT FK_fact_eligibility_check_payer_key FOREIGN KEY (payer_key) REFERENCES dw.dim_payer(payer_key),
    CONSTRAINT FK_fact_eligibility_check_other_payer_key FOREIGN KEY (other_payer_key) REFERENCES dw.dim_payer(payer_key),
    CONSTRAINT FK_fact_eligibility_check_plan_begin_date_key FOREIGN KEY (plan_begin_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_eligibility_check_plan_end_date_key FOREIGN KEY (plan_end_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_eligibility_check_channel_key FOREIGN KEY (channel_key) REFERENCES dw.dim_channel(channel_key),
    CONSTRAINT FK_fact_eligibility_check_source_system_key FOREIGN KEY (source_system_key) REFERENCES dw.dim_source_system(source_system_key)
);
GO

-- 1 APPOINTMENT | Agent table A2 Permit Clerk | build tier 1
-- GRAIN: One service line on one prior-authorization request version (278 SV1/SV2). Header facts (request id, dates) repeat on its lines.
-- Built from: prior_authorization
CREATE TABLE dw.fact_auth_request_line (
    auth_request_line_fact_key BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_fact_auth_request_line PRIMARY KEY,
    tenant_id INT NOT NULL,
    auth_request_ref NVARCHAR(50) NOT NULL,  -- Our request reference
    request_version SMALLINT NOT NULL,  -- Initial 1, then extension, revision, cancel
    line_number SMALLINT NOT NULL,  -- Line within the request
    payer_auth_number NVARCHAR(50) NOT NULL,  -- Number the payer issued
    appointment_ref NVARCHAR(50) NOT NULL,  -- Appointment the request is for
    patient_key INT NULL,  -- Patient
    payer_key INT NULL,  -- Payer asked
    coverage_key INT NULL,  -- Policy
    requesting_provider_key INT NULL,  -- Requesting provider
    rendering_provider_key INT NULL,  -- Rendering provider
    service_code_key INT NULL,  -- Procedure asked for
    primary_diagnosis_key INT NULL,  -- Principal diagnosis
    pos_key INT NULL,  -- Place of service
    requested_date_key INT NULL,  -- Date requested
    decided_date_key INT NULL,  -- Date decided
    valid_from_date_key INT NULL,  -- Approved from
    valid_to_date_key INT NULL,  -- Approved to
    status_key INT NULL,  -- Request status (requested, pended, certified, modified, not_certified, cancelled, expired)
    channel_key INT NULL,  -- How it was submitted
    rule_key INT NULL,  -- Rule that said auth was required
    review_action_code NVARCHAR(20) NULL,  -- HCR01 action: A1, A3, A4, A6 ...
    units_requested INT NULL,  -- Units asked
    units_approved INT NULL,  -- Units certified
    units_used INT NULL,  -- Units consumed as of known_at
    turnaround_days SMALLINT NULL,  -- Request to decision
    authorization_key INT NULL,  -- Authorization record this request produced
    service_from_date_key INT NULL,  -- Service window start
    service_to_date_key INT NULL,  -- Service window end
    facility_key INT NULL,  -- Location
    urgency NVARCHAR(20) NULL,  -- standard, expedited
    decision_reason_code NVARCHAR(20) NULL,  -- Reason the payer gave
    encounter_ref NVARCHAR(50) NOT NULL,  -- Journey link: the encounter
    source_system_key INT NULL,  -- where the row came from
    event_key BIGINT NULL,  -- lineage: event.id
    known_at DATETIME2(0) NOT NULL,  -- point in time
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_fact_auth_request_line_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_auth_request_line_nk UNIQUE (tenant_id, auth_request_ref, line_number, request_version),
    CONSTRAINT FK_fact_auth_request_line_patient_key FOREIGN KEY (patient_key) REFERENCES dw.dim_patient(patient_key),
    CONSTRAINT FK_fact_auth_request_line_payer_key FOREIGN KEY (payer_key) REFERENCES dw.dim_payer(payer_key),
    CONSTRAINT FK_fact_auth_request_line_coverage_key FOREIGN KEY (coverage_key) REFERENCES dw.dim_coverage(coverage_key),
    CONSTRAINT FK_fact_auth_request_line_requesting_provider_key FOREIGN KEY (requesting_provider_key) REFERENCES dw.dim_provider(provider_key),
    CONSTRAINT FK_fact_auth_request_line_rendering_provider_key FOREIGN KEY (rendering_provider_key) REFERENCES dw.dim_provider(provider_key),
    CONSTRAINT FK_fact_auth_request_line_service_code_key FOREIGN KEY (service_code_key) REFERENCES dw.dim_service_code(service_code_key),
    CONSTRAINT FK_fact_auth_request_line_primary_diagnosis_key FOREIGN KEY (primary_diagnosis_key) REFERENCES dw.dim_diagnosis(diagnosis_key),
    CONSTRAINT FK_fact_auth_request_line_pos_key FOREIGN KEY (pos_key) REFERENCES dw.dim_place_of_service(place_of_service_key),
    CONSTRAINT FK_fact_auth_request_line_requested_date_key FOREIGN KEY (requested_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_auth_request_line_decided_date_key FOREIGN KEY (decided_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_auth_request_line_valid_from_date_key FOREIGN KEY (valid_from_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_auth_request_line_valid_to_date_key FOREIGN KEY (valid_to_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_auth_request_line_status_key FOREIGN KEY (status_key) REFERENCES dw.dim_status(status_key),
    CONSTRAINT FK_fact_auth_request_line_channel_key FOREIGN KEY (channel_key) REFERENCES dw.dim_channel(channel_key),
    CONSTRAINT FK_fact_auth_request_line_rule_key FOREIGN KEY (rule_key) REFERENCES dw.dim_rule(rule_key),
    CONSTRAINT FK_fact_auth_request_line_authorization_key FOREIGN KEY (authorization_key) REFERENCES dw.dim_authorization(authorization_key),
    CONSTRAINT FK_fact_auth_request_line_service_from_date_key FOREIGN KEY (service_from_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_auth_request_line_service_to_date_key FOREIGN KEY (service_to_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_auth_request_line_facility_key FOREIGN KEY (facility_key) REFERENCES dw.dim_facility(facility_key),
    CONSTRAINT FK_fact_auth_request_line_source_system_key FOREIGN KEY (source_system_key) REFERENCES dw.dim_source_system(source_system_key)
);
GO

-- 2 ENCOUNTER | Journey solo fact | build tier 1
-- GRAIN: One service line performed at one encounter (visit). The solo fact of phase 2: no billed money yet.
-- Built from: visit; visit_note; appointment
CREATE TABLE dw.fact_encounter (
    encounter_fact_key BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_fact_encounter PRIMARY KEY,
    tenant_id INT NOT NULL,
    encounter_ref NVARCHAR(50) NOT NULL,  -- Visit id
    line_number SMALLINT NOT NULL,  -- Service line within the encounter
    emr_encounter_id NVARCHAR(50) NULL,  -- EMR encounter id
    appointment_ref NVARCHAR(50) NULL,  -- Journey link: appointment it came from (blank for a walk-in)
    appointment_version SMALLINT NULL,  -- Appointment version
    encounter_date_key INT NULL,  -- Date of service
    patient_key INT NULL,  -- Patient
    rendering_provider_key INT NULL,  -- Provider who saw the patient
    supervising_provider_key INT NULL,  -- Supervising provider
    facility_key INT NULL,  -- Location
    pos_key INT NULL,  -- Place of service
    payer_key INT NULL,  -- Primary payer
    coverage_key INT NULL,  -- Primary policy
    appointment_type_key INT NULL,  -- Visit type
    service_code_key INT NULL,  -- Procedure performed
    planned_service_key INT NULL,  -- Procedure planned at booking
    modifier_1_key INT NULL,  -- Modifier 1
    modifier_2_key INT NULL,  -- Modifier 2
    primary_diagnosis_key INT NULL,  -- Principal diagnosis
    encounter_status_key INT NULL,  -- Encounter status (domain encounter_status): in_progress, completed, note_pending, signed, charge_ready
    note_key INT NULL,  -- Documentation of this encounter
    authorization_key INT NULL,  -- Authorization this service relies on
    visit_kind NVARCHAR(20) NULL,  -- new, established, preventive, emergency, telehealth
    diagnosis_pointer VARCHAR(4) NULL,  -- A-L pointers
    laterality CHAR(1) NULL,  -- L, R, B
    gfe_ref NVARCHAR(50) NULL,  -- Good faith estimate reference
    mdm_problem_level NVARCHAR(20) NULL,  -- Medical decision making: problems
    mdm_data_level NVARCHAR(20) NULL,  -- Medical decision making: data
    mdm_risk_level NVARCHAR(20) NULL,  -- Medical decision making: risk
    units DECIMAL(7,2) NULL,  -- Units performed
    service_minutes SMALLINT NULL,  -- Minutes for timed codes
    total_time_minutes SMALLINT NULL,  -- Total encounter time
    signature_lag_days SMALLINT NULL,  -- Visit to signed note
    elements_documented TINYINT NULL,  -- Note elements present
    elements_required TINYINT NULL,  -- Note elements the level needs
    hpi_component_count SMALLINT NULL,  -- History of present illness components
    ros_system_count SMALLINT NULL,  -- Review of systems count
    encounter_line_count TINYINT NULL,  -- Always 1
    source_system_key INT NULL,  -- where the row came from
    event_key BIGINT NULL,  -- lineage: event.id
    known_at DATETIME2(0) NOT NULL,  -- point in time
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_fact_encounter_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_encounter_nk UNIQUE (tenant_id, encounter_ref, line_number),
    CONSTRAINT FK_fact_encounter_encounter_date_key FOREIGN KEY (encounter_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_encounter_patient_key FOREIGN KEY (patient_key) REFERENCES dw.dim_patient(patient_key),
    CONSTRAINT FK_fact_encounter_rendering_provider_key FOREIGN KEY (rendering_provider_key) REFERENCES dw.dim_provider(provider_key),
    CONSTRAINT FK_fact_encounter_supervising_provider_key FOREIGN KEY (supervising_provider_key) REFERENCES dw.dim_provider(provider_key),
    CONSTRAINT FK_fact_encounter_facility_key FOREIGN KEY (facility_key) REFERENCES dw.dim_facility(facility_key),
    CONSTRAINT FK_fact_encounter_pos_key FOREIGN KEY (pos_key) REFERENCES dw.dim_place_of_service(place_of_service_key),
    CONSTRAINT FK_fact_encounter_payer_key FOREIGN KEY (payer_key) REFERENCES dw.dim_payer(payer_key),
    CONSTRAINT FK_fact_encounter_coverage_key FOREIGN KEY (coverage_key) REFERENCES dw.dim_coverage(coverage_key),
    CONSTRAINT FK_fact_encounter_appointment_type_key FOREIGN KEY (appointment_type_key) REFERENCES dw.dim_appointment_type(appointment_type_key),
    CONSTRAINT FK_fact_encounter_service_code_key FOREIGN KEY (service_code_key) REFERENCES dw.dim_service_code(service_code_key),
    CONSTRAINT FK_fact_encounter_planned_service_key FOREIGN KEY (planned_service_key) REFERENCES dw.dim_service_code(service_code_key),
    CONSTRAINT FK_fact_encounter_modifier_1_key FOREIGN KEY (modifier_1_key) REFERENCES dw.dim_modifier(modifier_key),
    CONSTRAINT FK_fact_encounter_modifier_2_key FOREIGN KEY (modifier_2_key) REFERENCES dw.dim_modifier(modifier_key),
    CONSTRAINT FK_fact_encounter_primary_diagnosis_key FOREIGN KEY (primary_diagnosis_key) REFERENCES dw.dim_diagnosis(diagnosis_key),
    CONSTRAINT FK_fact_encounter_encounter_status_key FOREIGN KEY (encounter_status_key) REFERENCES dw.dim_status(status_key),
    CONSTRAINT FK_fact_encounter_note_key FOREIGN KEY (note_key) REFERENCES dw.dim_note(note_key),
    CONSTRAINT FK_fact_encounter_authorization_key FOREIGN KEY (authorization_key) REFERENCES dw.dim_authorization(authorization_key),
    CONSTRAINT FK_fact_encounter_source_system_key FOREIGN KEY (source_system_key) REFERENCES dw.dim_source_system(source_system_key)
);
GO

-- 2 ENCOUNTER | Journey detail | build tier 2
-- GRAIN: Bridge: one diagnosis on one encounter, in order.
-- Built from: claim_dx
CREATE TABLE dw.fact_encounter_dx (
    encounter_dx_fact_key BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_fact_encounter_dx PRIMARY KEY,
    tenant_id INT NOT NULL,
    encounter_ref NVARCHAR(50) NOT NULL,  -- Encounter
    dx_seq TINYINT NOT NULL,  -- Order 1-12
    diagnosis_key INT NULL,  -- Diagnosis
    onset_date_key INT NULL,  -- Onset date
    is_principal BIT NULL,  -- Principal
    source_system_key INT NULL,  -- where the row came from
    event_key BIGINT NULL,  -- lineage: event.id
    known_at DATETIME2(0) NOT NULL,  -- point in time
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_fact_encounter_dx_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_encounter_dx_nk UNIQUE (tenant_id, encounter_ref, dx_seq),
    CONSTRAINT FK_fact_encounter_dx_diagnosis_key FOREIGN KEY (diagnosis_key) REFERENCES dw.dim_diagnosis(diagnosis_key),
    CONSTRAINT FK_fact_encounter_dx_onset_date_key FOREIGN KEY (onset_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_encounter_dx_source_system_key FOREIGN KEY (source_system_key) REFERENCES dw.dim_source_system(source_system_key)
);
GO

-- 2 ENCOUNTER | Agent table A3 Note Chaser | build tier 2
-- GRAIN: One required documentation element on one note (history, exam, assessment, plan, laterality ...). Line level of fact_note.
-- Built from: visit_note.elements
CREATE TABLE dw.fact_note_element (
    note_element_fact_key BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_fact_note_element PRIMARY KEY,
    tenant_id INT NOT NULL,
    note_ref NVARCHAR(50) NOT NULL,  -- Note
    note_version SMALLINT NOT NULL,  -- Version
    element_code NVARCHAR(50) NOT NULL,  -- Element
    rule_key INT NULL,  -- Rule that requires it
    is_required BIT NULL,  -- Required for this service
    is_present BIT NULL,  -- Documented
    source_system_key INT NULL,  -- where the row came from
    event_key BIGINT NULL,  -- lineage: event.id
    known_at DATETIME2(0) NOT NULL,  -- point in time
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_fact_note_element_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_note_element_nk UNIQUE (tenant_id, note_ref, note_version, element_code),
    CONSTRAINT FK_fact_note_element_rule_key FOREIGN KEY (rule_key) REFERENCES dw.dim_rule(rule_key),
    CONSTRAINT FK_fact_note_element_source_system_key FOREIGN KEY (source_system_key) REFERENCES dw.dim_source_system(source_system_key)
);
GO

-- 2 ENCOUNTER | Agent table A3 Note Chaser | build tier 2
-- GRAIN: One order, referral, consent, result or attachment tied to a visit, authorization or claim.
-- Built from: new
CREATE TABLE dw.fact_document (
    document_fact_key BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_fact_document PRIMARY KEY,
    tenant_id INT NOT NULL,
    document_ref NVARCHAR(50) NOT NULL,  -- Document id
    doc_type_key INT NULL,  -- Type
    encounter_ref NVARCHAR(50) NOT NULL,  -- Journey link: encounter
    status_key INT NULL,  -- requested, received, signed, expired
    patient_key INT NULL,  -- Patient
    auth_request_ref NVARCHAR(50) NOT NULL,  -- Authorization
    claim_ref NVARCHAR(50) NOT NULL,  -- Claim
    ordering_provider_key INT NULL,  -- Ordering provider
    document_date_key INT NULL,  -- Document date
    signed_date_key INT NULL,  -- Signed
    valid_from_date_key INT NULL,  -- Valid from
    valid_to_date_key INT NULL,  -- Valid to
    visits_allowed SMALLINT NULL,  -- Referral visits allowed
    visits_used SMALLINT NULL,  -- Referral visits used
    content_hash CHAR(64) NULL,  -- Hash of the document
    channel_key INT NULL,  -- How it moved
    due_date_key INT NULL,  -- Due
    received_date_key INT NULL,  -- Received
    sent_date_key INT NULL,  -- Sent
    page_count SMALLINT NULL,  -- Pages
    payer_key INT NULL,  -- Payer for a records request
    diagnosis_key INT NULL,  -- Diagnosis the document supports
    external_ref NVARCHAR(50) NULL,  -- Payer's request reference
    tracking_ref NVARCHAR(50) NULL,  -- Carrier tracking
    appointment_ref NVARCHAR(50) NOT NULL,  -- Journey link: the appointment
    source_system_key INT NULL,  -- where the row came from
    event_key BIGINT NULL,  -- lineage: event.id
    known_at DATETIME2(0) NOT NULL,  -- point in time
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_fact_document_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_document_nk UNIQUE (tenant_id, document_ref),
    CONSTRAINT FK_fact_document_doc_type_key FOREIGN KEY (doc_type_key) REFERENCES dw.dim_document_type(document_type_key),
    CONSTRAINT FK_fact_document_status_key FOREIGN KEY (status_key) REFERENCES dw.dim_status(status_key),
    CONSTRAINT FK_fact_document_patient_key FOREIGN KEY (patient_key) REFERENCES dw.dim_patient(patient_key),
    CONSTRAINT FK_fact_document_ordering_provider_key FOREIGN KEY (ordering_provider_key) REFERENCES dw.dim_provider(provider_key),
    CONSTRAINT FK_fact_document_document_date_key FOREIGN KEY (document_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_document_signed_date_key FOREIGN KEY (signed_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_document_valid_from_date_key FOREIGN KEY (valid_from_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_document_valid_to_date_key FOREIGN KEY (valid_to_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_document_channel_key FOREIGN KEY (channel_key) REFERENCES dw.dim_channel(channel_key),
    CONSTRAINT FK_fact_document_due_date_key FOREIGN KEY (due_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_document_received_date_key FOREIGN KEY (received_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_document_sent_date_key FOREIGN KEY (sent_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_document_payer_key FOREIGN KEY (payer_key) REFERENCES dw.dim_payer(payer_key),
    CONSTRAINT FK_fact_document_diagnosis_key FOREIGN KEY (diagnosis_key) REFERENCES dw.dim_diagnosis(diagnosis_key),
    CONSTRAINT FK_fact_document_source_system_key FOREIGN KEY (source_system_key) REFERENCES dw.dim_source_system(source_system_key)
);
GO

-- 2 ENCOUNTER | Agent table A4 Code Whisperer | build tier 2
-- GRAIN: One code line compared by the Code Whisperer: billed or documented versus suggested. Line level of a coding review.
-- Built from: decision_record.action_payload
CREATE TABLE dw.fact_coding_review_line (
    coding_review_line_fact_key BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_fact_coding_review_line PRIMARY KEY,
    tenant_id INT NOT NULL,
    decision_id BIGINT NOT NULL,  -- Coding review decision
    line_number SMALLINT NOT NULL,  -- Line
    encounter_ref NVARCHAR(50) NOT NULL,  -- Visit
    billed_code_key INT NULL,  -- Code as billed or entered
    suggested_code_key INT NULL,  -- Code suggested
    suggested_dx_key INT NULL,  -- Diagnosis suggested
    finding_type_key INT NULL,  -- over_coded, under_coded, missing_modifier ...
    final_code_key INT NULL,  -- Code after the coder's decision
    coder_staff_key INT NULL,  -- Named coder
    decision_status_key INT NULL,  -- accepted, changed, declined
    billed_units DECIMAL(7,2) NULL,  -- Units billed
    suggested_units DECIMAL(7,2) NULL,  -- Units suggested
    dollar_difference DECIMAL(12,2) NULL,  -- Suggested minus billed at contract rate
    is_compliance_risk BIT NULL,  -- Over-coding risk
    source_system_key INT NULL,  -- where the row came from
    event_key BIGINT NULL,  -- lineage: event.id
    known_at DATETIME2(0) NOT NULL,  -- point in time
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_fact_coding_review_line_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_coding_review_line_nk UNIQUE (tenant_id, decision_id, line_number),
    CONSTRAINT FK_fact_coding_review_line_billed_code_key FOREIGN KEY (billed_code_key) REFERENCES dw.dim_service_code(service_code_key),
    CONSTRAINT FK_fact_coding_review_line_suggested_code_key FOREIGN KEY (suggested_code_key) REFERENCES dw.dim_service_code(service_code_key),
    CONSTRAINT FK_fact_coding_review_line_suggested_dx_key FOREIGN KEY (suggested_dx_key) REFERENCES dw.dim_diagnosis(diagnosis_key),
    CONSTRAINT FK_fact_coding_review_line_finding_type_key FOREIGN KEY (finding_type_key) REFERENCES dw.dim_finding_type(finding_type_key),
    CONSTRAINT FK_fact_coding_review_line_final_code_key FOREIGN KEY (final_code_key) REFERENCES dw.dim_service_code(service_code_key),
    CONSTRAINT FK_fact_coding_review_line_coder_staff_key FOREIGN KEY (coder_staff_key) REFERENCES dw.dim_staff(staff_key),
    CONSTRAINT FK_fact_coding_review_line_decision_status_key FOREIGN KEY (decision_status_key) REFERENCES dw.dim_status(status_key),
    CONSTRAINT FK_fact_coding_review_line_source_system_key FOREIGN KEY (source_system_key) REFERENCES dw.dim_source_system(source_system_key)
);
GO

-- 3 BILL | Journey solo fact | build tier 1
-- GRAIN: One service line on one claim (version). The solo fact of phase 3: billed amount appears here for the first time = units x the practice fee list. Claim header attributes repeat on each line.
-- Built from: claim_line; claim; charge; fee_schedule
CREATE TABLE dw.fact_bill (
    bill_fact_key BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_fact_bill PRIMARY KEY,
    tenant_id INT NOT NULL,
    claim_ref NVARCHAR(50) NOT NULL,  -- Our claim id
    frequency_code CHAR(1) NOT NULL,  -- 1 original, 7 replacement, 8 void
    line_number SMALLINT NOT NULL,  -- Line
    payer_claim_control_number NVARCHAR(50) NOT NULL,  -- Payer's claim number
    encounter_ref NVARCHAR(50) NOT NULL,  -- Journey link: encounter billed
    encounter_line_number SMALLINT NOT NULL,  -- Journey link: encounter line billed
    charge_ref NVARCHAR(50) NOT NULL,  -- Charge id in the practice system
    service_date_key INT NULL,  -- Date of service
    charge_entered_date_key INT NULL,  -- Charge entered
    submitted_date_key INT NULL,  -- Date sent
    target_send_date_key INT NULL,  -- Planned send date
    accident_date_key INT NULL,  -- Accident date
    patient_key INT NULL,  -- Patient
    billing_provider_key INT NULL,  -- Billing provider
    rendering_provider_key INT NULL,  -- Rendering provider
    supervising_provider_key INT NULL,  -- Supervising provider
    payer_key INT NULL,  -- Payer billed
    coverage_key INT NULL,  -- Policy billed
    pos_key INT NULL,  -- Place of service
    service_code_key INT NULL,  -- Procedure billed
    modifier_1_key INT NULL,  -- Modifier 1
    modifier_2_key INT NULL,  -- Modifier 2
    modifier_3_key INT NULL,  -- Modifier 3
    modifier_4_key INT NULL,  -- Modifier 4
    primary_diagnosis_key INT NULL,  -- Diagnosis the first pointer points to
    authorization_key INT NULL,  -- Authorization on the claim (REF*G1)
    charge_master_key INT NULL,  -- Fee list row used to price the line
    contract_rate_key INT NULL,  -- Contract rate used for the expected amount
    claim_status_key INT NULL,  -- Claim lifecycle status (domain claim_lifecycle): drafted, held, ready, sent, accepted, rejected, paid, denied, closed
    charge_entered_by_staff_key INT NULL,  -- Entered by
    diagnosis_pointer VARCHAR(4) NULL,  -- A-L pointers
    unit_basis CHAR(2) NULL,  -- UN, MJ
    laterality CHAR(1) NULL,  -- L, R, B
    prior_auth_number NVARCHAR(50) NULL,  -- REF*G1
    hold_reason NVARCHAR(50) NULL,  -- Why the charge is held
    filing_exception_code NVARCHAR(50) NULL,  -- Late filing exception
    accident_related_code NVARCHAR(20) NULL,  -- Accident type
    consent_flags NVARCHAR(20) NULL,  -- Assignment and release flags
    claim_content_hash BINARY(32) NULL,  -- Hash of the claim as sent
    isa13 NVARCHAR(9) NULL,  -- Interchange control number
    gs06 NVARCHAR(9) NULL,  -- Group control number
    st02 NVARCHAR(9) NULL,  -- Set control number
    ndc_code NVARCHAR(11) NULL,  -- Drug code
    line_indicators NVARCHAR(30) NULL,  -- Emergency, EPSDT, family planning
    units DECIMAL(7,2) NULL,  -- Units billed
    fee_per_unit DECIMAL(12,2) NULL,  -- Fee from the practice fee list
    billed_amount DECIMAL(12,2) NULL,  -- Billed = units x fee_per_unit
    expected_allowed DECIMAL(12,2) NULL,  -- Contract allowed when billed
    ndc_units DECIMAL(12,3) NULL,  -- Drug units
    claim_total_charge DECIMAL(12,2) NULL,  -- Claim total repeated on each line: do not sum across lines
    charge_lag_days SMALLINT NULL,  -- Service to charge entry
    line_count TINYINT NULL,  -- Always 1
    source_system_key INT NULL,  -- where the row came from
    event_key BIGINT NULL,  -- lineage: event.id
    known_at DATETIME2(0) NOT NULL,  -- point in time
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_fact_bill_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_bill_nk UNIQUE (tenant_id, claim_ref, frequency_code, line_number),
    CONSTRAINT FK_fact_bill_service_date_key FOREIGN KEY (service_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_bill_charge_entered_date_key FOREIGN KEY (charge_entered_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_bill_submitted_date_key FOREIGN KEY (submitted_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_bill_target_send_date_key FOREIGN KEY (target_send_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_bill_accident_date_key FOREIGN KEY (accident_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_bill_patient_key FOREIGN KEY (patient_key) REFERENCES dw.dim_patient(patient_key),
    CONSTRAINT FK_fact_bill_billing_provider_key FOREIGN KEY (billing_provider_key) REFERENCES dw.dim_provider(provider_key),
    CONSTRAINT FK_fact_bill_rendering_provider_key FOREIGN KEY (rendering_provider_key) REFERENCES dw.dim_provider(provider_key),
    CONSTRAINT FK_fact_bill_supervising_provider_key FOREIGN KEY (supervising_provider_key) REFERENCES dw.dim_provider(provider_key),
    CONSTRAINT FK_fact_bill_payer_key FOREIGN KEY (payer_key) REFERENCES dw.dim_payer(payer_key),
    CONSTRAINT FK_fact_bill_coverage_key FOREIGN KEY (coverage_key) REFERENCES dw.dim_coverage(coverage_key),
    CONSTRAINT FK_fact_bill_pos_key FOREIGN KEY (pos_key) REFERENCES dw.dim_place_of_service(place_of_service_key),
    CONSTRAINT FK_fact_bill_service_code_key FOREIGN KEY (service_code_key) REFERENCES dw.dim_service_code(service_code_key),
    CONSTRAINT FK_fact_bill_modifier_1_key FOREIGN KEY (modifier_1_key) REFERENCES dw.dim_modifier(modifier_key),
    CONSTRAINT FK_fact_bill_modifier_2_key FOREIGN KEY (modifier_2_key) REFERENCES dw.dim_modifier(modifier_key),
    CONSTRAINT FK_fact_bill_modifier_3_key FOREIGN KEY (modifier_3_key) REFERENCES dw.dim_modifier(modifier_key),
    CONSTRAINT FK_fact_bill_modifier_4_key FOREIGN KEY (modifier_4_key) REFERENCES dw.dim_modifier(modifier_key),
    CONSTRAINT FK_fact_bill_primary_diagnosis_key FOREIGN KEY (primary_diagnosis_key) REFERENCES dw.dim_diagnosis(diagnosis_key),
    CONSTRAINT FK_fact_bill_authorization_key FOREIGN KEY (authorization_key) REFERENCES dw.dim_authorization(authorization_key),
    CONSTRAINT FK_fact_bill_charge_master_key FOREIGN KEY (charge_master_key) REFERENCES dw.dim_charge_master(charge_master_key),
    CONSTRAINT FK_fact_bill_contract_rate_key FOREIGN KEY (contract_rate_key) REFERENCES dw.dim_contract_rate(contract_rate_key),
    CONSTRAINT FK_fact_bill_claim_status_key FOREIGN KEY (claim_status_key) REFERENCES dw.dim_status(status_key),
    CONSTRAINT FK_fact_bill_charge_entered_by_staff_key FOREIGN KEY (charge_entered_by_staff_key) REFERENCES dw.dim_staff(staff_key),
    CONSTRAINT FK_fact_bill_source_system_key FOREIGN KEY (source_system_key) REFERENCES dw.dim_source_system(source_system_key)
);
GO

-- 3 BILL | Journey detail | build tier 2
-- GRAIN: Bridge: one diagnosis on one claim in order.
-- Built from: claim_dx
CREATE TABLE dw.fact_bill_dx (
    bill_dx_fact_key BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_fact_bill_dx PRIMARY KEY,
    tenant_id INT NOT NULL,
    claim_ref NVARCHAR(50) NOT NULL,  -- Claim
    frequency_code CHAR(1) NOT NULL,  -- Claim version
    dx_seq TINYINT NOT NULL,  -- Order 1-12
    diagnosis_key INT NULL,  -- Diagnosis
    onset_date_key INT NULL,  -- Onset date
    is_principal BIT NULL,  -- Principal (qualifier ABK)
    source_system_key INT NULL,  -- where the row came from
    event_key BIGINT NULL,  -- lineage: event.id
    known_at DATETIME2(0) NOT NULL,  -- point in time
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_fact_bill_dx_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_bill_dx_nk UNIQUE (tenant_id, claim_ref, frequency_code, dx_seq),
    CONSTRAINT FK_fact_bill_dx_diagnosis_key FOREIGN KEY (diagnosis_key) REFERENCES dw.dim_diagnosis(diagnosis_key),
    CONSTRAINT FK_fact_bill_dx_onset_date_key FOREIGN KEY (onset_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_bill_dx_source_system_key FOREIGN KEY (source_system_key) REFERENCES dw.dim_source_system(source_system_key)
);
GO

-- 3 BILL | Agent table A6 Courier | build tier 2
-- GRAIN: One acknowledgement or status event for one claim: 837 sent, 999, 277CA, 276/277 answer, resubmission.
-- Built from: ack_277ca; ack_999
CREATE TABLE dw.fact_claim_status_event (
    claim_status_event_fact_key BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_fact_claim_status_event PRIMARY KEY,
    tenant_id INT NOT NULL,
    claim_ref NVARCHAR(50) NOT NULL,  -- Claim
    event_type NVARCHAR(20) NOT NULL,  -- sent, ack_999, ack_277ca, status_277, resubmitted
    event_ref NVARCHAR(50) NOT NULL,  -- Control number of the file or message
    event_date_key INT NULL,  -- Date
    claim_status_key INT NULL,  -- Status
    ack_code_key INT NULL,  -- 999 result
    channel_key INT NULL,  -- Route
    payer_key INT NULL,  -- Payer
    rejection_owner_role_key INT NULL,  -- Role that fixes it
    payer_claim_number NVARCHAR(50) NULL,  -- Payer claim number
    charge_amount DECIMAL(12,2) NULL,  -- Charge on the status
    seconds_since_sent INT NULL,  -- Sent to this event
    acked_control_ref NVARCHAR(100) NULL,  -- Control numbers a 999 acknowledges
    pend_reason_code NVARCHAR(30) NULL,  -- Coded pend reason
    reported_paid_amount DECIMAL(12,2) NULL,  -- Paid amount stated on a status answer
    encounter_ref NVARCHAR(50) NOT NULL,  -- Journey link: the encounter
    source_system_key INT NULL,  -- where the row came from
    event_key BIGINT NULL,  -- lineage: event.id
    known_at DATETIME2(0) NOT NULL,  -- point in time
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_fact_claim_status_event_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_claim_status_event_nk UNIQUE (tenant_id, claim_ref, event_type, event_ref),
    CONSTRAINT FK_fact_claim_status_event_event_date_key FOREIGN KEY (event_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_claim_status_event_claim_status_key FOREIGN KEY (claim_status_key) REFERENCES dw.dim_claim_status(claim_status_key),
    CONSTRAINT FK_fact_claim_status_event_ack_code_key FOREIGN KEY (ack_code_key) REFERENCES dw.dim_ack_code(ack_code_key),
    CONSTRAINT FK_fact_claim_status_event_channel_key FOREIGN KEY (channel_key) REFERENCES dw.dim_channel(channel_key),
    CONSTRAINT FK_fact_claim_status_event_payer_key FOREIGN KEY (payer_key) REFERENCES dw.dim_payer(payer_key),
    CONSTRAINT FK_fact_claim_status_event_rejection_owner_role_key FOREIGN KEY (rejection_owner_role_key) REFERENCES dw.dim_role(role_key),
    CONSTRAINT FK_fact_claim_status_event_source_system_key FOREIGN KEY (source_system_key) REFERENCES dw.dim_source_system(source_system_key)
);
GO

-- 3 BILL | Agent table A5 Mirror | build tier 2
-- GRAIN: A model's predicted denial for one claim line before it is sent. Predictions stay apart from actual outcomes.
-- Built from: new
CREATE TABLE dw.fact_denial_prediction (
    denial_prediction_fact_key BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_fact_denial_prediction PRIMARY KEY,
    tenant_id INT NOT NULL,
    decision_id BIGINT NOT NULL,  -- Decision that made the prediction
    claim_ref NVARCHAR(50) NOT NULL,  -- Claim
    line_number SMALLINT NOT NULL,  -- Line
    predicted_reason_key INT NULL,  -- Most likely denial reason
    simulated_outcome NVARCHAR(20) NULL,  -- paid, denied, partial
    predicted_denial_probability DECIMAL(5,4) NULL,  -- 0-1
    simulated_allowed_amount DECIMAL(12,2) NULL,  -- Allowed in the simulation
    simulated_patient_responsibility DECIMAL(12,2) NULL,  -- Patient share in the simulation
    source_system_key INT NULL,  -- where the row came from
    event_key BIGINT NULL,  -- lineage: event.id
    known_at DATETIME2(0) NOT NULL,  -- point in time
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_fact_denial_prediction_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_denial_prediction_nk UNIQUE (tenant_id, decision_id, claim_ref, line_number),
    CONSTRAINT FK_fact_denial_prediction_predicted_reason_key FOREIGN KEY (predicted_reason_key) REFERENCES dw.dim_adjustment_reason(adjustment_reason_key),
    CONSTRAINT FK_fact_denial_prediction_source_system_key FOREIGN KEY (source_system_key) REFERENCES dw.dim_source_system(source_system_key)
);
GO

-- 4 TRANSACTIONS, DENIALS, AR | Journey detail | build tier 3
-- GRAIN: One 835 payment: the EFT or check.
-- Built from: payment
CREATE TABLE dw.fact_payment (
    payment_fact_key BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_fact_payment PRIMARY KEY,
    tenant_id INT NOT NULL,
    trace_number NVARCHAR(50) NOT NULL,  -- BPR/TRN trace
    payer_key INT NULL,  -- Payer
    payment_date_key INT NULL,  -- Payment date
    channel_key INT NULL,  -- EFT, check, virtual card
    credit_debit CHAR(1) NULL,  -- C or D
    payment_amount DECIMAL(12,2) NULL,  -- Amount
    plb_adjustment_total DECIMAL(12,2) NULL,  -- Provider-level adjustments
    handling_code CHAR(2) NULL,  -- BPR handling
    payment_format_code CHAR(3) NULL,  -- BPR format
    originator_supplemental_code NVARCHAR(50) NULL,  -- Originator supplemental code
    payee_provider_key INT NULL,  -- Payee
    payer_bank_account_key INT NULL,  -- Payer's bank account
    practice_bank_account_key INT NULL,  -- Practice's bank account
    source_system_key INT NULL,  -- where the row came from
    event_key BIGINT NULL,  -- lineage: event.id
    known_at DATETIME2(0) NOT NULL,  -- point in time
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_fact_payment_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_payment_nk UNIQUE (tenant_id, trace_number),
    CONSTRAINT FK_fact_payment_payer_key FOREIGN KEY (payer_key) REFERENCES dw.dim_payer(payer_key),
    CONSTRAINT FK_fact_payment_payment_date_key FOREIGN KEY (payment_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_payment_channel_key FOREIGN KEY (channel_key) REFERENCES dw.dim_channel(channel_key),
    CONSTRAINT FK_fact_payment_payee_provider_key FOREIGN KEY (payee_provider_key) REFERENCES dw.dim_provider(provider_key),
    CONSTRAINT FK_fact_payment_payer_bank_account_key FOREIGN KEY (payer_bank_account_key) REFERENCES dw.dim_bank_account(bank_account_key),
    CONSTRAINT FK_fact_payment_practice_bank_account_key FOREIGN KEY (practice_bank_account_key) REFERENCES dw.dim_bank_account(bank_account_key),
    CONSTRAINT FK_fact_payment_source_system_key FOREIGN KEY (source_system_key) REFERENCES dw.dim_source_system(source_system_key)
);
GO

-- 4 TRANSACTIONS, DENIALS, AR | Journey solo fact | build tier 1
-- GRAIN: One payer transaction on one bill line (835 service line): billed, allowed, paid and patient share. The solo fact of phase 4.
-- Built from: remit_line
CREATE TABLE dw.fact_transaction_line (
    transaction_line_fact_key BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_fact_transaction_line PRIMARY KEY,
    tenant_id INT NOT NULL,
    trace_number NVARCHAR(50) NOT NULL,  -- Payment
    claim_ref NVARCHAR(50) NOT NULL,  -- Claim
    line_number SMALLINT NOT NULL,  -- Line
    payer_claim_control_number NVARCHAR(50) NOT NULL,  -- Payer claim number
    payment_date_key INT NULL,  -- Payment date
    service_date_key INT NULL,  -- Service date
    payer_key INT NULL,  -- Payer
    patient_key INT NULL,  -- Patient
    service_code_key INT NULL,  -- Procedure paid
    modifier_1_key INT NULL,  -- Modifier 1
    claim_status_key INT NULL,  -- CLP02 claim status
    match_method NVARCHAR(20) NULL,  -- How the line was matched to the claim line
    units DECIMAL(7,2) NULL,  -- Units paid
    charge_amount DECIMAL(12,2) NULL,  -- Billed
    allowed_amount DECIMAL(12,2) NULL,  -- Allowed
    paid_amount DECIMAL(12,2) NULL,  -- Paid
    patient_responsibility DECIMAL(12,2) NULL,  -- Patient share
    contract_expected DECIMAL(12,2) NULL,  -- Contract allowed for this line
    underpayment_amount DECIMAL(12,2) NULL,  -- Contract expected minus paid plus patient share when positive
    encounter_ref NVARCHAR(50) NOT NULL,  -- Journey link: encounter
    encounter_line_number SMALLINT NOT NULL,  -- Journey link: encounter line
    contract_rate_key INT NULL,  -- Contract rate used for the expected amount
    source_system_key INT NULL,  -- where the row came from
    event_key BIGINT NULL,  -- lineage: event.id
    known_at DATETIME2(0) NOT NULL,  -- point in time
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_fact_transaction_line_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_transaction_line_nk UNIQUE (tenant_id, trace_number, claim_ref, line_number),
    CONSTRAINT FK_fact_transaction_line_payment_date_key FOREIGN KEY (payment_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_transaction_line_service_date_key FOREIGN KEY (service_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_transaction_line_payer_key FOREIGN KEY (payer_key) REFERENCES dw.dim_payer(payer_key),
    CONSTRAINT FK_fact_transaction_line_patient_key FOREIGN KEY (patient_key) REFERENCES dw.dim_patient(patient_key),
    CONSTRAINT FK_fact_transaction_line_service_code_key FOREIGN KEY (service_code_key) REFERENCES dw.dim_service_code(service_code_key),
    CONSTRAINT FK_fact_transaction_line_modifier_1_key FOREIGN KEY (modifier_1_key) REFERENCES dw.dim_modifier(modifier_key),
    CONSTRAINT FK_fact_transaction_line_claim_status_key FOREIGN KEY (claim_status_key) REFERENCES dw.dim_claim_status(claim_status_key),
    CONSTRAINT FK_fact_transaction_line_contract_rate_key FOREIGN KEY (contract_rate_key) REFERENCES dw.dim_contract_rate(contract_rate_key),
    CONSTRAINT FK_fact_transaction_line_source_system_key FOREIGN KEY (source_system_key) REFERENCES dw.dim_source_system(source_system_key)
);
GO

-- 4 TRANSACTIONS, DENIALS, AR | Journey detail | build tier 3
-- GRAIN: One adjustment on one transaction line (CAS): contractual, patient, or denial. A denial is an adjustment whose reason is flagged is_denial (see vw_denial_line).
-- Built from: adjustment
CREATE TABLE dw.fact_adjustment (
    adjustment_fact_key BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_fact_adjustment PRIMARY KEY,
    tenant_id INT NOT NULL,
    trace_number NVARCHAR(50) NOT NULL,  -- Payment
    claim_ref NVARCHAR(50) NOT NULL,  -- Claim
    line_number SMALLINT NOT NULL,  -- Line, 0 for claim level
    seq TINYINT NOT NULL,  -- Adjustment order
    payment_date_key INT NULL,  -- Payment date
    payer_key INT NULL,  -- Payer
    adjustment_reason_key INT NULL,  -- CARC
    remark_code_key INT NULL,  -- RARC
    service_code_key INT NULL,  -- Procedure
    group_code CHAR(2) NULL,  -- CO, PR, OA, PI, CR
    adjustment_amount DECIMAL(12,2) NULL,  -- Amount
    adjustment_quantity DECIMAL(7,2) NULL,  -- Units adjusted
    source_system_key INT NULL,  -- where the row came from
    event_key BIGINT NULL,  -- lineage: event.id
    known_at DATETIME2(0) NOT NULL,  -- point in time
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_fact_adjustment_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_adjustment_nk UNIQUE (tenant_id, trace_number, claim_ref, line_number, seq),
    CONSTRAINT FK_fact_adjustment_payment_date_key FOREIGN KEY (payment_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_adjustment_payer_key FOREIGN KEY (payer_key) REFERENCES dw.dim_payer(payer_key),
    CONSTRAINT FK_fact_adjustment_adjustment_reason_key FOREIGN KEY (adjustment_reason_key) REFERENCES dw.dim_adjustment_reason(adjustment_reason_key),
    CONSTRAINT FK_fact_adjustment_remark_code_key FOREIGN KEY (remark_code_key) REFERENCES dw.dim_remark_code(remark_code_key),
    CONSTRAINT FK_fact_adjustment_service_code_key FOREIGN KEY (service_code_key) REFERENCES dw.dim_service_code(service_code_key),
    CONSTRAINT FK_fact_adjustment_source_system_key FOREIGN KEY (source_system_key) REFERENCES dw.dim_source_system(source_system_key)
);
GO

-- 4 TRANSACTIONS, DENIALS, AR | Journey detail | build tier 3
-- GRAIN: Periodic snapshot: one open claim on one as-of date.
-- Built from: ar_snapshot
CREATE TABLE dw.fact_ar_snapshot (
    ar_snapshot_fact_key BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_fact_ar_snapshot PRIMARY KEY,
    tenant_id INT NOT NULL,
    claim_ref NVARCHAR(50) NOT NULL,  -- Claim
    as_of_date_key INT NOT NULL,  -- Snapshot date
    payer_key INT NULL,  -- Payer
    provider_key INT NULL,  -- Provider
    aging_bucket NVARCHAR(20) NULL,  -- 0-30, 31-60, 61-90, 91-120, 120+
    balance DECIMAL(12,2) NULL,  -- Open balance
    days_outstanding SMALLINT NULL,  -- Age
    patient_balance DECIMAL(12,2) NULL,  -- Patient share still open
    secondary_expected_amount DECIMAL(12,2) NULL,  -- Expected from the next payer
    source_system_key INT NULL,  -- where the row came from
    event_key BIGINT NULL,  -- lineage: event.id
    known_at DATETIME2(0) NOT NULL,  -- point in time
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_fact_ar_snapshot_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_ar_snapshot_nk UNIQUE (tenant_id, claim_ref, as_of_date_key),
    CONSTRAINT FK_fact_ar_snapshot_as_of_date_key FOREIGN KEY (as_of_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_ar_snapshot_payer_key FOREIGN KEY (payer_key) REFERENCES dw.dim_payer(payer_key),
    CONSTRAINT FK_fact_ar_snapshot_provider_key FOREIGN KEY (provider_key) REFERENCES dw.dim_provider(provider_key),
    CONSTRAINT FK_fact_ar_snapshot_source_system_key FOREIGN KEY (source_system_key) REFERENCES dw.dim_source_system(source_system_key)
);
GO

-- 4 TRANSACTIONS, DENIALS, AR | Agent table A8 Advocate | build tier 3
-- GRAIN: One step on one appeal or dispute (denial appeal, underpayment dispute). New: no appeal table exists.
-- Built from: new
CREATE TABLE dw.fact_appeal_event (
    appeal_event_fact_key BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_fact_appeal_event PRIMARY KEY,
    tenant_id INT NOT NULL,
    appeal_ref NVARCHAR(50) NOT NULL,  -- Appeal id
    event_seq SMALLINT NOT NULL,  -- Step
    claim_ref NVARCHAR(50) NOT NULL,  -- Claim
    line_number SMALLINT NOT NULL,  -- Line
    appeal_type_key INT NULL,  -- denial_appeal, underpayment_dispute, reconsideration
    status_key INT NULL,  -- drafted, approved, sent, won, lost, expired
    adjustment_reason_key INT NULL,  -- Reason appealed
    payer_key INT NULL,  -- Payer
    event_date_key INT NULL,  -- Date
    deadline_date_key INT NULL,  -- Deadline
    channel_key INT NULL,  -- Route
    amount_disputed DECIMAL(12,2) NULL,  -- Disputed
    amount_recovered DECIMAL(12,2) NULL,  -- Recovered
    clock_start_date_key INT NULL,  -- Date the appeal clock starts (denial notice)
    payer_reference VARCHAR(50) NULL,  -- Payer's appeal reference
    evidence_count SMALLINT NULL,  -- Documents attached
    letter_hash BINARY(32) NULL,  -- Hash of the letter
    source_system_key INT NULL,  -- where the row came from
    event_key BIGINT NULL,  -- lineage: event.id
    known_at DATETIME2(0) NOT NULL,  -- point in time
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_fact_appeal_event_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_appeal_event_nk UNIQUE (tenant_id, appeal_ref, event_seq),
    CONSTRAINT FK_fact_appeal_event_appeal_type_key FOREIGN KEY (appeal_type_key) REFERENCES dw.dim_status(status_key),
    CONSTRAINT FK_fact_appeal_event_status_key FOREIGN KEY (status_key) REFERENCES dw.dim_status(status_key),
    CONSTRAINT FK_fact_appeal_event_adjustment_reason_key FOREIGN KEY (adjustment_reason_key) REFERENCES dw.dim_adjustment_reason(adjustment_reason_key),
    CONSTRAINT FK_fact_appeal_event_payer_key FOREIGN KEY (payer_key) REFERENCES dw.dim_payer(payer_key),
    CONSTRAINT FK_fact_appeal_event_event_date_key FOREIGN KEY (event_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_appeal_event_deadline_date_key FOREIGN KEY (deadline_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_appeal_event_channel_key FOREIGN KEY (channel_key) REFERENCES dw.dim_channel(channel_key),
    CONSTRAINT FK_fact_appeal_event_clock_start_date_key FOREIGN KEY (clock_start_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_appeal_event_source_system_key FOREIGN KEY (source_system_key) REFERENCES dw.dim_source_system(source_system_key)
);
GO

-- 4 TRANSACTIONS, DENIALS, AR | Cash and payments | build tier 3
-- GRAIN: One bank deposit line.
-- Built from: bank_deposit
CREATE TABLE dw.fact_bank_deposit (
    bank_deposit_fact_key BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_fact_bank_deposit PRIMARY KEY,
    tenant_id INT NOT NULL,
    deposit_ref NVARCHAR(50) NOT NULL,  -- Deposit id
    trace_ref NVARCHAR(50) NOT NULL,  -- Trace carried by the bank
    deposit_date_key INT NULL,  -- Date
    payer_key INT NULL,  -- Payer if known
    channel_key INT NULL,  -- ACH, check, lockbox
    deposit_amount DECIMAL(12,2) NULL,  -- Amount
    matched_payment_note NVARCHAR(50) NULL,  -- Matched trace_number, blank if unmatched
    bank_item_ref NVARCHAR(50) NOT NULL,  -- Bank's item reference
    match_method NVARCHAR(20) NULL,  -- How the deposit was matched to a payment
    funds_availability_code NVARCHAR(20) NULL,  -- When funds are available
    bank_account_key INT NULL,  -- Account deposited to
    source_system_key INT NULL,  -- where the row came from
    event_key BIGINT NULL,  -- lineage: event.id
    known_at DATETIME2(0) NOT NULL,  -- point in time
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_fact_bank_deposit_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_bank_deposit_nk UNIQUE (tenant_id, deposit_ref),
    CONSTRAINT FK_fact_bank_deposit_deposit_date_key FOREIGN KEY (deposit_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_bank_deposit_payer_key FOREIGN KEY (payer_key) REFERENCES dw.dim_payer(payer_key),
    CONSTRAINT FK_fact_bank_deposit_channel_key FOREIGN KEY (channel_key) REFERENCES dw.dim_channel(channel_key),
    CONSTRAINT FK_fact_bank_deposit_bank_account_key FOREIGN KEY (bank_account_key) REFERENCES dw.dim_bank_account(bank_account_key),
    CONSTRAINT FK_fact_bank_deposit_source_system_key FOREIGN KEY (source_system_key) REFERENCES dw.dim_source_system(source_system_key)
);
GO

-- 4 TRANSACTIONS, DENIALS, AR | Cash and payments | build tier 3
-- GRAIN: One posting in the practice system for a payment.
-- Built from: posting
CREATE TABLE dw.fact_posting (
    posting_fact_key BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_fact_posting PRIMARY KEY,
    tenant_id INT NOT NULL,
    posting_ref NVARCHAR(50) NOT NULL,  -- Posting id
    payment_trace NVARCHAR(50) NOT NULL,  -- Payment posted
    claim_ref NVARCHAR(50) NOT NULL,  -- Claim
    posted_date_key INT NULL,  -- Posted
    posted_by_role_key INT NULL,  -- Role
    posted_amount DECIMAL(12,2) NULL,  -- Amount posted
    days_to_post SMALLINT NULL,  -- Payment to posting
    line_number SMALLINT NOT NULL,  -- Line posted to
    batch_ref NVARCHAR(50) NULL,  -- Posting batch
    posting_method NVARCHAR(20) NULL,  -- manual, auto, era
    is_unapplied BIT NULL,  -- Held unapplied
    is_reversal BIT NULL,  -- Reverses a posting
    contractual_adjustment_amount DECIMAL(12,2) NULL,  -- Contractual write-down posted
    patient_transfer_amount DECIMAL(12,2) NULL,  -- Moved to patient
    source_system_key INT NULL,  -- where the row came from
    event_key BIGINT NULL,  -- lineage: event.id
    known_at DATETIME2(0) NOT NULL,  -- point in time
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_fact_posting_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_posting_nk UNIQUE (tenant_id, posting_ref),
    CONSTRAINT FK_fact_posting_posted_date_key FOREIGN KEY (posted_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_posting_posted_by_role_key FOREIGN KEY (posted_by_role_key) REFERENCES dw.dim_role(role_key),
    CONSTRAINT FK_fact_posting_source_system_key FOREIGN KEY (source_system_key) REFERENCES dw.dim_source_system(source_system_key)
);
GO

-- 4 TRANSACTIONS, DENIALS, AR | Cash and payments | build tier 3
-- GRAIN: One patient payment or statement on a claim's patient share.
-- Built from: patient_payment; patient_statement
CREATE TABLE dw.fact_patient_balance_event (
    patient_balance_event_fact_key BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_fact_patient_balance_event PRIMARY KEY,
    tenant_id INT NOT NULL,
    event_ref NVARCHAR(50) NOT NULL,  -- Payment or statement id
    claim_ref NVARCHAR(50) NOT NULL,  -- Claim
    event_type NVARCHAR(20) NOT NULL,  -- statement, payment, refund, adjustment
    event_date_key INT NULL,  -- Date
    channel_key INT NULL,  -- Statement channel or payment method
    status_key INT NULL,  -- Statement status
    patient_key INT NULL,  -- Patient
    amount DECIMAL(12,2) NULL,  -- Amount
    reason_code NVARCHAR(50) NULL,  -- Reason for the event
    due_date_key INT NULL,  -- Due date
    counterparty_ref NVARCHAR(100) NULL,  -- Who the event is with (role or reference)
    notice_seq SMALLINT NULL,  -- Statement notice number
    applied_line_number SMALLINT NULL,  -- Bill line the payment applies to
    template_ref NVARCHAR(50) NULL,  -- Statement template
    source_system_key INT NULL,  -- where the row came from
    event_key BIGINT NULL,  -- lineage: event.id
    known_at DATETIME2(0) NOT NULL,  -- point in time
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_fact_patient_balance_event_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_patient_balance_event_nk UNIQUE (tenant_id, event_ref),
    CONSTRAINT FK_fact_patient_balance_event_event_date_key FOREIGN KEY (event_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_patient_balance_event_channel_key FOREIGN KEY (channel_key) REFERENCES dw.dim_channel(channel_key),
    CONSTRAINT FK_fact_patient_balance_event_status_key FOREIGN KEY (status_key) REFERENCES dw.dim_status(status_key),
    CONSTRAINT FK_fact_patient_balance_event_patient_key FOREIGN KEY (patient_key) REFERENCES dw.dim_patient(patient_key),
    CONSTRAINT FK_fact_patient_balance_event_due_date_key FOREIGN KEY (due_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_patient_balance_event_source_system_key FOREIGN KEY (source_system_key) REFERENCES dw.dim_source_system(source_system_key)
);
GO

-- 4 TRANSACTIONS, DENIALS, AR | Cash and payments | build tier 3
-- GRAIN: One provider-level adjustment on a payment (PLB): interest, takeback, recoupment, withhold.
-- Built from: plb_adjustment
CREATE TABLE dw.fact_plb_adjustment (
    plb_adjustment_fact_key BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_fact_plb_adjustment PRIMARY KEY,
    tenant_id INT NOT NULL,
    trace_number NVARCHAR(50) NOT NULL,  -- Payment
    plb_seq TINYINT NOT NULL,  -- Order
    provider_key INT NULL,  -- Provider
    fiscal_period_date_key INT NULL,  -- Fiscal period date
    plb_reason_code VARCHAR(10) NULL,  -- PLB reason
    reference_id VARCHAR(50) NULL,  -- Reference
    amount DECIMAL(12,2) NULL,  -- Amount
    source_system_key INT NULL,  -- where the row came from
    event_key BIGINT NULL,  -- lineage: event.id
    known_at DATETIME2(0) NOT NULL,  -- point in time
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_fact_plb_adjustment_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_plb_adjustment_nk UNIQUE (tenant_id, trace_number, plb_seq),
    CONSTRAINT FK_fact_plb_adjustment_provider_key FOREIGN KEY (provider_key) REFERENCES dw.dim_provider(provider_key),
    CONSTRAINT FK_fact_plb_adjustment_fiscal_period_date_key FOREIGN KEY (fiscal_period_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_plb_adjustment_source_system_key FOREIGN KEY (source_system_key) REFERENCES dw.dim_source_system(source_system_key)
);
GO

-- 4 TRANSACTIONS, DENIALS, AR | Cash and payments | build tier 3
-- GRAIN: One event on a patient payment plan: set up, instalment, missed, completed.
-- Built from: new
CREATE TABLE dw.fact_payment_plan (
    payment_plan_fact_key BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_fact_payment_plan PRIMARY KEY,
    tenant_id INT NOT NULL,
    plan_ref NVARCHAR(50) NOT NULL,  -- Plan id
    event_seq SMALLINT NOT NULL,  -- Order of events
    claim_ref NVARCHAR(50) NOT NULL,  -- Claim
    patient_key INT NULL,  -- Patient
    status_key INT NULL,  -- active, missed, completed, cancelled
    event_date_key INT NULL,  -- Date
    first_due_date_key INT NULL,  -- First instalment due
    next_due_date_key INT NULL,  -- Next instalment due
    missed_date_key INT NULL,  -- Date missed
    installment_amount DECIMAL(12,2) NULL,  -- Amount per instalment
    installment_count SMALLINT NULL,  -- Number of instalments
    source_system_key INT NULL,  -- where the row came from
    event_key BIGINT NULL,  -- lineage: event.id
    known_at DATETIME2(0) NOT NULL,  -- point in time
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_fact_payment_plan_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_payment_plan_nk UNIQUE (tenant_id, plan_ref, event_seq),
    CONSTRAINT FK_fact_payment_plan_patient_key FOREIGN KEY (patient_key) REFERENCES dw.dim_patient(patient_key),
    CONSTRAINT FK_fact_payment_plan_status_key FOREIGN KEY (status_key) REFERENCES dw.dim_status(status_key),
    CONSTRAINT FK_fact_payment_plan_event_date_key FOREIGN KEY (event_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_payment_plan_first_due_date_key FOREIGN KEY (first_due_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_payment_plan_next_due_date_key FOREIGN KEY (next_due_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_payment_plan_missed_date_key FOREIGN KEY (missed_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_payment_plan_source_system_key FOREIGN KEY (source_system_key) REFERENCES dw.dim_source_system(source_system_key)
);
GO

-- ALL PHASES | Agent spine | build tier 1
-- GRAIN: One agent decision record: one agent run on one event. The shared spine of the work layer.
-- Built from: decision_record
CREATE TABLE dw.fact_agent_decision (
    agent_decision_fact_key BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_fact_agent_decision PRIMARY KEY,
    tenant_id INT NOT NULL,
    decision_id BIGINT NOT NULL,  -- decision_record.id
    event_ref NVARCHAR(50) NOT NULL,  -- Triggering event
    subject_type NVARCHAR(20) NOT NULL,  -- appointment, claim, claim_line, visit, payment, enrollment, patient_account ...
    subject_ref NVARCHAR(50) NOT NULL,  -- Id of the thing decided about
    agent_key INT NOT NULL,  -- Agent
    action_type_key INT NOT NULL,  -- Proposed action
    context_key INT NULL,  -- Autonomy level, mode, outcome
    decision_date_key INT NULL,  -- Date decided
    owner_role_key INT NULL,  -- Role that must act
    approver_staff_key INT NULL,  -- Named approver
    approved_date_key INT NULL,  -- Date approved or rejected
    payer_key INT NULL,  -- Payer the decision concerns
    patient_key INT NULL,  -- Patient the decision concerns
    provider_key INT NULL,  -- Provider the decision concerns
    agent_version NVARCHAR(20) NULL,  -- Version that decided
    model_id NVARCHAR(100) NULL,  -- Model used, if any
    prompt_hash CHAR(64) NULL,  -- Prompt hash
    materiality_amount DECIMAL(12,2) NULL,  -- Dollars at stake
    confidence DECIMAL(5,4) NULL,  -- 0-1
    is_executed BIT NULL,  -- An action actually ran
    verification_condition NVARCHAR(500) NULL,  -- What must be true afterwards
    verification_result NVARCHAR(500) NULL,  -- Whether it held
    decision_count TINYINT NULL,  -- Always 1
    phase_code TINYINT NULL,  -- Journey phase the decision belongs to: 1 appointment, 2 encounter, 3 bill, 4 transactions
    appointment_ref NVARCHAR(50) NOT NULL,  -- Journey link: the appointment
    encounter_ref NVARCHAR(50) NOT NULL,  -- Journey link: the encounter
    claim_ref NVARCHAR(50) NOT NULL,  -- Journey link: the claim
    due_date_key INT NULL,  -- Deadline of the card or action
    priority_score DECIMAL(12,4) NULL,  -- Rank score on the work card
    trigger_type NVARCHAR(40) NULL,  -- What started the decision
    sla_class NVARCHAR(20) NULL,  -- Service level class
    model_version VARCHAR(40) NULL,  -- Model version
    input_snapshot_hash BINARY(32) NULL,  -- Hash of the input snapshot
    run_cost_amount DECIMAL(12,2) NULL,  -- Cost of the run
    token_count INT NULL,  -- Tokens used
    source_system_key INT NULL,  -- where the row came from
    event_key BIGINT NULL,  -- lineage: event.id
    known_at DATETIME2(0) NOT NULL,  -- point in time
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_fact_agent_decision_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_agent_decision_nk UNIQUE (tenant_id, event_ref, agent_key, action_type_key),
    CONSTRAINT FK_fact_agent_decision_agent_key FOREIGN KEY (agent_key) REFERENCES dw.dim_agent(agent_key),
    CONSTRAINT FK_fact_agent_decision_action_type_key FOREIGN KEY (action_type_key) REFERENCES dw.dim_action_type(action_type_key),
    CONSTRAINT FK_fact_agent_decision_context_key FOREIGN KEY (context_key) REFERENCES dw.dim_decision_context(decision_context_key),
    CONSTRAINT FK_fact_agent_decision_decision_date_key FOREIGN KEY (decision_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_agent_decision_owner_role_key FOREIGN KEY (owner_role_key) REFERENCES dw.dim_role(role_key),
    CONSTRAINT FK_fact_agent_decision_approver_staff_key FOREIGN KEY (approver_staff_key) REFERENCES dw.dim_staff(staff_key),
    CONSTRAINT FK_fact_agent_decision_approved_date_key FOREIGN KEY (approved_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_agent_decision_payer_key FOREIGN KEY (payer_key) REFERENCES dw.dim_payer(payer_key),
    CONSTRAINT FK_fact_agent_decision_patient_key FOREIGN KEY (patient_key) REFERENCES dw.dim_patient(patient_key),
    CONSTRAINT FK_fact_agent_decision_provider_key FOREIGN KEY (provider_key) REFERENCES dw.dim_provider(provider_key),
    CONSTRAINT FK_fact_agent_decision_due_date_key FOREIGN KEY (due_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_agent_decision_source_system_key FOREIGN KEY (source_system_key) REFERENCES dw.dim_source_system(source_system_key)
);
GO

-- ALL PHASES | Agent spine | build tier 1
-- GRAIN: One rule evaluated inside one decision (rules fired, passed or failed).
-- Built from: decision_record.rules_fired
CREATE TABLE dw.fact_decision_rule_result (
    decision_rule_result_fact_key BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_fact_decision_rule_result PRIMARY KEY,
    tenant_id INT NOT NULL,
    decision_id BIGINT NOT NULL,  -- Parent decision
    rule_key INT NOT NULL,  -- Rule
    agent_key INT NULL,  -- Agent
    passed BIT NULL,  -- Rule result as the agent defines it (check the sign per rule)
    is_blocking BIT NULL,  -- A failure stops execution
    detail NVARCHAR(500) NULL,  -- Plain explanation
    source_system_key INT NULL,  -- where the row came from
    event_key BIGINT NULL,  -- lineage: event.id
    known_at DATETIME2(0) NOT NULL,  -- point in time
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_fact_decision_rule_result_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_decision_rule_result_nk UNIQUE (tenant_id, decision_id, rule_key),
    CONSTRAINT FK_fact_decision_rule_result_rule_key FOREIGN KEY (rule_key) REFERENCES dw.dim_rule(rule_key),
    CONSTRAINT FK_fact_decision_rule_result_agent_key FOREIGN KEY (agent_key) REFERENCES dw.dim_agent(agent_key),
    CONSTRAINT FK_fact_decision_rule_result_source_system_key FOREIGN KEY (source_system_key) REFERENCES dw.dim_source_system(source_system_key)
);
GO

-- ALL PHASES | Agent spine | build tier 1
-- GRAIN: One gap or finding raised on one thing at one check: unsigned note, no authorization, inactive coverage, unmatched deposit ...
-- Built from: decision_record.action_payload
CREATE TABLE dw.fact_finding (
    finding_fact_key BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_fact_finding PRIMARY KEY,
    tenant_id INT NOT NULL,
    finding_type_key INT NOT NULL,  -- Kind of gap
    agent_key INT NULL,  -- Agent
    subject_type NVARCHAR(20) NOT NULL,  -- What the gap is on
    subject_ref NVARCHAR(50) NOT NULL,  -- Id of that thing
    check_date_key INT NOT NULL,  -- Date found
    closed_date_key INT NULL,  -- Date it cleared (closing event)
    payer_key INT NULL,  -- Payer
    provider_key INT NULL,  -- Provider
    patient_key INT NULL,  -- Patient
    owner_role_key INT NULL,  -- Role that owns it
    decision_id BIGINT NOT NULL,  -- Decision record
    detail NVARCHAR(500) NULL,  -- Plain explanation
    days_open SMALLINT NULL,  -- Check date to closed date
    dollars_at_risk DECIMAL(12,2) NULL,  -- Amount exposed
    is_open BIT NULL,  -- Still open
    phase_code TINYINT NULL,  -- Journey phase
    appointment_ref NVARCHAR(50) NOT NULL,  -- Journey link: the appointment
    encounter_ref NVARCHAR(50) NOT NULL,  -- Journey link: the encounter
    claim_ref NVARCHAR(50) NOT NULL,  -- Journey link: the claim
    resolution_type NVARCHAR(30) NULL,  -- How it was resolved
    occurrence_count SMALLINT NULL,  -- Times raised
    deadline_date_key INT NULL,  -- Deadline
    adjustment_reason_key INT NULL,  -- Related denial reason
    recoverability NVARCHAR(20) NULL,  -- likely, possible, unlikely
    pricing_basis NVARCHAR(20) NULL,  -- How the amount was priced
    gold_label NVARCHAR(20) NULL,  -- Answer-key label in tests
    source_system_key INT NULL,  -- where the row came from
    event_key BIGINT NULL,  -- lineage: event.id
    known_at DATETIME2(0) NOT NULL,  -- point in time
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_fact_finding_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_finding_nk UNIQUE (tenant_id, finding_type_key, subject_type, subject_ref, check_date_key),
    CONSTRAINT FK_fact_finding_finding_type_key FOREIGN KEY (finding_type_key) REFERENCES dw.dim_finding_type(finding_type_key),
    CONSTRAINT FK_fact_finding_agent_key FOREIGN KEY (agent_key) REFERENCES dw.dim_agent(agent_key),
    CONSTRAINT FK_fact_finding_check_date_key FOREIGN KEY (check_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_finding_closed_date_key FOREIGN KEY (closed_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_finding_payer_key FOREIGN KEY (payer_key) REFERENCES dw.dim_payer(payer_key),
    CONSTRAINT FK_fact_finding_provider_key FOREIGN KEY (provider_key) REFERENCES dw.dim_provider(provider_key),
    CONSTRAINT FK_fact_finding_patient_key FOREIGN KEY (patient_key) REFERENCES dw.dim_patient(patient_key),
    CONSTRAINT FK_fact_finding_owner_role_key FOREIGN KEY (owner_role_key) REFERENCES dw.dim_role(role_key),
    CONSTRAINT FK_fact_finding_deadline_date_key FOREIGN KEY (deadline_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_finding_adjustment_reason_key FOREIGN KEY (adjustment_reason_key) REFERENCES dw.dim_adjustment_reason(adjustment_reason_key),
    CONSTRAINT FK_fact_finding_source_system_key FOREIGN KEY (source_system_key) REFERENCES dw.dim_source_system(source_system_key)
);
GO

-- ALL PHASES | Agent spine | build tier 1
-- GRAIN: One status change on one work task (opened, assigned, worked, escalated, closed). New: no task table exists today.
-- Built from: new
CREATE TABLE dw.fact_work_task_event (
    work_task_event_fact_key BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_fact_work_task_event PRIMARY KEY,
    tenant_id INT NOT NULL,
    task_ref NVARCHAR(50) NOT NULL,  -- Task id
    event_seq SMALLINT NOT NULL,  -- Order of the change
    decision_id BIGINT NOT NULL,  -- Decision that created the task
    action_type_key INT NULL,  -- Kind of task
    status_key INT NULL,  -- Task status after this event
    assigned_role_key INT NULL,  -- Role
    assigned_staff_key INT NULL,  -- Person
    event_date_key INT NULL,  -- Date of change
    due_date_key INT NULL,  -- Due date
    channel_key INT NULL,  -- Where the task lives (EMR task, queue, email)
    event_ts DATETIME2(0) NULL,  -- Exact time
    minutes_spent SMALLINT NULL,  -- Work time logged
    reminder_count TINYINT NULL,  -- Reminders sent
    escalation_level TINYINT NULL,  -- 0 none
    outcome_code NVARCHAR(50) NULL,  -- Coded outcome of the task
    assigned_by_staff_key INT NULL,  -- Assigned by
    rework_reason NVARCHAR(100) NULL,  -- Why it was reopened
    snoozed_until_date_key INT NULL,  -- Snoozed until
    promised_pay_date_key INT NULL,  -- Date the payer promised payment
    payer_contact_ref NVARCHAR(50) NULL,  -- Payer contact reference (no personal name)
    source_system_key INT NULL,  -- where the row came from
    event_key BIGINT NULL,  -- lineage: event.id
    known_at DATETIME2(0) NOT NULL,  -- point in time
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_fact_work_task_event_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_work_task_event_nk UNIQUE (tenant_id, task_ref, event_seq),
    CONSTRAINT FK_fact_work_task_event_action_type_key FOREIGN KEY (action_type_key) REFERENCES dw.dim_action_type(action_type_key),
    CONSTRAINT FK_fact_work_task_event_status_key FOREIGN KEY (status_key) REFERENCES dw.dim_status(status_key),
    CONSTRAINT FK_fact_work_task_event_assigned_role_key FOREIGN KEY (assigned_role_key) REFERENCES dw.dim_role(role_key),
    CONSTRAINT FK_fact_work_task_event_assigned_staff_key FOREIGN KEY (assigned_staff_key) REFERENCES dw.dim_staff(staff_key),
    CONSTRAINT FK_fact_work_task_event_event_date_key FOREIGN KEY (event_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_work_task_event_due_date_key FOREIGN KEY (due_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_work_task_event_channel_key FOREIGN KEY (channel_key) REFERENCES dw.dim_channel(channel_key),
    CONSTRAINT FK_fact_work_task_event_assigned_by_staff_key FOREIGN KEY (assigned_by_staff_key) REFERENCES dw.dim_staff(staff_key),
    CONSTRAINT FK_fact_work_task_event_snoozed_until_date_key FOREIGN KEY (snoozed_until_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_work_task_event_promised_pay_date_key FOREIGN KEY (promised_pay_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_work_task_event_source_system_key FOREIGN KEY (source_system_key) REFERENCES dw.dim_source_system(source_system_key)
);
GO

-- ALL PHASES | Agent spine | build tier 1
-- GRAIN: One approval decision by a named person (maker-checker).
-- Built from: approval_request
CREATE TABLE dw.fact_approval (
    approval_fact_key BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_fact_approval PRIMARY KEY,
    tenant_id INT NOT NULL,
    approval_ref NVARCHAR(50) NOT NULL,  -- Approval request id
    decision_id BIGINT NOT NULL,  -- Decision approved
    status_key INT NULL,  -- pending, approved, rejected
    approver_role_key INT NULL,  -- Role required
    decided_by_staff_key INT NULL,  -- Person
    decided_date_key INT NULL,  -- Date
    reason NVARCHAR(500) NULL,  -- Reason or comment
    hours_to_decision DECIMAL(8,2) NULL,  -- Request to decision
    batch_ref NVARCHAR(50) NULL,  -- Batch approved together
    feedback_label NVARCHAR(30) NULL,  -- false_positive, override, correct
    finding_code VARCHAR(30) NULL,  -- Reviewer finding
    second_approver_staff_key INT NULL,  -- Second approver
    source_system_key INT NULL,  -- where the row came from
    event_key BIGINT NULL,  -- lineage: event.id
    known_at DATETIME2(0) NOT NULL,  -- point in time
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_fact_approval_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_approval_nk UNIQUE (tenant_id, approval_ref),
    CONSTRAINT FK_fact_approval_status_key FOREIGN KEY (status_key) REFERENCES dw.dim_status(status_key),
    CONSTRAINT FK_fact_approval_approver_role_key FOREIGN KEY (approver_role_key) REFERENCES dw.dim_role(role_key),
    CONSTRAINT FK_fact_approval_decided_by_staff_key FOREIGN KEY (decided_by_staff_key) REFERENCES dw.dim_staff(staff_key),
    CONSTRAINT FK_fact_approval_decided_date_key FOREIGN KEY (decided_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_approval_second_approver_staff_key FOREIGN KEY (second_approver_staff_key) REFERENCES dw.dim_staff(staff_key),
    CONSTRAINT FK_fact_approval_source_system_key FOREIGN KEY (source_system_key) REFERENCES dw.dim_source_system(source_system_key)
);
GO

-- ALL PHASES | Agent spine | build tier 1
-- GRAIN: One proposed or sent note/task to the EMR, with who approved it. Notes and tasks only (rule 2).
-- Built from: new
CREATE TABLE dw.fact_writeback (
    writeback_fact_key BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_fact_writeback PRIMARY KEY,
    tenant_id INT NOT NULL,
    writeback_key NVARCHAR(200) NOT NULL,  -- event id | run kind
    decision_id BIGINT NOT NULL,  -- Decision it came from
    status_key INT NULL,  -- proposed, approved, sent, failed
    channel_key INT NULL,  -- emr_message, emr_task
    approver_staff_key INT NULL,  -- Named approver
    proposed_date_key INT NULL,  -- Proposed
    sent_date_key INT NULL,  -- Sent
    emr_message_id NVARCHAR(50) NULL,  -- Id the EMR returned
    title NVARCHAR(250) NULL,  -- Note title
    body_hash BINARY(32) NULL,  -- Hash of the note body: the body is not stored
    recipient_role_key INT NULL,  -- Role the note is for
    source_system_key INT NULL,  -- where the row came from
    event_key BIGINT NULL,  -- lineage: event.id
    known_at DATETIME2(0) NOT NULL,  -- point in time
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_fact_writeback_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_writeback_nk UNIQUE (tenant_id, writeback_key),
    CONSTRAINT FK_fact_writeback_status_key FOREIGN KEY (status_key) REFERENCES dw.dim_status(status_key),
    CONSTRAINT FK_fact_writeback_channel_key FOREIGN KEY (channel_key) REFERENCES dw.dim_channel(channel_key),
    CONSTRAINT FK_fact_writeback_approver_staff_key FOREIGN KEY (approver_staff_key) REFERENCES dw.dim_staff(staff_key),
    CONSTRAINT FK_fact_writeback_proposed_date_key FOREIGN KEY (proposed_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_writeback_sent_date_key FOREIGN KEY (sent_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_writeback_recipient_role_key FOREIGN KEY (recipient_role_key) REFERENCES dw.dim_role(role_key),
    CONSTRAINT FK_fact_writeback_source_system_key FOREIGN KEY (source_system_key) REFERENCES dw.dim_source_system(source_system_key)
);
GO

-- ALL PHASES | Agent spine | build tier 1
-- GRAIN: One detected amount and what was later recovered or confirmed.
-- Built from: new
CREATE TABLE dw.fact_value_ledger (
    value_ledger_fact_key BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_fact_value_ledger PRIMARY KEY,
    tenant_id INT NOT NULL,
    decision_id BIGINT NOT NULL,  -- Decision that detected it
    agent_key INT NULL,  -- Detecting agent
    detected_date_key INT NULL,  -- Detected
    confirmed_date_key INT NULL,  -- Confirmed by payment
    claim_ref NVARCHAR(50) NOT NULL,  -- Claim
    detected_amount DECIMAL(12,2) NULL,  -- Amount detected
    confirmed_amount DECIMAL(12,2) NULL,  -- Later paid
    is_holdout BIT NULL,  -- Held out from action to measure lift
    stage_code VARCHAR(20) NULL,  -- detected, worked, submitted, accepted, paid
    recovery_stage NVARCHAR(20) NULL,  -- Recovery stage
    incremental_amount DECIMAL(12,2) NULL,  -- Recovery above the control group
    source_system_key INT NULL,  -- where the row came from
    event_key BIGINT NULL,  -- lineage: event.id
    known_at DATETIME2(0) NOT NULL,  -- point in time
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_fact_value_ledger_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_value_ledger_nk UNIQUE (tenant_id, decision_id),
    CONSTRAINT FK_fact_value_ledger_agent_key FOREIGN KEY (agent_key) REFERENCES dw.dim_agent(agent_key),
    CONSTRAINT FK_fact_value_ledger_detected_date_key FOREIGN KEY (detected_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_value_ledger_confirmed_date_key FOREIGN KEY (confirmed_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_value_ledger_source_system_key FOREIGN KEY (source_system_key) REFERENCES dw.dim_source_system(source_system_key)
);
GO

-- ALL PHASES | Agent spine | build tier 1
-- GRAIN: One metric value for one slice on one date: the reusable metrics layer (periodic snapshot).
-- Built from: new
CREATE TABLE dw.fact_kpi_value (
    kpi_value_fact_key BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_fact_kpi_value PRIMARY KEY,
    tenant_id INT NOT NULL,
    metric_key INT NOT NULL,  -- Metric
    as_of_date_key INT NOT NULL,  -- Date
    payer_key INT NULL,  -- Slice: payer
    provider_key INT NULL,  -- Slice: provider
    service_code_key INT NULL,  -- Slice: procedure
    agent_key INT NULL,  -- Slice: agent
    slice_hash CHAR(16) NOT NULL,  -- Hash of the slice values
    numerator DECIMAL(16,4) NULL,  -- Numerator
    denominator DECIMAL(16,4) NULL,  -- Denominator
    value DECIMAL(16,4) NULL,  -- Metric value
    pos_key INT NULL,  -- Slice: place of service
    source_system_key INT NULL,  -- where the row came from
    event_key BIGINT NULL,  -- lineage: event.id
    known_at DATETIME2(0) NOT NULL,  -- point in time
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_fact_kpi_value_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_kpi_value_nk UNIQUE (tenant_id, metric_key, as_of_date_key, slice_hash),
    CONSTRAINT FK_fact_kpi_value_metric_key FOREIGN KEY (metric_key) REFERENCES dw.dim_metric(metric_key),
    CONSTRAINT FK_fact_kpi_value_as_of_date_key FOREIGN KEY (as_of_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_kpi_value_payer_key FOREIGN KEY (payer_key) REFERENCES dw.dim_payer(payer_key),
    CONSTRAINT FK_fact_kpi_value_provider_key FOREIGN KEY (provider_key) REFERENCES dw.dim_provider(provider_key),
    CONSTRAINT FK_fact_kpi_value_service_code_key FOREIGN KEY (service_code_key) REFERENCES dw.dim_service_code(service_code_key),
    CONSTRAINT FK_fact_kpi_value_agent_key FOREIGN KEY (agent_key) REFERENCES dw.dim_agent(agent_key),
    CONSTRAINT FK_fact_kpi_value_pos_key FOREIGN KEY (pos_key) REFERENCES dw.dim_place_of_service(place_of_service_key),
    CONSTRAINT FK_fact_kpi_value_source_system_key FOREIGN KEY (source_system_key) REFERENCES dw.dim_source_system(source_system_key)
);
GO

-- ALL PHASES | Agent spine | build tier 1
-- GRAIN: One forecast day for the 28-day cash forecast, with its range.
-- Built from: new
CREATE TABLE dw.fact_cash_forecast (
    cash_forecast_fact_key BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_fact_cash_forecast PRIMARY KEY,
    tenant_id INT NOT NULL,
    forecast_date_key INT NOT NULL,  -- When forecast was made
    target_date_key INT NOT NULL,  -- Day forecast
    payer_key INT NOT NULL,  -- Payer, null for all
    expected_cash DECIMAL(12,2) NULL,  -- Expected
    low_cash DECIMAL(12,2) NULL,  -- 80% low
    high_cash DECIMAL(12,2) NULL,  -- 80% high
    actual_cash DECIMAL(12,2) NULL,  -- Actual once known
    required_cash DECIMAL(12,2) NULL,  -- Cash needed
    source_system_key INT NULL,  -- where the row came from
    event_key BIGINT NULL,  -- lineage: event.id
    known_at DATETIME2(0) NOT NULL,  -- point in time
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_fact_cash_forecast_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_cash_forecast_nk UNIQUE (tenant_id, forecast_date_key, target_date_key, payer_key),
    CONSTRAINT FK_fact_cash_forecast_forecast_date_key FOREIGN KEY (forecast_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_cash_forecast_target_date_key FOREIGN KEY (target_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_cash_forecast_payer_key FOREIGN KEY (payer_key) REFERENCES dw.dim_payer(payer_key),
    CONSTRAINT FK_fact_cash_forecast_source_system_key FOREIGN KEY (source_system_key) REFERENCES dw.dim_source_system(source_system_key)
);
GO

-- ALL PHASES | Agent spine | build tier 1
-- GRAIN: One reconciliation check of source data against the practice system (opening data-quality checks).
-- Built from: new
CREATE TABLE dw.fact_data_check (
    data_check_fact_key BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_fact_data_check PRIMARY KEY,
    tenant_id INT NOT NULL,
    check_code NVARCHAR(50) NOT NULL,  -- Which check
    run_date_key INT NOT NULL,  -- Run date
    items_compared INT NULL,  -- Items compared
    mismatch_count INT NULL,  -- Mismatches
    max_difference DECIMAL(12,2) NULL,  -- Largest difference
    tolerance DECIMAL(12,2) NULL,  -- Tolerance
    passed BIT NULL,  -- Within tolerance
    source_system_key INT NULL,  -- where the row came from
    event_key BIGINT NULL,  -- lineage: event.id
    known_at DATETIME2(0) NOT NULL,  -- point in time
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_fact_data_check_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_data_check_nk UNIQUE (tenant_id, check_code, run_date_key),
    CONSTRAINT FK_fact_data_check_run_date_key FOREIGN KEY (run_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_data_check_source_system_key FOREIGN KEY (source_system_key) REFERENCES dw.dim_source_system(source_system_key)
);
GO

-- PROVIDER (ALL PHASES) | Agent table A13 Credentialing | build tier 3
-- GRAIN: One enrollment or screening event for a provider and payer.
-- Built from: enrollment; provider_screening
CREATE TABLE dw.fact_enrollment_event (
    enrollment_event_fact_key BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_fact_enrollment_event PRIMARY KEY,
    tenant_id INT NOT NULL,
    enrollment_ref NVARCHAR(50) NOT NULL,  -- Enrollment or screening id
    event_seq SMALLINT NOT NULL,  -- Step
    provider_key INT NULL,  -- Provider
    payer_key INT NULL,  -- Payer
    status_key INT NULL,  -- Enrollment or screening status
    event_date_key INT NULL,  -- Date
    effective_date_key INT NULL,  -- Effective
    expires_date_key INT NULL,  -- Expires or revalidation due
    screening_result NVARCHAR(20) NULL,  -- clear, hit
    screening_source NVARCHAR(100) NULL,  -- List screened
    submitted_date_key INT NULL,  -- Submitted
    enrollment_type NVARCHAR(20) NULL,  -- initial, revalidation, add_location
    payer_provider_id NVARCHAR(50) NULL,  -- Provider id at the payer
    coverage_program NVARCHAR(30) NULL,  -- Program
    application_ref NVARCHAR(50) NULL,  -- Application reference
    status_reason NVARCHAR(200) NULL,  -- Reason for the status
    facility_key INT NULL,  -- Location
    screening_match_method NVARCHAR(20) NULL,  -- How a screening hit was matched
    screened_entity_type NVARCHAR(20) NULL,  -- provider, group
    source_system_key INT NULL,  -- where the row came from
    event_key BIGINT NULL,  -- lineage: event.id
    known_at DATETIME2(0) NOT NULL,  -- point in time
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_fact_enrollment_event_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_enrollment_event_nk UNIQUE (tenant_id, enrollment_ref, event_seq),
    CONSTRAINT FK_fact_enrollment_event_provider_key FOREIGN KEY (provider_key) REFERENCES dw.dim_provider(provider_key),
    CONSTRAINT FK_fact_enrollment_event_payer_key FOREIGN KEY (payer_key) REFERENCES dw.dim_payer(payer_key),
    CONSTRAINT FK_fact_enrollment_event_status_key FOREIGN KEY (status_key) REFERENCES dw.dim_status(status_key),
    CONSTRAINT FK_fact_enrollment_event_event_date_key FOREIGN KEY (event_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_enrollment_event_effective_date_key FOREIGN KEY (effective_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_enrollment_event_expires_date_key FOREIGN KEY (expires_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_enrollment_event_submitted_date_key FOREIGN KEY (submitted_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_enrollment_event_facility_key FOREIGN KEY (facility_key) REFERENCES dw.dim_facility(facility_key),
    CONSTRAINT FK_fact_enrollment_event_source_system_key FOREIGN KEY (source_system_key) REFERENCES dw.dim_source_system(source_system_key)
);
GO

-- PROVIDER (ALL PHASES) | Agent table A13 Credentialing | build tier 3
-- GRAIN: One event on a provider credential: licence, DEA, board certification, malpractice, CAQH attestation.
-- Built from: new
CREATE TABLE dw.fact_provider_credential_event (
    provider_credential_event_fact_key BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_fact_provider_credential_event PRIMARY KEY,
    tenant_id INT NOT NULL,
    credential_ref NVARCHAR(50) NOT NULL,  -- Credential id
    event_seq SMALLINT NOT NULL,  -- Order
    provider_key INT NULL,  -- Provider
    credential_type NVARCHAR(30) NULL,  -- licence, dea, board, malpractice, caqh
    issuing_state CHAR(2) NULL,  -- State
    document_status NVARCHAR(20) NULL,  -- on_file, expiring, expired
    event_date_key INT NULL,  -- Date
    expires_date_key INT NULL,  -- Expires
    attested_date_key INT NULL,  -- Attested
    source_system_key INT NULL,  -- where the row came from
    event_key BIGINT NULL,  -- lineage: event.id
    known_at DATETIME2(0) NOT NULL,  -- point in time
    loaded_at DATETIME2(0) NOT NULL CONSTRAINT DF_fact_provider_credential_event_la DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_fact_provider_credential_event_nk UNIQUE (tenant_id, credential_ref, event_seq),
    CONSTRAINT FK_fact_provider_credential_event_provider_key FOREIGN KEY (provider_key) REFERENCES dw.dim_provider(provider_key),
    CONSTRAINT FK_fact_provider_credential_event_event_date_key FOREIGN KEY (event_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_provider_credential_event_expires_date_key FOREIGN KEY (expires_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_provider_credential_event_attested_date_key FOREIGN KEY (attested_date_key) REFERENCES dw.dim_date(date_key),
    CONSTRAINT FK_fact_provider_credential_event_source_system_key FOREIGN KEY (source_system_key) REFERENCES dw.dim_source_system(source_system_key)
);
GO

-- One row per bill line, followed back to its encounter line and appointment and forward to the payer transaction. The whole journey in one place.
CREATE VIEW dw.vw_claim_journey AS
SELECT a.appointment_ref, a.appointment_date_key, e.encounter_ref, e.encounter_date_key, b.claim_ref, b.frequency_code, b.line_number, b.service_code_key, b.units, b.billed_amount, b.expected_allowed, t.paid_amount, t.patient_responsibility, t.allowed_amount FROM dw.fact_bill b LEFT JOIN dw.fact_encounter e ON e.tenant_id = b.tenant_id AND e.encounter_ref = b.encounter_ref AND e.line_number = b.encounter_line_number LEFT JOIN dw.fact_appointment a ON a.tenant_id = e.tenant_id AND a.appointment_ref = e.appointment_ref AND a.version_seq = e.appointment_version LEFT JOIN dw.fact_transaction_line t ON t.tenant_id = b.tenant_id AND t.claim_ref = b.claim_ref AND t.line_number = b.line_number;
GO

-- Every adjustment that is a denial, with its reason, group and amount.
CREATE VIEW dw.vw_denial_line AS
SELECT j.* , r.carc_code, r.reason_category FROM dw.fact_adjustment j JOIN dw.dim_adjustment_reason r ON r.adjustment_reason_key = j.adjustment_reason_key WHERE r.is_denial = 1;
GO
