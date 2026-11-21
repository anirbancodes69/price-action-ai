"""Chunked runs: saving, merging and the equality with one run over the whole range."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from app.backtest.chunks import merge_chunks, save_chunk
from app.backtest.costs import CostSchedule
from app.backtest.replay import SessionSpec, SymbolData
from app.backtest.run import SessionInput
from app.backtest.strategy_run import run_strategy_backtest
from app.domain.params import RulesetParams
from app.domain.session import DailyLevels
from app.rulesets import load_ruleset

from ..trading._session import CLOSE, OPEN, mk
from ..trading.test_setups_sweep import SAME_BAR

D = Decimal
SID = "liquidity_sweep_reversal"


def _params() -> RulesetParams:
    p = load_ruleset("pa-intraday", "0.3.0")
    return RulesetParams(
        p.code, p.version, {**p.values, "analysis.min_bars_5m": 5, "analysis.min_bars_15m": 5}
    )


def _session(day: int) -> SessionInput:
    shift = timedelta(days=day)
    rows = mk(SAME_BAR + [("1485", "1487", "1484", "1486")] * 4)
    rows = [type(b)(b.start + shift, b.end + shift, b.open, b.high, b.low, b.close) for b in rows]
    sym = SymbolData("A", rows, rows, DailyLevels(D("1510"), D("1480"), D("1495")), D("0.05"))
    spec = SessionSpec(OPEN.date() + shift, OPEN + shift, CLOSE + shift)
    return SessionInput(spec, [sym])


def _run(days: list[int]):  # type: ignore[no-untyped-def]
    return run_strategy_backtest(SID, "4a", [_session(d) for d in days], _params(), D("100000"), CostSchedule(),
                                 "engine test", "TEST", "TEST")  # fmt: skip


META = {
    "ruleset": "pa-intraday@0.3.0", "strategy_id": SID, "experiment": "4a", "capital": "100000",
    "tie_break_seed": 1, "data_source": "TEST", "universe": "TEST",
}  # fmt: skip


def test_merged_chunks_equal_one_run_over_the_whole_range(tmp_path: Path) -> None:
    whole = _run([0, 1, 2, 3, 4, 5])
    paths = []
    for i, days in enumerate(([0, 1], [2, 3], [4, 5])):
        r = _run(days)
        save_chunk(tmp_path / f"{i}.pkl", r, META, [])
        paths.append(tmp_path / f"{i}.pkl")
    merged, exclusions, _ = merge_chunks(list(reversed(paths)))  # the order of the files does not matter
    assert exclusions == []
    assert merged.trades == whole.trades and len(whole.trades) == 6
    assert merged.metrics == whole.metrics
    assert merged.equity_curve == whole.equity_curve
    assert merged.record.sessions == 6 and merged.record.strategy_id == SID


def test_merge_rejects_overlapping_chunks_and_mixed_configurations(tmp_path: Path) -> None:
    a, b = _run([0, 1]), _run([1, 2])
    save_chunk(tmp_path / "a.pkl", a, META, [])
    save_chunk(tmp_path / "b.pkl", b, META, [])
    with pytest.raises(ValueError, match="overlap"):
        merge_chunks([tmp_path / "a.pkl", tmp_path / "b.pkl"])
    save_chunk(tmp_path / "c.pkl", _run([3]), {**META, "experiment": "4b"}, [])
    with pytest.raises(ValueError, match="different configurations"):
        merge_chunks([tmp_path / "a.pkl", tmp_path / "c.pkl"])


def test_the_trades_carry_their_anchor_and_swept_level() -> None:
    [t, *_] = _run([0]).trades
    assert (t.anchor, t.swept_level) == ("PDL", D("1480"))
    # The fixture ends before the session exit, so its trade is an end-of-data trade, outside the metrics.
    assert t.end_of_data
