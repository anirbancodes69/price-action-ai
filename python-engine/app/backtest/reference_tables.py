"""Hash-pinned, review-gated reference tables for the B0 research path (OD-8 Step 2, D2/D5/D6).

Tick table, corporate-event table and session-facts table are curated historical data, not strategy
parameters (DR-7). Each file is JSON with `kind`, `version`, `review_status` and `rows`. Loading requires the
caller to pin the file's SHA-256 and, by default, accepts only `INDEPENDENTLY_REVIEWED` (an AI review is
never an
independent review). With the explicit opt-in `allow_solo=True` it also accepts `OWNER_APPROVED_SOLO_RESEARCH`
(DEC-045 / DR-12) when the metadata carries a decision reference and the owner's approval evidence; see
`app.backtest.approval`. That status is never converted into `INDEPENDENTLY_REVIEWED` and waives no check
below.
A hash mismatch, an unknown kind, missing or empty provenance or an inconsistent table fails the load; nothing
is repaired or defaulted.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from enum import StrEnum
from itertools import pairwise
from pathlib import Path
from typing import Any

from app.backtest.approval import INDEPENDENT, TableApproval, parse_approval
from app.domain.ticks import TickRow, TickTable

REVIEWED = INDEPENDENT  # unchanged value and meaning
UNREVIEWED = "UNREVIEWED"


class ReferenceTableError(ValueError):
    """A reference table is unreadable, mismatched with its pinned hash, or unreviewed."""


@dataclass(frozen=True, slots=True)
class LoadedTable:
    kind: str
    version: str
    sha256: str
    review_status: str
    rows: list[dict[str, Any]]
    approval: TableApproval | None = None  # parsed approval basis; None only when the load was not gated


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_table(
    path: Path,
    kind: str,
    expected_sha256: str,
    *,
    require_reviewed: bool = True,
    allow_solo: bool = False,
) -> LoadedTable:
    actual = file_sha256(path)
    if actual != expected_sha256:
        raise ReferenceTableError(f"{path.name}: sha256 {actual} does not match the pinned {expected_sha256}")
    doc = json.loads(path.read_text(encoding="utf-8"), parse_float=Decimal)
    if doc.get("kind") != kind:
        raise ReferenceTableError(f"{path.name}: kind {doc.get('kind')!r}, expected {kind!r}")
    status = doc.get("review_status")
    approval = _gate(doc, path.name, require_reviewed, allow_solo)
    rows = doc.get("rows")
    if not isinstance(rows, list):
        raise ReferenceTableError(f"{path.name}: rows missing")
    return LoadedTable(kind, str(doc.get("version")), actual, str(status), rows, approval)


def _gate(meta: dict[str, Any], name: str, require_reviewed: bool, allow_solo: bool) -> TableApproval | None:
    if not require_reviewed:
        return None  # tests only; the B0 runner never passes this
    try:
        return parse_approval(meta, name=name, allow_solo=allow_solo)
    except ValueError as e:
        raise ReferenceTableError(str(e)) from e


def _prov(row: dict[str, Any], key: str) -> str:
    """Row provenance (circular, source file, hash): required and non-empty, on every status."""
    v = row[key]
    if not isinstance(v, str) or not v.strip():
        raise ReferenceTableError(f"row provenance {key!r} is empty: {row}")
    return v


def _d(s: str | None) -> date | None:
    return date.fromisoformat(s) if s else None


def tick_table_from(t: LoadedTable) -> TickTable:
    return TickTable(
        TickRow(
            r["symbol"],
            date.fromisoformat(r["effective_from"]),
            _d(r.get("effective_to")),
            Decimal(str(r["tick"])),
            _prov(r, "basis"),
        )
        for r in t.rows
    )


# ---------------------------------------------------------------- corporate events (D5, limitation L-6)


class EventType(StrEnum):
    SYMBOL_CHANGE = "SYMBOL_CHANGE"
    DEMERGER = "DEMERGER"
    SPLIT = "SPLIT"
    BONUS = "BONUS"
    RIGHTS = "RIGHTS"
    DIVIDEND = "DIVIDEND"
    OTHER = "OTHER"


class EventStatus(StrEnum):
    CONFIRMED = "CONFIRMED"
    UNRESOLVED = "UNRESOLVED"  # material event whose treatment is not established: fails closed
    FLAGGED = "FLAGGED"  # recorded, not excluded


EXCLUDING_TYPES = frozenset({EventType.SYMBOL_CHANGE, EventType.DEMERGER})


@dataclass(frozen=True, slots=True)
class CorporateEvent:
    event_type: EventType
    symbol: str
    day: date
    source: str
    source_hash: str
    confidence: str
    status: EventStatus


class EventTable:
    def __init__(self, events: list[CorporateEvent]) -> None:
        seen: set[tuple[str, date, EventType]] = set()
        for e in events:
            k = (e.symbol, e.day, e.event_type)
            if k in seen:
                raise ReferenceTableError(f"duplicate event row {k}")
            seen.add(k)
        self._by_key: dict[tuple[str, date], list[CorporateEvent]] = {}
        for e in events:
            self._by_key.setdefault((e.symbol, e.day), []).append(e)

    def on(self, symbol: str, day: date) -> list[CorporateEvent]:
        return list(self._by_key.get((symbol, day), ()))

    def exclusion_reason(self, symbol: str, day: date) -> str | None:
        """`L6_EVENT` for a confirmed symbol change or demerger; `L6_EVENT_UNRESOLVED` fails closed."""
        evs = self.on(symbol, day)
        if any(e.status is EventStatus.UNRESOLVED for e in evs):
            return "L6_EVENT_UNRESOLVED"
        if any(e.status is EventStatus.CONFIRMED and e.event_type in EXCLUDING_TYPES for e in evs):
            return "L6_EVENT"
        return None

    def has_event(self, symbol: str, day: date) -> bool:
        return bool(self._by_key.get((symbol, day)))


def event_table_from(t: LoadedTable) -> EventTable:
    return EventTable(
        [
            CorporateEvent(
                EventType(r["event_type"]),
                r["symbol"],
                date.fromisoformat(r["date"]),
                _prov(r, "source"),
                _prov(r, "source_hash"),
                r["confidence"],
                EventStatus(r["status"]),
            )
            for r in t.rows
        ]
    )


# ---------------------------------------------------------------- session facts (D6, limitation L-3)

SESSION_HOURS_UNKNOWN = "SESSION_HOURS_UNKNOWN"


@dataclass(frozen=True, slots=True)
class SessionFacts:
    day: date
    session_open: time
    continuous_end: time
    last_expected_bar_start: time
    expected_bar_count: int
    segments: tuple[tuple[time, time], ...]  # continuous trading segments (special sessions)
    source: str
    confidence: str
    missing_late_bar_flag: bool  # L-3: the final expected bar is known to be absent in stored data
    excluded_reason: str | None  # primary-population exclusion (for example SPECIAL_SESSION)


class SessionFactsTable:
    """Dated rows: `regimes` (inclusive date ranges) plus single-date `special` rows, which win."""

    def __init__(self, regimes: list[tuple[date, date | None, SessionFacts]], special: list[SessionFacts]):
        regimes = sorted(regimes, key=lambda r: r[0])
        for a, b in pairwise(regimes):
            if a[1] is None or a[1] >= b[0]:
                raise ReferenceTableError(f"overlapping session regimes at {b[0]}")
        days = [s.day for s in special]
        if len(days) != len(set(days)):
            raise ReferenceTableError("duplicate special-session date")
        self._regimes = regimes
        self._special = {s.day: s for s in special}

    def facts(self, day: date) -> SessionFacts | None:
        """`None` means unknown: the caller excludes with `SESSION_HOURS_UNKNOWN`; nothing is defaulted."""
        if day in self._special:
            return self._special[day]
        for lo, hi, f in self._regimes:
            if lo <= day and (hi is None or day <= hi):
                return SessionFacts(
                    day,
                    f.session_open,
                    f.continuous_end,
                    f.last_expected_bar_start,
                    f.expected_bar_count,
                    f.segments,
                    f.source,
                    f.confidence,
                    f.missing_late_bar_flag,
                    f.excluded_reason,
                )
        return None


def _t(s: str) -> time:
    return time.fromisoformat(s)


def _facts(r: dict[str, Any], day: date) -> SessionFacts:
    return SessionFacts(
        day,
        _t(r["session_open"]),
        _t(r["continuous_end"]),
        _t(r["last_expected_bar_start"]),
        int(r["expected_bar_count"]),
        tuple((_t(a), _t(b)) for a, b in r.get("segments", [[r["session_open"], r["continuous_end"]]])),
        _prov(r, "source"),
        r["confidence"],
        bool(r.get("missing_late_bar_flag", False)),
        r.get("excluded_reason"),
    )


def session_table_from(t: LoadedTable) -> SessionFactsTable:
    regimes: list[tuple[date, date | None, SessionFacts]] = []
    special: list[SessionFacts] = []
    for r in t.rows:
        if "date" in r:
            special.append(_facts(r, date.fromisoformat(r["date"])))
        else:
            lo = date.fromisoformat(r["effective_from"])
            regimes.append((lo, _d(r.get("effective_to")), _facts(r, lo)))
    return SessionFactsTable(regimes, special)


def session_bounds(day: date, f: SessionFacts, tz: Any) -> tuple[datetime, datetime]:
    return datetime.combine(day, f.session_open, tz), datetime.combine(day, f.continuous_end, tz)


# ---------------------------------------------------------------- price-basis matrix (D3)


def load_price_basis(
    csv_path: Path,
    manifest_path: Path,
    expected_sha256: str,
    *,
    require_reviewed: bool = True,
    allow_solo: bool = False,
) -> tuple[dict[tuple[str, date], str], LoadedTable]:
    """Per instrument-session price basis from the archived matrix CSV and its provenance manifest.

    The manifest (`*.MANIFEST.json`) must carry the same SHA-256 and a `review_status`; an unreviewed matrix
    is refused by default (DR-7/DR-7a). Returns `({(symbol, day): scale_class}, LoadedTable)`; the caller maps
    the class to `PriceBasis`. Unknown classes, duplicate keys and a manifest mismatch fail the load.
    """
    actual = file_sha256(csv_path)
    if actual != expected_sha256:
        raise ReferenceTableError(
            f"{csv_path.name}: sha256 {actual} does not match the pinned {expected_sha256}"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("sha256") != actual or manifest.get("kind") != "price_basis_matrix":
        raise ReferenceTableError(f"{manifest_path.name}: does not describe {csv_path.name}")
    status = manifest.get("review_status")
    approval = _gate(manifest, csv_path.name, require_reviewed, allow_solo)
    import csv as _csv

    out: dict[tuple[str, date], str] = {}
    rows: list[dict[str, Any]] = []
    with csv_path.open(newline="", encoding="utf-8") as fh:
        for r in _csv.DictReader(fh):
            key = (r["symbol"], date.fromisoformat(r["date"]))
            if key in out:
                raise ReferenceTableError(f"duplicate price-basis row {key}")
            if r["scale_class"] not in ("TRADED_SCALE_VERIFIED", "PROVIDER_ADJUSTED", "UNVERIFIABLE"):
                raise ReferenceTableError(f"unknown scale_class {r['scale_class']!r} at {key}")
            out[key] = r["scale_class"]
            rows.append({"symbol": r["symbol"], "date": r["date"], "scale_class": r["scale_class"]})
    return out, LoadedTable(
        "price_basis_matrix", str(manifest.get("artifact")), actual, str(status), rows, approval
    )
