# Code Quality and Pull Requests

| Field | Value |
|---|---|
| Document ID | ENG-12 |
| Version | 0.1.0 |
| Status | Specification ready |
| Owner | Technical Lead |
| Last updated | 2026-11-15 |
| Related | [ENG-10 §9–10](10_GITHUB_ACTIONS_CI_CD.md#9-pull-request-checks) · [ENG-11](11_BRANCHING_AND_RELEASE_STRATEGY.md) · [ENG-07](07_TESTING_STRATEGY.md) |

## 1. Code quality standards

| Component | Standards |
|---|---|
| Frontend | TypeScript strict; no `any` without comment; components follow existing layering (`app/` thin routes, `features/`, `components/`); colours only via tokens; labels via `lib/labels.ts`; formatting via `lib/format.ts`; ESLint clean |
| Laravel | PSR-12 via Pint; Larastan level 6 → raise to 8 by M10; Form Requests for validation; Policies for authorization; no cross-module model access |
| Python | Ruff lint + format; mypy strict for `domain/` and `schemas/`; pure domain (import-linter); `Decimal` for money; docstrings cite TRD sections |
| All | No secrets; no commented-out code; meaningful names; small PRs (< 400 changed lines excluding generated files where practical) |

## 2. PR title conventions

Conventional Commits (ENG-11 §3), validated in CI. Scope required. Max 72 characters.

## 3. Pull request template (proposed `.github/pull_request_template.md`)

```markdown
## Summary
<!-- What changes and why. Link the spec section(s) this implements, e.g. TRD-04 §3, ARC-04 T2. -->

Closes #<issue>  <!-- or: label `no-issue` + reason -->

## Type
- [ ] feat  - [ ] fix  - [ ] refactor  - [ ] docs  - [ ] chore/ci/build  - [ ] ruleset change

## Testing evidence
<!-- Commands run, new/updated tests, screenshots for UI, sample outputs for engine changes. -->

## Checklist
- [ ] Tests added/updated; CI green
- [ ] Documentation updated (authoritative doc in `docs/`; DOCUMENTATION_STATUS if status changed)
- [ ] Feature catalog status updated (PRD-06) if a feature changed state
- [ ] **Migrations:** none / reviewed (backward compatible with previous release, expand→contract, no long locks)
- [ ] **API compatibility:** none / additive only / breaking (requires /v2 + ADR)
- [ ] **Contracts regenerated** (OpenAPI / engine schemas) if changed
- [ ] **Ruleset:** golden outputs unchanged, or ruleset version bumped + CHANGELOG entry
- [ ] **Security:** no secrets; tokens/PII not logged; authz + tenant scoping on new endpoints; inputs validated
- [ ] **Constraints respected:** no order placement; demo never shown as live; no LLM in calculations; plans/trades kept separate; long-only actionability
- [ ] Data-mode / licensing impact considered (personal data not shared across tenants)
```

## 4. Review checklists

### 4.1 Migration review

Backward compatible with the currently deployed app; additive first; defaults for new NOT NULL columns or two-step backfill; `CONCURRENTLY` for large indexes; CHECK/FK constraints present per ARC-03; down migration exists for dev (not relied on in prod); seeding idempotent.

### 4.2 API compatibility review

Additive changes only within v1; enum additions documented as extensible; OpenAPI updated; contract tests updated; frontend mappers handle new fields; deprecations carry headers.

### 4.3 Security review (required for `risk:security` label, auth, integrations, infra)

AuthN/AuthZ on every route; tenant scope; 404 for foreign ids; rate limits; input validation; output whitelisting; redaction; secrets via env; third-party actions SHA-pinned; container runs as non-root (existing frontend image already uses a non-root `nextjs` user).

### 4.4 Trading engine review

Spec section referenced; boundary tests added; no look-ahead (accessor used); parameters from `RulesetParams`; golden diffs explained; ruleset bump if outputs change.

## 5. Definition of done

Code merged with green `ci-gate`; acceptance criteria of the linked requirement met; docs and feature catalog updated; deployed to staging (Phase 3+) without errors.
