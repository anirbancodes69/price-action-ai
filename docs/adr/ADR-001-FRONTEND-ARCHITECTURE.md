# ADR-001: Next.js App Router Frontend

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-11-15 |
| Deciders | Product owner / Technical lead |
| Version | 1.0 |
| Related | [ENG-02](../engineering/02_FRONTEND_ARCHITECTURE.md) · [PRD-07](../product/07_UI_UX_SPECIFICATION.md) · [ARC-02](../architecture/02_TECHNOLOGY_STACK.md) |

## Context

The product needs a data-dense trading UI with charts, server-rendered pages for fast first load, and a clean boundary to a separate backend. A Phase 1 frontend already exists: Next.js 16 (App Router, Cache Components, standalone output), React 19, TypeScript strict, Tailwind CSS v4, TradingView Lightweight Charts v5, with all data behind a `DataSource` interface and a mock adapter.

## Decision

Keep **Next.js (App Router) + React + TypeScript + Tailwind CSS + Lightweight Charts** as the frontend. Pages remain thin server components calling the `DataSource` adapter; the frontend never talks to the engine, Kite or the database directly; it consumes only `/api/v1` (proxied same-origin to Laravel). No UI component library is introduced; the custom token-based design system stays.

## Alternatives considered

| Alternative | Why not chosen |
|---|---|
| Vite + React SPA | Simpler build, but loses SSR/streaming and server-side cookie forwarding; the existing code would need rework. |
| Remix / React Router framework | Comparable capabilities; no benefit over the already-built Next.js app. |
| Laravel Blade/Inertia | Would merge frontend into the backend deployable; loses the existing React investment and the explicit API boundary needed for SaaS clients. |

## Consequences

+ Existing work is preserved; SSR improves perceived performance; the `DataSource` seam makes backend integration a contained change (ENG-02 §5).
− Next.js 16 conventions change quickly (frontend/AGENTS.md warns of breaking changes); upgrades need care.
− Two runtimes (Node + PHP) in production.

## Status

Accepted on 2026-11-15. Superseding requires a new ADR referencing this one.
