"""Simulated positions, exits and trades (TRD-06 §4.2)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.backtest.costs import CostSchedule, intraday_costs
from app.backtest.slippage import SlippageModel
from app.domain.risk.exits import evaluate_bar_exit
from app.domain.types import Bar


@dataclass(frozen=True, slots=True)
class Position:
    symbol: str
    setup_type: str
    paqs: int
    context_15m: str  # 15m structure state at the signal, for breakdowns
    qty: int
    entry_fill: Decimal
    stop: Decimal
    target: Decimal
    signal_at: datetime
    fill_at: datetime
    structure_exit_pending: bool = False
    anchor: str = ""  # setup anchor (research breakdowns)
    swept_level: Decimal | None = None

    @property
    def risk_amount(self) -> Decimal:
        return self.qty * (self.entry_fill - self.stop)


@dataclass(frozen=True, slots=True)
class ExitConfig:
    slippage_pct: Decimal
    session_exit_time: datetime
    session_exit_enabled: bool = True
    structure_exit_enabled: bool = True
    # Per-execution-type slippage (D-4). `None` keeps the legacy behaviour: `slippage_pct` on the entry and
    # on stop exits only, so existing callers and earlier results are unchanged.
    slippage: SlippageModel | None = None

    @property
    def model(self) -> SlippageModel:
        return self.slippage or SlippageModel.legacy(self.slippage_pct)


@dataclass(frozen=True, slots=True)
class Trade:
    symbol: str
    setup_type: str
    paqs: int
    context_15m: str
    qty: int
    entry: Decimal
    exit: Decimal
    reason: str
    signal_at: datetime
    fill_at: datetime
    exit_at: datetime
    gross_pnl: Decimal
    costs: Decimal
    net_pnl: Decimal
    risk_amount: Decimal
    r_gross: Decimal
    r_net: Decimal
    end_of_data: bool = False
    anchor: str = ""
    swept_level: Decimal | None = None
    slippage_cost: Decimal = Decimal(
        0
    )  # rupees lost to assumed slippage (gross before slippage = gross + this)


def step_position(pos: Position, bar: Bar, cfg: ExitConfig) -> tuple[Decimal, str] | None:
    """Exit `(price, reason)` on `bar`, or `None`. Reasons follow TRD-06 §4.2.

    `evaluate_bar_exit` gives the reference price; the slippage model then moves it adversely by the
    percentage of the execution type (stop, target, session end, structure). Stop and target in one bar:
    `STOP_COLLISION` (BT-04).
    """
    r = evaluate_bar_exit(
        bar,
        pos.stop,
        pos.target,
        Decimal(0),
        cfg.session_exit_time,
        cfg.session_exit_enabled,
        pos.structure_exit_pending,
        cfg.structure_exit_enabled,
    )
    if r is None:
        return None
    m = cfg.model
    if r.reason == "STOP":
        reason = "STOP_GAP" if r.gap else ("STOP_COLLISION" if bar.high >= pos.target else "STOP")
        return m.exit_price("stop", r.price), reason
    if r.reason == "TARGET":
        return m.exit_price("target", r.price), "TARGET_GAP" if r.gap else "TARGET"
    kind = "session_end" if r.reason == "SESSION_END" else "structure"
    return m.exit_price(kind, r.price), r.reason


def close_trade(
    pos: Position,
    exit_price: Decimal,
    exit_at: datetime,
    reason: str,
    schedule: CostSchedule,
    end_of_data: bool = False,
    slippage: SlippageModel | None = None,
) -> Trade:
    gross = (exit_price - pos.entry_fill) * pos.qty
    costs = intraday_costs(pos.entry_fill * pos.qty, exit_price * pos.qty, schedule).total
    net = gross - costs
    risk = pos.risk_amount
    return Trade(
        pos.symbol,
        pos.setup_type,
        pos.paqs,
        pos.context_15m,
        pos.qty,
        pos.entry_fill,
        exit_price,
        reason,
        pos.signal_at,
        pos.fill_at,
        exit_at,
        gross,
        costs,
        net,
        risk,
        gross / risk,
        net / risk,
        end_of_data,
        pos.anchor,
        pos.swept_level,
        slippage.cost(pos.entry_fill, exit_price, pos.qty, reason) if slippage else Decimal(0),
    )
