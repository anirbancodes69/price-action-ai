# Testing Strategy

| Field | Value |
|---|---|
| Document ID | ENG-07 |
| Version | 0.1.0 |
| Status | Specification ready (no tests exist today) |
| Owner | Technical Lead / QA |
| Last updated | 2026-11-15 |
| Related | [TRD-08 Trading validation](../trading/08_TRADING_ENGINE_VALIDATION.md) · [ENG-10 CI/CD](10_GITHUB_ACTIONS_CI_CD.md) · [ENG-12 Code quality](12_CODE_QUALITY_AND_PULL_REQUESTS.md) |

## 1. Purpose

Defines test levels, tooling, ownership and CI mapping for each component. The trading engine catalogue is owned by TRD-08 and is not repeated here.

## 2. Test pyramid by component

| Level | Frontend | Laravel | Python engine |
|---|---|---|---|
| Static | ESLint, `tsc --noEmit` | Pint, Larastan | Ruff (lint+format), mypy, import-linter |
| Unit | Vitest: formatters, labels, mappers, validators, filters | Pest unit: services with fakes | pytest: domain, risk, execution, validator |
| Property-based | — | — | Hypothesis: rounding, no look-ahead, determinism |
| Golden | — | — | Analysis outputs per fixture (TRD-08 TV-R3) |
| Integration | — | Pest feature tests on PostgreSQL + Redis containers | DB repositories, workers with Postgres + Redis |
| Contract | Types generated from OpenAPI compile | Responses validated against `contracts/api/openapi.yaml`; engine DTOs vs `contracts/engine` | Exported schemas up to date; FastAPI responses validate |
| Architecture | — | Module boundary rules (Pest arch) | import-linter (domain purity) |
| Security | Dependency audit | Dependency audit, tenant isolation matrix | Dependency audit, redaction tests |
| E2E | Playwright smoke on Compose stack (M7+) | (via E2E) | (via E2E) |

## 3. Critical test suites

| Suite | Purpose | Required from |
|---|---|---|
| Trading catalogue (TV-*) | Rule correctness, no look-ahead | M3 |
| Tenant isolation matrix | Every tenant-scoped endpoint returns 404 cross-tenant | M6 |
| Token custody | Token never in API responses/logs/job payloads | M2 |
| Data-mode honesty | DEMO responses always flagged (TV-DM-01) | M6 |
| Plan integrity | Client qty ignored; server values stored (TV-API-01) | M6 |
| LLM validator | Ungrounded numbers rejected (TV-LLM-01) | M8 |
| Migrations | Up on empty DB; up from previous release schema | M1 |
| Determinism monitor | Nightly re-run sample hash equality | M4 |

## 4. Test data

- Hand-built CSV candle fixtures for trading rules; demo generator for UI/dev; **no real provider data committed** (licensing).
- Laravel factories for all models; a `DemoSeeder` mirrors frontend mocks for E2E.
- Recorded HTTP fixtures for Kite with tokens scrubbed.

## 5. Coverage and quality targets

No arbitrary global coverage threshold. Initial targets:

| Area | Target |
|---|---|
| `python-engine/app/domain/` | 100% of TRD-08 catalogue implemented; line coverage reported, aim ≥ 90% (not gating initially) |
| Laravel services for trading/risk/integrations | Every public method has at least one feature or unit test |
| Frontend | Mappers and validators unit-tested; E2E smoke for the 4 main journeys |

Improvement strategy: report coverage in CI from M3; after two milestones of stable numbers, gate on "no decrease" for `domain/` rather than a fixed number.

## 6. Environments for tests

CI uses GitHub-hosted runners with PostgreSQL and Redis **service containers** (same major versions as production). Local runs via `docker compose run --rm <service> <test command>` ([ENG-08](08_DEVELOPMENT_ENVIRONMENT.md)). SQLite is not used for Laravel tests.

## 7. Manual testing

Before release gate G1: exploratory session per journey (PRD-04), visual check of chart annotations against engine outputs for 10 instruments, verification that no screen offers order placement (BAC-06), devtools check for tokens (BAC-07).
