"""Shared synthetic-test seam for the B0 contract (`app.backtest.b0_contract`).

Most B0 unit tests use small snapshot minimums on hand-built bars, so their ruleset is a *modified copy* of
0.6.0 and its content hash is not the released one. `small_b0_hash` pins the contract to that copy for the one
test that asks for it; the real constant is untouched everywhere else, and the strict-runner and exclusivity
tests deliberately do not use it.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from app.backtest import b0_contract
from app.rulesets import load_ruleset


def small_b0_params():  # type: ignore[no-untyped-def]
    p = load_ruleset("pa-intraday", "0.6.0")
    return replace(p, values={**p.values, "analysis.min_bars_5m": 5, "analysis.min_bars_15m": 5})


@pytest.fixture
def small_b0_hash(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(b0_contract, "B0_RULESET_HASH", small_b0_params().content_hash)
