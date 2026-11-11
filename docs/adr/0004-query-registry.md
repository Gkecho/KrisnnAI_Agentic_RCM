# ADR-0004: Query registry for financial analytics

Status: accepted (2026-11-11)

## Context
The SQL behind every chart of `fin_data.js` lived as inline constants in `tools/analytics/export_fin_data.py`. The owner wants
each chart's SQL editable in one place with the hierarchy used in an earlier product (solution > parent application >
application > customer > role): a change at a broad level reaches everything below, a narrower level can override, and the
narrowest published override wins. Changes need review, rollback and an audit trail. Hard rules 1, 2, 8 and 10 apply to any
SQL that can be edited.

## Decisions
1. **SQLite registry outside the locked model.** `var/analytics_registry.sqlite` (git-ignored) holds scope nodes, query
   specs, versions and the audit log. It is not a table in `krisnnai_r2`: that model is locked, the registry holds no
   patient data, and nothing in the analytics path may write to the client-facing database (rule 2).
2. **Standard-library server.** The admin window is `http.server` on 127.0.0.1:8780 with one static HTML page. FastAPI
   cannot be loaded on this PC; the stack rule favours FastAPI in general, so this is a documented local-tool exception.
   Ports 8765 and 8766 belong to other apps and are not used.
3. **Option C: publish-only.** The admin regenerates `out/fin/fin_data.js` and stops. It never copies into the site
   folder and never deploys; a person does that. The site stays static and cannot be changed by the admin by accident.
4. **Demo-relaxed approval by default.** Setting `approval_mode` is `demo` (maker may approve their own change, recorded as
   "single-user demo") or `strict` (self-approval refused). Default `demo` because there is one user today. There is no
   authentication, so strict is a process guard, not identity proof. Revisit before a second person or tenant uses it.
5. **Validation by our own tokenizer, not a SQL library.** One SELECT statement, function/table/cast allow-lists, required
   per-table `tenant_id = :tenant_id`, declared binds only, executed text rebuilt from validated tokens, read-only
   transaction, statement timeout, row cap, and an exact result-column contract with Decimal money. The limits (it is a
   guard, not a proof) are written down in `docs/fin_admin.md`.
6. **Seed from the exporter.** The former `SQL_*` constants are named solution-level queries (`flow.links`, `lag.paid`,
   `ar.matrix`, `denials.matrix` ...) with every column aliased, because the contract is by column name and order. The
   assembly code stays in Python. Output with the seed is byte-identical to the previous exporter except `generated_at`.
7. **Resolution context for the static file.** `fin_data.js` has no role, so "publish to site data" resolves each query
   for the tenant in its owning application with no role; role overrides apply to role-aware consumers and to
   `export_fin_data.py --role`.

## Consequences
- Editing a chart's SQL is a reviewed, versioned, reversible change with an impact preview and a hash-chained audit log.
- The exporter now depends on `qreg`/`qsafe` and on a registry file (created and seeded on first use).
- Existing test `test_every_query_filters_tenant` now checks the seed in `fin_seed.py` instead of `SQL_*` constants.
- Semantic correctness of an edited query is still a human review task.
