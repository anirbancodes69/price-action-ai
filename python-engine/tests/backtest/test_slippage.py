"""D-4: execution-specific slippage assumptions, the legacy model, sensitivity and the report basis."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal as D

import pytest

from app.backtest.report import MEASURED_NET, format_report, performance_basis, report_dict, sensitivity_table
from app.backtest.run import BacktestConfig, SessionInput, run_backtest
from app.backtest.slippage import SlippageModel, from_options, kind_for_reason
from app.backtest.trade import ExitConfig, Position, close_trade, step_position

from .test_costs_trade import T0, S, _bar, _pos
from .test_replay import BASE, CLOSE, OPEN, SCHEDULE, day, make_analyse, sym

U = SlippageModel.uniform(D("0.10"))
LEGACY = SlippageModel.legacy(D("0.05"))


def test_the_models_are_named_and_always_assumed() -> None:
    assert (U.id, U.basis) == ("adverse-all", "ASSUMED")
    assert (LEGACY.id, LEGACY.entry, LEGACY.stop, LEGACY.target) == (
        "legacy-stop-only",
        D("0.05"),
        D("0.05"),
        0,
    )
    assert "not measured" in U.describe()


def test_each_execution_type_has_its_own_percentage() -> None:
    m = SlippageModel.parse("stop=0.2,target=0.1", D("0.05"))
    assert [m.pct(k) for k in ("entry", "stop", "target", "session_end", "structure")] == [
        D("0.05"), D("0.2"), D("0.1"), D("0.05"), D("0.05"),
    ]  # fmt: skip
    for bad in ("nope=1", "stop"):
        with pytest.raises(ValueError, match="bad slippage item"):
            SlippageModel.parse(bad, D("0.05"))
    assert SlippageModel.from_dict(m.to_dict()) == m
    assert from_options("legacy", None, D("0.05")) == LEGACY
    assert from_options("adverse-all", "target=0", D("0.05")).target == 0


def test_every_exit_type_fills_adversely_under_adverse_all() -> None:
    cfg = ExitConfig(D("0.05"), T0 + timedelta(hours=5), slippage=U)
    p = _pos()  # stop 98, target 105
    assert step_position(p, _bar("100", "100.5", "97.5", "99"), cfg) == (D("98") * D("0.999"), "STOP")
    assert step_position(p, _bar("100", "106", "99", "105"), cfg) == (D("105") * D("0.999"), "TARGET")
    assert step_position(p, _bar("106", "107", "105", "106"), cfg) == (D("106") * D("0.999"), "TARGET_GAP")
    assert step_position(p, _bar("97", "99", "96", "98"), cfg) == (D("97") * D("0.999"), "STOP_GAP")
    assert step_position(_pos(structure_exit_pending=True), _bar("100", "101", "99", "100"), cfg) == (
        D("100") * D("0.999"), "STRUCTURE_EXIT",
    )  # fmt: skip
    ses = ExitConfig(D("0.05"), T0, slippage=U)
    assert step_position(p, _bar("100", "101", "99", "100"), ses) == (D("100") * D("0.999"), "SESSION_END")


def test_without_a_model_the_legacy_behaviour_is_unchanged() -> None:
    cfg = ExitConfig(D("0.05"), T0 + timedelta(hours=5))
    assert cfg.model == LEGACY
    p = _pos()
    assert step_position(p, _bar("100", "106", "99", "105"), cfg) == (D("105"), "TARGET")  # no slippage
    assert step_position(p, _bar("100", "100.5", "97.5", "99"), cfg) == (D("98") * D("0.9995"), "STOP")


def test_slippage_cost_is_recovered_from_the_filled_prices() -> None:
    pos = Position("X", "T", 0, "", 100, D("100.10"), D("98"), D("105"), T0, T0)
    model = SlippageModel.uniform(D("0.10"))
    exit_p = model.exit_price("target", D("105"))
    t = close_trade(pos, exit_p, T0, "TARGET", S, slippage=model)
    entry_ref = D("100.10") / D("1.001")
    assert abs(t.slippage_cost - ((D("100.10") - entry_ref) + (D("105") - exit_p)) * 100) < D("1e-9")
    assert abs(t.gross_pnl + t.slippage_cost - (D("105") - entry_ref) * 100) < D("1e-9")
    assert close_trade(pos, D("101"), T0, "END_OF_DATA", S, True, model).slippage_cost < D("10.1") + 1
    assert kind_for_reason("END_OF_DATA") is None and kind_for_reason("STOP_COLLISION") == "stop"


def _run(model: SlippageModel | None):  # type: ignore[no-untyped-def]
    rows = day({3: ("100", "100.5", "99.9", "100.2"), 4: ("100.2", "103.5", "100", "103")})
    spec = __import__("app.backtest.replay", fromlist=["SessionSpec"]).SessionSpec(OPEN.date(), OPEN, CLOSE)
    cfg = BacktestConfig(BASE, D("100000"), SCHEDULE, "t", "DEMO", "U", slippage=model)
    return run_backtest([SessionInput(spec, [sym("AAA", rows)])], cfg, make_analyse({("AAA", 2): 70}))


def test_a_run_records_the_model_and_the_legacy_default_reproduces_old_results() -> None:
    legacy_default, explicit = _run(None), _run(LEGACY)
    assert legacy_default.trades == explicit.trades
    assert legacy_default.record.slippage["id"] == "legacy-stop-only"
    t = legacy_default.trades[0]
    assert (t.entry, t.exit, t.reason) == (D("100.05"), D("103"), "TARGET")  # the documented hand computation


def test_adverse_all_lowers_a_target_exit_and_the_sensitivity_is_monotonic() -> None:
    nets = []
    for pct in ("0", "0.05", "0.10", "0.20"):
        r = _run(SlippageModel.uniform(D(pct), f"uniform-{pct}"))
        nets.append(r.trades[0].net_pnl)
        assert r.trades[0].exit == D("103") * (1 - D(pct) / 100)
    assert nets == sorted(nets, reverse=True) and len(set(nets)) == 4
    table = sensitivity_table([_run(U), _run(LEGACY)])
    assert "not measurements" in table and "adverse-all" in table and "legacy-stop-only" in table


def test_report_separates_gross_estimated_net_and_unavailable_measured_net() -> None:
    r = _run(U)
    b = performance_basis(r)
    t = r.trades[0]
    assert D(b["gross_before_slippage_r"]) == (t.gross_pnl + t.slippage_cost) / t.risk_amount
    assert D(b["gross_before_slippage_r"]) > D(b["gross_after_slippage_r"]) > D(b["estimated_net_r"])
    assert b["measured_net"] == MEASURED_NET and "ASSUMED" in b["slippage_basis"]
    text = format_report(r)
    assert "ASSUMED, not measured" in text and "measured net NOT AVAILABLE" in text
    assert "gross before slippage" in text and "estimated net" in text
    d = report_dict(r)
    assert (
        d["performance_basis"]["measured_net"] == MEASURED_NET
        and d["record"]["slippage"]["id"] == "adverse-all"
    )
