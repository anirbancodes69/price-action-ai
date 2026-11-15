# PriceAction AI — Python engine

Deterministic quantitative engine: FastAPI **internal** API plus arq workers, sharing one codebase and image.
Specification: [docs/engineering/04_PYTHON_ENGINE_ARCHITECTURE.md](../docs/engineering/04_PYTHON_ENGINE_ARCHITECTURE.md).

Status (M0): skeleton only — `/health`, `/ready`, authenticated `/internal/v1/ping`, JSON logging with
secret redaction, and a worker heartbeat job. Trading logic starts in M3.

```bash
# via Docker (preferred)
docker compose run --rm engine uv run pytest
# or locally with uv
uv sync && uv run pytest && uv run ruff check . && uv run mypy
```
