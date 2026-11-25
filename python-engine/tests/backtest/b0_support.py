"""Synthetic reference evidence for tests of the B0 contract (no real table, no real hash)."""

from __future__ import annotations

TABLES = ("tick", "event", "session", "price_basis")
INDEPENDENT = "INDEPENDENTLY_REVIEWED"
SOLO = "OWNER_APPROVED_SOLO_RESEARCH"
LABEL = "EXPLORATORY — SOLO RESEARCH — NOT INDEPENDENTLY VALIDATED"


def reference_data(statuses: dict[str, str] | None = None) -> dict[str, str]:
    """What the strict runner records, built by hand: every table independently reviewed unless `statuses` says
    otherwise (then the weakest basis governs, as in `approval.summarise_approvals`)."""
    st = dict.fromkeys(TABLES, INDEPENDENT) | (statuses or {})
    solo = SOLO in st.values()
    return {
        "tick_table_sha256": "a" * 64,
        "event_table_sha256": "b" * 64,
        "session_table_sha256": "c" * 64,
        "price_basis_sha256": "d" * 64,
        "tick_resolver_version": "tick-resolver-1.0.0",
        **{f"{k}_review_status": v for k, v in st.items()},
        "approval_basis": SOLO if solo else INDEPENDENT,
        "approval_decision_refs": "DEC-045" if solo else "",
        "result_label": LABEL if solo else "",
    }


INDEPENDENT_RD = reference_data()
SOLO_RD = reference_data({"tick": SOLO})


def ctx(params, rd=None):  # type: ignore[no-untyped-def]
    """A synthetic execution context (tests only; production issues it solely in `b0_run.build_reference`)."""
    from app.backtest.b0_contract import issue_context

    return issue_context(params, rd if rd is not None else INDEPENDENT_RD)
