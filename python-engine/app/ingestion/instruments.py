"""Instrument sync: provider instrument master -> `instruments`, provider refs and snapshots (ENG-05 §6)."""

from __future__ import annotations

import uuid
from collections.abc import Collection
from dataclasses import dataclass
from datetime import date

from sqlalchemy import Connection, func, insert, select, update

from app.db.tables import instrument_provider_refs, instrument_snapshots, instruments
from app.providers.base import MarketDataProvider, ProviderContext


@dataclass(frozen=True, slots=True)
class SyncReport:
    created: int
    refs_added: int
    snapshots_added: int
    missing: tuple[str, ...]  # requested symbols the provider does not list


def sync_instruments(
    conn: Connection,
    provider: MarketDataProvider,
    ctx: ProviderContext,
    symbols: Collection[str],
    on: date,
) -> SyncReport:
    """Create or refresh the NSE equities in `symbols` from the provider's instrument master.

    Idempotent. A changed provider token closes the old reference and opens a new one on `on`; a changed
    tick size, lot size or name does the same for the snapshot. Symbols the provider does not list are
    reported, never invented.
    """
    wanted = {s.strip().upper() for s in symbols if s.strip()}
    listed = {
        i.ref.symbol: i for i in provider.fetch_instruments(ctx) if not i.is_index and i.ref.symbol in wanted
    }
    created = refs_added = snaps_added = 0
    for symbol in sorted(listed):
        inst = listed[symbol]
        iid = conn.execute(
            select(instruments.c.id).where(
                instruments.c.exchange == "NSE",
                instruments.c.trading_symbol == symbol,
                instruments.c.status == "ACTIVE",
            )
        ).scalar()
        if iid is None:
            iid = uuid.uuid4()
            conn.execute(
                insert(instruments).values(
                    id=iid,
                    exchange="NSE",
                    segment="EQ",
                    trading_symbol=symbol,
                    name=inst.name or symbol,
                    status="ACTIVE",
                    is_demo=False,
                    created_at=func.now(),
                    updated_at=func.now(),
                )
            )
            created += 1
        refs_added += _ensure_ref(conn, iid, provider.provider_code, inst.ref.token, on)
        snaps_added += _ensure_snapshot(conn, iid, inst.name or symbol, inst.tick_size, inst.lot_size, on)
    conn.commit()
    return SyncReport(created, refs_added, snaps_added, tuple(sorted(wanted - set(listed))))


def _ensure_ref(conn: Connection, iid: uuid.UUID, provider: str, ref_id: str, on: date) -> int:
    r = instrument_provider_refs
    cur = conn.execute(
        select(r.c.id, r.c.provider_token).where(
            r.c.instrument_id == iid, r.c.provider == provider, r.c.valid_to.is_(None)
        )
    ).first()
    if cur is not None and cur.provider_token == ref_id:
        return 0
    if cur is not None:
        conn.execute(update(r).where(r.c.id == cur.id).values(valid_to=on))
    row = {"id": uuid.uuid4(), "instrument_id": iid, "provider": provider, "valid_from": on}
    row["provider_token"] = ref_id  # the provider's opaque instrument id (not a credential)
    conn.execute(insert(r).values(**row))
    return 1


def _ensure_snapshot(conn: Connection, iid: uuid.UUID, name: str, tick: object, lot: int, on: date) -> int:
    s = instrument_snapshots
    cur = conn.execute(
        select(s.c.effective_from, s.c.name, s.c.tick_size, s.c.lot_size).where(
            s.c.instrument_id == iid, s.c.effective_to.is_(None)
        )
    ).first()
    if cur is not None and (cur.name, cur.tick_size, cur.lot_size) == (name, tick, lot):
        return 0
    if cur is not None:
        if cur.effective_from >= on:  # same-day correction: replace in place
            conn.execute(
                update(s)
                .where(s.c.instrument_id == iid, s.c.effective_from == cur.effective_from)
                .values(name=name, tick_size=tick, lot_size=lot)
            )
            return 0
        conn.execute(
            update(s).where(s.c.instrument_id == iid, s.c.effective_to.is_(None)).values(effective_to=on)
        )
    conn.execute(
        insert(s).values(
            instrument_id=iid, effective_from=on, name=name, tick_size=tick, lot_size=lot, status="ACTIVE"
        )
    )
    return 1
