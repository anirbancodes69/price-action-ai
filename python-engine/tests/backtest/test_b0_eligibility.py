"""D2 to D6: B0 instrument-session eligibility, ORB/control symmetry, loader hook (synthetic data; no database)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta
from decimal import Decimal

import pytest

from app.backtest import loader
from app.backtest.b0_eligibility import (
    B0Reference,
    EligibilityMap,
    PriceBasis,
    TickStatus,
    classify_tick,
    instrument_session_eligibility,
    ratio_step,
)
from app.backtest.exclusions import Exclusion
from app.backtest.reference_tables import (
    REVIEWED,
    CorporateEvent,
    EventStatus,
    EventTable,
    EventType,
    LoadedTable,
    session_table_from,
)
from app.domain.ticks import TickResolution, TickRow, TickTable
from app.domain.types import Bar
from app.ingestion.session import IST

D = Decimal
DAY = date(2025, 3, 5)
TRADED, ADJ = PriceBasis.TRADED_SCALE_VERIFIED, PriceBasis.PROVIDER_ADJUSTED
SESSION_ROWS = [
    {"effective_from": "2024-01-01", "effective_to": "2026-07-31", "session_open": "09:15",
     "continuous_end": "15:30", "last_expected_bar_start": "15:25", "expected_bar_count": 75,
     "source": "T", "confidence": "HIGH"},
    {"date": "2024-01-20", "session_open": "09:15", "continuous_end": "15:30",
     "last_expected_bar_start": "15:25", "expected_bar_count": 75, "source": "C", "confidence": "LOW",
     "excluded_reason": "SPECIAL_SESSION_2024_01_20"},
]  # fmt: skip


def _bars(day: date, prices: list[tuple[str, str, str, str]] | None = None, n: int = 3) -> list[Bar]:
    rows = prices or [("100.00", "100.50", "99.50", "100.20")] * n
    s = datetime.combine(day, time(9, 15), IST)
    return [
        Bar(s + timedelta(minutes=5 * i), s + timedelta(minutes=5 * i + 5), D(o), D(h), D(lo), D(c))
        for i, (o, h, lo, c) in enumerate(rows)
    ]


def _ref(
    events: list[CorporateEvent] | None = None, basis: PriceBasis = TRADED, ticks: list[TickRow] | None = None
):  # type: ignore[no-untyped-def]
    rows = ticks if ticks is not None else [TickRow("AAA", date(2024, 1, 1), None, D("0.05"), "T")]
    return B0Reference(
        TickTable(rows),
        EventTable(events or []),
        session_table_from(LoadedTable("session_table", "t1", "x", REVIEWED, SESSION_ROWS)),
        {("AAA", DAY): basis, ("AAA", date(2024, 1, 20)): basis},
        {"tick_table_sha256": "a" * 64},
    )


def _open(day: date = DAY) -> datetime:
    return datetime.combine(day, time(9, 15), IST)


def _elig(ref: B0Reference, bars: list[Bar] | None = None, day: date = DAY, sym: str = "AAA", **kw):  # type: ignore[no-untyped-def]
    return instrument_session_eligibility(
        ref, sym, day, bars if bars is not None else _bars(day), _open(day), **kw
    )


def test_a_clean_traded_scale_session_is_eligible_with_the_resolved_tick() -> None:
    e = _elig(_ref())
    assert (e.eligible, e.reason, e.tick, e.tick_status) == (
        True,
        None,
        D("0.05"),
        TickStatus.TICK_VERIFIED_PASS,
    )


def test_provider_adjusted_sessions_are_eligible_without_tick_rounding_and_say_so() -> None:
    """D3 option A: no traded-scale rounding, `TICK_ROUNDING_NOT_APPLIED`, neither pass nor fail."""
    bars = _bars(DAY, [("100.01", "100.53", "99.57", "100.23")] * 3)  # not multiples of 0.05
    e = _elig(_ref(basis=ADJ), bars)
    assert (e.eligible, e.tick, e.tick_status) == (True, None, TickStatus.TICK_UNVERIFIABLE)
    assert "TICK_ROUNDING_NOT_APPLIED" in e.notes and e.price_basis is ADJ


def test_an_unclassified_price_basis_is_treated_as_unverifiable_not_as_traded() -> None:
    ref = _ref()
    e = instrument_session_eligibility(
        ref, "AAA", date(2025, 3, 6), _bars(date(2025, 3, 6)), _open(date(2025, 3, 6))
    )
    assert e.eligible and e.tick is None and e.tick_status is TickStatus.TICK_UNVERIFIABLE


def test_only_a_verified_misalignment_invalidates_with_tick_misaligned() -> None:
    bars = _bars(DAY, [("100.01", "100.50", "99.50", "100.20")] * 3)
    e = _elig(_ref(), bars)
    assert (e.eligible, e.reason, e.tick_status) == (False, "TICK_MISALIGNED", TickStatus.TICK_VERIFIED_FAIL)
    res = TickResolution.resolved_as(D("0.05"), "T")
    assert (
        classify_tick(bars, res, ADJ) is TickStatus.TICK_UNVERIFIABLE
    )  # same prices, adjusted scale: not a fail
    assert classify_tick(bars, TickResolution.unknown("x"), TRADED) is TickStatus.TICK_UNKNOWN


def test_an_unknown_tick_excludes_the_instrument_session_and_never_becomes_0_05() -> None:
    e = _elig(_ref(ticks=[TickRow("AAA", date(2025, 4, 1), None, D("0.05"), "T")]))
    assert (e.eligible, e.reason, e.tick, e.tick_status) == (
        False,
        "TICK_UNKNOWN",
        None,
        TickStatus.TICK_UNKNOWN,
    )
    assert _elig(_ref(), sym="ZZZ").reason == "TICK_UNKNOWN"


def test_unknown_session_hours_fail_closed_and_are_never_defaulted_to_1530() -> None:
    ref = _ref()
    e = instrument_session_eligibility(
        ref, "AAA", date(2023, 6, 1), _bars(date(2023, 6, 1)), _open(date(2023, 6, 1))
    )
    assert (e.eligible, e.reason) == (False, "SESSION_HOURS_UNKNOWN")
    assert instrument_session_eligibility(ref, "AAA", DAY, _bars(DAY), None).reason == "SESSION_HOURS_UNKNOWN"


def test_2024_01_20_is_excluded_from_the_primary_population_with_its_reason() -> None:
    d = date(2024, 1, 20)
    assert _elig(_ref(), _bars(d), d).reason == "SPECIAL_SESSION_2024_01_20"


def test_range_defects_are_reported_with_the_frozen_mg02_reasons() -> None:
    assert _elig(_ref(), _bars(DAY, n=2)).reason == "OR_NOT_CLOSED"
    gap = _bars(DAY)
    assert _elig(_ref(), gap[:1] + gap[2:]).reason == "OR_MISSING_BAR"
    bad = _bars(DAY, [("100", "99", "98", "100")] * 3)  # high below open
    assert _elig(_ref(), bad).reason == "OR_INVALID_OHLC"


def _ev(kind: EventType, status: EventStatus, sym: str = "AAA") -> CorporateEvent:
    return CorporateEvent(kind, sym, DAY, "src", "h", "HIGH", status)


def test_l6_confirmed_symbol_changes_and_demergers_exclude_only_that_instrument_session() -> None:
    ref = _ref([_ev(EventType.DEMERGER, EventStatus.CONFIRMED)])
    assert _elig(ref).reason == "L6_EVENT"
    other = date(2025, 3, 6)
    ref2 = _ref([_ev(EventType.SYMBOL_CHANGE, EventStatus.CONFIRMED)])
    assert instrument_session_eligibility(
        ref2, "AAA", other, _bars(other), _open(other)
    ).eligible  # not the company


def test_l6_unresolved_events_fail_closed_and_other_actions_are_only_flagged() -> None:
    assert _elig(_ref([_ev(EventType.DEMERGER, EventStatus.UNRESOLVED)])).reason == "L6_EVENT_UNRESOLVED"
    e = _elig(_ref([_ev(EventType.SPLIT, EventStatus.CONFIRMED)]))
    assert e.eligible and "L6_EVENT_FLAGGED" in e.notes


def test_the_provider_ratio_step_safety_net_excludes_unexplained_material_steps_only() -> None:
    thr = D("0.005")
    assert ratio_step(D("1.0"), D("1.006")) > thr and ratio_step(D("1.0"), D("1.004")) < thr
    assert _elig(_ref(), provider_ratio_step=D("0.0051")).reason == "PROVIDER_RATIO_STEP"
    assert _elig(_ref(), provider_ratio_step=D("0.005")).eligible  # not above the threshold
    explained = _ref([_ev(EventType.SPLIT, EventStatus.CONFIRMED)])
    e = _elig(explained, provider_ratio_step=D("0.02"))
    assert e.eligible and "PROVIDER_RATIO_STEP_EXPLAINED" in e.notes


def test_reason_precedence_is_the_documented_order_and_all_reasons_are_kept() -> None:
    ref = _ref([_ev(EventType.DEMERGER, EventStatus.CONFIRMED)], ticks=[])
    e = _elig(ref, _bars(DAY, n=2), provider_ratio_step=D("0.9"))
    assert e.reason == "L6_EVENT"
    # The event row explains the ratio step, so no PROVIDER_RATIO_STEP reason; the others keep the table order.
    assert e.reasons == ("L6_EVENT", "TICK_UNKNOWN", "OR_NOT_CLOSED")


def test_the_l3_missing_late_bar_flag_is_recorded_not_excluded() -> None:
    rows = [{**SESSION_ROWS[0], "missing_late_bar_flag": True}]
    ref = B0Reference(
        TickTable([TickRow("AAA", date(2024, 1, 1), None, D("0.05"), "T")]),
        EventTable([]),
        session_table_from(LoadedTable("session_table", "t1", "x", REVIEWED, rows)),
        {("AAA", DAY): TRADED},
        {},
    )
    e = _elig(ref)
    assert e.eligible and "L3_MISSING_LATE_BAR" in e.notes


def test_orb_and_controls_read_the_same_eligibility_objects_so_the_populations_cannot_differ() -> None:
    ref = _ref([_ev(EventType.DEMERGER, EventStatus.CONFIRMED, "BBB")])
    items = {}
    for sym in ("AAA", "BBB", "CCC"):
        items[(sym, DAY)] = _elig(ref, sym=sym)
    m = EligibilityMap(items)
    orb_arm = m.eligible_keys()
    control_arm = [k for k in sorted(items) if m.get(*k).eligible]  # a control draws from the same map
    assert orb_arm == control_arm == [("AAA", DAY)]
    assert m.get("AAA", DAY) is m.get("AAA", DAY)  # one object, computed once
    assert m.reason_counts() == {"L6_EVENT": 1, "TICK_UNKNOWN": 1}
    assert [_elig(ref, sym=s) for s in ("AAA", "BBB", "CCC")] == [
        items[(s, DAY)] for s in ("AAA", "BBB", "CCC")
    ]


# --- loader hook ---------------------------------------------------------------------------------------------------

DAYS = [date(2025, 3, 3), date(2025, 3, 4), date(2025, 3, 5)]


@pytest.fixture
def fake_store(monkeypatch: pytest.MonkeyPatch) -> None:
    def load_bars(_c, _s, _i, tf, _f, _l):  # type: ignore[no-untyped-def]
        return [b for d in DAYS for b in _bars(d, n=4)] if tf == "5m" else []

    def boom(*_a: object, **_k: object) -> None:
        raise AssertionError("the B0 path must not read instrument_snapshots or session defaults")

    monkeypatch.setattr(loader, "load_bars", load_bars)
    monkeypatch.setattr(loader, "tick_and_lot", boom)
    monkeypatch.setattr(loader, "session_spec", boom)


def _ref_all(basis: PriceBasis = TRADED, ticks: list[TickRow] | None = None) -> B0Reference:
    r = _ref(basis=basis, ticks=ticks)
    return B0Reference(r.ticks, r.events, r.sessions, {("AAA", d): basis for d in DAYS}, r.hashes)


def test_the_b0_loader_uses_the_dated_tables_and_shares_one_eligibility_decision(fake_store: None) -> None:
    ex: list[Exclusion] = []
    out: dict = {}
    s = loader.load_backtest_inputs(
        None,
        uuid.uuid4(),
        {"AAA": uuid.uuid4()},
        DAYS[0],
        DAYS[-1],
        2,
        exclusions=ex,
        b0=_ref_all(),
        eligibility_out=out,  # type: ignore[arg-type]
    )
    assert [x.spec.session_date for x in s] == DAYS and ex == []
    assert all(x.symbols[0].tick == D("0.05") and x.spec.session_close.time() == time(15, 30) for x in s)
    assert set(out) == {("AAA", d) for d in DAYS} and all(v.eligible for v in out.values())


def test_the_b0_loader_leaves_out_unknown_tick_instrument_sessions_and_records_them(fake_store: None) -> None:
    ex: list[Exclusion] = []
    ref = _ref_all(ticks=[TickRow("AAA", DAYS[1], None, D("0.05"), "T")])
    s = loader.load_backtest_inputs(
        None,
        uuid.uuid4(),
        {"AAA": uuid.uuid4()},
        DAYS[0],
        DAYS[-1],
        2,
        exclusions=ex,
        b0=ref,  # type: ignore[arg-type]
    )
    assert [x.spec.session_date for x in s] == [DAYS[0], DAYS[1], DAYS[2]]
    assert [len(x.symbols) for x in s] == [0, 1, 1]
    assert ex == [Exclusion(DAYS[0], "AAA", "TICK_UNKNOWN")]


def test_the_b0_loader_passes_none_for_provider_adjusted_sessions_so_nothing_is_rounded(
    fake_store: None,
) -> None:
    s = loader.load_backtest_inputs(
        None,
        uuid.uuid4(),
        {"AAA": uuid.uuid4()},
        DAYS[0],
        DAYS[-1],
        2,
        b0=_ref_all(ADJ),  # type: ignore[arg-type]
    )
    assert all(x.symbols[0].tick is None for x in s)


def test_the_b0_loader_excludes_a_session_with_unknown_hours(
    fake_store: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    ex: list[Exclusion] = []
    ref = _ref_all()
    ref2 = B0Reference(
        ref.ticks, ref.events,
        session_table_from(LoadedTable("session_table", "t1", "x", REVIEWED, [{**SESSION_ROWS[0], "effective_from": "2025-03-04"}])),
        ref.price_basis, ref.hashes,
    )  # fmt: skip
    s = loader.load_backtest_inputs(
        None,
        uuid.uuid4(),
        {"AAA": uuid.uuid4()},
        DAYS[0],
        DAYS[-1],
        2,
        exclusions=ex,
        b0=ref2,  # type: ignore[arg-type]
    )
    assert [x.spec.session_date for x in s] == DAYS[1:]
    assert ex == [Exclusion(DAYS[0], None, "SESSION_HOURS_UNKNOWN")]
