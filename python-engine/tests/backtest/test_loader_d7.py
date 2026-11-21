"""D-7 loader options: special-session removal and previous-day levels from 1D bars (no database)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from app.backtest import loader
from app.backtest.exclusions import MISSING_PREV_DAY_LEVELS, SPECIAL_SESSIONS, Exclusion, summarise
from app.backtest.replay import SessionSpec
from app.domain.session import DailyLevels
from app.domain.types import Bar
from app.ingestion.session import IST

D = Decimal
DAYS = [date(2024, 2, 28), date(2024, 2, 29), date(2024, 3, 1), date(2024, 3, 2), date(2024, 3, 4)]
A, B = uuid.uuid4(), uuid.uuid4()


def _day_bars(day: date, high: str) -> list[Bar]:
    s = datetime(day.year, day.month, day.day, 9, 15, tzinfo=IST)
    return [Bar(s, s + timedelta(minutes=5), D("100"), D(high), D("99"), D("100"))]


@pytest.fixture(autouse=True)
def fake_store(monkeypatch: pytest.MonkeyPatch) -> None:
    def load_bars(_conn, _src, _iid, tf, _first, _last):  # type: ignore[no-untyped-def]
        return [b for i, d in enumerate(DAYS) for b in _day_bars(d, str(101 + i))] if tf == "5m" else []

    monkeypatch.setattr(loader, "load_bars", load_bars)
    monkeypatch.setattr(
        loader,
        "session_spec",
        lambda _c, day, prev: SessionSpec(
            day,
            datetime(day.year, day.month, day.day, 9, 15, tzinfo=IST),
            datetime(day.year, day.month, day.day, 15, 30, tzinfo=IST),
        ),
    )
    monkeypatch.setattr(loader, "tick_and_lot", lambda *_: (D("0.05"), 1))


def _levels(missing: set[date]) -> dict[date, DailyLevels]:
    return {d: DailyLevels(D(200 + i), D(50 + i), D(180 + i)) for i, d in enumerate(DAYS) if d not in missing}


def test_the_five_special_sessions_are_listed_with_reasons() -> None:
    assert sorted(SPECIAL_SESSIONS) == [
        date(2024, 3, 2),
        date(2024, 5, 18),
        date(2024, 11, 1),
        date(2025, 10, 21),
        date(2026, 11, 8),
    ]


def test_defaults_keep_the_earlier_behaviour() -> None:
    got = loader.load_backtest_inputs(None, uuid.uuid4(), {"A": A}, DAYS[1], DAYS[4], 1)  # type: ignore[arg-type]
    assert [i.spec.session_date for i in got] == DAYS[1:]  # the Saturday session is replayed
    assert got[-1].symbols[0].prev_day == DailyLevels(
        D("104"), D("99"), D("100")
    )  # from the 5m bars of the Saturday


def test_special_sessions_are_removed_from_the_replay_the_window_and_the_previous_day() -> None:
    ex: list[Exclusion] = []
    daily = {"A": _levels(set())}
    got = loader.load_backtest_inputs(
        None, uuid.uuid4(), {"A": A}, DAYS[1], DAYS[4], 2,  # type: ignore[arg-type]
        daily_levels=daily, skip_days={date(2024, 3, 2)}, exclusions=ex,
    )  # fmt: skip
    assert [i.spec.session_date for i in got] == [DAYS[1], DAYS[2], DAYS[4]]
    monday = got[-1].symbols[0]
    assert all(
        b.start.date() != date(2024, 3, 2) for b in monday.bars_5m
    )  # no partial-session bars in the window
    assert monday.prev_day == DailyLevels(D(202), D(52), D(182))  # Friday's daily bar, not the Saturday
    assert ex == [Exclusion(date(2024, 3, 2), None, "SPECIAL_SESSION_PARTIAL_SATURDAY")]


def test_an_instrument_without_the_previous_daily_bar_is_left_out_and_recorded() -> None:
    ex: list[Exclusion] = []
    daily = {"A": _levels(set()), "B": _levels({DAYS[2]})}  # B has no Friday daily bar
    got = loader.load_backtest_inputs(
        None, uuid.uuid4(), {"A": A, "B": B}, DAYS[2], DAYS[4], 1,  # type: ignore[arg-type]
        daily_levels=daily, skip_days={DAYS[3]}, exclusions=ex,
    )  # fmt: skip
    by_day = {i.spec.session_date: [s.symbol for s in i.symbols] for i in got}
    assert by_day == {DAYS[2]: ["A", "B"], DAYS[4]: ["A"]}
    assert Exclusion(DAYS[4], "B", MISSING_PREV_DAY_LEVELS) in ex
    assert summarise(ex) == {"SPECIAL_SESSION_PARTIAL_SATURDAY": 1, MISSING_PREV_DAY_LEVELS: 1}


def test_a_daily_bar_that_does_not_contain_the_5m_range_is_left_out_and_recorded() -> None:
    from app.backtest.exclusions import INCONSISTENT_PREV_DAY_LEVELS

    ex: list[Exclusion] = []
    # The 5m bar of 2024-03-01 has high 103; B's daily high 102 cannot be that day's high (a price break).
    daily = {"A": _levels(set()), "B": {**_levels(set()), DAYS[2]: DailyLevels(D("102"), D("98"), D("100"))}}
    got = loader.load_backtest_inputs(
        None, uuid.uuid4(), {"A": A, "B": B}, DAYS[4], DAYS[4], 1,  # type: ignore[arg-type]
        daily_levels=daily, skip_days={DAYS[3]}, exclusions=ex,
    )  # fmt: skip
    assert [s.symbol for s in got[0].symbols] == ["A"]
    assert Exclusion(DAYS[4], "B", INCONSISTENT_PREV_DAY_LEVELS) in ex
