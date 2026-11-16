---
name: price-action-domain
description: PriceAction AI trading-methodology guardrails. Use whenever a task defines, implements, reviews, displays, documents or explains a trading concept - swing pivots, HH/HL/LH/LL/EQH/EQL labels, market structure state, BOS, CHoCH, wick breaches, support/resistance zones, breakouts and retests, liquidity sweeps, the four setup types, PAQS quality score, signal states, NO_TRADE, stop/target/risk rules - in any layer (engine, API enums, frontend labels, LLM prompts, docs/trading). Also use when someone proposes adding an indicator (RSI, MACD, moving averages, ATR, Bollinger) or a new setup or parameter.
---

# Price-action domain

Keeps every trading concept in the project consistent with the authoritative methodology. The methodology lives in `docs/trading/` (TRD-01..08). This skill tells you where each rule is and which invariants are non-negotiable. It does **not** restate rule values: always read the spec section.

## Scope

- In scope: the meaning of trading terms and rules wherever they appear (Python domain code, DB enums, API schemas, frontend labels and badges, explanation prompts, docs).
- Out of scope: how to structure and test engine code (use the `quant-engine` skill) and market-data ingestion (use `market-data`).

## Required context (read before acting)

1. [TRD-01](../../../docs/trading/01_TRADING_METHODOLOGY.md): principles MP-01..MP-09 (§2), pipeline (§3), candle and numeric conventions (§4–§5), **parameter registry (§6, the only home of parameter values)**, canonical vocabulary (§7) and non-goals (§8).
2. Then only the rule document the task touches. Use [references/rule-map.md](references/rule-map.md) to find the exact section.
3. [GLOSSARY](../../../docs/GLOSSARY.md) for terminology. Use its wording in docs and UI.

## Workflow

1. **Classify the request.** Is it (a) applying an existing rule, (b) changing a rule or parameter, or (c) adding a new concept (indicator, setup type, timeframe)?
2. **Locate the authority.** Find the section in the rule map and read it. If the spec is silent or ambiguous, look for an `OQ-*` open question in that doc. Do **not** resolve it by assumption: ask the owner (CLAUDE.md §8).
3. **Check the invariants** below against the proposed change.
4. **For (b) or (c):** this is a methodology change. It needs:
   - the TRD doc updated in the same PR;
   - a new ruleset version (active ruleset `pa-intraday`, TRD-01 §6) if outputs change (TRD-01 §6, ENG-04 §5);
   - new or updated TRD-08 test vectors.
   Indicators are outside product scope (MP-01): refuse to add them as signal inputs and point to OQ-TRD-02 when volume is the topic. Check the canonical names in TRD-01 §7 before adding vocabulary.
5. **For vocabulary in other layers** (API enum, DB `CHECK`, frontend label): use the TRD-01 §7 canonical values. The frontend still uses the legacy mock vocabulary. Map it through [TRD-04 §12](../../../docs/trading/04_SETUP_DETECTION_RULES.md#12-frontend-vocabulary-reconciliation) and do not invent a third set.

## Non-negotiable invariants

| Invariant | Authority |
|---|---|
| Pure price action: OHLCV of closed candles only. Volume is evidence, never a signal | TRD-01 MP-01, TRD-04 §8 |
| Daily timeframe, closed candles only. Forming candles are never evaluated | MP-02, MP-03 |
| No look-ahead: every object has `confirmed_at_index`; a pivot at `i` exists only from `i + R` | MP-04, TRD-02 §3.4 |
| Close beats wick: breaks need a close beyond level × buffer. A close inside the buffer is a `WICK_BREACH`, not a break | MP-05, TRD-02 §8 |
| A pivot confirmed on bar `t` cannot be broken by bar `t`'s close | TRD-02 §6 |
| Labels compare against the previous **same-kind** confirmed pivot with the equal-level tolerance, and are never revised | TRD-02 §4 |
| Within a bar, invalidation is checked before confirmation | TRD-04 SD-01 |
| NO_TRADE is a valid, often correct outcome. Never force a setup | MP-07, C-10 |
| LONG is actionable. SHORT is computed but informational only, and can never become a plan | TRD-04 SD-06, C-12 |
| The quality score is rule-conformance, not a probability. No win-rate or prediction claims | TRD-01 §8, TRD-04 §9 |
| All thresholds come from the ruleset registry. Never hard-code or restate values elsewhere | TRD-01 §6 |
| Every parameter is a `HYPOTHESIS` until backtests promote it | MP-09, TRD-08 §6 |

## Validation

- Every rule you cite resolves to a real TRD section.
- No parameter value is duplicated outside TRD-01 §6. Code reads `RulesetParams`; docs reference the key.
- Vocabulary matches TRD-01 §7 exactly (case and spelling).
- If outputs change: ruleset version bumped, TRD docs and TRD-08 vectors updated in the same change.

## Deliverables

- The change, plus a short note citing the TRD sections applied.
- For methodology changes: the TRD diff, the ruleset version bump, the test-vector additions, and any new `OQ-*` raised for the owner.
- Documentation sync per the `docs-sync` skill.
