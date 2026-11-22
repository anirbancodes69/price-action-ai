"""TRD-06 §5 cost illustration and §4.2 exit mapping. Expected values are hand-computed."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.backtest.costs import CostSchedule, intraday_costs
from app.backtest.trade import ExitConfig, Position, close_trade, step_position
from app.domain.types import Bar

D = Decimal
S = CostSchedule()
T0 = datetime(2026, 11, 18, 4, 0, tzinfo=UTC)


def test_cost_illustration_from_spec() -> None:
    """33 shares, buy 1498.10, sell 1529.00: ₹53.08 in total (TRD-06 §5)."""
    c = intraday_costs(D("1498.10") * 33, D("1529.00") * 33, S)
    assert (c.brokerage, c.stt, c.exchange, c.sebi, c.stamp, c.gst) == (
        D("29.97"),  # 14.83 + 15.14
        D("12.61"),
        D("2.97"),
        D("0.10"),
        D("1.48"),
        D("5.95"),
    )
    assert c.total == D("53.08")


def test_brokerage_is_capped_per_order() -> None:
    c = intraday_costs(D("1000000"), D("1000000"), S)  # 0.03 % = 300 -> capped at 20 per side
    assert c.brokerage == D("40.00")


def _pos(**kw) -> Position:  # type: ignore[no-untyped-def]
    args = {
        "symbol": "A",
        "setup_type": "X",
        "paqs": 70,
        "context_15m": "BULLISH",
        "qty": 100,
        "entry_fill": D("100"),
        "stop": D("98"),
        "target": D("105"),
        "signal_at": T0,
        "fill_at": T0,
    }
    args.update(kw)
    return Position(**args)


def _bar(o: str, h: str, lo: str, c: str, start: datetime = T0) -> Bar:
    return Bar(start, start + timedelta(minutes=5), D(o), D(h), D(lo), D(c))


CFG = ExitConfig(D("0.05"), T0 + timedelta(hours=5))


def test_exit_reasons_and_slippage() -> None:
    p = _pos()
    assert step_position(p, _bar("100", "101", "99", "100"), CFG) is None
    assert step_position(p, _bar("100", "101", "97.5", "99"), CFG) == (D("98") * D("0.9995"), "STOP")
    assert step_position(p, _bar("100", "105.5", "97.5", "99"), CFG) == (
        D("98") * D("0.9995"),
        "STOP_COLLISION",
    )
    assert step_position(p, _bar("97", "98", "96", "97"), CFG) == (D("97") * D("0.9995"), "STOP_GAP")
    assert step_position(p, _bar("100", "106", "99", "105"), CFG) == (
        D("105"),
        "TARGET",
    )  # no positive slippage
    assert step_position(p, _bar("106", "107", "105", "106"), CFG) == (D("106"), "TARGET_GAP")


def test_session_end_and_structure_exit_at_open() -> None:
    bar = _bar("100", "101", "99", "100")
    cfg = ExitConfig(D("0.05"), T0)
    assert step_position(_pos(), bar, cfg) == (D("100"), "SESSION_END")
    assert step_position(_pos(structure_exit_pending=True), bar, CFG) == (D("100"), "STRUCTURE_EXIT")
    off = ExitConfig(D("0.05"), T0, session_exit_enabled=False, structure_exit_enabled=False)
    assert step_position(_pos(structure_exit_pending=True), bar, off) is None


def test_close_trade_pnl_and_r() -> None:
    t = close_trade(_pos(), D("105"), T0, "TARGET", S)
    assert (t.gross_pnl, t.risk_amount, t.r_gross) == (D("500"), D("200"), D("2.5"))
    # buy 10000, sell 10500: brokerage 3.00 + 3.15, STT 2.63, exchange 0.30 + 0.31, SEBI 0.01 + 0.01,
    # stamp 0.30, GST 18 % of (6.15 + 0.61 + 0.02) = 1.22
    assert t.costs == D("6.15") + D("2.63") + D("0.61") + D("0.02") + D("0.30") + D("1.22")
    assert t.net_pnl == D("500") - t.costs and t.r_net == t.net_pnl / D("200")
    loss = close_trade(_pos(), D("98"), T0, "STOP", S)
    assert loss.gross_pnl == D("-200") and loss.net_pnl < loss.gross_pnl  # costs add to the loss


def test_groww_published_schedule_differs_only_in_brokerage_and_exchange_rates() -> None:
    from dataclasses import fields

    from app.backtest.costs import GROWW_PUBLISHED

    changed = {f.name for f in fields(S) if getattr(S, f.name) != getattr(GROWW_PUBLISHED, f.name)}
    assert changed == {"version", "brokerage_pct", "exchange_pct"}
    # 50,000 each way: 0.03% is 15 rupees a side, 0.1% reaches the 20 rupee cap
    ours = intraday_costs(D(50000), D(50000), S)
    groww = intraday_costs(D(50000), D(50000), GROWW_PUBLISHED)
    assert (ours.brokerage, groww.brokerage) == (D("30.00"), D("40.00"))
    # at 100,000 both are at the cap
    assert intraday_costs(D(100000), D(100000), S).brokerage == D("40.00")
    assert intraday_costs(D(100000), D(100000), GROWW_PUBLISHED).brokerage == D("40.00")
