# UI mapping: the product preview and what this repo can feed it

The preview is the "Product preview" section of the KrisnnAI site (`krisnai-site/product.html` and `product-x.js`; illustrative data, no PHI). This page
says, per screen, what feeds it from `krisnai-rcm`, and what does not exist yet. Read-only today: the data reaches a page through `ui_data.json` /
`ui_data.js` (see `docs/ui.md`). Checked against the preview files on 2026-10-16; the live `/app` is behind a sign-in and was not opened.

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
