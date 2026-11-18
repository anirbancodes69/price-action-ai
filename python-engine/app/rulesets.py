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
