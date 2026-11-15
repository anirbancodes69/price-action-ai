# Documentation Status

| Field | Value |
|---|---|
| Version | 0.1.0 |
| Status | Current |
| Owner | Documentation owner |
| Last updated | 2026-11-15 |

## 1. Document status

| Document | Status | Dependencies | Open questions | Last reviewed |
|---|---|---|---|---|
| [Product Vision](product/01_PRODUCT_VISION.md) | Approved for MVP planning | — | OQ-VIS-01, OQ-VIS-02 | 2026-11-15 |
| [Business Requirements Document (BRD)](product/02_BRD.md) | Draft for owner sign-off | PRD-01 | — | 2026-11-15 |
| [Product Requirements Document (PRD)](product/03_PRD.md) | Specification ready | PRD-02, TRD-*, ARC-04 | OQ-PRD-01, OQ-PRD-02, OQ-PRD-03 | 2026-11-15 |
| [User Journeys](product/04_USER_JOURNEYS.md) | Specification ready | PRD-03, PRD-05 | — | 2026-11-15 |
| [Onboarding Specification](product/05_ONBOARDING_SPECIFICATION.md) | Specification ready | PRD-03, ARC-03, ARC-04 | OQ-ONB-01, OQ-ONB-02 | 2026-11-15 |
| [Feature Catalog](product/06_FEATURE_CATALOG.md) | Specification ready | PRD-03, ENG-01 | — | 2026-11-15 |
| [UI/UX Specification](product/07_UI_UX_SPECIFICATION.md) | Reflects implemented frontend + additions | ENG-02 | — | 2026-11-15 |
| [System Architecture](architecture/01_SYSTEM_ARCHITECTURE.md) | Specification ready | ADR-001..006 | OQ-ARC-01, OQ-ARC-02, OQ-ARC-03 | 2026-11-15 |
| [Technology Stack](architecture/02_TECHNOLOGY_STACK.md) | Specification ready (versions pinned in M0) | ARC-01 | — | 2026-11-15 |
| [Database Design](architecture/03_DATABASE_DESIGN.md) | Specification ready | ARC-01, TRD-01..07, ADR-005, ADR-011 | OQ-DB-01, OQ-DB-02, OQ-DB-03 | 2026-11-15 |
| [API Specification (Public REST API v1)](architecture/04_API_SPECIFICATION.md) | Specification ready | ARC-03, ARC-06, TRD-05 | OQ-API-01, OQ-API-02, OQ-API-03 | 2026-11-15 |
| [Data Flow](architecture/05_DATA_FLOW.md) | Specification ready | ARC-01, ARC-08, TRD-07 | — | 2026-11-15 |
| [Security Architecture](architecture/06_SECURITY_ARCHITECTURE.md) | Specification ready | ARC-01, ARC-03, ARC-08 | OQ-SEC-01, OQ-SEC-02, OQ-SEC-03 | 2026-11-15 |
| [AI and LLM Architecture](architecture/07_AI_AND_LLM_ARCHITECTURE.md) | Specification ready (provider pending) | TRD-04, ADR-009 | OQ-AI-01, OQ-AI-02, OQ-AI-03 | 2026-11-15 |
| [Integration Architecture](architecture/08_INTEGRATION_ARCHITECTURE.md) | Specification ready (Kite facts to verify) | ADR-007, ADR-011 | OQ-INT-01, OQ-INT-02, OQ-INT-03 | 2026-11-15 |
| [Trading Methodology](trading/01_TRADING_METHODOLOGY.md) | Specification ready (parameters = hypotheses) | ADR-008 | OQ-TRD-01, OQ-TRD-02, OQ-TRD-03 | 2026-11-15 |
| [Market Structure Rules](trading/02_MARKET_STRUCTURE_RULES.md) | Specification ready | TRD-01 | OQ-STR-01, OQ-STR-02, OQ-STR-03 | 2026-11-15 |
| [Support and Resistance Rules](trading/03_SUPPORT_RESISTANCE_RULES.md) | Specification ready | TRD-01, TRD-02 | OQ-SR-01, OQ-SR-02, OQ-SR-03 | 2026-11-15 |
| [Setup Detection Rules and Price Action Quality Score](trading/04_SETUP_DETECTION_RULES.md) | Specification ready | TRD-01..03, TRD-05 | OQ-SD-01, OQ-SD-02, OQ-SD-03, OQ-SD-04 | 2026-11-15 |
| [Risk Management Rules](trading/05_RISK_MANAGEMENT_RULES.md) | Specification ready | TRD-01, TRD-04 | OQ-RM-01, OQ-RM-02, OQ-RM-03, OQ-RM-04 | 2026-11-15 |
| [Backtesting Methodology](trading/06_BACKTESTING_METHODOLOGY.md) | Specification ready (costs to verify; universe history source pending) | TRD-01..05 | OQ-BT-01, OQ-BT-02, OQ-BT-03, OQ-BT-04, OQ-BT-05 | 2026-11-15 |
| [Paper Trading Specification](trading/07_PAPER_TRADING_SPECIFICATION.md) | Specification ready | TRD-04..06 | OQ-PT-01, OQ-PT-02, OQ-PT-03 | 2026-11-15 |
| [Trading Engine Validation](trading/08_TRADING_ENGINE_VALIDATION.md) | Specification ready | TRD-02..06 | — | 2026-11-15 |
| [Implementation Roadmap](engineering/01_IMPLEMENTATION_ROADMAP.md) | Specification ready | All | OQ-RD-01, OQ-RD-02 | 2026-11-15 |
| [Frontend Architecture](engineering/02_FRONTEND_ARCHITECTURE.md) | Reflects implemented code + plan | PRD-07, ARC-04 | — | 2026-11-15 |
| [Backend Architecture (Laravel)](engineering/03_BACKEND_ARCHITECTURE.md) | Specification ready | ARC-01, ARC-03, ARC-04, ARC-06 | — | 2026-11-15 |
| [Python Engine Architecture](engineering/04_PYTHON_ENGINE_ARCHITECTURE.md) | Specification ready | TRD-*, ARC-07, ARC-08 | — | 2026-11-15 |
| [Data Ingestion Specification](engineering/05_DATA_INGESTION_SPECIFICATION.md) | Specification ready | ARC-03, ARC-08 | OQ-ING-01, OQ-ING-02 | 2026-11-15 |
| [Error Handling and Logging](engineering/06_ERROR_HANDLING_AND_LOGGING.md) | Specification ready | ARC-01, ARC-04 | — | 2026-11-15 |
| [Testing Strategy](engineering/07_TESTING_STRATEGY.md) | Specification ready | TRD-08, ENG-10 | — | 2026-11-15 |
| [Development Environment](engineering/08_DEVELOPMENT_ENVIRONMENT.md) | Implemented (M0) | ARC-01, OPS-02 | — | 2026-11-15 |
| [GitHub Repository Strategy](engineering/09_GITHUB_REPOSITORY_STRATEGY.md) | Specification ready | ADR-012 | — | 2026-11-15 |
| [GitHub Actions CI/CD](engineering/10_GITHUB_ACTIONS_CI_CD.md) | Specification ready (no workflows yet) | ENG-07, ENG-09, ADR-012 | — | 2026-11-15 |
| [Branching and Release Strategy](engineering/11_BRANCHING_AND_RELEASE_STRATEGY.md) | Specification ready | ENG-09, ENG-10 | — | 2026-11-15 |
| [Code Quality and Pull Requests](engineering/12_CODE_QUALITY_AND_PULL_REQUESTS.md) | Specification ready | ENG-10, ENG-11 | — | 2026-11-15 |
| [Deployment Guide](operations/01_DEPLOYMENT_GUIDE.md) | Specification ready (no environments yet) | ENG-10, OPS-02 | OQ-OPS-01, OQ-OPS-02 | 2026-11-15 |
| [Environment Configuration](operations/02_ENVIRONMENT_CONFIGURATION.md) | Specification ready | ARC-06, ENG-08 | — | 2026-11-15 |
| [Monitoring and Observability](operations/03_MONITORING_AND_OBSERVABILITY.md) | Specification ready (tooling pending) | ENG-06 | OQ-MON-01 | 2026-11-15 |
| [Data Retention and Backup](operations/04_DATA_RETENTION_AND_BACKUP.md) | Specification ready (periods need legal confirmation) | ARC-03 | OQ-RET-01, OQ-RET-02 | 2026-11-15 |
| [Compliance and Risk Considerations](operations/05_COMPLIANCE_AND_RISK_CONSIDERATIONS.md) | Pending legal review | ADR-010, ADR-011 | OQ-CMP-01, OQ-CMP-02 | 2026-11-15 |
| [Disaster Recovery](operations/06_DISASTER_RECOVERY.md) | Specification ready | OPS-04 | — | 2026-11-15 |
| [ADR-001: Next.js App Router Frontend](adr/ADR-001-FRONTEND-ARCHITECTURE.md) | Accepted | — | — | 2026-11-15 |
| [ADR-002: Laravel as Application Backend](adr/ADR-002-LARAVEL-APPLICATION-BACKEND.md) | Accepted | — | — | 2026-11-15 |
| [ADR-003: Python as Quantitative Engine](adr/ADR-003-PYTHON-QUANTITATIVE-ENGINE.md) | Accepted | — | — | 2026-11-15 |
| [ADR-004: Modular Monolith with One Separate Quant Service](adr/ADR-004-MODULAR-MONOLITH.md) | Accepted | — | — | 2026-11-15 |
| [ADR-005: PostgreSQL as Primary Database](adr/ADR-005-POSTGRESQL-DATABASE.md) | Accepted | — | — | 2026-11-15 |
| [ADR-006: Redis for Caching, Queues, Sessions and Rate Limiting](adr/ADR-006-REDIS-CACHING-AND-QUEUES.md) | Accepted | — | — | 2026-11-15 |
| [ADR-007: Market Data Provider Abstraction](adr/ADR-007-MARKET-DATA-PROVIDER-ABSTRACTION.md) | Accepted | — | — | 2026-11-15 |
| [ADR-008: Deterministic, Versioned Trading Calculations](adr/ADR-008-DETERMINISTIC-TRADING-ENGINE.md) | Accepted | — | — | 2026-11-15 |
| [ADR-009: LLM Restricted to Explanation](adr/ADR-009-LLM-EXPLANATION-ONLY.md) | Accepted | — | — | 2026-11-15 |
| [ADR-010: Manual Trade Execution in MVP](adr/ADR-010-MANUAL-TRADE-EXECUTION-MVP.md) | Accepted | — | — | 2026-11-15 |
| [ADR-011: Demo, Personal and Licensed Data Modes with Tenant Isolation](adr/ADR-011-DATA-MODES-AND-TENANT-ISOLATION.md) | Accepted | — | — | 2026-11-15 |
| [ADR-012: GitHub Actions for CI/CD](adr/ADR-012-GITHUB-ACTIONS-CI-CD.md) | Accepted | — | — | 2026-11-15 |
| [Documentation index](README.md) | Current | — | — | 2026-11-15 |
| [Glossary](GLOSSARY.md) | Current | — | — | 2026-11-15 |
| [ADR index](adr/README.md) | Current | — | — | 2026-11-15 |
| [Documentation audit report](AUDIT_REPORT.md) | Current | — | — | 2026-11-15 |

## 2. Open questions register

All unresolved decisions, aggregated from each document's "Open questions" section (61 items). Resolve by updating the owning document (and an ADR where the decision is architectural), then remove the row there; this table is regenerated from the documents.

| ID | Question | Owning document |
|---|---|---|
| OQ-VIS-01 | Market sizing and willingness-to-pay research before Phase C. | [Product Vision](product/01_PRODUCT_VISION.md) |
| OQ-VIS-02 | Brand/legal name availability and trademark check for "PriceAction AI". | [Product Vision](product/01_PRODUCT_VISION.md) |
| OQ-PRD-01 | Paper trades: dedicated `/paper-trades` route or a tab inside `/portfolio`? | [Product Requirements Document (PRD)](product/03_PRD.md) |
| OQ-PRD-02 | Should the scanner show SHORT informational setups by default (current UI does) or hide them behind a toggle? Proposed: hidden by default when preference is `LONG_ONLY`. | [Product Requirements Document (PRD)](product/03_PRD.md) |
| OQ-PRD-03 | Keep "Exchange" filter (NSE/BSE) in scanner UI? Proposed: remove for MVP. | [Product Requirements Document (PRD)](product/03_PRD.md) |
| OQ-ONB-01 | Is product analytics wanted in the personal phase? | [Onboarding Specification](product/05_ONBOARDING_SPECIFICATION.md) |
| OQ-ONB-02 | Should experience level change defaults (e.g. lower risk % for `NEW`)? Proposed: suggest 0.5% for `NEW`, user can change. | [Onboarding Specification](product/05_ONBOARDING_SPECIFICATION.md) |
| OQ-ARC-01 | Managed Postgres vs container in production (cost vs operational safety). | [System Architecture](architecture/01_SYSTEM_ARCHITECTURE.md) |
| OQ-ARC-02 | Should the frontend move to SSE for job progress in M9? | [System Architecture](architecture/01_SYSTEM_ARCHITECTURE.md) |
| OQ-ARC-03 | Python job library: arq (chosen) vs Celery vs RQ — revisit if scheduling/priority needs grow. | [System Architecture](architecture/01_SYSTEM_ARCHITECTURE.md) |
| OQ-DB-01 | Enable RLS before M10? Cost: every connection must set `app.tenant_id`, including workers. | [Database Design](architecture/03_DATABASE_DESIGN.md) |
| OQ-DB-02 | Store candle snapshot payloads in Postgres (chosen) vs object storage once volume grows. | [Database Design](architecture/03_DATABASE_DESIGN.md) |
| OQ-DB-03 | Per-tenant plan-number sequence implementation (counter table vs advisory lock). | [Database Design](architecture/03_DATABASE_DESIGN.md) |
| OQ-API-01 | Should `/analysis/{symbol}` embed candles by default (simpler frontend) or always require `include=candles` (smaller payloads)? Current choice: opt-in. | [API Specification (Public REST API v1)](architecture/04_API_SPECIFICATION.md) |
| OQ-API-02 | CSV export rights under each data mode — legal review required (OPS-05). | [API Specification (Public REST API v1)](architecture/04_API_SPECIFICATION.md) |
| OQ-API-03 | SSE/websocket channel for job progress and notifications (post-MVP). | [API Specification (Public REST API v1)](architecture/04_API_SPECIFICATION.md) |
| OQ-SEC-01 | Kite app model: single platform app (users authorise it) vs bring-your-own api_key per user. Affects token custody and terms compliance; see OPS-05. | [Security Architecture](architecture/06_SECURITY_ARCHITECTURE.md) |
| OQ-SEC-02 | Secret manager for production (host-provided vs SOPS-encrypted files vs GitHub Environments only). | [Security Architecture](architecture/06_SECURITY_ARCHITECTURE.md) |
| OQ-SEC-03 | When to make 2FA mandatory (proposed: before any non-owner user is onboarded). | [Security Architecture](architecture/06_SECURITY_ARCHITECTURE.md) |
| OQ-AI-01 | LLM provider and model choice; contract with provider (data retention, region). | [AI and LLM Architecture](architecture/07_AI_AND_LLM_ARCHITECTURE.md) |
| OQ-AI-02 | Should Q&A history (multi-turn) be supported, or single-turn only (current spec)? | [AI and LLM Architecture](architecture/07_AI_AND_LLM_ARCHITECTURE.md) |
| OQ-AI-03 | Hindi/regional language explanations (future). | [AI and LLM Architecture](architecture/07_AI_AND_LLM_ARCHITECTURE.md) |
| OQ-INT-01 | Verify Kite Connect historical limits, rate limits, token expiry, subscription requirements, and terms of use for personal vs multi-user apps. | [Integration Architecture](architecture/08_INTEGRATION_ARCHITECTURE.md) |
| OQ-INT-02 | Are Kite daily candles adjusted for splits/bonuses? Determines whether the adjustment step is applied or skipped for this provider. | [Integration Architecture](architecture/08_INTEGRATION_ARCHITECTURE.md) |
| OQ-INT-03 | Licensed vendor selection for SaaS mode (coverage of delisted symbols, corporate actions, historical index constituents). | [Integration Architecture](architecture/08_INTEGRATION_ARCHITECTURE.md) |
| OQ-TRD-01 | Should weekly structure be added as a context filter (e.g. only long when weekly is not `BEARISH`)? | [Trading Methodology](trading/01_TRADING_METHODOLOGY.md) |
| OQ-TRD-02 | Should volume confirmation become a scored component? It is currently evidence-only to stay "pure price action". | [Trading Methodology](trading/01_TRADING_METHODOLOGY.md) |
| OQ-TRD-03 | Which backtest result thresholds promote a parameter from `HYPOTHESIS` to `VALIDATED`? Proposed in TRD-08 §6, needs sign-off. | [Trading Methodology](trading/01_TRADING_METHODOLOGY.md) |
| OQ-STR-01 | Add `structure.transition_max_bars` (proposed default 40) to fall back from `TRANSITION` to `SIDEWAYS`? | [Market Structure Rules](trading/02_MARKET_STRUCTURE_RULES.md) |
| OQ-STR-02 | Should a minimum swing size (e.g. 2% from prior opposite pivot) filter noise pivots? | [Market Structure Rules](trading/02_MARKET_STRUCTURE_RULES.md) |
| OQ-STR-03 | Outside-bar ordering convention (§3.3) — accept or treat outside bars as non-pivots? | [Market Structure Rules](trading/02_MARKET_STRUCTURE_RULES.md) |
| OQ-SR-01 | Should zone breaks require 1 close (consistent with BOS) or 2 closes (current)? | [Support and Resistance Rules](trading/03_SUPPORT_RESISTANCE_RULES.md) |
| OQ-SR-02 | Should higher-timeframe (weekly) pivots be merged into daily zones with a weight? Future scope. | [Support and Resistance Rules](trading/03_SUPPORT_RESISTANCE_RULES.md) |
| OQ-SR-03 | Should touch counting decay with age instead of the recency bonus? | [Support and Resistance Rules](trading/03_SUPPORT_RESISTANCE_RULES.md) |
| OQ-SD-01 | Should a separate `RANGE_BREAKOUT` type be reinstated to match the existing UI/backtest strategy list? | [Setup Detection Rules and Price Action Quality Score](trading/04_SETUP_DETECTION_RULES.md) |
| OQ-SD-02 | Entry convention: close-confirmation + next open (chosen) vs. buy-stop above trigger intraday. The latter needs intraday data and is deferred. | [Setup Detection Rules and Price Action Quality Score](trading/04_SETUP_DETECTION_RULES.md) |
| OQ-SD-03 | Is `entry_window_bars = 1` too strict for end-of-day users who review the next evening? | [Setup Detection Rules and Price Action Quality Score](trading/04_SETUP_DETECTION_RULES.md) |
| OQ-SD-04 | Should PAQS thresholds differ per setup type? | [Setup Detection Rules and Price Action Quality Score](trading/04_SETUP_DETECTION_RULES.md) |
| OQ-RM-01 | Should estimated round-trip costs be added to `risk_per_share` for sizing? | [Risk Management Rules](trading/05_RISK_MANAGEMENT_RULES.md) |
| OQ-RM-02 | Add sector concentration limits? | [Risk Management Rules](trading/05_RISK_MANAGEMENT_RULES.md) |
| OQ-RM-03 | Confirm NSE tick-size table and its history for backtests. | [Risk Management Rules](trading/05_RISK_MANAGEMENT_RULES.md) |
| OQ-RM-04 | Frontend settings currently show defaults of 6 max positions and 2% portfolio heat; onboarding shows 5 positions. Canonical defaults here are 5 / 5% — confirm with product owner. | [Risk Management Rules](trading/05_RISK_MANAGEMENT_RULES.md) |
| OQ-BT-01 | Source of point-in-time NIFTY 500 membership and delisted price history. | [Backtesting Methodology](trading/06_BACKTESTING_METHODOLOGY.md) |
| OQ-BT-02 | Source and maintenance of historical statutory charge schedules. | [Backtesting Methodology](trading/06_BACKTESTING_METHODOLOGY.md) |
| OQ-BT-03 | Corporate-action data source. | [Backtesting Methodology](trading/06_BACKTESTING_METHODOLOGY.md) |
| OQ-BT-04 | Should cash dividends be credited in 0.1.x? | [Backtesting Methodology](trading/06_BACKTESTING_METHODOLOGY.md) |
| OQ-BT-05 | Promotion thresholds (proposed in TRD-08 §6). | [Backtesting Methodology](trading/06_BACKTESTING_METHODOLOGY.md) |
| OQ-PT-01 | Should paper fills optionally use a limit price at `entry_ref` instead of the open? | [Paper Trading Specification](trading/07_PAPER_TRADING_SPECIFICATION.md) |
| OQ-PT-02 | Should users be allowed multiple paper accounts (e.g. per strategy)? | [Paper Trading Specification](trading/07_PAPER_TRADING_SPECIFICATION.md) |
| OQ-PT-03 | Timing of EOD job — proposed 18:30 IST to allow for late data corrections; confirm against provider data availability. | [Paper Trading Specification](trading/07_PAPER_TRADING_SPECIFICATION.md) |
| OQ-RD-01 | Target dates per milestone. | [Implementation Roadmap](engineering/01_IMPLEMENTATION_ROADMAP.md) |
| OQ-RD-02 | Should M8 (LLM) be deferred after M9 to reach G1 sooner? Dependency graph allows it. | [Implementation Roadmap](engineering/01_IMPLEMENTATION_ROADMAP.md) |
| OQ-ING-01 | Should demo data roll forward daily (looks alive, but might be mistaken for live) or stay fixed at a past as-of date (clearer)? Proposed: fixed. | [Data Ingestion Specification](engineering/05_DATA_INGESTION_SPECIFICATION.md) |
| OQ-ING-02 | Exact thresholds for PARTIAL vs FAILED runs. | [Data Ingestion Specification](engineering/05_DATA_INGESTION_SPECIFICATION.md) |
| OQ-OPS-01 | Caddy vs Nginx for edge proxy; hosting provider; managed PostgreSQL (OQ-ARC-01). | [Deployment Guide](operations/01_DEPLOYMENT_GUIDE.md) |
| OQ-OPS-02 | Zero-downtime frontend switch (blue/green with two frontend containers) needed in Phase B? | [Deployment Guide](operations/01_DEPLOYMENT_GUIDE.md) |
| OQ-MON-01 | Self-hosted Prometheus/Grafana/GlitchTip vs hosted services (cost vs maintenance). | [Monitoring and Observability](operations/03_MONITORING_AND_OBSERVABILITY.md) |
| OQ-RET-01 | Legal confirmation of retention periods and privacy policy wording (India's Digital Personal Data Protection framework). | [Data Retention and Backup](operations/04_DATA_RETENTION_AND_BACKUP.md) |
| OQ-RET-02 | Whether provider terms limit storage duration of personally fetched historical data. | [Data Retention and Backup](operations/04_DATA_RETENTION_AND_BACKUP.md) |
| OQ-CMP-01 | Engage legal counsel: timing and scope (classification, terms, privacy). | [Compliance and Risk Considerations](operations/05_COMPLIANCE_AND_RISK_CONSIDERATIONS.md) |
| OQ-CMP-02 | Whether beta users must use only DEMO or their own PERSONAL connection (and whether a shared platform Kite app is allowed). | [Compliance and Risk Considerations](operations/05_COMPLIANCE_AND_RISK_CONSIDERATIONS.md) |

## 3. Priority open questions (block upcoming milestones)

| ID | Blocks | Why |
|---|---|---|
| OQ-INT-01 / OQ-INT-02 | M2 | Kite historical limits, rate limits, token expiry, terms and price adjustment must be verified before the adapter is finalised. |
| OQ-SEC-01 | M2 / G2 | Kite app model (platform app vs bring-your-own key) affects token custody and terms compliance. |
| OQ-RM-04 | M6 | Canonical risk defaults (5 positions / 5% heat / 25% max position) vs current UI values. |
| OQ-AI-01 | M8 | LLM provider/model. |
| OQ-BT-01 / OQ-BT-03 | M9–M10 | Point-in-time NIFTY 500 membership and corporate-action sources for unbiased backtests. |
| OQ-TRD-03 | M10 | Parameter promotion criteria sign-off. |
| OQ-CMP-01 | G2 | Legal counsel engagement. |
