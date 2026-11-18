"""Loads ruleset JSON files into `RulesetParams` (I/O lives outside `app/domain`)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from app.domain.params import RulesetParams

RULESETS_DIR = Path(__file__).resolve().parent.parent / "rulesets"
_CODE = re.compile(r"^[a-z][a-z0-9-]{0,31}$")
_VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


def load_ruleset(code: str, version: str, root: Path = RULESETS_DIR) -> RulesetParams:
    """Load `<root>/<code>/<version>.json`.

    `code` and `version` can come from a request or a setting, so they are validated here instead of being
    trusted: a malformed one is a `FileNotFoundError` (the API turns that into 422), never a path outside
    `root`.
    """
    if not _CODE.fullmatch(code) or not _VERSION.fullmatch(version):
        raise FileNotFoundError(f"unknown ruleset {code!r} {version!r}")
    base = root.resolve()
    path = (base / code / f"{version}.json").resolve()
    if not path.is_relative_to(base):  # defence in depth; the patterns above already exclude separators
        raise FileNotFoundError(f"unknown ruleset {code!r} {version!r}")
    values = json.loads(path.read_text(encoding="utf-8"))
    return RulesetParams(code=code, version=version, values=values)
