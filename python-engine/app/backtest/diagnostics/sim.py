"""Common exit simulation, matched random-entry controls and forward returns (plan §4: DX-1..DX-5).

All functions work on one instrument-session: `bars` are that session's closed 5m bars, chronological. Exits
reuse `step_position` and `close_trade`, so a control is judged by the same exit and cost code as a strategy.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal

from app.backtest.costs import CostSchedule
from app.backtest.trade import ExitConfig, Position, Trade, close_trade, step_position
from app.domain.params import RulesetParams
from app.domain.risk.fill import simulate_entry
from app.domain.types import Bar
from app.ingestion.session import IST

D = Decimal
RISK_UNIT = D(500)
NO_VALUE_LIMIT = D(10) ** 12  # 4a lifts the position-value limit
TARGET_R = D("2.5")  # common target for strategy entries and controls (plan §4a item 1)
HORIZONS = (3, 6, 12)  # bars after the signal bar's close (DX-2)
MAX_REDRAWS = 20
OPEN_END = time(9, 30)  # opening range ends: 09:15 + session.opening_range_minutes


@dataclass(frozen=True, slots=True)
class Rules:
    """Session-independent numbers taken from the ruleset (nothing is tuned here)."""

    slippage_pct: Decimal
    min_rr: Decimal
    max_gap_pct: Decimal
    cutoff_minutes: int
    exit_minutes: int
    risk_unit: Decimal = RISK_UNIT


def rules_from(p: RulesetParams, risk_unit: Decimal = RISK_UNIT) -> Rules:
    return Rules(
        p.decimal("backtest.slippage_pct"),
        p.decimal("risk.min_rr"),
        p.decimal("risk.max_entry_gap_pct"),
        p.int_("session.entry_cutoff_minutes_before_close"),
        p.int_("session.exit_minutes_before_close"),
        risk_unit,
    )


def session_times(
    bars: Sequence[Bar], rules: Rules, close_time: time = time(15, 30)
) -> tuple[datetime, datetime, datetime]:
    """(opening-range end, entry cutoff, session-exit time) on the bars' own date and zone."""
    day = bars[0].start.astimezone(IST).date()
    close = datetime.combine(day, close_time, IST)
    or_end = datetime.combine(day, OPEN_END, IST)
    cutoff = close - timedelta(minutes=rules.cutoff_minutes)
    return or_end, cutoff, close - timedelta(minutes=rules.exit_minutes)


def exit_config(rules: Rules, exit_time: datetime, *, stop_slippage: bool = True) -> ExitConfig:
    slip = rules.slippage_pct if stop_slippage else D(0)
    return ExitConfig(slip, exit_time, True, False)


def simulate(
    bars: Sequence[Bar],
    i: int,
    symbol: str,
    entry: Decimal,
    stop: Decimal,
    qty: int,
    target: Decimal,
    cfg: ExitConfig,
    schedule: CostSchedule,
    *,
    optimistic: bool = False,
    horizon: int | None = None,
) -> Trade:
    """Hold from the fill bar `i` to the first exit. `optimistic`: a bar touching stop and target takes the
    target (BT-04 upper bound). `horizon`: exit at the close of the `horizon`-th bar from the fill bar, with
    no target (the stop and session end still apply)."""
    pos = Position(symbol, "DIAG", 0, "", qty, entry, stop, target, bars[i].start, bars[i].start)
    if horizon is not None:
        pos = Position(symbol, "DIAG", 0, "", qty, entry, stop, entry * 1000, bars[i].start, bars[i].start)
    for j in range(i, len(bars)):
        ex = step_position(pos, bars[j], cfg)
        if ex is not None:
            price, reason = ex
            if optimistic and reason == "STOP_COLLISION":
                price, reason = pos.target, "TARGET"
            return close_trade(pos, price, bars[j].start, reason, schedule)
        if horizon is not None and j - i + 1 == horizon:
            return close_trade(pos, bars[j].close, bars[j].end, "HORIZON", schedule)
    last = bars[-1]
    return close_trade(pos, last.close, last.end, "END_OF_DATA", schedule, True)


def exit_price_at(bars: Sequence[Bar], exit_time: datetime) -> Decimal:
    """Open of the first bar starting at the session-exit time, else the last close."""
    for b in bars:
        if b.start >= exit_time:
            return b.open
    return bars[-1].close


def forward_returns(
    bars: Sequence[Bar], i: int, entry: Decimal, stop: Decimal, exit_time: datetime
) -> dict[str, tuple[float, float]]:
    """From the fill price to the close `h` bars after the signal bar (the fill bar is the first of them) and
    to the session exit, with no stop or target: `(percent, in units of the stop distance)` (DX-2)."""
    dist = entry - stop
    out: dict[str, tuple[float, float]] = {}
    ends = {f"h{h}": bars[i + h - 1].close for h in HORIZONS if i + h - 1 < len(bars)}
    ends["session"] = exit_price_at(bars, exit_time)
    for k, px in ends.items():
        out[k] = (float((px - entry) / entry * 100), float((px - entry) / dist))
    return out


@dataclass(frozen=True, slots=True)
class Control:
    trade: Trade
    fill_index: int
    forward: dict[str, tuple[float, float]]
    redraws: int


def eligible_signal_bars(bars: Sequence[Bar], or_end: datetime, cutoff: datetime) -> list[int]:
    """Signal bars that close at or after the opening range ends, with the next bar starting before cutoff."""
    return [s for s in range(len(bars) - 1) if bars[s].end >= or_end and bars[s + 1].start < cutoff]


def fill_and_run(
    bars: Sequence[Bar],
    s: int,
    symbol: str,
    ref: Decimal,
    stop: Decimal,
    rules: Rules,
    schedule: CostSchedule,
    target_r: Decimal = TARGET_R,
    unlimited_value: Decimal = NO_VALUE_LIMIT,
) -> Control | None:
    """A signal at the close of bar `s` with reference entry `ref` and `stop`: fill at the next open by the
    real fill rule (`simulate_entry`), then the common exit. `None` when the fill is skipped."""
    _, cutoff, exit_time = session_times(bars, rules)
    if s + 1 >= len(bars) or ref <= stop:
        return None
    target = ref + target_r * (ref - stop)
    plan = int(rules.risk_unit // (ref - stop))
    fill = simulate_entry(
        bars[s + 1].open, ref, stop, target, plan, rules.risk_unit, unlimited_value, rules.min_rr,
        rules.max_gap_pct, bars[s + 1].start, cutoff, rules.slippage_pct,
    )  # fmt: skip
    if not fill.filled or fill.price is None:
        return None
    cfg = exit_config(rules, exit_time)
    t = simulate(bars, s + 1, symbol, fill.price, stop, fill.qty, target, cfg, schedule)
    return Control(t, s + 1, forward_returns(bars, s + 1, fill.price, stop, exit_time), 0)


def draw_control(
    bars: Sequence[Bar],
    symbol: str,
    stop_pct: Decimal,
    rng: random.Random,
    rules: Rules,
    schedule: CostSchedule,
    after_index: int = 0,
    target_r: Decimal = TARGET_R,
    unlimited_value: Decimal = NO_VALUE_LIMIT,
) -> Control | None:
    """One control: a uniformly random eligible signal bar after `after_index` (the previous control's exit
    bar, so one position per symbol), filled by the same rule as a strategy; a skipped fill is redrawn (at
    most `MAX_REDRAWS` times). `None` when no bar qualifies."""
    or_end, cutoff, _ = session_times(bars, rules)
    pool = [s for s in eligible_signal_bars(bars, or_end, cutoff) if s + 1 > after_index]
    redraws = 0
    while pool and redraws <= MAX_REDRAWS:
        s = rng.choice(pool)
        ref = bars[s].close
        stop = ref * (1 - stop_pct / 100)
        c = fill_and_run(bars, s, symbol, ref, stop, rules, schedule, target_r, unlimited_value)
        if c is not None:
            return Control(c.trade, c.fill_index, c.forward, redraws)
        redraws += 1
    return None
