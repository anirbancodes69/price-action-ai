"""Instrument-session eligibility for the B0 research path (OD-8 Step 2, decisions D2 to D6).

One pure function decides, once per instrument-session, whether the session may be used and with which tick.
The ORB run and every matched control read the **same** `Eligibility` object (`EligibilityMap`), so the two
arms cannot see different populations. No default is ever applied: an unknown tick, unknown session hours, an
unresolved corporate event or an unverified price basis is reported, not repaired.

Reason precedence (first match wins; every reason is also kept in `reasons`):
`SESSION_HOURS_UNKNOWN`, the session-facts exclusion (for example `SPECIAL_SESSION_2024_01_20`),
`FROZEN_TIMING_NOT_APPLICABLE` (not the regular 09:15-15:30 session, so the frozen cutoff and exit times
cannot be applied faithfully; reported separately, never moved), `L6_EVENT_UNRESOLVED`, `L6_EVENT`,
`PROVIDER_RATIO_STEP`, `TICK_UNKNOWN`, the `ORB-MG-02` range reasons (`OR_*`), `TICK_MISALIGNED`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import StrEnum

from app.backtest.approval import RunApproval
from app.backtest.b0_contract import B0ExecutionContext
from app.backtest.reference_tables import SESSION_HOURS_UNKNOWN, EventTable, SessionFactsTable
from app.domain.setups.orb_range import validate_opening_range
from app.domain.ticks import TickResolution, TickTable
from app.domain.types import Bar

RATIO_STEP_THRESHOLD = Decimal("0.005")  # D5: 0.5 % step in the provider adjustment ratio
TICK_ROUNDING_NOT_APPLIED = "TICK_ROUNDING_NOT_APPLIED"
TICK_UNKNOWN = "TICK_UNKNOWN"
TICK_MISALIGNED = "TICK_MISALIGNED"
PROVIDER_RATIO_STEP = "PROVIDER_RATIO_STEP"
L3_MISSING_LATE_BAR = "L3_MISSING_LATE_BAR"
FROZEN_TIMING_NOT_APPLICABLE = "FROZEN_TIMING_NOT_APPLICABLE"
# The frozen B0 clock times (range 09:15-09:30; entry cutoff and session-end exit counted back from the
# regular close) are defined for the regular 09:15-15:30 session. They are never moved for a short session.
FROZEN_SESSION_OPEN, FROZEN_REGULAR_CLOSE = time(9, 15), time(15, 30)


class PriceBasis(StrEnum):
    TRADED_SCALE_VERIFIED = "TRADED_SCALE_VERIFIED"
    PROVIDER_ADJUSTED = "PROVIDER_ADJUSTED"
    UNVERIFIABLE = "UNVERIFIABLE"


class TickStatus(StrEnum):
    """MG02-A1 (policy approved; the frozen specification text is not amended until review)."""

    TICK_VERIFIED_PASS = "TICK_VERIFIED_PASS"  # noqa: S105
    TICK_VERIFIED_FAIL = "TICK_VERIFIED_FAIL"
    TICK_UNKNOWN = "TICK_UNKNOWN"
    TICK_UNVERIFIABLE = "TICK_UNVERIFIABLE"


def frozen_timing_applies(session_open: time, continuous_end: time) -> bool:
    return session_open == FROZEN_SESSION_OPEN and continuous_end == FROZEN_REGULAR_CLOSE


def classify_tick(window: Sequence[Bar], resolution: TickResolution, basis: PriceBasis) -> TickStatus:
    """Only `TICK_VERIFIED_FAIL` invalidates a range. Never defaults a tick."""
    if not resolution.resolved:
        return TickStatus.TICK_UNKNOWN
    if basis is not PriceBasis.TRADED_SCALE_VERIFIED:
        return TickStatus.TICK_UNVERIFIABLE
    assert resolution.value is not None
    tick = resolution.value
    aligned = all(p % tick == 0 for b in window for p in (b.open, b.high, b.low, b.close))
    return TickStatus.TICK_VERIFIED_PASS if aligned else TickStatus.TICK_VERIFIED_FAIL


def ratio_step(previous_ratio: Decimal, ratio: Decimal) -> Decimal:
    """Relative change of the provider adjustment ratio (daily close / last 5m close) between sessions."""
    return abs(ratio / previous_ratio - 1)


@dataclass(frozen=True, slots=True)
class Eligibility:
    eligible: bool
    reason: str | None  # the primary exclusion reason
    reasons: tuple[str, ...]
    tick_status: TickStatus | None
    tick: Decimal | None  # the tick to round levels to; None = no rounding (provider-adjusted or ineligible)
    price_basis: PriceBasis | None
    notes: tuple[str, ...]  # non-excluding facts: TICK_ROUNDING_NOT_APPLIED, L3_MISSING_LATE_BAR, event flags


@dataclass(frozen=True, slots=True)
class B0Reference:
    """The reviewed, hash-pinned reference data of a B0 run. `hashes` goes into the run record."""

    ticks: TickTable
    events: EventTable
    sessions: SessionFactsTable
    price_basis: Mapping[tuple[str, date], PriceBasis]
    hashes: Mapping[str, str]
    approval: RunApproval | None = (
        None  # approval basis of the tables (DEC-045 / DR-12); None = not established
    )
    context: B0ExecutionContext | None = None  # issued by the strict runner (`b0_contract.issue_context`)


def _ineligible(
    reasons: list[str], tick_status: TickStatus | None, basis: PriceBasis | None, notes: list[str]
) -> Eligibility:
    return Eligibility(False, reasons[0], tuple(reasons), tick_status, None, basis, tuple(notes))


def instrument_session_eligibility(
    ref: B0Reference,
    symbol: str,
    day: date,
    session_bars_5m: Sequence[Bar],
    session_open: datetime | None,
    *,
    provider_ratio_step: Decimal | None = None,
) -> Eligibility:
    """Decide one instrument-session. `session_open` comes from the session-facts table (None = unknown)."""
    notes: list[str] = []
    facts = ref.sessions.facts(day)
    basis = ref.price_basis.get((symbol, day), PriceBasis.UNVERIFIABLE)
    if facts is None or session_open is None:
        return _ineligible([SESSION_HOURS_UNKNOWN], None, basis, notes)
    reasons: list[str] = []
    if facts.excluded_reason:
        reasons.append(facts.excluded_reason)
    if not frozen_timing_applies(facts.session_open, facts.continuous_end):
        reasons.append(FROZEN_TIMING_NOT_APPLICABLE)
    if facts.missing_late_bar_flag:
        notes.append(L3_MISSING_LATE_BAR)
    event_reason = ref.events.exclusion_reason(symbol, day)
    if event_reason:
        reasons.append(event_reason)
    elif ref.events.has_event(symbol, day):
        notes.append("L6_EVENT_FLAGGED")
    if provider_ratio_step is not None and provider_ratio_step > RATIO_STEP_THRESHOLD:
        if not ref.events.has_event(symbol, day):
            reasons.append(PROVIDER_RATIO_STEP)  # unexplained material step: excluded until a row is reviewed
        else:
            notes.append("PROVIDER_RATIO_STEP_EXPLAINED")
    resolution = ref.ticks.resolve(symbol, day)
    if not resolution.resolved:
        reasons.append(TICK_UNKNOWN)
    k_minutes = 15
    window = [
        b for b in session_bars_5m if session_open <= b.start < session_open + timedelta(minutes=k_minutes)
    ]
    status = classify_tick(window, resolution, basis) if resolution.resolved else TickStatus.TICK_UNKNOWN
    rng = validate_opening_range(session_bars_5m, session_open, k_minutes)
    if not rng.valid and rng.reason is not None:
        reasons.append(rng.reason.value)
    if status is TickStatus.TICK_VERIFIED_FAIL:
        reasons.append(TICK_MISALIGNED)
    if status is TickStatus.TICK_UNVERIFIABLE:
        notes.append(TICK_ROUNDING_NOT_APPLIED)
    if reasons:
        return _ineligible(reasons, status, basis, notes)
    tick = resolution.value if basis is PriceBasis.TRADED_SCALE_VERIFIED else None
    return Eligibility(True, None, (), status, tick, basis, tuple(notes))


class EligibilityMap:
    """Eligibility computed once per instrument-session and shared by the ORB run and the controls."""

    def __init__(self, items: Mapping[tuple[str, date], Eligibility]) -> None:
        self._items = dict(items)

    def get(self, symbol: str, day: date) -> Eligibility:
        return self._items[(symbol, day)]

    def __contains__(self, key: tuple[str, date]) -> bool:
        return key in self._items

    def eligible_keys(self) -> list[tuple[str, date]]:
        return sorted(k for k, v in self._items.items() if v.eligible)

    def reason_counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for v in self._items.values():
            if v.reason:
                out[v.reason] = out.get(v.reason, 0) + 1
        return out
