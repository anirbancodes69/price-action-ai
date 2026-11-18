"""Universe membership loader and provider references (ENG-05, ARC-03 §6.4).

The constituent list is **owner-supplied** (a symbol file): no machine-readable point-in-time source is
verified yet (OQ-BT-01), so nothing here guesses membership.
"""

from __future__ import annotations

import csv
import io
import uuid
from collections.abc import Collection
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from sqlalchemy import Connection, insert, select, update

from app.db.tables import instrument_provider_refs, instruments, universe_memberships, universes
from app.providers.base import ProviderInstrumentRef


class UnknownUniverse(Exception):
    """The universe row does not exist (Laravel seeds them; the engine only reads `universes`)."""


@dataclass(frozen=True, slots=True)
class UniverseReport:
    added: int
    closed: int
    unchanged: int
    unknown: tuple[str, ...]  # symbols with no active instrument: run the instrument sync first
    not_closed: tuple[str, ...]  # removals that could not be dated (would violate the membership range check)


def parse_symbols(text: str) -> list[str]:
    """Symbols from a plain list (one per line, `#` comments) or a CSV with a `Symbol` column."""
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    if not lines:
        return []
    head = [c.strip().lower() for c in next(csv.reader([lines[0]]))]
    if "symbol" in head:
        col = head.index("symbol")
        rows = csv.reader(io.StringIO("\n".join(lines[1:])))
        out = [r[col].strip().upper() for r in rows if len(r) > col and r[col].strip()]
    else:
        out = [ln.split(",")[0].strip().upper() for ln in lines]
    return list(dict.fromkeys(out))  # de-duplicated, order kept


def read_symbol_file(path: Path) -> list[str]:
    return parse_symbols(path.read_text(encoding="utf-8"))


def load_universe(
    conn: Connection, code: str, symbols: Collection[str], effective_from: date
) -> UniverseReport:
    """Make the open memberships of universe `code` equal `symbols` as of `effective_from`."""
    uid = conn.execute(select(universes.c.id).where(universes.c.code == code)).scalar()
    if uid is None:
        raise UnknownUniverse(code)
    wanted = {s.strip().upper() for s in symbols if s.strip()}
    ids: dict[str, uuid.UUID] = {}
    for sym, iid in conn.execute(
        select(instruments.c.trading_symbol, instruments.c.id).where(
            instruments.c.exchange == "NSE",
            instruments.c.status == "ACTIVE",
            instruments.c.trading_symbol.in_(wanted),
        )
    ):
        ids[sym] = iid
    m = universe_memberships
    open_rows = {
        r.instrument_id: r
        for r in conn.execute(
            select(m.c.id, m.c.instrument_id, m.c.effective_from).where(
                m.c.universe_id == uid, m.c.effective_to.is_(None)
            )
        )
    }
    added = unchanged = 0
    for sym in sorted(ids):
        if ids[sym] in open_rows:
            unchanged += 1
            continue
        conn.execute(
            insert(m).values(
                id=uuid.uuid4(),
                universe_id=uid,
                instrument_id=ids[sym],
                effective_from=effective_from,
                source_ref="owner symbol file",
            )
        )
        added += 1
    closed = 0
    not_closed: list[str] = []
    names = dict(conn.execute(select(instruments.c.id, instruments.c.trading_symbol)).all())
    for iid, row in open_rows.items():
        if iid in ids.values():
            continue
        if effective_from > row.effective_from:
            conn.execute(update(m).where(m.c.id == row.id).values(effective_to=effective_from))
            closed += 1
        else:
            not_closed.append(names.get(iid, str(iid)))
    conn.commit()
    return UniverseReport(
        added, closed, unchanged, tuple(sorted(wanted - set(ids))), tuple(sorted(not_closed))
    )


def universe_refs(conn: Connection, code: str, provider_code: str, on: date) -> list[ProviderInstrumentRef]:
    """Provider references of the universe members valid on `on`, ordered by symbol."""
    m, r = universe_memberships, instrument_provider_refs
    rows = conn.execute(
        select(instruments.c.trading_symbol, r.c.provider_token)
        .select_from(
            universes.join(m, m.c.universe_id == universes.c.id)
            .join(instruments, instruments.c.id == m.c.instrument_id)
            .join(r, r.c.instrument_id == instruments.c.id)
        )
        .where(
            universes.c.code == code,
            m.c.effective_from <= on,
            (m.c.effective_to.is_(None)) | (m.c.effective_to > on),
            r.c.provider == provider_code,
            r.c.valid_from <= on,
            (r.c.valid_to.is_(None)) | (r.c.valid_to > on),
        )
        .order_by(instruments.c.trading_symbol)
    ).all()
    return [ProviderInstrumentRef(token=tok, symbol=sym) for sym, tok in rows]


def universe_members(conn: Connection, code: str, on: date) -> dict[str, uuid.UUID]:
    """Symbol -> instrument id of the members valid on `on` (point in time, effective-dated)."""
    m = universe_memberships
    rows = conn.execute(
        select(instruments.c.trading_symbol, instruments.c.id)
        .select_from(
            universes.join(m, m.c.universe_id == universes.c.id).join(
                instruments, instruments.c.id == m.c.instrument_id
            )
        )
        .where(
            universes.c.code == code,
            m.c.effective_from <= on,
            (m.c.effective_to.is_(None)) | (m.c.effective_to > on),
        )
        .order_by(instruments.c.trading_symbol)
    ).all()
    return dict(rows)
