"""Metrics (TRD-06 §10), splits (§9) and the run record (BT-05). Expected values are hand-computed."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from app.backtest.costs import CostSchedule
from app.backtest.metrics import compute_metrics, equity_curve, max_drawdown
from app.backtest.replay import SessionResult, SessionSpec, Skip, SymbolData
from app.backtest.run import BacktestConfig, SessionInput, inputs_hash, run_backtest
from app.backtest.splits import (
    oos_allows_promotion,
    split_sessions,
    walk_forward,
    walk_forward_positive_in_most,
)
from app.backtest.trade import Trade
from app.domain.types import Bar

from .test_replay import BASE, FLAT, day, make_analyse

D = Decimal
OPEN = datetime(2026, 11, 18, 3, 45, tzinfo=UTC)
CLOSE = OPEN + timedelta(hours=6, minutes=15)


def spec(d: int) -> SessionSpec:
    o = OPEN + timedelta(days=d)
    return SessionSpec(o.date(), o, o + timedelta(hours=6, minutes=15))


def trade(net: str, r_net: str, gross: str, minutes: int, d: int = 0, start_min: int = 15, **kw) -> Trade:  # type: ignore[no-untyped-def]
    fill = OPEN + timedelta(days=d, minutes=start_min)
    args = {
        "symbol": "A",
        "setup_type": "OPENING_RANGE_BREAKOUT",
        "paqs": 70,
        "context_15m": "BULLISH",
        "qty": 10,
        "entry": D("100"),
        "exit": D("101"),
        "reason": "TARGET",
        "signal_at": fill,
        "fill_at": fill,
        "exit_at": fill + timedelta(minutes=minutes),
        "gross_pnl": D(gross),
        "costs": D("20"),
        "net_pnl": D(net),
        "risk_amount": D("500"),
        "r_gross": D(gross) / 500,
        "r_net": D(r_net),
    }
    args.update(kw)
    return Trade(**args)


def session(d: int, trades: list[Trade], skips: list[Skip] | None = None) -> SessionResult:
    net = sum((t.net_pnl for t in trades), D(0))
    return SessionResult(spec(d), tuple(trades), tuple(skips or ()), net)


def sample_sessions() -> list[SessionResult]:
    s1 = session(0, [trade("500", "1.0", "520", 30), trade("-250", "-0.5", "-230", 30, start_min=30)])
    s2 = session(1, [])
    s3 = session(
        2,
        [trade("-400", "-0.8", "-380", 15, d=2, reason="STOP")],
        [Skip("A", "X", OPEN, "ACCOUNT_LIMIT")],
    )
    return [s1, s2, s3]


def test_headline_metrics() -> None:
    m = compute_metrics(sample_sessions(), D("100000"))
    assert (m.trades, m.sessions) == (3, 3)
    assert m.win_rate == D(1) / 3
    assert m.avg_r_net == D("-0.1")  # (1.0 - 0.5 - 0.8) / 3
    assert m.profit_factor is not None and m.profit_factor.quantize(D("0.0001")) == D("0.7692")  # 500 / 650
    assert (m.mean_session_pnl, m.median_session_pnl, m.worst_session_pnl) == (D("-50"), D("0"), D("-400"))
    assert m.exit_mix == {"STOP": 1, "TARGET": 2} and m.skips == {"ACCOUNT_LIMIT": 1}
    assert m.cost_drag is not None and m.cost_drag.quantize(D("0.0001")) == D("0.0531")  # 60 / 1130
    assert m.sessions_account_blocked_pct is not None and m.sessions_account_blocked_pct.quantize(
        D("0.01")
    ) == D("33.33")
    assert m.low_sample is True


def test_drawdown_and_equity_curve() -> None:
    curve = equity_curve(sample_sessions(), D("100000"))
    assert curve == [D("100000"), D("100250"), D("100250"), D("99850")]
    dd, pct = max_drawdown(curve)
    assert dd == D("400") and pct.quantize(D("0.0001")) == D("0.3990")  # 400 / 100250
    assert max_drawdown([D("1"), D("2"), D("3")]) == (D("0"), D("0"))


def test_sharpe_exposure_and_time_in_trade() -> None:
    m = compute_metrics(sample_sessions(), D("100000"))
    assert m.sharpe_daily is not None and m.sharpe_daily.quantize(D("0.01")) == D("-2.42")
    # session 1: overlapping trades cover 09:30-10:15 IST... 45 minutes of 375; session 3: 15 minutes
    assert m.exposure_pct is not None and m.exposure_pct.quantize(D("0.0001")) == D("0.0533")
    assert m.avg_minutes_in_trade == D(25)  # (30 + 30 + 15) / 3


def test_breakdowns() -> None:
    m = compute_metrics(sample_sessions(), D("100000"))
    assert list(m.by_setup) == ["OPENING_RANGE_BREAKOUT"] and m.by_setup["OPENING_RANGE_BREAKOUT"].trades == 3
    assert set(m.by_half_hour) == {
        "09:30"
    }  # fills at 04:00 and 04:15 UTC = 09:30 and 09:45 IST... 09:30 bucket
    assert m.by_month["2026-11"].net_pnl == D("-150")
    assert m.by_context_15m["BULLISH"].avg_r_net == D("-0.1")


def test_end_of_data_trades_excluded_by_default() -> None:
    eod = trade("10", "0.1", "30", 5, end_of_data=True, reason="END_OF_DATA")
    s = [session(0, [trade("100", "1", "120", 5), eod])]
    m = compute_metrics(s, D("100000"))
    assert (m.trades, m.end_of_data_trades) == (1, 1)
    assert compute_metrics(s, D("100000"), include_end_of_data=True).trades == 2


def test_no_trades_gives_empty_metrics() -> None:
    m = compute_metrics([session(0, [])], D("100000"))
    assert (m.trades, m.win_rate, m.avg_r_net, m.profit_factor, m.sharpe_daily) == (0, None, None, None, None)


def dates(n: int) -> list[date]:
    return [date(2024, 1, 1) + timedelta(days=i) for i in range(n)]


def test_split_500_sessions() -> None:
    s = split_sessions(dates(500))
    assert (len(s.in_sample), len(s.out_of_sample), len(s.holdout)) == (300, 100, 100)
    assert s.in_sample[-1] < s.out_of_sample[0] and s.out_of_sample[-1] < s.holdout[0]


def test_walk_forward_windows() -> None:
    w = walk_forward(dates(500), 120, 40)
    assert len(w) == 9  # starts 0, 40, ..., 320
    assert (len(w[0].in_sample), len(w[0].out_of_sample)) == (120, 40)
    assert w[0].out_of_sample[0] == dates(500)[120] and w[1].in_sample[0] == dates(500)[40]
    assert walk_forward(dates(159), 120, 40) == []


def test_promotion_gates() -> None:
    assert (
        not oos_allows_promotion(None)
        and not oos_allows_promotion(D("0"))
        and oos_allows_promotion(D("0.01"))
    )
    assert walk_forward_positive_in_most([D("1"), D("1"), D("-1")])
    assert not walk_forward_positive_in_most([D("1"), D("-1")])  # exactly half is not "most"
    assert not walk_forward_positive_in_most([])


def shift(bs: list[Bar], days: int) -> list[Bar]:
    d = timedelta(days=days)
    return [replace(b, start=b.start + d, end=b.end + d) for b in bs]


def sym(name: str, rows: list[Bar]) -> SymbolData:
    return SymbolData(name, rows, [], None, D("0.05"))


def two_sessions() -> list[SessionInput]:
    rows = day({3: ("100", "100.5", "99.9", "100.2"), 4: ("100.2", "103.5", "100", "103")})
    return [SessionInput(spec(0), [sym("A", rows)]), SessionInput(spec(1), [sym("A", shift(rows, 1))])]


def cfg(**kw) -> BacktestConfig:  # type: ignore[no-untyped-def]
    args = {
        "params": BASE,
        "capital": D("100000"),
        "schedule": CostSchedule(),
        "engine_version": "test",
        "data_source": "DEMO",
        "universe": "TEST",
    }
    args.update(kw)
    return BacktestConfig(**args)


def test_run_backtest_fixed_vs_compounding() -> None:
    fn = make_analyse({("A", 2): 80})
    fixed = run_backtest(two_sessions(), cfg(), fn)
    assert [t.qty for t in fixed.trades] == [476, 476]
    comp = run_backtest(two_sessions(), cfg(sizing_mode="COMPOUNDING"), fn)
    assert [t.qty for t in comp.trades] == [476, 482]  # budget (100000 + 1352.79) x 0.5 % / 1.05 per share
    assert [d for d, _ in fixed.equity_curve] == [spec(0).session_date, spec(1).session_date]
    assert fixed.equity_curve[-1][1] == D("100000") + sum((t.net_pnl for t in fixed.trades), D(0))


def test_run_record_flags_and_determinism() -> None:
    fn = make_analyse({("A", 2): 80})
    a, b = run_backtest(two_sessions(), cfg(), fn), run_backtest(two_sessions(), cfg(), fn)
    assert a == b  # BT-05: reproducible
    r = a.record
    assert (r.ruleset, r.cost_schedule_version, r.sessions, r.sizing_mode) == (
        "pa-intraday 0.1.0",
        "nse-intraday-assumed-0",
        2,
        "FIXED",
    )
    assert set(a.flags) == {"short_history", "survivorship_bias_risk", "low_sample"}
    ok = run_backtest(two_sessions(), cfg(point_in_time_universe=True), fn)
    assert "survivorship_bias_risk" not in ok.flags
    changed = two_sessions()
    changed[0] = SessionInput(spec(0), [sym("A", day({3: FLAT, 5: ("100", "100", "100", "100")}))])
    assert inputs_hash(changed) != inputs_hash(two_sessions())


def test_default_analysis_path_runs_end_to_end() -> None:
    """BT-03 smoke test: the replay uses the live `analyse` (no scripted function) without error."""
    from app.backtest.replay import replay_session
    from app.domain.params import RulesetParams
    from app.domain.risk.account import RiskProfile

    p = RulesetParams(
        BASE.code, BASE.version, {**BASE.values, "analysis.min_bars_5m": 5, "analysis.min_bars_15m": 5}
    )
    rows = day({}, n=12)
    r = replay_session([sym("A", rows)], spec(0), p, RiskProfile.from_params(p, D("100000")), CostSchedule())
    assert r.spec == spec(0) and r.net_pnl == sum((t.net_pnl for t in r.trades), D(0))
