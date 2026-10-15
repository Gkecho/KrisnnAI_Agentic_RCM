# KrisnAI RCM roadmap: all 15 agents

Source: `KrisnnAI_RCM_Strategy_v5_Redline.docx` (Section 3 portfolio and release waves, Section 10 MVP, Section 11 180-day roadmap,
Appendix A spec template). `docs/BUILD_PLAN.md` was written earlier and only detailed M0-M10; this file covers every agent.
Update the **Status** column as work lands. Milestones M0-M11 are done; M12 onward are proposed and need approval (plan mode first for each).

## Rules from the strategy that apply to every agent
- **Spec before build.** No agent is built or enabled without a completed Appendix A spec (24 fields, in `docs/specs/Ax.md`, drafted for all 15 agents). Thresholds are
  fixed from baseline data *before* anyone reviews shadow results; they stay TBD until then.
- **Goes live only** with a shadow-mode report meeting its exit criteria and a named business owner. An agent that misses its window moves to the next wave.
- **One shared foundation** (data model, policy, decision records, replay, approvals); new agents add domain policies and adapters, not silos.
- Autonomy is granted per action type, L0-L4, promoted only on evidence (Section 6 and 11B).

## Agents

| # | Agent | Phase / wave | Milestone | Status | Needs (data / dependency) |
|---|---|---|---|---|---|
| A15-lite | Leakage diagnostic (land motion) | MVP, foundation | M5 | **Done** | 837/835/PM visits. Agent map now follows the strategy numbering. |
| A14 baseline | KPI and cash baseline | MVP, foundation | M4 | **Done** | claims, remits |
| A8 | Denial Resolution & Appeal | MVP, Wave 1 | M7 | **Done, shadow** | Spec redone on Appendix A. Outcome tracking and evidence gathering still missing. |
| A5 | Claim Prevention & Digital Twin | MVP, Wave 1 | M8 | **Done, shadow** | Five rules built; NCCI/MUE rows are synthetic stand-ins. Still needs CMS tables, payer-rule library v1, eligibility/auth data, and the calibrated denial model. |
| A7 | AR Next-Best-Action | MVP, Wave 1 | M9 | **Done, shadow** | Sweeper + agent + ranked inbox cards. Still needs real 276/277 status (with A6), pending-claim (records request) detection, routing to registration/authorization. |
| A6 | Claim Submission & Response | MVP, Wave 1 | M10 | **Done, shadow (response side)** | Rejection handling built. Still needs a release signal for the submission side, an X12 837 writer, the real partner adapter, 276/277 status, and signed-off technical rejection codes. |
| A14 | RCM Control Tower (expanded) | MVP, Wave 1 | M11 | **Done, shadow** | Cross-agent inbox, cash forecast + measured accuracy, backlog, 4 signals, daily escalation review built. Still needs a UI (FastAPI blocked), productivity / staffing / load balancing (need task logs and staff data), a fitted forecast model. |
| Synthea foundation | Synthea import, payer simulator, ground truth (`docs/synthea.md`) | Data, Wave 2 prerequisite | M12a | **Done (tested on a mini folder; real Synthea run pending Docker)** | Appointments, 271, notes, charges, authorizations still to add with A1, A3, A2. |
| A10 | Contract & Underpayment | MVP, Wave 2 | M12 | **Done, shadow** | Per-payment contract check, cause category, payer-wide patterns, dispute package draft. Needs real contracts, contract extraction (approved model), dispute submission, payer multi-procedure rules. |
| A3 | Documentation Completeness | MVP, Wave 2 | M13 | **Done, shadow** | Note and charge feeds (new tables), five gap types, sweeper, four task/review actions, charge-lag KPI. Needs a real EHR note-status and PM charge-log feed, provider-lead sign-off on elements and days, orders. |
| A1 | Pre-Visit Financial Clearance | MVP, Wave 2 | M14 | **Done, shadow** | Appointments + 271 parser, four gap types, 72 h / 24 h checkpoints, patient estimate. Needs the clearinghouse 270 adapter, real 271 variants, referral/auth data (A2), front-desk sign-off. |
| A9 | Denial Prevention Learning | MVP+, Wave 3 | M15 | **Done, shadow** | Clusters (payer + CPT + CARC, 120-day window), proposals, named approval, A5 `learned_pattern`, forward test, attribution. One rule family; thresholds are placeholders. |
| A2 | Authorization Intelligence | MVP+, Wave 3 | M16 | **Done, shadow** | Authorization feed + payer requirement table, five gap types, 7 d / 2 d checkpoints, request task and exception review. No portal, no clinical check, no approval-risk model. |
| A11 | Payment Posting & Reconciliation | MVP+, Wave 3 | M17 | **Done, shadow** | Bank deposit and posting feeds, six reconciliation gaps, days-to-deposit and days-to-post KPIs, unapplied cash and variance. No posting write-back (gated), no patient payments, bank file variants (BAI2, lockbox) not covered. |
| A4 | Coding & Charge Integrity Copilot | Phase 2 | M20 | **Done, shadow (suggestions only)** | E/M level-of-service audit on documented elements: over- and under-coding signals, audit variance by provider and code. Placeholder level table, no note text, no ICD-10 / modifier / procedure coding, no model. Liability boundary: a certified coder decides. |
| A12 | Patient Financial Engagement | Phase 2 | M19 | **Done, shadow (staff-facing worklist only)** | Patient payment and statement feeds, five item types, plain-language explanation for staff, aging stages. No outreach, no payment processing, no write-off; legal review of TCPA / Reg F / state law and a BAA vendor are prerequisites. Secondary balances not tracked (no COB owner). |
| A13 | Credentialing & Enrollment | Phase 2 | M18 | **Done, shadow** | Enrollment and screening feeds, six gap types, claim-risk dollars from the visit extract. Rendering provider not parsed from the 837 (follow-up); no portal, packet or live OIG lookup. |
| A15 full | Revenue Assurance Investigator | Phase 2 | M21 | **Done, shadow** | Realisation vs contract by payer and payer+CPT, recent vs baseline window; each flagged slice explained from A15-lite leaks and tagged with the upstream agents that flagged the claim before billing; sweeper, one review per slice, detected-vs-later-paid ledger. Placeholder thresholds; no volume / mix decomposition; attribution by key match, not causal proof. |

## Order of work
1. **M8a (done): specs.** `docs/specs/A1.md` ... `A15.md` drafted on the real Appendix A (24 fields each), thresholds TBD; `A8.md` redone on it. The A15-lite agent map now follows the strategy's numbering (authorization to A2, coding to A4, coverage to A1, claim defects to A5). Strategy document copied to `docs/strategy_v5.docx`.
2. **Wave 1 (M8-M11): done.** A5, A7, A6, A14, same pattern as A8: shadow mode, replay against synthetic ground truth.
3. **Platform work that Wave 1 and 2 need** (the strategy lists these in Days 0-60; not built yet): approvals HTTP endpoints and a simple UI
   (blocked: FastAPI cannot load on the dev PC, see below), identity resolution across systems, RBAC, a durable workflow engine decision (ADR-0003,
   Temporal is the named candidate), value ledger / outcome attribution with a holdout design, first real EHR/PM adapter, real clearinghouse adapter, payer-rule library v1.
4. **Wave 2 (M12-M14):** A10, A3, A1. A3 and A1 need new synthetic data first (notes/charges; appointments and eligibility).
5. **Wave 3 (M15-M17):** A9, A2, A11, after Waves 1-2 have produced outcome history.
6. **Phase 2 (M18-M21, done):** A4, A12, A13, full A15. All fifteen agents are built in shadow mode.

## Known blockers and open decisions (from the strategy's Appendix B and this build)
- **FastAPI cannot load** on the development PC (Windows Smart App Control blocks `pydantic-core`; no pure-Python build). The approval service functions exist and are tested; the HTTP layer waits on a different machine or a changed policy.
- Open in the strategy: first EHR/PM adapter, first clearinghouse, workflow engine, model hosting with BAA, write-back actions permitted in the pilot, autonomy thresholds. None can be decided by code; each needs a named owner.
- Data for A1, A2, A3, A11, A12, A13 does not exist in the repo yet; each of those milestones starts with a synthetic generator.
- **Secondary billing / COB** (stage 15 of the end-to-end RCM doc) has no owning agent in the strategy; needs an owner decision. See `docs/RCM_REVIEW.md`, which also maps all 17 stages of that doc to our agents and lists the A5/A7/A8/A10 refinements it implies.
- The Valley database run (matching, KPIs, A15, A8 on a larger data set) is still pending the AWS security-group change.

## Engine gaps against the strategy (Section 8 guardrails, 11B build rules, 11C priorities)
The M6 engine covers the decision record, policy table, idempotency, replay, approval queue and disabled/stub adapters. The strategy also asks for the
following, none of which is built yet. They belong in the platform work before any agent leaves shadow mode:
- **Kill switch** at tenant, workflow and agent level, and **blast-radius controls** (batch and rate limits, dry-run, canary cohorts, per-action dollar caps).
- **Maker-checker**: the approver of an L3 action must differ from the initiator, approvals time-bound and logged.
- **Versioned, effective-dated policy**: rules, prompts, models, thresholds and payer policies versioned and released by staged rollout with per-tenant feature flags.
- **Before/after values and source evidence** on every write-back (today the adapters are stubs, so nothing writes back).
- **Failure-injection tests** (duplicate events, retries, partial failures, outages, adversarial documents) before any action type reaches gate G3.
- **Identity resolution** across systems, **value ledger / outcome attribution**, PHI masking in lower environments, log retention policy.
- **Release-gate records** G0 to G5 with signed evidence packs (the strategy's gates are organisational, but the evidence packs come from the system).
