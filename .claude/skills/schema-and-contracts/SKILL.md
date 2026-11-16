---
name: schema-and-contracts
description: Workflow for PriceAction AI database schema and API contract changes - Laravel migrations in backend/database/migrations (raw SQL, CHECK constraints, immutability triggers, per-table role grants, single-writer ownership), PostgreSQL constraint tests, seeders, the engine's SQLAlchemy read model and schema-diff, the /api/v1 contract in ARC-04 and contracts/api/openapi.yaml, and engine JSON Schemas in contracts/engine. Use when adding or changing a table, column, constraint, index, grant, seeder, endpoint, request/response shape, enum or error code.
---

# Schema and contracts

Schema and contract changes are the highest-regression-risk changes in this repo: three runtimes share one database and one API. ARC-03 is the schema authority, ARC-04 is the API authority, and from M1 `contracts/` is the machine-readable source (ENG-12 §4 asks reviewers to take particular care).

> Current state: ARC-03 §4–§8 are migrated with role grants and PHPUnit constraint tests in `backend/tests/Feature/Database/`; seeders exist (T-102). `contracts/api/openapi.yaml` (T-103: 88 operations, Redocly lint plus an ARC-04 coverage check in `contracts-ci.yml`) and `contracts/engine/*.json` (T-104: 13 JSON Schemas exported from `python-engine/app/schemas`, stale-export check in `python-engine-ci.yml`) exist. The engine's SQLAlchemy read model is `python-engine/app/db/tables.py`, guarded by a schema-diff test against the migrated database. There are no `/api/v1` endpoints yet.

## Required context

1. CURRENT.md, TASKS.md (the task's acceptance criteria) and the M1 or M6 section of ENG-01.
2. **Schema:** [ARC-03](../../../docs/architecture/03_DATABASE_DESIGN.md) §2 conventions, **§2.1 "as migrated" notes**, the section for your tables, §9 tenant isolation, §12 migration strategy, §13 integrity. Writers are in [ARC-01 §6](../../../docs/architecture/01_SYSTEM_ARCHITECTURE.md#6-data-ownership-writers). Roles are in [ARC-06 §6](../../../docs/architecture/06_SECURITY_ARCHITECTURE.md#6-encryption-and-database-privileges).
3. **API:** [ARC-04](../../../docs/architecture/04_API_SPECIFICATION.md) §2 conventions (envelopes, errors, pagination, idempotency), §3 shared schemas, the endpoint section, and the §15 authorization matrix. The internal engine API is in [ARC-08 §5](../../../docs/architecture/08_INTEGRATION_ARCHITECTURE.md#5-internal-engine-api-laravel--engine).
4. An existing migration and test as the pattern. See [references/migration-checklist.md](references/migration-checklist.md).

## Workflow (schema)

1. Write the migration as **raw SQL** in a new, date-prefixed file. Never edit a merged migration.
2. Encode domain invariants as constraints (enum `CHECK`s from TRD-01 §7, `stop < entry < target` for LONG, OHLC validity, `tenant_id` NOT NULL with a leading index), following ARC-03 naming (`ix_`, `uq_`).
3. Enforce immutability with triggers where ARC-03 requires it, and grants per writer (ARC-01 §6). Use guarded `DO` blocks when roles may not exist (CI has no app roles).
4. Write a constraint test per rule: each invalid statement must be **rejected by the database** (`AssertsDatabaseRejects`), plus a positive insert. Prove each test catches its bug by breaking the constraint once.
5. Verify a full rollback and re-migrate of **all** migrations on a fresh DB, then run `make test-backend` and Pint.
6. Record every deviation from the ARC-03 text in **ARC-03 §2.1**. If the engine reads the table, update the SQLAlchemy read model and schema-diff test (T-104, once it exists).

## Workflow (API and contracts)

1. Change ARC-04 first (or together with the change): endpoint, schema, error codes, authorization row.
2. From T-103 onward, update `contracts/api/openapi.yaml` in the same PR and keep it lint-clean. Engine contracts are Pydantic models exported to `contracts/engine/`, and CI fails on stale exports (ENG-04 §8).
3. Tenant-scoped endpoints return 404 for foreign IDs and need a cross-tenant test (ARC-06 §4). Server-side values (quantity, levels) are never taken from the client (TV-API-01).
4. Breaking changes need a new API version or an expand → contract sequence. Note consumers (frontend `DataSource` mappers, Laravel engine client).

## Hard rules

- One writer per table, except the documented ARC-01 §6 exceptions. Laravel migrations own all DDL; the engine never migrates.
- Migrations are forward-only in production and backward compatible with the previous release (ARC-03 §12).
- Proposed plans, paper trades and actual trades stay in separate tables (C-11). Analysis rows reference an immutable snapshot and ruleset version (C-08).
- No secrets in seeders. Demo data is flagged DEMO.
- Never place trading logic in SQL or PHP beyond integrity constraints that duplicate engine invariants.

## Deliverables

- The migration or contract, tests with real output, and the rollback/re-migrate result.
- Doc updates: ARC-03 (§2.1 included), ARC-04, ARC-05 if a data flow changed, ENG-03, and ENG-02 §8 if frontend data needs changed. Then the `docs-sync` skill.
