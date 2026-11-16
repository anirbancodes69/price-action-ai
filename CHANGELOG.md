# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). The project will use [Semantic Versioning](https://semver.org/) from the first release (`v0.x.y`, [ENG-11 §5](docs/engineering/11_BRANCHING_AND_RELEASE_STRATEGY.md#5-versioning)). Release automation (release-please) may take over maintaining this file later (ENG-11 §6). Trading ruleset changes will also be recorded in `python-engine/rulesets/CHANGELOG.md`.

No release has been tagged yet. The entries below come from the merged git history.

## [Unreleased]

### Added

- Project design standards adopted for the whole frontend (`docs/design-standards.md`, ADR-013): OKLCH token system with PriceAction brand values; light, dark and system themes (dark default); shared components `PageFrame`/`PageHeader`, `Panel`/`Card`/`RowList`, `Stat`/`Eyebrow`/`StatGrid`, `FilterRow`/`ClearButton`, `ChoiceGroup`/`PillTabs`, `SectionLinks`, `Empty`, `ErrorState`, shaped skeletons and `lib/colors.ts`; route error boundary for the authenticated app; every screen refactored (one primary action, filters on the page, one stat row, panels capped at five rows on the dashboard). Chart annotations use dedicated tokens, with distinct line styles for entry, stop and target, and dashed "(ref)" levels for reference-only setups. WCAG 2.1 AA contrast verified for all token pairs.
- Database migrations for ARC-03 §8 trading (watchlists, trade plans with long-only and stop < entry < target checks, paper accounts/trades/events, actual trades and fills, journal entries, backtest runs and trades, notifications) and single-writer role grants (`apply_role_grants()`: per-table ownership, column-level shared writes, write-once `candle_snapshots`, append-only `audit_logs`, new tables closed by default), with database-level tests (M1, in progress).
- Project Claude Code skills in `.claude/skills/`: `price-action-domain`, `quant-engine`, `market-data`, `schema-and-contracts`, `frontend-ui`, `security-guardrails`, `quality-gate`, `docs-sync`. They are workflows and checklists that point to the authoritative specs. `docs-sync` includes a relative Markdown link and anchor checker and a changed-files → docs-to-review script. Indexed in `CLAUDE.md` §10.
- Database migrations for ARC-03 §7 analysis (ruleset versions, immutable candle snapshots, analysis batches and runs, swing points, structure events, price zones, liquidity events, detected setups, AI explanations), with triggers that make snapshots, runs, children and setups immutable and freeze rulesets once active, plus database-level tests (M1, in progress).
- Database migrations for ARC-03 §6 market data (instruments, instrument provider refs, effective-dated instrument snapshots, universes and point-in-time memberships, raw daily candles with OHLC checks, corporate actions, ingestion runs with a duplicate-run guard, data-quality issues, market calendar) and the `trading_preferences.universe_id` foreign key, with database-level constraint tests (M1, in progress).
- Database migrations for ARC-03 §4–§5 (tenants, users, tenant memberships, user profiles, onboarding progress, audit log, trading preferences, risk profiles, subscription entitlements, provider connections, data sources, data source selections) with CHECK and EXCLUDE constraints, insert-only `audit_logs` for runtime roles, and database-level constraint tests (M1, in progress).
- Project-control documents: `CLAUDE.md`, `CURRENT.md`, `ROADMAP.md`, `DECISIONS.md`, `TASKS.md`, `CHANGELOG.md`, `CONTRIBUTING.md`.
- M0 foundation (PR #1): Docker Compose stack (Next.js frontend, Laravel 13 php-fpm + nginx, queue worker, scheduler, FastAPI engine, arq worker, PostgreSQL 17 with per-service roles, Redis 7.4) with health checks and a hot-reload dev overlay; Makefile and `scripts/setup-env.sh`.
- Laravel skeleton with `/api/health` (shallow and deep), JSON logging with secret redaction, PHPUnit tests.
- FastAPI engine skeleton with `/health`, `/ready` and token-protected `/internal/v1/ping`; arq heartbeat worker; ruff, strict mypy and pytest.
- Frontend Vitest unit tests and `typecheck` script.
- GitHub Actions: `ci.yml` coordinator with path filters, semantic PR titles and a single required `ci-gate`; frontend, backend, python-engine, docker-build and security-scan workflows; PR and issue templates; CODEOWNERS; Dependabot.
- Phase 1 frontend (mock data only) and Phase 2 specification set under `docs/` with ADR-001..012 (initial import).

### Changed

- Frontend status tones: lifecycle states use `success/warning/destructive/info/neutral` instead of the brand accent and market colours; `MetricCard`, `EmptyState`, `Segmented` and `PageContainer` replaced by the standard components. Fixed a chart race where the initial visible range could apply before candles loaded.
- `users` migration replaced the stock Laravel one: UUID primary key, `citext` email, status and soft delete; no `name` (moved to `user_profiles.display_name`) and no sessions table (Redis). Local dev databases need `make reset`.
- `make test-backend` now runs against a dedicated `priceaction_test` database using the schema-owner role, so migration and constraint tests can run.
- Frontend runtime aligned with Node 26 (Docker image, CI, `@types/node`) (PR #3, #11).
- Dependency updates: ESLint 10, frontend minor/patch group, GitHub Actions group (PR #5, #6, #7).
- Pinned PHP, Python, TypeScript and `@types/node` major versions in Dependabot to match the documented runtimes (PR #10).

### Fixed

- Frontend typecheck generates Next.js route types first (PR #1).
- Frontend lockfile regenerated on Linux for CI compatibility.

### Security

- Secret scanning (gitleaks) and dependency audits in CI; GitHub secret scanning with push protection enabled; `.env` files gitignored, with placeholder-only `.env.example` templates.
- Log redaction of credentials and tokens in the backend.
