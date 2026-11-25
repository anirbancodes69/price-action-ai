"""The authoritative-run contract of the original ORB B0 (DEC-045 / DR-12 follow-up): one execution path.

Original B0 is `orb_b0` on `pa-intraday 0.6.0`. A run of either is only valid if it carries, in its run
record,
the evidence of the strict runner (`scripts/run_orb_b0.py`): the released ruleset hash, the SHA-256 and the
approval status of every reference table, the resolver version and a consistent approval basis (with the exact
solo label when a table is owner-approved). The check lives in `BacktestConfig.__post_init__`, the one place
every replay path builds its configuration, so a legacy script, a chunked run, a merge or a direct library
call
cannot produce a B0 run record without it. The strategy id `orb_b0` and the ruleset `0.6.0` are reserved for
this contract: `0.6.0` with any other strategy is refused as well, so a legacy result can never be mistaken
for a B0 result. Pure functions; no I/O.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass

from app.backtest.approval import ApprovalError, RunApproval, validate_run_approval
from app.domain.params import RulesetParams
from app.rulesets import ROLE_RESEARCH, ruleset_role

B0_STRATEGY = "orb_b0"
B0_RULESET = ("pa-intraday", "0.6.0")
B0_RULESET_HASH = "aaa4ab079aa1da614c26be3dde958598e514106dba42bbd07405d88f538fc426"
STRICT_RUNNER = "scripts/run_orb_b0.py"
TABLES = ("tick", "event", "session", "price_basis")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class B0ContractError(ValueError):
    """A B0 run or record does not satisfy the strict-runner contract."""


def refusal_message(what: str) -> str:
    return (
        f"{what} is reserved for the strict original-B0 runner: use {STRICT_RUNNER} "
        "(hash-pinned, approval-gated, evidence-labelled). Legacy runners do not produce B0 results."
    )


def legacy_refusal(strategy_id: str | None, ruleset: str | None) -> str | None:
    """For command-line entry points: a message if the request names `orb_b0` or ruleset
    `pa-intraday@0.6.0`."""
    if strategy_id == B0_STRATEGY:
        return refusal_message(f"strategy {B0_STRATEGY!r}")
    if ruleset is not None and tuple(ruleset.split("@", 1)) == B0_RULESET:
        return refusal_message("ruleset pa-intraday@0.6.0")
    return None


def is_b0_related(params: RulesetParams, strategy_id: str | None) -> bool:
    return strategy_id == B0_STRATEGY or (params.code, params.version) == B0_RULESET


def validate_b0_reference_data(rd: Mapping[str, str]) -> RunApproval:
    """The evidence of the strict runner: table hashes, resolver version, per-table statuses, a consistent
    approval basis and result label. Raises `B0ContractError`; returns the validated approval."""
    for k in TABLES:
        h = rd.get(f"{k}_table_sha256" if k != "price_basis" else "price_basis_sha256", "")
        if not _HEX64.match(h):
            raise B0ContractError(f"reference data lacks a SHA-256 for the {k} table")
    if not rd.get("tick_resolver_version"):
        raise B0ContractError("reference data lacks the tick resolver version")
    status = {k: rd.get(f"{k}_review_status", "") for k in TABLES}
    refs = tuple(x for x in (rd.get("approval_decision_refs") or "").split(",") if x)
    try:
        ra = RunApproval(rd.get("approval_basis", ""), rd.get("result_label") or None, refs, status)
        validate_run_approval(ra)
    except ApprovalError as e:
        raise B0ContractError(f"approval metadata invalid: {e}") from e
    return ra


def _context_digest(strategy_id: str, ruleset_hash: str, items: tuple[tuple[str, str], ...]) -> str:
    return hashlib.sha256(json.dumps([strategy_id, ruleset_hash, items], sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class B0ExecutionContext:
    """The validated, immutable evidence a B0 configuration needs, bound to the ruleset hash and the strategy.

    Production code creates it in one place, `b0_run.build_reference`, through `issue_context` after the
    tables were loaded and approved (a repository test fails if any other module under `app/` or `scripts/`
    issues one). A copy edited afterwards, or a context paired with other reference data or another
    ruleset, fails its digest or binding check. This is a consistency and accident guard, not protection
    against code that forges a context in a local Python process: no secret is involved, none is claimed.
    """

    strategy_id: str
    ruleset_hash: str
    reference_data: tuple[tuple[str, str], ...]
    digest: str

    def __post_init__(self) -> None:
        if self.digest != _context_digest(self.strategy_id, self.ruleset_hash, self.reference_data):
            raise B0ContractError("execution context digest does not match its contents")


def issue_context(params: RulesetParams, reference_data: Mapping[str, str]) -> B0ExecutionContext:
    """Validate the full contract and freeze it into a context. Only `b0_run` calls this in production."""
    validate_b0_config(params, B0_STRATEGY, reference_data, None, _issuing=True)
    items = tuple(sorted((str(k), str(v)) for k, v in reference_data.items()))
    digest = _context_digest(B0_STRATEGY, params.content_hash, items)
    return B0ExecutionContext(B0_STRATEGY, params.content_hash, items, digest)


def validate_b0_config(
    params: RulesetParams,
    strategy_id: str | None,
    reference_data: Mapping[str, str],
    context: B0ExecutionContext | None = None,
    *,
    _issuing: bool = False,
) -> None:
    """No-op for anything unrelated to B0 (non-B0 backtests are unchanged). Otherwise the full contract."""
    if not is_b0_related(params, strategy_id):
        return
    if strategy_id != B0_STRATEGY:
        raise B0ContractError(refusal_message(f"ruleset pa-intraday 0.6.0 (strategy {strategy_id!r})"))
    if (params.code, params.version) != B0_RULESET:
        raise B0ContractError(refusal_message(f"strategy orb_b0 on ruleset {params.code} {params.version}"))
    if ruleset_role(params.code, params.version) != ROLE_RESEARCH:
        raise B0ContractError("the B0 ruleset must have the RESEARCH role")
    if params.content_hash != B0_RULESET_HASH:
        raise B0ContractError("ruleset content hash differs from the released pa-intraday 0.6.0")
    validate_b0_reference_data(reference_data)
    if _issuing:
        return
    if context is None:
        raise B0ContractError(refusal_message("a B0 run without an execution context"))
    if (context.strategy_id, context.ruleset_hash) != (B0_STRATEGY, params.content_hash):
        raise B0ContractError("execution context belongs to another strategy or ruleset")
    if dict(context.reference_data) != {str(k): str(v) for k, v in reference_data.items()}:
        raise B0ContractError("execution context belongs to different reference data")
