"""Shared API dependencies: ruleset resolution."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException

from app.domain.params import RulesetParams
from app.rulesets import load_ruleset
from app.settings import Settings, get_settings


@lru_cache
def _load(code: str, version: str) -> RulesetParams:
    return load_ruleset(code, version)


def ruleset_for(settings: Settings, version: str | None = None) -> RulesetParams:
    """The active ruleset code at `version` (default: the active version). Unknown versions are a 422."""
    code, active_version = settings.active_ruleset.split("@")
    try:
        return _load(code, version or active_version)
    except FileNotFoundError:
        raise HTTPException(422, detail="UNKNOWN_RULESET_VERSION") from None


def get_active_params(settings: Annotated[Settings, Depends(get_settings)]) -> RulesetParams:
    return ruleset_for(settings)
