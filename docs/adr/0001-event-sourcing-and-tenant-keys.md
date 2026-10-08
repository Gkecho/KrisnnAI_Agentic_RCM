# ADR-0001: Event-sourced core model with tenant-composite keys

Status: accepted (M1). Date: 2026-10-08.

## Context
KrisnAI must replay history point in time (rule 9), stay idempotent on re-ingest (rule 7) and
never mix tenants (rule 8), on SQL Server, without trusting every query to remember a WHERE clause.

## Decisions
1. **Append-only `event` table.** One row per claim / remit / acknowledgement / loaded row with
   the raw payload and `known_at`. A SQL Server trigger rejects UPDATE and DELETE. Normalized
   tables are rebuilt from events.
2. **Tenant-composite foreign keys.** Every table has `UNIQUE (tenant_id, id)`; every child
   references its parent by `(tenant_id, parent_id)`. A cross-tenant reference is impossible at the
   database level, not just in code.
3. **Idempotency keys in the schema.** `source_file(tenant_id, file_sha256)` and
   `event(tenant_id, source_file_id, isa13, gs06, st02, seq_in_file)` are unique.
4. **Scoped sessions.** Application code uses `tenant_session(engine, tenant_id)`: SELECTs are
   filtered by tenant automatically and INSERTs for another tenant are rejected.
5. **Patients are hashes.** `patient_ref.ref_hash` = salted SHA-256; the salt name lives on
   `tenant.patient_salt_key` and the salt itself in the environment / secret store.
6. **Portable models, T-SQL migration.** Tests run the models on SQLite; the Alembic migration
   targets SQL Server (type overrides: DATE, DATETIME2, NVARCHAR(MAX), SYSUTCDATETIME()).

## Consequences
- `source_file` and `event` rows are never edited; fixing data means loading a new file.
- Match links stay NULL until M3, which records `match_method` per link.
- `docs/data_model.md` is generated from the models and checked by a test.
