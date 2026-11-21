"""Merge the chunk files of one single-strategy run into one report. Run from `python-engine/`:

  uv run python scripts/merge_backtests.py CHUNK.pkl [CHUNK.pkl ...] [--json merged.json]

Chunks come from `run_backtest.py --save-chunk`. They must share one configuration and not overlap. The merged
metrics are computed by the same code as a single run (app/backtest/chunks.py). Prints no credentials.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.backtest.chunks import merge_chunks
from app.backtest.exclusions import summarise
from app.backtest.report import format_report, report_dict


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("chunks", nargs="+", type=Path)
    p.add_argument("--json", dest="json_out", type=Path)
    a = p.parse_args(argv)
    result, exclusions, meta = merge_chunks(a.chunks)
    print(format_report(result))
    print("Exclusions: " + (", ".join(f"{k} {v}" for k, v in summarise(exclusions).items()) or "none"))
    print(f"Chunks: {len(a.chunks)}; members_on {meta.get('members_on')}")
    if a.json_out:
        out = report_dict(result)
        out["exclusions"] = [
            {"day": e.day.isoformat(), "symbol": e.symbol, "reason": e.reason} for e in exclusions
        ]
        a.json_out.write_text(json.dumps(out, indent=2))
        print(f"\nFull result written to {a.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
