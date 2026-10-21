# UI mapping: the product preview and what this repo can feed it

The preview is the "Product preview" section of the KrisnnAI site (`krisnai-site/product.html`; no PHI). This page says, per screen, what feeds it from
`krisnai-rcm`, and what does not exist yet. Read-only today: the data reaches the page through `ui_data.js` (see `docs/ui.md`, produced by
`krisnai/demo/export.py`). Checked against the preview on 2026-10-19 (as of 2026-10-14 in the data). The live `/app` is behind a sign-in; the preview was
checked locally with a stand-in login.

## Logins: who sees what (preview, 2026-10-19)
The sign-in page has no role choice. Inside the preview a **"Logged in as"** dropdown in the header lists ten staff roles, two managers and a Product tour. It
starts on the signed-in role if the site knows it, else on Revenue owner. There is no automated demo path: a person explores freely. Each staff role has a
queue (engine cards whose `owner` and `agent` match), a Work group (My work, plus Approval queue and Claim timeline where they apply), a Team group (Team &
queues, Agent activity, Trust & QA) and three role-specific screens: **Results**, **Setup**, **Showcase**.

| Login | Queue (engine owner / agent) | Open items (as of 2026-10-14) | Results | Setup | Showcase |
|---|---|---|---|---|---|
| Billing specialist | `biller`; `billing` with A6, A7 | 119 | My scorecard | Rules I rely on (rejection routes) | One item, end to end |
| Denial specialist | every A8 denial (`billing`, `coding`, `front_desk`) | 238 | My scorecard | Rules I rely on (CARC routes) | One item, end to end |
| AR lead | `ar_lead` (A7) | 112 | My scorecard | Rules I rely on (windows) | One item, end to end |
| Payment poster | `payment_poster` (A11) | 39 | My scorecard | none | One item, end to end |
| Finance | `finance` (A10, A11) | 303 | My scorecard | Rules I rely on (fee schedule) | One item, end to end |
| Provider | `provider` (A3 signatures) | 371 | My scorecard | none | One item, end to end |
| Coder | `coder`/`coding` with A4, A5 | 18 | My scorecard | Rules I rely on (NCCI, MUE) | One item, end to end |
| Front desk | `front_desk` | 64 | My scorecard | Rules I rely on | One item, end to end |
| Practice manager | `practice_manager` (A9) | 2 | Morning brief | Agent controls | One item, end to end |
| Revenue owner / CFO | `revenue_assurance_lead` (A15) | 12 | Analytics, History replay, My scorecard | Agent controls, Connections | One item, end to end |
| Billing manager | billing staff (billers, denial and AR specialists) | team view | Workflow analytics | n/a | n/a |
| Coding manager | coders | team view | Workflow analytics | n/a | n/a |
| Product tour (not a login) | none | n/a | Morning brief, Analytics, History replay, Value ledger | Agent controls, Connections | Claim journey, Day in fast-forward, What if, Agent report cards, Before / after |

Front desk's queue is denials (A8) because A1 and A2 have no open tasks in the demo run: every appointment is in the past at the as-of date. The filing and
appeal windows tables in "Rules I rely on" are empty in the demo run (the engine uses its 365-day default). Not a login: Patient billing
(`patient_billing`, 518 items) and Compliance (`compliance_owner`, 6 items); engine cards for those owners are not shown to anyone yet.

## Review workspace (My work, every role with a queue)
Clicking **Review** on an item opens a workspace: *what the engine found* (rules passed or flagged, from the card), *where this fits in the workflow* (text
copied from the site's Workflows page, labelled as a design example, not a result from this run), and decision options per action type (A1, A2, A4, A6,
A7, A8, A10, A13 and the rest of the queue's action types). Choosing an override needs a typed reason. The last step shows "Recorded" with a demo label and
"nothing was sent". Decisions live only in the browser session: no write-back, no approval API.

## Manager logins: staff analytics (synthetic)
`krisnai/demo/staff.py` builds a **synthetic** workforce (8 billing staff, 6 coders; fictional names, labelled synthetic on screen) with a planted answer key
of strengths and weaknesses, then analyses it the way a real task log would be. It feeds `ui_data.staff` and these screens:

| Screen | What it shows |
|---|---|
| Workflow analytics (home) | six tabs: Throughput (stacked bars, first-pass line), Speed vs quality (scatter), Skill matrix, Handling time (box plots), Rework cost, Capacity scenarios |
| Team workload, Employee analysis | per-person load, speed and first-pass rate by task type, with a minimum sample size before anything is flagged |
| Work allocation | suggested placement (most constrained task types first; a person with a quality gap on that task is excluded); accept, override with a warning, or accept all; a "Not placed" list with reasons |
| Training plan | the evidence, the module, a possible mentor, assign |
| Improvements | process changes the analysis points to |

Capacity scenarios (12 weeks, shown over 6): even split, suggested allocation, + training closes the gaps, + 10% overtime, + an upstream fix halving the top
denial cause. In the demo run the planted answer key is found 9 of 9 with none spurious; for billing, the suggested allocation clears 311 vs 263 right the
first time in week 1, in 3 vs 5 weeks, with 6.7 vs 10.8 rework hours; the coding team uses about 45% of its time; 19 `a8_fix_task` items cannot be placed (no
coder history); the billing ceiling is about 614 tasks a week. **These numbers come from simulated staff**; real staff analytics needs task-completion
logging (not built) and the client's sign-off on measuring individuals. The 35-hour week and other assumptions are listed in `staff.assumptions`.

## Agent names in the preview
A1 Gatekeeper · A2 Permit Clerk · A3 Note Chaser · A4 Code Whisperer · A5 Mirror · A6 Courier · A7 Hunter · A8 Advocate · A9 Coach · A10 Auditor ·
A11 Bookkeeper · A12 Concierge · A14 Captain · A15 Detective (full) / Scout (A15-lite). Runner = the portal bot (`integrations/portal`). Scribe = the decision record.

## Screens
| Preview screen | Fed by | Status |
|---|---|---|
| **My work** (`W`: amt, claim, patient, payer, due, agent, priority, why, action, alternatives, confidence) | `ui_data.queue` (A14 `open_cards`). Fields: `value`, `claim`, `payer`, `billed`, `deadline`, `agent`, `priority`, `why`, `next_steps`, `confidence`, `queue_type`, `owner` | Ready (this change added `claim`, `payer`, `billed`, `queue_type`, `confidence`, `filing_days_left`, `action_type`). Role filter = card `owner`. "Alternatives" = the other `next_steps`. Patient column: only a salted reference exists, never a name |
| **Approval queue** (`A`: batches and single items by agent) | engine approvals service (`engine/approvals`), A6 resubmit review, A8 appeal tasks, A5 holds, A10 dispute packages, A9 rule proposals + forward test | Data exists. Approve / reject needs the approval API and **maker-checker**, which are not built |
| **Claim timeline** (`TL`) | `event`, `decision_record` and lineage per claim | Feasible; needs a per-claim query (not written) |
| **Team & queues** | A14 backlog, queues, signals | Partial. "Captain suggests rebalance" needs staff and task logs (none) |
| **Agent activity** (level, counts, live feed, claim map) | decision counts per agent (`ui_data.agents`), decision stream | Counts: ready. **Levels L1-L4 shown in the preview are not real**: every agent is L0 / shadow |
| **Trust & QA** (gates, QA sample queue, drift and safety alerts) | release gates G0-G5, policy table, replay | Not built (gates are docs only; no QA sampling, no drift detection, no auto-demotion) |
| **Morning brief** | A14 daily escalation review + cash forecast | Ready |
| **Analytics** (scorecard, payers, denials by CARC, payer x reason, AR aging, cash, procedures, providers, opportunities) | the 9 KPIs (`docs/metrics.md`), A8 / A10 decisions, A15 slices, open cards | Mostly ready. Providers table: rendering provider is not parsed from the 837 |
| **History replay** (data health, reconciliation to PM, baseline, what agents would have done, money left behind, learned rules, payer changes, one-claim example) | G0 reconciliation, replay engine, A15-lite baseline, A9 learned rules, A15 slices | Mostly ready; the best match |
| **Value ledger** (detected vs confirmed by month, 10% holdout, latest confirmed) | A15 detected-vs-later-paid ledger, A11 postings | Partial. "Confirmed" needs the ERA match to be attributed; **the 10% holdout is not built** |
| **Agent controls** (levels, kill switches by tenant / payer / agent, change log with gate evidence) | policy table (default allowed / L0 / shadow) | Policy table only. **Kill switch, blast-radius limits, versioned policy and the change log are not built** |
| **Connections** (ports, swap-to) | adapters: disabled / stub, mock + Stedi clearinghouse, FHIR, portal | Mock and sandbox adapters exist; swapping is configuration. Eligibility verified live on Stedi only |
| **My scorecard** (per role) | `ui_data.queue_stats`: per owner and agent, open count, dollars, by cause, by payer, age, due | Ready (real counts from the run) |
| **Rules I rely on** (per role) | `ui_data.reference`: CARC and rejection routes, NCCI pairs, MUE limits, fee schedule, authorization requirements, filing and appeal windows | Ready, read-only. Windows tables are empty in the demo run |
| **One item, end to end** (per role) | one real queue item plus the Workflows-page text | Item is real; the "without KrisnAI" comparison is a design example, labelled so |
| **Workflow analytics, Team workload, Employee analysis, Work allocation, Training plan, Improvements** (managers) | `ui_data.staff` from `krisnai/demo/staff.py` | **Synthetic staff.** Needs task-completion logging and client policy sign-off to be real |
| Showcase: Claim journey, Day in fast-forward, What if, Agent report cards, Before / after | demo content; What if and report cards could use replay; Before / after needs the holdout | Not fed |

## Worklist pills (Billing screen)
| Pill | Source |
|---|---|
| Denial | A8 (`a8_fix_task`, `a8_appeal_task`, takeback and recoupment reviews) |
| Rejection | A6 (`a6_rejection_task`, `a6_resubmit_review`) |
| No response | A7 (`a7_status_check_task`, `a7_escalate_review`) |
| Underpaid | A10 (`a10_dispute_review`, `a10_contract_check_task`) |
| Filing risk | A7 when `filing_days_left` is 60 or less. A5 filing-window cards are not yet tagged |

## KPI tiles on the standalone `krisnai-ui` Billing page
| Tile | Feed |
|---|---|
| Claims needing action | count of open cards with a `queue_type` |
| $ at risk | the UI sums billed; `value` is expected recovery. Show both; they mean different things |
| Done today | **not available**: nothing is "resolved" in shadow mode; task completion write-back does not exist |
| $ confirmed this week | **not available**: the nearest is the A15 detected-vs-later-paid ledger (attribution by key match, not confirmation) |

## Rules for the UI
- Show a shadow banner (`meta.shadow` is always true). Show agent levels as "proposed", not "active".
- Money is a two-decimal string, dates are ISO strings, `billed` and `confidence` can be null.
- Real client data never goes into a public deployment; the JSON for a real client sits behind that client's own access control.

## What unlocks the most screens
The engine guardrails: kill switch and blast-radius limits, maker-checker, versioned policy with a change log. Together they feed Agent controls, Approval
queue (action side), Trust & QA, and make the levels shown in Agent activity real.
