# Brief: design planned (TBD) tables for the KrisnnAI canonical data model

KrisnnAI RCM is an intelligence layer over a practice's PM/EHR and clearinghouse. Synthetic data only, no real PHI. The brand is spelled
**KrisnnAI** (double n) everywhere. The canonical model has 41 reviewed, locked tables. Some tables are still "TBD" (planned, not designed).
Your job: design the TBD tables assigned to you, in the same style as the locked tables, and re-point the agent fields that were waiting for them.

Work folder: `tools/data_model/`  (use the Write tool for files; the Bash tool mangles heredoc quotes/backslashes).

## Read first
1. `model.json` -- the 41 existing tables with all columns (name, type, priority, link, desc, fb) plus the `tbd` list (name, phase, what, tier, enables, plugs, until).
2. `gen_final.py` lines 1-60 (helpers) and the agent tables (search `GA = "5 Agent outputs"`, `agent_task`, `agent_finding`) -- copy their style exactly.
   `gen_core.py` lines 28-65 define `common()`, `audit()`, `L()`, `M_ I_ O_`.
3. `docs/data_model/KrisnnAI-Agent-Field-Remap.xlsx` (the version before the planned-table review), sheet `Remapped`: columns Area, Agent, Group, Field, What it is, Direction, Old table, Old column,
   Result, Final table, Final column, Note. Your rows are those with Result = "Planned table" and Final table in your assignment. Read every one of them
   (Field + What it is + Note) to learn what the agents really need to read, produce or store.
4. `gap_decisions.md` and `gap_block.py` for decisions already made (do not redo them).

## Rules (non-negotiable)
- Every table: first column `<table>_id` (internal identity), then `tenant_id`; the client's own number goes in `<table>_number` flagged restricted (`L(..., True)`), only when the client has one.
- Every column is a 7-tuple built with `L(name, sqltype, priority, link, description, fallback, restricted=False)`; priority is `M_` Mandatory, `I_` Important or `O_` Optional.
  Every column MUST have a plain-language description (why we need it) and a fallback (what to use if the source does not send it).
- Table-level: `priority`, `group` (use an existing group string: "1 Appointment", "2 Encounter", "3 Bill and claim", G4, GA, "Reference", "Data operations"), `pair`
  (header / detail / ledger / event / reference / ...), `what` (one row is...), `purpose`, `metrics`, `fallback` ladder (numbered, best to weakest source).
- Money is `DECIMAL(12,2)`. Dates `DATE`, timestamps `DATETIME2(0)`. Booleans `BIT`.
- No names, birth dates, addresses, phone numbers, raw member/patient numbers or free text with patient content. Patient/member identifiers are salted hashes only. Roles, never named people.
- Use `common("<table>")` at the start and `audit("<table>")` (versioned) or `audit("<table>", False)` (append-only) at the end. Versioned tables carry `previous_<table>_id`.
- Link columns to existing tables with the `link` argument (e.g. `L("payer_id","INT",I_,"payer",...)`); the target must exist in the model or in your own new tables.
- Do NOT use the words "fact" or "dim" in any table or column name. Plain names only.
- Agent output tables (group GA) are written by agents as they run and never rebuilt from canonical tables; agents never write into canonical tables.
- KPIs, rates and counts are NOT stored: they are views over tables. Store only what cannot be rebuilt (events, decisions, predictions, snapshots that depend on what was known then).
- Keep tables lean: only columns some agent or metric really needs, plus the standard identity/audit columns. Prefer an existing column on an existing table over a new table.
  If you find that a TBD table is not needed because existing columns already cover it, say so and do not create it.
- You must NOT modify any existing table or any shared file (`gen_final.py`, `model.json`, workbooks). Write only your own module and notes file.

## Deliverables (your own files only)
1. `plan\plan_<K>.py` (K = your letter). Plain python executed inside the gen_final namespace (so `add`, `common`, `audit`, `L`, `M_`, `I_`, `O_`, `T`, `GA`, `G4`, `NOTE_` are globals). It must:
   - call `add("<table>", priority, group, pair, what, purpose, metrics, fallback, cols)` for each new table (no `status=` argument);
   - define `TBD_DONE = ["referral", ...]` : the TBD names you designed (they will be removed from the TBD list), and nothing else;
   - define `REMAP = {("<old table>", "<old column>"): ("<final table>", "<final column or empty>", "<result>", "<short note>")}` covering EVERY row of the
     Remapped sheet whose Final table is one of your tables. Result is one of: Exact (same column name), Renamed, Added, Derived (computed, final column may be empty), Partial, Dropped (decided not to store, say why).
     Use Added for columns that exist only because of this design; any agent field with truly no home must be Dropped with a reason, never silently omitted.
2. `plan\notes_<K>.md`: for each table, plain-language summary (what a row is, why, which agents need it with counts, key decisions and defaults you took, anything you dropped and why,
   and any change you recommend to a LOCKED table, listed but not made).
3. Validate before finishing: `python test_plan.py plan\plan_<K>.py` must print `OK: module is valid`.

## Final report (short)
Return: tables designed (column counts), TBD names covered, how many REMAP rows by result, tables you decided NOT to create and why, recommendations for locked tables, and the validator's last line.
Do not commit, push, deploy or open any browser. Do not touch files outside the work folder (read-only access to the Downloads workbook).
