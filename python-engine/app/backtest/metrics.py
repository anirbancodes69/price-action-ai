"""Performance metrics (TRD-06 §10). Reporting arithmetic, not trading rules."""

from __future__ import annotations

import statistics
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from app.backtest.replay import SessionResult
from app.backtest.trade import Trade

IST = timedelta(hours=5, minutes=30)
LOW_SAMPLE_TRADES, LOW_SAMPLE_SESSIONS = 30, 60  # TRD-06 §10


@dataclass(frozen=True, slots=True)
class GroupStats:
    trades: int
    win_rate: Decimal | None
    avg_r_net: Decimal | None
    net_pnl: Decimal


@dataclass(frozen=True, slots=True)
class Metrics:
    trades: int
    sessions: int
    win_rate: Decimal | None
    avg_r_net: Decimal | None
    avg_r_gross: Decimal | None
    profit_factor: Decimal | None  # None when there is no losing trade
    max_drawdown: Decimal  # rupees, end-of-session equity
    max_drawdown_pct: Decimal
    mean_session_pnl: Decimal | None
    median_session_pnl: Decimal | None
    worst_session_pnl: Decimal | None
    sessions_account_blocked_pct: Decimal | None
    sharpe_daily: Decimal | None
    exposure_pct: Decimal | None
    avg_minutes_in_trade: Decimal | None
    exit_mix: dict[str, int]
    skips: dict[str, int]
    cost_drag: Decimal | None
    by_setup: dict[str, GroupStats]
    by_half_hour: dict[str, GroupStats]
    by_context_15m: dict[str, GroupStats]
    by_month: dict[str, GroupStats]
    low_sample: bool
    end_of_data_trades: int


def _mean(xs: Sequence[Decimal]) -> Decimal | None:
    return sum(xs, Decimal(0)) / len(xs) if xs else None


def _group(trades: Sequence[Trade]) -> GroupStats:
    wins = sum(1 for t in trades if t.net_pnl > 0)
    return GroupStats(
        len(trades),
        Decimal(wins) / len(trades) if trades else None,
        _mean([t.r_net for t in trades]),
        sum((t.net_pnl for t in trades), Decimal(0)),
    )


def _grouped(trades: Sequence[Trade], key: Callable[[Trade], str]) -> dict[str, GroupStats]:
    buckets: dict[str, list[Trade]] = defaultdict(list)
    for t in trades:
        buckets[key(t)].append(t)
    return {k: _group(v) for k, v in sorted(buckets.items())}


def equity_curve(sessions: Sequence[SessionResult], capital: Decimal) -> list[Decimal]:
    """End-of-session equity, starting with the initial capital."""
    eq = [capital]
    for s in sessions:
        eq.append(eq[-1] + s.net_pnl)
    return eq


def max_drawdown(curve: Sequence[Decimal]) -> tuple[Decimal, Decimal]:
    """Largest peak-to-trough fall: rupees and percent of the peak."""
    peak, worst, worst_pct = curve[0], Decimal(0), Decimal(0)
    for v in curve:
        peak = max(peak, v)
        dd = peak - v
        if dd > worst:
            worst, worst_pct = dd, dd / peak * 100
    return worst, worst_pct


def _exposure(session: SessionResult) -> Decimal:
    spans = sorted((t.fill_at, t.exit_at) for t in session.trades)
    covered = timedelta(0)
    cur_start: datetime | None = None
    cur_end: datetime | None = None
    for a, b in spans:
        if cur_end is None or a > cur_end:
            if cur_start is not None and cur_end is not None:
                covered += cur_end - cur_start
            cur_start, cur_end = a, b
        else:
            cur_end = max(cur_end, b)
    if cur_start is not None and cur_end is not None:
        covered += cur_end - cur_start
    length = session.spec.session_close - session.spec.session_open
    return Decimal(covered.total_seconds()) / Decimal(length.total_seconds())


def compute_metrics(
    sessions: Sequence[SessionResult],
    capital: Decimal,
    include_end_of_data: bool = False,
) -> Metrics:
    all_trades = [t for s in sessions for t in s.trades]
    eod = sum(1 for t in all_trades if t.end_of_data)
    trades = all_trades if include_end_of_data else [t for t in all_trades if not t.end_of_data]
    pnls = [t.net_pnl for t in trades]
    gross_pos = sum((p for p in pnls if p > 0), Decimal(0))
    gross_neg = -sum((p for p in pnls if p < 0), Decimal(0))
    curve = equity_curve(sessions, capital)
    dd, dd_pct = max_drawdown(curve)
    session_pnl = [s.net_pnl for s in sessions]
    returns = [p / capital for p in session_pnl]
    sharpe: Decimal | None = None
    if len(returns) >= 2:
        sd = statistics.stdev(returns)
        if sd > 0:
            sharpe = statistics.mean(returns) / sd * Decimal(252).sqrt()
    skips: dict[str, int] = defaultdict(int)
    for s in sessions:
        for k in s.skips:
            skips[k.reason] += 1
    mix: dict[str, int] = defaultdict(int)
    for t in trades:
        mix[t.reason] += 1
    gross_abs = sum((abs(t.gross_pnl) for t in trades), Decimal(0))
    blocked = sum(1 for s in sessions if any(k.reason == "ACCOUNT_LIMIT" for k in s.skips))
    n_sessions = len(sessions)
    return Metrics(
        trades=len(trades),
        sessions=n_sessions,
        win_rate=Decimal(sum(1 for p in pnls if p > 0)) / len(pnls) if pnls else None,
        avg_r_net=_mean([t.r_net for t in trades]),
        avg_r_gross=_mean([t.r_gross for t in trades]),
        profit_factor=gross_pos / gross_neg if gross_neg > 0 else None,
        max_drawdown=dd,
        max_drawdown_pct=dd_pct,
        mean_session_pnl=_mean(session_pnl),
        median_session_pnl=statistics.median(session_pnl) if session_pnl else None,
        worst_session_pnl=min(session_pnl) if session_pnl else None,
        sessions_account_blocked_pct=Decimal(blocked) / n_sessions * 100 if n_sessions else None,
        sharpe_daily=sharpe,
        exposure_pct=_mean([_exposure(s) for s in sessions]) if sessions else None,
        avg_minutes_in_trade=_mean([Decimal((t.exit_at - t.fill_at).total_seconds()) / 60 for t in trades]),
        exit_mix=dict(sorted(mix.items())),
        skips=dict(sorted(skips.items())),
        cost_drag=sum((t.costs for t in trades), Decimal(0)) / gross_abs if gross_abs > 0 else None,
        by_setup=_grouped(trades, lambda t: t.setup_type),
        by_half_hour=_grouped(trades, _half_hour),
        by_context_15m=_grouped(trades, lambda t: t.context_15m),
        by_month=_grouped(trades, lambda t: (t.fill_at + IST).strftime("%Y-%m")),
        low_sample=len(trades) < LOW_SAMPLE_TRADES or n_sessions < LOW_SAMPLE_SESSIONS,
        end_of_data_trades=eod,
    )


def _half_hour(t: Trade) -> str:
    local = t.fill_at + IST
    return f"{local.hour:02d}:{30 if local.minute >= 30 else 0:02d}"
