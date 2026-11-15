# Glossary

| Field | Value |
|---|---|
| Version | 0.1.0 |
| Status | Current |
| Owner | Documentation owner |
| Last updated | 2026-11-15 |

Terms are grouped by domain. Where a term has a precise rule, the definition links to its authoritative document.

## Product

| Term | Definition |
|---|---|
| Decision support | The product informs the trader's decision; it does not make or execute it. |
| Demo mode | Use of the `DEMO` data source: synthetic sample data, always badged, never live. |
| Personal mode | Use of a `PERSONAL` data source fetched through the user's own authorised broker connection, visible only to that tenant. |
| Licensed (SaaS) mode | Use of a `LICENSED` data source under a commercial redistribution licence (future). |
| Data mode | `DEMO` / `PERSONAL` / `LICENSED`; returned as `meta.data_mode` with all market data ([ADR-011](adr/ADR-011-DATA-MODES-AND-TENANT-ISOLATION.md)). |
| Universe | Set of instruments analysed; product universe is NIFTY 500; subsets are NIFTY 50/100/200/MIDCAP 150. |
| Watchlist | User-curated list of instruments. |
| Trade plan | A user's proposal (entry, stop, target, quantity) derived from a setup or entered manually. Not an order. |
| Paper trade | A simulated position created from a plan by the paper engine. |
| Actual trade | A user-recorded real execution done on the broker's platform. |
| Book | Paper or Actual portfolio; never combined. |
| Journal entry | Reflection attached to a closed paper or actual trade. |
| Entitlement | Plan-based feature/quota permissions for a tenant. |
| Release gate (G1/G2/G3) | Conditions for personal MVP, private beta, SaaS ([PRD-02 §12](product/02_BRD.md#12-release-gates)). |

## Trading

| Term | Definition |
|---|---|
| Price action | Analysis using only OHLCV of closed candles; no indicators. |
| Candle (bar) | Daily OHLCV record for a trading session. |
| Closed candle | A daily bar whose official close has been ingested. |
| Swing high / swing low (pivot) | Bar whose high (low) is extreme relative to `L` bars left and `R` bars right ([TRD-02 §3](trading/02_MARKET_STRUCTURE_RULES.md#3-swing-pivots)). |
| Confirmed pivot | A pivot whose `R` right-side bars have closed; available from `confirmed_at_index = i + R`. |
| HH / HL / LH / LL | Higher high, higher low, lower high, lower low — labels comparing a pivot to the previous same-kind pivot. |
| EQH / EQL | Equal high / equal low within `structure.equal_level_tolerance_pct`. |
| Structure state | `BULLISH`, `BEARISH`, `SIDEWAYS`, `TRANSITION` ([TRD-02 §5](trading/02_MARKET_STRUCTURE_RULES.md#5-structure-state)). |
| BOS (Break of Structure) | Close beyond the last swing high (bullish) or low (bearish) plus buffer, in the trend direction. |
| CHoCH (Change of Character) | Close beyond the protected low (in bullish) or protected high (in bearish) plus buffer; signals possible reversal. |
| Protected low / high | The swing low (high) the current trend must hold; set at each BOS. |
| Wick breach | Price trades beyond a level intrabar but the close does not qualify as a break. |
| Zone (support/resistance) | Price band built by clustering confirmed pivots ([TRD-03](trading/03_SUPPORT_RESISTANCE_RULES.md)). |
| Touch | A pivot in, or a reacting visit to, a zone. |
| Role reversal (flip) | Broken resistance acting as support, or vice versa. |
| Liquidity pool | Equal highs/lows where stops likely cluster. |
| Liquidity sweep | Wick beyond a liquidity level followed by a reclaim close. |
| Setup | One of `BREAKOUT_RETEST`, `SUPPORT_REJECTION`, `TREND_PULLBACK`, `LIQUIDITY_SWEEP_REVERSAL` ([TRD-04](trading/04_SETUP_DETECTION_RULES.md)). |
| Setup status | `FORMING`, `AWAITING_CONFIRMATION`, `ENTRY_CONFIRMED`, `INVALIDATED`, `EXPIRED`. |
| Trigger price | Level a close must exceed (plus buffer) to confirm entry. |
| Entry confirmation | Close above trigger × (1 + breakout buffer). |
| Entry window | The next session's open after confirmation. |
| Invalidation | Condition that terminates a setup before entry. |
| Expiry | Setup termination after `setup.expiry_bars` without confirmation. |
| Signal state | Trader-facing state: `NO_TRADE`, `BUY_WATCH`, `ENTRY_CONFIRMED`, `HOLD`, `EXIT`. |
| PAQS | Price Action Quality Score (0–100): rule-conformance score, **not** a probability ([TRD-04 §9](trading/04_SETUP_DETECTION_RULES.md#9-price-action-quality-score-paqs)). |
| R / R-multiple | Profit or loss expressed in units of initial risk. |
| R:R (risk/reward) | (target − entry) / (entry − stop). |
| Risk budget | capital × risk per trade %. |
| Portfolio heat | Sum of open risk to stops across open positions. |
| Gap rule | Next-open fill constraints ([TRD-05 §7](trading/05_RISK_MANAGEMENT_RULES.md#7-entry-gap-rules)). |
| Same-candle collision | A bar touching both stop and target; resolved as stop. |
| Look-ahead bias | Using information not available at decision time. |
| Survivorship bias | Testing only on instruments that survived to today. |
| Point-in-time universe | Universe membership as it was on each historical date. |
| In-sample / out-of-sample / holdout | Data segments for exploration, validation and final check. |
| Tick size | Minimum price increment for an instrument (from instrument master). |
| Corporate action | Split, bonus, dividend, rights, merger, demerger, symbol change. |
| Long / short | Buy-side / sell-side direction; short is informational only in MVP. |

## Architecture and data

| Term | Definition |
|---|---|
| Modular monolith | Single deployable with enforced internal module boundaries ([ADR-004](adr/ADR-004-MODULAR-MONOLITH.md)). |
| Engine | Python service + workers implementing deterministic analysis. |
| Domain library | Pure, I/O-free Python package `app/domain`. |
| Ruleset / ruleset version | Immutable set of rule parameters, e.g. `pa-core 0.1.0`. |
| Candle snapshot | Immutable, content-hashed set of candles used as analysis input. |
| Analysis run | Immutable result of analysing one snapshot with one ruleset (the "analysis snapshot"). |
| Analysis batch | Group of analysis runs for a universe and date. |
| Setup key | Stable identifier of the same setup across daily runs. |
| Data source | Unit of market-data licensing/isolation (`data_sources`). |
| Provider adapter | Implementation of `MarketDataProvider` for one vendor/broker. |
| Ingestion run | One execution of a data-ingestion job. |
| Tenant | Isolation boundary owning user data. |
| JIT token fetch | Worker retrieves a broker token from Laravel just before use, never persisting it. |
| Service token | Shared bearer secret authenticating internal service calls. |
| Entitlement gate | Check that a tenant's plan allows a feature. |
| RLS | PostgreSQL Row-Level Security (planned for SaaS readiness). |
| Fallback (AI) | Deterministic template explanation used when the LLM fails validation or is unavailable. |
| Grounding | Requirement that every number/reference in LLM output exists in the supplied context. |

## Engineering

| Term | Definition |
|---|---|
| GitHub Flow | Branching model with `main` + short-lived branches merged by PR. |
| Conventional Commits | Commit/PR-title format `type(scope): summary`. |
| `ci-gate` | Single required status check aggregating component CI results. |
| Reusable workflow | GitHub Actions workflow invoked via `workflow_call`. |
| GHCR | GitHub Container Registry. |
| GitHub Environment | Deployment target with protection rules and scoped secrets. |
| Golden test | Test comparing output to a committed expected file. |
| Property-based test | Test asserting invariants over generated inputs (Hypothesis). |
| Contract test | Test validating payloads against OpenAPI / JSON Schema. |
| Expand → contract | Migration pattern keeping schema backward compatible across releases. |
| RPO / RTO | Recovery point / time objectives. |
