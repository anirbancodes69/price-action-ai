# ADR-004: Modular Monolith with One Separate Quant Service

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-11-15 |
| Deciders | Product owner / Technical lead |
| Version | 1.0 |
| Related | [ARC-01](../architecture/01_SYSTEM_ARCHITECTURE.md) · [ADR-002](ADR-002-LARAVEL-APPLICATION-BACKEND.md) · [ADR-003](ADR-003-PYTHON-QUANTITATIVE-ENGINE.md) |

## Context

The team is one developer; the domain has clear sub-areas (identity, trading, journal, analysis read models) but low independent-scaling needs. Operational overhead must stay minimal while preserving the option to extract services later.

## Decision

Build a **modular monolith** in Laravel with enforced module boundaries (ARC-01 §5), plus **one** separate Python service (engine API + workers) justified by a genuine capability boundary. Communication is HTTP (sync, internal) and Redis queues (async). No Kafka, Kubernetes, service mesh or per-domain microservices.

## Alternatives considered

| Alternative | Why not chosen |
|---|---|
| Microservices per domain | Independent deploys and scaling, but high cost in infrastructure, observability, contracts and data consistency for a solo developer. |
| Single monolith including quant code | Lowest overhead, but mixes CPU-heavy deterministic code with web serving and loses the Python ecosystem. |
| Serverless functions | Cold starts, execution limits for backtests, vendor lock-in. |

## Consequences

+ One business deployable, one database, simple local development (Docker Compose).
+ Module boundaries enforced by architecture tests enable later extraction.
− Shared database couples Laravel and engine schemas; mitigated by single-writer rule, DB roles and schema-diff tests.
− Scaling is vertical first; acceptable for the personal phase.

## Status

Accepted on 2026-11-15. Superseding requires a new ADR referencing this one.
