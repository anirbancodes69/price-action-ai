---
name: quality-gate
description: Verification workflow for PriceAction AI before a task is called done or a PR is opened - choosing and running the right tests and linters per component (Vitest, ESLint, tsc, PHPUnit, Pint, pytest, ruff, mypy), migration up/down/re-migrate checks, Docker Compose build and health smoke, CI ci-gate and path filters, Conventional Commit PR titles with required scope, regression and test-gap review, and honest reporting of real results. Use when finishing an implementation, when asked to test/verify/validate, when CI fails, or before committing, pushing or opening a pull request.
---

# Quality gate

Proves a change works with real command output, and finds the tests a change is missing. Authority: [ENG-07](../../../docs/engineering/07_TESTING_STRATEGY.md) (test levels), [TRD-08](../../../docs/trading/08_TRADING_ENGINE_VALIDATION.md) (engine catalogue), [ENG-10](../../../docs/engineering/10_GITHUB_ACTIONS_CI_CD.md) (CI), [ENG-12](../../../docs/engineering/12_CODE_QUALITY_AND_PULL_REQUESTS.md) (PR quality), [ENG-08](../../../docs/engineering/08_DEVELOPMENT_ENVIRONMENT.md) (commands).

## Workflow

1. **Scope the change.** Run `git diff --name-only main...HEAD` plus `git status`. Map paths to components using [references/commands.md](references/commands.md).
2. **Gap review before running anything.** For each behaviour change, ask: which test would fail if this broke? If none, write it. Use the levels in ENG-07 §2:
   - Trading code needs TRD-08 vectors (`quant-engine` skill).
   - Schema changes need DB-rejection tests (`schema-and-contracts` skill).
   - Tenant-scoped endpoints need cross-tenant 404 tests (from M6).
   - Secrets need redaction tests.
3. **Run the component gates** from the commands reference: Docker first (`make …`). Use the CI-equivalent command if Docker is not running, and say so.
4. **Run the extra checks the change type demands:**
   - Migrations: fresh DB, up, full rollback, up again.
   - Compose, Dockerfiles or infra: `docker compose config`, build, `make up` and wait for health, `make health`.
   - CI files: path filters in `ci.yml` still route the change, and `ci-gate` still lists the job.
   - Docs: run the link check from the `docs-sync` skill.
5. **Regression sweep.** Run the full suite of every touched component, not only new tests. If shared contracts or schema changed, also run the consumers' suites.
6. **PR readiness:**
   - Branch name `feature|fix|chore|docs|refactor/…`.
   - Title `type(scope): summary`, where type is one of `feat fix docs chore refactor test ci build perf` and scope is one of `frontend backend engine contracts infra docs ruleset deps`. CI rejects a missing scope.
   - The PR template is complete.
   - No secrets in the diff.
   - Commit or push only when the user asks.

## Reporting rules

- Report the exact commands and real outcomes (pass/fail counts, the failing test names, an output excerpt). Never claim a pass for something not run. Say "not run" and why.
- Distinguish verified locally, verified in CI, and not verified.
- Failing tests are reported as failures, not explained away. Do not weaken or skip a test to get green. A skipped TRD-08 test blocks merge (TRD-08 §1).
- Record verified results in TASKS.md acceptance criteria only after they pass (CLAUDE.md §7).

## Known gaps (do not assume these exist)

- ENG-07 names Pest, Larastan and import-linter. The repo actually uses **PHPUnit 12**, and has neither Larastan nor import-linter yet.
- ENG-10 §2.2 describes a `docs-lint` job (markdown lint, link check). `ci.yml` has no such job yet; use the `docs-sync` script locally.
- `contracts/`, OpenAPI lint, schema-diff, Hypothesis and Playwright are planned (M1–M7), not present.

## Deliverables

A short verification report: commands run with results, tests added, checks not run with reasons, and remaining risks.
