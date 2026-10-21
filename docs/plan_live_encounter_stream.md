# Plan: a live encounter stream through the whole ecosystem

Status: **S1 to S5 built and verified** (2026-10-21). Remaining work is in the follow-ups at the end of section 5g. Decisions in section 4 are confirmed by Gk. Synthetic data only, local only, shadow mode.

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

## 5e. S3 result (2026-10-21): the independent payer
`krisnai/live/payer.py` is now a seeded payer. For each claim it draws from a random stream seeded by (seed, claim id), so the same seed, config and claims give a **byte-identical truth log regardless of arrival order** (tested, including a reversed order).

- **It follows what it published.** It reads the Knowledge Book: a service the book says is not covered, or that needs a prior authorization the claim lacks, is denied (CARC 96 or 197). Demo book: a 2026 therapy visit without an authorization is denied; the same visit with a 2025 service date is paid; granting an authorization changes the answer.
- **It behaves like a payer.** At configured rates a claim pends for records (remit 35 days out instead of 14) or is denied for an ordinary reason (CARC 50, 16, 18, 97, 4).
- **It deviates from what it published, on purpose.** At a configured rate it makes one of four mistakes: `wrong_denial` (CARC 31 although coverage was confirmed), `stale_version` (a prior-authorization rule that was not in force on the service date, only for a service whose rule actually changed between years), `unpublished_rule` (an edit that is not in the book) or `underpay_off_schedule` (10 to 25% under the fee schedule). Each shows in the truth log with what the book said it should have been; with the rate at zero there are no deviations.
- **Truth log:** `PayerSim.truth_csv()` (one row per decision: outcome, CARC, published outcome and reason, deviation kind, pended, billed, allowed, paid). `krisnai live s1` now writes `truth.csv` next to `truth.jsonl`, outside the engine's inbox.
- **The outside world sees the payer's state over time.** `LiveWorld` answers claim-status requests and the mock portal from the payer's own state on the simulation clock: a pended claim shows "Pending: in review" with a records request until its remit date, then "Finalized: paid or denied". The portal bot read exactly this in a test. `remits_due(day)` hands out each 835 once, in claim order, when its date comes.
- **Rejection and denial stay distinct:** a clearinghouse technical rejection is held in the world, never reaches the payer, and never appears in the truth log.
- **Tests:** `tests/test_live_s3.py` (11); the earlier live and portal tests still pass, and both slow end-to-end tests pass against OpenEMR. One additive change to the mock portal: a world may supply its own reason line and records-request flag; the old behaviour is unchanged for worlds that do not.

**Not done:** the rates and the deviation mix are demo settings, not payer statistics; an ordinary denial is random, so the book cannot predict it (it is not counted as a deviation). Nothing scores the agents against the truth log yet (S5), and the single-encounter runner still uses a scripted denial; the S4 orchestrator will use the rates.

## 5f. S4 result (2026-10-21): the orchestrator and clock
`krisnai live run --count 50` (`krisnai/live/stream.py`, `emr.py`) pushes synthetic encounters through the whole chain on a simulated clock, with nobody typing anything in. Each simulated day it: books patients and appointments in the EMR and checks eligibility (booking day); creates the encounter, signed note and transcript and runs the transcript coder (visit day, three days later); has the EMR charge and write the 837P, sends it to the clearinghouse and lets the payer decide (billing); issues each 835 on its remit date; runs the status bot and, weekly, the portal bot against the payer's live state; and runs the engine's daily run (all agents, shadow mode) over whatever files arrived. The EMR sits behind a small interface (`OpenEmrPort`, and an in-memory `FakeEmr` for tests), so the orchestrator is tested without Docker.

**Crash safety (the gate).** State is saved after every step (retrying through Windows file locks, which OneDrive caused for real during this build); every EMR write looks for the record first; every payer decision comes from a (seed, claim id) stream. Verified two ways: with the in-memory EMR, killing the run at five different points (including after a side effect and before the save) and resuming gave the same truth log byte for byte, the same stages and files, and no repeated event; and against the **real OpenEMR**, a 50-encounter run killed at step 150 and resumed ended with exactly 50 patients, 50 appointments, 50 encounters and 100 documents, none duplicated.

**The 50-encounter run against OpenEMR** (seed 7, policy on): 38 visits auto-accepted by policy, 2 sampled for a coder's quality check and confirmed by a **simulated** coder (labelled as simulated everywhere), 10 problematic visits left in the coder queue with their reasons (3 missing plan, 2 two problems, 2 unclear status, 2 unsigned, 1 thin chronic). 40 claims billed, 40 remits issued; the payer paid 31, denied 8 (3 for lapsed coverage that Gatekeeper's eligibility check had flagged before the visit, 4 ordinary or deviation denials, 1 wrong denial), underpaid 1, pended 4. The engine's agents raised: 8 denial tasks (A8: 2 appeals, 5 fixes, 1 write-off review, one for each denial) and 32 patient statements (A12).

**What the first run exposed, and the fix:** the one underpayment (claim 97-1768, paid 75.00 against a schedule that would have paid 100.00) produced **no A10 card**, although A10 ran 32 decisions: the stream had not loaded the practice's contract fee schedule, which A10 compares payments to. That was a gap in the stream, not in the agent; the stream now loads the practice's fee schedule on day one (`fee_schedule.csv`), and the rerun in section 5g shows A10 catching the underpayment. The first run is kept at `out/live_run50_nofee` for comparison.

**Limits:** 'real time' is the simulated clock, run day by day; the simulated coder is a stand-in for a person; no clearinghouse rejections or corrected claims are injected yet (so A6 and the resubmission bot are not exercised); the payer's rates are demo settings. Streamed patients use fixed member ids, so running the stream again on the same OpenEMR reuses them instead of creating new ones. Tests: `tests/test_live_s4.py` (12 fast, 2 slow).

## 5g. S5 result (2026-10-21): the scorecard, the reconciliation and the live view
`krisnai live score --run <folder>` (`krisnai/live/score.py`) lays the agents' work beside the payer's hidden truth log and reads every 835 file back to reconcile it; `krisnai live export` turns a run into the data the preview shows (`tools_stream.js`). Reports: `scorecard.html`, `scorecard.json`, `ledger.csv`.

**The 50-encounter run against OpenEMR (with the fee schedule loaded):**

| What the payer did | Claims | Agent raised work | Missed |
|---|---|---|---|
| ordinary denial | 2 | 2 | 0 |
| denial the book predicts (coverage lapsed) | 3 | 3 | 0 |
| denial that contradicts the published rules (deviation) | 3 | 3 | 0 |
| underpayment below the fee schedule (deviation) | 1 | 1 (A10 dispute review) | 0 |
| paid correctly | 31 | none expected | 0 false alarms |

**9 of 9 payer problems found, 0 false alarms.** The first run, without the fee schedule, found 8 of 9: it missed the underpayment. Eligibility: 3 patients had lapsed coverage and Gatekeeper raised a coverage exception for all 3, before the visit, with no false alarms on the 47 active patients. Coding against the answer key: 38 auto-accepted visits all had the right code and diagnosis; all 10 problem visits were routed with the right reason; A4 raised no findings.

**The finding that matters most: 0 of the 3 payer deviations were recognized as contradicting the published rules.** The agents treated a wrong denial, an unpublished edit and a stale rule like any other denial and raised the normal denial work. No agent reads the Knowledge Book, so none could notice that the payer broke its own rules. This is the gap the deviation layer was built to expose; closing it means moving A8 (and A5, A7) onto the book, a separate change.

**Reconciliation.** 40 remits read from the 835 files: billed 5,430.00; the payer says it paid 2,843.00; patient responsibility 710.75; contractual write-down 806.25; denied (billed) 1,070.00. The remits tie out to the payer's truth log with 0 mismatches; a remit in two files counts once; a claim with no remit is listed as awaiting. **Cash collected is always 0.00**: a remit is what the payer says it paid, and no bank deposits exist in this simulation, so none is shown as collected. Posting remits back into OpenEMR (its ERA importer) was not tried.

**Live view.** The preview's "Tools in action" screen now has a section for the recorded run: the funnel from booking to payment, this scorecard, the money box with the cash line, and a day-by-day replay that lights up the tools in the diagram (28 simulated days with activity, 394 steps). It is labelled a recorded synthetic run. The rendering was checked with the real data in a script; it has not been looked at in a browser yet, and it is not deployed.

**The policy and the claim trace in the preview (added after S5).** The preview now has a "Payer rules" screen: the Knowledge Book's ten rule versions (what each says, when each applies, what date it is judged on, its source), and a "try it" that runs the lookup and deadline logic in the browser so a viewer can change a service date, denial date or evaluation date and watch the rule version and the deadline change (a December 2025 service picks the 2025 rules; a denial notified on 2 January 2026 gets the 120-day window and shows as expired; a missing date or an unconfirmed window is a request to a named owner, never an answer). The browser logic was checked against the Python Knowledge Book on 6,300 comparisons with 0 mismatches. The "Tools in action" screen also has "Follow one claim": for each of the 50 encounters, the coder's checks, what the payer actually did against what the policy says (the hidden log, labelled as such), the work the agents raised, and the timeline. Looked at in a browser on localhost; not deployed. **Honest note shown on the screen:** the demo ruleset holds no rule that bites on ordinary office visits (only a coverage rule for CPT 99213), so in the recorded run the book forced no denial and no agent reads it; making the policy bite in the stream (for example an authorization rule for new complex visits) and moving the agents onto it are the follow-ups.

**Tests:** `tests/test_live_s5.py` (6 fast, 1 slow): the tie-out, a tampered remit flagged, a double file counted once, a missing remit listed, every payer behaviour classified, found, missed, false alarm and recognized counted against a hand-made truth, and a real streamed run scored end to end.

**Honest limits.** The score measures the loop against our own payer simulator on synthetic data, not accuracy against real payers; the deviation rate, the rates of denial and pend, and the mix of mistakes are demo settings; nine problems is a small sample; the same seed on the same OpenEMR reuses the same patients and claim ids, so a rerun repeats the same decisions.

**Follow-ups, in the order I would take them:** (1) move A8, A5 and A7 onto the Knowledge Book so deviations are recognized; (2) inject clearinghouse rejections so A6 and the resubmission bot are exercised; (3) simulate bank deposits so A11's reconciliation and a real cash line exist; (4) post remits into OpenEMR through its ERA importer; (5) replace the simulated coder with a queue a person can work in the preview.

## 5h. "Give it a transcript and it runs the whole workflow" (added after S5)
`krisnai live serve` starts a small local service (`krisnai/live/service.py`, port 8780) and the preview's **Run a visit** screen talks to it: paste or pick a visit transcript, choose whether the note is signed, whether coverage has lapsed and how the payer behaves (pays, denies, breaks its own rules, asks for records first), and press Run. The same chain as the 50-encounter stream runs for that one visit on a simulated clock (about 7 seconds of real time with the real engine): the visit is recorded, the transcript coder decides, the EMR writes the claim, the clearinghouse and the payer respond, the engine's agents react, and the screen shows each step as it happens and then the whole trace (the coder's checks, what the payer did against the policy, the agents' work, the money with cash collected at 0.00).

- **Safety:** it answers only on the machine it runs on (other callers get 403) and only to the preview's origin; one visit at a time (a second gets 409); a transcript is capped at 20,000 characters; it uses an in-memory EMR unless started with `--emr openemr`; synthetic data only (ADR-0002).
- **What the first run showed:** a complete signed visit is auto-accepted, billed and paid; an unsigned or incomplete one stops at the coder with nothing billed; a denied visit gets an A8 task; a paid visit raises no agent work within eight simulated days of the remit (the 50-encounter run's patient statements came later).
- **Limits:** it works only when the service runs on the same computer as the browser, so the deployed site cannot run it (it needs the local engine); the payer is our simulator; the transcript coder reads the wording of the generated transcripts well and has not been tried on real speech.
- **Tests:** `tests/test_live_service.py` (10 fast, 1 slow with the real engine): a complete visit reaches a remit; the chosen payer behaviour changes the outcome; lapsed coverage is flagged and denied; a failed check stops at the coder; bad input is refused; one run at a time; failures are reported; non-local callers and other origins are refused.

## 5i. Many visits together, and the route of every step (added after 5h)
The **Run a visit** screen now has a "Many visits together" tab: paste several transcripts separated by a line of `=====` (optional first lines `# A title`, `# unsigned`, `# lapsed`), or load text files, or load the nine built-in sample scripts, pick how the payer behaves, and press **Run all together** (up to 25 visits). `POST /api/batch` runs them as one stream (one engine, bookings five a day) and the screen shows the progress, then **results by claim number** (a table: visit, claim number, what the coder decided, what the payer did, what the agents raised), then **each visit in full** stacked under its own claim number with expand-all and collapse-all. A visit the coder stops has no claim number and is shown as "no claim (stopped at the coder)", because nothing was billed.

Every step in the progress area now also shows its **route**, not just a tick: for example "Eligibility checked: Eligibility bot → clearinghouse (270 request) → payer (271 reply)", with what actually happened on it in this run ("8 active, 1 inactive"); likewise for the booking, the visit, the coder, the claim, the clearinghouse, the payer, the remit and the agents' work.

Bugs the batch tests caught and fixed: the payer mode "Pays normally" was falling back to the stream's random default rates and could deny a claim, so every payer mode now sets all three rates; a visit stopped at the coder was shown with a claim number it never used; and a saved run's settings compared an empty tuple with an empty list, which would have stopped a killed run from resuming (caught by re-running the resume tests). First batch of nine: 4 became claims (3 paid; 1 denied for lapsed coverage, with Gatekeeper's coverage exception and an A8 task), 5 stopped at the coder with their reasons. Tests: `tests/test_live_service.py` now has 14 fast and 1 slow.

## 5j. What each agent did on a visit, and how (added after 5i)
Every visit's trace now has a section **"What the agents did, and how"** (in "Run a visit", in the many-visits results and in "Follow one claim"). It lists every agent that looked at the visit, in order, including the ones that looked and found nothing to raise. For each one it shows, from the engine's own decision record: what it did in plain words; the checks it ran, each with a yes or no and the reason (for example Gatekeeper: "coverage active: no, coverage is active on the visit date"; Advocate: "routing found: yes, CARC 27 has a row in the denial route table"); the facts it looked at; the work item it raised with owner, due date and expected dollars; its confidence; and that it ran at level L0 in shadow mode. The same finding seen on several days is shown once with its date range.

What the first batch showed: for a paid visit the Gatekeeper, Code Whisperer, Mirror and Auditor each ran their checks and raised nothing; for the lapsed-coverage visit the Gatekeeper flagged the coverage three days before the visit and the Advocate raised a fix task after the denial. It also exposes a fact worth knowing: the Advocate's check "appeal window from table" answers no, because the denial tables have no filing-window row and it falls back to a 180-day default, which is the engine's own table and not the Knowledge Book.

**Two fixes after 5j (found because the service tests passed only some of the time):** the status call could read a run's state file at the instant the run replaced it, which Windows refuses (it now retries, and reads the run's status before its trace so a trace is never half-finished and marked done); and the 10% quality-check sample depended on a run-specific id, so the same transcript could go to a coder on one run and not the next (the quality sample is now off for typed-in visits so the same transcript always gets the same answer; it stays on at 10% in the 50-encounter stream). I committed 5j before seeing these two failures, which I should not have done; this commit fixes them and the full live suite (92 tests) passes, with the service tests run five times in a row.

## 5k. The journey from a transcript to a settled claim: three parts built in parallel, then combined (added after 5j)
Three pieces were built at the same time by three agents, each in its own copy of the repository with its own files, against a shared catalog and a per-visit payer hook, then merged and combined.

- **S6, the realistic world.** A catalog of 67 conditions and 53 services across nine specialties; **six invented payers** (SYNAETNA, SYNCIGNA, SYNUNITED, SYNBLUE, SYNMCARE, SYNMCAID) with their own market share, rates, pay speed, authorization lists, coverage, bundling and medical-necessity edits and filing limits, published in the Knowledge Book; a payer picked at random for each visit (the same seed gives the same pick) and an outcome decided from what the claim contains (coverage lapsed, other insurance first, duplicate, timely filing, not covered, bundled, no authorization, medical necessity, plus seeded pends, ordinary denials, underpayments and deviations from the payer's own rules); and `generate_wide`, a transcript generator across the whole catalog whose share of problems varies with the seed.
- **S7, reading any transcript.** A reader that copes with dialogue, SOAP notes, narrative, dictation and bullets, with synonyms and abbreviations, negation, "rule out", laterality, minutes converted to units, and a list of everything it could not interpret (it never guesses). The coder is built on it. An optional AI layer exists but is off: it makes no network call, and anything it proposes is rejected unless the code is in the catalog and its quoted evidence appears word for word in the transcript; a disagreement with the rules goes to a coder. On 59 hand-written client-style transcripts the reader's results were: held-out set (written before the reader and then tuned against) 39 of 39; blind set (first run before tuning) diagnosis 17 of 20, services 19 of 20, route 17 of 20, and after fixing those failures 19, 20 and 20 of 20, which is optimistic because the fixes were prompted by seeing those cases.
- **S8, the bots reply to the payer.** ADR-0003 (demo only, mock payer only, every action approved by a labelled simulated person or a capped policy, no change to a code or write-off without a named approval). A responder sends corrected claims, appeals, disputes and records and checks each denial against the payer's own published rules (a payer that contradicts its own rule is appealed on that ground); the payer answers again (seeded; a correctly cited deviation is overturned about 90% of the time, an ordinary appeal about 25 to 35%); clearinghouse rejections can be injected and are fixed and resent; the run continues until each claim is paid, settled as a patient balance, or in review, crash-safe like the rest; second remits reconcile without double counting; the scorecard counts replies.

**Combining them found problems none of the three tests could.** The first combined run of 60 wide visits (six payers, replies on, the real engine) scored 12 of 12 payer problems found and 0 false alarms, but the coding check against the answer key showed 6 visits auto-accepted with a code that disagreed with the key and 6 problem visits not routed for the expected reason. The causes were real: a preventive visit was auto-accepted as an office visit; an MRI ordered with no stated reason was auto-accepted; a visit plus therapy was billed as therapy alone; the visit-level ladder had no "straightforward" or "high" level; and "back skin" was counted as two body systems. The coder now sends preventive and emergency visits (coded from age band or emergency level) and visits with therapy to a person, requires a stated reason for orders that need one, picks the visit code from how deep the documentation is, and the reader treats "back skin" as one finding. After the fixes the same run auto-accepted 38 visits with **0 disagreeing with the key** and 0 problem visits missed (11 clean visits went to a coder instead: the safe side). Tests that hold the three together: `tests/test_live_integration.py`.

**What a run looks like now** (25 varied visits, "Random" payer, in the preview's Run a visit screen, 29 seconds of real time): 18 became claims and 7 stopped at the coder; the insurers were mixed; the payer paid 15, denied 2 and underpaid 1; the bots sent corrected claims, records, appeals and a dispute, 16 claims ended as patient balances and some were left for a person; the agents raised 87 work items. The "Generate 25 varied visits" button builds such a batch from the wide generator and labels each visit with what it tests.

**Honest limits.** The payers, their rates and their rules are invented; nothing is real payer behavior. The reader has been measured on a small number of hand-written transcripts and on generated ones; real speech will be harder, and the AI layer is off until a model is chosen. The coder is deliberately cautious (preventive, emergency, therapy with a visit and any procedure with a visit go to a person), so fewer visits are auto-accepted. A records reply only acknowledges (it does not move the payment date), and only prior-authorization and active-coverage contradictions are recognized as the payer breaking its own rules (not bundling). Decision records for replies are written to a file, not the engine's table. One slow test failed once under full-suite load and passed on both reruns.

## 5l. The claim as a CMS-1500 form next to its EDI (added after 5k)
Each visit that becomes a claim now shows **"The claim: the CMS-1500 form, and the EDI it becomes"** in its trace (Run a visit, the many-visits results and Follow one claim). The form (insurer, patient, diagnoses A to L, prior authorization, one row per service with date, place, code, modifier, diagnosis pointer, charge, units and rendering NPI, tax ID, total, facility, billing provider) is **read back from the 837P claim file itself** by `krisnai/live/claim_form.py`, so it shows exactly what the file says and cannot drift from it; touching a box highlights the EDI line it came from, and each EDI line has a plain-words note. Works on both the in-memory EMR's claim and OpenEMR's own claim (tested on both). Tests: `tests/test_claim_form.py`.

Found while checking that results follow the typed text: the claim used to carry only the visit line and the first diagnosis; it now carries every service and every diagnosis the coder found, with sides as modifiers and units from minutes, and each claim line is tested against the payer's published rules. A side named elsewhere in a note now counts when it is the only side named (two sides, or hand dominance, never count). A note that fails as unsigned now says which of three causes made it so.

## 6. Risks and limits
- OpenEMR's billing needs SQL setup and a PHP helper; this is fragile across OpenEMR versions, so pin 7.0.3.
- Payer behaviour is our own invention. Denial rates are not real payer statistics, and the screen must say so.
- Agents are shadow and read-only: they raise tasks, they do not fix claims. "Agents working the denial" means proposals and queue items.
- Memory: OpenEMR, the Microsoft FHIR server, Supabase and Postgres together ran this PC out of memory. Run this with Supabase and Postgres stopped.
- Not covered: eligibility from a real payer (Stedi stays optional), real portals, real MFA, vendor EMRs, write-back to any client system.
