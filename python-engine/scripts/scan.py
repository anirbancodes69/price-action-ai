"""Scan the universe on the latest stored bars and print sized trade plans. Run from `python-engine/`:

  uv run python scripts/scan.py [--code NIFTY50] [--account account.json] [--as-of ISO] [--all]
      [--watch SECONDS] [--json out.json] [--ruleset pa-intraday@0.1.0]

Needs DATABASE_URL (an engine-role URL), INGEST_DATA_SOURCE_ID and bars ingested by the tick (or backfilled).
`--account` is a JSON file with your capital and today's closed trades and open positions (the engine does not
store trades yet); without it a fresh account with ₹1,00,000 is assumed. Decision support only (ADR-010).
Never prints credentials.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine, select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # make `app` importable when run as a script

from app.analysis.account import AccountInput, read_account
from app.analysis.format import format_scan, scan_dict
from app.analysis.scan import scan_universe
from app.analysis.snapshot import load_symbol_snapshot
from app.backtest.b0_contract import legacy_refusal
from app.db.tables import data_sources
from app.ingestion.session import IST
from app.ingestion.universe import universe_members
from app.rulesets import load_ruleset
from app.settings import get_settings


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--code", default="NIFTY50")
    p.add_argument("--account", type=Path)
    p.add_argument("--as-of", type=datetime.fromisoformat, help="replay a past moment (ISO, with offset)")
    p.add_argument("--all", action="store_true", help="also list NO_TRADE and unanalysable symbols")
    p.add_argument("--watch", type=int, metavar="SECONDS", help="repeat every SECONDS until interrupted")
    p.add_argument("--json", dest="json_out", type=Path)
    p.add_argument("--ruleset", default="pa-intraday@0.1.0")
    return p


def run_once(a: argparse.Namespace) -> int:
    s = get_settings()
    if not s.ingest_data_source_id:
        print("Set INGEST_DATA_SOURCE_ID (the data source whose candles to scan).", file=sys.stderr)
        return 2
    source = uuid.UUID(s.ingest_data_source_id)
    refusal = legacy_refusal(None, a.ruleset)
    if refusal:
        print(refusal, file=sys.stderr)
        return 2
    code, version = a.ruleset.split("@")
    params = load_ruleset(code, version)
    account = read_account(a.account) if a.account else AccountInput(Decimal(100000))
    now = a.as_of or datetime.now(UTC)
    engine = create_engine(s.database_url.get_secret_value())
    with engine.connect() as conn:
        ds = conn.execute(
            select(data_sources.c.mode, data_sources.c.provider).where(data_sources.c.id == source)
        ).first()
        if ds is None:
            print("INGEST_DATA_SOURCE_ID does not exist in data_sources.", file=sys.stderr)
            return 2
        members = universe_members(conn, a.code, now.astimezone(IST).date())
        if not members:
            print(f"No members in universe {a.code}. Run market_data_cli.py load-universe.", file=sys.stderr)
            return 2
        items = []
        for sym, iid in members.items():
            snap = load_symbol_snapshot(
                conn, source, iid, sym, params.int_("analysis.lookback_sessions"), a.as_of
            )
            if snap is not None:
                items.append(snap)
    engine.dispose()
    rows = scan_universe(items, params, account, now)
    label = f"{ds.provider} ({ds.mode})" + (" - SAMPLE DATA, not live" if ds.mode == "DEMO" else "")
    print(format_scan(rows, label, now, a.all))
    if a.json_out:
        a.json_out.write_text(json.dumps(scan_dict(rows, label, now), indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    a = _parser().parse_args(argv)
    if not a.watch:
        return run_once(a)
    try:
        while True:
            print("\033[2J\033[H", end="")  # clear the terminal between refreshes
            run_once(a)
            time.sleep(a.watch)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
