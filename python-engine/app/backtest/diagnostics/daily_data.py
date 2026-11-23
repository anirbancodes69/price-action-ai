"""Daily-bar loading shared by the Gate 0 and daily screening runners (research harness).

Prices are loaded only up to a caller-chosen last date (the in-sample guard). The special sessions and the
Gate 0 data findings (docs/research/gate0-daily-diagnosis-report.md) are applied by the callers.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Connection, select

from app.backtest.diagnostics.daily import DayBar
from app.backtest.exclusions import SPECIAL_SESSIONS
from app.db.tables import candles

# Sessions that exist for only one or two stocks (Budget Saturday, Diwali Muhurat); found by DG-0, run 1.
DAILY_SPECIAL_SESSIONS: dict[date, str] = {
    date(2015, 2, 28): "SPECIAL_SESSION_BUDGET_SATURDAY",
    date(2016, 10, 30): "SPECIAL_SESSION_MUHURAT",
    date(2017, 10, 19): "SPECIAL_SESSION_MUHURAT",
    date(2018, 11, 7): "SPECIAL_SESSION_MUHURAT",
}
# DG-0 findings, run 1 (each checked against public records, see the Gate 0 report): provider data for these
# corporate actions is not adjusted, so the series is cut there; one bar has an unadjusted open (dropped).
KNOWN_DROPS: tuple[tuple[str, date], ...] = (("ADANIENT", date(2015, 6, 3)),)
KNOWN_BREAKS: tuple[tuple[str, date], ...] = (
    ("ADANIENT", date(2015, 6, 3)),  # demerger ex-date (Adani Ports, Adani Power, Adani Transmission)
    ("ADANIENT", date(2018, 9, 6)),  # Adani Gas demerger ex-date
    ("GRASIM", date(2017, 7, 19)),  # financial-services spin-off ex-date
)


def load_calendar(conn: Connection, source: uuid.UUID, ids: list[uuid.UUID], skip: set[date]) -> list[date]:
    """Session dates only (no prices), special sessions removed."""
    rows = conn.execute(
        select(candles.c.trade_date)
        .where(
            candles.c.data_source_id == source,
            candles.c.timeframe == "1D",
            candles.c.instrument_id.in_(ids),
        )
        .distinct()
    ).all()
    return sorted(
        r.trade_date for r in rows if r.trade_date not in SPECIAL_SESSIONS and r.trade_date not in skip
    )


def load_day_bars(
    conn: Connection, source: uuid.UUID, iid: uuid.UUID, last: date, drop: set[date]
) -> list[DayBar]:
    rows = conn.execute(
        select(
            candles.c.trade_date,
            candles.c.open,
            candles.c.high,
            candles.c.low,
            candles.c.close,
            candles.c.volume,
        )
        .where(
            candles.c.data_source_id == source,
            candles.c.instrument_id == iid,
            candles.c.timeframe == "1D",
            candles.c.trade_date <= last,  # the in-sample guard: nothing later is read
        )
        .order_by(candles.c.trade_date)
    ).all()
    return [
        DayBar(r.trade_date, r.open, r.high, r.low, r.close, int(r.volume))
        for r in rows
        if r.trade_date not in SPECIAL_SESSIONS and r.trade_date not in drop
    ]
