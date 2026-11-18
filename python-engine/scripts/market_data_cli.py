"""Owner CLI for market data setup. Run from `python-engine/`:
`uv run python scripts/market_data_cli.py <command> ...`

  sync-instruments --symbols FILE            instrument master -> instruments, refs, snapshots
  load-universe --code NIFTY50 --symbols FILE --from YYYY-MM-DD
  backfill --code NIFTY50 --timeframe 5m --from YYYY-MM-DD --to YYYY-MM-DD
  history-check --code NIFTY50 --timeframe 5m --from YYYY-MM-DD --to YYYY-MM-DD

Needs DATABASE_URL (an engine-role URL), KITE_API_KEY and a fresh `.kite_token` (scripts/kite_login.py).
The NIFTY 50 symbol file is supplied by the owner: no constituent source is verified yet (OQ-BT-01).
Never prints credentials.
"""

from __future__ import annotations

import argparse
import sys
import time
import uuid
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import create_engine, select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # make `app` importable when run as a script


from app.db.tables import data_sources
from app.ingestion.backfill import backfill
from app.ingestion.history_check import history_report
from app.ingestion.instruments import sync_instruments
from app.ingestion.session import IST
from app.ingestion.universe import load_universe, read_symbol_file, universe_members, universe_refs
from app.providers.base import ProviderContext
from app.settings import get_settings
from app.workers.ingest import build_provider


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("sync-instruments")
    a.add_argument("--symbols", type=Path, required=True)
    b = sub.add_parser("load-universe")
    b.add_argument("--code", default="NIFTY50")
    b.add_argument("--symbols", type=Path, required=True)
    b.add_argument("--from", dest="from_", type=date.fromisoformat, required=True)
    c = sub.add_parser("backfill")
    c.add_argument("--code", default="NIFTY50")
    c.add_argument("--timeframe", choices=["5m", "15m"], default="5m")
    c.add_argument("--from", dest="from_", type=date.fromisoformat, required=True)
    c.add_argument("--to", type=date.fromisoformat, required=True)
    d = sub.add_parser("history-check")
    d.add_argument("--code", default="NIFTY50")
    d.add_argument("--timeframe", choices=["5m", "15m"], default="5m")
    d.add_argument("--from", dest="from_", type=date.fromisoformat, required=True)
    d.add_argument("--to", type=date.fromisoformat, required=True)
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    s = get_settings()
    if not s.ingest_data_source_id:
        print("Set INGEST_DATA_SOURCE_ID (the data_sources row to write candles for).", file=sys.stderr)
        return 2
    source = uuid.UUID(s.ingest_data_source_id)
    provider, supplier = build_provider(s)
    ctx = ProviderContext(str(source), supplier)
    engine = create_engine(s.database_url.get_secret_value())
    today = datetime.now(UTC).astimezone(IST).date()
    with engine.connect() as conn:
        if conn.execute(select(data_sources.c.id).where(data_sources.c.id == source)).first() is None:
            print("INGEST_DATA_SOURCE_ID does not exist in data_sources.", file=sys.stderr)
            return 2
        if args.cmd == "sync-instruments":
            r = sync_instruments(conn, provider, ctx, read_symbol_file(args.symbols), today)
            print(f"created={r.created} refs_added={r.refs_added} snapshots_added={r.snapshots_added}")
            if r.missing:
                print("not listed by the provider:", ", ".join(r.missing))
        elif args.cmd == "load-universe":
            u = load_universe(conn, args.code, read_symbol_file(args.symbols), args.from_)
            print(f"added={u.added} closed={u.closed} unchanged={u.unchanged}")
            if u.unknown:
                print("no instrument (run sync-instruments first):", ", ".join(u.unknown))
            if u.not_closed:
                print("could not close (joined on/after the date):", ", ".join(u.not_closed))
        elif args.cmd == "history-check":
            members = universe_members(conn, args.code, args.to)
            hr = history_report(
                conn,
                source,
                members,
                args.timeframe,
                args.from_,
                args.to,
                provider.capabilities().intraday_close,
            )
            print(f"{hr.timeframe}: {hr.sessions} sessions {hr.first}..{hr.last}, clean={hr.clean}")
            for c in hr.symbols:
                if c.missing_bars or c.missing_sessions:
                    print(
                        f"  {c.symbol}: {c.coverage_pct:.1f}% complete, {c.missing_bars} bars missing,"
                        f" {len(c.missing_sessions)} sessions absent, worst {list(c.worst)}"
                    )
        else:
            refs = universe_refs(conn, args.code, provider.provider_code, args.to)
            rep = backfill(conn, source, provider, ctx, refs, args.timeframe, args.from_, args.to, time.sleep)
            print(f"{rep.status}: inserted={rep.inserted} updated={rep.updated} requests={rep.requests}")
            for line in [*rep.failed[:20], *(f"unmapped {x}" for x in rep.skipped_unmapped[:20])]:
                print(" ", line)
    engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
