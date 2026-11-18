"""Account state and account-level limits (TRD-05 §8)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.domain.params import RulesetParams


@dataclass(frozen=True, slots=True)
class ClosedTrade:
    net_pnl: Decimal  # after costs; list is in closing order


@dataclass(frozen=True, slots=True)
class OpenPosition:
    entry_fill: Decimal
    current_stop: Decimal
    qty: int


@dataclass(frozen=True, slots=True)
class RiskProfile:
    capital: Decimal
    risk_pct: Decimal  # percent, 0.5 = 0.5 %
    max_position_value: Decimal
    daily_loss_limit_pct: Decimal
    max_consecutive_losses: int
    max_open_positions: int
    max_open_risk_pct: Decimal

    @property
    def daily_loss_limit(self) -> Decimal:
        return self.capital * self.daily_loss_limit_pct / 100

    @classmethod
    def from_params(cls, params: RulesetParams, capital: Decimal) -> RiskProfile:
        """The ruleset defaults (TRD-01 §6); users may override within the registry ranges."""
        return cls(
            capital=capital,
            risk_pct=params.decimal("risk.default_risk_per_trade_pct"),
            max_position_value=params.decimal("risk.default_max_position_value"),
            daily_loss_limit_pct=params.decimal("risk.default_daily_loss_limit_pct"),
            max_consecutive_losses=params.int_("risk.default_max_consecutive_losses"),
            max_open_positions=params.int_("risk.default_max_open_positions"),
            max_open_risk_pct=params.decimal("risk.default_max_open_risk_pct"),
        )


@dataclass(frozen=True, slots=True)
class AccountState:
    """Derived on demand for one book and one session (TRD-05 §8.1); never stored."""

    realised_net_pnl_today: Decimal
    realised_net_loss_today: Decimal
    open_risk: Decimal
    day_loss_used: Decimal
    losing_streak: int
    open_positions: int  # open positions plus plans awaiting a fill
    cost_basis_open: Decimal


def derive_account_state(
    closed_today: Sequence[ClosedTrade],
    open_positions: Sequence[OpenPosition],
    pending_fills: int = 0,
) -> AccountState:
    pnl = sum((t.net_pnl for t in closed_today), Decimal(0))
    loss = max(Decimal(0), -pnl)
    open_risk = sum(
        (max(Decimal(0), p.entry_fill - p.current_stop) * p.qty for p in open_positions), Decimal(0)
    )
    streak = 0
    for t in reversed(closed_today):
        if t.net_pnl < 0:
            streak += 1
        else:
            break
    basis = sum((p.entry_fill * p.qty for p in open_positions), Decimal(0))
    return AccountState(
        pnl, loss, open_risk, loss + open_risk, streak, len(open_positions) + pending_fills, basis
    )


def check_account_limits(
    state: AccountState,
    profile: RiskProfile,
    session_open: bool,
    bar_end: datetime,
    cutoff: datetime,
) -> str | None:
    """First failing limit in TRD-05 §8 order, else `None`."""
    if not session_open:
        return "SESSION_CLOSED"
    if bar_end > cutoff:
        return "ENTRY_CUTOFF_PASSED"
    if state.realised_net_loss_today >= profile.daily_loss_limit:
        return "DAILY_LOSS_LIMIT_REACHED"
    if state.losing_streak >= profile.max_consecutive_losses:
        return "MAX_CONSECUTIVE_LOSSES_REACHED"
    if state.open_positions >= profile.max_open_positions:
        return "MAX_POSITIONS_REACHED"
    return None
