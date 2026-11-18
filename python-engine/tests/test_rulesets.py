"""Ruleset loader and RulesetParams (ENG-04 §5, PE-06)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.params import RulesetParams
from app.rulesets import load_ruleset


def test_load_active_ruleset_and_accessors() -> None:
    p = load_ruleset("pa-intraday", "0.1.0")
    assert (p.code, p.version) == ("pa-intraday", "0.1.0")
    assert (p.pivot_left("5m"), p.pivot_right("15m")) == (2, 2)
    assert p.break_buffer("5m") == Decimal("0.0005")  # 0.05 % as an exact fraction
    assert p.equal_tolerance() == Decimal("0.001")
    assert p.int_("analysis.min_bars_5m") == 150


def test_missing_and_non_integer_parameters_fail_loudly() -> None:
    p = RulesetParams("x", "1", {"a": 1.5, "b": True})
    with pytest.raises(KeyError, match="nope"):
        p.get("nope")
    with pytest.raises(TypeError):
        p.int_("a")
    with pytest.raises(TypeError):
        p.int_("b")
