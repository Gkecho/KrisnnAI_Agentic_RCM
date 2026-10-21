# Plan: a live encounter stream through the whole ecosystem

Status: **S1, S2 and S2b built and verified** (2026-10-21); S3 onward not started. Decisions in section 4 are confirmed by Gk. Synthetic data only, local only, shadow mode.

## 1. Goal
Create dummy appointments and push them through the system one at a time, as if real visits were happening, with nobody typing data in:

appointment -> eligibility check (Gatekeeper, A1) -> visit with a transcript -> coder proposes codes (a person approves) -> OpenEMR makes the 837 -> mock clearinghouse -> mock payer decides on its own -> portal and remit show the result -> our agents work what they can see -> a queue item for a person.

The payer's real decisions are kept in a hidden log, so afterwards we can score what the agents found against what actually happened.

It proves the loop runs end to end on its own and that agents react only to what a payer would show them. It does not prove real payer accuracy, vendor-EMR integration or recovered money.

## 2. Spike result (2026-10-21, on the local OpenEMR 7.0.3)
| Question | Answer |
|---|---|
| Can OpenEMR produce the 837 itself, without its screens? | **Yes.** `X125010837P::genX12837P()` run from PHP inside the container produced a valid 005010X222A1 professional claim for a seeded encounter, no validation warnings. Sample: `out/openemr/spike_837.x12` (git-ignored). Script: `krisnai/integrations/openemr/spike/spike837.php` |
| Does our own parser read it? | **Yes.** `krisnai/ingest/p837.py` parsed claim id, charge, service date, CPT, diagnosis and payer name. Gaps: payer id and tax id came back empty or None (the payer id was missing until `encounter_claim` was set to false and the payer's `cms_id` filled in) |
| Can the REST API create what a claim needs? | Partly. REST can create insurance companies, patient insurance policies, encounters, SOAP notes and documents. There is **no REST endpoint for charges** (the billing table) |
| How did the charge get in? | OpenEMR's own `BillingUtilities::addBilling()` called from PHP. Setup that has no API (facility NPI and EIN, provider NPI, an X12 partner row, encounter facility and provider) was set with SQL inside our container, the same pattern as enabling the OAuth client |
| Does the mock clearinghouse accept it? | **Not yet tested, and the code says no.** `MockWorld.accept_claims` answers for claims in the synthetic book; a new claim needs a path of its own |
| Do agents read transcripts? | **No.** A4 compares the billed E/M level with the signed note's *named elements*; it states that no model reads notes. Turning a transcript into codes is a new component |
| Posting a remit back into OpenEMR | `ParseERA` and the payment screens exist; **not tried** |

Things the spike changed in the demo OpenEMR (synthetic, throwaway): facility 3 renamed and given an NPI and address; the `admin` user's name set to "Demo Provider" with an NPI; one X12 partner; one insurance company; patient 1's insurance, two billing rows and a claims row. `krisnai openemr down` removes all of it.

Quirks seen: the ISA date (ISA09/10) is a fixed value in OpenEMR's output, so nothing downstream may rely on it. CLM01 is `pid-encounter` (for example `1-2`).

## 3. Components
| Piece | Exists? | Work |
|---|---|---|
| Appointment creation in OpenEMR (REST) | yes (seed) | reuse; create one at a time |
| Eligibility bot + mock clearinghouse 270/271 | yes | answers must come from the payer simulator, not the book |
| Encounter + note in OpenEMR (REST) | yes (seed) | reuse |
| **Transcript generator** (50, deterministic, templated by visit type) | no | new |
| **Transcript coder**: extracts named note elements and suggests CPT/ICD, then waits for a person | no | new; rules first, no model in v1 |
| Charge entry + 837P in OpenEMR | spike only | productionize as `krisnai/integrations/openemr/billing.py` plus a small PHP helper |
| Mock clearinghouse 837 -> 999 + 277CA | yes, book-only | accept any well-formed claim; technical reject modes |
| **Payer simulator**: independent decisions (pay, underpay, deny with a CARC, pend, technical reject), seeded | no | new; writes `truth.csv` the agents never see |
| Mock payer portal showing live payer state | yes, static book | read the payer simulator's state |
| 835 / 277 back to our inbox | yes (X12 writers) | generate from payer decisions |
| Agents A1, A3-A8, A10, A11, A14 | yes (shadow) | run per simulated day; no change to rules |
| **Orchestrator + simulated clock** | no | new; `krisnai live run --encounters N --seed S` |
| **Scorecard**: agent findings vs `truth.csv` | partly (answer-key pattern exists) | extend |

**Independence is enforced, not promised:** the payer simulator lives in its own package; a test fails if any agent or bot imports it, and the agents get its output only as X12 files and portal pages.

**"Real time" means** a fast simulated clock. The engine runs in daily batches, so each tick is one or more simulated days, and the screen must say so.

## 3b. Payer Knowledge Book (planned module, not built)
One central place where agents look up insurance rules. It supplies rules; it does not decide a claim.

| Rule family | Question it answers for an agent |
|---|---|
| Coverage | Is this service covered under this plan? |
| Prior authorization requirements | Does this plan and service need approval first? |
| Medical necessity guidelines | What clinical evidence does approval need? |
| Billing and payment policy | How must the claim be billed? |
| Denial and appeal rules | After a denial, what is the next action and the deadline? |

**Each rule is a record, not an uploaded PDF:** payer, applicable plan and state, service or CPT, rule family, effective-from and effective-to, **the date the rule is judged on** (service date for coverage; denial-notification date for appeal deadlines), original source link or title, version, status (draft, reviewed, active), and unknown where a fact is missing. Old versions are kept. When a source changes: detect, keep both versions, extract candidate changes, a person reviews, activate by effective date, list affected cases.

**Rules for agents:** a December 2025 service is looked up under the coverage rule in force on that date; an appeal deadline uses the appeal rule and the denial-notification date. Missing or conflicting information raises an exception to a named owner; the agent never guesses. Public rulebooks alone cannot answer for one patient: the exact plan, eligibility and authorization status are also needed.

**Public sources:** the UHC, Aetna, Humana, Cigna and selected BCBS comparison report was prepared outside this repo and is not here; it is needed before the public-rule import (v2).

**How it meets the payer simulator (one decision for Gk):** the simulator reads the book to behave like a payer, and the agents read the same book. If both used the same rules and nothing else, the agents could never disagree with the payer and the scorecard would be circular. So the book holds what a payer *publishes*, and the simulator adds a hidden **deviation layer** (a configured share of decisions that misapply a rule, use a stale version, or follow an unpublished rule), recorded in `truth.csv`. Agents see only the published rules and the payer's answers, so the demo can show them catching real mismatches. Recommended: yes.

**v1 scope:** a small explicit demo ruleset for one fictional payer, labelled "client-confirmed demo ruleset" and never presented as official policy; the schema, versioning and effective-date lookup; the unknown/conflict exception. Public documents and the change-detection pipeline are v2.

## 4. Decisions
1. **837 source: OpenEMR's own generator.** Confirmed by Gk 2026-10-21. Our X12 builder stays as the fallback and for replacement claims.
2. **Transcripts to codes: rule-based extraction on templated transcripts first** (agreed); a language model only later, behind the engine's model abstraction. **Exception-only coding, confirmed by Gk 2026-10-21:** codes that pass every deterministic check are auto-accepted by policy; everything else goes to a coder; 10% of auto-accepts are sampled to a coder; config caps stand in for the unbuilt kill switch. About 20% of the 50 transcripts are deliberately problematic (missing elements, unsupported level, ambiguous visit) so the routing shows. Off by default; demo tenant only (ADR-0002).
3. **Payer behaviour: seeded random.** Confirmed by Gk 2026-10-21, so a run replays identically. Rates live in a config file and are recorded in `truth.csv`.
4. **Demo OpenEMR charge writes and policy-based coding: ADR-0002 accepted for the demo** (`docs/adr/0002-demo-openemr-charge-write.md`). It covers only the local demo instance; it is not a route to unattended automation on a client system.
5. **Payer Knowledge Book:** see section 3b.

## 5. Milestones (each ends in a gate; stop and report if a gate fails)
| # | Deliverable | Gate |
|---|---|---|
| S1 | **One encounter end to end, one payer, no randomness.** Appointment -> 270/271 -> note -> charge -> OpenEMR 837 -> mock clearinghouse 999/277CA -> payer decision -> 835 -> inbox -> daily run -> a queue item | The queue item traces back to the OpenEMR encounter by id; re-running creates nothing new |
| S2 | Transcript generator (50, about 20% problematic) and transcript coder with auto-accept policy, coder routing and 10% sampling | Suggested codes match the generator's expected codes on the clean ones; every problematic one is routed with its reason; nothing is charged without a policy or person approval record |
| S2b | Payer Knowledge Book v1: schema, versions, effective-date lookup, demo ruleset, unknown/conflict exception | A 2025 service picks the 2025 rule, never a 2026 one; an appeal deadline changes when the notification date changes; a missing rule raises an exception |
| S3 | Payer simulator with seeded decisions and `truth.csv`; reads the book plus the hidden deviation layer; mock portal reads its state | Same seed gives byte-identical truth; import-boundary test passes; rejection and denial stay distinct |
| S4 | Orchestrator and clock: push encounters one by one, run the daily agents per tick, resumable | 50 encounters run unattended; killing and restarting mid-run neither repeats nor loses an encounter |
| S5 | Scorecard against truth; remit posted back or reconciled; a live view in the preview (Tools in action) | Report lists what agents found, missed and flagged wrongly; a remit is never shown as cash collected |

No dates are committed. S1 is the first thing worth showing the boss.

## 5b. S1 result (2026-10-21)
`krisnai live s1` runs one encounter through the whole chain against the local OpenEMR (about 2 minutes). Verified twice (denied and paid):

| Step | Tool | What happened |
|---|---|---|
| 1 appointment | OpenEMR REST | dummy patient and appointment created, booked on the simulated day for three days later |
| 2 eligibility | Eligibility bot, mock clearinghouse, payer sim | 270 sent, 271 answered from the payer's enrolment list; saved as a file for the engine |
| 3 visit | OpenEMR REST | encounter and a signed note |
| 4 claim | OpenEMR billing (PHP, ADR-0002) | charge entered with an approval record; **OpenEMR wrote the 837P** |
| 5 clearinghouse | Mock clearinghouse (`LiveWorld`) | technical checks; 999 and 277CA. A technical problem is a rejection and never reaches the payer |
| 6 payer | Payer sim (`krisnai/live/payer.py`) | decides on its own; writes the 835; the decision goes to `truth.jsonl`, outside the inbox |
| 7 feeds | OpenEMR FHIR | appointment, visit, note read back for this patient |
| 8 agents | the engine's daily run | denied: A8 raised `a8_appeal_task` (claim 51-1635 = OpenEMR patient 51, encounter 1635). Paid: no card |

**Gate:** the card traces back to the OpenEMR encounter by id; re-running the same files loads nothing again (8 skipped, 6 decision records and 3 cards unchanged).

**Tests:** `tests/test_live_s1.py`, 10 fast tests (parser reads OpenEMR's 837; pay, deny and 835; clearinghouse rejection vs denial; eligibility; billing needs an approval and only targets our container; **no agent, engine or bot module imports `krisnai.live`**) and one slow end-to-end test that skips when OpenEMR is down.

**What S1 is not:** the payer denies one configured CPT (no randomness), the code is fixed at 99213 (no transcript coder yet), the portal does not read the payer's state yet, and the agents react through the engine's daily batch, not instantly.

**Left over for later milestones:** the payer id and tax id fields in our 837 parser come back empty or None for OpenEMR's claim (`REF*EIN` is not read); OpenEMR's ISA date is a fixed value; remit posting back into OpenEMR is untried.

## 5c. S2 result (2026-10-21)
`krisnai/live/transcripts.py` makes 50 synthetic visit transcripts for a seed (40 clean, 10 problematic: 3 missing plan, 2 two unrelated problems, 2 new-or-established never stated, 2 unsigned, 1 thin documentation for a chronic follow-up) with an answer key. `krisnai/live/coder.py` reads only the text and the signed flag, extracts the named note elements, suggests an E/M code (using A4's level table) and one diagnosis, runs seven checks, and applies the ADR-0002 policy. `krisnai live s2` scores it; `krisnai live s1 --visit N` runs transcript N through the whole chain.

| Result (seed 7, policy on) | Count |
|---|---|
| clean visits auto-accepted with the right code and diagnosis | 35 of 40 |
| clean visits sampled to a coder (10% quality check, deterministic) | 5 |
| problematic visits routed to a coder with the right reason | 10 of 10 |
| problematic visits auto-accepted | 0 |

Also verified: the same holds for seeds 11, 23 and 99; with the policy off every clean visit goes to a coder (`policy_off`); the daily cap stops auto-accepts and says why; three hand-written transcripts in wording the generator never used are read correctly; an unsigned note is never coded; the coder module never imports the answer key. Live through OpenEMR: transcript 1 was auto-accepted (99214, I10, "policy:demo-exception-only-v1"), billed by OpenEMR's 837P and paid; transcript 6 (unsigned) stopped at the coder with nothing billed. Tests: `tests/test_live_s2.py` (13 fast, 1 slow).

**Honest limits.** The transcripts and the reader were written by the same author, so the near-perfect score mostly shows the routing and policy logic works, not that rule-based coding can read real speech. Real transcripts would be longer, messier and need a language model or a certified coder's rules; the E/M level table is A4's placeholder, not the AMA or CMS guidelines. A routed visit stays pending: nothing resolves it yet (the person's decision and resume are S4/S5 work). The 5 "clean held back" in some runs are the 10% sample, by design.

## 5d. S2b result (2026-10-21): Payer Knowledge Book v1
`krisnai/knowledge/` (agents may import it, unlike the payer simulator): `book.py` (rule records, versions, point-in-time lookup, JSON save and load), `deadlines.py` (appeal and corrected-claim routes), `demo.py` (the demo ruleset for fictional payer SYNAETNA, every rule labelled "client-confirmed demo ruleset, not official payer policy"). `krisnai knowledge lookup|deadline --as-of <date>` queries it.

- **Date handling:** each rule names the date it is judged on. Coverage and prior authorization use the service date; the appeal window uses the denial-notification date; corrected claims run from the service date on their own clock. The evaluation date is always passed in; a test fails if the module reads the computer's clock.
- **Gate checks, all passing:** a December 2025 service gets the 2025 coverage rule (20 visits) and a January 2026 service the 2026 rule (12), including when evaluated in October 2026 and on the 31 December / 1 January boundary; the appeal deadline moves from 180 to 120 days when the notification date crosses into 2026 (2026-01-02 gives 2026-05-02); an old service with a recent denial is judged on the denial date, not rejected for age; an old denial comes back as expired, not as an appeal to file; a missing rule, a missing event date, a fact marked unknown, two rules that overlap with equal scope, and a plan-specific rule when the plan is unknown each return a problem that names an owner and what to ask, never a guess.
- **Point in time:** a rule the book learned on 2026-03-01 is invisible to an evaluation on 2026-02-01; retiring a version affects only later evaluations; old versions are kept.
- **Tests:** `tests/test_knowledge.py`, 20 tests.

**Not done in v1:** the rules live in a JSON file, not a database table; no change-detection pipeline; no public payer documents (the UHC, Aetna, Humana, Cigna and BCBS comparison report is not in this repo); **agents do not read the book yet** (A5 and A8 still use their own filing-window table and the engine's 365-day default). Wiring the payer simulator to the book is S3; moving A5, A7 and A8 onto it is a separate, later change.

## 6. Risks and limits
- OpenEMR's billing needs SQL setup and a PHP helper; this is fragile across OpenEMR versions, so pin 7.0.3.
- Payer behaviour is our own invention. Denial rates are not real payer statistics, and the screen must say so.
- Agents are shadow and read-only: they raise tasks, they do not fix claims. "Agents working the denial" means proposals and queue items.
- Memory: OpenEMR, the Microsoft FHIR server, Supabase and Postgres together ran this PC out of memory. Run this with Supabase and Postgres stopped.
- Not covered: eligibility from a real payer (Stedi stays optional), real portals, real MFA, vendor EMRs, write-back to any client system.
