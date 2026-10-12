# Review of "End-to-End Healthcare Revenue & Claims Intelligence" against the build

Source: a workshop website (provider side: 14 modules; payer side: 12 modules) supplied as a zip on 2026-10-12. It is a process
and opportunity map, not a specification. Its figures (for example ">90% first-pass acceptance", "2-5% added recovery from
underpayments", "30-50% fewer days in patient A/R") are the source's own claims and are **targets to measure against, not
results we have shown**. The payer-side modules describe how insurers adjudicate; they are context for the payer-rule library
and for understanding denial causes, not agent scope (we sit on the provider side).

## 1. The doc's 17 stages mapped to our agents

| # | Doc stage | Agent | Notes |
|---|---|---|---|
| 1 | Patient registration and appointment | A1 | Scheduling, intake and reminders are front-office tools; we consume the outcome (eligibility, estimate), we do not replace them |
| 2 | Eligibility, benefits, coverage discovery (COB) | A1 | 270/271 parser and synthetic data still missing |
| 3 | Referral and prior authorization | A2 | |
| 4 | Clinical documentation and transcription | A3 | Ambient capture and transcription are a different product; we use the signed note and a readiness score |
| 5 | Coding | A4 | The doc names an external coding engine ("InstaCode") as the coding hand-off. We sit above it. Open decision: which coding engine, if any |
| 6 | Charge entry and charge integrity | A4 | Strategy name is "Coding & Charge Integrity Copilot" |
| 7 | Claim scrubbing | A5 | Doc lists five check families; A5 implements part of them (section 3) |
| 8 | Billing and claim generation | A6 | |
| 9 | Submission / clearinghouse | A6 | |
| 10 | 999 / 277CA acceptance | A6 | Parsers built (M2); rejection routing is A6 work |
| 11 | Adjudication and status monitoring | A7 (with A6) | 276/277 status inquiry has no parser or data yet |
| 12 | Payment posting and reconciliation | A11 (A10 for variances) | |
| 13 | A/R management | A7 | |
| 14 | Denial and appeals management | A8, then A9 for prevention | |
| 15 | **Secondary billing / COB** | **none** | **Gap.** No agent in the strategy owns secondary claims. Needs an owner decision (proposal: COB discovery in A1, secondary claim creation in A6, secondary balance detection in A7) |
| 16 | Patient A/R and collections | A12 | Compliance review (FDCPA, TCPA, Reg F) applies |
| 17 | Account closure and reporting | A14 (A15 for insights) | |

Enrollment/credentialing (A13) appears in the doc only as a scrubbing check ("provider enrolled with payer").

## 2. The doc's operating model against our harness

The doc's target model has **four layers** (AI/predictive, rules and policy engines, workflow automation/APIs, human teams), a
data-integration layer, an audit trail, governance/exception management and **three feedback loops**. Ours matches:

| Doc | Build |
|---|---|
| Rules and policy engines | Deterministic checks first (rule 6); policy table per action type |
| AI / predictive | Model abstraction behind `engine/models.py`, stub by default, BAA gate |
| Workflow automation / APIs | Adapters (task/note, clearinghouse), disabled by default |
| Human teams, exception management | Approval queue, autonomy levels L0-L4, work routed to named owners |
| Audit trail | Decision record on every run, replay with fingerprints |
| Data integration layer | Event-sourced model; any source (files, database, clearinghouse) feeds the same events |
| Loop 1: denials/rejections -> upstream fix | A8 (built), A9 (planned) |
| Loop 2: underpayments -> recovery | A15-lite (built), A10 (planned) |
| Loop 3: insights -> upstream process | A14, A15 full (planned) |

What the doc asks for that the engine lacks is already on the roadmap's engine-gaps list (dashboards/KPI monitoring in the UI,
governance). Nothing in the doc contradicts the strategy.

## 3. What this changes in the work

**A5 claim prevention (built).** The doc's scrubbing module lists five families of checks. Built: required fields, duplicate
claim, timely filing, NCCI pair without modifier, MUE units. Candidate additions that need only data we already store
(deterministic, cheap): NPI check digit; diagnosis pointer must refer to a diagnosis that exists; replacement/void claims
(frequency 7/8) must carry the payer claim number; claim total equals the sum of line charges; valid place-of-service code;
units greater than zero. Need data we do not have: age/gender edits (no date of birth stored), code validity and effective dates
(needs code tables), provider enrollment with payer (A13 data), diagnosis supports procedure and NCD/LCD (needs policy library),
attachments. The doc also asks that failed edits be **routed by category** (registration, authorization, coding, billing) and
**prioritized by revenue impact**. A5 currently routes to billing or coding only; add registration/authorization owners when the
rules that need them exist.

**A7 AR next-best-action (in progress, plan adjusted).**
- Priority should rank by "dollars, age, **filing risk**, payer behavior" (doc, A/R improvement B). The approved plan had dollars,
  chance of paying, age. Add filing risk (days left before the payer's filing limit) to urgency.
- Work should be **routed to the right team** (coding, billing, registration, authorization, denial team), not always billing.
  v1 classifies what it can see: no response (billing status check), returned by the 277CA (billing/coding fix and resubmit),
  and hands denials to A8, underpayments to A10, patient balances to A12 rather than duplicating them.
- Cards show the **aging bucket** (0-30, 31-60, 61-90, 90+) beside the priority, because staff think in buckets even when
  priority differs.
- "Pending-claim management" (a payer asks for records) needs 277 status codes we do not parse yet: recorded as a gap.

**A8 denial and appeals (built).** The doc's list matches what A8 does (capture, classify, root cause, route, deadline
tracking, appeal drafting). Not yet built: **document retrieval and evidence assembly**, **root cause linked to the upstream
process**, **second-level escalation** when the first appeal fails (doc flow), and one **shared denial taxonomy** (our
`carc_route` table is the start of it).

**A10 / A15 underpayments.** The doc gives nine root-cause categories for underpayment: contract/pricing, modifiers,
bundling/NCCI, units/charges, medical necessity, authorization, timely filing, payer policy, data/coding. Use these as the
classification when A10 is built; today A15-lite reports the dollars but not the reason.

**New open decision.** Who owns secondary billing / COB (stage 15)? Add to the strategy's Appendix B list.

**Not our scope.** Ambient AI documentation, transcription, patient scheduling and the omni-channel front door, and the coding
engine itself. We take their output as input and measure the effect on claims.
