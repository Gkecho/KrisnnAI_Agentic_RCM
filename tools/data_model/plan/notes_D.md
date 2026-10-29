# Notes K=D: appeal, patient_statement, payment_plan, patient_contact_preference, payment_adjustment

All five were designed (none dropped as "not needed"). Column counts include identity and audit columns: appeal 32, patient_statement 26, payment_plan 24, patient_contact_preference 25, payment_adjustment 14. patient_contact_preference IS on the TBD list in the current model, so it is in TBD_DONE.

## appeal (Important, group 4, versioned event)
- One row = one appeal round on one denial (first, second, external review). Needed because denial holds only ONE outcome/recovered_amount per denial, while Advocate (A8) and Auditor (A10) need per-round clock start, deadline, amount disputed, evidence count, letter hash, payer case number, decision.
- Decision: denial.outcome, recovered_amount, appeal_deadline and resubmitted_claim_id STAY on denial as the final roll-up (no change). Appeal carries the rounds. Fallback rung 3 rebuilds one "first" appeal per denial from those denial columns.
- Evidence = count only; letter = hash only (no text, no documents). Payer case number and the practice's appeal number are restricted.
- Links to agent_decision (drafting) and agent_approval (the human review the A7 "review ref" points to).
- Defaults taken: amount_disputed falls back to denied_amount; deadline falls back to denial.appeal_deadline.
- Agents: A8 Advocate (13 rows), A10 Auditor (5 rows), A7 Hunter (1 row). Win history (A8 history_wins, win_probability) stays Derived from appeal + denial by payer and reason; not stored.

## patient_statement (Important, group 4, versioned event)
- One row = one statement/notice sent to a patient (date, amount shown, channel, dunning level, delivery status). Status changes (delivered, returned, disputed) are new versions.
- Needed: ar.last_statement_date only gives the last date, so dunning level, channel and Reg F timing cannot be known. Agent: A12 Concierge (7 rows).
- Decisions: dunning_level kept as a stored column because it is the level that was sent then (not rebuildable once rules change). Reg F dates are optional. Contact attempts per period are a view over this table plus agent_task.
- Dropped: patient reply / inbound text (free text may carry patient content); only the resulting status (disputed) is kept.

## payment_plan (Important, group 4, versioned header)
- One row = one plan per patient. NO instalment table: instalments are patient payments already in transactions; plan holds total, instalment size/count, next_due_date, missed_instalments, autopay flag.
- missed_instalments is stored because it is a point-in-time fact (versions keep the history). Autopay is a flag only; no card or bank details. Agent: A12 Concierge (1 row autopay flag; also feeds patient AR forecast).

## patient_contact_preference (Important, group 4, versioned header, TBD phase 3)
- One row = one patient's consent/preference state, as flags. New version on each consent or opt-out change, which keeps TCPA consent history.
- Contains: preferred_channel, quiet hours start/end (hour numbers), address_status, has_phone, text_consent, autodial_consent, consent_date/source/wording_version, opt_out and date, has_authorized_rep, guarantor_hash (salted hash, restricted). NO phone numbers, emails, addresses or names.
- Defaults (conservative): no text/autodial consent, opt_out 0, channel mail. Language stays on patient.language (already renamed). Agent: A12 Concierge (9 rows).
- Mild sensitivity note: guarantor_hash links two people; kept restricted.

## payment_adjustment (Optional, group 4, append-only detail)
- No Remapped row needs it, so it is designed lean on its own merit: payment.plb_amount is a total; the breakdown (takeback, recoupment, interest, penalty, PLB reason code) cannot be rebuilt from it and is needed for cash reconciliation. Rule: sum of rows = payment.plb_amount.
- PLB03 reference number deliberately not stored (gap decision: stays in raw 835). Can be skipped if the team prefers; the total on payment still works (fallback rung 3). Marked Optional.

## Old tables reviewed
- fact_appeal_event -> appeal. fact_patient_balance_event: statement rows -> patient_statement; payment/refund/balance rows were already remapped to transactions (correct, not mine). dim_patient_contact -> patient_contact_preference (+ patient.language, payment_plan.autopay_enrolled). No leftover columns without a home, except the dropped patient reply text.
- REMAP keys must be unique, so rows sharing an old column (for example status_key, event_date_key) are one entry with a note naming the extra new columns; a few synthetic old-column names are used for rows that had to be separate (payer_decision, decision_date, denial_overturned_flag, channel_and_send_time, patient_reply_text, autodial_consent). Remapped-sheet rows with the same old table/column and final table collapse accordingly (34 sheet rows -> 28 entries).

## Recommendations for LOCKED tables (not made)
- ar.last_statement_date and ar_interval.last_statement_date become derivable from patient_statement; keep as a denormalized convenience or mark Derived.
- Remap rows "contact attempt log", "validation notice date", "number of contact attempts" are currently mapped to transactions.transaction_date/transaction_number, which is wrong (not money movements). Re-point to patient_statement (statement/notice dates) and agent_task (contact_channel, reminder_count); this is a remap-sheet correction owned by whoever merges, not mine.
- The "financial assistance / discount decision" row maps to transactions.amount; fine as a write-off/adjustment, but the approval belongs in agent_approval.
- denial: no change. Optional later: denial.outcome could be documented as "roll-up of appeal.payer_decision".
