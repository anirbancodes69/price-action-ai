# Rule map: concept → authoritative section

Pointers only. Read the linked section; do not copy its contents into code comments, skills or other docs.

| Concept | Authoritative section |
|---|---|
| Methodology principles MP-01..11 | [TRD-01 §2](../../../../docs/trading/01_TRADING_METHODOLOGY.md#2-methodology-principles) |
| Analysis pipeline order | [TRD-01 §3](../../../../docs/trading/01_TRADING_METHODOLOGY.md#3-analysis-pipeline) |
| Candle validation, min history, adjusted prices | [TRD-01 §4](../../../../docs/trading/01_TRADING_METHODOLOGY.md#4-candle-conventions) |
| Session conventions (opening range, entry cutoff, session-end exit) | [TRD-01 §4.1](../../../../docs/trading/01_TRADING_METHODOLOGY.md#41-session-conventions) |
| Percent units, `above`/`below` with buffer, tick rounding direction | [TRD-01 §5](../../../../docs/trading/01_TRADING_METHODOLOGY.md#5-numeric-conventions) |
| **All parameter keys and defaults** | [TRD-01 §6](../../../../docs/trading/01_TRADING_METHODOLOGY.md#6-ruleset-parameter-registry-authoritative) |
| Canonical enums (state, label, event, setup, status, signal, run status) | [TRD-01 §7](../../../../docs/trading/01_TRADING_METHODOLOGY.md#7-outputs-and-vocabulary) |
| Swing high/low definition, tie-breaking, outside bars | [TRD-02 §3.1–3.3](../../../../docs/trading/02_MARKET_STRUCTURE_RULES.md#3-swing-pivots) |
| Pivot confirmation timing | [TRD-02 §3.4](../../../../docs/trading/02_MARKET_STRUCTURE_RULES.md#34-confirmation-timing-no-look-ahead) |
| HH / HL / LH / LL / EQH / EQL labelling | [TRD-02 §4](../../../../docs/trading/02_MARKET_STRUCTURE_RULES.md#4-swing-labels) |
| Structure state machine (SIDEWAYS, BULLISH, BEARISH, TRANSITION) | [TRD-02 §5](../../../../docs/trading/02_MARKET_STRUCTURE_RULES.md#5-structure-state) |
| Break of Structure | [TRD-02 §6](../../../../docs/trading/02_MARKET_STRUCTURE_RULES.md#6-break-of-structure-bos) |
| Change of Character | [TRD-02 §7](../../../../docs/trading/02_MARKET_STRUCTURE_RULES.md#7-change-of-character-choch) |
| Wick breach vs close break | [TRD-02 §8](../../../../docs/trading/02_MARKET_STRUCTURE_RULES.md#8-wick-breach-vs-close-break) |
| Higher-timeframe alignment (15m context on 5m) | [TRD-02 §9](../../../../docs/trading/02_MARKET_STRUCTURE_RULES.md#9-higher-timeframe-alignment-15m-context-on-a-5m-run) |
| Sessions, edge cases, repainting checklist | [TRD-02 §10](../../../../docs/trading/02_MARKET_STRUCTURE_RULES.md#10-sessions-and-edge-cases) |
| S/R zone construction (pivot clustering) | [TRD-03 §3](../../../../docs/trading/03_SUPPORT_RESISTANCE_RULES.md#3-zone-construction-pivot-clustering) |
| Touches and strength score | [TRD-03 §4](../../../../docs/trading/03_SUPPORT_RESISTANCE_RULES.md#4-touches-and-strength) |
| Zone break, role reversal (flip), statuses | [TRD-03 §5](../../../../docs/trading/03_SUPPORT_RESISTANCE_RULES.md#5-invalidation-and-role-reversal) |
| Equal highs/lows (liquidity pools) | [TRD-03 §6](../../../../docs/trading/03_SUPPORT_RESISTANCE_RULES.md#6-equal-highs--equal-lows) |
| Proximity | [TRD-03 §7](../../../../docs/trading/03_SUPPORT_RESISTANCE_RULES.md#7-proximity) |
| Session reference levels (PDH/PDL/PDC, opening range, session high/low) | [TRD-03 §8](../../../../docs/trading/03_SUPPORT_RESISTANCE_RULES.md#8-session-reference-levels) |
| Setup lifecycle and common rules SD-01..09 | [TRD-04 §2](../../../../docs/trading/04_SETUP_DETECTION_RULES.md#2-common-lifecycle) |
| Opening range breakout | [TRD-04 §3](../../../../docs/trading/04_SETUP_DETECTION_RULES.md#3-setup-1--opening_range_breakout-long) |
| Previous-day high break (and low break, informational) | [TRD-04 §4](../../../../docs/trading/04_SETUP_DETECTION_RULES.md#4-setup-2--prev_day_high_break-long) |
| Breakout and retest | [TRD-04 §5](../../../../docs/trading/04_SETUP_DETECTION_RULES.md#5-setup-3--breakout_retest-long) |
| Trend continuation (after validation) | [TRD-04 §6](../../../../docs/trading/04_SETUP_DETECTION_RULES.md#6-setup-4--trend_continuation-long-after-validation) |
| Liquidity sweep reversal (after validation) | [TRD-04 §7](../../../../docs/trading/04_SETUP_DETECTION_RULES.md#7-setup-5--liquidity_sweep_reversal-long-after-validation) |
| Entry, stop, target ladder, R:R | [TRD-04 §8](../../../../docs/trading/04_SETUP_DETECTION_RULES.md#8-levels) |
| Evidence items | [TRD-04 §9](../../../../docs/trading/04_SETUP_DETECTION_RULES.md#9-evidence) |
| PAQS quality score | [TRD-04 §10](../../../../docs/trading/04_SETUP_DETECTION_RULES.md#10-price-action-quality-score-paqs) |
| Setup expiry | [TRD-04 §11](../../../../docs/trading/04_SETUP_DETECTION_RULES.md#11-expiry) |
| Primary setup and signal state mapping | [TRD-04 §12](../../../../docs/trading/04_SETUP_DETECTION_RULES.md#12-signal-state-mapping) |
| Frontend legacy vocabulary → canonical | [TRD-04 §13](../../../../docs/trading/04_SETUP_DETECTION_RULES.md#13-frontend-vocabulary-reconciliation) |
| Position sizing, stop and R:R validation, rounding, entry gaps, heat | [TRD-05](../../../../docs/trading/05_RISK_MANAGEMENT_RULES.md) |
| Backtest execution model, costs, survivorship, OOS | [TRD-06](../../../../docs/trading/06_BACKTESTING_METHODOLOGY.md) |
| Plan → paper trade → actual trade separation, EOD processing | [TRD-07](../../../../docs/trading/07_PAPER_TRADING_SPECIFICATION.md) |
| Mandatory test vectors (TV-*) | [TRD-08 §3](../../../../docs/trading/08_TRADING_ENGINE_VALIDATION.md#3-mandatory-test-catalogue) |
| UI chart annotation rules (unconfirmed pivots, wick-breach markers, SHORT styling) | [PRD-07 §7](../../../../docs/product/07_UI_UX_SPECIFICATION.md#7-chart-annotation-rules) |
