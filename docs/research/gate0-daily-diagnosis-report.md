# Gate 0 Report: Daily-Timeframe Framework Diagnosis

| Field | Value |
|---|---|
| Version | 1.0.0 |
| Date | 2026-11-23 |
| Plan | [gate0-daily-diagnosis-plan.md](gate0-daily-diagnosis-plan.md) (approved 2026-11-23); post-run amendments in plan §8.2 |
| Authority | [ADR-019](../adr/ADR-019-DAILY-TIMEFRAME-RESEARCH-TRACK.md) |
| Status | DG-0 to DG-6 done. **The report decides nothing**; whether the track continues is the owner's call (§7) |
| Data | Kite daily bars, today's NIFTY 50, **data version 2026-11-23** (one backfill run, 2015-01-01..2026-11-19, 2,936 sessions after the special sessions; 44 stocks with full history, 6 listed later). In-sample only: 1,761 sessions, 2015-01-01..2022-02-15. Out-of-sample and holdout prices were not loaded by any run |
| Code | `python-engine/app/backtest/diagnostics/daily.py`, `scripts/run_gate0.py`, `DeliverySchedule` in `costs.py` |

Hypothetical, simulated results only (TRD-06 BT-06). Aggregates only; raw output stays outside the repository. Intervals are 95%, bootstrap over calendar months (10,000 resamples, seed 1). Delivery charges are Groww's published rates (read 2026-11-23, unverified); slippage 0.05% on each side is an assumption.

## 1. Result in one paragraph

The daily framework is **not hostile, and not a free baseline either**. The data is usable after three corporate-action breaks, one bad bar and four special sessions were handled (§3). The simulator agrees with a separate recomputation on 20 of 20 trades. Random long entries with wide stops and long holds earn a small positive gross (+0.05 to +0.12R) and about **zero net** (-0.04R to +0.01R at 5% to 8% stops held 20 sessions, every interval includes zero); narrow stops lose (-0.16R to -0.29R net at a 2% stop). Friction falls from 0.30R at a 2% stop to 0.12R at 8%, confirming ADR-019's table. Compared with intraday (random entries -0.33R net) the wide-stop baseline is about 0.3R better, so friction was the lever; but there is no positive baseline: **a daily strategy must show its own edge, about +0.1R over its matched baseline, to clear the validation bar (net above 0.10R).**

## 2. Hypotheses

| ID | Hypothesis | Verdict | Evidence |
|---|---|---|---|
| HD1 | Friction relative to the stop dominates daily cost | **Supported** | DG-2: friction 0.30R at 2%, 0.23R at 3%, 0.19R at 4%, 0.16R at 5%, 0.12R at 8%; the random baseline moves from -0.25R net at 2% to about 0 at 5% to 8% with a 20-session hold |
| HD2 | Random long holds have a positive baseline | **Supported, but period-dependent** | DG-1: gross mean return per entry +0.23% (5 sessions), +0.62% (10), +1.38% (20; interval +0.45% to +2.21%). 2017, 2020 and 2021 carry it; 2015, 2018 and 2022 are negative |
| HD3 | Overnight gaps push realised losses beyond 1R | **Small** | Average stop-out R is -1.02 to -1.06; gap exits are 1% to 4% of trades (the share falls as the stop widens) |
| HD4 | The holding limit changes the baseline materially | **Yes, for narrow stops** | 20 sessions beat 10 by about +0.03R to +0.07R gross at 3% to 8% stops; at 2% the difference is within noise |
| HD5 | Data defects distort results | **Found and handled** | DG-0 (§3): 3 unadjusted corporate actions, 1 bad bar, 4 special sessions |
| HD6 | The delivery cost schedule is wrong | **Small effect** | DG-6: the exchange rate (0.00297% or 0.00307%) changes net R by under 0.001R; brokerage 0 raises it by about 0.05R, a cap of ₹40 changes it by about 0.001R. Rates are one date's published values |
| HD7 | The simulator has a defect | **One design defect found and fixed** | DG-4: 20 of 20 agree. Separately, the slippage sensitivity was not monotone, which exposed sizing at the fill (plan §8.2); fixed to match TRD-05 and re-run |

## 3. DG-0: data audit

- **Coverage:** 44 stocks from 2015-01-01 to 2026-11-19; INDIGO from 2015-11, SBILIFE and HDFCLIFE from 2017, MAXHEALTH from 2020, ETERNAL from 2021, JIOFIN from 2023 (their listing dates). JIOFIN has no in-sample sessions.
- **Adjustment:** no gap looks like an unadjusted split or bonus, so the provider's daily bars are **adjusted for splits and bonuses**. They are **not consistently adjusted for demergers and mergers**:

| Event | Finding | Handling |
|---|---|---|
| ADANIENT 2015-06-03 | Demerger ex-date; the open (555.80) is an unadjusted print, the low and close are post-demerger ([Business Standard](https://www.business-standard.com/article/pti-stories/adani-enterprises-shares-fall-on-demerger-115060300960_1.html)) | The bar is dropped and the series is cut there |
| ADANIENT 2018-09-06 | Adani Gas demerger ex-date, -28.9% gap ([Business Standard](https://www.business-standard.com/amp/article/markets/adani-enterprises-trade-ex-date-for-spin-off-rebounds-15-from-day-s-low-118090600280_1.html)) | Series cut |
| GRASIM 2017-07-19 | Spin-off of the financial business, -18.2% gap while peers were flat ([Business Standard](https://www.business-standard.com/article/markets/grasim-industries-trades-ex-date-for-spin-off-117071900238_1.html)) | Series cut |
| ONGC 2020-03-23 | -16.1% gap on the COVID crash day (TRENT -12.5%, TATASTEEL -11.3%, others near -10%) | Genuine; kept |

- **Special sessions:** 2015-02-28 (Budget Saturday), 2016-10-30, 2017-10-19 and 2018-11-07 (Diwali Muhurat) exist for only one or two stocks; excluded from every series.
- **Missing sessions:** one (ADANIENT, the dropped bar); no OHLC defects; no non-positive prices.
- **Limit:** only gaps above 15% (or split-like) are flagged. A smaller unadjusted spin-off would look like an ordinary fall.

## 4. DG-1 and DG-2

Drift (gross, % per entry, no costs; hold 20 sessions by year): 2015: -0.53, 2016: +1.31, 2017: +2.51, 2018: -0.22, 2019: +1.29, 2020: +2.58, 2021: +2.73, 2022: -2.77. All stocks pooled and the equal-weight basket give nearly the same figures. This is today's NIFTY 50 (survivorship) over a period that was largely rising, so the level is an upper bound.

Friction at the planning values (risk ₹500, position cap ₹50,000, slippage 0.05% each side, Groww delivery charges):

| Stop | Position | Charges | Slippage | Friction |
|---|---|---|---|---|
| 2% | ₹25,000 | ₹127 | ₹25 | 0.30R |
| 3% | ₹16,667 | ₹100 | ₹17 | 0.23R |
| 4% | ₹12,500 | ₹81 | ₹12 | 0.19R |
| 5% | ₹10,000 | ₹69 | ₹10 | 0.16R |
| 8% | ₹6,250 | ₹52 | ₹6 | 0.12R |

## 5. DG-3: random-entry baseline grid (the bar a strategy must beat)

One random signal session per stock, month and seed (5 seeds), in-sample; stop below the signal close, target in risks above it, time stop; R measured against the **planned risk** (plan §8.2). The last column is the pre-registered basis (R against the risk at the fill), kept because it is what was registered; it is noisier.

| Stop | Target | Hold | Trades | Gross R | Net R [95% interval] | Net R, fill-risk basis (run 2) |
|---|---|---|---|---|---|---|
| 2% | none | 10 | 19,719 | +0.020 | -0.253 [-0.361, -0.140] | -0.235 |
| 2% | none | 20 | 19,714 | +0.110 | -0.162 [-0.326, +0.007] | -0.182 |
| 2% | 2.5R | 10 | 19,719 | -0.013 | -0.286 [-0.355, -0.217] | -0.270 |
| 2% | 2.5R | 20 | 19,715 | +0.000 | -0.272 [-0.345, -0.199] | -0.257 |
| 2% | 4R | 10 | 19,719 | +0.016 | -0.257 [-0.344, -0.165] | -0.238 |
| 2% | 4R | 20 | 19,715 | +0.043 | -0.229 [-0.337, -0.121] | -0.224 |
| 3% | none | 10 | 19,719 | +0.047 | -0.160 [-0.249, -0.064] | -0.122 |
| 3% | none | 20 | 19,714 | +0.117 | -0.090 [-0.227, +0.047] | -0.066 |
| 3% | 2.5R | 10 | 19,720 | +0.027 | -0.179 [-0.252, -0.103] | -0.165 |
| 3% | 2.5R | 20 | 19,715 | +0.061 | -0.146 [-0.239, -0.054] | -0.135 |
| 3% | 4R | 10 | 19,720 | +0.034 | -0.172 [-0.256, -0.085] | -0.168 |
| 3% | 4R | 20 | 19,713 | +0.109 | -0.098 [-0.216, +0.019] | -0.090 |
| 5% | none | 10 | 19,720 | +0.065 | -0.080 [-0.147, -0.010] | -0.076 |
| 5% | none | 20 | 19,715 | +0.120 | -0.024 [-0.135, +0.085] | -0.008 |
| 5% | 2.5R | 10 | 19,720 | +0.051 | -0.093 [-0.156, -0.028] | -0.075 |
| 5% | 2.5R | 20 | 19,715 | +0.106 | -0.038 [-0.136, +0.059] | -0.019 |
| 5% | 4R | 10 | 19,720 | +0.056 | -0.088 [-0.155, -0.019] | -0.062 |
| 5% | 4R | 20 | 19,715 | +0.118 | -0.026 [-0.135, +0.082] | +0.001 |
| 8% | none | 10 | 19,428 | +0.058 | -0.052 [-0.103, -0.002] | -0.039 |
| 8% | none | 20 | 19,422 | +0.122 | +0.012 [-0.075, +0.096] | +0.016 |
| 8% | 2.5R | 10 | 19,428 | +0.058 | -0.052 [-0.101, -0.004] | -0.047 |
| 8% | 2.5R | 20 | 19,424 | +0.112 | +0.002 [-0.081, +0.083] | +0.011 |
| 8% | 4R | 10 | 19,427 | +0.057 | -0.053 [-0.101, -0.005] | -0.042 |
| 8% | 4R | 20 | 19,423 | +0.117 | +0.007 [-0.077, +0.090] | +0.011 |

- **Slippage sensitivity** (net R, 0% / 0.05% / 0.10% per side), 20-session hold, no target: stop 2% -0.110 / -0.162 / -0.214; 3% -0.056 / -0.090 / -0.124; 5% -0.004 / -0.024 / -0.045; 8% +0.025 / +0.012 / -0.001.
- **Charges sensitivity** (5% stop, 20-session hold, no target; net R, fill-risk basis): base -0.014; exchange rate 0.00297% -0.014; brokerage cap ₹0 +0.035; cap ₹40 -0.014.
- **DG-5 survivorship sensitivity:** the 44 full-history stocks against all 50: the difference in net R is within ±0.02R and every interval includes zero. This is a weak test (all 50 are today's constituents).
- **Fills inside half the planned stop** (open gapped down toward the stop): 125 to 812 of about 19,400 to 19,700 trades per configuration, most at 2% stops.

## 6. What the plan's rules say

| Rule | Reading |
|---|---|
| Random long entries with net R above zero (interval above zero) in some configuration | **Not met**: no configuration has a net interval above zero; the best (5% to 8% stops, 20 sessions) is about zero with intervals from -0.13 to +0.10 |
| Baselines near 0R gross and negative net: friction sets the bar | **Partly**: gross is +0.05R to +0.12R at wide stops, net about 0; narrow stops are clearly negative |
| DG-5 material difference | Not met |
| History shorter than 1,250 sessions | Not met (2,936 sessions) |
| DG-0 or DG-4 defects | DG-0 defects handled with a rerun; DG-4 agrees; the sizing defect fixed and re-run (plan §8.2) |

**Bar for a first daily screen:** to be worth a pre-registered screen a strategy must beat its matched baseline by at least 0.05R (detectable), and to clear the validation criterion (net above 0.10R, [criteria §3](validation-criteria.md#3-research_validated-proposed)) it needs about +0.09R to +0.13R over a 5% to 8% stop baseline held 20 sessions. Narrow-stop daily setups (about 2%) start 0.16R to 0.29R below zero and are not attractive.

## 7. For the owner

1. **Continue the track or stop.** The framework is sound enough to screen entries; the baseline is about zero net at wide stops, so any edge must be real. The first step would be a pre-registered screen (a fixed family, a matched control per variant, a stricter interval for the number tried, as the intraday fast screen) restricted to setups with stops of about 5% or more, held up to 20 sessions. It needs its own approval; nothing is started.
2. **Decide on the R basis.** The pre-registered R (against the fill risk) is fragile when the open gaps toward the stop; the planned-risk basis is bounded and consistent. I recommend the planned-risk basis for all later daily work. The ruleset and the intraday engine are unchanged.
3. **Optional:** measure real slippage (the 0.05% per side assumption costs 0.02R to 0.04R per 0.05%) and confirm historical delivery rates.

## 8. Limitations

- Today's NIFTY 50 over 2015 to 2022 (`survivorship_bias_risk`); a rising period; costs `costs_unverified` (one date's published rates, two pages disagree on one rate); slippage an assumption.
- Unadjusted spin-offs under 15% would not be flagged; unadjusted ones above were handled by hand.
- Random baselines say nothing about any entry rule. Intervals resample about 85 calendar months, so they are wide.
- **Disclosure:** before the plan was drafted, one data-quality query listed the largest overnight gaps across all stored daily bars, including dates later than the in-sample end (it showed SHRIRAMFIN 2026-01-01). No performance statistic was computed from those bars, and every Gate 0 run loaded prices only up to the in-sample end.
- Three runs were made: run 1 (as registered, found the data defects), run 2 (after the data fixes, exposed the sizing and R-basis fragility), run 3 (sizing fixed, planned-risk R added). All are kept outside the repository; the figures here are run 3, and the fill-risk basis of run 2 is shown beside them.
