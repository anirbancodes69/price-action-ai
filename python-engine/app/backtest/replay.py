"""Bar-by-bar replay of one session over a set of instruments (TRD-06 §2, §4).

Signals are produced at a 5m close by the same `analyse` the live engine uses (BT-03), seeing only bars
that ended at or before that close (BT-01); entries fill at the next bar's open (BT-02).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from app.backtest.costs import CostSchedule
from app.backtest.slippage import SlippageModel
from app.backtest.trade import ExitConfig, Position, Trade, close_trade, step_position
from app.domain.analyse import AnalysisResult, analyse
from app.domain.audit import DecisionRecord, build_decision_records
from app.domain.params import RulesetParams
from app.domain.risk.account import (
    AccountState,
    ClosedTrade,
    OpenPosition,
    RiskProfile,
    check_account_limits,
    derive_account_state,
)
from app.domain.risk.fill import simulate_entry
from app.domain.risk.request import RiskRequest, RiskResult, calculate_risk
from app.domain.session import DailyLevels, entry_cutoff
from app.domain.setups.signal import Signal
from app.domain.setups.types import SetupDirection
from app.domain.snapshot import SnapshotStatus
from app.domain.types import Bar, Direction, EventType
from app.domain.zone_cache import ZoneCache


@dataclass(frozen=True, slots=True)
class SymbolData:
    """Closed bars for one instrument: lookback history plus the session, chronological."""

    symbol: str
    bars_5m: Sequence[Bar]
    bars_15m: Sequence[Bar]
    prev_day: DailyLevels | None
    # Required, no default. `None` means "do not round levels to a tick" (provider-adjusted price scale, D3).
    tick: Decimal | None
    lot_size: int = 1
    # Memo of zone builds across this symbol's analyses in a replay: a speed-up only, results are identical.
    zone_cache: ZoneCache = field(default_factory=ZoneCache, compare=False, repr=False)


@dataclass(frozen=True, slots=True)
class SessionSpec:
    session_date: date
    session_open: datetime
    session_close: datetime
    previous_session_open: datetime | None = None


@dataclass(frozen=True, slots=True)
class Skip:
    symbol: str
    setup_type: str
    signal_at: datetime
    reason: str


@dataclass(frozen=True, slots=True)
class SessionResult:
    spec: SessionSpec
    trades: tuple[Trade, ...]
    skips: tuple[Skip, ...]
    net_pnl: Decimal


AnalyseFn = Callable[[SymbolData, int, SessionSpec, RulesetParams], AnalysisResult]


def default_analyse(sym: SymbolData, k: int, spec: SessionSpec, params: RulesetParams) -> AnalysisResult:
    """Live analysis on the first `k` 5m bars and the 15m bars closed by then (BT-01)."""
    bars5 = list(sym.bars_5m[:k])
    bars15 = [b for b in sym.bars_15m if b.end <= bars5[-1].end]
    return analyse(
        bars5,
        bars15,
        spec.session_open,
        sym.prev_day,
        params,
        spec.previous_session_open,
        sym.tick,
        spec.session_close,
        sym.zone_cache,
    )


@dataclass(frozen=True, slots=True)
class _Order:
    symbol: str
    setup_type: str
    paqs: int
    context_15m: str
    qty: int
    entry_ref: Decimal
    stop: Decimal
    target: Decimal
    risk_budget: Decimal
    signal_at: datetime
    anchor: str = ""
    swept_level: Decimal | None = None


# Order for candidates closing on the same bar competing for slots: (session, paqs, symbol) -> key.
OrderKey = Callable[[SessionSpec, int, str], Any]


def score_then_symbol(_spec: SessionSpec, paqs: int, symbol: str) -> tuple[int, str]:
    """The combined-engine order: highest score first, then symbol (not acceptable for single strategies)."""
    return -paqs, symbol


def _skip_reason(blocked: str | None, errors: Sequence[str]) -> str:
    if blocked == "MAX_POSITIONS_REACHED":
        return blocked
    if blocked:
        return "ACCOUNT_LIMIT"
    return errors[0] if errors else "REJECTED"


def replay_session(
    symbols: Sequence[SymbolData],
    spec: SessionSpec,
    params: RulesetParams,
    profile: RiskProfile,
    schedule: CostSchedule,
    analyse_fn: AnalyseFn = default_analyse,
    order_key: OrderKey = score_then_symbol,
    decision_sink: Callable[[DecisionRecord], None] | None = None,
    slippage: SlippageModel | None = None,
) -> SessionResult:
    """Replay one session. `decision_sink` (Phase 1 P5) receives one `DecisionRecord` per evaluated setup at
    each bar close, read-only: it never changes a decision. Fill-time skips stay in `SessionResult.skips`."""
    cutoff = entry_cutoff(spec.session_close, params.int_("session.entry_cutoff_minutes_before_close"))
    exit_time = spec.session_close - timedelta(minutes=params.int_("session.exit_minutes_before_close"))
    ecfg = ExitConfig(
        params.decimal("backtest.slippage_pct"),
        exit_time,
        bool(params.get("exit.session_end_exit_enabled")),
        bool(params.get("exit.structure_exit_enabled")),
        slippage,
    )
    model = ecfg.model
    slip = model.entry  # entry slippage; exits use `model` per execution type
    min_rr = params.decimal("risk.min_rr")
    max_gap = params.decimal("risk.max_entry_gap_pct")

    by_sym = {s.symbol: s for s in symbols}
    # bar index (into bars_5m) by start time, restricted to this session
    index: dict[str, dict[datetime, int]] = {
        s.symbol: {
            b.start: i for i, b in enumerate(s.bars_5m) if spec.session_open <= b.start < spec.session_close
        }
        for s in symbols
    }
    timeline = sorted({t for m in index.values() for t in m})

    closed: list[Trade] = []
    skips: list[Skip] = []
    open_pos: dict[str, Position] = {}
    pending: list[_Order] = []
    last_idx: dict[str, int] = {}

    def state(extra_pending: int) -> AccountState:
        return derive_account_state(
            [ClosedTrade(t.net_pnl) for t in closed],
            [OpenPosition(p.entry_fill, p.stop, p.qty) for p in open_pos.values()],
            extra_pending,
        )

    for start in timeline:
        # A. fill orders created at the previous close, at this bar's open
        orders, pending = pending, []
        for n, o in enumerate(orders):
            i = index[o.symbol].get(start)
            if i is None:
                skips.append(Skip(o.symbol, o.setup_type, o.signal_at, "SKIPPED_NO_BAR"))
                continue
            bar = by_sym[o.symbol].bars_5m[i]
            blocked = check_account_limits(state(len(orders) - n - 1), profile, True, bar.end, cutoff)
            fill = simulate_entry(
                bar.open,
                o.entry_ref,
                o.stop,
                o.target,
                o.qty,
                o.risk_budget,
                profile.max_position_value,
                min_rr,
                max_gap,
                bar.start,
                cutoff,
                slip,
                blocked,
            )
            if not fill.filled or fill.price is None:
                skips.append(Skip(o.symbol, o.setup_type, o.signal_at, fill.reason or "SKIPPED"))
                continue
            open_pos[o.symbol] = Position(
                o.symbol,
                o.setup_type,
                o.paqs,
                o.context_15m,
                fill.qty,
                fill.price,
                o.stop,
                o.target,
                o.signal_at,
                bar.start,
                anchor=o.anchor,
                swept_level=o.swept_level,
            )
        # B. exits on this bar (fill bars included: stop checked first)
        for sym_name in list(open_pos):
            i = index[sym_name].get(start)
            if i is None:
                continue
            bar = by_sym[sym_name].bars_5m[i]
            ex = step_position(open_pos[sym_name], bar, ecfg)
            if ex:
                closed.append(
                    close_trade(open_pos.pop(sym_name), ex[0], bar.start, ex[1], schedule, slippage=model)
                )
        # C. analysis at the close of this bar
        cands: list[tuple[int, str, AnalysisResult]] = []
        analysed: dict[str, AnalysisResult] = {}
        risks: dict[str, RiskResult] = {}
        for s in symbols:
            i = index[s.symbol].get(start)
            if i is None:
                continue
            last_idx[s.symbol] = i
            res = analyse_fn(s, i + 1, spec, params)
            analysed[s.symbol] = res
            if res.check.status is not SnapshotStatus.VALID or res.signal is None:
                continue
            pos = open_pos.get(s.symbol)
            if (
                pos is not None
                and res.structure_5m is not None
                and any(
                    e.type is EventType.CHOCH and e.direction is Direction.DOWN and e.break_index == i
                    for e in res.structure_5m.events
                )
            ):
                open_pos[s.symbol] = replace(pos, structure_exit_pending=True)
            prim = res.signal.primary
            if res.signal.signal is Signal.ENTRY_CONFIRMED and prim is not None and prim.levels is not None:
                cands.append((prim.paqs.total if prim.paqs else 0, s.symbol, res))
        for paqs, name, res in sorted(cands, key=lambda c: order_key(spec, c[0], c[1])):
            prim = res.signal.primary if res.signal else None
            if prim is None or prim.levels is None:
                continue
            sig_at = res.signal.signal_at if res.signal else start
            stype = prim.setup.type.value
            if name in open_pos or any(o.symbol == name for o in pending):
                skips.append(Skip(name, stype, sig_at, "ALREADY_IN_POSITION"))
                continue
            sd = by_sym[name]
            lv = prim.levels
            req = RiskRequest(
                SetupDirection.LONG,
                lv.entry,
                lv.stop,
                lv.target if lv.target is not None else lv.entry,
                sd.tick,
                sd.lot_size,
                profile,
                state(len(pending)),
                True,
                sig_at,
                cutoff,
            )
            rr = calculate_risk(req, params)
            risks[name] = rr
            if not rr.ok or rr.sizing is None or rr.entry is None or rr.stop is None or rr.target is None:
                skips.append(Skip(name, stype, sig_at, _skip_reason(rr.blocked_reason, rr.errors)))
                continue
            h = res.htf.state.state.value if res.htf and res.htf.state else "NONE"
            pending.append(
                _Order(
                    name,
                    stype,
                    paqs,
                    h,
                    rr.sizing.qty,
                    rr.entry,
                    rr.stop,
                    rr.target,
                    rr.sizing.risk_budget,
                    sig_at,
                    prim.setup.anchor,
                    prim.setup.swept_level,
                )
            )

        if decision_sink is not None:
            for sym_name, res in analysed.items():
                bar_end = by_sym[sym_name].bars_5m[index[sym_name][start]].end
                for rec in build_decision_records(
                    res,
                    sym_name,
                    params.values,
                    bar_end,
                    params.content_hash,
                    risks.get(sym_name),
                    index[sym_name][start],
                ):
                    decision_sink(rec)

    for o in pending:
        skips.append(Skip(o.symbol, o.setup_type, o.signal_at, "SKIPPED_NO_BAR"))
    # session end: positions still open exit at the last close of their data
    for name, pos in list(open_pos.items()):
        bar = by_sym[name].bars_5m[last_idx[name]]
        at_exit = bar.end >= exit_time
        price = model.exit_price("session_end", bar.close) if at_exit else bar.close  # data cut: none
        closed.append(
            close_trade(
                pos,
                price,
                bar.end,
                "SESSION_END" if at_exit else "END_OF_DATA",
                schedule,
                not at_exit,
                model,
            )
        )
    net = sum((t.net_pnl for t in closed), Decimal(0))
    return SessionResult(spec, tuple(closed), tuple(skips), net)
