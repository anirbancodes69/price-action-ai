# PriceAction AI

AI-assisted, rule-based **price-action analysis and trade-planning** for Indian equity swing and positional traders (NSE cash market, NIFTY 500, daily timeframe).

PriceAction AI is a decision-support tool. It does **not** place orders and does not provide investment advice. Deterministic rules compute structure, setups, levels and position size; an LLM only explains those results.

## Status

| Component | State |
|---|---|
| Frontend (`frontend/`) | Phase 1 UI built (Next.js 16, React 19, Tailwind v4, Lightweight Charts). It runs entirely on **sample data** through a mock adapter. |
| Documentation (`docs/`) | Phase 2 specification. This is the source of truth for upcoming development. |
| Laravel backend, Python engine, PostgreSQL, Redis, CI | Specified, not yet built. See the [roadmap](docs/engineering/01_IMPLEMENTATION_ROADMAP.md). |

## Documentation

Start at **[docs/README.md](docs/README.md)** for the structure, reading order and source-of-truth rules. Key entry points:

- [Product vision](docs/product/01_PRODUCT_VISION.md)
- [System architecture](docs/architecture/01_SYSTEM_ARCHITECTURE.md)
- [Trading methodology & parameter registry](docs/trading/01_TRADING_METHODOLOGY.md)
- [Implementation roadmap](docs/engineering/01_IMPLEMENTATION_ROADMAP.md)
- [Architecture decision records](docs/adr/README.md)

## Run the frontend

```bash
docker compose up --build frontend             # production build → http://localhost:3000
docker compose --profile dev up frontend-dev   # hot reload → http://localhost:3001
```

`/` redirects to `/login`. In this build any syntactically valid email and password opens the demo workspace. Details are in [frontend/README.md](frontend/README.md) and [docs/engineering/08_DEVELOPMENT_ENVIRONMENT.md](docs/engineering/08_DEVELOPMENT_ENVIRONMENT.md).

## Planned repository layout

```
frontend/        Next.js app (exists)
backend/         Laravel application backend (planned)
python-engine/   FastAPI quantitative engine + workers (planned)
contracts/       OpenAPI and engine JSON Schemas (planned)
infrastructure/  Docker and deployment configuration (planned)
docs/            Product, architecture, trading, engineering, operations docs, ADRs
```
