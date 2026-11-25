"""Fast screening runner (T-I145, docs/research/fast-screening-protocol.md). Run from `python-engine/`:

  uv run python scripts/run_screen.py --s01 DIR --s02 DIR --out DIR [--members-on 2026-11-19]

One automatic pass, exactly as pre-registered: screen Tier 0 (saved Strategy 01 and 02 trades, all stocks,
2024) and Tier 1 (minimal entries M1-M3 on the 10 screen stocks, 2024) against matched random-entry controls;
promote by the protocol's rule; confirm only the promoted variants on 2025-01-01..2025-09-23 over all stocks
at slippage 0%, 0.05% and 0.10%. Out-of-sample and holdout are never read. Writes `screen.json` and
`screen.txt` (aggregates) to `--out`. Hypothetical, simulated results (TRD-06 BT-06).
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import uuid
from collections import defaultdict
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import Connection, create_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # make `app` importable when run as a script

from app.backtest.b0_contract import legacy_refusal
from app.backtest.costs import GROWW_PUBLISHED, CostSchedule, intraday_costs
from app.backtest.diagnostics.decompose import stop_of, stop_pct_of
from app.backtest.diagnostics.screen import (
    CONFIRM_LEVEL,
    PROMOTE_LEVEL,
    STOP_FILTERS,
    confirmed,
    detect,
    entry_params,
    load_trades,
    passes_stop,
    promoted,
    session_halves,
    tier1_variants,
)
from app.backtest.diagnostics.sim import (
    TARGET_R,
    Rules,
    draw_control,
    exit_config,
    fill_and_run,
    rules_from,
    session_times,
    simulate,
)
from app.backtest.diagnostics.stats import Sums, add, bootstrap_mean
from app.backtest.exclusions import SPECIAL_SESSIONS
from app.backtest.loader import load_bars, load_daily_levels
from app.backtest.trade import Trade
from app.domain.types import Bar
from app.ingestion.session import IST
from app.ingestion.universe import universe_members
from app.rulesets import load_ruleset
from app.settings import get_settings

D = Decimal
SCREEN = (date(2024, 1, 2), date(2024, 12, 31))
CONFIRM = (date(2025, 1, 1), date(2025, 9, 23))
SCREEN_STOCKS = [  # positions 5, 10, ..., 50 of the alphabetical NIFTY 50 (protocol §3)
    "AXISBANK", "BHARTIARTL", "ETERNAL", "HINDALCO", "ITC", "M&M", "ONGC", "SHRIRAMFIN", "TECHM", "WIPRO",
]  # fmt: skip
SEEDS = (1, 2, 3, 4, 5)
SCHED = CostSchedule()
SLIPPAGES = (D("0.00"), D("0.05"), D("0.10"))
T0_FILTERS = tuple(f for f in STOP_FILTERS if f > 0)


@dataclass(slots=True)
class Row:
    """One strategy trade and its matched controls, in R: (gross, net assumed, net Groww)."""

    variant: str
    day: date
    strat: tuple[float, float, float]
    controls: list[tuple[float, float, float]] = field(default_factory=list)
    redraws: int = 0
    missing: int = 0


def values(t: Trade) -> tuple[float, float, float]:
    g = intraday_costs(t.entry * t.qty, t.exit * t.qty, GROWW_PUBLISHED).total
    return float(t.r_gross), float(t.r_net), float(t.r_gross - g / t.risk_amount)


@dataclass(slots=True)
class SymbolBars:
    by_day: dict[date, list[Bar]]
    pdh: dict[date, Decimal]


def load_symbol(conn: Connection, source: uuid.UUID, iid: uuid.UUID, first: date, last: date) -> SymbolBars:
    margin = timedelta(days=14)
    by_day: dict[date, list[Bar]] = defaultdict(list)
    for b in load_bars(conn, source, iid, "5m", first - margin, last):
        d = b.start.astimezone(IST).date()
        if d not in SPECIAL_SESSIONS:
            by_day[d].append(b)
    levels = load_daily_levels(conn, source, iid, first - margin, last)
    days = sorted(by_day)
    pdh: dict[date, Decimal] = {}
    for k in range(1, len(days)):
        lv, pb = levels.get(days[k - 1]), by_day[days[k - 1]]
        if lv is None or (pb and (lv.high < max(b.high for b in pb) or lv.low > min(b.low for b in pb))):
            continue  # missing or inconsistent previous-day bar (D-7): no PDH that session
        pdh[days[k]] = lv.high
    return SymbolBars(dict(by_day), pdh)


def controls_for(
    row: Row, bars: list[Bar], symbol: str, pct: Decimal, key: str, rules: Rules, after: dict[int, int]
) -> None:
    for seed in SEEDS:
        rng = random.Random(f"{seed}|{key}|{symbol}|{row.day}")  # noqa: S311
        c = draw_control(bars, symbol, pct, rng, rules, SCHED, after_index=after.get(seed, 0))
        if c is None:
            row.missing += 1
            continue
        row.redraws += c.redraws
        row.controls.append(values(c.trade))
        ex = next((k for k, b in enumerate(bars) if b.start == c.trade.exit_at), len(bars))
        after[seed] = ex


def tier1_rows(
    sym: str, data: SymbolBars, first: date, last: date, rules: Rules, only: set[str] | None, params: Any
) -> tuple[list[Row], dict[str, int]]:
    rows: list[Row] = []
    n: dict[str, int] = defaultdict(int)
    for day, bars in data.by_day.items():
        if not first <= day <= last or len(bars) < 5:
            continue
        for vid, entry, flt in tier1_variants():
            if only is not None and vid not in only:
                continue
            sig = detect(entry, bars, params, data.pdh.get(day))
            if sig is None:
                continue
            n[f"{vid}_signals"] += 1
            if not passes_stop(sig.stop_pct, flt, params):
                n[f"{vid}_stop_filtered"] += 1
                continue
            c = fill_and_run(bars, sig.index, sym, sig.ref, sig.stop, rules, SCHED)
            if c is None:
                n[f"{vid}_fill_skipped"] += 1
                continue
            row = Row(vid, day, values(c.trade))
            controls_for(row, bars, sym, stop_pct_of(c.trade), vid, rules, {})
            rows.append(row)
    return rows, n


def tier0_rows(
    sym: str, data: SymbolBars, saved: dict[str, dict[str, list[Trade]]], first: date, last: date,
    rules: Rules, only: set[str] | None, params: Any,
) -> tuple[list[Row], dict[str, int]]:  # fmt: skip
    rows: list[Row] = []
    n: dict[str, int] = defaultdict(int)
    for sid, tag in (("s01", "T0-S01"), ("s02", "T0-S02")):
        mine = sorted(saved[sid].get(sym, []), key=lambda t: t.fill_at)
        after_by_day: dict[tuple[date, str], dict[int, int]] = defaultdict(dict)
        for t in mine:
            day = t.fill_at.astimezone(IST).date()
            bars = data.by_day.get(day)
            if bars is None or not first <= day <= last:
                continue
            idx = next((k for k, b in enumerate(bars) if b.start == t.fill_at), None)
            pct = stop_pct_of(t)
            for flt in T0_FILTERS:
                vid = f"{tag}@>={flt}%"
                if (only is not None and vid not in only) or idx is None or not passes_stop(pct, flt, params):
                    continue
                entry = bars[idx].open * (1 + rules.slippage_pct / 100)
                stop = stop_of(t)
                if entry <= stop:
                    continue
                target = entry + TARGET_R * (entry - stop)
                cfg = exit_config(rules, session_times(bars, rules)[2])
                st = simulate(bars, idx, sym, entry, stop, t.qty, target, cfg, SCHED)
                n[f"{vid}_trades"] += 1
                row = Row(vid, day, values(st))
                controls_for(row, bars, sym, pct, vid, rules, after_by_day[(day, vid)])
                rows.append(row)
    return rows, n


def sums_of(rows: list[Row], col: int, which: str) -> Sums:
    out: dict[Any, tuple[float, int]] = {}
    for r in rows:
        if which == "strat":
            add(out, r.day, r.strat[col])
        else:
            for c in r.controls:
                add(out, r.day, c[col])
    return out


def stats(rows: list[Row], level: float) -> dict[str, Any]:
    n = len(rows)
    out: dict[str, Any] = {"trades": n, "controls": sum(len(r.controls) for r in rows)}
    out["redraws"] = sum(r.redraws for r in rows)
    out["controls_missing"] = sum(r.missing for r in rows)
    if n == 0:
        return out
    for col, name in enumerate(("gross", "net", "net_groww")):
        s, c = sums_of(rows, col, "strat"), sums_of(rows, col, "ctl")
        diff = bootstrap_mean(s, c, level=level)
        out[name] = {
            "strategy": round(bootstrap_mean(s, level=level).estimate, 4),
            "control": round(bootstrap_mean(c, level=level).estimate, 4),
            "diff": round(diff.estimate, 4),
            "lo": round(diff.low, 4),
            "hi": round(diff.high, 4),
        }
    return out


def run_pass(
    conn: Connection,
    source: uuid.UUID,
    members: dict[str, uuid.UUID],
    saved: dict[str, dict[str, list[Trade]]],
    rng_dates: tuple[date, date],
    rules: Rules,
    tier0: set[str] | None,
    tier1: set[str] | None,
    params: Any,
    only_symbols: list[str] | None,
) -> tuple[list[Row], dict[str, int]]:
    rows: list[Row] = []
    counts: dict[str, int] = defaultdict(int)
    for k, (sym, iid) in enumerate(sorted(members.items()), 1):
        want0 = tier0 is None or len(tier0) > 0
        want1 = (tier1 is None or len(tier1) > 0) and sym in SCREEN_STOCKS
        if only_symbols is not None and sym not in only_symbols:
            continue
        if not want0 and not want1:
            continue
        data = load_symbol(conn, source, iid, *rng_dates)
        if want0:
            r0, c0 = tier0_rows(sym, data, saved, *rng_dates, rules, tier0, params)
            rows += r0
            for a, b in c0.items():
                counts[a] += b
        if want1:
            r1, c1 = tier1_rows(sym, data, *rng_dates, rules, tier1, params)
            rows += r1
            for a, b in c1.items():
                counts[a] += b
        print(f"  {k}/{len(members)} {sym} (rows so far {len(rows)})", flush=True)
    return rows, counts


def by_variant(rows: list[Row]) -> dict[str, list[Row]]:
    out: dict[str, list[Row]] = defaultdict(list)
    for r in rows:
        out[r.variant].append(r)
    return out


def all_variant_ids() -> list[str]:
    t0 = [f"T0-S0{i}@>={f}%" for i in (1, 2) for f in T0_FILTERS]
    return t0 + [v[0] for v in tier1_variants()]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--s01", required=True, type=Path)
    p.add_argument("--s02", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--code", default="NIFTY50")
    p.add_argument("--members-on", type=date.fromisoformat, default=date(2026, 11, 19))
    p.add_argument("--ruleset", default="pa-intraday@0.4.0")
    p.add_argument("--smoke", type=int, help="smoke test: only the first N symbols (results not meaningful)")
    a = p.parse_args(argv)
    s = get_settings()
    if not s.ingest_data_source_id:
        print("Set INGEST_DATA_SOURCE_ID.", file=sys.stderr)
        return 2
    source = uuid.UUID(s.ingest_data_source_id)
    refusal = legacy_refusal(None, a.ruleset)
    if refusal:
        print(refusal, file=sys.stderr)
        return 2
    code, version = a.ruleset.split("@")
    ruleset = load_ruleset(code, version)
    base_rules, params = rules_from(ruleset), entry_params(ruleset)
    saved = {"s01": load_trades(a.s01), "s02": load_trades(a.s02)}
    result: dict[str, Any] = {"screen": {}, "confirm": {}, "promoted": [], "counts": {}}
    engine = create_engine(s.database_url.get_secret_value())
    with engine.connect() as conn:
        members = universe_members(conn, a.code, a.members_on)
        assert sorted(members)[4::5] == SCREEN_STOCKS, "the screen stocks are fixed by the protocol (§3)"
        only = sorted(members)[: a.smoke] if a.smoke else None
        if only is not None:
            only = sorted(set(only) | set(SCREEN_STOCKS[:2]))
        print("Screen 2024 (Tier 0 on all stocks, Tier 1 on the 10 screen stocks)", flush=True)
        rows, counts = run_pass(conn, source, members, saved, SCREEN, base_rules, None, None, params, only)
        result["counts"]["screen"] = dict(counts)
        groups = by_variant(rows)
        promo: list[str] = []
        for vid in all_variant_ids():
            st = stats(groups.get(vid, []), PROMOTE_LEVEL)
            ok = "gross" in st and promoted(
                st["trades"], st["gross"]["strategy"], st["gross"]["diff"], st["gross"]["lo"]
            )
            st["promoted"] = ok
            result["screen"][vid] = st
            if ok:
                promo.append(vid)
        result["promoted"] = promo
        print(f"Promoted: {promo}", flush=True)
        if promo:
            t0 = {v for v in promo if v.startswith("T0-")}
            t1 = {v for v in promo if not v.startswith("T0-")}
            for slip in SLIPPAGES:
                rules = replace(base_rules, slippage_pct=slip)
                print(f"Confirm 2025, slippage {slip}%", flush=True)
                crows, ccounts = run_pass(conn, source, members, saved, CONFIRM, rules, t0, t1, params, only)
                cg = by_variant(crows)
                first_half, second_half = session_halves([r.day for r in crows])
                for vid in promo:
                    st = stats(cg.get(vid, []), CONFIRM_LEVEL)
                    entry = result["confirm"].setdefault(vid, {"by_slippage": {}})
                    entry["by_slippage"][str(slip)] = st
                    if slip == D("0.05") and "gross" in st:
                        halves = [
                            stats([r for r in cg[vid] if r.day in h], CONFIRM_LEVEL)
                            for h in (first_half, second_half)
                        ]
                        hd = [h["gross"]["diff"] if "gross" in h else 0.0 for h in halves]
                        entry["half_diffs"] = hd
                        entry["confirmed"] = confirmed(
                            st["trades"], st["gross"]["diff"], st["gross"]["lo"], hd
                        )
                        entry["counts"] = {k: v for k, v in ccounts.items() if k.startswith(vid)}
    engine.dispose()
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "screen.json").write_text(json.dumps(result, indent=2, default=str))
    text = render(result)
    (a.out / "screen.txt").write_text(text)
    print(text)
    return 0


def render(res: dict[str, Any]) -> str:
    L = [
        "Fast screening (aggregates; hypothetical, simulated results)",
        "",
        "Screen 2024 (99% interval on the gross edge)",
    ]
    L.append(
        "variant | trades | gross strat / ctl / diff [99% CI] | net strat / ctl | net Groww strat | promoted"
    )
    for vid, st in res["screen"].items():
        if "gross" not in st:
            L.append(f"{vid} | {st['trades']} | no trades")
            continue
        g, n, ng = st["gross"], st["net"], st["net_groww"]
        L.append(
            f"{vid} | {st['trades']} | {g['strategy']} / {g['control']} / {g['diff']} [{g['lo']}, {g['hi']}]"
            f" | {n['strategy']} / {n['control']} | {ng['strategy']} | {st['promoted']}"
        )
    L += ["", f"Promoted: {res['promoted']}", ""]
    for vid, e in res["confirm"].items():
        L.append(f"Confirm 2025 {vid}: confirmed={e.get('confirmed')} half diffs={e.get('half_diffs')}")
        for slip, st in e["by_slippage"].items():
            if "gross" in st:
                g, n = st["gross"], st["net"]
                L.append(
                    f"  slippage {slip}%: {st['trades']} trades, gross {g['strategy']} vs ctl {g['control']}"
                    f" diff {g['diff']} [{g['lo']}, {g['hi']}], net {n['strategy']} vs {n['control']}"
                )
    L += ["", f"Counts: {json.dumps(res['counts'], sort_keys=True)}"]
    return "\n".join(L)


if __name__ == "__main__":
    raise SystemExit(main())
