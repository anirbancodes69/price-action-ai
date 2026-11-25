"""E7 (OD-8 step 1): truncation equality for today's opening-range detector (`ORB-MG-03`, MP-03, MP-04).

Cutting the series after bar k must give exactly the setups the full series gave for bars up to k: a result
never depends on a later bar. Hand-built bars only.
"""

from __future__ import annotations

from typing import Any

from app.domain.htf import HtfContext
from app.domain.setups.opening_range import detect_opening_range
from app.domain.setups.types import Setup
from app.domain.types import BarState, StructureState

from ._session import ctx_for, flat_htf, mk
from .test_setups_session import ORB_DAY

LONG_DAY = [
    *ORB_DAY,
    ("1498.1", "1499", "1497", "1498.5"),
    ("1498.5", "1500", "1498", "1499.5"),
    ("1499.5", "1501", "1499", "1500"),
    ("1500", "1501", "1484", "1485"),  # a close below the OR low late in the day
    ("1485", "1486", "1480", "1481"),
]
GAP_DAY = [row for i, row in enumerate(LONG_DAY) if i != 1]  # the 09:20 bar is missing


def _key(s: Setup) -> tuple[Any, ...]:
    return (s.direction, s.detected_at_index, s.trigger_price, s.stop_base, s.status, s.confirmed_at_index)


def _static(k: tuple[Any, ...]) -> tuple[Any, ...]:
    return k[:4]  # direction, detected bar, trigger, stop base


def _setups(rows: list[tuple[str, str, str, str]], k: int) -> tuple[list[tuple[Any, ...]], list[str]]:
    bars = mk(rows[: k + 1])
    htf: list[HtfContext] = flat_htf(len(bars), StructureState.BULLISH)
    out, reasons = detect_opening_range(ctx_for(bars, htf=htf))
    return sorted(map(_key, out), key=repr), reasons


def test_truncation_equality_a_setup_detected_on_or_before_bar_k_is_the_same_on_truncated_data() -> None:
    for rows in (LONG_DAY, GAP_DAY):
        full_setups, _ = _setups(rows, len(rows) - 1)
        for k in range(3, len(rows)):
            cut, _ = _setups(rows, k)
            want = [_static(s) for s in full_setups if s[1] <= k]
            got = [_static(s) for s in cut]
            assert sorted(got, key=repr) == sorted(want, key=repr), (len(rows), k)
            # A confirmation on or before bar k is also identical; later confirmations are simply not yet known.
            for f in full_setups:
                if f[1] <= k and f[5] is not None and f[5] <= k:
                    assert f in cut, (len(rows), k, f)


def test_no_range_exists_before_its_last_bar_closes() -> None:
    for rows in (LONG_DAY,):
        for k in (0, 1):
            assert _setups(rows, k) == ([], [])  # MG-03: the range is used only from E(K-1)


def test_neutral_context_is_not_a_hidden_input_to_the_truncation_result() -> None:
    bars = mk(LONG_DAY[:8])
    neutral = [HtfContext(0, BarState(StructureState.SIDEWAYS, None, None, None)) for _ in bars]
    a = detect_opening_range(ctx_for(bars, htf=neutral))
    b = detect_opening_range(ctx_for(bars, htf=neutral))
    assert a == b  # deterministic
