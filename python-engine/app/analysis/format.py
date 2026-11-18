"""Text and JSON output for a scan."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from app.analysis.scan import ScanRow
from app.ingestion.session import IST

HEADER = "Decision support only. You place any order yourself on the broker platform."


def _p(v: Decimal | None) -> str:
    return "-" if v is None else f"{v:.2f}"


def _t(v: datetime | None) -> str:
    return "-" if v is None else v.astimezone(IST).strftime("%H:%M")


def format_scan(rows: list[ScanRow], data_label: str, now: datetime, show_all: bool = False) -> str:
    """`data_label` names the data source and mode (DEMO data is never presented as live, ADR-011)."""
    lines = [f"Scan at {now.astimezone(IST):%Y-%m-%d %H:%M} IST | data: {data_label}", HEADER]
    stale = [r.symbol for r in rows if r.stale]
    if stale:
        lines.append(f"STALE DATA (latest bar older than two bars): {', '.join(stale)}")
    shown = [r for r in rows if show_all or r.signal in ("ENTRY_CONFIRMED", "BUY_WATCH")]
    if not shown:
        lines.append("No actionable setups. No-trade is a valid outcome.")
    else:
        lines.append(
            f"{'symbol':<12}{'signal':<17}{'setup':<24}{'PAQS':>5}{'entry':>10}{'stop':>10}{'target':>10}"
            f"{'rr':>6}{'qty':>6}{'risk ₹':>9}{'until':>7}  notes"
        )
        for r in shown:
            paqs = "-" if r.paqs is None else str(r.paqs)
            qty = "-" if r.qty is None else str(r.qty)
            lines.append(
                f"{r.symbol:<12}{r.signal:<17}{(r.setup_type or '-'):<24}{paqs:>5}"
                f"{_p(r.entry):>10}{_p(r.stop):>10}{_p(r.target):>10}{_p(r.rr):>6}"
                f"{qty:>6}{_p(r.risk_amount):>9}{_t(r.valid_until):>7}  {', '.join(r.reasons)}"
            )
    counts: dict[str, int] = {}
    for r in rows:
        counts[r.signal] = counts.get(r.signal, 0) + 1
    lines.append("Symbols: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    return "\n".join(lines)


def scan_dict(rows: list[ScanRow], data_label: str, now: datetime) -> dict[str, Any]:
    def plain(v: Any) -> Any:
        if isinstance(v, Decimal):
            return str(v)
        if isinstance(v, datetime):
            return v.isoformat()
        if isinstance(v, tuple):
            return [plain(x) for x in v]
        return v

    return {
        "as_of": now.isoformat(),
        "data": data_label,
        "notice": HEADER,
        "rows": [{k: plain(getattr(r, k)) for k in r.__dataclass_fields__} for r in rows],
    }
