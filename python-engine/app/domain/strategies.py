"""Strategy registry for the independent strategy library (ADR-018, process §2.1).

A strategy is identified by its id and runs only its own detector in the single-strategy run mode. Strategies
are added here one at a time, after their specification is approved.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.domain.analyse import Detector
from app.domain.setups.failed_breakdown import detect_failed_breakdown
from app.domain.setups.liquidity_sweep import detect_liquidity_sweep
from app.domain.setups.opening_range import detect_opening_range
from app.domain.setups.orb_b0 import detect_orb_b0

STRATEGY_DETECTORS: dict[str, Sequence[Detector]] = {
    "liquidity_sweep_reversal": (detect_liquidity_sweep,),
    "failed_breakout": (detect_failed_breakdown,),
    # E1 (OD-8 step 1): today's opening-range detector, unchanged, so the isolation proof (P0-3) can run.
    # It is NOT the frozen B0 path (E4) and must not be described as B0: it keeps the 15m context filter,
    # the width band and the short mirror (ORB specification §17.1).
    "opening_range_breakout": (detect_opening_range,),
    # E4 (OD-8 step 2): the frozen B0 reference only, long only; needs ruleset pa-intraday 0.6.0.
    "orb_b0": (detect_orb_b0,),
}


def strategy_detectors(strategy_id: str) -> Sequence[Detector]:
    try:
        return STRATEGY_DETECTORS[strategy_id]
    except KeyError:
        raise ValueError(f"unknown strategy {strategy_id!r}; known: {sorted(STRATEGY_DETECTORS)}") from None
