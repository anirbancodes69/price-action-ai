# PriceAction AI

AI-assisted, rule-based **price-action analysis and trade-planning** for Indian equity swing and positional traders (NSE cash market, NIFTY 500, daily timeframe).

PriceAction AI is a decision-support tool. It does **not** place orders and does not provide investment advice. Deterministic rules compute structure, setups, levels and position size; an LLM only explains those results.

## Status

| Component | State |
|---|---|
| Frontend (`frontend/`) | Phase 1 UI built (Next.js 16, React 19, Tailwind v4, Lightweight Charts). It runs entirely on **sample data** through a mock adapter. |
| Documentation (`docs/`) | Phase 2 specification. This is the source of truth for upcoming development. |
| Infrastructure (M0) | Done. Docker Compose stack (Laravel and FastAPI skeletons with health checks, arq worker, PostgreSQL, Redis, nginx), GitHub Actions CI, Makefile. |
| Trading engine, API, persistence | Specified, not built yet. Next up is M1 (database and contracts). See the [roadmap](docs/engineering/01_IMPLEMENTATION_ROADMAP.md). |

## Documentation

Start at **[docs/README.md](docs/README.md)** for the structure, reading order and source-of-truth rules. Key entry points:

- [Product vision](docs/product/01_PRODUCT_VISION.md)
- [System architecture](docs/architecture/01_SYSTEM_ARCHITECTURE.md)
- [Trading methodology & parameter registry](docs/trading/01_TRADING_METHODOLOGY.md)
- [Implementation roadmap](docs/engineering/01_IMPLEMENTATION_ROADMAP.md)
- [Architecture decision records](docs/adr/README.md)

## Run locally

You need Docker and `make`.

```bash
./scripts/setup-env.sh   # once: creates .env with random development secrets
make up                  # whole stack → frontend http://localhost:3000, API http://localhost:8000/api/health
make dev                 # hot reload (frontend-dev on :3001)
make test && make lint   # every suite, run inside containers
make help                # all targets
```

`/` redirects to `/login`. In this build any syntactically valid email and password opens the demo workspace. Details: [docs/engineering/08_DEVELOPMENT_ENVIRONMENT.md](docs/engineering/08_DEVELOPMENT_ENVIRONMENT.md).

## Repository layout

```
frontend/        Next.js app (exists)
backend/         Laravel 13 application backend (skeleton)
python-engine/   FastAPI quantitative engine + arq workers (skeleton)
contracts/       OpenAPI and engine JSON Schemas (planned)
infrastructure/  Docker configuration (nginx, postgres init, redis)
scripts/         setup-env.sh
.github/         CI workflows, templates, CODEOWNERS, Dependabot
docs/            Product, architecture, trading, engineering, operations docs, ADRs
```
