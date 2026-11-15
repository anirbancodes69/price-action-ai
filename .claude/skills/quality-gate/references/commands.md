# Component → gates (as configured in Makefile and .github/workflows)

Re-check the `Makefile` and workflow files if a command fails; they are the source.

| Changed paths | Local (Docker, preferred) | CI job (workflow) | CI-equivalent without Docker |
|---|---|---|---|
| `frontend/**` | `make lint-frontend` · `make test-frontend` | frontend-ci: lint, typecheck, test, build | `cd frontend && npm run lint && npm run typecheck && npm test && npm run build` |
| `backend/**` | `make lint-backend` · `make test-backend` (needs `make dev` for postgres) | backend-ci: composer validate, Pint, migrate on empty PG, PHPUnit | needs PostgreSQL. Use Docker. |
| `backend/database/**` | above + fresh-DB up / rollback / up | backend-ci migrations step | — |
| `python-engine/**` | `make lint-engine` · `make test-engine` | python-engine-ci: ruff check, ruff format --check, mypy, pytest | `cd python-engine && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest` |
| `docker-compose*.yml`, `infrastructure/**`, `**/Dockerfile*` | `make build` · `make up` · `make health` | docker-build: compose validate, build, up --wait, smoke | — |
| `.github/**` | review path filters and `ci-gate` needs list | all workflows run | — |
| `docs/**`, `*.md`, `.claude/**` | `python3 .claude/skills/docs-sync/scripts/check_links.py` | none yet (planned docs-lint) | same |
| any | — | security-scan: gitleaks, npm/composer/pip audit | — |

Full suites: `make test` and `make lint`. Stack lifecycle: `make dev`, `make down`, `make reset` (deletes volumes).
