"""Daily-timeframe simulator, random-entry baselines and data audit helpers (Gate 0, docs/research/gate0-...).

Everything works on one stock's daily bars (`DayBar`, chronological). A signal at the close of session `s`
fills at the open of `s + 1`; the fill session counts as the first held session. No entry rule lives here:
only the machinery a later strategy is judged on.
"""

from __future__ import annotations

import itertools
import random
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.backtest.costs import DeliverySchedule, delivery_costs

D = Decimal
RISK_UNIT = D(500)
POSITION_CAP = D(50000)
MAX_REDRAWS = 20
GAP_FLAG_PCT = 0.15
SPLIT_DENOMINATORS = (2, 3, 4, 5, 10)  # the signature of an unadjusted split or bonus: ratio near 1/k
SPLIT_TOLERANCE = 0.03
SLIPPAGE_PCT = D("0.05")
MAX_GAP_UP_PCT = D(1)  # a fill is skipped when the open is more than this above the signal close
IN_SAMPLE_SHARE = D("0.6")


@dataclass(frozen=True, slots=True)
class DayBar:
    day: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal


@dataclass(frozen=True, slots=True)
class DailyRules:
    slippage_pct: Decimal = SLIPPAGE_PCT
    max_gap_up_pct: Decimal = MAX_GAP_UP_PCT
    risk_unit: Decimal = RISK_UNIT
    position_cap: Decimal = POSITION_CAP


@dataclass(frozen=True, slots=True)
class DailyTrade:
    symbol: str
    signal_day: date
    fill_day: date
    exit_day: date
    entry: Decimal
    exit: Decimal
    qty: int
    reason: str  # STOP, STOP_GAP, STOP_COLLISION, TARGET, TARGET_GAP, TIME_STOP, END_OF_DATA
    stop: Decimal
    hold_sessions: int
    gross_pnl: Decimal
    costs: Decimal
    risk: Decimal  # at the fill: qty * (entry - stop)
    ref: Decimal  # the signal close the order was planned from

    @property
    def r_gross(self) -> Decimal:
        return self.gross_pnl / self.risk

    @property
    def r_net(self) -> Decimal:
        return (self.gross_pnl - self.costs) / self.risk

    @property
    def planned_risk(self) -> Decimal:
        """Risk the order was planned with: qty * (signal close - stop). Unlike `risk` it does not shrink when
        the open gaps down toward the stop, so R measured against it stays bounded."""
        return self.qty * (self.ref - self.stop)

    @property
    def r_gross_planned(self) -> Decimal:
        return self.gross_pnl / self.planned_risk

    @property
    def r_net_planned(self) -> Decimal:
        return (self.gross_pnl - self.costs) / self.planned_risk


def fill_entry(nxt: DayBar, ref: Decimal, stop: Decimal, rules: DailyRules) -> tuple[Decimal, int] | None:
    """Entry price and quantity for a signal whose close was `ref`, filled at the open of `nxt`; `None` when
    skipped: the open is at or below the stop, more than `max_gap_up_pct` above `ref`, or size rounds to 0.
    The quantity is planned from `ref` and **never increased at the fill** (TRD-05 section 7.1): a higher open
    can only reduce it, a lower open leaves it unchanged."""
    if nxt.open <= stop or nxt.open > ref * (1 + rules.max_gap_up_pct / 100):
        return None
    entry = nxt.open * (1 + rules.slippage_pct / 100)
    if entry <= stop or ref <= stop:
        return None
    planned = int(rules.risk_unit // (ref - stop))
    qty = min(planned, int(rules.risk_unit // (entry - stop)), int(rules.position_cap // entry))
    return (entry, qty) if qty >= 1 else None


def run_daily(
    bars: Sequence[DayBar],
    s: int,
    symbol: str,
    ref: Decimal,
    stop: Decimal,
    target: Decimal | None,
    hold: int,
    rules: DailyRules,
    schedule: DeliverySchedule,
) -> DailyTrade | None:
    """Fill at the open of `s + 1` and hold until the first exit: an open at or below the stop (gap), an open
    at or above the target (gap), the intraday stop (adverse slippage; a session touching stop and target
    counts as the stop), the target (no slippage), or the close of the `hold`-th session from the fill
    session (adverse slippage). Bars running out before that exit at the last close (`END_OF_DATA`)."""
    if s + 1 >= len(bars):
        return None
    filled = fill_entry(bars[s + 1], ref, stop, rules)
    if filled is None:
        return None
    entry, qty = filled
    slip = rules.slippage_pct / 100
    for j in range(s + 1, len(bars)):
        b = bars[j]
        price: Decimal | None = None
        reason = ""
        if j > s + 1 and b.open <= stop:
            price, reason = b.open * (1 - slip), "STOP_GAP"
        elif target is not None and j > s + 1 and b.open >= target:
            price, reason = b.open, "TARGET_GAP"
        elif b.low <= stop:
            price = stop * (1 - slip)
            reason = "STOP_COLLISION" if target is not None and b.high >= target else "STOP"
        elif target is not None and b.high >= target:
            price, reason = target, "TARGET"
        elif j - s == hold:
            price, reason = b.close * (1 - slip), "TIME_STOP"
        if price is not None:
            return _trade(symbol, bars, s, j, entry, price, qty, reason, stop, ref, schedule)
    return _trade(
        symbol, bars, s, len(bars) - 1, entry, bars[-1].close, qty, "END_OF_DATA", stop, ref, schedule
    )


def _trade(
    symbol: str,
    bars: Sequence[DayBar],
    s: int,
    j: int,
    entry: Decimal,
    exit_price: Decimal,
    qty: int,
    reason: str,
    stop: Decimal,
    ref: Decimal,
    schedule: DeliverySchedule,
) -> DailyTrade:
    gross = (exit_price - entry) * qty
    costs = delivery_costs(entry * qty, exit_price * qty, schedule).total
    return DailyTrade(
        symbol, bars[s].day, bars[s + 1].day, bars[j].day, entry, exit_price, qty, reason, stop,
        j - s, gross, costs, qty * (entry - stop), ref,
    )  # fmt: skip


def segment_at(bars: Sequence[DayBar], breaks: Sequence[date]) -> list[list[DayBar]]:
    """Split a series before the first session on or after each break date (a corporate action the provider
    does not adjust: demerger, merger). No trade or holding window crosses a break."""
    out: list[list[DayBar]] = [[]]
    pending = sorted(breaks)
    for b in bars:
        while pending and b.day >= pending[0]:
            pending.pop(0)
            if out[-1]:
                out.append([])
        out[-1].append(b)
    return [seg for seg in out if seg]


def eligible_signals(bars: Sequence[DayBar], hold: int) -> list[int]:
    """Signal sessions whose whole holding window lies inside `bars` (so a trade never reads past the
    in-sample end)."""
    return list(range(len(bars) - 1 - hold))


def month_key(d: date) -> tuple[int, int]:
    return d.year, d.month


def month_pool(bars: Sequence[DayBar], hold: int, month: tuple[int, int]) -> list[int]:
    """Eligible signal sessions that fall in the calendar `month`."""
    return [s for s in eligible_signals(bars, hold) if month_key(bars[s].day) == month]


def draw_baseline(
    bars: Sequence[DayBar],
    symbol: str,
    month: tuple[int, int],
    stop_pct: Decimal,
    target_r: Decimal | None,
    hold: int,
    seed_key: str,
    rules: DailyRules,
    schedule: DeliverySchedule,
    pool: Sequence[int] | None = None,
) -> tuple[DailyTrade | None, int]:
    """One random-entry baseline trade for `symbol` in calendar `month`: a uniformly random signal session of
    that month, stop `stop_pct` below the signal close, target `target_r` risks above it (or none). A skipped
    fill is redrawn up to `MAX_REDRAWS` times. Returns the trade (or `None`) and the number of redraws.
    `pool` may carry the precomputed `month_pool` (a speed-up only)."""
    pool = month_pool(bars, hold, month) if pool is None else pool
    rng = random.Random(seed_key)  # noqa: S311 - research sampling, not security
    redraws = 0
    while pool and redraws <= MAX_REDRAWS:
        s = rng.choice(pool)
        ref = bars[s].close
        stop = ref * (1 - stop_pct / 100)
        target = ref + target_r * (ref - stop) if target_r is not None else None
        t = run_daily(bars, s, symbol, ref, stop, target, hold, rules, schedule)
        if t is not None:
            return t, redraws
        redraws += 1
    return None, redraws


def drift_returns(bars: Sequence[DayBar], hold: int) -> list[tuple[date, float]]:
    """DG-1: for each signal session, `(fill day, close of the hold-th session / fill open - 1)` in percent,
    gross, no stop or target, no costs."""
    out: list[tuple[date, float]] = []
    for s in eligible_signals(bars, hold):
        buy, sell = bars[s + 1].open, bars[s + hold].close
        out.append((bars[s + 1].day, float((sell / buy - 1) * 100)))
    return out


# --- data audit (DG-0) -------------------------------------------------------------------------------------


def gap_flags(bars: Sequence[DayBar]) -> list[tuple[date, float, str]]:
    """Overnight gaps (`open / previous close - 1`) above 15% in size, or whose open/close ratio is within 3%
    of 1/2, 1/3, 1/4, 1/5 or 1/10: `(day, gap, why)`."""
    out: list[tuple[date, float, str]] = []
    for prev, cur in itertools.pairwise(bars):
        if prev.close <= 0:
            continue
        ratio = float(cur.open / prev.close)
        why = []
        if abs(ratio - 1) > GAP_FLAG_PCT:
            why.append("GAP_OVER_15PCT")
        if any(abs(ratio * k - 1) <= SPLIT_TOLERANCE for k in SPLIT_DENOMINATORS):
            why.append("SPLIT_SIGNATURE")
        if why:
            out.append((cur.day, ratio - 1, "+".join(why)))
    return out


def ohlc_defects(bars: Sequence[DayBar]) -> list[tuple[date, str]]:
    out: list[tuple[date, str]] = []
    for b in bars:
        if min(b.open, b.high, b.low, b.close) <= 0:
            out.append((b.day, "NON_POSITIVE_PRICE"))
        elif not (b.low <= b.open <= b.high and b.low <= b.close <= b.high):
            out.append((b.day, "OHLC_INCONSISTENT"))
    return out


def missing_sessions(calendar: Sequence[date], days: Sequence[date]) -> list[date]:
    """Sessions in the union `calendar` on or after the stock's first date that the stock lacks."""
    if not days:
        return []
    have, first = set(days), min(days)
    return [d for d in calendar if d >= first and d not in have]


def in_sample_last_date(calendar: Sequence[date], share: Decimal = IN_SAMPLE_SHARE) -> date:
    """Last in-sample session of the chronological split, from the session dates alone (no prices)."""
    ordered = sorted(set(calendar))
    return ordered[int(len(ordered) * share) - 1]


def verify_daily_trade(bars: Sequence[DayBar], t: DailyTrade, slippage_pct: Decimal) -> list[str]:
    """Recompute a trade's fill and exit from the raw bars with separate logic; list mismatches. `TARGET`
    exits are checked for plausibility only (the target is not stored on the trade)."""
    days = {b.day: k for k, b in enumerate(bars)}
    if t.fill_day not in days or t.exit_day not in days:
        return ["trade days missing from the bars"]
    out: list[str] = []
    i, j = days[t.fill_day], days[t.exit_day]
    slip = slippage_pct / 100
    if t.entry != bars[i].open * (1 + slip):
        out.append("entry != fill-session open plus slippage")
    for k in range(i, j):  # no session before the exit may have touched the stop
        if (k > i and bars[k].open <= t.stop) or bars[k].low <= t.stop:
            out.append(f"stop touched before the exit on {bars[k].day}")
    b = bars[j]
    if t.reason == "STOP" and abs(t.exit - t.stop * (1 - slip)) > D("0.000001"):
        out.append("stop exit price")
    if t.reason == "STOP_GAP" and abs(t.exit - b.open * (1 - slip)) > D("0.000001"):
        out.append("gap exit price")
    if t.reason == "TIME_STOP":
        if t.hold_sessions != j - days[t.signal_day]:
            out.append("hold length")
        if abs(t.exit - b.close * (1 - slip)) > D("0.000001"):
            out.append("time-stop exit price")
    if t.reason in ("TARGET", "TARGET_GAP") and b.high < t.exit:
        out.append("target above the exit session's high")
    if abs((t.exit - t.entry) * t.qty - t.gross_pnl) > D("0.000001"):
        out.append("gross P&L")
    return out
