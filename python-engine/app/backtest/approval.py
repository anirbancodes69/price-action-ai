"""Approval basis of curated reference data and the research-result label (DEC-045 / DR-12).

Two statuses, never merged and never converted into one another:

- `INDEPENDENTLY_REVIEWED`: an actual independent human review took place and is evidenced elsewhere. This
  module cannot establish that; it only keeps the status distinct and refuses to infer it.
- `OWNER_APPROVED_SOLO_RESEARCH`: owner approval under the solo-research exception DEC-045 / DR-12.
Independent
  human review has **not** occurred. It is a governance approval basis, not a data-quality certification:
  every
  hash, schema, provenance, coverage and conflict check still applies in full.

Anything else (missing, unknown, `UNREVIEWED`, "AI reviewed", malformed) is refused. A solo-approved table
also
needs an explicit opt-in by the caller, a decision reference, and owner-approval evidence; there is no
mechanism
that approves a table merely because the exception exists. Pure functions, no I/O.

Run rule for a mix of statuses (deterministic and conservative): the weakest basis governs. If every table is
`INDEPENDENTLY_REVIEWED` the run basis is `INDEPENDENTLY_REVIEWED` and it carries no solo label; if any
table is
`OWNER_APPROVED_SOLO_RESEARCH` the whole run basis is `OWNER_APPROVED_SOLO_RESEARCH` and the result must carry
`SOLO_RESULT_LABEL`. Each table's own status is kept unchanged in the record (nothing is upgraded or
downgraded).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any

INDEPENDENT = "INDEPENDENTLY_REVIEWED"
SOLO = "OWNER_APPROVED_SOLO_RESEARCH"
SOLO_DECISION_REFS = frozenset({"DEC-045", "DR-12"})
SOLO_RESULT_LABEL = "EXPLORATORY — SOLO RESEARCH — NOT INDEPENDENTLY VALIDATED"
# Metadata that would claim an independent review; refused on a solo-approved table.
INDEPENDENT_CLAIM_KEYS = frozenset(
    {
        "independent_review",
        "independently_reviewed",
        "independent_reviewer",
        "reviewer",
        "reviewed_by",
        "review_date",
    }
)
SOLO_ONLY_KEYS = frozenset({"decision_ref", "owner_approval"})


class ApprovalError(ValueError):
    """The approval metadata is missing, unknown, contradictory or claims more than it may."""


@dataclass(frozen=True, slots=True)
class TableApproval:
    status: str
    decision_ref: str | None  # solo only
    owner_approval: Mapping[str, str] | None  # solo only


def _owner_evidence(meta: Mapping[str, Any], name: str) -> dict[str, str]:
    ev = meta.get("owner_approval")
    if not isinstance(ev, dict):
        raise ApprovalError(f"{name}: owner_approval evidence is required for {SOLO}")
    out: dict[str, str] = {}
    for key in ("approved_by", "approved_on", "record"):
        v = ev.get(key)
        if not isinstance(v, str) or not v.strip():
            raise ApprovalError(f"{name}: owner_approval.{key} is required and must be non-empty text")
        out[key] = v
    if out["approved_by"] != "owner":
        raise ApprovalError(f"{name}: owner_approval.approved_by must be 'owner' (no AI or third party)")
    try:
        date.fromisoformat(out["approved_on"])
    except ValueError as e:
        raise ApprovalError(f"{name}: owner_approval.approved_on is not an ISO date") from e
    return out


def parse_approval(meta: Mapping[str, Any], *, name: str, allow_solo: bool) -> TableApproval:
    """Validate the approval metadata of one table. `allow_solo=False` is the default of every caller."""
    status = meta.get("review_status")
    if status == INDEPENDENT:
        if SOLO_ONLY_KEYS & set(meta):
            raise ApprovalError(f"{name}: solo-approval metadata on an {INDEPENDENT} table is contradictory")
        return TableApproval(INDEPENDENT, None, None)
    if status == SOLO:
        if not allow_solo:
            raise ApprovalError(
                f"{name}: {SOLO} is not enabled for this load; the caller must opt in (DEC-045 / DR-12)"
            )
        claims = INDEPENDENT_CLAIM_KEYS & set(meta)
        if claims:
            raise ApprovalError(
                f"{name}: a solo-approved table cannot carry independent-review claims {sorted(claims)}"
            )
        ref = meta.get("decision_ref")
        if ref not in SOLO_DECISION_REFS:
            raise ApprovalError(
                f"{name}: decision_ref must be one of {sorted(SOLO_DECISION_REFS)}, got {ref!r}"
            )
        return TableApproval(SOLO, str(ref), _owner_evidence(meta, name))
    if allow_solo:
        raise ApprovalError(
            f"{name}: review_status {status!r}; independent human review or owner approval under "
            "DEC-045 / DR-12 is required"
        )
    raise ApprovalError(
        f"{name}: review_status {status!r}; independent human review is required (DR-7/DR-7a)"
    )


@dataclass(frozen=True, slots=True)
class RunApproval:
    basis: str  # INDEPENDENT or SOLO: the weakest basis among the tables
    result_label: str | None  # SOLO_RESULT_LABEL if basis is SOLO, else None
    decision_refs: tuple[str, ...]
    table_status: Mapping[str, str]  # each table's own status, unchanged


def summarise_approvals(tables: Mapping[str, TableApproval]) -> RunApproval:
    if not tables:
        raise ApprovalError("no tables: a run needs an approval basis")
    statuses = {k: v.status for k, v in sorted(tables.items())}
    if any(s not in (INDEPENDENT, SOLO) for s in statuses.values()):
        raise ApprovalError(f"unsupported status among {statuses}")
    if SOLO in statuses.values():
        refs = tuple(sorted({v.decision_ref for v in tables.values() if v.decision_ref}))
        ra = RunApproval(SOLO, SOLO_RESULT_LABEL, refs, statuses)
    else:
        ra = RunApproval(INDEPENDENT, None, (), statuses)
    validate_run_approval(ra)
    return ra


def validate_run_approval(ra: RunApproval) -> None:
    """Consistency of a run's approval record; raises `ApprovalError` on any contradiction."""
    values = set(ra.table_status.values())
    if not values or not values <= {INDEPENDENT, SOLO}:
        raise ApprovalError(f"table statuses must be {INDEPENDENT} or {SOLO}, got {sorted(values)}")
    if ra.basis == SOLO:
        if SOLO not in values:
            raise ApprovalError("solo basis without a solo-approved table")
        if ra.result_label != SOLO_RESULT_LABEL:
            raise ApprovalError("a solo-research run must carry the exact result label")
        if not ra.decision_refs or not set(ra.decision_refs) <= SOLO_DECISION_REFS:
            raise ApprovalError("a solo-research run needs DEC-045 / DR-12 as its decision reference")
    elif ra.basis == INDEPENDENT:
        if values != {INDEPENDENT}:
            raise ApprovalError("independent basis while a table is not independently reviewed")
        if ra.result_label is not None or ra.decision_refs:
            raise ApprovalError("an independently reviewed run must not carry the solo label or references")
    else:
        raise ApprovalError(f"unknown run approval basis {ra.basis!r}")
