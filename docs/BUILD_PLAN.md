# KrisnAI RCM — build plan for Claude Code

Goal of this plan: get from an empty repo to **A15-lite (read-only leakage diagnostic) working on synthetic data**, then the **decision engine** and the first agents running in **shadow mode**. Each milestone ends with tests that prove it works.

Rule: finish a milestone, review, commit, then paste the next prompt. Don't skip ahead.

---

## Before you start (Gk provides)
- [ ] Table and column names of the existing EDI dashboard DB (`INFORMATION_SCHEMA.COLUMNS` output, names only, no data).
- [ ] 2–3 real 837P/835 files **de-identified**, or none (Claude Code will generate synthetic ones).
- [ ] One sample fee schedule layout (columns only is fine).
- [ ] Which PM system the first client uses (name only).
- [ ] Strategy v5 docx copied to `docs/strategy_v5.docx`.

---

## M0 — Repo, guardrails, synthetic data (1–2 days)
**Done when:** `pytest` passes; `make_synthetic.py` produces a matching 837P + 835 + 999 + 277CA set for ~500 claims across 4 payers, with known planted problems (denials by CARC, underpayments, timely-filing losses, unbilled visits).

> **Prompt:** Read CLAUDE.md and docs/BUILD_PLAN.md. Do milestone M0. Set up the repo layout, pyproject (ruff, pytest), a SQL Server connection config via env vars, and `tests/fixtures/make_synthetic.py` that generates synthetic X12 837P, 835, 999 and 277CA files plus a fee schedule CSV. Plant known problems with a ground-truth CSV listing every planted issue (claim id, type, expected $, recoverable or structural). Start in plan mode.

---

## M1 — Minimal core data model (2–3 days)
Tables (all with `tenant_id`, `source_file_id`, `loaded_at`):
`tenant, source_file, event, payer, provider, patient_ref (hashed), claim, claim_line, claim_dx, ack_999, ack_277ca, remit (835 CLP), remit_line (SVC), adjustment (CAS group/CARC/amount), remit_remark (RARC), plb_adjustment, payment (TRN/BPR), fee_schedule, ar_snapshot`.

**Done when:** Alembic migration creates everything on SQL Server; cross-tenant leak test passes; ERD written to `docs/data_model.md`.

> **Prompt:** Do M1. Design the minimal core data model listed in BUILD_PLAN.md as SQLAlchemy models + one Alembic migration for SQL Server. Event-sourced: raw `event` rows are append-only; normalized tables are rebuilt from events. Write docs/data_model.md with the ERD (mermaid) and one line per column explaining its X12 source (e.g. claim.claim_submitter_id ← CLM01). Plan mode first. If I've provided my existing EDI DB column list in docs/existing_schema.txt, map to it in the doc.

---

## M2 — X12 ingestion (3–4 days)
Parsers: 837P (loops 2000A/B, 2300 CLM/HI, 2400 SV1/DTP), 835 (CLP, SVC, CAS, RARC/LQ, PLB, BPR/TRN), 999 (AK2/IK3/IK4/IK5), 277CA (STC).
**Done when:** synthetic files load end to end; loading the same file twice changes nothing (idempotent on file hash + ISA13/GS06/ST02); malformed segment → file marked failed with reason, not a crash.

> **Prompt:** Do M2. Write tolerant X12 parsers for 837P, 835, 999 and 277CA in krisnai/ingest (read delimiters from ISA). Load into events then normalized tables. Add a CLI: `krisnai ingest <path> --tenant <id>`. Tests: round-trip on synthetic files, idempotency, malformed file handling. Plan mode first.

---

## M3 — Matching (2 days)
Claim ↔ remit: `CLP01 = CLM01`, fallback on payer claim number `CLP07`, then patient_ref + DOS + billed amount. Line ↔ line: SVC01 procedure + modifiers + DOS + units vs SV1. Remit ↔ payment: `TRN02` trace number.
**Done when:** match report shows match rate and unmatched reasons; ≥ 99% on synthetic; every match stores which rule matched it.

> **Prompt:** Do M3. Build krisnai/match with the matching rules in BUILD_PLAN.md, storing match_method on each link. Produce a match quality report (counts, rate, unmatched reasons). Tests use the synthetic ground truth. Plan mode first.

---

## M4 — Metric dictionary + baseline (2 days)
KPIs as SQL views with a written definition each: clean claim rate, first-pass paid rate, denial rate (count and $) by CARC/payer/CPT, days in AR, AR > 90, net collection rate, underpayment $, charge lag, rejection rate (999/277CA).
**Done when:** each KPI has a definition in `docs/metrics.md`, a view, and a test against hand-computed values on a tiny fixture; every KPI can be computed `as_of` a date.

> **Prompt:** Do M4. Create the metric dictionary in docs/metrics.md and SQL Server views in krisnai/metrics. Each KPI must support an as_of date. Test each one against a small hand-built fixture where I can verify the numbers by eye. Plan mode first.

---

## M5 — A15-lite leakage diagnostic (4–5 days) ← first sellable piece
Logic:
- Expected allowed = fee schedule × units (with modifier/multiple-procedure rules); fallback = payer + CPT median paid, flagged as fallback.
- Classify each gap: denial (by CARC category), underpayment, unbilled visit, timely filing lost, unexplained adjustment.
- Recoverable if appeal/filing window still open; otherwise structural.
- Map each finding to the agent that would address it (A1, A3, A5, A6, A7, A8, A10).
- Findings are "detected", never "recovered".

Output: JSON + Excel report (by payer, CPT, location, provider; recoverable vs structural; ranked opportunity list; baseline KPI sheet), plus a reconciliation check vs source totals (G0).

**Done when:** on synthetic data it finds ≥ 95% of planted issues with the right type and $, and the reconciliation check passes.

> **Prompt:** Do M5: agents/a15_lite. Read-only. Implement expected allowed, gap classification, recoverable vs structural, agent mapping, and the report (JSON + xlsx via openpyxl). Add the G0 reconciliation check that stops the report if totals differ from source beyond a configurable tolerance. Evaluate against the synthetic ground truth and print precision/recall per issue type. Plan mode first.

---

## M6 — Decision engine core (4–5 days)
- `engine/pipeline.py`: the 8 steps as an interface every agent implements: trigger → context pack → deterministic checks → model reasoning → confidence & materiality → human checkpoint → action adapter → verify & learn.
- `engine/policy.py`: per tenant + action type: allowed/denied, autonomy level, $ thresholds, approver role. Default L0 shadow.
- `engine/decision_record.py`: table + writer (fields in CLAUDE.md).
- `engine/models.py`: model abstraction with a stub provider.
- `engine/replay.py`: point-in-time replay harness that runs an agent over history using only data known at each event time.
- `engine/adapters/`: task/note adapter (disabled by default), clearinghouse adapter (stub).
- Approval queue table + API endpoints (list, approve, reject with reason).

**Done when:** a dummy agent runs through all 8 steps in shadow mode, writes decision records, respects policy (a denied action never executes), and replay produces identical results on re-run.

> **Prompt:** Do M6. Build the decision engine in krisnai/engine as described in BUILD_PLAN.md. Include tests proving: denied actions never execute, shadow mode never calls adapters, every run writes a decision record, replay is deterministic and has no future leakage. Plan mode first.

---

## M7 — A8 Denial & appeal, shadow mode (4 days)
- Trigger: 835 denial line, takeback, recoupment.
- CARC routing table (config, not code): front desk 27, 31, 197, 198, 22 · coding 4, 11, 97, 50 · billing 16, 18, 29 (extend from synthetic set).
- Deadline calc from payer appeal days (config per payer).
- Correctable vs appealable vs write-off review.
- Expected recovery = $ × win probability (simple payer+CARC historical rate first, model later).
- Appeal drafting: model stub only for now.

**Done when:** replay over synthetic history assigns category/owner/deadline for every denial; decision records written; nothing executes. Spec written in `docs/specs/A8.md` (Appendix A fields, thresholds left blank for sign-off).

> **Prompt:** Do M7: agents/a8_denial on the decision engine, shadow mode only. Put CARC routing and payer appeal windows in config tables. Write docs/specs/A8.md with every Appendix A field; leave thresholds as TBD for business sign-off. Report replay results. Plan mode first.

---

## M8 → M10 — A5, A7, A6 in shadow mode
Same pattern as M7, one agent per milestone, each with its `docs/specs/Ax.md`:
- **M8 A5 Claim prevention:** pre-release checks (required fields, NCCI pair without modifier, MUE, auth units, eligibility on DOS, duplicate, TFL days). Flags only; never edits codes.
- **M9 A7 AR next-best-action:** expected payment date per payer, priority = $ × (1 − p_paid) × urgency, next-action suggestion.
- **M10 A6 Submission & response:** map 999/277CA errors to fix types; technical fix proposals from provider master; resubmission only via clearinghouse stub.

> **Prompt (repeat per agent):** Do M8 (A5) following the M7 pattern: shadow mode only, config-driven rules, decision records, docs/specs/A5.md with Appendix A fields, replay results vs synthetic ground truth. Plan mode first.

---

## Later (do not start yet)
A14 control tower dashboards, A1 and A3 (need PM schedule and note data), A10 (needs real contracts), live mode and approvals UI, PM write-back adapter, durable workflow engine decision (ADR-0003), SOC 2 controls.

## Open decisions for Gk / management
- Hosting and model provider with BAA (needed before any real PHI).
- Durable workflow engine (Temporal vs keeping job table).
- Thresholds for each agent's Appendix A spec (business sign-off before shadow results are reviewed).
