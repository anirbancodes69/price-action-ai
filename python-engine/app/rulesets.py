"""Loads ruleset JSON files into `RulesetParams` (I/O lives outside `app/domain`)."""

from __future__ import annotations

import json
from pathlib import Path

from app.domain.params import RulesetParams

RULESETS_DIR = Path(__file__).resolve().parent.parent / "rulesets"


def load_ruleset(code: str, version: str, root: Path = RULESETS_DIR) -> RulesetParams:
    values = json.loads((root / code / f"{version}.json").read_text(encoding="utf-8"))
    return RulesetParams(code=code, version=version, values=values)
