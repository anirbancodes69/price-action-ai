# Branching and Release Strategy

| Field | Value |
|---|---|
| Document ID | ENG-11 |
| Version | 0.1.0 |
| Status | Specification ready |
| Owner | Technical Lead |
| Last updated | 2026-11-15 |
| Related | [ENG-09](09_GITHUB_REPOSITORY_STRATEGY.md) · [ENG-10](10_GITHUB_ACTIONS_CI_CD.md) · [ENG-12](12_CODE_QUALITY_AND_PULL_REQUESTS.md) · [OPS-01](../operations/01_DEPLOYMENT_GUIDE.md) |

## 1. Model: GitHub Flow

`main` is always releasable; all work happens on short-lived branches merged via PR. GitFlow is not used: a solo developer with continuous delivery to staging gains nothing from `develop`/`release` branches, and long-lived branches increase merge risk for shared contracts.

## 2. Branches

| Branch | Purpose | Naming | Lifetime |
|---|---|---|---|
| `main` | Integrated, releasable code | — | permanent, protected |
| Feature | New functionality | `feature/<area>-<short-desc>` e.g. `feature/engine-pivots` | < 1 week preferred |
| Bugfix | Non-urgent fixes | `fix/<area>-<short-desc>` | short |
| Chore | Tooling, deps, CI | `chore/<desc>` | short |
| Docs | Documentation only | `docs/<desc>` | short |
| Refactor | No behaviour change | `refactor/<desc>` | short |
| Hotfix | Urgent production fix | `fix/hotfix-<desc>` from the production tag if `main` has unreleased changes | hours |

## 3. Commits: Conventional Commits

Format `type(scope): summary` — types `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `ci`, `build`, `perf`; scopes `frontend`, `backend`, `engine`, `contracts`, `infra`, `docs`, `ruleset`. Breaking changes: `!` after type or `BREAKING CHANGE:` footer. Because merges are squash-only, the **PR title** becomes the commit message and is validated in CI.

Examples: `feat(engine): detect confirmed swing pivots (TRD-02 §3)`, `fix(backend): reject client-supplied plan quantity`, `docs(trading): clarify zone break buffer ownership`.

## 4. Pull request lifecycle

1. Open a draft PR early; CI runs.
2. Complete the PR template (ENG-12 §3).
3. Self-review the diff (solo) — checklist includes migrations, API compatibility, security, docs.
4. All required checks green, conversations resolved → mark ready → squash merge.
5. Branch auto-deleted.

## 5. Versioning

- **Application release version:** SemVer `vMAJOR.MINOR.PATCH` for the monorepo as a whole (one version for all images). Pre-1.0 during MVP: `v0.x.y` (minor for features, patch for fixes).
- **Ruleset version:** independent SemVer per ruleset (`pa-core 0.1.0`), bumped when trading outputs change ([ENG-04 §5](04_PYTHON_ENGINE_ARCHITECTURE.md#5-ruleset-versioning)).
- **API version:** `/api/v1` path; breaking changes require `/v2` ([ARC-04 §2.1](../architecture/04_API_SPECIFICATION.md#21-versioning)).
- **Engine package version:** follows app release version.

## 6. Release tagging and changelog

- Release-please (or equivalent) maintains a release PR from Conventional Commits, updating `CHANGELOG.md` and the version file; merging it creates tag `vX.Y.Z` and a GitHub Release.
- `release.yml` builds and publishes images tagged `vX.Y.Z` (Phase 2+).
- Ruleset changes are additionally recorded in `python-engine/rulesets/CHANGELOG.md`.

## 7. Hotfix process

1. Branch `fix/hotfix-<desc>` from `main` (or from the deployed tag if `main` contains unreleased risky changes).
2. Minimal fix + test; PR with label `hotfix`; same required checks (no bypass).
3. Merge, tag patch release, deploy to staging, verify, deploy to production with approval.
4. If branched from a tag, merge the fix back to `main` immediately.

Break-glass (repository admin bypass of protection) is allowed only when CI itself is broken and production is impaired; it must be followed within 24 h by an issue documenting why, and a normal PR restoring compliance.
