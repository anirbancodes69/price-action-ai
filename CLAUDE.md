# CLAUDE.md — PriceAction AI

Persistent instructions for Claude Code (and any other contributor). Keep this file short. It points to the authoritative documents and does not copy them.

## 1. Project overview

PriceAction AI is an AI-assisted, rule-based **price-action analysis and trade-planning** platform for Indian equity swing and positional traders. Initial scope: NSE cash market, NIFTY 500, daily timeframe. It is decision support only: users execute trades themselves on their broker's platform.

- **Users:** retail swing traders, positional traders, equity investors who use price action.
- **Capabilities (planned):** market scanner, per-stock structure analysis (swings, BOS/CHoCH, S/R zones, liquidity), setup detection with a quality score, risk-based trade plans, watchlists, paper trading, backtesting, journal, LLM explanations.
- **Methodology:** pure price action. No RSI, MACD or moving-average signals. See [TRD-01](docs/trading/01_TRADING_METHODOLOGY.md).
- **Direction:** personal-first, designed so it can become a SaaS later (data licensing and legal review gate that step; see [ADR-011](docs/adr/ADR-011-DATA-MODES-AND-TENANT-ISOLATION.md)).

Current state: **[CURRENT.md](CURRENT.md)**. Milestones: **[ROADMAP.md](ROADMAP.md)**.

### Repository layout

```
frontend/        Next.js 16 app (Phase 1 UI, mock data only). Read frontend/AGENTS.md before framework-level changes.
backend/         Laravel 13 application backend (M0 skeleton: health endpoint only)
python-engine/   FastAPI quant engine + arq workers (M0 skeleton: health/ping only)
contracts/       OpenAPI + engine JSON Schemas (planned, M1; directory does not exist yet)
infrastructure/  Docker configs (nginx, postgres init, redis)
scripts/         setup-env.sh
docs/            Authoritative specification. Start at docs/README.md
.github/         CI workflows (ci-gate), templates, CODEOWNERS, Dependabot
```

## 2. Mandatory technology decisions

Next.js (App Router) · React · TypeScript (strict) · Tailwind CSS · TradingView Lightweight Charts · Laravel · Python FastAPI + arq workers · PostgreSQL · Redis · Docker Compose · GitHub Actions.

- **Do not** introduce Bootstrap or any UI component library. The frontend uses its own token-based design system ([ADR-001](docs/adr/ADR-001-FRONTEND-ARCHITECTURE.md)).
- Pinned versions: [ARC-02](docs/architecture/02_TECHNOLOGY_STACK.md). Changing a decision follows §8.

## 3. Architecture rules

- **Modular monolith** (Laravel) plus **one** separate Python quant service. Do not add microservices or extra infrastructure ([ADR-004](docs/adr/ADR-004-MODULAR-MONOLITH.md)).
- **API-first.** The frontend talks only to `/api/v1` on Laravel. It never calls the engine, Kite or the database directly. Contracts are defined in [ARC-04](docs/architecture/04_API_SPECIFICATION.md); from M1, `contracts/` will hold the machine-readable source.
- **Separation:** UI in `frontend/`, business/application logic in `backend/`, all trading calculations in `python-engine/app/domain`. Never duplicate trading logic in PHP or TypeScript.
- **Market data goes through the provider abstraction** (`MarketDataProvider`; Zerodha Kite first, DEMO provider always; [ADR-007](docs/adr/ADR-007-MARKET-DATA-PROVIDER-ABSTRACTION.md)).
- **Single writer per table**, with the explicit exceptions listed in [ARC-01 §6](docs/architecture/01_SYSTEM_ARCHITECTURE.md). Schema owner: Laravel migrations ([ARC-03](docs/architecture/03_DATABASE_DESIGN.md)).
- Keep demo, personal and licensed data modes separate. Demo data is never presented as live ([ADR-011](docs/adr/ADR-011-DATA-MODES-AND-TENANT-ISOLATION.md)).

## 4. Trading engine rules (non-negotiable)

- Calculations are **deterministic**, pure and independently testable ([ADR-008](docs/adr/ADR-008-DETERMINISTIC-TRADING-ENGINE.md)).
- **No look-ahead bias:** a pivot is usable only from its confirmation bar; a signal at close *t* fills at open *t+1* ([TRD-06](docs/trading/06_BACKTESTING_METHODOLOGY.md)).
- Parameters come only from the **versioned ruleset** (`pa-core x.y.z`, registry in [TRD-01 §6](docs/trading/01_TRADING_METHODOLOGY.md#6-ruleset-parameter-registry-authoritative)). If outputs change, bump the ruleset version and update the TRD docs in the same PR.
- Every analysis references an **immutable candle snapshot** and the ruleset version.
- **The LLM only explains.** It never calculates or changes entry, stop-loss, target, quantity or classification ([ADR-009](docs/adr/ADR-009-LLM-EXPLANATION-ONLY.md)).
- **No automated broker order placement in MVP** ([ADR-010](docs/adr/ADR-010-MANUAL-TRADE-EXECUTION-MVP.md)).
- **No-trade is a valid outcome.** Bearish setups are informational only (long-only actionability).
- Proposed trade plans, paper trades and actual trades are stored and handled **separately**.

## 5. Development rules

- **Docker first.** Use `make up`, `make dev`, `make test` and `make lint` (see [Makefile](Makefile) and [ENG-08](docs/engineering/08_DEVELOPMENT_ENVIRONMENT.md)).
- Strong typing everywhere: TypeScript strict, mypy for Python, typed PHP. Domain types in `frontend/src/types` are the frontend contract.
- Reuse existing components (`frontend/src/components/**`), labels (`lib/labels.ts`) and formatters (`lib/format.ts`). Do not create parallel versions.
- Pages depend only on the `DataSource` interface (`frontend/src/lib/data/source.ts`). Backend integration means swapping the adapter, not rewriting pages.
- Add or update tests with every behaviour change ([ENG-07](docs/engineering/07_TESTING_STRATEGY.md)). Trading code needs the TRD-08 test vectors.
- Error handling and logging follow [ENG-06](docs/engineering/06_ERROR_HANDLING_AND_LOGGING.md). Never log tokens, credentials or PII.
- Broker credentials never reach the frontend. The Kite access token is encrypted at rest and fetched just in time ([ARC-06](docs/architecture/06_SECURITY_ARCHITECTURE.md)).
- No unnecessary restructuring or renaming. Existing structure is authoritative.

## 6. GitHub rules

- GitHub Flow: short-lived branches `feature/…`, `fix/…`, `chore/…`, `docs/…`, `refactor/…` ([ENG-11](docs/engineering/11_BRANCHING_AND_RELEASE_STRATEGY.md)).
- **Conventional Commits.** PR titles are validated by CI. Types: `feat fix docs chore refactor test ci build perf`. Scopes: `frontend backend engine contracts infra docs ruleset deps`. **A scope is required** (`type(scope): summary`, e.g. `docs(docs): …`); CI rejects titles without one. Merges are squash-only.
- `main` is protected by the "Protect Main" ruleset: PR required, `ci-gate` must pass, linear history, no force-push.
- Complete the [PR template](.github/pull_request_template.md). Review migrations and API contract changes with particular care ([ENG-12 §4](docs/engineering/12_CODE_QUALITY_AND_PULL_REQUESTS.md)).
- Never commit secrets. `.env` is gitignored, and `.env.example` holds placeholders only.
- Do not commit or push unless the user asks.

## 7. Working protocol

**Start of every substantial task**

1. Read this file and [CURRENT.md](CURRENT.md).
2. Read the relevant milestone in [ROADMAP.md](ROADMAP.md) → [ENG-01](docs/engineering/01_IMPLEMENTATION_ROADMAP.md), plus the relevant tasks in [TASKS.md](TASKS.md).
3. Read the relevant [DECISIONS.md](DECISIONS.md) entries and their ADRs.
4. Read only the specs that matter for the task (reading order in [docs/README.md §3](docs/README.md#3-reading-order)). Follow cross-references. Do not load all docs.
5. Inspect the existing code you will touch. Identify dependencies and regression risk.
6. For substantial changes, write an implementation plan first.

**During**: follow the established architecture, implement in small steps, add tests, check real behaviour, and never silently change a decision.

**End (definition of done; documentation is part of done)**

1. Run the relevant tests and linters (`make test`, `make lint`, or the component equivalent) and report real results.
2. Verify the acceptance criteria.
3. Update the authoritative docs for whatever changed (§9 mapping), then summaries and links.
4. Sync [CURRENT.md](CURRENT.md), [TASKS.md](TASKS.md), [ROADMAP.md](ROADMAP.md) (if milestone progress changed), [CHANGELOG.md](CHANGELOG.md) (if significant), [PRD-06 feature catalog](docs/product/06_FEATURE_CATALOG.md) (if feature state changed) and [docs/DOCUMENTATION_STATUS.md](docs/DOCUMENTATION_STATUS.md) (if document status changed).
5. Report what changed and what limitations remain.

Progress must reflect **verified repository state**, not intentions or plans. Never mark something complete just because a spec exists. If code and spec disagree, record it (e.g. [ENG-02 §9](docs/engineering/02_FRONTEND_ARCHITECTURE.md#9-discrepancy-register)) and decide which one to fix.

## 8. Decision-change protocol

Never silently change an architectural or product decision. If a change is needed:

1. Explain why, list affected components and the alternatives considered.
2. Write a new ADR (`docs/adr/ADR-NNN-*.md`) that supersedes the old one. Mark the old one `Superseded by ADR-NNN`.
3. Update [DECISIONS.md](DECISIONS.md), [docs/adr/README.md](docs/adr/README.md) and the affected specs.
4. State the migration and compatibility consequences.
5. Update this file only if the persistent instructions change.

Unresolved questions are `OQ-*` items in each doc, aggregated in [DOCUMENTATION_STATUS §2](docs/DOCUMENTATION_STATUS.md#2-open-questions-register). Do not resolve them by assumption. Ask the owner.

## 9. Documentation maintenance (mandatory)

Docs evolve with the code, in the same PR. Review the docs below for each kind of change and update only those actually affected:

| Change | Review |
|---|---|
| Frontend | PRD-03, PRD-06, PRD-07, ENG-02 (incl. §9 discrepancies), ARC-04 if data needs change |
| Database schema | ARC-03, ARC-04, ARC-05, ENG-03, related ADRs, migration/testing notes |
| API | ARC-04 (+ `contracts/` from M1), ENG-03, ENG-02 §8, ARC-06, API tests |
| Trading logic | TRD-01..08, ENG-04; bump the ruleset version if outputs change |
| CI, Docker, GitHub, deploy | ENG-08, ENG-09, ENG-10, ENG-11, OPS-01/02, ARC-06 |
| Architecture | New/updated ADR, DECISIONS.md, ARC-*, ENG-01; CLAUDE.md only if instructions change |

Do not touch unrelated documents just to show activity.
