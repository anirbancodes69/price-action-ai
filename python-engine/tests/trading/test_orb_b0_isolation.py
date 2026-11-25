"""P0-3 for B0: a B0-specific isolation proof (hand-built and seeded random bars; no database, no real data).

The existing isolation proof covers the opening-range detector of today's code (CUR). It is not claimed to cover
B0: B0 is a different detector (`detect_orb_b0`) that no combined run contains. These tests show what B0 needs:
its outputs do not change when other detectors or strategies are enabled, no other detector can be the source
of a B0 setup or trade, B0 reads no previous-day level or 15m context, its signal stream equals an independent
statement of the frozen rules, and the strategy name cannot silently select another detector.
"""

from __future__ import annotations

import random
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from app.backtest.costs import CostSchedule
from app.backtest.replay import SymbolData
from app.backtest.run import SessionInput
from app.backtest.slippage import SlippageModel
from app.backtest.strategy_run import run_strategy_backtest
from app.domain import analyse as analyse_mod
from app.domain.analyse import ALL_DETECTORS, analyse
from app.domain.session import DailyLevels
from app.domain.setups.breakout_retest import detect_breakout_retest
from app.domain.setups.failed_breakdown import detect_failed_breakdown
from app.domain.setups.liquidity_sweep import detect_liquidity_sweep
from app.domain.setups.opening_range import detect_opening_range
from app.domain.setups.orb_b0 import OrbB0Setup, detect_orb_b0
from app.domain.setups.prev_day import detect_prev_day
from app.domain.setups.types import SetupDirection, SetupStatus, SetupType
from app.domain.strategies import STRATEGY_DETECTORS, strategy_detectors
from app.domain.types import Bar
from app.rulesets import load_ruleset

from ..backtest.b0_support import INDEPENDENT_RD, ctx
from ..backtest.test_strategy_run import _spec
from ._session import CLOSE, OPEN, ctx_for, mk

D = Decimal
BASE = load_ruleset("pa-intraday", "0.6.0")
P = replace(BASE, values={**BASE.values, "analysis.min_bars_5m": 5, "analysis.min_bars_15m": 5})
KW = {"previous_session_open": None, "session_close": CLOSE}
OR3 = [("1002", "1005", "1000", "1003"), ("1003", "1004", "1001", "1002"), ("1002", "1003", "1000.5", "1001")]
QUIET, BREAK = ("1003", "1004", "1001", "1003"), ("1003", "1007", "1002", "1006")
SCENARIOS = {
    "breakout": [*OR3, QUIET, BREAK, ("1005", "1020", "1004", "1019")],
    "whipsaw": [*OR3, ("1001", "1002", "998", "999"), QUIET, BREAK],
    "no_breakout": [*OR3, *[QUIET] * 8],
    "expired": [*OR3, *[QUIET] * 13, BREAK],
    "narrow": [("1000", "1002", "1000", "1000.5")] * 3 + [QUIET] * 4,
}
OTHERS = (
    detect_opening_range,
    detect_prev_day,
    detect_breakout_retest,
    detect_liquidity_sweep,
    detect_failed_breakdown,
)
PREV = DailyLevels(D("1100"), D("990"), D("1000"))


def _b0_setups(res):  # type: ignore[no-untyped-def]
    return [(s.setup, s.levels) for s in (res.setups or ()) if isinstance(s.setup, OrbB0Setup)]


def _run(rows, detectors, params=P, prev=PREV, b15=None):  # type: ignore[no-untyped-def]
    b5 = mk(rows)
    return analyse(b5, b15 or b5, OPEN, prev, params, detectors=detectors, isolated=True, **KW)


# --- the registry and the substitution guard ---------------------------------------------------------------------------


def test_the_b0_strategy_maps_to_the_b0_detector_alone_and_not_to_the_existing_one() -> None:
    assert tuple(strategy_detectors("orb_b0")) == (detect_orb_b0,)
    assert tuple(strategy_detectors("opening_range_breakout")) == (detect_opening_range,)
    assert detect_orb_b0 not in ALL_DETECTORS and detect_orb_b0 is not detect_opening_range
    assert "orb_b0" in STRATEGY_DETECTORS


def test_the_existing_isolation_script_does_not_claim_b0() -> None:
    text = (Path(__file__).resolve().parents[2] / "scripts/check_strategy_isolation.py").read_text()
    assert '"orb_b0"' not in text  # its proof compares today's detector; B0 has this test file instead


def test_a_ruleset_without_the_b0_keys_cannot_run_b0_so_the_name_cannot_fall_back() -> None:
    with pytest.raises(KeyError):
        old = load_ruleset("pa-intraday", "0.5.0")
        small = replace(old, values={**old.values, "analysis.min_bars_5m": 5, "analysis.min_bars_15m": 5})
        _run(SCENARIOS["breakout"], strategy_detectors("orb_b0"), small)


# --- invariance and source ------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_b0_output_does_not_change_when_other_detectors_or_strategy_flags_are_enabled(name: str) -> None:
    rows = SCENARIOS[name]
    flags = {
        **P.values,
        "setup.liquidity_sweep_enabled": True,
        "setup.failed_breakout_enabled": True,
        "setup.failed_break_max_bars": 6,
    }
    other_params = replace(P, values=flags)
    for k in range(5, len(rows) + 1):
        b5 = mk(rows[:k])
        alone = analyse(b5, b5, OPEN, PREV, P, detectors=(detect_orb_b0,), isolated=True, **KW)
        mixed = analyse(
            b5, b5, OPEN, PREV, other_params, detectors=(detect_orb_b0, *OTHERS), isolated=True, **KW
        )
        assert _b0_setups(alone) == _b0_setups(mixed), (name, k)
        assert alone.signal is not None and mixed.signal is not None


def test_no_other_detector_can_be_the_source_of_a_b0_setup() -> None:
    rows = SCENARIOS["breakout"]
    b5 = mk(rows)
    combined = analyse(b5, b5, OPEN, PREV, P, **KW)  # the default detectors: no B0
    assert combined.setups is not None and _b0_setups(combined) == []
    cur, _ = detect_opening_range(ctx_for(b5, params=P))
    assert cur and all(type(s).__name__ == "Setup" for s in cur)  # CUR emits plain Setups, never OrbB0Setup
    own = _run(rows, (detect_orb_b0,))
    assert own.setups and all(isinstance(s.setup, OrbB0Setup) for s in own.setups)
    assert all(s.setup.direction is SetupDirection.LONG for s in own.setups)


@pytest.mark.usefixtures("small_b0_hash")
def test_a_b0_run_is_unaffected_when_every_other_detector_would_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(_ctx: object) -> object:
        raise AssertionError("another detector was called by the B0 run")

    rows = [*OR3, QUIET, BREAK, ("1005", "1020", "1004", "1019")]
    bars = mk(rows)
    inputs = [SessionInput(_spec(), [SymbolData("A", bars, bars, None, D("0.05"))])]

    def go():  # type: ignore[no-untyped-def]
        return run_strategy_backtest(
            "orb_b0",
            "4a",
            inputs,
            P,
            D("100000"),
            CostSchedule(),
            "e",
            "d",
            "u",
            slippage=SlippageModel.uniform(D("0.05"), "u"),
            reference_data=INDEPENDENT_RD,
            b0_context=ctx(P),
        )

    before = go()
    monkeypatch.setattr(analyse_mod, "ALL_DETECTORS", (boom,) * 5)
    after = go()
    assert before.trades == after.trades and len(after.trades) == 1
    assert {t.setup_type for t in after.trades} == {SetupType.OPENING_RANGE_BREAKOUT.value}


def test_b0_reads_no_previous_day_level_and_no_15m_context() -> None:
    rows = SCENARIOS["breakout"]
    base = _b0_setups(_run(rows, (detect_orb_b0,)))
    assert base
    for prev in (None, DailyLevels(D("1"), D("0.5"), D("0.7")), DailyLevels(D("5000"), D("4000"), D("4500"))):
        assert _b0_setups(_run(rows, (detect_orb_b0,), prev=prev)) == base
    b5 = mk(rows)
    ctx_params = replace(P, values={**P.values, "analysis.min_bars_15m": 1})

    def to15(bars: list[Bar], shift: int) -> list[Bar]:
        out = []
        for k in range(0, len(bars) - 2, 3):
            g = bars[k : k + 3]
            out.append(Bar(g[0].start, g[-1].end, g[0].open + shift, max(x.high for x in g) + shift,
                           min(x.low for x in g) + shift, g[-1].close + shift))  # fmt: skip
        return out

    flat = [replace(b, open=D("1000"), high=D("1000"), low=D("1000"), close=D("1000")) for b in b5]
    for ctx15 in (to15(b5, -40), to15(b5, 70), to15(flat, 0)):
        got = analyse(b5, ctx15, OPEN, PREV, ctx_params, detectors=(detect_orb_b0,), isolated=True, **KW)
        assert got.check.status.value == "VALID" and _b0_setups(got) == base


# --- the signal stream follows the frozen rules (independent oracle) -------------------------------------------------


def _g(x: float) -> str:
    return f"{round(x / 0.05) * 0.05:.2f}"


def _random_rows(rng: random.Random) -> list[tuple[str, str, str, str]]:
    base = rng.uniform(900, 1100)
    width = rng.choice([0.0015, 0.0025, 0.004, 0.01, 0.019, 0.022, 0.03])
    rows = []
    n = rng.randint(4, 40)
    price = base
    for i in range(n):
        step = base * rng.uniform(-0.002, 0.003)
        o, c = price, price + step
        spread = base * (width / 3 if i < 3 else rng.uniform(0.0003, 0.002))
        hi, lo = max(o, c) + rng.uniform(0, spread), min(o, c) - rng.uniform(0, spread)
        rows.append((_g(o), _g(hi), _g(lo), _g(c)))
        price = float(_g(c))
    return [(o, str(max(D(h), D(o), D(c))), str(min(D(lo), D(o), D(c))), c) for o, h, lo, c in rows]


def _oracle(rows):  # type: ignore[no-untyped-def]
    """An independent, line-by-line statement of the frozen B0 signal rules (ORB spec §10.3)."""
    bars: list[Bar] = mk(rows)
    if bars[-1].end < OPEN + timedelta(minutes=15):
        return ("SILENT", None)
    hi, lo = max(b.high for b in bars[:3]), min(b.low for b in bars[:3])
    width = (hi - lo) / lo * 100
    if width < D("0.3"):
        return ("REASON", "OR_TOO_NARROW")
    if width > D("2.0"):
        return ("REASON", "OR_TOO_WIDE")
    window_end = OPEN + timedelta(minutes=15 + 60)
    cutoff = CLOSE - timedelta(minutes=45)
    for j in range(3, len(bars)):
        b = bars[j]
        if b.end > cutoff:
            return ("EXPIRED", j)
        if b.end > window_end:
            return ("EXPIRED", j)
        if b.close < lo * (1 - D("0.0005")):
            return ("INVALIDATED", j)
        if b.close > hi * (1 + D("0.0005")):
            return ("CONFIRMED", j)
    return ("AWAITING", None)


def test_the_b0_signal_stream_equals_an_independent_statement_of_the_frozen_rules() -> None:
    rng = random.Random(20261125)  # noqa: S311 (seeded test data)
    seen: set[str] = set()
    for _ in range(600):
        rows = _random_rows(rng)
        expect = _oracle(rows)
        setups, reasons = detect_orb_b0(ctx_for(mk(rows), params=BASE))
        if expect[0] == "SILENT":
            assert (setups, reasons) == ([], [])
        elif expect[0] == "REASON":
            assert (setups, reasons) == ([], [expect[1]])
        else:
            assert reasons == [] and len(setups) == 1
            s = setups[0]
            assert isinstance(s, OrbB0Setup) and s.direction is SetupDirection.LONG
            want = {"EXPIRED": SetupStatus.EXPIRED, "INVALIDATED": SetupStatus.INVALIDATED,
                    "CONFIRMED": SetupStatus.ENTRY_CONFIRMED, "AWAITING": SetupStatus.AWAITING_CONFIRMATION}[expect[0]]  # fmt: skip
            assert s.status is want, (rows, expect)
            if expect[0] == "CONFIRMED":
                assert s.confirmed_at_index == expect[1] and s.confirm_close == mk(rows)[expect[1]].close
            if expect[0] in ("EXPIRED", "INVALIDATED"):
                assert s.ended_at_index == expect[1]
        seen.add(expect[0] + (":" + str(expect[1]) if expect[0] == "REASON" else ""))
    assert {
        "CONFIRMED",
        "INVALIDATED",
        "AWAITING",
        "EXPIRED",
        "REASON:OR_TOO_NARROW",
        "REASON:OR_TOO_WIDE",
    } <= seen
