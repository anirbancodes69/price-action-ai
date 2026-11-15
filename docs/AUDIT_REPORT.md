# Documentation Audit Report

| Field | Value |
|---|---|
| Version | 1.0 |
| Status | Current |
| Owner | Documentation owner |
| Audit date | 2026-11-15 |
| Scope | All 58 Markdown files under `docs/` plus root `README.md` |

## 1. Purpose

Records the consistency audit performed after the Phase 2 documentation was written: what was checked, how, what was fixed and what remains open. Re-run the audit at the end of each milestone.

## 2. Method

1. **Automated checks** (scripted):
   - All required files exist (57 required by the Phase 2 brief + this report).
   - All relative links and `#anchors` resolve (GitHub slug rules).
   - Every parameter key used in backticks across the docs exists in the [TRD-01 §6 registry](trading/01_TRADING_METHODOLOGY.md#6-ruleset-parameter-registry-authoritative).
   - Every DB entity in the frontend mapping ([ENG-02 §8](engineering/02_FRONTEND_ARCHITECTURE.md#8-route--feature--api--entity-mapping)) exists in [ARC-03](architecture/03_DATABASE_DESIGN.md), and every table has an owning Laravel module or engine owner.
   - Every API ID in the mapping exists in [ARC-04](architecture/04_API_SPECIFICATION.md).
   - Every `page.tsx` route in `frontend/src/app` appears in the mapping.
   - No `TODO`/`TBD`/`FIXME` placeholders.
2. **Manual review** of the 14 cross-document relationships in §3.

## 3. Cross-document validation results

| # | Check | Result | Notes |
|---|---|---|---|
| 1 | BRD ↔ PRD | Pass | Every BRQ maps to FRs/BRs: BRQ-002→BR-001; BRQ-003→FR-012/BR-002; BRQ-004→FR-020; BRQ-005→ARC-03 C-08 columns; BRQ-006/007→FR-061/062; BRQ-008→BR-008; BRQ-009→FR-090–093; BRQ-010→BR-003; BRQ-014→US-05. ID clash `BR-` (BRD vs PRD) fixed by renaming BRD IDs to `BRQ-`. |
| 2 | PRD ↔ frontend routes | Pass | All 13 page routes plus the `/` and `/analysis` redirects and not-found are covered in PRD-03 §6. New routes proposed: `/reset-password` (required); `/paper-trades` or a portfolio tab (OQ-PRD-01). |
| 3 | Frontend features ↔ API | Pass | Each route maps to API IDs (ENG-02 §8). Gap: the current `DataSource` is read-only, so a mutations client is specified (ENG-02 §5). |
| 4 | API ↔ database | Pass | Request/response fields map to ARC-03 columns. Plan, setup, signal and status enums match. The API serialises money as strings and the DB uses `numeric`. |
| 5 | Database ↔ architecture | Pass after fix | ARC-01's "one writer per table" contradicted ARC-03 for four trading tables. Fixed by documenting explicit shared-write exceptions (ARC-01 §6) that match ARC-06 DB-role grants. |
| 6 | Trading rules ↔ Python engine | Pass | Every TRD section has a module in ENG-04 §2; parameters come only from `RulesetParams` (PE-06); TRD-08 catalogue mapped to CI jobs. |
| 7 | Risk calculations ↔ trading specs | Pass | TRD-05 worked examples re-computed (qty 167, binding POSITION_CAP; heat example 135; gap limit ₹1,525.41; R:R 3.49 / 2.32 / 1.55). ARC-04 §8.1 example matches. PRD US-06 matches. |
| 8 | Backtesting ↔ look-ahead prevention | Pass | Signal at close t / fill at open t+1 (BT-02); pivots usable only from `confirmed_at_index`; BOS requires pivot confirmed before the break bar; paper EOD ordering avoids same-day hindsight; TV-NLA-01..04 required. |
| 9 | Security ↔ broker integration | Pass | No Zerodha password is collected; `request_token` is discarded; the access token is encrypted, never in API/Redis/logs, fetched just-in-time by workers (ARC-06 §5, ARC-08 §4, ARC-05 §3). |
| 10 | GitHub workflows ↔ repo structure | Pass | Path filters (ENG-10 §2.2) match the ENG-09 layout (`frontend/`, `backend/`, `python-engine/`, `contracts/`, `infrastructure/`, `docs/trading/`). |
| 11 | CI checks ↔ testing strategy | Pass | Each suite in ENG-07 §3 has a CI job; gates introduced progressively per roadmap milestone. |
| 12 | Deployment ↔ Docker architecture | Pass | OPS-01 service roll order and health checks match the ENG-08 service list and ARC-01 components; the existing frontend `HEALTHCHECK` is reused. |
| 13 | Roadmap ↔ dependencies | Pass | The M0→M10 graph respects data and contract dependencies; M3 may run in parallel with M2 on fixtures; M8 can be deferred after M9 (OQ-RD-02). |
| 14 | SaaS ↔ data licensing | Pass | Licensing and legal review are explicit G3 gates (PRD-02 §12, OPS-05 §3/§8, ADR-011). PERSONAL data is excluded from shared caches, shared AI summaries and exports (ARC-08 §2, ARC-07 §9, ARC-04 N2). |

## 4. Issues found and fixed during the audit

| ID | Issue | Fix |
|---|---|---|
| AF-01 | `BR-` ID prefix used for both BRD requirements and PRD business rules | BRD now uses `BRQ-` |
| AF-02 | ARC-01 claimed single writer per table; ARC-03 had shared writes | Shared-write exceptions table added to ARC-01 §6 |
| AF-03 | ARC-05 had Laravel inserting `ingestion_runs` (engine-owned) | Laravel now submits the job through the engine API, and the engine creates the run |
| AF-04 | TRD-02 state diagram showed an unspecified TRANSITION→SIDEWAYS timeout | Removed from the diagram; documented as OQ-STR-01 |
| AF-05 | Zone-break buffer ambiguity (structure vs breakout buffer) | Buffer ownership defined in TRD-03 §5.1 |
| AF-06 | Parameters referenced but not registered (`risk.default_max_position_pct`, `exit.structure_exit_enabled`, `backtest.slippage_pct`) | Added to the TRD-01 registry |
| AF-07 | Measured-move target could be circular (entry + min_rr × risk) | Explicitly forbidden in TRD-04 §7.3 |
| AF-08 | ARC-01 implied Laravel orchestrated EOD steps; ARC-05 had the worker chaining them | Worker chains the pipeline; Laravel handles engine events |
| AF-09 | Broken anchors (route mapping, risk API) and one `TBD` | Fixed |

## 5. Remaining gaps and contradictions (not resolved here, by design)

These are explicit decisions or verifications that belong to the owner or to later milestones. None is silently assumed.

| ID | Gap | Where tracked |
|---|---|---|
| G-01 | Frontend vocabulary (setup types, statuses, universes, plan statuses) differs from the canonical spec | ENG-02 §9 D-01..D-24; resolved in M7 |
| G-02 | Risk defaults differ between settings UI (6 positions / 2% heat), onboarding (5) and spec (5 / 5% / 25%) | OQ-RM-04 |
| G-03 | Kite Connect behaviour (limits, token expiry, adjustment, terms) is assumed, not verified | OQ-INT-01/02, OQ-SEC-01 |
| G-04 | No source yet for point-in-time NIFTY 500 membership, delisted prices or corporate actions | OQ-BT-01/03 |
| G-05 | Statutory cost values in TRD-06 §5 need verification and dated schedules | OQ-BT-02 |
| G-06 | NSE tick-size table history unverified | OQ-RM-03 |
| G-07 | LLM provider/model not selected | OQ-AI-01 |
| G-08 | Legal classification, privacy policy and retention periods need counsel | OQ-CMP-01, OQ-RET-01/02 |
| G-09 | All trading parameters are unvalidated hypotheses; promotion criteria need sign-off | TRD-01 MP-09, OQ-TRD-03 |
| G-10 | Zone break (2 closes) vs BOS (1 close) asymmetry is intentional but debatable | OQ-SR-01 |
| G-11 | Paper-trades UI location undecided | OQ-PRD-01 |
| G-12 | The repository has no commits, no root `.gitignore`, and `.DS_Store` / `tsconfig.tsbuildinfo` are present | ENG-01 M0 tasks |

The full list of 61 open questions is in [DOCUMENTATION_STATUS §2](DOCUMENTATION_STATUS.md#2-open-questions-register).

## 6. Scope compliance

| Restriction | Verified |
|---|---|
| No Laravel/FastAPI code, migrations, endpoints or workflow YAML created | ✔ Only `docs/**` and root `README.md` were added |
| Frontend unchanged | ✔ No file under `frontend/` modified (mtime check) |
| No dependencies installed, nothing committed or pushed | ✔ Repository still has no commits |
| Trading logic unchanged | ✔ The demo heuristic in `frontend/src/mocks` is untouched and documented as non-authoritative |

## 7. Recommendation

Proceed to **M0** (first commit with a root `.gitignore`, then the CI foundation and Compose skeleton), then **M1** (migrations, OpenAPI and engine contracts). Resolve G-02 and G-03 before M2/M6 begin.
