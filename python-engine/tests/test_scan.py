"""Scan, account input and output formatting. Expected values are hand-computed."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from app.analysis.account import AccountInput, parse_account
from app.analysis.format import HEADER, format_scan, scan_dict
from app.analysis.scan import is_stale, scan_symbol, scan_universe
from app.backtest.replay import SessionSpec, SymbolData
from app.domain.risk.account import ClosedTrade, OpenPosition

from .backtest.test_replay import BASE, CLOSE, OPEN, day, make_analyse

D = Decimal
SPEC = SessionSpec(OPEN.date(), OPEN, CLOSE)


def sym(name: str, n: int = 3) -> SymbolData:
    return SymbolData(name, day({}, n=n), [], None, D("0.05"))


ACCOUNT = AccountInput(D("100000"))
FN = make_analyse({("A", 2): 80, ("D", 2): 60})
NOW = sym("A").bars_5m[-1].end


def test_confirmed_entry_is_sized_from_the_account() -> None:
    row = scan_symbol(sym("A"), SPEC, BASE, ACCOUNT, NOW, FN)
    assert (row.signal, row.setup_type, row.paqs) == ("ENTRY_CONFIRMED", "OPENING_RANGE_BREAKOUT", 80)
    assert (row.entry, row.stop, row.target, row.rr) == (D("100"), D("99"), D("103"), D("3"))
    # risk 0.5% of 1,00,000 = 500 at ₹1 per share; the ₹50,000 cap allows 500: tie resolves to RISK_BUDGET
    assert (row.qty, row.risk_amount, row.position_value, row.binding_constraint) == (
        500,
        D("500"),
        D("50000"),
        "RISK_BUDGET",
    )
    assert row.signal_at == NOW and row.valid_until == NOW  # the scripted analysis sets both to the bar end
    assert row.htf_state == "BULLISH" and not row.stale


def test_account_limits_block_the_plan_with_a_reason() -> None:
    lost = AccountInput(D("100000"), (ClosedTrade(D("-1500")),))
    row = scan_symbol(sym("A"), SPEC, BASE, lost, NOW, FN)
    assert row.signal == "ENTRY_CONFIRMED" and row.qty is None
    assert "DAILY_LOSS_LIMIT_REACHED" in row.reasons
    full = AccountInput(
        D("100000"), (), (OpenPosition(D("50"), D("49"), 1), OpenPosition(D("50"), D("49"), 1))
    )
    assert "MAX_POSITIONS_REACHED" in scan_symbol(sym("A"), SPEC, BASE, full, NOW, FN).reasons


def test_no_trade_and_short_history_rows() -> None:
    quiet = scan_symbol(sym("B"), SPEC, BASE, ACCOUNT, NOW, FN)
    assert (quiet.signal, quiet.qty, quiet.entry) == ("NO_TRADE", None, None) and quiet.reasons == (
        "NO_SETUP",
    )
    from app.backtest.replay import default_analyse

    short = scan_symbol(sym("B"), SPEC, BASE, ACCOUNT, NOW, default_analyse)  # real analysis, only 3 bars
    assert short.signal == "INSUFFICIENT_HISTORY" and any("5m bars 3" in r for r in short.reasons)


def test_staleness_boundary() -> None:
    end = NOW
    assert not is_stale(end, end + timedelta(minutes=10))  # exactly two bar lengths
    assert is_stale(end, end + timedelta(minutes=10, seconds=1))
    assert scan_symbol(sym("A"), SPEC, BASE, ACCOUNT, end + timedelta(minutes=30), FN).stale


def test_rows_are_ordered_actionable_first() -> None:
    items = [(sym(n), SPEC) for n in ("B", "D", "A", "C")]
    rows = scan_universe(items, BASE, ACCOUNT, NOW, FN)
    assert [(r.symbol, r.signal) for r in rows] == [
        ("A", "ENTRY_CONFIRMED"),
        ("D", "ENTRY_CONFIRMED"),
        ("B", "NO_TRADE"),
        ("C", "NO_TRADE"),
    ]  # PAQS 80 before 60, then alphabetical


def test_parse_account() -> None:
    a = parse_account(
        {
            "capital": 100000,
            "closed_today": [{"net_pnl": "-300"}, {"net_pnl": 100}],
            "open_positions": [{"entry_fill": "100", "stop": "98", "qty": 10}],
            "pending_fills": 1,
        }
    )
    st = a.state()
    assert a.capital == D("100000") and st.realised_net_pnl_today == D("-200") and st.open_risk == D("20")
    assert st.losing_streak == 0 and st.open_positions == 2
    assert parse_account({"capital": "50000"}).state().open_positions == 0


def test_text_output_labels_data_and_notice() -> None:
    rows = scan_universe([(sym("A"), SPEC), (sym("B"), SPEC)], BASE, ACCOUNT, NOW, FN)
    text = format_scan(rows, "DEMO (DEMO) - SAMPLE DATA, not live", NOW)
    assert HEADER in text and "SAMPLE DATA, not live" in text
    assert "ENTRY_CONFIRMED" in text and "OPENING_RANGE_BREAKOUT" in text and "500" in text
    assert "NO_TRADE 1" in text and "ENTRY_CONFIRMED 1" in text
    quiet = scan_universe([(sym("B"), SPEC)], BASE, ACCOUNT, NOW, FN)
    assert "No actionable setups" in format_scan(quiet, "x", NOW)
    assert "B " in format_scan(quiet, "x", NOW, show_all=True)
    stale = scan_universe([(sym("A"), SPEC)], BASE, ACCOUNT, NOW + timedelta(hours=1), FN)
    assert "STALE DATA" in format_scan(stale, "x", NOW)


def test_json_output_is_serialisable() -> None:
    import json

    d = scan_dict(scan_universe([(sym("A"), SPEC)], BASE, ACCOUNT, NOW, FN), "x", NOW)
    json.dumps(d)
    assert d["rows"][0]["entry"] == "100" and d["rows"][0]["qty"] == 500 and d["notice"] == HEADER
