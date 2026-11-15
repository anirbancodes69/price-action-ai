# Migration checklist (as practised in this repo)

Patterns to copy, taken from the merged migrations. Re-check the files themselves before relying on this list.

| Item | Where to look |
|---|---|
| Raw SQL migration structure, up and down | `backend/database/migrations/2026_11_16_000003_create_market_data_tables.php` |
| Immutability triggers, deferrable FK, guarded role grants | `backend/database/migrations/2026_11_16_000004_create_analysis_tables.php` |
| "Database must reject" helper | `backend/tests/Feature/Database/AssertsDatabaseRejects.php` |
| Constraint test style (one test per rule, positive insert first) | `backend/tests/Feature/Database/AnalysisSchemaTest.php` |

## Before opening the PR

- [ ] Table, column, enum and constraint names match ARC-03 conventions and TRD-01 §7 vocabulary.
- [ ] Every tenant-owned table has `tenant_id uuid NOT NULL` FK and an index leading with `tenant_id`.
- [ ] FKs are `RESTRICT` unless ARC-03 says `CASCADE`.
- [ ] Money is `numeric(14,2)`, prices `numeric(12,2)`, percentages `numeric(6,3)`, ratios `numeric(8,4)` (ARC-03 §2).
- [ ] Grants follow ARC-01 §6 writers and ARC-06 §6 roles. They are guarded when roles are absent (CI).
- [ ] A rejection test exists for each constraint, and each was mutation-checked once.
- [ ] Fresh DB: all migrations up, all down, all up again. Clean.
- [ ] `make test-backend` and `make lint-backend` pass. Record the test count in TASKS.md.
- [ ] ARC-03 §2.1 lists every deviation or addition versus the spec text.
- [ ] Local dev DB note in CURRENT.md if developers must run `make reset`.

## Commands

```bash
make dev            # stack up (postgres needed)
make test-backend   # creates priceaction_test, migrates as app_migrator, runs PHPUnit
make lint-backend   # Pint --test
make migrate        # apply to the dev DB as the schema-owner role
```
