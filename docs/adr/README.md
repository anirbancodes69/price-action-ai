# Architecture Decision Records

| Field | Value |
|---|---|
| Version | 1.2 |
| Status | Current |
| Owner | Solution Architect |
| Last updated | 2026-11-17 |

## Purpose

ADRs record significant, hard-to-reverse decisions with their context and trade-offs. Specifications elsewhere in `docs/` must not contradict an accepted ADR; if they need to, write a new ADR that supersedes the old one.

## Format

Each ADR has: Status, Date, Context, Decision, Alternatives considered, Consequences, Related documents. File name `ADR-NNN-SHORT-TITLE.md`. Statuses: `Proposed`, `Accepted`, `Superseded by ADR-NNN`, `Deprecated`.

## Index

| ADR | Title | Status | Date |
|---|---|---|---|
| [ADR-001](ADR-001-FRONTEND-ARCHITECTURE.md) | Next.js App Router Frontend | Accepted | 2026-11-15 |
| [ADR-002](ADR-002-LARAVEL-APPLICATION-BACKEND.md) | Laravel as Application Backend | Accepted | 2026-11-15 |
| [ADR-003](ADR-003-PYTHON-QUANTITATIVE-ENGINE.md) | Python as Quantitative Engine | Accepted | 2026-11-15 |
| [ADR-004](ADR-004-MODULAR-MONOLITH.md) | Modular Monolith with One Separate Quant Service | Accepted | 2026-11-15 |
| [ADR-005](ADR-005-POSTGRESQL-DATABASE.md) | PostgreSQL as Primary Database | Accepted | 2026-11-15 |
| [ADR-006](ADR-006-REDIS-CACHING-AND-QUEUES.md) | Redis for Caching, Queues, Sessions and Rate Limiting | Accepted | 2026-11-15 |
| [ADR-007](ADR-007-MARKET-DATA-PROVIDER-ABSTRACTION.md) | Market Data Provider Abstraction | Accepted | 2026-11-15 |
| [ADR-008](ADR-008-DETERMINISTIC-TRADING-ENGINE.md) | Deterministic, Versioned Trading Calculations | Accepted | 2026-11-15 |
| [ADR-009](ADR-009-LLM-EXPLANATION-ONLY.md) | LLM Restricted to Explanation | Accepted | 2026-11-15 |
| [ADR-010](ADR-010-MANUAL-TRADE-EXECUTION-MVP.md) | Manual Trade Execution in MVP | Accepted | 2026-11-15 |
| [ADR-011](ADR-011-DATA-MODES-AND-TENANT-ISOLATION.md) | Demo, Personal and Licensed Data Modes with Tenant Isolation | Accepted | 2026-11-15 |
| [ADR-012](ADR-012-GITHUB-ACTIONS-CI-CD.md) | GitHub Actions for CI/CD | Accepted | 2026-11-15 |
| [ADR-013](ADR-013-DESIGN-STANDARDS.md) | Adopt the Project Design Standards | Accepted | 2026-11-16 |
| [ADR-014](ADR-014-PERSONAL-INTRADAY-WORKSTATION.md) | Personal Intraday Price-Action Workstation | Accepted | 2026-11-17 |
| [ADR-015](ADR-015-INTRADAY-TIME-AND-SNAPSHOT-MODEL.md) | Intraday Time Model and Snapshots by Reference | Accepted | 2026-11-17 |
| [ADR-016](ADR-016-LIVE-ENGINE-PROXY-FOR-SCANNER-AND-ANALYSIS.md) | Live Engine Proxy for the Scanner and Analysis (Personal Mode) | Accepted | 2026-11-18 |
| [ADR-017](ADR-017-TRADE-PLANS-WITHOUT-STORED-ANALYSIS-RUNS.md) | Trade Plans Without Stored Analysis Runs (Personal Mode) | Accepted | 2026-11-19 |
| [ADR-018](ADR-018-INDEPENDENT-STRATEGY-LIBRARY.md) | Independent Strategy Library, Developed and Validated One Strategy at a Time | Accepted | 2026-11-21 |
| [ADR-019](ADR-019-DAILY-TIMEFRAME-RESEARCH-TRACK.md) | Daily-Timeframe Research Track (Longer Holding Period) | **Proposed** | 2026-11-23 |

## Candidate future ADRs

| Topic | Trigger |
|---|---|
| LLM provider selection | OQ-AI-01 resolved |
| Licensed market-data vendor | Before G3 |
| PostgreSQL RLS adoption | M10 |
| Edge proxy and hosting provider | M10 (OQ-OPS-01) |
| First real market-data provider: Groww vs Kite (or both) | OQ-INT-04 resolved (T-203) |
| Kite app model (platform app vs bring-your-own key) | OQ-SEC-01 resolved |
