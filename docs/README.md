# PriceAction AI — Documentation

| Field | Value |
|---|---|
| Version | 0.1.0 |
| Status | Current |
| Owner | Product Owner / Technical Lead |
| Last updated | 2026-11-15 |

## 1. Purpose

This directory is the **authoritative specification** for PriceAction AI: an AI-assisted, rule-based price-action analysis and trade-planning platform for NSE cash equities (NIFTY 500, daily timeframe). It defines what to build before backend development begins. Where code and these documents disagree, the disagreement is a defect to be resolved explicitly (see the frontend discrepancy register in [ENG-02 §9](engineering/02_FRONTEND_ARCHITECTURE.md#9-discrepancy-register)).

**Current implementation state (2026-11-15):** only the Next.js frontend exists, serving sample data through a mock adapter. Backend, engine, database and CI are specified here but not built.

## 2. Structure

| Folder | Prefix | Contents |
|---|---|---|
| [product/](product/) | PRD-01..07 | Vision, BRD, PRD, user journeys, onboarding, feature catalog, UI/UX |
| [architecture/](architecture/) | ARC-01..08 | System architecture, tech stack, database, API, data flow, security, AI/LLM, integrations |
| [trading/](trading/) | TRD-01..08 | Methodology & parameter registry, market structure, S/R, setups & quality score, risk, backtesting, paper trading, validation |
| [engineering/](engineering/) | ENG-01..12 | Roadmap, frontend, backend, Python engine, ingestion, errors/logging, testing, dev environment, GitHub repo, CI/CD, branching/release, code quality/PRs |
| [operations/](operations/) | OPS-01..06 | Deployment, environment config, monitoring, retention/backup, compliance, disaster recovery |
| [adr/](adr/README.md) | ADR-001..012 | Architecture decision records |
| [GLOSSARY.md](GLOSSARY.md) | — | Terminology |
| [DOCUMENTATION_STATUS.md](DOCUMENTATION_STATUS.md) | — | Status, dependencies, open questions per document |
| [AUDIT_REPORT.md](AUDIT_REPORT.md) | — | Cross-document consistency audit |

Note: in the product folder, `PRD-03` is the Product Requirements Document itself; `PRD-xx` is the series prefix for all product documents. In the BRD, business requirements use `BRQ-`; in the PRD, business rules use `BR-`.

## 3. Reading order

| Reader | Order |
|---|---|
| Everyone (start here) | [PRD-01 Vision](product/01_PRODUCT_VISION.md) → [GLOSSARY](GLOSSARY.md) → [ARC-01 System architecture](architecture/01_SYSTEM_ARCHITECTURE.md) → [ADR index](adr/README.md) |
| Product | PRD-02 BRD → PRD-03 PRD → PRD-04 Journeys → PRD-05 Onboarding → PRD-06 Features → PRD-07 UI/UX |
| Trading engine | TRD-01 (parameter registry) → TRD-02 → TRD-03 → TRD-04 → TRD-05 → TRD-06 → TRD-07 → TRD-08 → ENG-04 |
| Backend | ARC-03 DB → ARC-04 API → ARC-06 Security → ARC-08 Integration → ENG-03 → ENG-05 → ENG-06 |
| Frontend | PRD-07 → ENG-02 (mapping + discrepancies) → ARC-04 |
| DevOps | ENG-08 → ENG-09 → ENG-10 → ENG-11 → OPS-01..06 |
| Next implementer | ENG-01 Roadmap (start at M0) → DOCUMENTATION_STATUS → AUDIT_REPORT |

## 4. Source-of-truth rules

1. **One authoritative home per fact.** Other documents link to it rather than restating it:
   - Trading parameters and defaults → [TRD-01 §6](trading/01_TRADING_METHODOLOGY.md#6-ruleset-parameter-registry-authoritative)
   - Trading rules → TRD-02..07
   - Database schema → ARC-03; API contracts → ARC-04 (OpenAPI generated from it in M1 becomes the machine-readable source)
   - Feature status → PRD-06; frontend discrepancies → ENG-02 §9
   - Decisions → ADRs
2. **Accepted ADRs win** over other documents; changing them requires a superseding ADR.
3. **Assumptions** are marked `ASSUMPTION` / `HYPOTHESIS`; **unresolved decisions** are listed as `OQ-*` open questions in each document and aggregated in DOCUMENTATION_STATUS.
4. Product constraints C-01..C-17 (below) apply to every document.

### Product constraints

| ID | Constraint |
|---|---|
| C-01 | PriceAction AI is initially a trading analysis and decision-support platform. |
| C-02 | No automated broker order placement in MVP. |
| C-03 | Demo data must never be represented as live data. |
| C-04 | Personal Zerodha API access is not assumed to permit commercial data redistribution. |
| C-05 | SaaS commercialisation requires separate data licensing and legal/regulatory review. |
| C-06 | Broker credentials are never exposed to the frontend. |
| C-07 | The LLM never overrides deterministic calculations. |
| C-08 | Every analysis references an immutable candle snapshot and versioned ruleset. |
| C-09 | Historical backtests avoid look-ahead bias. |
| C-10 | No-trade is a valid outcome. |
| C-11 | Actual trades and proposed trade plans are stored separately. |
| C-12 | Bearish setups are informational in the NSE cash-equity MVP. |
| C-13 | All financial calculations are deterministic and independently testable. |
| C-14 | GitHub Actions is the mandatory CI/CD platform. |
| C-15 | Docker Compose is the local development environment. |
| C-16 | Production deployment requires controlled approval. |
| C-17 | No secrets or credentials are committed to GitHub. |

## 5. Maintaining the documentation

- Docs live with the code; changes go through PRs like code ([ENG-12](engineering/12_CODE_QUALITY_AND_PULL_REQUESTS.md) template requires doc updates).
- Every document starts with a metadata table (ID, version, status, owner, last updated, related). Bump the version on meaningful changes (minor for additions, major for changed meaning).
- Statuses: `Draft`, `Specification ready`, `Pending` (missing decisions listed), `Approved`, `Reflects implemented code`, `Superseded`.
- When a behaviour changes: update the authoritative document, then any summaries/links, then PRD-06 status and DOCUMENTATION_STATUS.
- Ruleset-affecting changes also bump the ruleset version (TRD-01, ENG-04 §5).
- Mermaid is used for diagrams (renders on GitHub).
- Run the docs checks in CI (markdown lint + relative link check, ENG-10 §2.2).
