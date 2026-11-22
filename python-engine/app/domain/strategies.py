"""Strategy registry for the independent strategy library (ADR-018, process §2.1).

A strategy is identified by its id and runs only its own detector in the single-strategy run mode. Strategies
are added here one at a time, after their specification is approved.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.domain.analyse import Detector
from app.domain.setups.failed_breakdown import detect_failed_breakdown
from app.domain.setups.liquidity_sweep import detect_liquidity_sweep

STRATEGY_DETECTORS: dict[str, Sequence[Detector]] = {
    "liquidity_sweep_reversal": (detect_liquidity_sweep,),
    "failed_breakout": (detect_failed_breakdown,),
}


def strategy_detectors(strategy_id: str) -> Sequence[Detector]:
    try:
        return STRATEGY_DETECTORS[strategy_id]
    except KeyError:
        raise ValueError(f"unknown strategy {strategy_id!r}; known: {sorted(STRATEGY_DETECTORS)}") from None
