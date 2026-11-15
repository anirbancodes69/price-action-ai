# CURRENT — Project State

Last verified: **2026-11-16** against the repository and GitHub (`main` at `e6f8a0e`; Claude Code skills on branch `chore/claude-code-skills`).

Status vocabulary: `NOT STARTED` · `IN PROGRESS` · `COMPLETED` · `BLOCKED` · `NEEDS REVIEW`.
Update this file at the end of every substantial task, based only on verified state.

## Phase and milestone

| Item | Value |
|---|---|
| Phase | Foundation complete; feature development not yet started |
| Last completed milestone | **M0** — repository, Docker and CI foundation (merged in PR #1, 2026-11-15) |
| Current milestone | **M1** — database and contracts: `IN PROGRESS` |
| Detailed plan | [ROADMAP.md](ROADMAP.md) → [ENG-01](docs/engineering/01_IMPLEMENTATION_ROADMAP.md) |

## Component status

| Area | Status | What actually exists |
|---|---|---|
| Frontend UI | `COMPLETED` (Phase 1, mock data) | Next.js 16.4.6, React 19, Tailwind v4, Lightweight Charts v5. Routes: auth (login/register/forgot-password), onboarding, dashboard, market-scanner, analysis, watchlists, trade-plans, portfolio, journal, backtesting, settings. Vitest unit tests for format, labels, auth validation and scanner filters. |
| Frontend data | **Mock only** | Every page reads the `DataSource` mock adapter (`frontend/src/lib/data`). Analysis overlays come from a demo heuristic (`src/mocks/demo-analysis.ts`), **not** the specified trading rules. Login accepts any well-formed email and password. There is no mutation client yet. |
| Frontend ↔ spec | `NEEDS REVIEW` | 24 known discrepancies (D-01..D-24) in [ENG-02 §9](docs/engineering/02_FRONTEND_ARCHITECTURE.md#9-discrepancy-register), to be resolved in M7. |
| Claude Code skills | `NEEDS REVIEW` | 8 project skills in `.claude/skills/` (price-action-domain, quant-engine, market-data, schema-and-contracts, frontend-ui, security-guardrails, quality-gate, docs-sync). They are workflows that link to the specs, plus two stdlib scripts (docs impact mapping, relative link and anchor check). Indexed in CLAUDE.md §10. No agents and no `.claude/settings.json`. |
| Documentation | `COMPLETED` (specification) | 58 spec files under `docs/` plus 12 accepted ADRs. They describe the target system, so most of it is **not implemented**. |
| Backend (Laravel 13) | `IN PROGRESS` | `GET /api/health`, log redaction, PHPUnit tests. **Schema (M1), merged:** ARC-03 §4–§5 (12 identity and trading-configuration tables, PR #13), §6 market data (9 tables + `trading_preferences.universe_id` FK, PR #14) and §7 analysis (ruleset versions, candle snapshots, analysis batches/runs, swing points, structure events, price zones, liquidity events, detected setups, AI explanations) with immutability triggers (PR #15). 41 backend tests incl. 36 database-constraint tests. **Not yet:** ARC-03 §8 trading tables, per-table role grants, seeders, domain modules, `/api/v1` endpoints. |
| Python engine | `IN PROGRESS` (skeleton only) | FastAPI `/health` and authenticated `/internal/v1/ping`, arq worker settings, structured logging, pytest. `app/domain/` is empty. **No trading logic, providers or ingestion.** |
| Contracts (`contracts/`) | `NOT STARTED` | Directory does not exist (planned for M1). |
| Infrastructure | `COMPLETED` (local dev) | Docker Compose with frontend, backend (php-fpm + nginx), queue worker, scheduler, engine, engine worker, PostgreSQL 17 and Redis 7.4, all with health checks. Dev overlay with hot reload. Makefile. `scripts/setup-env.sh`. No staging or production environments. |
| GitHub CI | `COMPLETED` (M0 gates) | `ci.yml` coordinator with path filters, semantic PR titles and the `ci-gate` job. Component workflows: frontend (lint, typecheck, test, build), backend (pint, migrate, phpunit), python-engine (ruff, mypy, pytest), docker-build (build + Compose smoke), security-scan (gitleaks, dependency audits). |
| GitHub settings | `COMPLETED` | "Protect Main" ruleset (PR required, `ci-gate` required and strict, linear history, no force-push or deletion, threads resolved); squash-only merges; auto-delete branches; secret scanning + push protection; Dependabot security updates; CodeQL runs on `main`. |
| CD / deployment | `NOT STARTED` | Phases 2–4 of [ENG-10 §11](docs/engineering/10_GITHUB_ACTIONS_CI_CD.md#11-environments-and-deployment-evolution). |

## Completed milestones

| Milestone | Date | Evidence |
|---|---|---|
| Phase 1 frontend + Phase 2 documentation imported | 2026-11-15 | commit `427de44` |
| M0 — repository, Docker, CI foundation | 2026-11-15 | PR #1 (`43c37bd`, `4103ee7`) |

## Work in progress

- Branch `chore/claude-code-skills`: **T-002** (project Claude Code skills). Structure, frontmatter and link checks verified locally; not yet committed or merged.
- Local dev databases created before PR #13 must be recreated (`make reset`), because the stock Laravel `users` migration was replaced (UUID ids, no `name`, no sessions table).

## Immediate next task

**T-101d — ARC-03 §8 trading-table migrations and per-table writer grants** (then T-102, T-103, T-104, T-105) — see [TASKS.md](TASKS.md). An owner decision on OQ-RM-04 helps the seed data but does not block it.

## Known blockers

| Blocks | Item |
|---|---|
| M2 | OQ-INT-01/02 — Kite Connect limits, token expiry, price adjustment and terms not verified. OQ-SEC-01 — Kite app model. Kite developer app needed. |
| M8 | OQ-AI-01 — LLM provider/model not chosen. |
| M9–M10 | OQ-BT-01/03 — point-in-time NIFTY 500 membership and corporate-action data sources. |

## Pending decisions and inconsistencies

| Item | Detail |
|---|---|
| Repo visibility | [ENG-09 §6](docs/engineering/09_GITHUB_REPOSITORY_STRATEGY.md#6-repository-settings) specifies **Private**; the GitHub repository is currently **public**. Owner to decide; then align the doc or the setting. |
| Ruleset merge methods | The ruleset allows merge/squash/rebase, but repo settings disable merge commits and linear history is required. Effective behaviour is squash or rebase. ENG-09 says squash only. Low impact. |
| Action pinning | Third-party Actions are pinned by major tag, not commit SHA (ENG-09 §6 asks for SHA). Known follow-up from M0. |
| Risk defaults | OQ-RM-04 — UI (6 positions / 2% heat) vs onboarding (5) vs spec (5 / 5% / 25%). |
| Test tooling vs ENG-07 | ENG-07 §2 names Pest, Larastan and import-linter. The backend actually uses PHPUnit 12, and none of the three tools exists yet. Owner to decide: align ENG-07 to PHPUnit, or adopt Pest. |
| Docs CI | ENG-10 §2.2 describes a `docs-lint` job (markdown lint, link check). `ci.yml` has none. A local link checker now exists (`.claude/skills/docs-sync/scripts/check_links.py`) and could back that job. |
| Priority open questions | [DOCUMENTATION_STATUS §3](docs/DOCUMENTATION_STATUS.md#3-priority-open-questions-block-upcoming-milestones); 61 total in §2. |
