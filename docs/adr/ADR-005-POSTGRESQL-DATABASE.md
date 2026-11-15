# ADR-005: PostgreSQL as Primary Database

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-11-15 |
| Deciders | Product owner / Technical lead |
| Version | 1.0 |
| Related | [ARC-03](../architecture/03_DATABASE_DESIGN.md) · [OPS-04](../operations/04_DATA_RETENTION_AND_BACKUP.md) |

## Context

The system needs relational integrity for trading records, effective-dated reference data (universe membership, instrument attributes), JSONB for engine outputs, arrays, exclusion constraints and reliable backups/PITR.

## Decision

Use **PostgreSQL** (17, or 18 if tooling supports it at M0) as the single system of record, with extensions `citext`, `btree_gist`, `pgcrypto`. Domain invariants are duplicated as CHECK constraints. No separate time-series database initially; candles live in a plain indexed table (partition later if needed).

## Alternatives considered

| Alternative | Why not chosen |
|---|---|
| MySQL/MariaDB | Laravel-native, but weaker support for exclusion constraints, arrays, partial indexes and JSONB operators used in the schema. |
| TimescaleDB / ClickHouse for candles | Better for large time series; unnecessary at ~millions of daily rows; adds operational weight. Revisit if intraday data is introduced. |
| MongoDB | Loses relational integrity needed for plans/trades/journal. |

## Consequences

+ Strong integrity (FK, CHECK, EXCLUDE), effective dating, JSONB, mature backup tooling; supported by Laravel and SQLAlchemy.
− Must manage roles carefully because two services share the database.

## Status

Accepted on 2026-11-15. Superseding requires a new ADR referencing this one.
