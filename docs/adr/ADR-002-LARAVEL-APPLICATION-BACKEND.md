# ADR-002: Laravel as Application Backend

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-11-15 |
| Deciders | Product owner / Technical lead |
| Version | 1.0 |
| Related | [ENG-03](../engineering/03_BACKEND_ARCHITECTURE.md) · [ARC-01](../architecture/01_SYSTEM_ARCHITECTURE.md) |

## Context

The application backend owns identity, tenants, authorization, onboarding, plans, journals, notifications, entitlements, audit and the public REST API. It must be productive for a solo developer and provide mature auth, queues, scheduling, validation and migrations out of the box.

## Decision

Use **Laravel (PHP 8.4)** as the application backend: Sanctum SPA cookie auth, Horizon on Redis for queues, the Laravel scheduler, Form Requests, Policies, Eloquent with PostgreSQL, Pest for tests. Laravel owns the single migration history for the shared database.

## Alternatives considered

| Alternative | Why not chosen |
|---|---|
| NestJS (TypeScript) | Shares language with the frontend, but requires assembling auth/queues/scheduling from libraries; less batteries-included. |
| Django | Strong admin and ORM, and would share Python with the engine; however coupling business logic to the quant codebase is undesirable, and the owner's preference/productivity favours Laravel. |
| FastAPI for everything | One language, but auth, sessions, admin tooling and migrations would need custom assembly; mixes business logic with the deterministic engine. |

## Consequences

+ Fast delivery of CRUD-heavy business features with first-class auth, queues and scheduling.
+ Clear separation from the quantitative engine.
− Three languages in the repo (TS, PHP, Python); CI and tooling per language.
− Shared database requires single-writer discipline (ARC-01 §6).

## Status

Accepted on 2026-11-15. Superseding requires a new ADR referencing this one.
