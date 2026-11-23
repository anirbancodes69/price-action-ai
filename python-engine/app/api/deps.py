"""Shared API dependencies: ruleset resolution."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException

from app.domain.params import RulesetParams
from app.rulesets import ROLE_LIVE, load_ruleset, ruleset_role
from app.settings import Settings, get_settings


@lru_cache
def _load(code: str, version: str) -> RulesetParams:
    return load_ruleset(code, version)


def ruleset_for(settings: Settings, version: str | None = None) -> RulesetParams:
    """The active ruleset code at `version` (default: the active version). Unknown versions are a 422."""
    code, active_version = settings.active_ruleset.split("@")
    chosen = version or active_version
    # Only LIVE rulesets serve the API (scanner, analysis, positions, risk). Research and retired rulesets
    # are for the backtest tooling; selecting one here would present research behaviour as live.
    if ruleset_role(code, chosen) not in (ROLE_LIVE, None):
        raise HTTPException(422, detail="RULESET_NOT_LIVE")
    try:
        return _load(code, chosen)
    except FileNotFoundError:
        raise HTTPException(422, detail="UNKNOWN_RULESET_VERSION") from None


def get_active_params(settings: Annotated[Settings, Depends(get_settings)]) -> RulesetParams:
    return ruleset_for(settings)
