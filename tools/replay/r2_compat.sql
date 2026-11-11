-- canon_compat: read-only compatibility layer that lets the Replay engine (tools/replay/world.py COLS) read the R2 model in krisnnai_r2.
--
-- Contents: VIEWS only. Nothing here changes, copies or writes any R2 table. Every view filters tenant_id = 1 (hard rule 8) and keeps tenant_id in its output.
-- Names and columns are the canonical ones world.py expects; the right-hand side is the R2 source.
-- Idempotent: CREATE SCHEMA IF NOT EXISTS + CREATE OR REPLACE VIEW. Apply with:  python tools/replay/r2_compat.py
--
-- GAPS (R2 genuinely lacks the data; the view exposes it as it is, never invented):
--   payer.standard_turnaround_days   was NULL for all payers; now filled by tools/synthea/load_payer_turnaround.py (derived from the generated data); SELF stays NULL
--   encounter_details.documented_level  NULL on all 356,338 encounter_line rows (A4 has nothing to compare)
--   document                         0 rows in R2 (plan-of-care lookups find nothing)
--   enrollment                       0 rows in R2 (A13 has nothing to watch)
--   claim_status_history             R2 has no 277CA rejections (is_rejection is false on every row), so A6 gets no input
--   payment.unapplied_amount         0 on every R2 payment (A11 has nothing to flag)
--   staff                            R2 staff numbers are STF-001..014; the engine looks people up by codes (FD01, B01, ...). Aliased by role below.

CREATE SCHEMA IF NOT EXISTS canon_compat;

-- ---------------------------------------------------------------- reference tables
CREATE OR REPLACE VIEW canon_compat.practice AS
SELECT practice_id, practice_number, practice_name, tenant_id FROM public.practice WHERE tenant_id = 1;

CREATE OR REPLACE VIEW canon_compat.facility AS
SELECT facility_id, facility_name, practice_id, tenant_id FROM public.facility WHERE tenant_id = 1;

CREATE OR REPLACE VIEW canon_compat.specialty AS
SELECT specialty_id, specialty_name, tenant_id FROM public.specialty WHERE tenant_id = 1;

CREATE OR REPLACE VIEW canon_compat.payer AS
SELECT payer_id, payer_code, payer_name, payer_number, payer_type, parent_payer, filing_days, corrected_claim_days, appeal_days,
       standard_turnaround_days,            -- derived observed median (load_payer_turnaround.py); NULL for SELF
       tenant_id
FROM public.payer WHERE tenant_id = 1;

CREATE OR REPLACE VIEW canon_compat.cpt_code AS
SELECT cpt_code_id, code, is_timed, tenant_id FROM public.cpt_code WHERE tenant_id = 1;

CREATE OR REPLACE VIEW canon_compat.modifier AS
SELECT modifier_id, modifier_code, modifier_group, tenant_id FROM public.modifier WHERE tenant_id = 1;

CREATE OR REPLACE VIEW canon_compat.adjustment_reason AS
SELECT adjustment_reason_id, carc_code, reason_class, short_label, reason_category, suggested_action, owner_role, upstream_stage, is_appealable, is_technical, tenant_id
FROM public.adjustment_reason WHERE tenant_id = 1;

-- fee_list <- fee_schedule_line: the current (latest effective_from) base fee per CPT, modifier-free rows only
CREATE OR REPLACE VIEW canon_compat.fee_list AS
SELECT DISTINCT ON (f.cpt_code_id) f.cpt_code_id, f.fee_per_unit, f.tenant_id
FROM public.fee_schedule_line f
WHERE f.tenant_id = 1 AND f.modifier_id IS NULL
ORDER BY f.cpt_code_id, f.effective_from DESC;

-- staff: R2 has staff_number STF-nnn and roles; the engine addresses people by role codes. Each alias row points at a real R2 staff row (same staff_id).
-- The original STF-nnn rows stay too. Roles with no R2 equivalent get no alias (the engine then skips that code): C03 (only 2 coders in R2).
-- MAPPING (a role-based judgement, not data in R2; confirm or change here):
--   engine code  R2 staff_number  R2 role            reasoning
--   FD01, FD02   STF-012, STF-013 front_desk        front desk staff 1 and 2 (STF-014 unused)
--   B01, B02     STF-002, STF-003 biller            billers 1 and 2
--   B03          STF-001          biller_manager    stands in for the "billing lead" who approves resubmits and disputes
--   M01          STF-001          biller_manager    stands in for the "manager" who approves learned rules (same person as B03; R2 has no manager role)
--   D01          STF-007          denial_analyst    the denial specialist (STF-008 unused)
--   C01, C02     STF-005, STF-006 coder             coders 1 and 2; engine code C03 has no R2 staff, so it is skipped
--   AR01         STF-009          ar_specialist     (STF-010 unused)
--   PP01         STF-011          payment_poster
--   Not mapped: STF-004 (biller), STF-008, STF-010, STF-014. The aliases carry the real staff_id, so any task assigned to "B03" is assigned to STF-001.
CREATE OR REPLACE VIEW canon_compat.staff AS
SELECT s.staff_id, s.staff_number, s.staff_role, s.team, s.tenant_id FROM public.staff s WHERE s.tenant_id = 1
UNION ALL
SELECT s.staff_id, a.alias, s.staff_role, s.team, s.tenant_id
FROM public.staff s
JOIN (VALUES ('STF-012', 'FD01'), ('STF-013', 'FD02'),                      -- front_desk
             ('STF-002', 'B01'), ('STF-003', 'B02'),                        -- biller
             ('STF-001', 'B03'), ('STF-001', 'M01'),                        -- biller_manager stands in for billing lead and manager
             ('STF-007', 'D01'),                                            -- denial_analyst
             ('STF-005', 'C01'), ('STF-006', 'C02'),                        -- coder
             ('STF-009', 'AR01'), ('STF-011', 'PP01')) AS a(num, alias) ON a.num = s.staff_number
WHERE s.tenant_id = 1;

CREATE OR REPLACE VIEW canon_compat.provider AS
SELECT provider_id, provider_name, provider_type, practice_id, specialty_id, tenant_id FROM public.provider WHERE tenant_id = 1;

CREATE OR REPLACE VIEW canon_compat.patient AS
SELECT patient_id, tenant_id FROM public.patient WHERE tenant_id = 1;

CREATE OR REPLACE VIEW canon_compat.coverage AS
SELECT coverage_id, termination_date, tenant_id FROM public.coverage WHERE tenant_id = 1;

CREATE OR REPLACE VIEW canon_compat."authorization" AS
SELECT authorization_id, units_approved, payer_id, tenant_id FROM public."authorization" WHERE tenant_id = 1;

-- ---------------------------------------------------------------- scheduling and eligibility
CREATE OR REPLACE VIEW canon_compat.appointment AS
SELECT appointment_id, patient_id, appointment_date, appointment_status, provider_id, payer_id, coverage_id, booked_date, tenant_id
FROM public.appointment WHERE tenant_id = 1;

-- appointment_details <- appointment_line
CREATE OR REPLACE VIEW canon_compat.appointment_details AS
SELECT appointment_id, line_number, authorization_id, expected_charge, tenant_id FROM public.appointment_line WHERE tenant_id = 1;

CREATE OR REPLACE VIEW canon_compat.eligibility_check AS
SELECT eligibility_check_id, appointment_id, coverage_id, patient_id, payer_id, check_date, service_date, plan_end_date, is_aaa_reject, tenant_id
FROM public.eligibility_check WHERE tenant_id = 1;

-- ---------------------------------------------------------------- clinical and charge capture
CREATE OR REPLACE VIEW canon_compat.encounter AS
SELECT encounter_id, patient_id, encounter_date, encounter_type, authorization_id, note_status, note_signed_date, signature_lag_days, rendering_provider_id, payer_id, appointment_id, tenant_id
FROM public.encounter WHERE tenant_id = 1;

-- encounter_details <- encounter_line
CREATE OR REPLACE VIEW canon_compat.encounter_details AS
SELECT encounter_id, cpt_code_id,
       documented_level,                    -- GAP: NULL on every R2 row
       modifier_1_id, modifier_2_id, tenant_id
FROM public.encounter_line WHERE tenant_id = 1;

CREATE OR REPLACE VIEW canon_compat.document AS
SELECT patient_id, document_type, document_date, document_status, tenant_id FROM public.document WHERE tenant_id = 1;   -- GAP: R2 table is empty

CREATE OR REPLACE VIEW canon_compat.bill AS
SELECT bill_id, encounter_id, patient_id, payer_id, charge_entered_date, total_billed, bill_status, bill_type, rendering_provider_id, service_date, tenant_id
FROM public.bill WHERE tenant_id = 1;

-- ---------------------------------------------------------------- claims
CREATE OR REPLACE VIEW canon_compat.claim AS
SELECT claim_id, claim_number, payer_id, patient_id, encounter_id, bill_id, authorization_id, coverage_id, service_date_from, submitted_date, total_charge, rendering_provider_id, tenant_id
FROM public.claim WHERE tenant_id = 1;

-- claim_details <- claim_line (claim_detail_id = claim_line_id)
-- A denied line has no allowed amount: the denial stage set it to 0, which A10 and A15 would read as an underpayment against expected_allowed.
CREATE OR REPLACE VIEW canon_compat.claim_details AS
SELECT claim_line_id AS claim_detail_id, claim_id, cpt_code_id, modifier_1_id, modifier_2_id,
       CASE WHEN line_status = 'denied' THEN NULL ELSE allowed_amount END::numeric(12,2) AS allowed_amount, expected_allowed, paid_amount, charge_amount, denied_amount, patient_responsibility, line_number, tenant_id
FROM public.claim_line WHERE tenant_id = 1;

-- claim_status_history: R2 event vocabulary mapped to the engine's. acknowledged -> accepted_277ca / rejected_277ca (by is_rejection), adjudicated -> remit_835.
-- submitted, reprocessed and pending pass through unchanged (the engine ignores them). R2 has no rejection rows (GAP for A6).
CREATE OR REPLACE VIEW canon_compat.claim_status_history AS
SELECT claim_id,
       CASE WHEN event_type = 'acknowledged' AND is_rejection THEN 'rejected_277ca'
            WHEN event_type = 'acknowledged' THEN 'accepted_277ca'
            WHEN event_type = 'adjudicated' THEN 'remit_835'
            ELSE event_type END AS event_type,
       event_date, status_after, is_rejection, rejection_reason, tenant_id
FROM public.claim_status_history WHERE tenant_id = 1;

-- ---------------------------------------------------------------- denials, appeals, cash
-- denial_details <- claim_detail_id = claim_line_id
CREATE OR REPLACE VIEW canon_compat.denial AS
SELECT denial_id, claim_id, claim_line_id AS claim_detail_id, payer_id, denial_date, denied_amount, adjustment_reason_id, denial_status, appeal_deadline, upstream_stage,
       is_preventable, owner_role, resolved_date, outcome, recovered_amount, tenant_id
FROM public.denial WHERE tenant_id = 1;

CREATE OR REPLACE VIEW canon_compat.appeal AS
SELECT appeal_id, denial_id, submitted_date, decision_date, is_overturned, recovered_amount, appeal_status, tenant_id FROM public.appeal WHERE tenant_id = 1;

CREATE OR REPLACE VIEW canon_compat.payment AS
SELECT payment_id, payer_id, payment_source, payment_date, payment_amount, posted_amount, unapplied_amount, tenant_id FROM public.payment WHERE tenant_id = 1;

-- transactions: what the engine needs from the ledger is the posted payment that recovered a denial (World.tx_den, used to tell a confirmed recovery from a pending one).
-- R2 ledger_entry has no denial_id, so the link is derived: the payment on the denied claim line, by the payer, posted on the denial's resolved_date, on an overturned denial (exactly one per denial in R2; its amount can differ from denial.recovered_amount).
-- This view therefore holds ONLY those denial-recovery payments, not the whole 1.2M-row ledger (the engine reads nothing else from it).
CREATE OR REPLACE VIEW canon_compat.transactions AS
SELECT DISTINCT ON (d.denial_id) l.ledger_entry_id AS transaction_id, d.denial_id, l.transaction_type, l.transaction_date, l.payment_id, l.amount, l.tenant_id
FROM public.denial d
JOIN public.ledger_entry l ON l.claim_line_id = d.claim_line_id AND l.tenant_id = d.tenant_id
WHERE d.tenant_id = 1 AND d.outcome = 'overturned' AND l.transaction_type = 'payment'
  AND l.transaction_date = d.resolved_date AND l.responsible_party = 'payer'
ORDER BY d.denial_id, l.ledger_entry_id;

-- ar <- ar_snapshot, ALL snapshots (month-end ones plus 'current' at the R2 data date), one row per bill, balance owner and snapshot.
-- as_of_date and snapshot_type are extra columns: the engine picks, for each replay date, the latest snapshot with as_of_date <= that date (hard rule 9). Before the first snapshot there is none.
CREATE OR REPLACE VIEW canon_compat.ar AS
SELECT ar_snapshot_id AS ar_id, bill_id, claim_id, patient_id, payer_id, balance_owner, balance, days_outstanding, service_date, tenant_id, as_of_date, snapshot_type
FROM public.ar_snapshot WHERE tenant_id = 1;

-- enrollment: GAP, R2 table is empty
CREATE OR REPLACE VIEW canon_compat.enrollment AS
SELECT enrollment_id, provider_id, payer_id, event_type, expires_date, tenant_id FROM public.enrollment WHERE tenant_id = 1;
