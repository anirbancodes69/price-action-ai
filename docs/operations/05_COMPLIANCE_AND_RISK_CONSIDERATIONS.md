# Compliance and Risk Considerations

| Field | Value |
|---|---|
| Document ID | OPS-05 |
| Version | 0.1.0 |
| Status | Pending legal review (not legal advice) |
| Owner | Product Owner |
| Last updated | 2026-11-15 |
| Related | [PRD-02 Release gates](../product/02_BRD.md#12-release-gates) · [ADR-010](../adr/ADR-010-MANUAL-TRADE-EXECUTION-MVP.md) · [ADR-011](../adr/ADR-011-DATA-MODES-AND-TENANT-ISOLATION.md) · [ARC-07](../architecture/07_AI_AND_LLM_ARCHITECTURE.md) |

> **This document is an engineering and product risk register, not legal advice.** Every item marked "review" requires a qualified Indian securities/technology lawyer before Phase B (private beta) or Phase C (SaaS).

## 1. Purpose

Identifies regulatory, contractual and product risks, the design controls already in place, and the decisions that must be made before wider release.

## 2. Product classification risk (review)

| Topic | Consideration | Current design control | Decision needed |
|---|---|---|---|
| Investment advice / research analysis | Indian securities regulation (SEBI) governs persons providing investment advice or research reports/recommendations to others. A tool that publishes buy/sell recommendations to third parties for a fee may fall within such regimes. | Personal phase: owner is the only user. Product framed as rule-based decision support; no personalised recommendations; no bare BUY/SELL; "No trade" first-class; disclaimers; LLM explanation-only. | Legal opinion on classification for Phase B/C, including whether registration (e.g. research analyst / investment adviser) or specific exemptions apply, and required disclosures. |
| Algorithmic trading | Regulatory frameworks for retail algorithmic trading through brokers/APIs exist and have evolved. | No order placement at all (ADR-010). | Re-review before any execution feature. |
| Performance claims / advertising | Hypothetical/backtested performance presentation is sensitive. | Results labelled hypothetical; no return promises; low-sample warnings. | Review marketing copy before Phase C. |
| Use of AI in advice-like contexts | Regulators have shown interest in AI disclosures and accountability. | LLM cannot produce numbers or advice; validator; disclaimers; versioned prompts. | Review disclosure wording. |

## 3. Market data licensing (hard gate)

| Rule | Detail |
|---|---|
| C-04 | Personal Kite Connect access is **not** assumed to permit redistribution or commercial use of data. |
| Design control | `data_sources` modes; PERSONAL data scoped to tenant; no shared caches/AI summaries/exports for PERSONAL; DEMO is synthetic. |
| SaaS gate (C-05) | Signed commercial data licence covering display to subscribers, storage, derived analytics, and (if offered) export, **before** any multi-tenant use of real data. |
| Exchange data policies | Real-time/delayed/EOD display to third parties may involve exchange data licensing via vendors — vendor contract must cover it. |
| Review | Kite Connect terms for (a) personal use by the developer, (b) multiple users authorising one developer app, (c) storage of historical data (OQ-SEC-01, OQ-RET-02). |

## 4. Data protection and privacy (review)

- India's Digital Personal Data Protection framework applies to personal data of users in India: lawful purpose, notice, consent, security safeguards, breach notification, data-principal rights (access, correction, erasure).
- Design controls: minimal PII (name, email), no broker credentials, encryption, audit, deletion flow (OPS-04 §4), no PII to LLM, provider data-retention settings minimised.
- Needed before Phase B: privacy policy, terms of use, consent capture at registration (`accept_terms`), breach response procedure, processor list (hosting, email, LLM, error tracking).

## 5. Broker integration risks

| Risk | Control |
|---|---|
| Credential misuse | Never collect Zerodha password/2FA; OAuth-style redirect only (ARC-06 §5) |
| Token leakage | Encryption, JIT fetch, redaction, audits |
| Terms violation | Personal use only until review; no automation of login |
| Provider outage/changes | Abstraction layer; data delays surfaced to user |

## 6. Financial-harm risks to users

| Risk | Control |
|---|---|
| Over-reliance on signals | Signal semantics (BUY WATCH ≠ entry), explanations, invalidation always shown, disclaimers |
| Mis-sized positions | Engine-computed sizing with caps; stop mandatory; min R:R |
| Demo mistaken for live | Mandatory data-mode badges; HV-06 for LLM; demo as-of fixed in the past (proposed) |
| Unvalidated parameters | Ruleset `validation_status` shown; promotion criteria (TRD-08 §6) |
| Short-selling confusion | Bearish setups informational, plans blocked |

## 7. Mandatory disclaimers (copy owners: product)

- Global footer / analysis & backtest pages: "PriceAction AI provides rule-based analysis for education and decision support. It is not investment advice. Trading involves risk of loss."
- Backtests: "Hypothetical, simulated results. Past performance does not indicate future results."
- AI panel: "Educational explanation of rule-based analysis. Not investment advice."
- Demo: "Sample data — not live or historical market data."

## 8. Compliance checklist by release gate

| Item | G1 Personal | G2 Beta | G3 SaaS |
|---|---|---|---|
| Disclaimers in UI | ✔ | ✔ | ✔ |
| Privacy policy + terms | — | ✔ | ✔ |
| Provider terms review | ✔ (personal use) | ✔ (multi-user) | ✔ |
| Legal classification opinion | — | ✔ | ✔ |
| Data licence for shared real data | — | If real data shared: ✔ | ✔ |
| 2FA, RLS, security review | — | 2FA | All |
| Breach response plan | — | ✔ | ✔ |

## 9. Open questions

| ID | Question |
|---|---|
| OQ-CMP-01 | Engage legal counsel: timing and scope (classification, terms, privacy). |
| OQ-CMP-02 | Whether beta users must use only DEMO or their own PERSONAL connection (and whether a shared platform Kite app is allowed). |
