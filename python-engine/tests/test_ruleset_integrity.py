"""Phase 1 P2/P3: ruleset roles, comparison and configuration integrity (docs/trading/ruleset-comparison.md)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.api.deps import ruleset_for
from app.rulesets import (
    ROLE_LIVE,
    RULESET_ROLES,
    available_rulesets,
    diff_rulesets,
    load_ruleset,
)
from app.settings import Settings

APP = Path(__file__).resolve().parent.parent / "app"
SOURCE = "\n".join(p.read_text() for p in APP.rglob("*.py"))

# Keys in `pa-intraday` with no effect today. Each verdict is in docs/trading/configuration-inventory.md.
# If one is wired up, remove it here: `test_dormant_keys_are_really_unread` fails until you do.
DORMANT_KEYS = {
    "score.min_display",  # display floor of 0 = show all; no consumer, TRD-04 §9 obsolete in the intraday design
    "setup.rejection_min_wick_ratio",  # the rejection setup does not exist in the intraday design
    "zone.max_width_pct",  # TRD-03 §3 describes a guard on malformed parameter sets that was never written
}
# Keys read through a built key (f"pivot.left_bars_{tf}") rather than a literal.
DYNAMIC_PREFIXES = ("pivot.left_bars_", "pivot.right_bars_", "structure.break_buffer_pct_")


def _read(key: str) -> bool:
    return f'"{key}"' in SOURCE or any(key.startswith(p) and p in SOURCE for p in DYNAMIC_PREFIXES)


def test_every_ruleset_on_disk_has_an_explicit_role() -> None:
    assert set(available_rulesets()) == set(RULESET_ROLES)


def test_exactly_one_pa_intraday_version_is_live_and_it_is_the_default() -> None:
    live = [k for k, r in RULESET_ROLES.items() if r == ROLE_LIVE]
    assert live == [("pa-intraday", "0.1.0")]
    assert Settings().active_ruleset == "pa-intraday@0.1.0"


def test_documented_differences_between_pa_intraday_versions_are_exactly_these() -> None:
    base = load_ruleset("pa-intraday", "0.1.0")
    a = "<absent>"
    assert diff_rulesets(base, load_ruleset("pa-intraday", "0.2.0")) == {
        "setup.liquidity_sweep_enabled": (a, True)
    }
    assert diff_rulesets(load_ruleset("pa-intraday", "0.2.0"), load_ruleset("pa-intraday", "0.3.0")) == {
        "exit.structure_exit_enabled": (True, False)
    }
    assert diff_rulesets(load_ruleset("pa-intraday", "0.3.0"), load_ruleset("pa-intraday", "0.4.0")) == {
        "setup.failed_breakout_enabled": (a, True),
        "setup.failed_break_max_bars": (a, 6),
    }


def test_content_hash_identifies_a_configuration() -> None:
    v1, v2 = load_ruleset("pa-intraday", "0.1.0"), load_ruleset("pa-intraday", "0.2.0")
    assert v1.content_hash == load_ruleset("pa-intraday", "0.1.0").content_hash
    assert v1.content_hash != v2.content_hash


@pytest.mark.parametrize("version", ["0.2.0", "0.3.0", "0.4.0", "0.5.0"])
def test_the_api_refuses_research_rulesets_as_active_or_requested(version: str) -> None:
    with pytest.raises(HTTPException) as e:
        ruleset_for(Settings(), version)
    assert (e.value.status_code, e.value.detail) == (422, "RULESET_NOT_LIVE")
    with pytest.raises(HTTPException) as e2:
        ruleset_for(Settings(active_ruleset=f"pa-intraday@{version}"))
    assert e2.value.detail == "RULESET_NOT_LIVE"


def test_the_api_serves_the_live_ruleset_and_rejects_unknown_versions() -> None:
    assert ruleset_for(Settings()).version == "0.1.0"
    with pytest.raises(HTTPException) as e:
        ruleset_for(Settings(), "9.9.9")
    assert e.value.detail == "UNKNOWN_RULESET_VERSION"


@pytest.mark.parametrize("version", ["0.1.0", "0.2.0", "0.3.0", "0.4.0", "0.5.0"])
def test_every_key_is_read_by_code_or_declared_dormant(version: str) -> None:
    unread = {k for k in load_ruleset("pa-intraday", version).values if not _read(k)}
    assert unread == DORMANT_KEYS & set(load_ruleset("pa-intraday", version).values)


def test_dormant_keys_are_really_unread() -> None:
    for k in DORMANT_KEYS:
        assert not re.search(re.escape(f'"{k}"'), SOURCE), f"{k} is now read: remove it from DORMANT_KEYS"


def test_zone_width_parameters_are_consistent() -> None:
    """The unimplemented `zone.max_width_pct` guard (TRD-03 §3), asserted where the key exists (0.5.0 retired it)."""
    for code, version in available_rulesets():
        if code != "pa-intraday":
            continue
        p = load_ruleset(code, version)
        if "zone.max_width_pct" not in p.values:
            continue
        assert p.decimal("zone.min_width_pct") <= p.decimal("zone.max_width_pct")
        assert p.decimal("zone.cluster_tolerance_pct") <= p.decimal("zone.max_width_pct")


def test_the_live_ruleset_matches_the_risk_planning_values() -> None:
    """P6: the configured defaults equal the approved planning values (CLAUDE.md §1, TRD-05)."""
    p = load_ruleset("pa-intraday", "0.1.0")
    assert p.decimal("risk.default_risk_per_trade_pct") == 0.5
    assert p.decimal("risk.default_max_position_value") == 50000
    assert p.decimal("risk.min_rr") == 2


def test_0_5_0_is_0_1_0_without_exactly_the_three_retired_keys_and_is_research() -> None:
    """DEC-024 D-2. Released rulesets are untouched; 0.5.0 is never live without a separate approval and ADR."""
    base, new = load_ruleset("pa-intraday", "0.1.0"), load_ruleset("pa-intraday", "0.5.0")
    assert diff_rulesets(base, new) == {k: (base.values[k], "<absent>") for k in sorted(DORMANT_KEYS)}
    assert RULESET_ROLES[("pa-intraday", "0.5.0")] == "RESEARCH"
    assert not {k for k in new.values if not _read(k)}  # no key without a reader remains


def test_released_rulesets_are_byte_identical_to_their_seeder_copies_and_unmodified() -> None:
    root = Path(__file__).resolve().parents[2] / "backend/database/seeders/data"
    if not root.exists():
        pytest.skip("backend seeder data is outside this checkout")
    for (code, version), path in available_rulesets().items():
        copy = root / f"{code}-{version}.json"
        assert copy.exists() and copy.read_bytes() == path.read_bytes(), (code, version)


# Tripwire (DEC-024): a released ruleset is never edited. A change here means a released file was modified;
# create a new version instead.
RELEASED_HASHES = {
    ("pa-core", "0.1.0"): "6807859f97e9b52b7b3cc02312efacccc4b03660fe2c6cea498379667ff66deb",
    ("pa-intraday", "0.1.0"): "bef6a910bc16d31811baffc70a6dc4e39591379911c461151072e2a1c6189b17",
    ("pa-intraday", "0.2.0"): "95caba3275e3dcdc81230b904f73e2ea723084d2901974b9984a144f2f13752a",
    ("pa-intraday", "0.3.0"): "2665c96a7d0dcac4187b47cf085a85208873e61349191c7300db497a4ed7354a",
    ("pa-intraday", "0.4.0"): "2cf26f81c1ba573e03472517c6a5c0f8376675908d112250883bd626fdbe6f0c",
    ("pa-intraday", "0.5.0"): "31b11969017c0a831d4c64eb8c0f39555bd3838cb3da79d7fed1e0d9e342e581",
}


def test_released_rulesets_have_not_been_modified() -> None:
    assert {k: load_ruleset(*k).content_hash for k in available_rulesets()} == RELEASED_HASHES


def test_0_5_0_gives_the_same_analysis_as_0_1_0_on_the_same_bars() -> None:
    """Compatibility check for retiring the dormant keys: identical outputs, only the ruleset version differs."""
    import math
    from dataclasses import replace
    from datetime import UTC, datetime, timedelta
    from decimal import Decimal as D

    from app.domain.analyse import analyse
    from app.domain.session import DailyLevels
    from app.domain.snapshot import SnapshotStatus
    from app.domain.types import Bar

    sessions, per = 6, 75
    t0 = datetime(2026, 11, 9, 3, 45, tzinfo=UTC)
    b5: list[Bar] = []
    for d in range(sessions):
        for i in range(per):
            s = t0 + timedelta(days=d, minutes=5 * i)
            c = 1000 + 12 * math.sin((d * per + i) / 7) + 0.05 * (d * per + i) % 3
            o = c - 0.4
            b5.append(Bar(s, s + timedelta(minutes=5), D(str(round(o, 2))), D(str(round(c + 0.8, 2))),
                          D(str(round(c - 0.9, 2))), D(str(round(c, 2)))))  # fmt: skip
    b15: list[Bar] = []
    for k in range(0, len(b5) - 2, 3):
        g = b5[k : k + 3]
        if g[0].start.date() == g[-1].start.date():
            b15.append(
                Bar(
                    g[0].start,
                    g[-1].end,
                    g[0].open,
                    max(x.high for x in g),
                    min(x.low for x in g),
                    g[-1].close,
                )
            )
    session_open = b5[-per].start
    out = []
    for v in ("0.1.0", "0.5.0"):
        p = load_ruleset("pa-intraday", v)
        p = replace(p, values={**p.values, "analysis.min_bars_5m": 100, "analysis.min_bars_15m": 40})
        out.append(analyse(b5, b15, session_open, DailyLevels(D("1010"), D("990"), D("1000")), p,
                           session_close=session_open + timedelta(hours=6, minutes=15)))  # fmt: skip
    a, b = out
    assert a.check.status is SnapshotStatus.VALID, a.check
    assert replace(a, ruleset_version="x") == replace(b, ruleset_version="x")
    assert a.setups is not None
