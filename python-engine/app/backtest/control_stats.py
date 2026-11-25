"""Statistics for the matched-control comparison, validation plan §4.3 and §4.6 infrastructure (E6).

Pure functions on lists of per-trade R values. They run nothing on real data and choose no threshold: the
numbers
(K = 1,000 replicates, 10,000 resamples, seed 1, 99%, 0.005R) are the plan's and are passed in by the caller.

Percentile rule (nearest rank, documented): for `N` sorted values and probability `q`, the value at 1-based
rank
`ceil(q N)`, so the 0.5th and 99.5th percentiles of 10,000 resamples are ranks 50 and 9,950.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class MonthTotals:
    """Per calendar month: the sum and the count of R over the months' trades. For the control, `r_sum` and
    `n`
    are the means over the K replicates of the month's total R and trade count."""

    r_sum: float
    n: float


def month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def totals_by_month(trades: Sequence[tuple[date, float]]) -> dict[str, MonthTotals]:
    sums: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    for d, r in trades:
        sums[month_key(d)] += r
        counts[month_key(d)] += 1
    return {m: MonthTotals(sums[m], float(counts[m])) for m in sorted(sums)}


def average_replicates(replicates: Sequence[Mapping[str, MonthTotals]]) -> dict[str, MonthTotals]:
    """Mean over replicates of each month's total R and trade count (a month absent from a replicate counts
    0)."""
    k = len(replicates)
    months = sorted({m for r in replicates for m in r})
    return {
        m: MonthTotals(
            sum(r[m].r_sum for r in replicates if m in r) / k, sum(r[m].n for r in replicates if m in r) / k
        )
        for m in months
    }


def mean_r(totals: Mapping[str, MonthTotals], months: Sequence[str] | None = None) -> float | None:
    ms = list(totals) if months is None else list(months)
    n = sum(totals[m].n for m in ms if m in totals)
    return sum(totals[m].r_sum for m in ms if m in totals) / n if n else None


def edge(
    orb: Mapping[str, MonthTotals], control: Mapping[str, MonthTotals], months: Sequence[str] | None = None
) -> float | None:
    """`Δ = X_ORB - X_control` over the same months (control already averaged over replicates)."""
    a, b = mean_r(orb, months), mean_r(control, months)
    return None if a is None or b is None else a - b


def percentile(sorted_values: Sequence[float], q: float) -> float:
    n = len(sorted_values)
    if n == 0:
        raise ValueError("no values")
    return sorted_values[max(0, min(n - 1, math.ceil(q * n) - 1))]


@dataclass(frozen=True, slots=True)
class BootstrapResult:
    delta: float
    low: float
    high: float
    resamples: int
    level: float
    months: int
    undefined_resamples: int


def month_block_bootstrap(
    orb: Mapping[str, MonthTotals],
    control: Mapping[str, MonthTotals],
    *,
    resamples: int,
    seed: int,
    level: float,
) -> BootstrapResult:
    """Resample calendar months with replacement; recompute `Δ` over the drawn months' ORB and control
    totals."""
    months = sorted(set(orb) & set(control))
    if not months:
        raise ValueError("no common months")
    point = edge(orb, control, months)
    if point is None:
        raise ValueError("edge undefined")
    rng = random.Random(seed)  # noqa: S311 (reproducible bootstrap, not security)
    deltas: list[float] = []
    undefined = 0
    for _ in range(resamples):
        drawn = [months[rng.randrange(len(months))] for _ in months]
        so = sum(orb[m].r_sum for m in drawn)
        no = sum(orb[m].n for m in drawn)
        sc = sum(control[m].r_sum for m in drawn)
        nc = sum(control[m].n for m in drawn)
        if no == 0 or nc == 0:
            undefined += 1
            continue
        deltas.append(so / no - sc / nc)
    deltas.sort()
    if not deltas:
        raise ValueError("every resample undefined")
    tail = (1 - level) / 2
    return BootstrapResult(
        point,
        percentile(deltas, tail),
        percentile(deltas, 1 - tail),
        resamples,
        level,
        len(months),
        undefined,
    )


def control_sampling_error(replicate_edges: Sequence[float]) -> tuple[float, float]:
    """Spread of `X_ORB - X_c(r)` across replicates and the Monte Carlo standard error of their mean."""
    k = len(replicate_edges)
    if k < 2:
        raise ValueError("need at least two replicates")
    m = sum(replicate_edges) / k
    sd = math.sqrt(sum((x - m) ** 2 for x in replicate_edges) / (k - 1))
    return sd, sd / math.sqrt(k)


def supplementary_p(x_orb: float, control_means: Sequence[float]) -> float:
    """`p = (1 + #{r: X_c(r) >= X_ORB}) / (K + 1)`; supplementary only, never a decision input."""
    return (1 + sum(1 for x in control_means if x >= x_orb)) / (len(control_means) + 1)


def chronological_thirds(sessions: Sequence[date]) -> list[list[date]]:
    """Three parts of equal session count (the remainder goes to the earlier parts)."""
    ordered = sorted(set(sessions))
    n = len(ordered)
    base, extra = divmod(n, 3)
    parts, i = [], 0
    for k in range(3):
        size = base + (1 if k < extra else 0)
        parts.append(ordered[i : i + size])
        i += size
    return parts


def stability(
    orb_trades: Sequence[tuple[date, float]],
    control_trades_by_replicate: Sequence[Sequence[tuple[date, float]]],
    sessions: Sequence[date],
    min_trades: int = 30,
) -> list[dict[str, object]]:
    """`Δ` in each chronological third; a part with fewer than `min_trades` ORB trades is shown, not
    interpreted."""
    out: list[dict[str, object]] = []
    for k, part in enumerate(chronological_thirds(sessions), start=1):
        days = set(part)
        o = [(d, r) for d, r in orb_trades if d in days]
        reps = [totals_by_month([(d, r) for d, r in rep if d in days]) for rep in control_trades_by_replicate]
        d_ = edge(totals_by_month(o), average_replicates(reps)) if o and reps else None
        out.append({"part": k, "orb_trades": len(o), "delta": d_, "interpretable": len(o) >= min_trades})
    return out


# ------------------------------------------------------------------ calibration harness (plan §4.6, not run)


@dataclass(frozen=True, slots=True)
class Calibration:
    simulations: int
    coverage: float  # share of intervals that contain the true delta
    false_positive: float  # share of null simulations whose interval excludes zero


def interval_calibration(
    simulate: Callable[[random.Random, float], object],
    interval: Callable[[object], tuple[float, float]],
    *,
    true_delta: float,
    simulations: int,
    seed: int,
) -> Calibration:
    """Coverage of an interval method on a simulated generator: `simulate(rng, delta)` returns a data set,
    `interval(data)` its (low, high). Coverage uses `true_delta`; the false-positive rate uses delta = 0. The
    generator and the pass thresholds are chosen by the owner's calibration protocol, not here."""
    rng = random.Random(seed)  # noqa: S311 (reproducible simulation, not security)
    hit = fp = 0
    for _ in range(simulations):
        lo, hi = interval(simulate(rng, true_delta))
        hit += lo <= true_delta <= hi
        lo0, hi0 = interval(simulate(rng, 0.0))
        fp += not (lo0 <= 0.0 <= hi0)
    return Calibration(simulations, hit / simulations, fp / simulations)
