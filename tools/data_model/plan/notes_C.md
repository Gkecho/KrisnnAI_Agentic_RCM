# Notes C: payer_rule, enrollment, eligibility_check, staff, calendar

All five TBD tables are designed (none dropped). Validator: OK. 129 columns in total (46 + 31 + 27 + 14 + 11, including identity and audit columns).
REMAP has 77 entries: the 63 Remapped rows (Exact 12, Renamed 27, Partial 12, Derived 8, Added 4) plus 14 old "No home" rows reviewed from fact_eligibility_check, fact_enrollment_event and dim_staff (Added 9, Dropped 5).

REMAP key note: the workbook has many rows with the same old table and old column (for example dim_rule.rule_id appears 14 times, dim_rule.description 4 times). The REMAP key is
(old table, old column), so where the pair repeats the old column is written as `column @ Agent / Field` to keep every row separate. The merger must split on " @ " if it needs the plain column.

## payer_rule (Important, group Reference, 46 columns, versioned)
- One row = one version of one rule. `rule_code` is the stable key shared by all versions (the key that agent_decision_details.rule_code and Mirror/Coach quote). `version`, `is_current`, `previous_payer_rule_id` give the chain; `effective_from` / `effective_to` give the dates the version applies to.
- Families (`rule_family`): authorization, bundling, medical_necessity, unit_limit, modifier, timely_filing, attachment, payer_edit, enrollment, multiple_procedure, learned_denial, detection (the Scout rules: denial, underpayment, rejection, unbilled visit, unexplained adjustment; Detective/Scout rows 57-62). `rule_action` says what happens.
- Scope is columns, not text: payer_id (blank = all), plan_type, place_of_service_id, practice_id (set when the row is a practice switch or override), cpt_code_id with cpt_code_to_id for a range, paired_cpt_code_id for bundling, modifier_id, diagnosis_code_id, adjustment_reason_id (CARC) for learned patterns, edit_field_code and requirement_code for payer claim edits, unit_limit and unit_limit_basis.
- Learned rules (Coach to Mirror): same table, `rule_source_code = learned`, `approval_status` proposed/approved/rejected/retired, `approved_by_staff_id` (pseudonym), `approved_date`. Evidence is stored as counts and dates only (evidence_claim_count, evidence_denied_count, evidence_denied_amount, evidence window). The denial rate is a view, not a column. Cluster key (payer, CPT, CARC) is derived.
- Rule source is a code (`rule_source_code`) plus a reference code (`rule_source_ref`). No free text anywhere. The plain-language rule sentence the agents showed is built in a view from family, action and codes, so the "rule text" fields are not stored.
- Agents (30 Remapped rows): Permit Clerk 2, Code Whisperer 4, Mirror 11, Coach 6, Detective/Scout 7. They read rules, enabled flag, version, synthetic flag, owner and learned rules, and Coach and Scout write rule ids into findings.
- Defaults taken: per-practice enable/disable is a practice_id row (no separate switch table); threshold values stay in practice_settings, only version/approver/date of the set map here; timely filing days stay on payer.filing_days; multiple-procedure reduction percentage stays on contract_rate.multi_procedure_reduction_pct.
- Dropped: plain-language rule text and payer_rule_text (rule 4: no free text).

## enrollment (Optional, Reference, event, 31 columns, append-only)
- One row = one enrollment status change for a provider and payer, or one exclusion-list screening (`event_type` = status or screening). One table covers both because both are dated events about a provider and Credentialing reads them together (21 rows: A13 19, Mirror 1, Courier 1).
- Status on a date = latest status event not after that date (Derived). Days to expiry, days pending, days since screening and enrollment cycle time (effective minus submitted) are views.
- Added columns for the old "no home" fields: submitted_date, facility_id (service location), payer_provider_number (restricted), plan_program_code (also holds EDI for Courier's clearinghouse enrollment), enrollment_type, application_number (restricted), end_reason_code (code only), match_method, plus revalidation_due_date, last_revalidated_date, screening_list_date, exclusion_type, excluded_date, reinstated_date.
- Dropped: screened_entities (only providers are screened today; add owner/vendor later as a new event_type).
- Appended, not versioned: each status is a new event, nothing is overwritten.

## eligibility_check (Important, group 1 Appointment, event, 27 columns, append-only)
- One row = one 270/271 exchange. coverage.last_verified_* keeps only the latest status, so history needs a table. Needed by Gatekeeper (A1, 4 rows) and Mirror (1 row).
- trace_number = TRG + appointment id, with -2 for the secondary (`is_secondary`). It is not the client's number, so it is not restricted.
- Columns follow the 271: is_active (EB 1/6, blank when rejected), is_aaa_reject plus aaa_reason_code, plan_begin_date/plan_end_date, copay_amount, coinsurance_pct, deductible_remaining, other_payer_id (EB R), auth_required_hint (the Permit Clerk "no home" field, evidence for the authorization rule).
- Age of the check = service_date minus check_date, computed. Coverage active on the date of service is the answer for that service_date.
- Benefit amounts repeat coverage columns by design: they are what the payer said at that time.

## staff (Important, Reference, 14 columns)
- One row = one pseudonymous person: `staff_number` (code like B01, restricted), practice, `staff_role`, `team`, `weekly_hours`, start/end dates, is_active. Needed by Captain (6 rows), and as the target for approver and owner fields.
- No names, no skills, no schedule or leave, no task-type list (all Dropped; task types come from agent_task). Busy flag and minutes per week are computed from agent_task counts and weekly_hours.
- Not versioned (kept minimal); a role or hours change is a new row with the old one ended.

## calendar (Important, Reference, 11 columns)
- One row = one date: calendar_date, is_business_day, is_holiday, holiday_code, business_day_number (running count so a business-day lag is one subtraction). Month, quarter and year are views over the date, not columns.
- Tenant level, since holidays differ by client. Without it the system falls back to calendar days and Monday to Friday.

## Recommendations for LOCKED tables (not made)
1. Add link columns `approved_by_staff_id` / `assigned_to_staff_id` (FK staff) next to transactions.approved_by, bill_details.change_approved_by, practice_settings.approved_by, agent_approval.approved_by and agent_task.assigned_to, or keep the text and load it from staff.staff_number.
2. agent_decision_details.rule_code / rule_version / rule_source can now join payer_rule (rule_code + version). Consider a payer_rule_id column on agent_decision_details to pin the exact version that ran.
3. coverage.last_verified_date / last_verified_status can become copies of the latest eligibility_check row; coverage.trace_number-style fields stay out.
4. agent_task.owner_role vocabulary should match payer_rule.owner_role (registration / authorization / coding / billing).
5. The TBD sheet entries for these five tables can be removed. Remaining text there (plugs: authorization, cpt_code, adjustment_reason) is already satisfied by payer_rule links.
