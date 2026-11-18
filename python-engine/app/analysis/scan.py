"""Scan a universe at one moment and size the plans (decision support; manual execution, ADR-010)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from app.analysis.account import AccountInput
from app.backtest.replay import AnalyseFn, SessionSpec, SymbolData, default_analyse
from app.domain.params import RulesetParams
from app.domain.risk.account import RiskProfile
from app.domain.risk.request import RiskRequest, calculate_risk
from app.domain.session import entry_cutoff
from app.domain.setups.signal import Signal
from app.domain.setups.types import SetupDirection
from app.domain.snapshot import SnapshotStatus

STALE_AFTER_BARS = 2  # data older than this many bar lengths is flagged (HYPOTHESIS)


@dataclass(frozen=True, slots=True)
class ScanRow:
    symbol: str
    signal: str  # ENTRY_CONFIRMED, BUY_WATCH, NO_TRADE, or a snapshot status when analysis could not run
    setup_type: str | None
    setup_status: str | None
    paqs: int | None
    entry: Decimal | None
    stop: Decimal | None
    target: Decimal | None
    target_source: str | None
    rr: Decimal | None
    qty: int | None
    risk_amount: Decimal | None
    position_value: Decimal | None
    binding_constraint: str | None
    reasons: tuple[str, ...]
    signal_at: datetime | None
    valid_until: datetime | None
    last_bar_end: datetime
    stale: bool
    htf_state: str | None


_RANK = {"ENTRY_CONFIRMED": 0, "BUY_WATCH": 1}


def is_stale(last_bar_end: datetime, now: datetime, step: timedelta = timedelta(minutes=5)) -> bool:
    """The latest closed bar should end within `STALE_AFTER_BARS` bar lengths of `now`."""
    return now - last_bar_end > step * STALE_AFTER_BARS


def scan_symbol(
    sym: SymbolData,
    spec: SessionSpec,
    params: RulesetParams,
    account: AccountInput,
    now: datetime,
    analyse_fn: AnalyseFn = default_analyse,
) -> ScanRow:
    last_end = sym.bars_5m[-1].end
    stale = is_stale(last_end, now)
    res = analyse_fn(sym, len(sym.bars_5m), spec, params)
    if res.check.status is not SnapshotStatus.VALID or res.signal is None:
        reasons = res.check.problems or (res.check.status.value,)
        return ScanRow(
            sym.symbol,
            res.check.status.value,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            tuple(reasons),
            None,
            None,
            last_end,
            stale,
            None,
        )
    sig = res.signal
    prim = sig.primary
    lv = prim.levels if prim else None
    htf = res.htf.state.state.value if res.htf and res.htf.state else None
    qty = risk_amount = value = None
    binding: str | None = None
    why: list[str] = list(sig.reasons)
    if sig.signal is not Signal.NO_TRADE and prim and lv and prim.setup.direction is SetupDirection.LONG:
        cutoff = entry_cutoff(spec.session_close, params.int_("session.entry_cutoff_minutes_before_close"))
        profile = RiskProfile.from_params(params, account.capital)
        rr = calculate_risk(
            RiskRequest(
                SetupDirection.LONG,
                lv.entry,
                lv.stop,
                lv.target if lv.target is not None else lv.entry,
                sym.tick,
                sym.lot_size,
                profile,
                account.state(),
                True,
                sig.signal_at,
                cutoff,
            ),
            params,
        )
        if rr.ok and rr.sizing:
            qty, risk_amount, value = rr.sizing.qty, rr.sizing.actual_risk, rr.sizing.position_value
            binding = rr.sizing.binding_constraint
        else:
            why.extend(rr.errors)
    return ScanRow(
        sym.symbol,
        sig.signal.value,
        prim.setup.type.value if prim else None,
        prim.setup.status.value if prim else None,
        prim.paqs.total if prim and prim.paqs else None,
        lv.entry if lv else None,
        lv.stop if lv else None,
        lv.target if lv else None,
        lv.target_source if lv else None,
        lv.rr if lv else None,
        qty,
        risk_amount,
        value,
        binding,
        tuple(why),
        sig.signal_at,
        sig.valid_until,
        last_end,
        stale,
        htf,
    )


def scan_universe(
    items: Sequence[tuple[SymbolData, SessionSpec]],
    params: RulesetParams,
    account: AccountInput,
    now: datetime,
    analyse_fn: AnalyseFn = default_analyse,
) -> list[ScanRow]:
    """Rows ordered: confirmed entries, watches, then the rest; by PAQS descending, then symbol."""
    rows = [scan_symbol(s, spec, params, account, now, analyse_fn) for s, spec in items]
    return sorted(rows, key=lambda r: (_RANK.get(r.signal, 2), -(r.paqs or 0), r.symbol))
