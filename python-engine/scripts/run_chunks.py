"""Run a single-strategy backtest in date chunks, one after the other. Run from `python-engine/`:

  uv run python scripts/run_chunks.py --strategy liquidity_sweep_reversal --experiment 4a \
      --ruleset pa-intraday@0.3.0 --members-on 2026-11-19 --out-dir DIR \
      --chunk 2024-01-02:2024-03-28 --chunk 2024-04-01:2024-06-28 ...

Each chunk is `scripts/run_backtest.py` in its own process (memory is released between chunks) that writes
`DIR/<from>_<to>.pkl` and `DIR/<from>_<to>.txt`. A chunk whose `.pkl` exists is skipped, so the run can be
restarted after a failure. It never runs chunks in parallel. A failed chunk stops the chain (exit code 1).
Merge with `scripts/merge_backtests.py DIR/*.pkl`. Needs the same environment as `run_backtest.py`.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--strategy", required=True)
    p.add_argument("--experiment", required=True, choices=["4a", "4b"])
    p.add_argument("--ruleset", required=True)
    p.add_argument("--members-on", required=True)
    p.add_argument("--out-dir", required=True, type=Path)
    p.add_argument("--chunk", action="append", required=True, help="FROM:TO (inclusive session dates)")
    p.add_argument("--tie-break-seed", default="1")
    p.add_argument("--slippage-model", choices=["legacy", "adverse-all"], default="adverse-all")
    a = p.parse_args(argv)
    a.out_dir.mkdir(parents=True, exist_ok=True)
    for spec in a.chunk:
        first, last = spec.split(":")
        stem = a.out_dir / f"{first}_{last}"
        if stem.with_suffix(".pkl").exists():
            print(f"skip {spec} (done)", flush=True)
            continue
        t0 = time.time()
        print(f"start {spec}", flush=True)
        cmd = [
            sys.executable,
            str(HERE / "run_backtest.py"),
            "--from", first, "--to", last,
            "--ruleset", a.ruleset, "--members-on", a.members_on,
            "--strategy", a.strategy, "--experiment", a.experiment,
            "--tie-break-seed", a.tie_break_seed,
            "--slippage-model", a.slippage_model,
            "--save-chunk", str(stem.with_suffix(".pkl")),
        ]  # fmt: skip
        with stem.with_suffix(".txt").open("w") as out:
            proc = subprocess.run(cmd, stdout=out, stderr=subprocess.STDOUT, check=False)  # noqa: S603
        rc = proc.returncode
        print(f"done {spec} rc={rc} in {time.time() - t0:.0f}s", flush=True)
        if rc != 0:
            print("chunk failed; stopping the chain", file=sys.stderr, flush=True)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
