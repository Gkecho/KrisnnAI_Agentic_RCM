# Replay results -> R2 agent_* tables -> ui_data.js

Code: `tools/replay/r2_persist.py` (Replay result -> agent_* rows), `tools/replay/r2_export_ui.py` (agent_* rows + R2 reference -> `ui_data.js`). Tests: `tests/test_replay_r2.py`.
Database: `krisnnai_r2` only, tenant_id = 1, `source = 'replay'`. Writes go to the nine agent_* tables and nowhere else.

## 1. What the persist layer takes

`Replay.S.rows[table]` after `run()` finishes (rows are updated in place as tasks complete, findings resolve and forecasts get actuals, so the end state is the right one) plus `Replay.traces`.
`r2_persist.from_engine(replay)` builds `{"rows": {...}, "traces": {...}}` from the object; `dump_results` / `load_results` do the same through a JSON file (Decimal, date and datetime are tagged so nothing becomes a float).
The ids in those rows (claim_id, payer_id, denial_id, patient_id, provider_id, appointment_id, encounter_id, authorization_id, practice_id, staff ids, transaction_id) must already be **R2 integer keys**. That is the job of the `canon_compat` adapter; persist checks every typed link against R2 before it writes and refuses the batch if one is missing.
The engine's own ids (agent_run_id, agent_decision_id and so on) are local; persist gives every new row a fresh R2 key and remaps the links between them.

## 2. Table mapping (engine -> R2)

| Replay row / field | R2 table.column | How |
|---|---|---|
| `agent_run` (one per agent per business day) | `agent_run` | same columns; `run_status` ok -> `succeeded`; `trigger_type` lower case; `ended_at` falls back to `started_at`; `code_version` becomes `<engine VERSION>\|lb<load_batch_id>` (see gaps) |
| `agent_decision` | `agent_decision` | same columns. `finding_id`, `task_id`, `known_at` are dropped (R2 links the other way: finding and task point at the decision) |
| decision `outcome` | `agent_decision.outcome` | flag/route -> `flag`; hold -> `hold`; clear/release/match -> `proceed`; suggest/proposed -> `propose_change`; anything else -> `needs_human` |
| decision `human_outcome` | `agent_decision.human_outcome` | accepted -> `accepted`; edited -> `changed` |
| decision `entity_type` | `agent_decision.entity_type` | claim_detail -> `claim_line`; payer_cpt -> `cpt_code`; payer_rule -> `payer` (entity_id = payer_id); ar -> `ar_snapshot`; the rest unchanged. The typed link (claim_id for claim, denial_id for denial, ...) must equal entity_id or the batch is refused (R2 CHECK) |
| `input_hash` (bytes) | `agent_decision.input_hash` | salted sha256, stored as a bytea hex literal |
| `reason_summary` | `agent_decision.reason_summary` | scanned for identifiers (SSN-like, 9+ digit numbers, e-mail, DOB/MRN) and refused on a hit |
| A5 prediction scored later | `agent_decision.recheck_condition` / `recheck_result` | `payer_answer_received` / confirmed, not_confirmed or pending, from the finding's final status (the decision record's verification condition and result) |
| `agent_decision_details` (one per rule) | `agent_decision_check` | rule_code, check_result (pass/fail), observed_value, expected_value, severity, rule_version, rule_source, check_seq kept. **Rules fired = these rows**; `agent_decision.rules_checked` / `rules_failed` are the counts and are reconciled in the export |
| trace `tables_read` | `agent_decision_check.evidence_ref` | `reads:<tables>` (100 chars) |
| `payer_rule_id` on a check | -- | not written: `payer_rule` is not an agent table. Learned-rule id is kept in `evidence_ref` as `learned_rule#<n>` |
| `agent_finding` | `agent_finding` | same columns. `finding_status` open -> `open`, resolved -> `fixed`, confirmed -> `accepted`, unconfirmed -> `dismissed`; resolution `recovered` -> `fixed`; `finding_hash` salted hash; `summary` identifier-scanned |
| `agent_task` | `agent_task` | same columns; `assigned_to` -> `assigned_to_staff_id`; status returned -> `done` with outcome `returned`; outcome resolved -> `done`; priority hi/md/lo -> high/normal/low. A rework is a new row, `version` 2, `previous_agent_task_id` set, and the earlier version gets `is_current = false` |
| `agent_approval` | `agent_approval` | `approved_by` -> `approved_by_staff_id` (required when approved, cleared otherwise); approval_type: code_change -> `code_change`, resubmit / appeal_send / dispute_send -> `send_to_payer`, rule_activation -> `setting_change` |
| `agent_writeback` | `agent_writeback` | target PM -> `pm`, portal -> `payer_portal`; type task_note -> `note`, appeal_submit / dispute_submit -> `appeal_packet`; send_status suppressed -> `not_sent_shadow`; `payload_hash` salted hash |
| `agent_value` | `agent_value` | detected -> `detected`; confirmed -> `recovered` with `ledger_entry_id = transaction_id`; pending (cash seen, remit not posted) -> `recovered`, `is_estimate = true`, no ledger entry (R2 fallback 2). `signed_amount = amount` (no reversals are produced); negative amounts refused |
| `agent_forecast` | `agent_forecast` | same columns; forecast_type weekly_cash -> `cash_week`; actual_amount / within_range as filled by the engine |
| `payer_rule` rows A9 proposes | -- | **not written** (not an agent table). A9's decision and finding point at the payer and carry the rule code and evidence in `summary` |
| `patient_statement` (A12) | -- | not written: no agent_* home; the A12 decision and task are written |
| `appeal.agent_decision_id` / `agent_approval_id` updates | -- | not written (client table). Join through `agent_approval.entity_id` / `agent_decision.denial_id` instead |

Boilerplate: `tenant_id = 1`, `source = 'replay'`, `loaded_at` = time of the persist call, `version` 1 and `is_current` true unless a successor exists. `is_source_deleted`, `is_active` and `load_batch_id` are not columns of the agent tables.
Money is Decimal end to end (a float is refused). Hashes are salted with the same salt as `r2load.h`.

### Idempotency, reset
Natural keys (hard rule 7), checked against rows already in R2 with the same source, so a rerun adds nothing:
run (agent, mode, started_at) - decision (agent, type, entity, decided_at) - check (decision, seq) - finding (agent, type, entity, found_date, version) - task (agent, type, entity, created_date, version) - approval (decision, type, date) - writeback (decision, type, attempt, version) - value (agent, stage, kind, entity, date, amount) - forecast (type, as_of, payer, target start, version).
Two rows with one key in the same batch (A4 can raise two decisions on one encounter in a day) are kept as the 1st and 2nd occurrence.
`--reset` runs `DELETE ... WHERE tenant_id = 1 AND source = 'replay'` on the nine tables, children first, and then writes. Counts after reset + write equal counts after the first write (tested).

## 3. ui_data.js: key -> source

| ui_data.js key | Built from | Notes |
|---|---|---|
| `schema` | constant 1 | |
| `meta.as_of` | `max(agent_run.started_at)::date` (or `--as-of`) | the data date; everything below is computed as of it |
| `meta.shadow` | true | every decision is `run_mode = 'shadow'` |
| `meta.run` | `agent_run` (status, runs, first/last run, code_version, lb id), `practice.practice_name`, `load_batch` (files_loaded = batches), `claim_status_history` rows <= as_of (events_added) | `gate` = all reconciliation checks passed. Extra keys `practice`, `runs`, `first_run`, `last_run`, `code_version`, `load_batch_id`, `source`, `note` are inside `run` |
| `meta.planted` | the generator rules of `tools/synthea/load_denials.py` and `load_auth_eligibility.py`: Medicare dental CARC 96, E/M with injection and no modifier 25 CARC 4, unit/frequency limits CARC 151, preventive visit without a routine diagnosis CARC 11, missing authorization CARC 197, each with the count of denials carrying that CARC from `denial` | described as generator rules, not an answer key. The site reads `denial_pattern` and `rate_cut`; `denial_pattern` is filled from the CARC 4 rule (UHC 0.8) and `rate_cut` is an explicit "none" because R2 has no payer-wide rate cut. New key `generator_rules` lists all five, `note` says what they are, `claims_billed` = claims submitted <= as_of |
| `queue[]` | open `agent_task` rows (+ `agent_decision`, `agent_finding`, `agent_decision_check`, `claim`, `payer`) | open as of as_of: created by then and `completed_date` null or later; a rework version only counts once its predecessor was returned. title = task title + claim reference; value = amount_at_stake x decision confidence; priority = value x 1.5 if overdue x 1.2 if high priority; deadline = finding.deadline_date or task.due_date; why = decision reason + failed checks; evidence = the checks (rule, pass/fail, observed/expected); next_steps = text per action type (not stored in R2); confidence = decision.confidence; payer = payer_code; billed = claim.total_charge for A5/A6/A7/A8/A10; queue_type Denial (A8), Rejection (A6), Underpaid (A10), Filing risk (A7 with <= 30 days left) or No response (other A7); top 40 per owner and agent |
| `queue[].claim` | `claim.claim_number` when the task has a claim; else `APT-`/`ENC-`/`PAY-`/`ENR-` + entity id | no patient data; the claim reference always resolves to an R2 claim (tested against the database) |
| `queue[].agent`, `owner`, `action_type` | agent_code -> `a8_denial` etc.; owner_role -> the site's owners (denial_specialist and billing_lead -> `billing`, ar_specialist -> `ar_lead`, manager -> `practice_manager`; A12 -> `patient_billing`, A13 -> `credentialing`, A15 -> `revenue_assurance_lead`); (agent, task_type) -> the site's action types | |
| `queue_totals` | the same open tasks, true count and value per `owner\|agent` | |
| `queue_stats` | the same: by_cause (CARC for A8, else finding_type), by_payer top 8, age buckets 0-7/8-14/15-30/30+, due overdue/next_30/later | |
| `agents[15]` | `agent_decision` (decisions, proposed = not proceed/no_action, no_action, actions by task type with `amount_at_stake`), `agent_task` + `agent_finding` (top 3 examples) | `planted` on A8 = denial counts for the five generator CARCs |
| `baseline` | `agent_finding` found <= as_of: findings, recoverable (preventable, less amount recovered by then), structural (not preventable); by_type keyed by the site's names (denial, rejection, timely_filing, unbilled_visit, underpayment) plus other finding types | |
| `slices` | A15 findings: `payer_code\|cpt` and `amount_at_risk` | |
| `replay.health` | `claim`, `denial`, `ar_snapshot` | clean_claim_rate = 1 - claims with a denial / claims (R2 has no clearinghouse rejections); days_in_ar = payer AR at the latest snapshot / (charges last 90 days / 90); ar_over_90_share by balance |
| `replay.reconciliation` | tie-outs on agent_* and claim: run.decisions_made vs decisions, decision.rules_checked vs checks, finding/task -> decision links, value -> finding links, claim total vs lines | |
| `replay.found_vs_planted` | `denial` by generator CARC (claims) vs A5 findings raised before the denial | planted = claims denied with that CARC; found = those A5 had already flagged; precision = confirmed predictions naming that CARC / predictions naming it. Expect near zero: A5's rules do not cover the generator patterns |
| `replay.by_payer`, `replay.opportunities` | `agent_finding` by payer; top 25 by amount_at_risk | |
| `reference` | R2: `adjustment_reason` (carc_routes), `claim_status_code` (rejection_routes), `payer_rule` families ncci_edit / unit_limit / authorization (ncci_pairs, mue_limits, auth_requirements), `fee_schedule_line`, `payer` (filing and appeal windows) | `policy` is empty: R2 has no policy table (all actions are L0 / shadow by default) |
| `staff` | `staff` (pseudonymous ids) + completed `agent_task` rows (assigned_to_staff_id, minutes_spent, outcome, due_date) | employees, metrics, benchmark, handle_time, rework_minutes, history, teams, gaps, strengths. The Replay engine simulates the humans, so `synthetic` stays true. allocation, unallocated, improvements, scenarios, planted are empty (not derivable yet) |

## 4. What the R2 agent tables cannot hold (gaps)

1. **No `load_batch_id` column** on any agent table, although the other R2 tables have one. The load-batch lineage is stored in `agent_run.code_version` (`v0.9-shadow|lb1`). Proposed fix: add `load_batch_id` to agent_run.
2. **Decision record (CLAUDE.md) fields with no column**: autonomy level applied (L0-L4), proposed action type and payload, agent version on the decision (it is on the run), model id/version on the decision (run has model_name only), approver on the decision (it is in agent_approval), execution result. Today everything is L0 / shadow so the level is implicit.
3. **Triggering event / trace**: `agent_decision` has no trigger text, no list of reads and no hand-off text. Only table names reach `agent_decision_check.evidence_ref`; the full trace stays in the replay jsonl log.
4. **`payer_rule` proposals (A9)** and **`patient_statement` (A12)** have no agent_* table; they are not persisted, and the decision/finding carry the rule code in `summary`.
5. **Task outcome `returned`** (sent back for rework) is not one of R2's outcomes (done, no_action_needed, declined); it is stored as is and the version chain records the rework.
6. **Vocabulary the engine invents**: finding types such as `coverage_ended`, `authorization_exhausted`, `predicted_denial` and the engine's check `rule_code`s are kept as strings (R2 lists examples only).
7. **Versioned rows use the same key space as new rows**: R2's primary key is (id, version) but the engine creates a rework as a new id with `previous_agent_task_id`. Persist keeps that (new id, version 2, predecessor not current).
8. **No policy / autonomy table** in R2, so `reference.policy` is empty.
9. **No clearinghouse rejections in R2** (`claim_status_history` has no rejection events): A6 will raise nothing, and the Rejection queue type stays empty.
10. **ui_data.js keys with no agent_* source**: `agent_approval` and `agent_forecast` feed no existing key (the site's Approvals and cash-forecast screens show sample content); `agent_value` only feeds a reconciliation check. The site's `liveReplay` / `liveAnalytics` screens read `meta.planted.denial_pattern` and `rate_cut` and print "simulator planted"; they still render, but the label and the five-rule list need a small site change (not done here).
