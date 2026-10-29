# Decision engine (M6)

Every agent runs through `krisnnai.engine.run(engine, tenant, agent, event_id, adapters=...)`. The agent cannot skip policy,
cannot call an adapter itself, and every run ends in exactly one **decision record** (CLAUDE.md fields, table `decision_record`).

## The 8 steps
| # | step | who | what |
|---|---|---|---|
| 1 | trigger | agent `wants(event)` | no match = no run, no record |
| 2 | context pack | agent `context_pack(session, event, as_of)` | only data known at the event's time (`known_event_ids`); lineage stored |
| 3 | deterministic checks | agent | plain rules, each with id and result; a failed `blocking` rule stops execution |
| 4 | model reasoning | agent `model_prompt` + engine `call_model` | optional; stub provider by default; a real provider needs an approved BAA |
| 5 | confidence and materiality | agent `assess` | a `Proposal`: action, payload, dollars, confidence, verification condition |
| 6 | human checkpoint | engine + policy | decides denied / shadow / observed / assisted / pending approval / execute |
| 7 | action adapter | engine | the only call to an adapter; disabled or stub by default |
| 8 | verify and learn | agent `verify` | condition and result stored on the record |

## Policy (`policy` table, per tenant + action type)
No row = **allowed, L0, shadow**: the engine records the decision and never executes.
| situation | outcome |
|---|---|
| `allowed = false` | `denied`: never executes, no approval request |
| a blocking check failed | `blocked_by_check` |
| mode `shadow`, or a replay | `shadow`: record only, adapters never called |
| live, L0 / L1 | `observed` / `assisted`: no execution |
| live, L2 | `pending_approval`; approving marks the draft approved, nothing runs |
| live, L3 | `pending_approval`; runs once after a named approval |
| live, L4 | runs alone only if materiality <= `max_amount` and confidence >= 0.90, otherwise `pending_approval` |
Promotion is a change to the `policy` row backed by evidence, never a code default.

## Approvals (`engine/approvals.py`)
`list_requests`, `approve(approver, approver_role)`, `reject(approver, reason)`. A named approver is required, the role must match the
policy's `approver_role`, a request can be decided once, rejection needs a reason, and approval is refused if the policy no longer allows live execution.

## Replay (`engine/replay.py`)
Runs an agent over events in `(known_at, id)` order, each with `as_of = event.known_at`, always shadow and with no adapters. Records are keyed
on (event, agent, action), so a second replay returns identical fingerprints (a hash of the record without timestamps).

## Adapters
`task_note` (disabled by default; when enabled it only fills an outbox, there is no PM connector yet) and `clearinghouse` (stub: records, never sends).

## Not built yet
The HTTP endpoints for the approval queue (FastAPI cannot load on the development PC: Windows Smart App Control blocks `pydantic-core`;
the service functions above are what the endpoints will call). Authentication and role checks beyond the text label. A scheduler that triggers agents.
