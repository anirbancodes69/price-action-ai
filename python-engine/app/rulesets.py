"""Loads ruleset JSON files into `RulesetParams` (I/O lives outside `app/domain`)."""

from __future__ import annotations

import json
from pathlib import Path

from app.domain.params import RulesetParams

RULESETS_DIR = Path(__file__).resolve().parent.parent / "rulesets"


def available_rulesets(root: Path = RULESETS_DIR) -> dict[tuple[str, str], Path]:
    """Every `<root>/<code>/<version>.json` on disk, keyed by `(code, version)`."""
    return {(p.parent.name, p.stem): p for p in sorted(root.glob("*/*.json"))}


def load_ruleset(code: str, version: str, root: Path = RULESETS_DIR) -> RulesetParams:
    """Load a ruleset by looking `(code, version)` up in the files that exist.

    `code` and `version` can come from a request or a setting. They are used only as a lookup key into the
    listing of the rulesets directory, never to build a path, so a malformed or hostile value is simply
    unknown (`FileNotFoundError`; the API turns that into 422).
    """
    path = available_rulesets(root).get((code, version))
    if path is None:
        raise FileNotFoundError(f"unknown ruleset {code!r} {version!r}")
    values = json.loads(path.read_text(encoding="utf-8"))
    return RulesetParams(code=code, version=version, values=values)


# Explicit role of every ruleset on disk (docs/trading/ruleset-comparison.md). A new ruleset file must be
# given a role here (tests enforce it) so no version can become the live one by accident.
#   LIVE      may be the engine's `ACTIVE_RULESET` and requested by an API caller
#   RESEARCH  backtests and research scripts only; refused by the API
#   RETIRED   kept for history; refused everywhere except explicit research loads
ROLE_LIVE, ROLE_RESEARCH, ROLE_RETIRED = "LIVE", "RESEARCH", "RETIRED"
RULESET_ROLES: dict[tuple[str, str], str] = {
    ("pa-core", "0.1.0"): ROLE_RETIRED,
    ("pa-intraday", "0.1.0"): ROLE_LIVE,
    ("pa-intraday", "0.2.0"): ROLE_RESEARCH,
    ("pa-intraday", "0.3.0"): ROLE_RESEARCH,
    ("pa-intraday", "0.4.0"): ROLE_RESEARCH,
    # 0.1.0 minus three dormant keys (DEC-024 D-2). Not live: promotion needs evidence and an ADR.
    ("pa-intraday", "0.5.0"): ROLE_RESEARCH,
    # 0.5.0 plus the ORB B0 reference configuration (OD-8 Step 2, D7). Research only.
    ("pa-intraday", "0.6.0"): ROLE_RESEARCH,
}


def ruleset_role(code: str, version: str) -> str | None:
    return RULESET_ROLES.get((code, version))


def diff_rulesets(a: RulesetParams, b: RulesetParams) -> dict[str, tuple[object, object]]:
    """Every key whose value differs between two rulesets, as `{key: (value in a, value in b)}`.

    A key present in only one side is reported with the string `"<absent>"` on the other.
    """
    absent = "<absent>"
    keys = sorted(set(a.values) | set(b.values))
    return {
        k: (a.values.get(k, absent), b.values.get(k, absent))
        for k in keys
        if a.values.get(k, absent) != b.values.get(k, absent)
    }
