"""Session bootstrap used by every diagnosis test (plan §4 'Statistics').

Whole sessions are resampled, so the trades of one day stay together. Defaults: 10,000 resamples, seed 1.
A difference is material when its 95% CI excludes zero and it is at least `min_effect`.
"""

from __future__ import annotations

import random
from collections.abc import Hashable, Mapping
from dataclasses import dataclass

Sums = Mapping[Hashable, tuple[float, int]]  # session -> (sum of values, count)


@dataclass(frozen=True, slots=True)
class Interval:
    estimate: float
    low: float
    high: float
    n: int  # observations behind the estimate

    def excludes_zero(self) -> bool:
        return self.low > 0 or self.high < 0

    def material(self, min_effect: float) -> bool:
        return self.excludes_zero() and abs(self.estimate) >= min_effect


def add(sums: dict[Hashable, tuple[float, int]], key: Hashable, value: float) -> None:
    s, n = sums.get(key, (0.0, 0))
    sums[key] = (s + value, n + 1)


def _mean(s: float, n: int) -> float:
    return s / n if n else 0.0


def bootstrap_mean(a: Sums, b: Sums | None = None, *, resamples: int = 10_000, seed: int = 1) -> Interval:
    """Mean of `a` (per observation), or the mean of `a` minus the mean of `b`, with a 95% session CI."""
    keys = sorted(set(a) | set(b or {}), key=str)
    m = len(keys)
    sa = [a.get(k, (0.0, 0))[0] for k in keys]
    na = [a.get(k, (0.0, 0))[1] for k in keys]
    sb = [(b or {}).get(k, (0.0, 0))[0] for k in keys]
    nb = [(b or {}).get(k, (0.0, 0))[1] for k in keys]
    n_obs = sum(na)
    est = _mean(sum(sa), sum(na)) - (_mean(sum(sb), sum(nb)) if b is not None else 0.0)
    if m == 0:
        return Interval(est, 0.0, 0.0, n_obs)
    rng = random.Random(seed)  # noqa: S311 - research resampling, not security
    draws: list[float] = []
    for _ in range(resamples):
        idx = rng.choices(range(m), k=m)
        d = _mean(sum(sa[i] for i in idx), sum(na[i] for i in idx))
        if b is not None:
            d -= _mean(sum(sb[i] for i in idx), sum(nb[i] for i in idx))
        draws.append(d)
    draws.sort()
    return Interval(est, draws[int(0.025 * (resamples - 1))], draws[int(0.975 * (resamples - 1))], n_obs)
