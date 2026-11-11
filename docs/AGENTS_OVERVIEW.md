# KrisnnAI RCM: the agents A1 to A15 and A15-lite

Reference document. Prepared 2026-11-11 from the repository docs, code and tests (sources listed at the end). Everything here describes shadow-mode behaviour on synthetic or generated data. Where the sources are silent, this document says "not documented".

---

## 1. Executive summary and overview

KrisnnAI RCM is an intelligence layer that sits above a medical practice's practice-management (PM) / EHR system and its clearinghouse. It reads claim, remittance, schedule, note and payment data, finds revenue problems, ranks them, and prepares work for named people. It does not replace those systems. The strategy defines fifteen narrow agents (A1 to A15), each watching one hand-off in the revenue cycle where money is typically lost (coverage, authorization, documentation, coding, claim defects, submission, unpaid claims, denials, learning from denials, underpayment, cash posting, patient balances, provider enrollment, operations oversight, revenue variance), plus A15-lite, a read-only leakage diagnostic that is the entry offer. All sixteen are built, but only in shadow mode: they record what they would have proposed and send nothing, change nothing and write nothing back to a client system. The agents are rules-based (plain code with documented thresholds); no AI model is approved for use, and the engine's default model provider is a deterministic stub. Findings are "detected" or "proposed" amounts, never "recovered" or "saved" money. All data so far is synthetic or generated, so every count in this document shows how the rules behave on that data, not how the product would perform in a real practice. Most thresholds are placeholders awaiting business sign-off.

### Overview table

| ID | Persona | Official name | Revenue-cycle stage | One-line job | Human owner (who acts) | Autonomy / mode |
|---|---|---|---|---|---|---|
| A1 | Gatekeeper | Pre-Visit Financial Clearance Agent | Before the visit | Flags visits whose coverage is inactive, has another primary payer, or was never (or not recently) checked; estimates the patient share | Front desk; practice manager approves unusual exceptions | L0, shadow |
| A2 | Permit Clerk | Authorization Intelligence Agent | Before the visit | Flags visits that need a prior authorization and have none, an expired or denied one, or no units left | Front desk; practice manager decides exceptions | L0, shadow |
| A3 | Note Chaser | Documentation Completeness Agent | After the visit | Flags missing or unsigned notes, missing note elements and missed or late charges | Provider (notes), biller (charges) | L0, shadow |
| A4 | Code Whisperer | Coding & Charge Integrity Copilot | After the visit | Compares the billed visit level with what the signed note supports; suggestion only | Coder (certified coder decides) | L0, shadow, suggestions only |
| A5 | Mirror | Claim Prevention & Digital Twin Agent | Before the claim leaves | Checks each claim before release for defects likely to cause a denial or lost filing | Billing or coding | L0, shadow |
| A6 | Courier | Claim Submission & Response Agent | Submission | Reads 999/277CA rejections, separates technical from business causes, prepares a fix; response side only | Billing; billing lead approves a resubmission packet | L0, shadow (response side) |
| A7 | Hunter | AR Next-Best-Action Agent | After submission (unpaid claims) | Ranks claims that are unpaid past the payer's usual turnaround and proposes the next follow-up | Billing; A/R lead for old items | L0, shadow |
| A8 | Advocate | Denial Resolution & Appeal Agent | Denials | Classifies each denial, names the owner and deadline, estimates recovery, drafts an appeal text | Billing, coding or front desk by CARC; denial specialist | L0, shadow |
| A9 | Coach | Denial Prevention Learning Agent | Denials (learning) | Finds recurring denial patterns and proposes a prevention rule for a manager to approve | Practice manager | L0, shadow |
| A10 | Auditor | Contract & Underpayment Agent | Payment | Compares each paid line with the contract rate and prepares a dispute package for short payments | Finance | L0, shadow |
| A11 | Bookkeeper | Payment Posting & Reconciliation Agent | Payment | Reconciles each payer payment to the bank deposit and to what was posted in the PM | Finance; payment poster | L0, shadow |
| A12 | Concierge | Patient Financial Engagement Agent | Patient balance | Builds a staff worklist of patient balances (statement missing, aging, credits, disputes); no outreach | Patient billing staff | L0, shadow, staff-facing only |
| A13 | Credentialing (no separate persona name documented) | Credentialing & Enrollment Agent | Across the practice | Flags provider enrollments that are missing, expired, expiring, pending too long, or screening that is stale or excluded | Credentialing; compliance owner decides exceptions | L0, shadow |
| A14 | Captain | RCM Operations Control Tower | Across the practice | Merges all agents' open work into one ranked inbox, forecasts cash, raises operational signals | Operations leader | L0, shadow |
| A15 | Detective (full) | Revenue Assurance Investigator | Across the practice | Finds payers or payer+CPT slices whose realisation against contract has fallen and explains the cause | Revenue assurance lead; finance/RCM leader validates | L0, shadow |
| A15-lite | Scout | Leakage diagnostic (read-only) | Across the practice (look-back) | One-off read-only report of detected leakage by type, payer, CPT, recoverable vs structural | Finance / RCM leader validates | Read-only; no decision records, no actions |

Persona names come from `tools/replay/engine.py` and `docs/ui_mapping.md`. "Scout" for A15-lite appears in `ARCHITECTURE.md` and `ui_mapping.md`. No persona name for A13 other than "Credentialing" is documented.

---

## 2. How the agents work together

### 2.1 Shadow mode and autonomy levels

Every new action type starts at autonomy level L0 in shadow mode: the engine records the decision and never executes. Promotion to a higher level is a change to a row in the `policy` table, per tenant and action type, backed by evidence, never a code default. Each level adds responsibility for the system and removes work from the human:

| Level | Name | System behaviour | Human role |
|---|---|---|---|
| L0 | Observe | Reads data and measures current state only | None needed |
| L1 | Assist | Detects issues, ranks work, explains why | Staff performs the action |
| L2 | Prepare | Drafts a transaction, task, appeal, correction or posting | Reviews and sends or approves |
| L3 | Approve and run | Executes after a named approval | Approves an exception or batch |
| L4 | Bounded autonomous | Runs low-risk actions inside client dollar caps | Reviews samples and exceptions |

Engine rule for L4: it runs alone only if the amount is at or below the policy's cap and confidence is at least 0.90; otherwise it waits for approval. In the current build every agent is L0 / shadow. The preview UI shows levels L1 to L4 for some agents; `docs/ui_mapping.md` states those levels are not real.

### 2.2 The decision record

Every agent run on an event ends in exactly one decision record (table `decision_record`). "No record, no action." It stores: tenant, agent id and version, event and trigger type, an input snapshot reference with source lineage, the rules that fired (id and result), model id/version and prompt hash if a model was used, confidence, financial materiality, the proposed action and payload, the autonomy level applied, mode (shadow or live), approver and time, execution result, verification condition and result, and creation time. Records are append-only. Every proposal also carries a standard "inbox card" (title, why, priority, expected value, deadline, owner, next steps, evidence) so a screen can show any agent's output the same way.

### 2.3 The eight-step engine

Every agent runs through the same engine (`krisnnai/engine/pipeline.py`) and cannot skip the policy step or call an adapter itself:

1. Trigger: the agent says whether it wants this event; no match means no run and no record.
2. Context pack: only data known at the event's time.
3. Deterministic checks: plain rules, each with an id and result; a failed blocking rule stops execution.
4. Model reasoning: optional, through the model abstraction (stub by default; a real provider is refused without an approved BAA).
5. Confidence and materiality: the agent produces a proposal with dollars, confidence and a verification condition.
6. Human checkpoint: the engine and policy decide denied, shadow, observed, assisted, pending approval or execute.
7. Action adapter: the only place anything is executed. Adapters are disabled or stubs (a task/note adapter that only fills an outbox, and a clearinghouse stub that records and never sends).
8. Verify and learn: the agent states the condition that proves success and the result.

Policy outcomes: allowed = false is denied; a failed blocking check is blocked; shadow or replay records only; live L0/L1 observes or assists; live L2 waits for approval (approving marks a draft approved, nothing runs); live L3 runs once after a named approval; live L4 as above. Approvals (`engine/approvals.py`) require a named approver whose role matches the policy, can be decided once, and a rejection needs a reason.

### 2.4 Hard rules that bind every agent (summary of CLAUDE.md)

1. No real PHI in the repo, tests, logs, prompts or commits; patient identifiers are salted hashes.
2. Read-only toward client systems. The only future write-back is tasks and notes, through a disabled-by-default, policy-gated adapter.
3. Never submit to payers directly; only through the partner clearinghouse adapter and only where policy allows.
4. Codes, refunds and write-offs are never automatic: no agent changes CPT, ICD-10 or modifiers or creates a write-off or refund without a named human approval.
5. Every decision writes a decision record.
6. Rules first, AI second: deterministic checks are plain code; a model may only extract, classify, predict or draft, behind the model abstraction. No PHI to any model without an approved BAA.
7. Idempotency: re-ingesting a file or re-running an agent on the same event creates no duplicates (keys: file hash, ISA13/GS06/ST02, and tenant + event + agent + action type).
8. Tenant isolation: every table has `tenant_id`, every query filters by it, and tests include a cross-tenant leak test.
9. Point-in-time correctness: anything used for replay or evaluation is computable "as of" a timestamp using only data known then.
10. Money is Decimal, never float; dates are dates.

### 2.5 Rules first, AI second; point-in-time; idempotency; tenant isolation in practice

- Rules first: all deterministic checks (deadlines, contract math, required fields, duplicates) are plain code with thresholds in `config.py` or in tenant tables. No approved model exists; the stub provider is the default. The only drafting uses are neutral text built from codes and dollars (A3 note query, A8 appeal draft, A10 dispute letter), all through the stub.
- Point-in-time: each event carries `known_at`. Replay (`engine/replay.py`) runs an agent over events in `(known_at, id)` order with `as_of = known_at`, always in shadow and with no adapters. Several agent defects found during development were leakage or date-matching errors that this discipline exposed (see A1, A2, A9, A14).
- Idempotency: records are keyed on (event, agent, action). A second replay returns identical fingerprints (a hash of the record without timestamps). Sweepers raise events only on a first gap, a change, a repeat interval, and a closing event.
- Tenant isolation: every agent has a cross-tenant test (see test counts below).

### 2.6 The shared layers

**Ingest (M2, `krisnnai ingest PATH --tenant ID`).** Loads X12 837P, 835, 999 and 277CA files and fee-schedule CSVs. Per file: SHA-256 hash (already loaded means skipped); parse with no database writes (any structural problem fails the file with a reason); one transaction writing `source_file`, `event` and normalized rows; envelope checks (ISA length, SE/GE/IEA counts and control numbers); a "re-sent file" check on ISA13/GS06/ST02 plus content. Events are append-only, one per fact. Patients exist only as `SHA-256(salt | member id)`. A loader for the fabricated Valley Wellness database exists (read-only against Valley).

**Matching (M3, `krisnnai match`).** Links 277CA to claim by CLM01 echo; remit to claim by `clp01`, then `clp07` (payer claim number), then `patient_dos_amount`; remit line to claim line by `line_exact` or `line_cpt_mod`; checks each payment (BPR02 equals the sum of CLP04 less PLB). Each link stores which rule matched. It never guesses: candidates with different CLM01 values are `ambiguous` and stay unmatched. A second run changes nothing.

**Canonical model and knowledge.** `docs/ARCHITECTURE.md` describes a source-neutral canonical model (journey tables, reference, `data_feed`) and agent-output tables (`agent_run`, `agent_decision`, `agent_finding`, `agent_task`, `agent_approval`, `agent_writeback`, `agent_value`, `agent_forecast`). The document states the application code and Alembic migrations still target the earlier minimal model and the canonical model is not wired in yet. A separate Payer Knowledge Book (`krisnnai/knowledge/`) holds versioned, effective-dated payer rules and computes appeal and corrected-claim deadlines, returning a "problem" (owner and what to ask) instead of guessing; it holds only a small demo ruleset for a fictional payer, is reachable from the CLI, and is not called by the agents (found by search; not stated as intended in the sources).

**Two implementations.** The agent folders under `krisnnai/agents/` run on the original minimal data model and are what the specs and most tests describe. The R2 history traces (section 4) run a separate day-by-day replay engine in `tools/replay/engine.py` on the R2 canonical database. It applies the same ideas but different thresholds and, for some agents, different rules. Each agent section notes the R2 version.

### 2.7 Test counts

Test counts below are `def test_` lines per file. `pytest --collect-only` could not run: the Python used for this research lacks SQLAlchemy, so every test module fails at import. Parametrized tests would raise the real count; only one parametrize use was found (in `test_ingest.py`).

| Area | File | Tests |
|---|---|---|
| A1 / A2 / A3 / A4 | test_a1 / a2 / a3 / a4 | 24 / 20 / 23 / 11 |
| A5 / A6 / A7 / A8 | test_a5 / a6 / a7 / a8 | 12 / 15 / 17 / 19 |
| A9 / A10 / A11 / A12 | test_a9 / a10 / a11 / a12 | 18 / 17 / 21 / 19 |
| A13 / A14 | test_a13 / a14 | 21 / 18 |
| A15-lite / A15 full | test_a15 / test_a15x | 16 / 13 |
| Engine, matching, ingest, knowledge | test_engine / match / ingest / knowledge | 22 / 10 / 26 / 20 |
| R2 replay | test_replay_r2 / test_replay_r2_compat | 36 / 16 |

Agent tests total 284.

---

## 3. The agents

Common to every agent section: owner roles are those named in the spec or the code; thresholds marked "placeholder" await sign-off and the specs state they are fixed from baseline data before shadow results are reviewed; per-action SLA, cost per transaction, drift thresholds, reversibility class and sign-off records are "TBD at spec review" in every spec unless stated. No agent has a model approved for use.

### A1. Gatekeeper: Pre-Visit Financial Clearance Agent

**Name and persona.** A1 Gatekeeper. Stage: before the visit. Milestone M14. Code: `krisnnai/agents/a1_clearance/`.

**The problem.** Revenue is lost when a visit goes ahead with coverage that is inactive, with another payer as primary, or with no eligibility check for that date of service. Strategy KPI: eligibility denial rate and pre-service clearance percentage.

**Desired actions.**
- Detects four gap types: `coverage_inactive` (271 says inactive, coverage ended before the visit or starts after it), `cob_other_payer` (271 names another primary payer), `no_eligibility_check` (no answer known for this appointment's date of service), `stale_check` (latest answer older than 14 days).
- Action types: `a1_eligibility_check_task` (no or stale answer), `a1_coverage_exception_review` (inactive; practice manager approves any exception), `a1_cob_review`.
- Also computes a patient estimate (remaining deductible first, then coinsurance on the rest, plus flat copay, capped at the allowed amount). It is shown on the decision; it is not sent to the patient.
- Acts: front desk. Never: sends a 270, contacts the patient, or changes anything in the PM. Not built: referral and prior-authorization detection (A2's data).

**Trigger and timing.** Appointment created or changed. Judged at checkpoints 3 days and 1 day before the visit; booking is the first check. CLI: `krisnnai a1 sweep|replay`.

**Inputs.** `appointment` table and `eligibility_response` (271 parser) feeds (migration 0009), fee schedule for the estimate. Referral/auth data not available.

**Checks and rules.** All plain code in `rules.check` and `rules.estimate`, as of the checkpoint day. An eligibility answer is for a date of service, so matching is by date. No model; none approved.

**What we built.** Modules: `agent.py`, `rules.py`, `config.py` (`CHECKPOINT_DAYS = (3, 1)`, `STALE_DAYS = 14`), `sweep.py`, `summary.py`. Decision: matching an answer by date of service, after the first version took any recent answer for the same patient. 24 tests.

**How we verified.** Replay on the Synthea book (300 patients, 1,776 appointments, 3,552 checkpoints): planted and found exactly 40 inactive coverage (each flagged before the visit), 71 other-payer, 142 never checked, 88 stale; 1,435 of 1,776 cleared (80.8%); 0 executed; the patient estimate equals the patient responsibility on every clean single-line paid claim. The 271s and defects were simulated by the same team that wrote the rules: this shows wiring, not realism.

**Limits and open items.** No live 270 adapter (verified live only for eligibility on a Stedi sandbox, per ARCHITECTURE); real 271 variants and referral/auth data missing; front-desk sign-off of thresholds not documented; SLA TBD. No regulatory sign-off (No Surprises Act good-faith estimate rules map here; TBD).

**R2 replay version.** Reads `eligibility_check` rows and flags a visit whose plan end date precedes the service date (rule `R-COV-ACTIVE`), plus an AAA-reject rule. See section 4.

---

### A2. Permit Clerk: Authorization Intelligence Agent

**Name and persona.** A2 Permit Clerk. Stage: before the visit. Milestone M16. Code: `krisnnai/agents/a2_authorization/`.

**The problem.** Services needing prior authorization are delivered without one, or past its window or units. Strategy KPIs: authorization turnaround and auth-related denials.

**Desired actions.**
- Five gap types: `no_authorization`, `authorization_denied`, `expired_authorization` (visit outside the approved window), `units_exhausted`, `pending_late` (requested 7 or more days ago, undecided, visit within 7 days).
- Action types: `a2_auth_request_task` (none requested, or a pending request to chase) and `a2_auth_exception_review` (denied, expired, exhausted; the practice manager decides to reschedule, appeal, re-request or proceed).
- Acts: front desk. Never: submit to a portal, assess clinical completeness, or predict approval risk (not built). Authorization denials (CARC 197/198) are still routed by A8 to the front desk.

**Trigger and timing.** Checkpoints 7 and 2 days before a booked visit whose payer + CPT is in `auth_requirement`. CLI: `krisnnai a2 seed|sweep|replay`.

**Inputs.** `prior_authorization` and `auth_requirement` tables (migration 0011), appointments. The authorization used is the one linked by `appointment_id`, else one whose approved window holds the visit date. A request, decision or unit count dated after the checkpoint does not yet exist.

**Checks and rules.** Plain code (`rules.check`). Requirements are placeholder payer + CPT rows from `a2 seed` (default CPTs 71046, 45378, 77067), not payer policy. No model.

**What we built.** `agent.py`, `rules.py`, `config.py` (`CHECKPOINT_DAYS = (7, 2)`, `PENDING_DAYS = 7`, `PENDING_WINDOW_DAYS = 7`, `VALIDITY_DAYS = 90`), `sweep.py`, `summary.py` (includes request-to-decision turnaround). 20 tests.

**How we verified.** Synthea mini book (1,500 claims): 398 appointments needing authorization, 66 with a gap; every planted defect found and nothing else; every planted lapse was a CARC 197 denial flagged before the visit; median request-to-decision turnaround 4 days. Real Synthea run (300 patients): only 17 appointments carry a CPT in the requirement set, 2 planted defects, both found; too small to say more. Finding: matching an authorization by patient + payer + CPT let an earlier visit's authorization hide a missing one; the feed now carries `appointment_id`.

**Limits and open items.** Requirements are placeholders; no packet building, clinical check, approval-risk model or portal status checks. Spec notes CMS-0057-F prior-authorization API requirements map to A2; sign-off TBD. SLA TBD.

**R2 replay version.** Flags the visit that exceeds the authorization's approved visit count. See section 4.

---

### A3. Note Chaser: Documentation Completeness Agent

**Name and persona.** A3 Note Chaser. Stage: after the visit. Milestone M13. Code: `krisnnai/agents/a3_documentation/`.

**The problem.** Missing, unsigned or incomplete notes delay or block charges; some visits are never billed at all. KPIs: charge lag and missed-charge dollars. A15-lite reports unbilled visits; A3 owns working them.

**Desired actions.**
- Gap types: `no_note` (none 3 days after service), `unsigned_note` (started 3+ days ago, unsigned), `missing_elements` (E/M needs assessment and plan; procedure, imaging, ECG need a procedure note; screening needs a result), `missing_minutes` (timed codes 97110, 97140, 90837), `no_charge` (note exists, no charge, no claim, more than 3 days), `charge_lag` (charge keyed more than 3 days after service; a KPI, not work for a person).
- Action types: `a3_missing_note_task`, `a3_signature_task`, `a3_note_query_task` (owner provider; the stub model drafts a neutral question from element names only, never a code or suggested answer), `a3_charge_review` (owner biller; value is the expected payer payment). One proposal per visit in priority: no_charge, no_note, unsigned, missing elements.
- Never: suggest a code, make a clinical judgment, or enter a charge.

**Trigger and timing.** Visit completed, note unsigned or charge delayed. A sweeper (`visit.doc_check`) raises an event when a visit first shows a gap, when its gaps change, every 7 days while open, and once when it comes clean. CLI: `krisnnai a3 sweep|replay`.

**Inputs.** `visit_note` and `charge` tables (migration 0008), visits extract. Notes are structured element names only (no note text).

**Checks and rules.** Plain code, as of a date. Element lists are a stand-in, not a coding reference. Model use: stub drafts the neutral query only.

**What we built.** `agent.py`, `rules.py`, `config.py` (`DOC_DUE_DAYS = 3`, `SIGN_DUE_DAYS = 3`, `CHARGE_LAG_DAYS = 3`, `REPEAT_DAYS = 7`), `sweep.py`, `summary.py` (charge-lag KPI). 23 tests.

**How we verified.** Synthea book (300 patients, about 2,300 visit lines): planted and found exactly 109 missing notes, 130 unsigned, 130 missing elements, 54 missed charges (6,079.42 of expected payment, equal to A15's unbilled-visit answer key), 174 late charges (mean 1.97 days, median 1); 0 executed. Notes and signatures are simulated.

**Limits and open items.** Missing orders and visit/charge inconsistencies beyond a missing charge are not built. A real EHR note-status feed and PM charge log, and provider-lead sign-off of elements and days, are needed. SLA TBD; compliance sign-off TBD.

**R2 replay version.** Checks each billed encounter three days after the visit and flags an unsigned note; resolves the finding if the note is later signed. See section 4.

---

### A4. Code Whisperer: Coding & Charge Integrity Copilot

**Name and persona.** A4 Code Whisperer. Stage: after the visit. Strategy phase 2; built in M20 (the spec header also says M18; see conflicts). Code: `krisnnai/agents/a4_coding/`.

**The problem.** The code billed may not match what the signed note documents: over-coding is a compliance risk; under-coding leaves revenue. KPIs: coder productivity, coding denials, audit variance.

**Desired actions.**
- Two signals: `level_unsupported` (billed above the documented level; overcoding, marked compliance risk, routed first) and `level_could_be_higher` (documented above what was billed; a revenue signal the coder may decline). The dollar difference is at the payer's contract, not the patient's share.
- One action type: `a4_coding_review`, owner coder. Every card says "Suggestion only: a certified coder decides; this agent changes no code, modifier or diagnosis." No payload carries a code to apply; a test asserts no action name can change a code, submit, hold or contact a provider.
- Not judged: no note, not signed as of the claim, or baseline elements missing (that is A3's finding).

**Trigger and timing.** Per claim, at the claim event, on the signed note's named elements. CLI: `krisnnai a4 replay|variance`.

**Inputs.** Signed-note element names (A3's note feed), claims, fee schedule. No new tables.

**Checks and rules.** A placeholder level table in `config.py`, explicitly not the AMA or CMS E/M guidelines: 99214 and 99204 need `history_detailed` and `exam_expanded` on top of the baseline (`assessment`, `plan`); 99213 and 99203 need nothing more. The highest level whose elements are all documented is the "documented level". No model; reading note text with a model would need a BAA, a certified-coder accuracy audit and compliance sign-off.

**What we built.** `agent.py`, `rules.py`, `config.py`, `summary.py` (variance by provider and code). 11 tests.

**How we verified.** Synthea book (300 patients): 1,104 levelled E/M lines judged; 59 differ (5.3%): 29 over-coding signals (1,152.10 at contract) and 30 under-coding signals (1,212.56), exactly the planted ones, over 5 rendering providers; 0 executed. The note elements and differences are simulated and the level table is a placeholder.

**Limits and open items.** No ICD-10, modifier or procedure coding, no NCCI/MUE logic in A4 itself (A5 has the pair and unit checks), no note text, no model. Spec compliance note: state AI-in-utilization-review laws may apply; sign-off TBD.

**R2 replay version.** Audits physical/occupational therapy evaluation codes (97161 to 97166) against `documented_level` on the encounter line. Nothing is raised when `documented_level` is empty (the R2 case). See section 4.

---

### A5. Mirror: Claim Prevention & Digital Twin Agent

**Name and persona.** A5 Mirror. Stage: before the claim leaves. Milestone M8. Code: `krisnnai/agents/a5_prevention/`.

**The problem.** Claims that will be denied or lost to filing limits are released. KPIs: clean claim rate and first-pass paid rate (docs/metrics.md).

**Desired actions.**
- Five rules at release time:

| Rule | Fails when | Proposal |
|---|---|---|
| `required_fields` | no service date, lines or diagnosis, or a line lacks CPT or diagnosis pointer | fix task (billing) |
| `duplicate_claim` | an earlier claim has the same patient, payer, date and codes | hold review (billing) |
| `timely_filing` | fewer than 30 days left of the payer's filing limit (365 when no row) | hold review (billing) |
| `ncci_pair` | a pair in `ncci_pair` on one date: indicator 0 always, indicator 1 without a modifier | hold review (coding) |
| `mue_units` | units of one code on one date exceed `mue_limit` | fix task (coding) |

- A sixth check, `learned_pattern`, applies only after a named person approves an A9 rule; it produces an `a5_fix_task` for billing.
- Action types: `a5_fix_task`, `a5_hold_review`, both tasks for a named human. Never edits codes or claims or submits.

**Trigger and timing.** Claim created before release; the check is on the claim snapshot at release time. CLI: `krisnnai a5 seed|replay`.

**Inputs.** Claims, lines, diagnoses, tables `ncci_pair`, `mue_limit`, `payer_filing_window`, `learned_rule` (migration 0006). Not evaluated and reported on every record rather than guessed: eligibility on the date of service and authorization units (no 270/271 or authorization data in this implementation).

**Checks and rules.** Plain code. The NCCI and MUE rows are synthetic stand-ins (`97140/97530` indicator 1, `99213/99214` indicator 0; MUE `99213` = 1, `97110` = 4), not the CMS tables. The 30-day warning and 365-day default are placeholders. The strategy envisions a calibrated, interpretable denial model; none is built.

**What we built.** `agent.py`, `rules.py`, `config.py` (rule data in tables, `seed_defaults`), `summary.py`; the `RELEASE_FIX_DAYS = 2` target. 12 tests.

**How we verified.** 200-claim synthetic set (seed 5): 200 checked, 10 flagged (all `a5_hold_review`: 6 `ncci_pair`, 5 `timely_filing`, one claim fails both), 0 executed, flagged charges 3,795.20. The spec states this is not an accuracy measure because that set had no planted claim defects to score. After A9 approval on the Synthea book, A5 flagged 83 claims with `learned_pattern` (see A9).

**Limits and open items.** Needs CMS NCCI/MUE tables, a payer-rule library, eligibility and authorization data, and a calibrated denial model; all TBD. Digital-twin adjudication simulation is not built.

**R2 replay version.** Reviews each claim on its submission day (next business day for weekend claims) using authorization visit count and coverage end date, plus approved learned rules.

---

### A6. Courier: Claim Submission & Response Agent

**Name and persona.** A6 Courier. Stage: submission. Milestone M10. Code: `krisnnai/agents/a6_submission/`.

**The problem.** Rejections at the clearinghouse or payer front door (999 and 277CA) delay cash and some claims age out. KPIs: submission acceptance, rejection turnaround.

**Desired actions.**
- Built (response side only): reads a 277CA with status category A3 (returned) or A4 (not found), or a 999 with status R (rejected) or E (accepted with errors); decides whether the rejection is technical or business using the tenant table `rejection_route` (placeholder seeds; only a 999 rejection is seeded as technical; an unmapped status is business and flagged `unrouted`); identifies the likely cause from A5's failed pre-release rules.
- Action types: `a6_rejection_task` (business; owner fixes the cause) and `a6_resubmit_review` (technical; a person approves a prepared packet; the only action that could ever reach the clearinghouse adapter, at L3 at most). The packet is the claim copied verbatim with an empty `edits` list and is not an X12 file (no 837 writer). A rejected claim is resubmitted as a corrected original, not a replacement (frequency 7).
- Priority = dollars x urgency (2 within 60 days of the filing limit, else 1); `fix_by` = rejection date + 3 days.
- Never: submit directly, change a code, or auto-correct a business rejection. Not built: the release/submission side, because there is no release signal.

**Trigger and timing.** Strategy trigger is "claim approved for release"; the built trigger is an acknowledgement event. A 999 covers a transaction set, so the proposal names every claim sharing the acknowledged GS06 and ST02 (examined in detail up to 25 per acknowledgement). CLI: `krisnnai a6 seed|replay`.

**Inputs.** `ack_999`, `ack_277ca`, claims, provider master data, A5's filing window and A15 pricing (`amount_priced`).

**Checks and rules.** Plain code: `rejection_routed`, `claim_matched`, `packet_unchanged`, `within_filing_limit`, `amount_priced`. No model.

**What we built.** `agent.py`, `config.py` (route table, `FIX_DAYS = 3`, `FILING_RISK_DAYS = 60`), `packet.py`, `summary.py`. A live L3 policy was tested end to end: the proposal waits for a named approval and only the clearinghouse stub records it as "not sent". 15 tests.

**How we verified.** 200-claim synthetic set: the 4 planted 277CA rejections each got a decision (business, owner billing, with a deadline); 0 executed, 0 unrouted, 542.97 affected (equal to A15's rejection total). The set has no 999 rejections, so the technical path is covered only by hand-built tests. Not an accuracy measure.

**Limits and open items.** No X12 837 writer, real partner adapter, 276/277 status inquiry, or signed-off technical rejection codes; strategy states resubmission is irreversible, so it stays at L2 until compensating controls and client authorization exist. The spec says to verify routing codes against current X12 code lists.

**R2 replay version.** Raises one decision per history event that is a clearinghouse rejection, with a billing-lead approval and a suppressed write-back (shadow).

---

### A7. Hunter: AR Next-Best-Action Agent

**Name and persona.** A7 Hunter. Stage: after submission, unpaid claims. Milestone M9. Code: `krisnnai/agents/a7_ar/`.

**The problem.** Claims sit unpaid past the payer's usual payment time and nobody follows up before the filing window shrinks. KPIs: days in AR, AR over 90 days, touches per claim.

**Desired actions.**
- Ranks claims and proposes: `a7_status_check_task` (billing), `a7_resubmit_review` (claim returned by the 277CA; billing), `a7_escalate_review` (no answer for 90+ days; A/R lead). None resubmits, writes off, refunds or edits a code.
- Priority = unpaid amount x (1 - chance it pays on its own) x urgency; urgency = 1 + days past expected / expected days (capped at +2), plus 1 when fewer than 60 days remain before the filing limit.
- `krisnnai a7 inbox` prints ranked cards, latest per claim, excluding claims the payer has since answered.
- Not built: real 276/277 status inquiry, detecting payer records requests, routing to registration or authorization.

**Trigger and timing.** A sweeper raises one `ar.followup_due` event per open claim once it passes the payer's expected payment date, and every 14 days while open. CLI: `krisnnai a7 sweep|replay|inbox`.

**Inputs.** Claims, remits (a payer answer closes the item), 277CA, payer payment history, fee schedule (A15 pricing), A5's filing window. No new tables.

**Checks and rules.** Plain code: `claim_open`, `past_expected_date`, `acknowledged`, `amount_priced`, `history_sufficient`. Expected days to pay = the payer's median over earlier paid claims (point in time). Chance a claim pays on its own = (paid + 1) / (n + 2) over that payer's claims at least 90 days old. Placeholders: 5-claim minimum history, 30-day default, 90-day maturity, 14-day repeat, 60-day filing-risk window, 90-day escalation age. No model.

**What we built.** `agent.py`, `sweep.py`, `timing.py`, `inbox.py`, `summary.py`. 17 tests.

**How we verified.** Synthetic open-AR set (80 claims over 200 days, about one in ten stuck, one in eight returned; weekly sweep 2026-03-01 to 2026-06-30): 108 follow-up events on 26 claims; proposals 30 status checks, 23 escalations, 55 resubmit reviews; 0 executed. The spec states this is not an accuracy measure.

**Limits and open items.** Approval for appeals, resubmission or write-off is by a human; SLA TBD. Payers' real status data is not yet read.

**R2 replay version.** Looks at each claim at the payer's standard turnaround days plus 14; if no remit is known by then it flags it and raises a follow-up task for an A/R specialist. A payer with no standard turnaround in R2 is skipped (abstains).

---

### A8. Advocate: Denial Resolution & Appeal Agent

**Name and persona.** A8 Advocate. Stage: denials. Milestone M7. Code: `krisnnai/agents/a8_denial/`.

**The problem.** Denials are not worked before the appeal window closes, or are routed to the wrong person. KPIs: denial overturn rate, recovery dollars, cycle time.

**Desired actions.**
- Classifies the root cause with the tenant table `carc_route`; names the owner (front desk, coding or billing); computes the deadline (payment date + payer appeal window, default 180 days); estimates expected recovery (amount at risk x smoothed payer+CARC win rate; win probability = (wins + 1) / (n + 2) over earlier denials of the same payer + CARC later paid and known at decision time); drafts an appeal with the stub model from payer code, CARC, CPT, amount and dates only (no names, member ids or birth dates).
- Action types: `a8_fix_task`, `a8_appeal_task`, `a8_write_off_review`, `a8_takeback_review`, `a8_recoupment_review`. Proposes only.
- Default routes (placeholders): CARC 27, 31, 22 coverage (front desk, correctable); 197, 198 authorization (front desk, appealable); 4, 11 coding (coding, correctable); 97 bundling and 50 medical necessity (coding, appealable); 16 missing information (billing, correctable); 18 duplicate and 29 timely filing (billing, write-off review). A CARC with no row routes to billing as write-off review and is flagged unrouted.
- Never: submit an appeal or write off. Not built: gathering supporting evidence, tracking outcomes.

**Trigger and timing.** 835 denial (CLP02 4 or a denied service line), takeback (CLP02 22) or recoupment (PLB reason WO or 72). CLI: `krisnnai a8 ...` (replay).

**Inputs.** 835 remits and PLB, claims, CAS adjustments, fee schedule (A15 pricing), earlier remits for win history, tables `carc_route` and `payer_appeal_window`.

**Checks and rules.** Routing and windows are tenant tables, not code. Model: the stub drafts the appeal text only.

**What we built.** `agent.py`, `routing.py`, `history.py`, `summary.py`. 19 tests. Spec docs/specs/A8.md redone on the Appendix A template.

**How we verified.** Replay on the synthetic set: 23 decisions, 0 executed (the spec's figure; the build plan's goal was a category, owner and deadline for every denial). No planted-versus-found scorecard is documented for A8.

**Limits and open items.** Appeal submission is irreversible, so it stays at L2 until compensating controls and client authorization exist; tasks proposed today are reversible. Evidence gathering, outcome tracking and CARC rows beyond the seed set are open. Win-rate is a simple historical rate; a model is later work.

**R2 replay version.** One decision per row in the `denial` table: routes by CARC, owner role, appeal deadline and a high/medium severity depending on days to deadline.

---

### A9. Coach: Denial Prevention Learning Agent

**Name and persona.** A9 Coach. Stage: denials (learning). Milestone M15. Code: `krisnnai/agents/a9_learning/`.

**The problem.** The same preventable denial recurs because no front-end rule stops it. KPI: preventable denial recurrence.

**Desired actions.**
- Finds clusters (payer + CPT + CARC) over claims the payer answered in the last 120 days; a cluster qualifies at 5 denied claims and a 30% denial rate. A weaker cluster sharing 80% of its denied claims with a stronger one for the same payer and CARC is dropped. If A5 had already flagged 80% of the cluster's claims before release, no rule is proposed.
- Action type: `a9_rule_proposal_review`, owner practice manager; the sweeper raises one `denial.pattern_found` event per new cluster. The proposal carries in-sample denial rate, recall and expected payment denied.
- A rule has effect only after `a9 approve --rule KEY --by NAME`; A5 then fails matching claims with `learned_pattern`. `a9 reject` is also available.
- `a9 forward` tests each rule on claims filed after it was proposed; `a9 attribution` links each denial to the upstream agent (A1, A2, A3, A5) that had flagged it, or none.
- Never: activates a rule without a named approval.

**Trigger and timing.** Confirmed denial outcome or recurring defect; the sweeper runs about every 30 days (`SWEEP_EVERY_DAYS = 30`). CLI: `krisnnai a9 sweep|replay|approve|reject|forward|attribution`.

**Inputs.** Event history rebuilt as of a date (outcomes from remits), A5 decision records, `learned_rule` table.

**Checks and rules.** Plain code. One rule family only; clustering on diagnosis, modifier, provider or free text and model-written explanations are not built. Config: `MIN_DENIALS = 5`, `MIN_RATE = 0.30`, `ALREADY_FLAGGED = 0.80`, `EXPLAINED_OVERLAP = 0.80`, `WINDOW_DAYS = 120`, `SAMPLE_CLAIMS = 5`; CARC 45 is not a denial. All placeholders.

**What we built.** `agent.py`, `clusters.py`, `sweep.py`, `decide.py`, `evaluate.py`, `summary.py`, `config.py`. 18 tests.

**How we verified.** Synthea book with one planted pattern (SYNANTHEM denies CPT 99213 with CARC 16 at 60% from 2026-01-01): exactly one proposal (6 of 16 claims denied, 38% in window, recall 100%, A5 had flagged none, 502.20 denied). After approval A5 flagged 83 claims; the forward test on later claims flagged 24 and hit 11 (precision 46%, recall 100%, 910.80 would have been held). Attribution over 226 denials: 40 had an A1 flag, 58 an A3 flag, 46 an A5 flag, 104 no upstream flag (counted once per flagging agent). Findings: measuring the rate over all history diluted a recent change (now a 120-day window); re-running A5 after approval appends records rather than replacing them. The pattern was planted by the same team that wrote the rule.

**Limits and open items.** Thresholds are placeholders; manager approval SLA TBD; the replay engine on R2 uses different thresholds (below).

**R2 replay version.** Looks daily for two templates (CARC 50 plan-of-care rule; CARC 97 distinct-service modifier rule) per payer with 10 or more matching denials in the last 60 days; proposes a rule that a manager approves five business days later. The CARC 50 rule is not learned while no plan-of-care documents exist.

---

### A10. Auditor: Contract & Underpayment Agent

**Name and persona.** A10 Auditor. Stage: payment. Milestone M12. Code: `krisnnai/agents/a10_underpay/`.

**The problem.** Payers pay less than the contract rate and nobody checks line by line. KPI: underpaid dollars detected (the strategy also names "recovered"; this build only detects).

**Desired actions.**
- For each paid line of an 835 claim payment: gap = contract allowed (fee schedule x units) - (paid + patient share on the line). Reversals and denials are A8's.
- Action types: `a10_dispute_review` (owner finance; a dispute package with payer, claim, short lines with allowed/paid/patient share/gap, cause, deadline, and a draft letter from the stub model using codes and dollars only) and `a10_contract_check_task` (owner finance; no fee-schedule row, so confirm the rate first; expected value 0).
- Likely cause from the CARC on the short line (placeholder map): only CARC 45 contract_pricing; 4 modifiers; 59 and 97 bundling_ncci; 151 units_charges; 50 medical_necessity; 197 authorization; 29 timely_filing; B15 and N130 payer_policy; 16 or unknown data_coding (lower confidence). These are the nine root causes in the source RCM document.
- Patterns: short lines for one payer, CPT and cause are bucketed by gap percentage; the commonest gap and its neighbours within one point form a pattern when there are at least 5 lines and at least half the short lines for that code; reported as a likely rate change or stale fee-schedule row with one dispute package.
- Never: submit a dispute, write off, or change anything.

**Trigger and timing.** ERA/EOB received or contract updated; one decision per paid 835 claim payment. CLI: `krisnnai a10 replay|patterns`.

**Inputs.** 835 remits, fee schedule (rows used only when effective on the service date), `payer_appeal_window` (default 180 days). Real contracts and contract extraction are not available.

**Checks and rules.** Plain code: `claim_matched`, `short_paid` (gap at least 1.00 on fee-schedule pricing; at least 20% of the expected amount when only payer history prices the line), `contract_priced`, `appeal_window_open`. Reuses A15-lite's pricer. No model.

**What we built.** `agent.py`, `config.py` (`FEE_FLOOR = 1.00`, `FALLBACK_FLOOR = 0.20`, `MIN_PATTERN_LINES = 5`, `BUCKET_WIDTH = 0.01`, `DOMINANT_SHARE = 0.50`), `patterns.py`, `summary.py`. 17 tests.

**How we verified.** Synthea book (300 patients, 18 months, 1,776 claims, planted 12% rate cut on SYNMEDICARE 99213 from 2026-06-01): 1,335 paid payments checked, 166 short-paid for 3,880.53, all dispute reviews, 0 executed. The 166 equal the planted 142 one-off underpayments plus the 24 rate-cut lines; A10 and A15-lite agree to the cent. One pattern for the rate cut (24 lines, 12.0%, 24% of that payer's paid 99213 lines). With a pattern minimum of 3 a spurious second pattern appeared from three unrelated one-offs, so the minimum is 5. Planted problems and rules share a design, so this shows wiring and arithmetic, not real-world detection.

**Limits and open items.** Needs real contracts, contract extraction with an approved model, dispute submission, and payer multi-procedure rules. A10 falls back to payer-history pricing if reliable fee schedules are not available.

**R2 replay version.** Per remit event, compares each line's allowed amount with the expected allowed (reduced 15% for the CQ modifier); a gap above 3% of expected is a finding, with a billing-lead dispute-package task. The R2 count was originally inflated by denied lines (section 4).

---

### A11. Bookkeeper: Payment Posting & Reconciliation Agent

**Name and persona.** A11 Bookkeeper. Stage: payment. Milestone M17. Code: `krisnnai/agents/a11_cash/`.

**The problem.** Cash is paid but missing from the bank, short, duplicated, or never posted to patient accounts. KPIs: days to post, unapplied cash, reconciliation variance.

**Desired actions.**
- Gap types: `deposit_missing` (none 5 days after payment), `deposit_variance`, `duplicate_deposit`, `not_posted` (no posting 3 days after payment), `partial_posting` (unapplied cash), unidentified deposit (raised 7 days after arrival). `deposit_late` and `posting_late` (over 7 days) are KPIs only.
- Action types: `a11_deposit_investigation_task` (finance), `a11_posting_task` (payment poster), `a11_unapplied_review` (finance), `a11_unidentified_deposit_review` (finance).
- Unapplied cash = not posted + partially posted amounts; variance = missing + short + duplicate amounts.
- Never: posts payments, accesses a bank, or writes back.

**Trigger and timing.** ERA/EOB/lockbox/bank transaction received; sweeper repeats open gaps every 7 days. CLI: `krisnnai a11 sweep|replay`.

**Inputs.** 835 payments, `bank_deposit` and `posting` feeds (migration 0012). Matching of deposits: by trace number; with no trace, payer + amount within 30 days, one deposit to one payment in date order. A zero-dollar remittance has no cash to reconcile.

**Checks and rules.** Plain code (`rules.reconcile`, `match_deposits`). Config: `DEPOSIT_DUE_DAYS = 5`, `DEPOSIT_LATE_DAYS = 7`, `POST_DUE_DAYS = 3`, `POST_LATE_DAYS = 7`, `MATCH_WINDOW_DAYS = 30`, `UNIDENTIFIED_AFTER_DAYS = 7`, `REPEAT_DAYS = 7`, `TOLERANCE = 0.00`. Model use: "TBD at spec review"; none.

**What we built.** `agent.py`, `rules.py`, `ledger.py`, `sweep.py`, `summary.py`, `config.py`. 21 tests.

**How we verified.** Synthea book (300 patients): 5,782 events. Planted and found exactly: 33 missing deposits (3,992.73), 34 short deposits (316.74), 20 duplicates (2,630.02), 44 never posted (4,976.71), 31 partly posted (656.49), 25 unidentified deposits (8,093.69); 80 late postings; late deposits 52 found against 49 planted (the 3 extra come from equal payer-and-amount payments whose untraced deposits cannot be told apart). Unapplied cash 5,633.20, variance 6,939.49; median 2 days to deposit and 1 to post; 0 executed. Finding: crediting every equal-amount untraced deposit to every equal-amount payment produced false duplicates, so deposits are assigned one to one.

**Limits and open items.** No posting write-back (gated; spec requires approval until accuracy criteria are met), no patient payments, bank file variants (BAI2, lockbox) not covered. The feeds and defects are simulated.

**R2 replay version.** The day after each payment, flags a payer payment with an unapplied (unposted) amount and raises a post-remit task for the payment poster.

---

### A12. Concierge: Patient Financial Engagement Agent

**Name and persona.** A12 Concierge. Stage: patient balance. Milestone M19. Code: `krisnnai/agents/a12_patient/`.

**The problem.** After insurance pays, the patient's share goes unstatemented or unchased, or is chased when it should not be (disputes, hardship). KPIs: patient collections, days patient AR.

**Desired actions.**
- A staff-facing worklist only. Per claim's patient share (835 CLP05 of the latest non-reversed, non-denied remit) less patient payments, read in order: `dispute_hold` (dispute or hardship stops everything), `credit_balance` (overpayment), payment plan (not chased), `small_balance` (under 10.00; a staff decision), `no_statement` (7 days after the share was confirmed), `balance_aging` at 30, 60 and 90 days with a sent statement.
- Action types: `a12_statement_task`, `a12_followup_task`, `a12_dispute_review`, `a12_credit_review`, `a12_small_balance_review`. The plain-language explanation on each card is a template from PR reason codes (deductible, coinsurance, copay): no model, no identifiers.
- Never: sends a statement, text, call, email or portal link; takes payment; refunds, writes off or adjusts a balance. A test asserts the action names. This is built in and not configurable.

**Trigger and timing.** Patient responsibility confirmed or a balance ages; repeat every 14 days. CLI: `krisnnai a12 sweep|replay`.

**Inputs.** `patient_payment` and `patient_statement` feeds (migration 0014), remits. Secondary balances are not tracked (no COB owner).

**Checks and rules.** Plain code (`rules.check`, `explain.py`). Config: `STATEMENT_DUE_DAYS = 7`, `AGING_FROM_DAYS = 30`, `STAGES = (90, 60, 30)`, `SMALL_BALANCE = 10.00`, `REPEAT_DAYS = 14`, stage weights 1.0/1.5/2.0 (priority = open balance x weight).

**What we built.** `agent.py`, `rules.py`, `data.py`, `explain.py`, `sweep.py`, `summary.py`, `config.py`. 19 tests.

**How we verified.** Synthea mini book (1,200 claims): every planted outcome found with its dollars and nothing else; collections and open balance consistent with the answer key; 0 executed. The first answer key described only claims older than 45 days, so five small open balances looked like false positives; the agent was right and the key was incomplete.

**Limits and open items.** Outreach needs legal review of TCPA consent, Reg F contact rules and state collection law, a consent source, an approved messaging vendor under a BAA, and payment processing. Compliance review is required before any outreach; none is built.

**R2 replay version.** Looks 30 days after service at patient-owner AR snapshots 20 or more days old (latest snapshot known that day) and generates a statement row with a dunning level; about one in four becomes a decision and a follow-up task. See section 4.

---

### A13. Credentialing: Credentialing & Enrollment Agent

**Name and persona.** A13, shown as "Credentialing" in the replay engine (no separate persona name documented). Stage: across the practice. Built in M18 (the spec header also says M20; see conflicts). Code: `krisnnai/agents/a13_credentialing/`.

**The problem.** Claims for providers who are not enrolled, whose enrollment has lapsed, or who are excluded are denied or create compliance risk. KPIs: credentialing denials, enrollment cycle time.

**Desired actions.**
- Gap types: `billing_without_enrollment` (services in the last 90 days with no enrollment, or denied/terminated), `enrollment_expired` (expiry passed with services since; dollars = expected payment of those services), `expiring_soon` (active, expires within 90 days), `pending_too_long` (pending 90 or more days; a pending application alone is not claim risk), `excluded_provider` (latest screening result excluded), `screening_stale` (over 35 days, or never).
- Action types: `a13_enrollment_task` (owner credentialing: renew, chase, run the screening) and `a13_enrollment_exception_review` (owner compliance owner decides whether to hold claims or stop scheduling).
- Never: holds a claim, stops scheduling, or contacts a payer.

**Trigger and timing.** Provider added; expiry or enrollment status changes. Sweeper raises events on a first gap, a change in gaps or services at risk, every 14 days, and once when a gap clears. CLI: `krisnnai a13 sweep|replay`.

**Inputs.** `enrollment` and `provider_screening` feeds (migration 0013); service evidence is the visit extract, since the claim carries only the billing NPI. Rendering provider is not parsed from the 837.

**Checks and rules.** Plain code (`check_enrollment`, `check_screening`). Config: `EXPIRY_WARN_DAYS = 90`, `PENDING_DAYS = 90`, `SERVICE_WINDOW_DAYS = 90`, `SCREENING_STALE_DAYS = 35`, `REPEAT_DAYS = 14`. No model.

**What we built.** `agent.py`, `rules.py`, `data.py`, `sweep.py`, `summary.py` (cycle time), `config.py`. 21 tests.

**How we verified.** Synthea mini book (1,500 claims): every planted defect found and nothing else, with dollars at risk equal to the answer key to the cent; the lapse defects were real CARC 185 denials from their date. Findings: an open gap's card kept the dollars from the day it was raised, so the sweeper now also raises an event when services at risk change; an answer-key file named `enrollment_truth.csv` was picked up by the loader as a feed (renamed `credentialing_truth.csv`).

**Limits and open items.** No provider-location combinations, application packets, portal, or live OIG/SAM lookups; compliance owner approval SLA TBD.

**R2 replay version.** Looks at enrollment rows of type `enrollment` and flags one 60 days before expiry (or at the replay start). The R2 enrollment table is empty.

---

### A14. Captain: RCM Operations Control Tower

**Name and persona.** A14 Captain. Stage: across the practice. Baseline KPIs M4; expanded scope M11. Code: `krisnnai/agents/a14_tower/`.

**The problem.** No one sees all the agents' open work, the expected cash, or the operational warning signs in one place. KPIs: cash forecast accuracy, backlog, productivity.

**Desired actions.**
- `compute_tower(engine, tenant, as_of)` (read-only, point in time) returns KPIs, a cash forecast, the **decision inbox** (open work across A5, A6, A7 and A8; the latest card per claim minus anything resolved), backlog, signals and pending approvals. Ranking scales across agents are not calibrated against each other (a sign-off item).
- Nine baseline KPIs from M4 as SQL with an as-of date: clean claim rate, first-pass paid rate, denial rate by CARC/payer/CPT, days in AR, AR over 90, net collection rate, underpayment dollars, charge lag, rejection rate (`docs/metrics.md`).
- Cash forecast: for an open claim of age a with the payer's smoothed share q of mature, unrejected claims that ever pay and its days-to-pay curve F, chance of payment in week k = q x (F(a+7k) - F(a+7k-7)) / (1 - q x F(a)). A payer with fewer than 5 paid mature claims gets a flat 60-day ramp (flagged). Interval = 80% (1.28 sd).
- Four signals: `backlog_growth` (open items up 25% and at least 5 in a week), `payer_slowdown` (median days to pay of the last 30 days at least 7 days slower than the prior 90, at least 5 paid claims each), `rejection_spike` (rejection share of the last 14 days at least 5 points above the prior 60, at least 10 claims), `deadline_critical` (any open item due within 7 days or overdue; never muted).
- Action type: `a14_escalation_review`, owner operations leader, at most one per day when a signal fires; carries signals, backlog, 28-day forecast and top inbox items. It changes no resource, assigns no work and writes nothing back.

**Trigger and timing.** Continuous; daily review. CLI: `krisnnai tower`, `krisnnai a14 sweep|replay`.

**Inputs.** All events and other agents' decision records. Not available: task logs and staff capacity (productivity, staffing, load balancing).

**Checks and rules.** Plain code. The strategy mentions prediction intervals from a model; the built forecast is a statistical method, with no fitted model and no AI model.

**What we built.** `agent.py`, `cards.py`, `forecast.py` (with `backtest`), `signals.py`, `tower.py`, `summary.py`. 18 tests. There is no UI because FastAPI cannot load on the development PC (Windows Smart App Control blocks `pydantic-core`); the tower is a JSON-ready dictionary.

**How we verified.** Backtest on the synthetic open-AR set (400 claims, fixed payer delays, 10% stuck, 12.5% returned): eight weekly forecasts gave a weighted absolute percentage error (WAPE) of 6%, with the actual inside the 80% range in 6 of 8. Thinner history is looser (100 open claims: 21%; 40: 30%). Flaws found and fixed: using all paid claims made payers look fast (now mature claims only); the chance-to-pay counted rejected claims the forecast excludes (now unrejected only); the first synthetic set chose open claims because they were unpaid, which made any backtest unfair. These numbers show the method works on data with a known answer, not on a real practice.

**Limits and open items.** Productivity, staffing and load balancing, and a fitted forecast model are not built; the strategy lists the operations leader as the approver of resource changes; SLA TBD.

**R2 replay version.** Each Monday writes a weekly cash forecast per payer (expected amount, a low-to-high range of 70% to 130%, 80% interval label, model name "rules"); escalates open tasks overdue by more than 3 days. A payer with no standard turnaround is skipped.

---

### A15. Detective: Revenue Assurance Investigator

**Name and persona.** A15 Detective (full investigator). Stage: across the practice. Milestone M21. Code: `krisnnai/agents/a15_investigator/`.

**The problem.** Collections against contract drift down for a payer or service line and no one knows why. KPIs: net collection rate and detected leakage; "recovered leakage" appears in the strategy but this build does not claim it.

**Desired actions.**
- Per remit line (matched, not reversed, priced from the fee schedule): expected = contract allowed; actual = paid + patient share (a denied line pays nothing); realisation = actual / expected. A slice (a payer, or a payer and CPT) is flagged when realisation over the **recent window (56 days)** fell **5 points or more** below the **baseline window (the 180 days before)**, with at least **8 lines** in each window and **500.00** of contract value in the recent window. Dollar impact = fall x recent expected.
- Each shortfall line in the recent window is explained by the A15-lite finding on its claim: underpayment on that line, else the claim's denial (category and CARC), else an unexplained adjustment, else **unexplained** (reported, never guessed).
- An upstream table tags each claim with the agents (A1, A2, A3, A4, A5, A13) whose decision record flagged it at or before the day the claim became known; claims nobody flagged are counted under `none`. This is attribution by key match to leaks already detected, not proof of cause.
- Action type: `a15_investigation_review`, owner revenue assurance lead, carrying the slice, the fall, the cause table and the upstream table. A card; nothing is executed.
- A ledger (`investigate ledger`) compares detected amounts with what was later paid.

**Trigger and timing.** The sweeper's `revenue.variance` event, every 28 days by default, one per flagged slice, again when the fall or top cause moves (2 points), and once when it clears. CLI: `krisnnai investigate sweep|replay|ledger`.

**Inputs.** Remits, claims, fee schedule, A15-lite's findings, other agents' decision records, visits and appointments (to match claims to upstream flags). No new tables.

**Checks and rules.** Plain code, no model; all thresholds are placeholders for the revenue assurance lead (`config.py`: `RECENT_DAYS = 56`, `BASELINE_DAYS = 180`, `MIN_LINES = 8`, `MIN_EXPECTED = 500.00`, `DROP_POINTS = 0.05`, `CHANGE_POINTS = 0.02`, `SWEEP_EVERY_DAYS = 28`).

**What we built.** `agent.py`, `variance.py`, `causes.py`, `sweep.py`, `ledger.py`, `summary.py`, `config.py`. 13 tests (full A15 only; A15-lite's 16 are in its own section).

**How we verified.** Real Synthea book (300 patients, planted rate cut `SYNANTHEM:99213` from 2026-08-01 at 30 and planted denial pattern `SYNHUMANA:99214`, sweeps every 28 days from 2026-04-14):
- The rate cut is flagged as slice `SYNANTHEM|99213`, top cause underpayment, 10 lines, 329.00, exactly the planted underpayments paid in the window.
- The denial pattern is flagged as `SYNHUMANA|99214`, top cause `denial:medical_necessity`, 2 lines, exactly the 2 planted claims.
- Three other slices (`SYNBLUECROSS`, `SYNMEDICARE|99213`, `SYNMEDICARE|99214`) plus the `SYNHUMANA` payer total were also flagged at the last sweep: random denials and timely-filing losses in small samples. These are false alarms against the answer key, which is why the thresholds are placeholders.
- On the rate-cut slice 485.40 of 697.00 shortfall was flagged by no upstream agent (an underpayment is not visible to A1 to A5); A3, A5 and A1 flagged the denials mixed into the same slice.
- Ledger, detected 2026-08-31, paid by 2026-10-14: 36,008.24 detected, 0.00 later paid. The simulator has no appeal, resubmission or re-billing behaviour, so zero is correct and says nothing about real recovery.

**Limits and open items.** No volume or payer-mix decomposition, no seasonality, no location or provider slices; cause is attribution, not causation; the ledger counts later payment, not work done or incremental recovery; A9's and A10's proposed patterns are not yet named on the review card. The engine gaps in section 2 (kill switch, maker-checker, versioned policy, identity resolution, before/after values) still stand.

**R2 replay version.** Each Monday over the last 60 days, per payer + CPT cell with at least 20 priced lines and realisation below 95% of contract, flags it (one flag per cell per 30 days). It differs from the library rule (56 vs 180 days, 5-point fall).

---

### A15-lite. Scout: Revenue leakage diagnostic (read-only)

**Name and persona.** A15-lite (Scout in the preview). Stage: across the practice, look-back. Milestone M5; the first sellable piece ("land motion"). Code: `krisnnai/agents/a15_lite/`.

**The problem.** A practice does not know how much revenue it is leaking or where, so there is no validated baseline.

**Desired actions.**
- Read-only diagnostic: `krisnnai a15 --tenant ID --as-of DATE --out DIR [--ground-truth ground_truth.csv] [--g0-tolerance 0.01]`. Writes `a15_lite.json` and `a15_lite.xlsx`. It changes no claim, remit or setting, recovers no money, proposes no action and writes no decision record.
- Six finding types, one finding per item:

| Type | Rule | Dollars | Window | Agent that would address it |
|---|---|---|---|---|
| `denial` | first remit denied (CLP02 4) | expected payer payment of its lines | appeal, from payment date | by CARC category |
| `timely_filing` | denial with CARC 29 | same | always structural | A5 |
| `underpayment` | paid line, allowed - (paid + patient share) > 0 | the shortfall | appeal | A10 |
| `rejection` | 999 rejected or 277CA A3/A4, never answered by an 835 | expected payer payment | filing, from service date | A6 |
| `unbilled_visit` | PM visit with no claim for that payer, patient, date and CPT | expected payer payment | filing | A3 |
| `unexplained_adjustment` | CO/OA/PI adjustment other than CARC 45 on a paid line not already an underpayment | the adjustment | appeal | A7 |

- Each finding is split recoverable vs structural (recoverable if the appeal or filing window is still open) and mapped to an agent using the strategy numbering (coverage A1; authorization A2; coding and bundling A4; missing information, duplicate and timely filing A5; medical necessity and other A8).
- Report: summary, by payer, CPT, location (place of service) and provider; recoverable vs structural; ranked opportunities (recoverable first, then dollars); baseline KPIs; reconciliation. No patient identifiers.

**Trigger and timing.** On request, as of a date, on historical data.

**Inputs.** Claims, remits, fee schedule and visits (PM extract); data known on or before the as-of date.

**Checks and rules.** Order of work: (1) **G0 reconciliation**: claim total = sum of its lines, remit billed and paid = sum of its lines, payment BPR02 = remits less PLB, at least 99% of remits linked to a claim; if any check is off beyond the tolerance (default 0.01) the run stops with exit code 2 and writes nothing. (2) Snapshot. (3) Pricing: allowed = fee schedule x units (latest row in force, first modifier); with no fee row, the payer's median received per unit for that CPT, flagged `fallback`; no data is `unpriced` ($0). The patient share is learned per payer, not hard-coded. (4) Detection. Fallback-priced underpayments flag only when 20% or more below the median. Defaults: appeal window 180 days, filing window 365 days, per-payer overrides exist. No model.

**What we built.** `config.py`, `g0.py`, `snapshot.py`, `expected.py` and `pricing.py`, `detect.py`, `evaluate.py`, `report.py`. Tests: 16 (`test_a15.py`), covering planted issues, G0 stop, JSON/Excel agreement, no identifiers, read-only, tenant isolation and CLI.

**How we verified.** On the 200-claim synthetic set (`--ground-truth` prints precision, recall and "right dollars + status" per type): all 49 planted issues found with the right type, dollars and recoverable/structural status, with no extra findings. The planted set was made by the same team that wrote the rules.

**Limits and open items.** Multiple-procedure reductions in expected allowed are not modelled; payer-specific windows from contracts are not used; claim-level CAS on multi-line remits is used for denial reasons only; replacement claims are not folded into the claim they replace. A validated leakage baseline on a real partner's data has not been run.

---

## 4. Status on the R2 database

**What this is.** The history traces were run over the whole `krisnnai_r2` history (119,941 claims, 2023-11-06 to 2026-11-06, 1,097 days) in shadow mode, and the results were saved in R2's nine `agent_*` tables (`tools/replay/r2_run.py`; mapping in `docs/replay_r2_mapping.md`). The replay (`tools/replay/engine.py`) walks the calendar day by day and lets each agent see only data known that day. The run had 0 integrity errors and every reconciliation check on the saved rows passed. The agents are rules-based and nothing was sent anywhere. **The data is generated, so these counts show how the rules behave on this dataset. They are not real-world performance, and no dollar figure here is recovered or saved money.**

**Saved rows.** `agent_run` 11,490; `agent_decision` 38,565; `agent_decision_check` 73,096; `agent_finding` 31,022; `agent_task` 33,138; `agent_approval` 8,930; `agent_writeback` 8,463; `agent_value` 35,289; `agent_forecast` 1,206. Detected amounts: about $2.14M "recoverable" and $1.19M "structural" (payer-wide or process problems); both are detected, not recovered.

| Agent | Result on R2 | What it means |
|---|---|---|
| A1 Gatekeeper | 3,510 decisions, all "clear" | Eligibility checks that passed; no coverage problem was found to flag |
| A2 Permit Clerk | nothing | No visit-cap overruns in the data |
| A3 Note Chaser | 131,243 items, 0 decisions | All notes are signed, so nothing to chase |
| A4 Code Whisperer | nothing | `documented_level` is empty, so there is nothing to compare billed levels to |
| A5 Mirror | 119,941 claims reviewed, 3,678 decisions, all released | Authorization and coverage checks never fail in this data; the plan-of-care rule is switched off until plan-of-care documents exist |
| A6 Courier | nothing | No clearinghouse rejections in the data |
| A7 Hunter | 116,033 items, 0 decisions | No claim waited past the payer's standard turnaround (derived median: 17 to 31 days) plus 14 days |
| A8 Advocate | 30,826 denials classified | Each denial got a CARC route, owner, deadline, finding and task (30,826 of each) |
| A9 Coach | 0 rule proposals | No payer pattern reached the learning threshold |
| A10 Auditor | 117,542 items, 0 decisions | After the correction below: no real underpayment, because allowed always equals expected on paid lines |
| A11 Bookkeeper | 355 decisions, all "match" | Payments with nothing unapplied; no exception to raise |
| A12 Concierge | 743 items, 196 findings and tasks | Patient balances in the month-end snapshots that are old enough to review |
| A13 Credentialing | nothing | The enrollment table is empty by design (no EDI enrollment data) |
| A14 Captain | 1,206 forecasts, 63 escalations | Weekly per-payer cash forecasts; overdue tasks escalated |
| A15 Detective | 0 | After the correction below, no payer + CPT cell pays under 95% of contract |

**Corrections made before the final run.** (1) R2 had no plan-of-care documents, so the plan-of-care rule said "missing" for every claim and the learned rules held everything (45,314 false positives); it now says "unknown" and the rule abstains. (2) 30% of claims were submitted on non-business days and were never reviewed; A5 now reviews them on the next business day. (3) A12 used the one current balance snapshot for every historical date, which leaks the future; it now uses the latest month-end snapshot on or before the review date. (4) The denial stage had set `allowed_amount` to 0 on 26,363 denied lines, which A10 and A15 read as underpayments; a denied line now has no allowed amount in the compatibility view, which removed 26,363 false A10 findings and the A15 flags that depended on them. (5) `payer.standard_turnaround_days` was empty for all payers; it is now the observed median days from submission to first payment (derived from the generated data, so it carries mild look-ahead).

**What the agents did not catch.** The data generator built five denial rules into the history (Medicare dental CARC 96, E/M with an injection and no modifier 25 CARC 4, unit and frequency limits CARC 151, preventive visit without a routine diagnosis CARC 11, missing authorization CARC 197), about 18,800 denials. The agents' pre-submission checks (A5) do not contain those rules, so **none of them was caught before the denial**; A8 handled them afterwards. This is a real finding about the current rule set, and the obvious next step is to add those five checks to A5 as payer rules.

**Reading the table.** "Nothing" and "0" mean the rule found nothing to flag in this dataset, either because the condition does not occur in the generated data or because the table that would feed the rule is empty. They are not a pass or a failure of the agent. Known data gaps: no `document` rows, no `enrollment` rows, no clearinghouse rejections, `documented_level` empty, `unapplied_amount` zero on every payment, and R2's agent tables have no columns for autonomy level, proposed-action payload or execution result, so the decision record is only partly stored.

---

## Sources used

`CLAUDE.md`; `docs/specs/A1.md` to `A15.md`, `a15_lite.md`, `engine.md`, `ingest.md`, `match.md`; `docs/ARCHITECTURE.md`, `BUILD_PLAN.md`, `ROADMAP.md`, `ui_mapping.md`, `DATA_CONTRACT.md`, `replay_r2_mapping.md`; `docs/strategy_v5.docx` (read by extracting its XML, as pandoc is not installed); code under `krisnnai/agents/`, `krisnnai/engine/`, `krisnnai/knowledge/`; tests under `tests/`; `tools/replay/engine.py`.
