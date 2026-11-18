# UI/UX Specification

| Field | Value |
|---|---|
| Document ID | PRD-07 |
| Version | 0.3.0 |
| Status | Reflects implemented frontend (Phase 1, daily mock data) + required additions, revised for intraday (ADR-014) |
| Owner | Product Manager / Frontend Lead |
| Last updated | 2026-11-17 |
| Related | [design-standards](../design-standards.md) · [ADR-013](../adr/ADR-013-DESIGN-STANDARDS.md) · [ENG-02 Frontend architecture](../engineering/02_FRONTEND_ARCHITECTURE.md) · [PRD-03 §6 Screens](03_PRD.md#6-screen-level-requirements) · `frontend/src/styles/tokens.css` · `frontend/src/lib/labels.ts` |

## 1. Purpose

Documents the product-level interaction rules so backend integration preserves them, and lists the UI additions the specification requires. Revised for the personal intraday direction ([ADR-014](../adr/ADR-014-PERSONAL-INTRADAY-WORKSTATION.md)): the existing screens and components stay; their data, time handling and some widgets change (milestone I6). Visual rules (layout, spacing, radius, type, colour, depth, states, accessibility) are governed by [docs/design-standards.md](../design-standards.md) ([ADR-013](../adr/ADR-013-DESIGN-STANDARDS.md)); their implementation is in [ENG-02 §11](../engineering/02_FRONTEND_ARCHITECTURE.md#11-design-system).

## 2. Design principles (as implemented)

| ID | Principle | Implementation |
|---|---|---|
| UX-01 | Dark-first, data-dense, calm trading UI | Dark default; light and system modes fully supported (`data-theme`, ENG-02 §11.2) |
| UX-02 | Never a bare BUY/SELL | `SignalBadge` uses distinct shape + icon + colour + tooltip per state |
| UX-03 | Sample data is always labelled | `SampleDataBadge`, market-status tooltip, settings "Sample data — Active" |
| UX-04 | Numbers are readable and stable | Tabular numerals everywhere, condensed figure face (`font-stat`), en-IN formatting, lakh/crore compaction |
| UX-05 | No-trade is normal | `NO TRADE` described as "Staying flat is a valid decision." |
| UX-06 | Explain before acting | Evidence panel "Why is this setup being considered?", entry conditions, invalidation |
| UX-07 | Plans are proposals | Plan dialog: "Creates a proposed plan for review. It does not place an order with any broker." |
| UX-08 | Freshness is always visible (new) | Every market-data screen shows the last completed bar time (IST) next to the data-mode badge; "Delayed" when it is more than one bar old during the session |
| UX-09 | The session is the frame (new) | A session clock shows time to the entry cutoff and to the session-end exit; after the cutoff, plan actions are disabled with the reason |
| UX-10 | Limits block visibly (new) | When an account limit is reached, a banner names the limit and the book, and plan actions are disabled — never a silent failure |

## 3. Design tokens

Token vocabulary and values follow [design-standards §6 and §12](../design-standards.md#12-token-template). PriceAction brand values, domain extensions (`bull`/`bear`, price-action annotation tokens) and theme conventions are in [ENG-02 §11](../engineering/02_FRONTEND_ARCHITECTURE.md#11-design-system). Components never use raw colour values.

Tones (`lib/colors.ts`): status `success`, `warning`, `destructive`, `info`, `neutral`; market `bull`, `bear`. The brand accent is reserved for the primary action, the active navigation row, a switch that is on and the current selection.

## 4. Signal and status presentation

| State | Label | Tone | Shape/icon |
|---|---|---|---|
| `BUY_WATCH` | BUY WATCH | warning | dashed outline, Eye |
| `ENTRY_CONFIRMED` | ENTRY CONFIRMED | success | solid fill, CircleCheck |
| `HOLD` | HOLD | info | soft fill, ShieldCheck |
| `EXIT` | EXIT | destructive | soft fill + border, LogOut |
| `NO_TRADE` | NO TRADE | neutral | outline, Ban |

Setup status, structure, plan status and outcome labels/tones are centralised in `lib/labels.ts`; backend enum values map onto these keys in the HTTP adapter (vocabulary reconciliation in [TRD-04 §13](../trading/04_SETUP_DETECTION_RULES.md#13-frontend-vocabulary-reconciliation)). New labels required: setup status `EXPIRED`, plan statuses `SKIPPED`/`EXPIRED`/`FILLED`, structure `SIDEWAYS` (replaces "Range"), setup types `OPENING_RANGE_BREAKOUT`, `PREV_DAY_HIGH_BREAK`, `PREV_DAY_LOW_BREAK`, reason codes `SESSION_CUTOFF`, `SESSION_END`, `ACCOUNT_LIMIT`, `HTF_AGAINST`.

Every signal badge in the scanner and analysis panel shows its time (`signal_at`) and, for `BUY_WATCH`/`ENTRY_CONFIRMED`, a countdown to `valid_until`; an expired signal is shown as stale, never as current.

## 5. Layout and navigation

- `(auth)` group: split-screen layout with product showcase (`auth-showcase.tsx`).
- `(app)` group: `AppShell` with collapsible sidebar (persisted in localStorage `pa-sidebar`), top navigation (search, market status, notifications, user menu), breadcrumbs, mobile nav.
- Navigation groups (`lib/navigation.ts`): Overview (Dashboard) · Market (Market Scanner, Stock Analysis, Watchlists) · Trading (Trade Plans, Active Trades — the `/portfolio` route, Trading Journal, Backtesting) · System (Settings). Register and onboarding are not linked (ADR-014).
- The top navigation adds the session clock (UX-09) beside the market status.
- Global search (`global-search.tsx`) opens analysis for a symbol.

## 6. Component library (existing)

Shared design-system components (PageFrame, Panel, Card, Stat/StatGrid, FilterRow, ChoiceGroup, SectionLinks, Empty, ErrorState, skeletons) are listed in [ENG-02 §11.3](../engineering/02_FRONTEND_ARCHITECTURE.md#113-shared-components). Domain components:

| Layer | Components |
|---|---|
| `components/ui` | Button, Input/Textarea, Select, Checkbox, Switch, Tabs, ChoiceGroup, SectionLinks, FilterRow, Dropdown, Dialog, Tooltip, Toast, Panel |
| `components/layout` | AppShell, AppSidebar, TopNavigation, Breadcrumb, PageFrame/PageHeader, GlobalSearch, MobileNav, Brand, UserBadge, theme |
| `components/data` | Stat/StatGrid, PriceDisplay, MarketStatus, DataTable, StatusBadge, Badge, Empty, ErrorState, LoadingSkeleton, Sparkline, SampleDataBadge, Disclaimer |
| `components/trading` | SignalBadge, SetupCard, TradePlanCard, RiskRewardDisplay, MarketStructureBadge, PriceLevelIndicator, AnalysisPanel, StockTable, LifecycleStrip, QualityScore |
| `components/charts` | PriceChart (+ zone and BOS/CHoCH primitives), EquityChart |

## 7. Chart annotation rules

| Object | Rendering rule |
|---|---|
| Time axis (new) | Bars are placed by UTC timestamp and labelled in IST; non-session time is collapsed with a session separator line; 5m is the default view, 15m the context view, daily display only |
| Swing points | Label (HH/HL/LH/LL/EQH/EQL) above highs / below lows, only for confirmed pivots, and in replay only from their confirmation bar (no repainting) |
| Unconfirmed bars | Last `pivot.right_bars` bars visually marked "unconfirmed" (new) |
| BOS / CHoCH | Horizontal segment from level pivot to break bar, labelled; BOS dashed in the break direction (bull/bear), CHoCH dotted in `chart-choch` |
| Wick breach | Small marker, no line (new) |
| Zones | Band from the bar it formed at to the right edge; opacity by strength; flipped zones styled differently |
| Session levels (new) | PDH/PDL/PDC as labelled horizontal lines across the current session; the opening range as a shaded box over its bars, extended as two lines once complete |
| Higher-timeframe context (new) | On the 5m view, the aligned 15m state is shown as a strip above the chart; 15m swing levels drawn thinner than 5m ones |
| Levels | Entry (`chart-entry`, solid), stop (bear, dashed), target (bull, dotted) lines with price labels; trigger shown as dashed when status is AWAITING (new) |
| Short/informational setups | Levels drawn long-dashed, titled "(ref)" on the axis and "Reference only" in the panel (implemented) |

## 8. States every data screen must handle

| State | Requirement |
|---|---|
| Loading | Skeletons (`loading.tsx` exists for `(app)`) |
| Empty | `EmptyState` with next action (e.g. "First analysis runs after data import completes") |
| Error | Route-level `error.tsx` with retry and request id (`(app)` implemented with digest; request id in M7) |
| Stale data | Last bar time always visible; "Data delayed since HH:MM" banner when the latest stored bar is more than one bar old during the session |
| Demo | `SampleDataBadge` whenever `meta.data_mode = DEMO` |
| Partial batch | "Analysed 48 / 50 — 2 delayed" indicator |
| Before the first bar / after the close | "Session starts 09:15 — first analysis at 09:20" / session summary with "Closed" status |
| Auto-refresh | Polling every 10–30 s during the session (ARC-04 §2.9); refresh pauses when the tab is hidden and resumes on focus |

## 9. Required UI additions (from specification)

| ID | Addition | Screen |
|---|---|---|
| UIA-01 | `/reset-password` page | auth |
| UIA-02 | Route protection (no onboarding redirect; ADR-014) | all `(app)` |
| UIA-03 | "Explain this chart" button and AI panel — **deferred** (ADR-014) | `/analysis/[symbol]` |
| UIA-04 | Ruleset version, `as_of` time, data mode footer on analysis | `/analysis/[symbol]` |
| UIA-05 | Paper / Actual book toggle | `/portfolio`, `/journal` |
| UIA-06 | Actual trade entry form (fills) replacing "Link order" toast | `/trade-plans`, `/portfolio` |
| UIA-07 | Paper trades list with stop-up and close | `/portfolio` tab or `/paper-trades` (OQ-PRD-01) |
| UIA-08 | Backtest run history, progress, results with bias flags | `/backtesting` |
| UIA-09 | Broker connect flow states (connecting, connected, expired, error) for Kite or Groww | `/settings` |
| UIA-10 | Data health (last bar, late/missing bars, last reconciliation) and DEMO/PERSONAL switch | `/settings#data`, dashboard |
| UIA-11 | Risk and limits fields: capital, risk %, max position value (₹), daily loss limit, losing-streak limit, open positions, open risk, min R:R override | `/settings#risk` |
| UIA-12 | Error boundaries | all `(app)` |
| UIA-13 | Universe: NIFTY 50 (default watchlist); remove other universe options from the MVP | settings, watchlists |
| UIA-14 | Remove/hide Exchange (NSE/BSE) filter | `/market-scanner` |
| UIA-15 | Intraday chart time handling: timestamped `Candle`, IST labels, session separators, 5m/15m toggle replacing 1D/1W/1M (`types/market.ts` `Timeframe`, `lib/chart/aggregate.ts`, `price-chart.tsx`) | `/analysis/[symbol]` |
| UIA-16 | Session clock with cutoff and session-end countdowns (UX-09); market status from the calendar API | top navigation, dashboard |
| UIA-17 | "Today" risk panel per book and account-limit banner (UX-10); disabled plan actions with reason | dashboard, `/trade-plans`, plan dialog |
| UIA-18 | Live P&L and current price with its time for open positions; distance to stop/target; time to session-end exit | `/portfolio` (Active Trades), dashboard |
| UIA-19 | Signal time and validity countdown on badges | scanner, analysis, dashboard |
| UIA-20 | Polling data hook used by the HTTP adapter behind `DataSource` (no component calls fetch directly) | all live screens |
| UIA-21 | Journal: planned vs actual (price and time), slippage, costs, net P&L; screenshot upload (I7) | `/journal` |

## 10. Accessibility

Target WCAG 2.2 AA (design-standards requires 2.1 AA as the floor). Contrast for every token pairing in both themes was verified on 2026-11-16 ([ENG-02 §11.5](../engineering/02_FRONTEND_ARCHITECTURE.md#115-verification-2026-11-16)). Already present: visible focus ring (`ring`) on every control, arrow-key roving in choice groups and tabs, focus management in Dialog, keyboard navigation in Dropdown, aria labels on signal badges, colour-independent signal shapes. To verify in M7: chart alternative text/table view for screen readers, focus order in plan dialog, screen-reader pass on the analysis workspace.

## 11. Copy rules

- Never "buy now", "sell", "guaranteed", "accuracy", "win probability".
- Use "setup", "plan", "proposed", "reference only", "sample data".
- Disclaimer component on analysis and backtest pages: "PriceAction AI provides rule-based analysis for education and decision support. It is not investment advice."
