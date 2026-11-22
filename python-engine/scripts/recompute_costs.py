"""Recompute the charges of saved 4a trades under another cost schedule (DX-6). Run from `python-engine/`:

  uv run python scripts/recompute_costs.py DIR [DIR ...]

Reads the chunk files in each DIR (own harness files, see app/backtest/chunks.py) and prints, per directory,
the average charges per trade in R and in rupees under the assumed schedule and under `GROWW_PUBLISHED`.
Gross results do not change; only the charges do. Hypothetical, simulated results (TRD-06 BT-06).
"""

from __future__ import annotations

import glob
import pickle
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # make `app` importable when run as a script

from app.backtest.costs import GROWW_PUBLISHED, CostSchedule, intraday_costs


def main(argv: list[str] | None = None) -> int:
    dirs = (argv if argv is not None else sys.argv[1:]) or []
    if not dirs:
        print(__doc__)
        return 2
    ours = CostSchedule()
    for d in dirs:
        n = 0
        r_a = r_b = Decimal(0)
        rs_a = rs_b = Decimal(0)
        for f in sorted(glob.glob(str(Path(d) / "*.pkl"))):
            payload = pickle.loads(Path(f).read_bytes())  # noqa: S301 - own harness files
            for s in payload["sessions"]:
                for t in s.trades:
                    buy, sell = t.entry * t.qty, t.exit * t.qty
                    a = intraday_costs(buy, sell, ours).total
                    b = intraday_costs(buy, sell, GROWW_PUBLISHED).total
                    n += 1
                    r_a, r_b = r_a + a / t.risk_amount, r_b + b / t.risk_amount
                    rs_a, rs_b = rs_a + a, rs_b + b
        if n:
            print(
                f"{d}: {n} trades; charges per trade {r_a / n:.3f}R / {rs_a / n:.1f} rupees "
                f"({ours.version}) -> {r_b / n:.3f}R / {rs_b / n:.1f} rupees ({GROWW_PUBLISHED.version})"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
