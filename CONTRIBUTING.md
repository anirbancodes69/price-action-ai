# Contributing to PriceAction AI

This guide is the short version. The detailed rules live in the engineering docs linked below. If this file and those docs disagree, the docs win; please fix this file.

## Prerequisites

- Docker (with Compose v2) and `make`. Everything else runs in containers.
- Optional, for running outside Docker: Node 26, PHP 8.4 + Composer, Python 3.13 + `uv`.

## Development setup

```bash
./scripts/setup-env.sh   # once: creates .env with random dev secrets
make up                  # production-like stack
make dev                 # hot reload (frontend-dev on :3001)
make test                # all test suites
make lint                # all linters and type checks
make help                # every target
```

Details: [ENG-08 Development environment](docs/engineering/08_DEVELOPMENT_ENVIRONMENT.md).

## Before you start

Read [CLAUDE.md](CLAUDE.md) (architecture and trading-engine rules), [CURRENT.md](CURRENT.md) (what exists today) and the relevant task in [TASKS.md](TASKS.md). Then read the specification for the area you are changing ([docs/README.md](docs/README.md#3-reading-order)).

## Branches

GitHub Flow from `main`, with short-lived branches ([ENG-11](docs/engineering/11_BRANCHING_AND_RELEASE_STRATEGY.md)):

`feature/<area>-<desc>` · `fix/<area>-<desc>` · `chore/<desc>` · `docs/<desc>` · `refactor/<desc>`

## Commits and PR titles

[Conventional Commits](https://www.conventionalcommits.org/): `type(scope): summary`.

- Types: `feat fix docs chore refactor test ci build perf`
- Scopes: `frontend backend engine contracts infra docs ruleset deps`. **A scope is required**; CI fails the PR title without one (`ci.yml`, job `semantic-title`).
- Breaking change: `!` after the type, or a `BREAKING CHANGE:` footer.

Merges are squash-only, so the **PR title** becomes the commit message. CI validates it.

GitHub fills the title of a PR with more than one commit from the **branch name** (for example `Feature/contracts openapi spec`), which never passes. The `semantic-title` job therefore rewrites such a title to the newest conforming commit subject (preferring `feat`/`fix`) and then validates it; it only fails when no commit subject conforms either. Editing a title re-runs CI automatically (`edited` trigger), so no close/reopen is needed. Still review the title: it is the squash commit message.

## Pull requests

1. Open a (draft) PR against `main` and fill in the [PR template](.github/pull_request_template.md).
2. `ci-gate` must be green. The "Protect Main" ruleset requires a PR, passing checks, an up-to-date branch and resolved conversations.
3. Self-review with the checklists in [ENG-12 §4](docs/engineering/12_CODE_QUALITY_AND_PULL_REQUESTS.md#4-review-checklists). Take particular care with **migrations** (backward compatible, expand → contract) and **API contracts** (additive only within `/v1`).

## Testing

- Every behaviour change ships with tests ([ENG-07](docs/engineering/07_TESTING_STRATEGY.md)).
- Trading logic must pass the TRD-08 test vectors, including no-look-ahead tests. If outputs change, bump the ruleset version.
- CI never calls live market-data providers. Use recorded fixtures.

## Code quality

- TypeScript strict, ESLint; PHP Pint; Python ruff + strict mypy.
- Respect module boundaries. Trading calculations only in `python-engine/app/domain`; no duplicated business logic.
- Reuse existing frontend components, labels and formatters. Use Tailwind with the existing design tokens, and no other UI frameworks.

## Documentation (required)

Documentation is part of the definition of done. Update the authoritative doc for whatever you changed, in the same PR (mapping in [CLAUDE.md §9](CLAUDE.md#9-documentation-maintenance-mandatory)). Update `CURRENT.md`, `TASKS.md`, `ROADMAP.md`, `CHANGELOG.md` and `docs/DOCUMENTATION_STATUS.md` when their content changes. Architectural changes need an ADR and a `DECISIONS.md` entry.

## Security

- Never commit secrets, tokens or real credentials. Use `.env` (gitignored) and keep `.env.example` to placeholders.
- Never log tokens, credentials or PII.
- Broker credentials never reach the frontend.
- Report vulnerabilities privately to the maintainer, not in public issues.
