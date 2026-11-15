# Backend Architecture (Laravel)

| Field | Value |
|---|---|
| Document ID | ENG-03 |
| Version | 0.1.0 |
| Status | Specification ready (not implemented) |
| Owner | Backend Lead |
| Last updated | 2026-11-15 |
| Related | [ARC-01 §5 Modules](../architecture/01_SYSTEM_ARCHITECTURE.md#5-laravel-module-boundaries) · [ARC-03](../architecture/03_DATABASE_DESIGN.md) · [ARC-04](../architecture/04_API_SPECIFICATION.md) · [ARC-06](../architecture/06_SECURITY_ARCHITECTURE.md) · [ADR-002](../adr/ADR-002-LARAVEL-APPLICATION-BACKEND.md) |

## 1. Purpose

Defines the internal structure of the Laravel application backend: modules, layers, authorization, jobs, transactions and integration boundaries.

## 2. Directory layout

```
backend/
  app/
    Modules/
      Identity/         Http/Controllers, Http/Requests, Http/Resources, Models, Policies, Services, Events
      Onboarding/
      Preferences/
      Risk/
      Entitlements/
      Integrations/     Connectors/Kite/KiteConnector.php, Services/ProviderTokenVault.php
      MarketData/
      Analysis/
      Watchlists/
      Trading/          TradePlans, PaperTrading (read + user commands), ActualTrades
      Journal/
      Backtesting/
      Notifications/
    Shared/
      Engine/           EngineClient (HTTP), DTOs generated/validated from contracts/engine
      Tenancy/          BelongsToTenant trait, TenantContext, DataSourceAccess
      Http/             ApiResponse envelope, error renderer, RequestId middleware
      Audit/            AuditLogger
  routes/
    api.php             /api/v1 public routes (grouped per module)
    internal.php        /internal/v1 engine-facing routes (service-token middleware)
  database/migrations, seeders, factories
  tests/Unit, tests/Feature, tests/Architecture
```

Each module exposes a `Contracts/` interface (e.g. `TradePlanService`) used by other modules. Cross-module Eloquent access is forbidden and enforced with Pest architecture tests (`arch()->expect('App\Modules\Journal')->not->toUse('App\Modules\Trading\Models')`).

## 3. Layers

| Layer | Responsibility | Rules |
|---|---|---|
| Controller | HTTP mapping only | Thin; `authorize()`; calls one service method; returns API Resource |
| Form Request | Input validation | All rules from ARC-04; domain errors mapped to codes |
| Service | Use-case orchestration, transactions | Pure PHP classes; injected dependencies; no HTTP concerns |
| Model (Eloquent) | Persistence | Tenant global scope; casts for decimals (`decimal:2`), enums (PHP backed enums mirroring DB CHECK values) |
| Repository | **Only where justified** — complex read models (scanner query, portfolio aggregation) | No generic repository pattern over Eloquent |
| API Resource | Output shaping | Money as strings; `meta.data_mode` added by a response macro for market-data endpoints |
| Policy | Authorization | Role matrix ARC-06 §3; tenant ownership |
| Job | Async work in Laravel | Idempotent; `ShouldBeUnique` where relevant |
| Event/Listener | Domain events (e.g. `TradePlanCreated`) | Audit + notifications |

## 4. Key services

| Service | Notes |
|---|---|
| `RegistrationService` | One transaction creating tenant/user/membership/profile/onboarding/default entitlement/paper account (ARC-03 §10). |
| `OnboardingService` | Applies step payloads to owning modules via their contracts. |
| `RiskProfileService` | Creates new versions; validates bounds against active ruleset. |
| `TradePlanService` | Loads setup + run, checks actionability (LONG, not terminal, entry window, latest run), calls `EngineClient::positionSize`, persists plan, emits event. Ignores any client quantity. |
| `ScannerQuery` | Reads latest completed `analysis_batch` for tenant's data source; joins primary setups; filters; cursor pagination; Redis cache 5 min keyed by (source, batch, filters hash) for global sources only. |
| `ProviderTokenVault` | Encrypt/decrypt with `PROVIDER_TOKEN_KEY` and key versions; only class allowed to read tokens; used by Kite callback and internal token endpoint. |
| `DataSourceAccess` | Returns readable data source IDs for a tenant (ARC-06 §4). |
| `EngineClient` | HTTP client with timeouts (2 s sync), retries only for idempotent GETs, maps engine errors to API errors. |
| `EngineEventHandler` | Handles `POST /internal/v1/events` idempotently (stores processed `event_id` in Redis 7 days + unique notification key). |

## 5. Authorization

Policies per model; `Gate::before` for platform admins only on admin routes. Entitlement checks via `EntitlementGate` middleware (`entitled:ai_explanations`). Rate limiters defined in `AppServiceProvider` per ARC-04 §2.7.

## 6. Jobs and queues (Horizon)

| Queue | Jobs |
|---|---|
| `default` | Notification creation, email sending |
| `events` | Engine event processing |
| `maintenance` | Retention purges, token-expiry sweep, re-encryption on key rotation |

Scheduler (`routes/console.php`): `eod:pipeline` per data source at `EOD_PIPELINE_TIME` on trading days (checks `market_calendar`), `providers:expire-tokens` before pipeline, `retention:run` daily 02:00 IST.

## 7. Transactions and concurrency

- Service methods that write multiple rows use `DB::transaction()` with explicit retry for serialization failures (3 attempts).
- Optimistic locking on `trade_plans.lock_version`; pessimistic `lockForUpdate()` for actual-trade aggregates and per-tenant plan-number counters.
- Engine calls happen **outside** DB transactions to avoid holding locks during network I/O; results are re-validated (e.g. plan still creatable) inside the transaction.

## 8. Integration boundaries

| Boundary | Mechanism |
|---|---|
| Engine | `Shared/Engine/EngineClient` only; DTOs validated against `contracts/engine` JSON Schemas in tests |
| Kite (connect flow) | `Integrations/Connectors/Kite/KiteConnector` implementing `BrokerConnector` |
| Email | Laravel Mail with provider driver |
| Frontend | `/api/v1` + OpenAPI contract tests (responses validated against `contracts/api/openapi.yaml`) |

## 9. Error handling

Global exception handler renders the error envelope (ARC-04 §2.4) with `request_id`; domain exceptions carry codes (`DomainException::code()`); unexpected exceptions → 500 `INTERNAL_ERROR` and error tracking. Details: [ENG-06](06_ERROR_HANDLING_AND_LOGGING.md).

## 10. Testing

Pest: unit (services with fakes), feature (HTTP + DB on PostgreSQL service container, never SQLite, because of CHECK/exclusion constraints and arrays), architecture (module rules), contract (OpenAPI). See [ENG-07](07_TESTING_STRATEGY.md).
