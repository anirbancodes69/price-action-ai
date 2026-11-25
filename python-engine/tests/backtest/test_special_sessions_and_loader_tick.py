"""E7 (OD-8 step 1): special-session eligibility (N-1) and the loader's tick source (N-2).

N-1: the research harness list keeps the three full-length weekend sessions and removes the partial and Muhurat
sessions. A weekend is not a reason to exclude a session.
N-2: `tick_and_lot` falls back silently to 0.05 when no snapshot covers the date. That is a recorded defect whose
fix belongs to E4/E5 (not authorised in step 1); the test below documents it as a strict expected failure, so it
turns into a failing test the day the loader is fixed and this marker must then be removed.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from app.backtest.exclusions import SPECIAL_SESSIONS
from app.backtest.loader import tick_and_lot

FULL_LENGTH_WEEKEND = [
    date(2024, 1, 20),
    date(2025, 2, 1),
    date(2026, 2, 1),
]  # Sat, Sat (Budget), Sun (Budget)
PARTIAL_OR_MUHURAT = [
    date(2024, 3, 2),
    date(2024, 5, 18),
    date(2024, 11, 1),
    date(2025, 10, 21),
    date(2026, 11, 8),
]


def test_the_three_full_length_weekend_sessions_are_not_special_sessions() -> None:
    assert [d.weekday() >= 5 for d in FULL_LENGTH_WEEKEND] == [True, True, True]
    assert not set(FULL_LENGTH_WEEKEND) & set(SPECIAL_SESSIONS)


def test_the_partial_and_muhurat_sessions_are_removed() -> None:
    assert set(SPECIAL_SESSIONS) == set(PARTIAL_OR_MUHURAT)


def test_removal_is_by_date_not_by_weekday() -> None:
    """A Sunday Muhurat session and Saturday partial sessions are listed; a Sunday Budget session is not."""
    weekend_listed = {d for d in SPECIAL_SESSIONS if d.weekday() >= 5}
    assert weekend_listed == {date(2024, 3, 2), date(2024, 5, 18), date(2026, 11, 8)}
    assert date(2026, 2, 1).weekday() == 6 and date(2026, 2, 1) not in SPECIAL_SESSIONS


class _NoRow:
    def execute(self, *_: Any, **__: Any) -> Any:
        class _R:
            def first(self) -> None:
                return None

        return _R()


@pytest.mark.xfail(
    strict=True,
    reason="N-2: tick_and_lot returns the placeholder 0.05 when no snapshot covers the date; fix is E4/E5",
)
def test_n2_the_loader_must_not_fall_back_silently_to_an_arbitrary_historical_tick() -> None:
    with pytest.raises(Exception):  # noqa: B017 - any explicit refusal is acceptable; today there is none
        tick_and_lot(_NoRow(), uuid.uuid4(), date(2024, 7, 1))  # type: ignore[arg-type]


def test_n2_today_the_fallback_is_exactly_the_placeholder_documented() -> None:
    """Pins the current behaviour (so the defect is measurable): no snapshot -> (0.05, 1)."""
    assert tick_and_lot(_NoRow(), uuid.uuid4(), date(2024, 7, 1)) == (Decimal("0.05"), 1)  # type: ignore[arg-type]
