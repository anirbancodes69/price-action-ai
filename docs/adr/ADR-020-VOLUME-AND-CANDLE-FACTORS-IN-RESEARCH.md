# ADR-020: Volume and Candle-Shape Factors in the Research Track

| Field | Value |
|---|---|
| Status | **Accepted** (2026-11-23, by the owner's instruction to run the protocol that needs it). Does not change MP-01 for the product |
| Date | 2026-11-23 |
| Deciders | Product owner |
| Version | 1.0 |
| Related | [ADR-019](ADR-019-DAILY-TIMEFRAME-RESEARCH-TRACK.md) · [ADR-018](ADR-018-INDEPENDENT-STRATEGY-LIBRARY.md) · [ADR-014](ADR-014-PERSONAL-INTRADAY-WORKSTATION.md) · [TRD-01 MP-01](../trading/01_TRADING_METHODOLOGY.md) · [Candle and volume screening protocol](../research/candle-volume-screening-protocol.md) |

## Context

[TRD-01](../trading/01_TRADING_METHODOLOGY.md) principle **MP-01** says the methodology is pure price action: only OHLC of confirmed candles, no indicators, and volume only as a *non-signal* context item. [CLAUDE.md §4](../../CLAUDE.md) repeats that no indicator or volume signal is allowed until the owner changes the methodology.

Every entry tested so far (setups, daily breakouts, pullbacks, failed breakdowns, support touches) used closes, highs and lows. None beat matched random entries at the observed friction. On 2026-11-23 the owner asked to test **candle type** (red or green, hammer, doji, engulfing and similar) and **volume** as entry and exit factors.

- **Candle shape** is derived from open, high, low and close only, so it **already fits MP-01** (pure price action). It needs no methodology change, only exact definitions.
- **Volume** is not price. Using it as a signal (for example, volume above its recent average on the signal candle) goes beyond MP-01, so it needs a decision. Daily volume is already stored for every bar; the backtest loaders have never read it.

## Decision

1. **Research track only.** Volume may be used as a **pre-registered signal filter** in the research track's screens ([ADR-019](ADR-019-DAILY-TIMEFRAME-RESEARCH-TRACK.md)), in exact, fixed definitions written before a run (for example "volume of the signal session at least 1.5 times the mean volume of the previous 20 sessions"). No volume value is tuned after a result.
2. **Candle-shape factors** (colour, body and wick ratios, named patterns defined by exact thresholds from OHLC) are allowed in the research track under the existing rules; this ADR records that they need no change to MP-01.
3. **Nothing live changes.** The scanner, the live ruleset (`pa-intraday 0.1.0`), the intraday detectors, the API and the frontend stay as they are. A volume-based or pattern-based rule may enter a product ruleset only after it reaches `RESEARCH_VALIDATED` ([validation criteria](../research/validation-criteria.md)) and a later decision changes TRD-01 for the product.
4. **Everything else in ADR-018 and ADR-019 stands:** one strategy at a time, matched random-entry controls, in-sample screen then confirmation, out-of-sample touched once, a recorded family size and a stricter interval for the number tried.
5. **Data handling.** Volume is checked before use (a volume audit like the price audit of Gate 0): volume that is not adjusted for splits or bonuses would make a relative-volume filter fire falsely, so affected sessions are excluded or the series cut, and each exclusion is reported.
6. **Scope of the relaxation.** Only volume, and only as the pre-registered filter. Other indicators (moving averages, RSI, MACD, VWAP, ATR-based signals) remain excluded until the owner decides otherwise.

## Alternatives considered

| Alternative | Why not chosen |
|---|---|
| Keep MP-01 as written and test candle shapes only | Possible and needs no decision; but it leaves out the one input that carries information beyond price, which the owner asked about. Can be chosen instead (the protocol then drops its volume variants). |
| Allow all indicators in research | Opens a very large space of rules and false positives; not asked for. |
| Change MP-01 for the whole product now | No volume rule has any evidence; changing the product methodology before a result repeats the ADR-014 rewrite. |

## Consequences

+ Lets the research track test the factors the owner expects to matter, in a controlled way.
+ No production change; if volume adds nothing, the cost is a few research documents and some research code.
− More ways to find a spurious pattern: each volume variant adds to the family size and must be paid for with the stricter interval.
− Volume data quality is unverified (adjustment for corporate actions, source differences); the volume audit is part of the work.
− If a volume rule later validates, TRD-01 MP-01, TRD-04 and the engine's inputs need a separate decision and specification.

**Migration and compatibility:** none now (research code and documents only; the stored `volume` column and the existing schema are used as they are).

## Status

Proposed on 2026-11-23; **accepted the same day** when the owner instructed that the candle and volume protocol be run ("first lets do the run"). DEC-022 records it. It does not change MP-01 for the product, the scanner or any live ruleset.
