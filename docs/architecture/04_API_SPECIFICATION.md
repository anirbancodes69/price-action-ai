# API Specification (Public REST API v1)

| Field | Value |
|---|---|
| Document ID | ARC-04 |
| Version | 0.1.0 |
| Status | Specification ready (daily); intraday conventions in §2.9 (ADR-015). Machine-readable contract in `contracts/api/openapi.yaml` (M1, T-103) |
| Owner | Backend Lead |
| Last updated | 2026-11-15 |
| Related | [ARC-03 Database](03_DATABASE_DESIGN.md) · [ARC-06 Security](06_SECURITY_ARCHITECTURE.md) · [ARC-08 Internal engine API](08_INTEGRATION_ARCHITECTURE.md) · [ENG-02 Frontend mapping](../engineering/02_FRONTEND_ARCHITECTURE.md#8-route--feature--api--entity-mapping) |

## 0. Personal-mode status (ADR-014, ADR-016)

Implemented so far (T-I82..T-I87): `POST /auth/login`, `POST /auth/logout`, `GET /me`, `GET /scanner`, `POST /risk/calculate`. Everything else in this document is specified but **not built**. Where the personal-mode behaviour differs from the text below:

| Endpoint | Difference |
|---|---|
| A3 login, A4 logout, A9 me | One owner account created with `php artisan owner:create` (no registration). `me` and the login response return `user` only; `tenant`, `entitlement`, `onboarding` and `data_source` are omitted. |
| N1 scanner | Live (ADR-016): each request calls the engine's `/internal/v1/scan` and analyses the universe on the latest closed bars. There is no batch, so no `meta.batch` and no `409 NO_ANALYSIS_AVAILABLE`; `analysis_run_id` and `volume` are `null`, `change` and `change_pct` are `null` when the previous close is unknown, `structure_state` is `null` when history is too short. `near` and `watchlist` are rejected with 422. Errors: 503 `ENGINE_UNAVAILABLE`, 502 `ENGINE_CONTRACT_ERROR`, 409 `NO_DATA_SOURCE` / `RULESET_UNAVAILABLE`. `meta` adds `total`, `ruleset`, `notice`. |
| R1 risk calculate | Laravel supplies the risk profile (stored, else ruleset defaults with the planning capital `TRADING_CAPITAL_DEFAULT`), the book's account state derived from the trade tables, tick/lot size and the session clock; the engine sizes. A rule violation is a 422 whose `error.details` carries `errors` and the full `calculation`. |
| `target_source` | Adds the intraday sources `MEASURED_OPENING_RANGE`, `PDH`, `SESSION_HIGH`, `OR_HIGH`, `HTF_SWING_HIGH`. |

## 1. Purpose and scope

Defines the public HTTP API served by Laravel under `/api/v1` and consumed by the Next.js frontend (and, later, other clients). Contracts are **resource-oriented and independent of frontend components**; the frontend adapter maps them to its view models. Internal engine endpoints are in [ARC-08](08_INTEGRATION_ARCHITECTURE.md).

**Machine-readable contract.** [`contracts/api/openapi.yaml`](../../contracts/api/openapi.yaml) (OpenAPI 3.1) carries every endpoint below, tagged with its id in `x-arc04-id`. Change this document and the file together. CI lints the file and fails when an endpoint id or its method and path differ between the two (`contracts/scripts/check_arc04_coverage.py`). Where this document leaves a payload open (for example `exposure`, backtest `metrics`, `entity`), the OpenAPI schema is deliberately loose (`additionalProperties: true`) and is tightened when the M6 contract tests are written.

## 2. Conventions

### 2.1 Versioning

- Base path `/api/v1`. Additive changes (new fields, endpoints, enum values documented as extensible) are allowed within v1. Removing/renaming fields or changing semantics requires `/api/v2` and a deprecation window of ≥ 1 release with `Deprecation` and `Sunset` headers.
- Enum fields listed as **extensible** may gain values; clients must handle unknown values gracefully.

### 2.2 Authentication

- Laravel Sanctum **SPA cookie authentication**. The frontend proxies `/api/*` and `/sanctum/*` to Laravel via a Next.js rewrite so that the session cookie is first-party.
- Flow: `GET /sanctum/csrf-cookie` → sets `XSRF-TOKEN`; mutating requests send `X-XSRF-TOKEN`. Session cookie: `HttpOnly; Secure; SameSite=Lax`.
- Next.js server components call Laravel over the internal network forwarding the incoming `Cookie` header and `X-Request-Id`.
- `Auth: session` below means an authenticated, email-verified user with an active tenant. `Auth: none` means public. Unverified users can only call auth/me endpoints.

### 2.3 Tenant context

Resolved server-side from the session (user's current tenant membership). Clients never send `tenant_id`. Any resource ID belonging to another tenant returns **404** (not 403) to avoid enumeration.

### 2.4 Envelopes

Success:

```json
{
  "data": { },
  "meta": { "request_id": "01JD…", "data_mode": "DEMO", "as_of": "2026-11-13" }
}
```

`meta.data_mode` (`DEMO` | `PERSONAL` | `LICENSED`) and `meta.as_of` are **mandatory on every response that contains market data or analysis** (constraint C-03). The frontend must render a sample/demo badge whenever `data_mode = DEMO`.

Error (all non-2xx):

```json
{
  "error": {
    "code": "RR_BELOW_MINIMUM",
    "message": "Risk/reward 1.55 is below the minimum 2.00.",
    "details": { "field_errors": { "target_price": ["..."] } },
    "request_id": "01JD…"
  }
}
```

### 2.5 Standard error codes

| HTTP | Code | When |
|---|---|---|
| 400 | `BAD_REQUEST` | Malformed JSON |
| 401 | `UNAUTHENTICATED` | No/expired session |
| 403 | `FORBIDDEN` | Authenticated but lacks permission or entitlement (`ENTITLEMENT_REQUIRED` variant) |
| 403 | `EMAIL_NOT_VERIFIED` | |
| 404 | `NOT_FOUND` | Missing or other tenant's resource |
| 409 | `CONFLICT` / `STALE_VERSION` | Optimistic-lock or state conflict (e.g. editing a non-PENDING plan) |
| 419 | `CSRF_TOKEN_MISMATCH` | Laravel CSRF |
| 422 | `VALIDATION_FAILED` + domain codes | Field validation; domain rule violations use specific codes (e.g. `STOP_NOT_BELOW_ENTRY`) |
| 429 | `RATE_LIMITED` / `QUOTA_EXCEEDED` | With `Retry-After` |
| 502 | `ENGINE_CONTRACT_ERROR` | Engine returned an unexpected payload |
| 503 | `ENGINE_UNAVAILABLE` / `PROVIDER_UNAVAILABLE` | Dependency down; `Retry-After` |

### 2.6 Pagination, filtering, sorting

- Cursor pagination: `?limit=25&cursor=<opaque>`; `limit` max 100. Response `meta.next_cursor` (null at end).
- Filtering uses explicit query params per endpoint; sorting `?sort=field` / `?sort=-field` from an allow-list.
- Dates `YYYY-MM-DD` (exchange date); timestamps ISO-8601 with offset.
- Prices and money are JSON **strings** with 2 decimals (e.g. `"1495.50"`) to avoid float drift; quantities are integers; percentages and ratios are strings with up to 4 decimals.

### 2.7 Rate limits (defaults, per user unless stated)

| Bucket | Limit |
|---|---|
| `auth` (login, register, forgot/reset password) | 5/min per IP+email, 20/hour per IP |
| `default` | 120/min |
| `analysis-refresh` | 10/min, and entitlement daily cap |
| `ai` | 10/min, and `ai_explanations_per_day` entitlement |
| `backtest-create` | 3/min, and `backtests_per_day` entitlement |
| `integration` (Zerodha connect) | 5/min |

Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `Retry-After` on 429.

### 2.8 Idempotency

`POST` endpoints that create trading records (`/trade-plans`, `/actual-trades`, `/actual-trades/{id}/fills`, `/backtests`) accept `Idempotency-Key` (UUID). Same key + same body within 24 h returns the original response; same key + different body → 409 `IDEMPOTENCY_KEY_REUSED`.

### 2.9 Intraday time conventions (ADR-015)

For the intraday direction ([ADR-014](../adr/ADR-014-PERSONAL-INTRADAY-WORKSTATION.md), [ADR-015](../adr/ADR-015-INTRADAY-TIME-AND-SNAPSHOT-MODEL.md)). These conventions apply when the endpoints below are revised in I1/I6; the OpenAPI file changes in the same PR.

- Every bar and every moment is an ISO-8601 timestamp **with the `+05:30` offset** (for example `2026-11-17T10:35:00+05:30`). Dates (`YYYY-MM-DD`) remain only for session dates.
- `Candle = { start, end, open, high, low, close: Price, volume: int }` where `start`/`end` are timestamps; daily candles use the session open and close.
- Candles and analysis take `?interval=5m|15m|1D` (`1m` reserved). The default for analysis is the 5m primary run with its 15m and daily context.
- `meta.as_of` becomes the timestamp of the end of the last completed bar used (still mandatory with `meta.data_mode`, C-03). Responses add `meta.next_bar_close` so the client knows when data can change.
- Signals carry `signal_at` (bar close that produced them) and `valid_until` (expiry within the session).
- Clients poll; recommended interval 10–30 seconds during the session. There is no push channel in the MVP (OQ-API-03 stays post-MVP).
- New resources (specified in TRD-05 revision, T-I06): `GET /api/v1/risk/today` (remaining daily risk, losing streak, block reason) and `GET /api/v1/positions/live` (current price and unrealised P&L of open positions, from the current-price cache).

## 3. Shared schemas

```text
Money        = string  "12345.67"
Price        = string  "1495.50"
Timestamp    = string  ISO-8601 with the +05:30 offset (§2.9)
Instrument   = { id, symbol, name, exchange: "NSE", segment: "EQ"|"INDEX", sector|null, isin|null, status, tick_size: Price, lot_size: int }
Candle       = { start, end: Timestamp, open, high, low, close: Price, volume: int }
SwingPoint   = { id, timeframe: "5m"|"15m", kind: "HIGH"|"LOW", bar_start, price, label, confirmed_at: Timestamp }
StructureEvt = { id, timeframe, type: "BOS"|"CHOCH"|"WICK_BREACH", direction: "UP"|"DOWN", level, level_bar_start, break_bar_start, break_close, close_inside_buffer }
Zone         = { id, role: "SUPPORT"|"RESISTANCE", low, high, touches, strength_score, strength_bucket, status, role_reversed, formed_at, distance_pct }
LiquidityEvt = { id, type, level, first_bar_start, last_bar_start }
SessionLevels= { pdh, pdl, pdc, or_high|null, or_low|null, session_high, session_low: Price; entry_cutoff_at, session_end_exit_at: Timestamp }
Setup        = { id, setup_key, type, direction: "LONG"|"SHORT", informational, status, detected_at, signal_at|null, valid_until|null,
                 levels: { trigger, entry, stop, target, rr, target_source } | null,
                 rr_below_min, entry_window_open,
                 quality: { score, version, components: [{ key, label, points, max, missing, reason }] },
                 evidence: [{ code, tone: "SUPPORTING"|"CAUTION", title, detail, refs }],
                 reason_codes: [string] }
AnalysisRun  = { id, instrument: Instrument, as_of: Timestamp, status, timeframe: "5m",
                 ruleset: { code, version, validation_status }, engine_version,
                 inputs: [{ role: "PRIMARY_5M"|"CONTEXT_15M"|"DAILY_CONTEXT", candle_snapshot_id }],
                 context: { htf_state, htf_transition_direction|null, session: SessionLevels },
                 structure: { state, transition_direction|null, protected_low|null, protected_high|null, summary_text },
                 signal: { state, reason_codes, signal_at|null, valid_until|null },
                 primary_setup_id|null, setups: [Setup], swings: [SwingPoint], events: [StructureEvt],
                 zones: [Zone], liquidity: [LiquidityEvt], candles: [Candle] (only when ?include=candles) }
ScannerRow   = { instrument: Instrument, last_close, change, change_pct, volume, analysis_run_id, as_of,
                 htf_state, structure_state, signal_state, signal_at|null, valid_until|null,
                 primary_setup: { type, direction, status, levels, quality_score } | null }
TradePlan    = { id, plan_number: "TP-1042", instrument, status, status_reason, source, direction: "LONG",
                 entry, stop, target, engine_levels|null, levels_overridden, quantity, risk_budget, risk_amount,
                 position_value, rr, binding_constraint, paper_tracking, note, analysis_run_id, setup_id|null,
                 triggered_at|null, valid_until|null,
                 ruleset_version, created_at, updated_at, lock_version, linked: { paper_trade_id|null, actual_trade_ids: [] } }
RiskResult   = see §8.1
```

The shapes above are the intraday versions (ADR-014/015, revised in T-I09). The daily versions (dates instead of timestamps, a single `candle_snapshot_id`) are retired.

## 4. Authentication and account

| # | Method & path | Auth | Request | Response | Validation / errors |
|---|---|---|---|---|---|
| A1 | `GET /sanctum/csrf-cookie` | none | — | 204, sets `XSRF-TOKEN` | — |
| A2 | `POST /api/v1/auth/register` | none (rate `auth`) | `{name, email, password, password_confirmation, accept_terms: true}` | 201 `{user, tenant, onboarding}`; session started; verification email sent | name 1–80; email RFC + unique (`EMAIL_TAKEN` 422); password ≥ 8 chars, ≥ 1 letter + 1 digit, not in breached list (`PASSWORD_WEAK`); `accept_terms` must be true |
| A3 | `POST /api/v1/auth/login` | none (rate `auth`) | `{email, password, remember: bool}` | 200 `{user, onboarding}` | 422 `INVALID_CREDENTIALS` (generic, no user enumeration); 423 `ACCOUNT_SUSPENDED` |
| A4 | `POST /api/v1/auth/logout` | session | — | 204; session invalidated, token regenerated | — |
| A5 | `POST /api/v1/auth/forgot-password` | none (rate `auth`) | `{email}` | 202 always (no enumeration) | email format |
| A6 | `POST /api/v1/auth/reset-password` | none (rate `auth`) | `{token, email, password, password_confirmation}` | 204; all other sessions revoked | 422 `RESET_TOKEN_INVALID` |
| A7 | `POST /api/v1/auth/email/verification-notification` | session (unverified ok) | — | 202 | rate 3/hour |
| A8 | `GET /api/v1/auth/email/verify/{id}/{hash}?signature=…` | signed URL | — | 302 → `/onboarding` or `/dashboard` | 403 `INVALID_SIGNATURE` |
| A9 | `GET /api/v1/me` | session (unverified ok) | — | `{user: {id, email, email_verified, display_name, experience_level, timezone}, tenant: {id, name, role}, entitlement: {plan_code, features}, onboarding: {status, current_step}, data_source: {id, mode, provider, status}}` | — |
| A10 | `PATCH /api/v1/me/profile` | session | `{display_name?, experience_level?, timezone?}` | 200 `{user}` | enum checks |
| A11 | `PUT /api/v1/me/password` | session | `{current_password, password, password_confirmation}` | 204; other sessions revoked | 422 `INVALID_CURRENT_PASSWORD` |
| A12 | `DELETE /api/v1/me` | session (owner) | `{password}` | 202; account scheduled for deletion (30 days), provider tokens revoked immediately | — |

Email change is out of MVP scope (requires re-verification flow).

## 5. Onboarding, preferences, data source, entitlements

| # | Method & path | Auth | Request | Response | Validation / errors |
|---|---|---|---|---|---|
| O1 | `GET /api/v1/onboarding` | session | — | `{status, flow_version, current_step, completed_steps, skipped_steps, steps: [{id, optional, completed, skipped}]}` | — |
| O2 | `PUT /api/v1/onboarding/steps/{step}` | session | Step payload (below) | 200 onboarding state | 422 per field; 409 `STEP_OUT_OF_ORDER` only if a required earlier step is missing |
| O3 | `POST /api/v1/onboarding/steps/{step}/skip` | session | — | 200 state | 422 `STEP_NOT_SKIPPABLE` for required steps |
| O4 | `POST /api/v1/onboarding/complete` | session | — | 200 state `COMPLETED` | 422 `ONBOARDING_INCOMPLETE` listing required steps |

Step payloads (`{step}` lower-case id):

| Step | Payload | Persists to |
|---|---|---|
| `welcome` | `{}` | onboarding_progress |
| `experience` | `{experience_level: "NEW"|"INTERMEDIATE"|"ADVANCED"}` | user_profiles |
| `style` | `{trading_styles: ["SWING","POSITIONAL","BREAKOUT","PULLBACK"] (1–4)}` | trading_preferences |
| `universe` (optional) | `{universe_code: "NIFTY500"|"NIFTY50"|"NIFTY100"|"NIFTY200"|"NIFTYMIDCAP150"}` | trading_preferences |
| `data_source` | `{mode: "DEMO"}` or `{mode: "PERSONAL", provider: "ZERODHA_KITE"}` (PERSONAL only records intent; connection is I1–I3) | data_source_selections |
| `risk` (optional) | `{trading_capital, risk_per_trade_pct, max_open_positions}` | risk_profiles (new version) |

| # | Method & path | Auth | Request | Response | Validation / errors |
|---|---|---|---|---|---|
| P1 | `GET /api/v1/preferences/trading` | session | — | `{trading_styles, default_timeframe, universe_code, direction_preference, notification_settings}` | — |
| P2 | `PUT /api/v1/preferences/trading` | session | same shape | 200 | `default_timeframe` must be `1D` in MVP (`TIMEFRAME_NOT_SUPPORTED`); direction enum |
| P3 | `GET /api/v1/risk-profile` | session | — | `{version, trading_capital, risk_per_trade_pct, max_position_value, daily_loss_limit_pct, max_consecutive_losses, max_open_positions, max_open_risk_pct, min_rr, max_entry_gap_pct, ruleset_bounds: {...}}` | — |
| P4 | `PUT /api/v1/risk-profile` | session | same fields (all required except the two overrides) | 201 new version | ranges from TRD-01 §6 (`pa-intraday`); `min_rr` ≥ ruleset (`MIN_RR_BELOW_RULESET`); `max_entry_gap_pct` ≤ ruleset |
| P5 | `GET /api/v1/data-sources` | session | — | `[{id, mode, provider, name, status, selectable, reason_if_not}]` (global entitled sources + own personal sources) | — |
| P6 | `PUT /api/v1/data-source-selection` | session (OWNER/ADMIN) | `{data_source_id}` | 200 | 403 `ENTITLEMENT_REQUIRED`; 404 for other tenant's personal source; 422 `DATA_SOURCE_NOT_READY` if personal source has no completed ingestion |
| P7 | `GET /api/v1/entitlements` | session | — | `{plan_code, status, valid_to, features, usage_today: {ai_explanations, backtests}}` | — |

## 6. Instruments, universes, market data

| # | Method & path | Auth | Request | Response | Notes / errors |
|---|---|---|---|---|---|
| M1 | `GET /api/v1/instruments` | session | `?q=&universe=NIFTY500&segment=EQ&limit&cursor` | `[Instrument]` paginated | `q` matches symbol prefix or name substring (min 1 char); used by global search |
| M2 | `GET /api/v1/instruments/{symbol}` | session | — | `Instrument` + `{universes: [code]}` | 404 |
| M3 | `GET /api/v1/universes` | session | — | `[{code, name, member_count, is_demo}]` | — |
| M4 | `GET /api/v1/universes/{code}/members` | session | `?as_of=YYYY-MM-DD&limit&cursor` | `[Instrument]` point-in-time | default `as_of` = latest trading day |
| M5 | `GET /api/v1/instruments/{symbol}/candles` | session | `?interval=5m|15m|1D&from&to` (timestamps or dates; max 2,000 bars) | `{candles: [Candle], interval, adjusted: bool}` + `meta.data_mode/as_of/next_bar_close` | from selected data source; only completed bars; 422 `RANGE_TOO_LARGE`; `1m` reserved |
| M6 | `GET /api/v1/market/indices` | session | — | `[{symbol, name, value, change, change_pct, trend: [Price] (last 30 closes)}]` | requires index candles in data source |
| M7 | `GET /api/v1/market/session` | session | — | `{exchange: "NSE", state: "PRE_OPEN"|"OPEN"|"CLOSED", is_trading_day, session_open, session_close, entry_cutoff_at, session_end_exit_at, next_open, last_trading_day, last_bar_close, calendar_verified}` | from `market_calendar`; `calendar_verified = false` while the holiday list is not loaded |
| M8 | `POST /api/v1/market-data/sync` | session (OWNER), PERSONAL source only | `{kind: "DAILY_CANDLES"|"BACKFILL", from?, to?}` | 202 `{ingestion_run_id}` | 409 `INGESTION_IN_PROGRESS`; 409 `PROVIDER_NOT_CONNECTED`; 403 for DEMO/LICENSED (system-managed) |
| M9 | `GET /api/v1/market-data/ingestion-runs` | session | `?limit&cursor` | `[{id, kind, status, trade_date, range, counts, quality_issue_count, started_at, finished_at}]` for the selected source | — |
| M10 | `GET /api/v1/market-data/ingestion-runs/{id}` | session | — | run + `quality_issues: [...]` (first 100) | — |

## 7. Scanner, analysis, setups, AI explanations

| # | Method & path | Auth | Request | Response | Notes / errors |
|---|---|---|---|---|---|
| N1 | `GET /api/v1/scanner` | session | `?universe=NIFTY50&watchlist=&q=&htf_state=BULLISH&structure=BULLISH&signal=BUY_WATCH&setup_type=&setup_status=&direction=LONG&min_rr=2&min_score=60&near=SUPPORT&sort=-quality_score&limit&cursor` | `[ScannerRow]` + `meta: {batch: {id, as_of, status, instruments_total, instruments_completed, instruments_late}, data_mode, next_bar_close}` | Personal mode: live engine call, no batch (see §0); otherwise the batch description below applies to the persisted model (ADR-016 defers it). |
| N2 | `GET /api/v1/scanner/export` | session | same filters | `text/csv` | Respects data licensing: disabled (403 `EXPORT_NOT_PERMITTED`) for LICENSED sources unless entitlement allows |
| N3 | `GET /api/v1/dashboard/summary` | session | — | `{session: {state, entry_cutoff_at, session_end_exit_at, last_bar_close}, books: {PAPER: RiskToday, ACTUAL: RiskToday}, open_positions, stocks_scanned, active_setups, awaiting_confirmation, active_trade_plans, top_setups: [ScannerRow] (6), upcoming_triggers: [{symbol, setup_id, condition, trigger, distance_pct, signal, valid_until}], recent_signals: [{symbol, analysis_run_id, signal, signal_at}]}` (RiskToday = R2 shape) | `active_setups` = LONG setups with status ∈ {FORMING, AWAITING_CONFIRMATION, ENTRY_CONFIRMED-on-as_of} |
| N4 | `GET /api/v1/activity` | session | `?limit&cursor` | `[{id, kind: "SETUP"|"PLAN"|"TRIGGER"|"INVALIDATED"|"JOURNAL"|"WATCHLIST", title, detail, at, entity}]` | Derived from notifications + audit log (user-facing subset) |
| N5 | `GET /api/v1/analysis/{symbol}` | session | `?as_of=<timestamp>&include=candles` | `AnalysisRun` (latest for the selected source, or the run at that 5m close) | 404 `NOT_FOUND` (unknown symbol) or `NO_BARS_FOR_SYMBOL`; 503 `ENGINE_UNAVAILABLE`; status `INSUFFICIENT_HISTORY` returned as 200 with empty setups and `signal.state = NO_TRADE`. **Personal mode (ADR-016):** served live from the engine; `inputs` and `liquidity` are empty, zone `distance_pct` is null, ids are deterministic UUIDv5 values of the content, `include=candles,candles_15m,candles_1d` returns the session's closed 5m and 15m bars and up to 60 prior daily bars |
| N6 | `POST /api/v1/analysis/{symbol}/refresh` | session (rate `analysis-refresh`) | — | 200 `AnalysisRun` if snapshot unchanged (idempotent) or computed within 2 s; else 202 `{job_id}` | Uses latest ingested candles; never fetches intraday |
| N7 | `GET /api/v1/analysis-runs/{id}` | session | `?include=candles` | `AnalysisRun` (immutable) | 404 if run's data source not accessible |
| N8 | `GET /api/v1/analysis-runs/{id}/structure` | session | — | `{state, transition_direction, protected_low, protected_high, swings, events}` | |
| N9 | `GET /api/v1/analysis-runs/{id}/zones` | session | — | `{zones, liquidity, nearest_support, nearest_resistance}` | |
| N10 | `GET /api/v1/analysis-runs/{id}/setups` | session | `?direction=` | `[Setup]` | |
| N11 | `GET /api/v1/setups/{id}` | session | — | `Setup` + `{analysis_run_id, instrument, history: [{as_of, status}] (same setup_key)}` | |
| N12 | `GET /api/v1/rulesets/current` | session | — | `{code, version, validation_status, parameters, score_version}` | Public transparency of rules |
| N13 | `POST /api/v1/analysis-runs/{id}/explanations` | session (rate `ai`) | `{setup_id?: uuid}` | 200 `Explanation` (cached) or 202 `{job_id}` | 403 `ENTITLEMENT_REQUIRED`; 429 `QUOTA_EXCEEDED`; LLM failure ⇒ `status: FALLBACK` with template text (never 5xx) |
| N14 | `POST /api/v1/analysis-runs/{id}/questions` | session (rate `ai`) | `{question: string 3–500 chars, setup_id?}` | 202 `{job_id}` → `Explanation` | Off-topic or calculation requests answered with refusal template (ARC-07 §7) |
| N15 | `GET /api/v1/explanations/{id}` | session | — | `Explanation = {id, kind, status, analysis_run_id, setup_id, question, answer: {summary, points: [{text, evidence_refs}], uncertainty, disclaimer}, model, prompt_version, created_at}` | |
| N16 | `GET /api/v1/jobs/{id}` | session | — | `{id, kind, status: "QUEUED"|"RUNNING"|"COMPLETED"|"FAILED", progress_pct, result: {type, id}|null, error_code}` | Job status stored in Redis (TTL 24 h); durable results are the referenced resources |

## 8. Risk and trade plans

### 8.1 Risk

**R1** `POST /api/v1/risk/calculate` — Auth: session. Pure calculation, persists nothing.

Request (the TRD-05 §3.1 example):

```json
{ "instrument": "RELIANCE", "direction": "LONG", "book": "PAPER",
  "entry": "1498.10", "stop": "1485.25", "target": "1529.00",
  "risk_per_trade_pct": "0.5" }
```

`risk_per_trade_pct` optional (defaults to the current risk profile). Laravel adds the risk profile, the book's account state (TRD-05 §8.1) and the session clock before calling the engine. Response 200:

```json
{ "data": {
  "quantity": 33, "risk_budget": "500.00", "risk_per_share": "12.85",
  "actual_risk": "424.05", "actual_risk_pct": "0.4241", "position_value": "49437.30",
  "rr": "2.4047", "rr_after_costs": "2.2800", "est_round_trip_costs": "53.08",
  "binding_constraint": "POSITION_CAP",
  "constraints": { "qty_risk": 38, "qty_capital": 66, "qty_position_cap": 33, "qty_open_risk": 77, "qty_daily_loss": 116 },
  "account_state": { "realised_net_pnl_today": "0.00", "open_risk": "0.00", "losing_streak": 0,
                     "remaining_daily_loss": "1500.00", "blocked_reason": null },
  "rounding": { "entry": "1498.10", "stop": "1485.25", "target": "1529.00" },
  "warnings": [], "errors": [], "ruleset_version": "pa-intraday 0.1.0" },
  "meta": { "request_id": "01JD…" } }
```

Errors (422, codes from [TRD-05](../trading/05_RISK_MANAGEMENT_RULES.md)): `SHORT_NOT_SUPPORTED`, `STOP_NOT_BELOW_ENTRY`, `STOP_TOO_TIGHT`, `STOP_TOO_WIDE`, `TARGET_NOT_ABOVE_ENTRY`, `RR_BELOW_MINIMUM`, `RISK_BUDGET_TOO_SMALL`, `INSUFFICIENT_CAPITAL`, `POSITION_CAP`, `OPEN_RISK_LIMIT_REACHED`, `DAILY_LOSS_LIMIT_REACHED`, `MAX_CONSECUTIVE_LOSSES_REACHED`, `MAX_POSITIONS_REACHED`, `ENTRY_CUTOFF_PASSED`, `SESSION_CLOSED`. 503 `ENGINE_UNAVAILABLE`.

**R2** `GET /api/v1/risk/today` — Auth: session. `?book=PAPER|ACTUAL` (required). Account state of the book for the current session (TRD-05 §8.1), computed from the trade tables: `{book, session_date, realised_net_pnl_today, open_risk, losing_streak, open_positions, daily_loss_limit, remaining_daily_loss, max_consecutive_losses, max_open_positions, blocked_reason|null, entry_cutoff_at, session_end_exit_at}`. 422 `BOOK_REQUIRED`.

### 8.2 Trade plans

| # | Method & path | Auth | Request | Response | Validation / errors |
|---|---|---|---|---|---|
| T1 | `GET /api/v1/trade-plans` | session | `?status=PENDING,TRIGGERED&symbol=&sort=-created_at&limit&cursor` | `[TradePlan]` + `meta.totals: {open_count, pending_count, planned_risk, avg_rr_open}` | — |
| T2 | `POST /api/v1/trade-plans` | session, `Idempotency-Key` | `{analysis_run_id, setup_id?, instrument, entry?, stop?, target?, risk_per_trade_pct?, paper_tracking?: true, note?}` — levels default to the setup's engine levels; manual plans require all three levels and no `setup_id` | 201 `TradePlan` | Server calls engine risk calc; **client-supplied quantity is not accepted**. Errors: risk codes (§8.1), `SETUP_NOT_ACTIONABLE` (SHORT/informational/rr_below_min), `ENTRY_WINDOW_ELAPSED`, `SETUP_TERMINAL` (invalidated/expired), `ANALYSIS_STALE` (run not the latest for that instrument) |
| T3 | `GET /api/v1/trade-plans/{id}` | session | — | `TradePlan` + `{events: [...audit subset]}` | 404 |
| T4 | `PATCH /api/v1/trade-plans/{id}` | session | `{lock_version, entry?, stop?, target?, note?, paper_tracking?}` | 200 `TradePlan` (quantity recomputed) | 409 `PLAN_NOT_EDITABLE` unless `PENDING`; 409 `STALE_VERSION`; risk codes |
| T5 | `POST /api/v1/trade-plans/{id}/cancel` | session | `{reason?}` | 200 | 409 unless `PENDING`/`TRIGGERED` |

There is deliberately **no** endpoint that places, modifies or cancels broker orders (constraint C-02, [ADR-010](../adr/ADR-010-MANUAL-TRADE-EXECUTION-MVP.md)).

## 9. Watchlists

| # | Method & path | Auth | Request | Response | Validation / errors |
|---|---|---|---|---|---|
| W1 | `GET /api/v1/watchlists` | session | — | `[{id, name, sort_order, items: [{symbol, added_at}]}]` | — |
| W2 | `POST /api/v1/watchlists` | session | `{name}` | 201 | name 1–60, unique per user (`NAME_TAKEN`); max per entitlement (`ENTITLEMENT_LIMIT`) |
| W3 | `PATCH /api/v1/watchlists/{id}` | session | `{name?, sort_order?}` | 200 | same |
| W4 | `DELETE /api/v1/watchlists/{id}` | session | — | 204 | 409 `LAST_WATCHLIST` (UI rule: at least one list remains) |
| W5 | `PUT /api/v1/watchlists/{id}/items/{symbol}` | session | — | 200 (idempotent add) | 404 unknown symbol; max 200 items |
| W6 | `DELETE /api/v1/watchlists/{id}/items/{symbol}` | session | — | 204 | — |

Watchlist rows with analysis are obtained via `GET /api/v1/scanner?watchlist={id}` (scanner accepts `watchlist` filter).

## 10. Paper trading, actual trades, portfolio

| # | Method & path | Auth | Request | Response | Validation / errors |
|---|---|---|---|---|---|
| X1 | `GET /api/v1/paper/account` | session | — | `{starting_capital, cash, invested, open_heat, realized_pnl, unrealized_pnl, reset_generation, as_of}` | — |
| X2 | `POST /api/v1/paper/account/reset` | session | `{starting_capital, confirm: true}` | 200 | archives prior generation; ≥ 10,000 |
| X3 | `GET /api/v1/paper/trades` | session | `?status=OPEN|CLOSED&limit&cursor` | `[PaperTrade]` | — |
| X4 | `GET /api/v1/paper/trades/{id}` | session | — | `PaperTrade + events` | — |
| X5 | `PATCH /api/v1/paper/trades/{id}/stop` | session | `{stop}` | 200 | `STOP_CAN_ONLY_MOVE_UP`; must be < last close |
| X6 | `POST /api/v1/paper/trades/{id}/close` | session | — | 202 (exit at next open) | 409 if closed or exit pending |
| X7 | `GET /api/v1/actual-trades` | session | `?status&limit&cursor` | `[ActualTrade]` | — |
| X8 | `POST /api/v1/actual-trades` | session, `Idempotency-Key` | `{instrument, trade_plan_id?, fill: {side: "BUY", quantity, price, executed_at, broker_order_id?, fees?}, notes?}` | 201 | price > 0 with at most two decimals; `executed_at` not in the future (trading-day check is a warning only, not built); `trade_plan_id` must be the user's (404 otherwise). The first call creates the owner's personal tenant. A repeated `Idempotency-Key` returns the same trade for 24 h |
| X9 | `POST /api/v1/actual-trades/{id}/fills` | session, `Idempotency-Key` | `{side, quantity, price, executed_at, broker_order_id?, broker_trade_id?, fees?}` | 201 | 422 `OVERSELL_NOT_ALLOWED`. The trade row (quantity, average cost, realised P&L gross of charges, charges, status) is recomputed from all fills, chronologically, in one transaction |
| X11 | `GET /api/v1/positions/live` | session | `?book=PAPER|ACTUAL` (required) | `[{position_id, symbol, quantity, entry_price, entry_at, current_price, price_at, unrealised_pnl, stop, target, distance_to_stop_pct, distance_to_target_pct, signal: "HOLD"|"EXIT"}]` + `meta.data_mode` | Current prices come from the current-price cache (ENG-05 §12) and are labelled with `price_at`; they never change analysis. 422 `BOOK_REQUIRED`. **Personal mode:** the price is the latest stored 5m close; `stop`/`target` come from the linked plan (null without one); `signal` is null until the engine evaluates open positions; the PAPER book lists nothing yet |
| X10 | `GET /api/v1/portfolio` | session | `?book=PAPER|ACTUAL` (required) | `{summary: {capital, invested, cash, unrealized_pnl, realized_pnl, open_risk, max_risk_per_trade_pct}, positions: [{symbol, quantity, avg_price, ltp, stop, plan_id, signal: "HOLD"|"EXIT", unrealized_pnl}], allocation: [{label, value}], exposure: {...}}` + `meta.data_mode` | 422 `BOOK_REQUIRED` — books are never mixed |

`PaperTrade = {id, trade_plan_id, instrument, status, entry_date, entry_price, quantity, initial_stop, current_stop, target, exit_date, exit_price, exit_reason, gross_pnl, charges, net_pnl, r_multiple, signal}`. `ActualTrade = {id, instrument, trade_plan_id, status, quantity_open, avg_entry_price, avg_exit_price, realized_pnl, charges, fills: [...]}`.

## 11. Journal

| # | Method & path | Auth | Request | Response | Notes |
|---|---|---|---|---|---|
| J1 | `GET /api/v1/journal` | session | `?kind=PAPER|ACTUAL&q=&outcome=WIN|LOSS|BREAKEVEN&setup_type=&followed_plan=&from&to&limit&cursor` | `[JournalEntry]` — `{id, kind, status, trade: {symbol, setup_type, direction, entry_date, exit_date, entry_price, exit_price, quantity, net_pnl, r_multiple, outcome}, followed_plan, followed_plan_system, notes, tags, emotions, mistakes, lessons, rating}` | `kind` defaults to `PAPER` |
| J2 | `GET /api/v1/journal/{id}` | session | — | `JournalEntry` | |
| J3 | `PATCH /api/v1/journal/{id}` | session | `{notes?, tags?, emotions?, mistakes?, lessons?, rating?, followed_plan?, status?}` | 200 | tags ≤ 20 × 40 chars |
| J4 | `GET /api/v1/journal/stats` | session | same filters as J1 | `{trades, win_rate, profit_factor, avg_r, net_pnl, plan_adherence_pct}` | Computed server-side (today computed client-side in `features/journal/stats.ts`) |

Manual journal entries without a trade are out of scope (UI currently toasts "coming next phase").

## 12. Backtesting

| # | Method & path | Auth | Request | Response | Validation / errors |
|---|---|---|---|---|---|
| B1 | `GET /api/v1/backtests/strategies` | session | — | `[{setup_type, name, description}]` — the four canonical setup types | — |
| B2 | `POST /api/v1/backtests` | session (rate `backtest-create`), `Idempotency-Key` | `{setup_types: [..], instruments: {kind: "SINGLE"|"UNIVERSE"|"WATCHLIST", symbol?, universe_code?, watchlist_id?}, date_from, date_to, starting_capital, risk_per_trade_pct, sizing_mode?: "FIXED", slippage_pct?}` | 202 `{id, status: "QUEUED"}` | date_from < date_to; span ≥ 1 year; capital ≥ 10,000; risk 0.1–5; data source must have history (`INSUFFICIENT_HISTORY`); quota `QUOTA_EXCEEDED`; DEMO source allowed but results flagged `data_mode = DEMO` |
| B3 | `GET /api/v1/backtests` | session | `?limit&cursor` | `[{id, status, config, metrics_summary, flags, queued_at, finished_at}]` | — |
| B4 | `GET /api/v1/backtests/{id}` | session | — | `{id, status, progress_pct, config, ruleset_version, engine_version, cost_schedule_version, metrics, equity_curve, flags, error_code}` | — |
| B5 | `GET /api/v1/backtests/{id}/trades` | session | `?outcome=FILLED|SKIPPED&limit&cursor` | `[BacktestTrade]` | — |
| B6 | `POST /api/v1/backtests/{id}/cancel` | session | — | 202 | 409 if terminal |

## 13. Zerodha connection

| # | Method & path | Auth | Request | Response | Validation / errors |
|---|---|---|---|---|---|
| I1 | `POST /api/v1/integrations/zerodha/connect` | session (OWNER, rate `integration`) | — | 200 `{login_url}` (Kite login URL with `api_key` and a signed `state` stored hashed) | 403 `ENTITLEMENT_REQUIRED`; 503 `PROVIDER_NOT_CONFIGURED` if deployment lacks Kite app credentials |
| I2 | `GET /api/v1/integrations/zerodha/callback?request_token=…&status=success&state=…` | session (browser redirect) | — | 302 → `/settings?section=broker&result=connected` or `result=error&code=…` | Validates `state` (CSRF); exchanges `request_token` server-side for access token; `request_token` never stored; errors `STATE_MISMATCH`, `PROVIDER_AUTH_FAILED` |
| I3 | `GET /api/v1/integrations/zerodha` | session | — | `{status, provider_user_id_masked, token_expires_at, last_connected_at, last_error_code, data_source_id}` — **never** returns tokens | — |
| I4 | `DELETE /api/v1/integrations/zerodha` | session (OWNER) | — | 204; token deleted (and invalidated at provider where supported), personal data source disabled | Personal candles retained per [OPS-04](../operations/04_DATA_RETENTION_AND_BACKUP.md) unless user requests deletion |

## 14. Notifications

| # | Method & path | Auth | Request | Response |
|---|---|---|---|---|
| Z1 | `GET /api/v1/notifications` | session | `?unread=true&limit&cursor` | `[{id, type, title, body, entity, read, created_at}]` + `meta.unread_count` |
| Z2 | `POST /api/v1/notifications/{id}/read` | session | — | 204 |
| Z3 | `POST /api/v1/notifications/read-all` | session | — | 204 |

Notification preferences are part of `PUT /api/v1/preferences/trading` (`notification_settings`). Email/push delivery channels beyond in-app are M9+.

## 15. Authorization matrix (summary)

Full matrix in [ARC-06 §3](06_SECURITY_ARCHITECTURE.md). In MVP every tenant has one user with role `OWNER`; `VIEWER` can call all `GET` endpoints of the tenant; `MEMBER` can manage own plans/trades/journal/watchlists; only `OWNER`/`ADMIN` can change data source, integrations and entitlements.

## 16. Open questions

| ID | Question |
|---|---|
| OQ-API-01 | Should `/analysis/{symbol}` embed candles by default (simpler frontend) or always require `include=candles` (smaller payloads)? Current choice: opt-in. |
| OQ-API-02 | CSV export rights under each data mode — legal review required (OPS-05). |
| OQ-API-03 | SSE/websocket channel for job progress and notifications (post-MVP). |
