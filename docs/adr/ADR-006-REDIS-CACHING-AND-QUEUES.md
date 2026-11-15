# ADR-006: Redis for Caching, Queues, Sessions and Rate Limiting

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-11-15 |
| Deciders | Product owner / Technical lead |
| Version | 1.0 |
| Related | [ARC-01 §7](../architecture/01_SYSTEM_ARCHITECTURE.md#7-communication-patterns) · [OPS-04 §2](../operations/04_DATA_RETENTION_AND_BACKUP.md#2-backups) |

## Context

Laravel needs queues, sessions and rate-limit counters; the Python engine needs a job queue; scanner results benefit from caching. A broker like Kafka/RabbitMQ is not justified at this scale.

## Decision

Use **Redis** (7.4, or Valkey as a drop-in) for: Laravel Horizon queues, sessions, cache, rate limiting, arq job queues, job status (TTL) and per-source provider rate limiters. Redis holds **no data of record**; everything is reconstructable. AOF `everysec` persistence for queue durability across restarts.

## Alternatives considered

| Alternative | Why not chosen |
|---|---|
| RabbitMQ | Robust messaging, but an extra service and no cache/session role. |
| Database-backed queues | Fewer moving parts, but adds load/locking to PostgreSQL and is weaker for cross-language workers. |
| Kafka | Event streaming not needed; heavy operational cost. |

## Consequences

+ One fast, simple dependency covering several needs; native support in Laravel and arq.
− Laravel and arq use different job formats → cross-language jobs go through the engine API (`POST /internal/v1/jobs`), never by writing the other side's queue format.
− Redis licensing changed across versions; confirm the chosen distribution's licence at M0.

## Status

Accepted on 2026-11-15. Superseding requires a new ADR referencing this one.
