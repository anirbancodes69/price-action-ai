# GitHub Repository Strategy

| Field | Value |
|---|---|
| Document ID | ENG-09 |
| Version | 0.1.0 |
| Status | Specification ready (repository has no commits yet) |
| Owner | Technical Lead |
| Last updated | 2026-11-15 |
| Related | [ENG-10 CI/CD](10_GITHUB_ACTIONS_CI_CD.md) · [ENG-11 Branching](11_BRANCHING_AND_RELEASE_STRATEGY.md) · [ENG-12 PRs](12_CODE_QUALITY_AND_PULL_REQUESTS.md) · [ADR-012](../adr/ADR-012-GITHUB-ACTIONS-CI-CD.md) |

## 1. Decision

A single **monorepo** on GitHub for all components. Rationale: one developer, shared contracts (OpenAPI, engine schemas, DB schema) change together, atomic PRs across layers, one CI configuration. Splitting is reconsidered only if independent teams or release cadences emerge.

## 2. Repository structure

Adapted to the existing layout (the `frontend/` directory stays where it is; nothing is moved):

```
/
  frontend/                 # existing Next.js app
  backend/                  # Laravel (M0)
  python-engine/            # FastAPI + workers + domain library (M0)
  contracts/
    api/openapi.yaml        # public API contract (M1)
    engine/*.json           # engine JSON Schemas exported from Pydantic (M1)
  docs/                     # this documentation
  infrastructure/
    docker/                 # shared Dockerfiles/configs: nginx, postgres init (roles, extensions), redis
    deploy/                 # compose overrides for staging/production, deploy scripts (M10)
  scripts/                  # dev wrappers, catalogue checks, schema export
  .github/
    workflows/              # CI/CD (ENG-10) — not created in documentation phase
    ISSUE_TEMPLATE/
    pull_request_template.md
    CODEOWNERS
    dependabot.yml
  docker-compose.yml        # existing
  .env.example
  .gitignore                # root (M0) — must exclude .DS_Store, .env*, **/node_modules, **/.next, **/tsconfig.tsbuildinfo, **/vendor, **/.venv, **/__pycache__
  README.md
```

## 3. Ownership boundaries

| Path | Owner (role) | Review requirement |
|---|---|---|
| `frontend/**` | Frontend lead | Self-review checklist (solo) |
| `backend/**` | Backend lead | Same |
| `python-engine/app/domain/**`, `python-engine/rulesets/**` | Trading engine lead | Must link TRD section; ruleset version bump if golden outputs change |
| `contracts/**` | Solution architect | API compatibility review (ENG-12 §4) |
| `backend/database/migrations/**` | Backend lead | Migration review (ENG-12 §4) |
| `docs/**` | Documentation owner per document header | Docs consistency check |
| `.github/**`, `infrastructure/**` | Technical lead | Security review |

`CODEOWNERS` lists the repository owner for all paths initially; it is structured by path so additional maintainers can be added without restructuring.

## 4. Documentation ownership

- `docs/` is the source of truth for product and architecture (see [docs/README.md](../README.md)).
- Behavioural changes must update the authoritative document in the same PR (PR template checkbox).
- `docs/DOCUMENTATION_STATUS.md` updated when a document's status changes.

## 5. Secret management

- Never commit secrets (constraint C-17). Enforced by GitHub secret scanning + push protection and a CI secret scanner (ENG-10 §8).
- `.env.example` files contain variable names and safe placeholders only.
- CI secrets: none required for build/test (ephemeral keys generated in workflow). Deployment secrets live in GitHub **Environments** (`staging`, `production`) with environment protection rules.
- Recorded HTTP fixtures are scrubbed of tokens; a test asserts no fixture contains token-like strings.

## 6. Repository settings

| Setting | Value |
|---|---|
| Visibility | Private |
| Default branch | `main` |
| Merge methods | Squash merge only (linear history); auto-delete head branches |
| Secret scanning + push protection | Enabled |
| Dependabot alerts + security updates | Enabled |
| Code scanning (CodeQL) | Enabled for JS/TS and Python (PHP via other SAST, ENG-10 §8) |
| Actions permissions | Default `GITHUB_TOKEN` read-only; workflows request elevated permissions explicitly |
| Allowed actions | GitHub-owned and verified creators; third-party actions pinned by commit SHA |
| Issues | Enabled with templates: bug, feature, spec change, open question |
| Wiki | Disabled (docs live in repo) |

## 7. Branch protection (`main`)

Ruleset (repository rules) on `main`:

- Require a pull request before merging; **required approvals: 0** while solo (self-review via PR checklist); raise to 1 when a second maintainer joins.
- Require status checks to pass (list in [ENG-10 §10](10_GITHUB_ACTIONS_CI_CD.md#10-ci-quality-gates)); require branches up to date before merging.
- Require conversation resolution.
- Block force pushes; block deletion; no direct pushes (including admins — "do not allow bypass", with emergency break-glass documented in ENG-11 §7).
- Require linear history.
- Signed commits: recommended, not required initially.

## 8. Labels

`area:frontend`, `area:backend`, `area:engine`, `area:infra`, `area:docs`, `type:feature`, `type:bug`, `type:chore`, `type:spec`, `risk:migration`, `risk:api-change`, `risk:security`, `ruleset-change`. Labels can be auto-applied by path (actions/labeler).
