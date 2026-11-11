# Query Admin: where every chart's SQL lives

Every data section of `fin_data.js` is produced by a named query stored in a local registry. The Python that assembles
the Sankey, triangle and so on stays in `tools/analytics/export_fin_data.py`; only the SQL moved.

| Piece | File |
|---|---|
| Registry, resolver, workflow, impact, audit | `tools/analytics/qreg.py` (SQLite, `var/analytics_registry.sqlite`, git-ignored) |
| SQL validation and read-only execution | `tools/analytics/qsafe.py` |
| Seed (the exporter's former `SQL_*` constants, now `:tenant_id` named queries) | `tools/analytics/fin_seed.py` |
| Test run with diff, "publish to site data" | `tools/analytics/qsvc.py` |
| Admin window (standard library `http.server`) | `tools/analytics/query_admin.py`, `admin_ui/index.html` |

Run: `python tools/analytics/query_admin.py` then open http://127.0.0.1:8780/ (stop with Ctrl+C).
The registry is not part of the locked `krisnnai_r2` model and holds no patient data (SQL text, scope names, audit rows).
Exporter without the window: `python tools/analytics/export_fin_data.py [--role billing_manager]`.

## Hierarchy

solution (KrisnnAI RCM analytics) > parent application (Financial) > application (Overview, Billing, Payments, A/R,
Denials, Patient, Payers) > customer (tenant; 1 = demo practice) > role (billing_manager, practice_manager).

A query saved at a level applies to everything below it. The narrowest node that has a PUBLISHED version wins;
otherwise the next broader level is used. Drafts, in-review and retired versions never take part in resolution.

Worked example (`billing.monthly`, the Billing page's monthly chart):

1. Seeded at solution level, v1. Every context resolves to it.
2. Billing application override published (say a different status mix). `billing / tenant 1 / billing_manager` now resolves
   to the application level; the Payments page is unaffected (the query is not even offered there).
3. A role override is published for `billing_manager`. That role resolves to the role level; `practice_manager` still gets
   the application override (fall-through).
4. Impact preview for an edit at solution level now says: 3 contexts affected, 1 shadowed (`billing/1/billing_manager`
   keeps its narrower override). An edit at role level touches 1 context.
5. "Retire override" on the role node: `billing_manager` falls back to the application version.

`resolve(query_id, {app, customer, role})` returns the SQL, the level, the node and the version it came from.

## Workflow

draft -> test run -> submit for review -> approve -> publish. Status values: `draft`, `in_review`, `approved`
(between approve and publish), `published`, `retired`. One open version per query and node; one published version per
query and node (publishing retires the previous one).

- Test run: runs the draft read-only for the selected tenant, shows row count, preview and a diff (rows added/removed)
  against the SQL that is effective at that node today, and probes a tenant with no data (must return nothing).
  Submit is refused unless the current text passed a test run; editing the draft clears that.
- Rollback: re-publishes an earlier (retired) version's SQL as a NEW version; history is never rewritten.
  "Retire override" removes a narrower override so the query falls through (not allowed at solution level).
- Impact preview: computed from the hierarchy, shown for every selected query and node.
- Approval mode (setting, audited): `demo` (default) lets the maker approve their own change and marks it
  "single-user demo" in the version and the audit log; `strict` refuses self-approval. There is no login: the actor
  name is typed in the page, so strict mode is a process guard on one machine, not an identity guarantee.
- Audit log: every action (draft, test, submit, approve, reject, publish, rollback, retire, mode change, site publish)
  with actor, time, mode and details. Rows are hash-chained; the page shows whether the chain is intact.

## Publish to site data

Resolves every query for tenant 1 (role-less, each query in its owning application), runs the exporter and writes
`out/fin/fin_data.js`. It does not copy into the Vercel site folder and does not deploy: copy the file and deploy when
ready. The audit row records the path, size, a hash of the content without `generated_at`, and any queries resolved
below solution level. Role overrides are visible in the admin and the resolver but a single static file has no role,
so they only reach the file with `export_fin_data.py --role <role>`.

Output with the seed only is byte-identical to the previous exporter apart from `meta.generated_at` (checked once
against the pre-refactor exporter: same SHA-256 after removing `generated_at`; `tests/test_query_admin.py` checks that
two runs agree).

## Safety limits (hard rules 1, 2, 8, 10)

Enforced before and while running:
- One statement, `SELECT` or `WITH ... SELECT` only. The SQL is tokenized by our own scanner; comments are dropped,
  quoted identifiers, `$` quoting, stray characters and unterminated strings/comments are rejected, any DDL/DML/utility
  keyword anywhere (INSERT, UPDATE, DELETE, INTO, FOR UPDATE, SET, COPY ...) is rejected. The text that is executed is
  rebuilt from the validated tokens, so what was checked is what runs.
- Function allow-list (aggregates, `coalesce`, `to_char`, `width_bucket`, percentiles ...), cast allow-list, table
  allow-list per query (the tables the seed uses), no schema-qualified names, no table functions.
- `:tenant_id` is required, with one `tenant_id = :tenant_id` condition (not next to `OR`) per table reference. Only the
  declared binds (`:tenant_id`, `:asof`, `:d`) are accepted; values are bound by the driver, never concatenated.
- Executed on a read-only connection (`set_session(readonly=True)`, re-checked with `SHOW transaction_read_only` before
  each run), `statement_timeout` (120 s default) and a row cap (5,000), then rolled back.
- Result columns must equal the query's contract exactly (names, order, value types). Column names that look like
  identifiers (`*_id`, `patient_id`, `dob`, ...) are rejected; text cells that look like UUIDs, hashes or SSNs, or are
  longer than 80 characters, are rejected. Money columns must be `Decimal`; a float fails the run.
- The page binds to 127.0.0.1:8780, checks the Host header, and requires a custom header plus JSON content type on every
  POST. The database password is read from the existing config by `r2load.connect()` and is never returned, logged or
  stored; connection errors are shown as "database connection problem (details hidden)".

What the validation cannot guarantee:
- Tenant isolation is a static heuristic plus a runtime probe, not a proof. A query can contain the required
  conditions yet join in a wrong way (for example a join that fans rows out, or a filter on one table but a subquery that
  re-reads another through a condition we count but do not understand). The empty-tenant probe catches queries that
  return data for a tenant with none, not every cross-tenant mix.
- "No person-level data" is name/shape based. A column with an allowed name can still carry a per-person value (an
  integer id aliased as `lines`, or a small text value). Reviewers must read the SQL; the column and value checks are a
  net, not a guarantee. The table allow-list limits which tables are readable but `claim`, `claim_line` and `ledger_entry`
  do hold patient references.
- Semantics are not checked: an edit can be valid SQL with the right columns and still compute a wrong number. The
  diff, the impact preview, the review step and the tests on `fin_data.js` (tie-outs) are the controls for that.
- Cost is bounded by timeout and row cap, not predicted; a heavy query can still hold the database for the timeout.
- A `FROM` inside `EXTRACT(... FROM ...)` is treated as a table reference and rejected (conservative).
- No authentication, local use only; strict mode relies on typed actor names.
