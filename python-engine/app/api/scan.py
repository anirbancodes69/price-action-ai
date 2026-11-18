"""``POST /internal/v1/scan`` (T-I79): analyse a universe on stored bars and size the plans."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Annotated, Protocol

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import create_engine, select

from app.analysis.account import AccountInput
from app.analysis.detail import to_detail
from app.analysis.format import HEADER
from app.analysis.scan import ScanRow, scan_universe
from app.analysis.snapshot import load_symbol_snapshot
from app.api.deps import ruleset_for
from app.backtest.replay import AnalyseFn, SessionSpec, SymbolData, default_analyse
from app.db.tables import data_sources, instruments
from app.domain.params import RulesetParams
from app.domain.risk.account import ClosedTrade, OpenPosition
from app.ingestion.session import IST
from app.ingestion.universe import universe_members
from app.schemas.analysis_detail import AnalysisDetail, AnalysisDetailRequest
from app.schemas.scan import ScanRequest, ScanResponse, ScanRowModel
from app.settings import Settings, get_settings

router = APIRouter()


class SnapshotSource(Protocol):
    """Where the scan reads its bars from. The real one is Postgres; tests substitute a fake."""

    def source_info(self, source: uuid.UUID) -> tuple[str, str] | None: ...

    def universe(
        self, source: uuid.UUID, code: str, as_of: datetime, lookback: int, replay: bool
    ) -> list[tuple[SymbolData, SessionSpec]]: ...

    def symbol(
        self, source: uuid.UUID, symbol: str, as_of: datetime | None, lookback: int
    ) -> tuple[SymbolData, SessionSpec] | None: ...


class DbSnapshotSource:
    def __init__(self, url: str) -> None:
        self._engine = create_engine(url)

    def dispose(self) -> None:
        self._engine.dispose()

    def source_info(self, source: uuid.UUID) -> tuple[str, str] | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                select(data_sources.c.mode, data_sources.c.provider).where(data_sources.c.id == source)
            ).first()
        return None if row is None else (row.mode, row.provider)

    def universe(
        self, source: uuid.UUID, code: str, as_of: datetime, lookback: int, replay: bool
    ) -> list[tuple[SymbolData, SessionSpec]]:
        out: list[tuple[SymbolData, SessionSpec]] = []
        with self._engine.connect() as conn:
            for sym, iid in universe_members(conn, code, as_of.astimezone(IST).date()).items():
                snap = load_symbol_snapshot(conn, source, iid, sym, lookback, as_of if replay else None)
                if snap is not None:
                    out.append(snap)
        return out

    def symbol(
        self, source: uuid.UUID, symbol: str, as_of: datetime | None, lookback: int
    ) -> tuple[SymbolData, SessionSpec] | None:
        with self._engine.connect() as conn:
            iid = conn.execute(
                select(instruments.c.id).where(
                    instruments.c.exchange == "NSE",
                    instruments.c.trading_symbol == symbol,
                    instruments.c.status == "ACTIVE",
                )
            ).scalar()
            return None if iid is None else load_symbol_snapshot(conn, source, iid, symbol, lookback, as_of)


def get_snapshot_source(settings: Annotated[Settings, Depends(get_settings)]) -> Iterator[SnapshotSource]:
    src = DbSnapshotSource(settings.database_url.get_secret_value())
    try:
        yield src
    finally:
        src.dispose()


def get_analyse_fn() -> AnalyseFn:
    return default_analyse


def account_input(req: ScanRequest) -> AccountInput:
    """The caller's aggregates as an `AccountInput` (positions are summarised, so represent them as one)."""
    a = req.account
    closed = (ClosedTrade(a.realised_net_pnl_today),) if a.realised_net_pnl_today else ()
    base = AccountInput(a.capital, closed, (), a.open_positions, a.losing_streak)
    # Open risk and cost basis arrive pre-aggregated; carry them through a synthetic position.
    if a.open_risk or a.open_cost_basis:
        pos = OpenPosition(a.open_cost_basis, a.open_cost_basis - a.open_risk, 1)
        base = AccountInput(a.capital, closed, (pos,), max(0, a.open_positions - 1), a.losing_streak)
    return base


def to_model(r: ScanRow) -> ScanRowModel:
    return ScanRowModel(
        symbol=r.symbol,
        signal=r.signal,
        setup_type=r.setup_type,
        setup_status=r.setup_status,
        paqs=r.paqs,
        entry=r.entry,
        stop=r.stop,
        target=r.target,
        target_source=r.target_source,
        rr=r.rr,
        quantity=r.qty,
        risk_amount=r.risk_amount,
        position_value=r.position_value,
        binding_constraint=r.binding_constraint,
        reasons=list(r.reasons),
        signal_at=r.signal_at,
        valid_until=r.valid_until,
        last_bar_end=r.last_bar_end,
        stale=r.stale,
        htf_state=r.htf_state,
    )


@router.post("/scan")
def scan(
    req: ScanRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    source: Annotated[SnapshotSource, Depends(get_snapshot_source)],
    analyse_fn: Annotated[AnalyseFn, Depends(get_analyse_fn)],
) -> ScanResponse:
    params: RulesetParams = ruleset_for(settings)
    info = source.source_info(req.data_source_id)
    if info is None:
        raise HTTPException(404, detail="DATA_SOURCE_NOT_FOUND")
    now = req.as_of_ts or datetime.now(UTC)
    items = source.universe(
        req.data_source_id,
        req.universe_code,
        now,
        params.int_("analysis.lookback_sessions"),
        req.as_of_ts is not None,
    )
    rows = scan_universe(items, params, account_input(req), now, analyse_fn)
    if not req.include_no_trade:
        rows = [r for r in rows if r.signal in ("ENTRY_CONFIRMED", "BUY_WATCH") or r.stale]
    return ScanResponse(
        as_of_ts=now,
        data_mode=info[0],
        provider=info[1],
        ruleset_version=f"{params.code} {params.version}",
        notice=HEADER,
        rows=[to_model(r) for r in rows],
    )


@router.post("/analysis")
def analysis(
    req: AnalysisDetailRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    source: Annotated[SnapshotSource, Depends(get_snapshot_source)],
    analyse_fn: Annotated[AnalyseFn, Depends(get_analyse_fn)],
) -> AnalysisDetail:
    """The full analysis of one symbol at the latest closed bar (or `as_of_ts`)."""
    params = ruleset_for(settings)
    if source.source_info(req.data_source_id) is None:
        raise HTTPException(404, detail="DATA_SOURCE_NOT_FOUND")
    snap = source.symbol(
        req.data_source_id, req.symbol, req.as_of_ts, params.int_("analysis.lookback_sessions")
    )
    if snap is None:
        raise HTTPException(404, detail="NO_BARS_FOR_SYMBOL")
    sym, spec = snap
    return to_detail(sym, spec, analyse_fn(sym, len(sym.bars_5m), spec, params))
