# KrisnnAI RCM: data contract and KPI map (for review)

Status: draft for review, 2026-10-15. Decisions recorded 2026-10-15: the client database keeps audit / history (Q1 yes) and has a master patient id (Q2 yes). Built from the code as of M15 (A1, A3, A5, A6, A7, A8, A9, A10, A14 built in shadow; A2, A4, A11, A12, A13 not built).
Two jobs: (1) say exactly what the agents read, so the full-database model can be designed to provide it; (2) show, agent by agent, which metric ranks or
triggers its actions and which thresholds are still placeholders that the three-year baseline must set. Mark it up; every "OPEN" is a decision for you.

## 1. How the pieces connect

```
source (EDI files, CSV extracts, later a client database)
   -> adapter (parse / map, hash the patient, stamp known_at)
   -> canonical model (tenant tables + append-only events)       <- this document is the contract for this layer
   -> agents (read only; one decision record per run)
```

- Agents never read a source system. They read the canonical tables through a tenant-filtered session, so a new source (the full database) needs an
  adapter, not agent changes, as long as the canonical fields below are filled.
- Every row carries `tenant_id`, `source_file_id` (lineage) and `loaded_at`. Events carry `known_at`: the moment the data became known, which is the
  key for point-in-time replay (rule 9). Patients exist only as a salted hash (`patient_ref.ref_hash`); no names, birth dates or member ids are stored.
- Idempotency: the same file (SHA-256) or the same transaction (ISA13 / GS06 / ST02 plus content) loads once.

## 2. Canonical entities: what the agents read

"Today" is where the data comes from now. "Full database must provide" is the contract for the new adapter.

### 2.1 Claims

| Entity | Grain and key | Fields agents use | Today | Full database must provide | Read by |
|---|---|---|---|---|---|
| `claim` | one claim version; `claim_submitter_id` (CLM01), `event_id` | payer, provider, patient hash, total charge, frequency code (1/7/8), place of service, service date, submitted date, payer claim number | 837P | the same, plus **the date the claim actually left the practice** (not only the creation date) and replacement / void links | A5 A6 A7 A8 A9 A10 A14 A15 |
| `claim_line` | one service line, (claim, line number) | CPT, modifiers 1-4, units, charge, diagnosis pointer, line service date | 837P | the same | A5 A8 A9 A10 A15 |
| `claim_dx` | (claim, seq) | ICD-10 code, qualifier | 837P | the same | A5 |
| `ack_999` | one acknowledged transaction set | status (A/E/R), error codes, acked GS06/ST02 | 999 | clearinghouse acknowledgement status per submission | A6 A5 A14 |
| `ack_277ca` | one claim status line | category (A1-A4), status code, entity, status date, payer claim number | 277CA | the same, plus any 276/277 status poll results | A6 A7 A5 A14 |

### 2.2 Payments and adjustments

| Entity | Grain and key | Fields agents use | Today | Full database must provide | Read by |
|---|---|---|---|---|---|
| `payment` | one BPR/TRN (check or EFT) | payer, trace, amount, method, payment date, PLB adjustments | 835 | the same, **plus the bank deposit date and amount** (reconciliation, A11) | A8 A11 A14 |
| `remit` | one CLP (claim payment) | claim status (1/2/3/4/22), charge, paid, patient responsibility, payer claim number, statement date | 835 | the same; **posting date and who posted** | A5 A7 A8 A9 A10 A14 A15 |
| `remit_line` | one SVC | CPT, modifiers, charge, paid, units, allowed amount, line date | 835 | the same | A8 A9 A10 A15 |
| `adjustment` | one CAS reason/amount pair, claim or line level | group (CO/PR/OA/PI/CR), CARC, amount, quantity | 835 | the same | A8 A9 A10 A15 |
| `remit_remark` | RARC per remit or line | remark code | 835 | the same | A8 |
| `plb_adjustment` | provider-level adjustment on a payment | reason (WO, 72, ...), amount | 835 | the same | A8 |
| `ar_snapshot` | claim balance on a date | balance, days outstanding, aging bucket | derived | derived (not a source) | A14 |

### 2.3 Scheduling, clinical documentation and charges

| Entity | Grain and key | Fields agents use | Today | Full database must provide | Read by |
|---|---|---|---|---|---|
| `visit` | one billable service, `visit_ref` | payer, provider, patient hash, service date, CPT, units | `visits.csv` (simulated in tests) | encounters with status (completed, cancelled), **provider and location**, units | A3 A15 A9 |
| `appointment` | `appt_ref` | payer on file, provider, patient hash, appointment date, booked date, expected CPT, status | `appointments.csv` (simulated) | schedule with **create / change history** (the trigger is "created or changed") | A1 A9 |
| `eligibility_response` | one subscriber answer, (trace, event) | active, plan begin/end, other payer, copay, coinsurance, deductible remaining, date of service asked, date produced | 271 (simulated) | stored eligibility results with the date of service they answered | A1 |
| `visit_note` | `visit_ref` | note date, signed date, minutes, documented elements (names only) | `notes.csv` (simulated) | **note status history** (started, signed, addended) and element presence; no note text is needed | A3 |
| `charge` | `charge_ref`, visit | CPT, units, **entered date** | `charges.csv` (simulated) | charge log with entered date and entering user (user is stored as a role, not a name) | A3 |

### 2.4 Reference and configuration

| Entity | Content | Today | Full database must provide | Read by |
|---|---|---|---|---|
| `prior_authorization`, `auth_requirement` | one request and outcome (status, window, units, linked appointment); payer + CPT pairs that need one | `authorizations.csv` (simulated), placeholder rows | the PM / portal authorization log and the payers' real requirement list | A2 |
| `payer`, `provider`, `patient_ref` | identifiers only; patient is a hash | from EDI | payer master with plan / product, provider master with specialty and location | all |
| `fee_schedule` | allowed amount per payer + CPT + modifier + effective / end date | `fee_schedule.csv` (synthetic) | **the real contracted rates**, with effective dates and version history | A10 A15 A1 A3 A6 A7 A8 A9 A14 (dollars) |
| `payer_appeal_window`, `payer_filing_window` | days | config rows (placeholders) | the real windows by payer / contract | A8 A10 / A5 A6 A7 |
| `carc_route`, `rejection_route` | owner and disposition by CARC / acknowledgement status | seeded placeholders | the practice's real work routing | A8 / A6 |
| `ncci_pair`, `mue_limit` | code edits | **synthetic stand-ins, not CMS** | the CMS NCCI and MUE tables (quarterly) | A5 |
| `learned_rule` | rules A9 proposed and a person approved | created by the approval command | n/a (ours) | A5 |

### 2.5 Engine tables (ours, not provided by the source)

`event` (append-only), `source_file`, `policy`, `decision_record`, `approval_request`. Every agent decision is one `decision_record`
(rules fired, input snapshot lineage, proposed action, mode, outcome).

## 3. What the source must provide that EDI cannot

These are the gaps a full database closes. Each is a field the agents currently infer or simulate.

1. **History, not only current state.** A live operational table usually holds today's value. Point-in-time replay needs created / updated times,
   an audit table or change capture for: claim status, appointment changes, note signature, charge entry, coverage on file. If none exists we snapshot
   daily from go-live, and everything before that is reconstructed from dates that are in the rows. **DECIDED: yes, the database keeps audit / history.**
   The adapter takes `known_at` from the audit timestamp (or the audit table) of each row, not from the extract date, and records which column it used.
2. **Submission truth.** Whether and when a claim was sent, and to whom (today: the 837 file date and the 999 / 277CA).
3. **Patient payments and statements** (`patient_payment` and `patient_statement` feeds exist and are simulated; A12 uses them for a staff-facing worklist; patient AR
   is still out of A14's totals; outreach consent and channel data are not modelled).
4. **Secondary / tertiary payer billing and coordination of benefits** (today: **no agent owns it**; the 271 other-payer flag is the only signal).
5. **Authorizations and referrals** with units, dates and status, **linked to the appointment they were requested for** (A2; `prior_authorization` feed is
   simulated today; referrals are not modelled).
6. **Contract documents or a structured contract table** (A10 uses the fee schedule only; no extraction).
7. **Work-queue and staff data** (tasks, who worked what, time spent) for A14 productivity, staffing and load balancing (none today).
8. **Bank deposits / lockbox** for A11 reconciliation (`bank_deposit` and `posting` feeds exist and are simulated; a real BAI2 or lockbox file
   and the PM posting log must be mapped to them; many payers send no trace number).
9. **Provider enrolment and credentialing** for A13 (`enrollment` and `provider_screening` feeds exist and are simulated; the rendering provider (NM1*82)
   is **not parsed from the 837 yet**, so service evidence comes from the visit extract; parsing it is a recommended adapter change).
10. **Identity.** One patient key across scheduling, billing, eligibility and notes. Today the member id is the key and is hashed with the tenant salt;
    cross-system identity resolution is **not built**. **DECIDED: yes, there is a master patient id.** The adapter hashes the master id (with the
    tenant salt) into `patient_ref`, so visits, appointments, notes, charges, eligibility and claims all join on one key. EDI files carry only the
    payer's member id, so a small crosswalk (member id -> master id) is loaded from the database and applied when an 837 / 835 / 271 is ingested;
    a member id with no crosswalk entry is kept under its own hash and reported as unresolved.

## 4. Rules the contract must hold (from CLAUDE.md)

| Rule | Consequence for the database adapter |
|---|---|
| No raw PHI in our store, logs or prompts | hash the patient identifier in the adapter, before the row is written; never copy names or birth dates |
| Read-only toward the client system | the adapter uses a read-only login on a replica; write-back is a separate, gated adapter limited to tasks and notes |
| Point in time | every row has a date it became known; replays use only rows known by the as-of date |
| Idempotency | a stable natural key per entity (listed above); re-extracting the same period changes nothing |
| Tenant isolation | `tenant_id` on every row; the adapter loads one tenant at a time |
| Money is exact | decimal, never float; source rounding is preserved |

## 5. KPI map: how each agent decides what to do

Two layers, so we review the right one:
- **Detection** is an explicit rule (rule 6: rules first). A person can see why a task was raised.
- **Ranking and triggering** is metric-driven. The metric is measured from the tenant's own history.

"Placeholder" means a number I chose to make the agent run; the three-year baseline replaces it (strategy: thresholds are fixed from baseline and shadow
evidence, not guessed). The baseline column says which data sets it.

| Agent | KPI (strategy) | Trigger | Detection rule | Metric that ranks or triggers | Placeholder thresholds | Baseline that sets them |
|---|---|---|---|---|---|---|
| A1 clearance | eligibility denial rate; pre-service clearance % | checkpoints 3 d and 1 d before a visit | 271 inactive / outside plan dates; other payer primary; no answer for this date of service; answer too old | clearance % = appointments with no open gap at 24 h; priority = allowed amount of the expected visit | checkpoints 3 and 1 day; stale after 14 days; coinsurance and copay from the 271 | your coverage-denial history (CARC 27, 31): how far ahead the lapse is knowable |
| A3 documentation | charge lag; missed-charge $ | visit with a gap, weekly while open | note missing / unsigned / missing element or minutes; no charge on a documented, unbilled visit | charge lag in days; priority = expected payer payment of the visit | note due 3 d, signature 3 d, charge lag 3 d, repeat 7 d; element lists | your charge-entry and signature timing (median and 90th percentile) |
| A5 prevention | clean-claim rate; first-pass paid rate | claim created before release | required fields; duplicate; timely filing; NCCI without modifier; MUE units; approved learned patterns | clean-claim and first-pass paid rates; priority = charge at risk | filing 365 d default, warn 30 d, fix in 2 d; **NCCI/MUE rows are synthetic** | CMS tables; your rejection / denial causes by rule |
| A6 submission | submission acceptance; rejection turnaround | 999 R/E, 277CA A3/A4 | routing table: technical vs business rejection; unknown = unrouted | rejection rate; priority = billed amount by urgency | fix in 3 d; filing risk 60 d | your rejection reasons and time-to-fix |
| A7 A/R | days in A/R; A/R > 90; touches per claim | claim unpaid beyond its expected payment date | none (a timing rule) | per-payer median days-to-pay; chance a claim pays on its own = (paid+1)/(n+2) over mature claims; priority = amount x (1 - chance) x urgency | default 30 d if under 5 history; mature 90 d; escalate 90 d; follow up 7 d; repeat 14 d; filing risk 60 d | your payer payment curves (the 3-year history is exactly this) |
| A8 denial | overturn rate; recovery $; cycle time | 835 denial, takeback (22), recoupment (PLB WO/72) | CARC routing table: category, owner, disposition | win probability by payer + CARC = (wins+1)/(n+2); priority = expected recovery | appeal window 180 d default | your appeal outcomes (needs resolved-denial history) |
| A9 learning | preventable denial recurrence | a payer-wide denial pattern | cluster: payer + CPT + CARC; A5 already flagged? | denial rate over the last 120 days of answered claims | 5 denials, 30% rate, 120-day window, 80% already-flagged, 80% overlap | your denial mix by payer and CPT; manager sign-off |
| A10 underpayment | underpaid $ detected / recovered | an 835 claim payment | paid + patient share below the fee schedule | gap vs contract; cause from the CARC on the line; pattern = same % short across lines | $1.00 floor; 20% on payer-history pricing; pattern needs 5 lines, within 1 point, half the short lines | your real contracts and underpayment history |
| A14 tower | cash forecast accuracy; backlog; productivity | continuous (daily) | four signals: backlog growth, payer slowdown, rejection spike, deadline critical | forecast WAPE and coverage; backlog by owner and age | +25% and 5 items; +7 d median days-to-pay; +5 points rejection share; due within 7 d; 28-day horizon, 80% interval | your own weekly backlog and cash history |
| A15 investigator | net collection rate; recovered leakage | every 28 days (sweep date) | realisation against contract fell by a slice (payer, payer+CPT) | realisation recent vs baseline; dollar impact; dollars by cause and by upstream flag; detected vs later-paid ledger | recent 56 d vs baseline 180 d by payment date; 8 lines, 500.00 expected, 5 points (placeholders) | your payer mix and seasonality (to set the thresholds); the revenue assurance lead's sign-off |
| A15-lite | validated leakage baseline | on request | denials, underpayments, rejections, unbilled visits, timely filing | recoverable vs structural $ | appeal 180 d, filing 365 d, G0 tolerance 0.01, 99% match | the contract with the client (G0 reconciliation) |
| A2 authorization | authorization turnaround; auth-related denials | checkpoints 7 d and 2 d before a visit needing authorization | none requested; denied; window expired; units used up; pending too long | turnaround days (request to decision); share of required appointments covered | 7 and 2 day checkpoints; pending after 7 days; requirement list is placeholder | your authorization log and denial history (CARC 197/198) |
| A11 cash | days to post; unapplied cash; reconciliation variance | an 835 payment, then weekly while a gap is open; an unexplained deposit | deposit missing / short / duplicate; claim not posted or partly posted | days to deposit and to post; unapplied cash and variance dollars | deposit due 5 d; post due 3 d; late over 7 d; match window 30 d | your bank file timing and posting lag by payer |
| A13 credentialing | credentialing denials; enrollment cycle time | provider + payer checked on each sweep; screening per provider | no active enrollment while services continue; expired; expiring; pending too long; excluded; stale screening | cycle time (application to effective); claim payment at risk | expiry warning 90 d; pending 90 d; service window 90 d; screening stale 35 d | your enrollment and denial history (CARC 185 and related) |
| A12 patient balance | patient collections; days in patient A/R | patient share confirmed, then weekly while open | dispute / hardship; credit; small balance; no statement; aging 30 / 60 / 90 | collections rate; average open age; open balance by stage | statement due 7 d; aging from 30 d; small balance 10.00 | your patient payment curve and write-off policy |
| A4 coding audit | coding denials; audit variance; coder productivity | each claim at the claim event | billed E/M level above or below the level the signed note's named elements support | audit variance rate over judged lines, by provider and code; dollar difference at contract | level table (placeholder); baseline elements; review in 3 days | your coding audit results and coding-denial history; the lead coder's level rules |

### 5.1 Where the claim "actions follow the metrics" is and is not true
- True for **ranking** (A7, A8, A9, A10, A14) and for **triggers that are rates or timing** (A7 expected payment date, A9 recurrence, A14 signals).
- Not true for **detection**: A5, A3, A1 and A10 raise tasks from explicit checks on the claim or note, and the metric only measures whether they are
  working. That is deliberate (a person must be able to see the rule).
- **No agent writes anything.** All actions are tasks and reviews in shadow mode; autonomy above L0 needs evidence, approval and the gaps in section 6.

## 6. Engine gaps that apply before any agent leaves shadow

Not data, but they decide how far the metrics can be trusted to act: kill switch, blast-radius limits, separate approver (maker-checker),
versioned policy, before / after values on write-back, failure injection tests, identity resolution, a value ledger, PHI masking checks, and a gate record per
promotion (strategy section 8 and 11C). Each is listed in `docs/ROADMAP.md`.

## 7. Open questions for you

1. ~~Audit timestamps or history~~ **Answered: yes.** Still open: for which tables (claims, appointments, notes, charges, coverage), and as columns or an
   audit table? That is the first thing to look at when the schema arrives.
2. ~~Master patient id~~ **Answered: yes.** Still open: is it the same id in the PM and the EHR, and how is a merged duplicate patient recorded?
3. Where do contracts live: a structured table, documents, or only in the 835s?
4. Who owns secondary billing / coordination of benefits today, and does the database hold the secondary payer and its claim state?
5. Which thresholds in section 5 should be set per payer from the baseline, and which are policy decisions for a manager?
6. Which KPI should be the first headline for the owner: days in A/R, net collection rate, or clean-claim rate?
