# ROADMAP — Milestone Progress

High-level progress tracker. The **detailed plan** (scope, files, tests, exit criteria, dependency graph, risks) is in **[docs/engineering/01_IMPLEMENTATION_ROADMAP.md](docs/engineering/01_IMPLEMENTATION_ROADMAP.md)** (ENG-01). This file must not duplicate that plan. Update the status and date columns when a milestone's acceptance criteria are **verified**.

Status: `NOT STARTED` · `IN PROGRESS` · `COMPLETED` · `BLOCKED` · `NEEDS REVIEW`. Target dates are not set yet (OQ-RD-01).

| M | Milestone | Objective | Depends on | Status | Completed |
|---|---|---|---|---|---|
| M0 | Repository and infrastructure foundation | Monorepo, Compose stack skeleton, GitHub repo config and CI gates | — | `COMPLETED` | 2026-11-15 |
| M1 | Database and API contracts | ARC-03 schema, seeders, OpenAPI and engine JSON Schemas | M0 | `IN PROGRESS` (ARC-03 §4–§7 migrated; §8, grants, seeders, contracts pending) | — |
| M2 | Zerodha integration and market data ingestion | Provider abstraction, DEMO + Kite providers, daily/backfill ingestion | M1 | `NOT STARTED` (verification blocked: OQ-INT-01/02) | — |
| M3 | Swing points and market structure | TRD-02 pivots and structure state | M1 (can run parallel to M2 on fixtures) | `NOT STARTED` | — |
| M4 | BOS, CHoCH, support/resistance and liquidity | TRD-02 breaks, TRD-03 zones, liquidity | M2, M3 | `NOT STARTED` | — |
| M5 | Setup detection and risk management | TRD-04 setups + PAQS, TRD-05 risk sizing, internal engine endpoints | M4 | `NOT STARTED` | — |
| M6 | Laravel APIs | ARC-04 `/api/v1` endpoints, tenancy, policies | M1, M5 | `NOT STARTED` | — |
| M7 | Frontend integration | HTTP adapter replaces mock; discrepancies D-01..D-24 | M6 | `NOT STARTED` | — |
| M8 | LLM explanations | ARC-07 explanation-only LLM with validator and fallback | M5, M7, OQ-AI-01 | `NOT STARTED` | — |
| M9 | Backtesting and paper trading | TRD-06, TRD-07; release gate G1 (personal MVP) | M5, M7 | `NOT STARTED` | — |
| M10 | Product validation and SaaS readiness | Parameter validation, staging/prod, RLS, 2FA, legal and licensing | M9 | `NOT STARTED` | — |

## Milestone acceptance (summary)

Full acceptance and exit criteria are in ENG-01 §3.

| M | Acceptance criteria |
|---|---|
| M0 | `docker compose up` healthy; CI green on PR; `main` protected; required check `ci-gate`. **Verified:** PRs #1–#11 ran through `ci-gate`, and the "Protect Main" ruleset is active. |
| M1 | Fresh DB migrates and seeds; OpenAPI validates; engine schema matches Laravel migrations. |
| M2 | DEMO + Kite candles ingested for NIFTY 500 with quality checks; adapter tests use recorded fixtures; token never logged. |
| M3 | TRD-02 test vectors and no-look-ahead tests pass. |
| M4 | TRD-02/03 break, zone and liquidity vectors pass. |
| M5 | Analysis runs contain setups with levels and evidence; risk endpoint matches TRD-05 examples; engine contract v1 frozen. |
| M6 | OpenAPI contract tests pass for all M6 endpoints; cross-tenant isolation matrix passes. |
| M7 | BAC-01 and BAC-03 pass end to end on DEMO data; no screen redesign. |
| M8 | US-12 passes; ≥ 90% validator pass rate on the eval set; spend cap verified. |
| M9 | BAC-04 and BAC-05 pass; gate G1 evaluated. |
| M10 | G2 conditions met; G3 workstreams owned and decisions recorded. |

## M0 notes

M0 included the GitHub repository configuration (ruleset, squash-only merges, secret scanning, Dependabot, CODEOWNERS, templates) and the GitHub Actions CI implementation. Deviations recorded in ENG-01 M0: backend and engine CI were pulled forward from M1; Trivy and Semgrep were deferred to image publishing; Actions are pinned by tag, not SHA.

## Open roadmap questions

- OQ-RD-01 — target dates per milestone.
- OQ-RD-02 — defer M8 (LLM) until after M9 to reach G1 sooner?
