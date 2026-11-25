"""Research run evidence (E8): data-class labels, timestamps, variant counter, hashes and pre-registration
support.

Nothing here writes to a database. `EvidenceRecord` is a plain, frozen, serialisable description of one
research
run that is stored next to the run's output file; `VariantLedger` is a small JSON file counting the distinct
variants evaluated so far. **No final pre-registration is created by this module**: `PreRegistration` can be
drafted with hashes and thresholds unset, and `validate_for_freeze` refuses it until every value is real and
consistent with the actual repository state (it never fills a value in).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from app.backtest.approval import ApprovalError, RunApproval, validate_run_approval
from app.backtest.b0_contract import B0_RULESET_HASH, B0_STRATEGY, B0ContractError, validate_b0_reference_data
from app.backtest.run import BacktestResult, compute_run_digest

DATA_CLASSES = ("DEVELOPMENT", "RESERVE", "PROSPECTIVE", "SYNTHETIC")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_GIT = re.compile(r"^[0-9a-f]{40}$")


class EvidenceError(ValueError):
    pass


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    run_kind: str  # "ORB_B0_4A", "ORB_B0_4B", "CONTROL_SET", ...
    data_class: str
    strategy_id: str
    ruleset: str
    ruleset_hash: str
    commit: str  # 40 hex, or "UNKNOWN"
    working_tree_clean: bool | None  # None = not determined
    reference_hashes: Mapping[str, str]
    engine_version: str
    inputs_hash: str
    first_session: str | None
    last_session: str | None
    variant_number: int  # cumulative count of distinct variants evaluated, including this one
    evaluated_at_utc: str
    approval_basis: str  # INDEPENDENTLY_REVIEWED or OWNER_APPROVED_SOLO_RESEARCH (the weakest table governs)
    approval_decision_refs: tuple[str, ...]  # DEC-045 / DR-12 for a solo basis, else empty
    table_review_status: Mapping[str, str]  # each table's own status, unchanged
    result_label: str | None  # the exact solo label for a solo basis, else None
    run_digest: str  # B0: `compute_run_digest` of the run record this evidence belongs to; else ""
    seeds: Mapping[str, int] = field(default_factory=dict)
    parameters: Mapping[str, str] = field(default_factory=dict)
    ai_review_label: str = "AI-ASSISTED — NON-INDEPENDENT"
    reproducibility: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """No record can carry a missing, replaced or contradictory label, even by direct construction."""
        run = RunApproval(
            self.approval_basis,
            self.result_label,
            tuple(self.approval_decision_refs),
            self.table_review_status,
        )
        try:
            validate_run_approval(run)
        except ApprovalError as e:
            raise EvidenceError(f"inconsistent approval metadata: {e}") from e
        ref = self.reference_hashes
        if ref.get("approval_basis", self.approval_basis) != self.approval_basis:
            raise EvidenceError("reference_hashes approval_basis contradicts the record")
        if (ref.get("result_label", self.result_label or "") or None) != self.result_label:
            raise EvidenceError("reference_hashes result_label contradicts the record")
        for k, v in ref.items():
            name = k.removesuffix("_review_status")
            if name != k and self.table_review_status.get(name, v) != v:
                raise EvidenceError(f"reference_hashes {k} contradicts table_review_status")
        if self.strategy_id == B0_STRATEGY or self.ruleset == "pa-intraday 0.6.0":
            self._check_b0()

    def _check_b0(self) -> None:
        """B0 evidence exists only for the strict contract: actual strategy, ruleset and released hash,
        table hashes and statuses in `reference_hashes`, and an approval record equal to the derived one."""
        if self.strategy_id != B0_STRATEGY:
            raise EvidenceError(
                f"ruleset 0.6.0 evidence is reserved for {B0_STRATEGY}, not {self.strategy_id!r}"
            )
        if self.ruleset != "pa-intraday 0.6.0" or self.ruleset_hash != B0_RULESET_HASH:
            raise EvidenceError("B0 evidence must name pa-intraday 0.6.0 and its released hash")
        try:
            derived = validate_b0_reference_data(self.reference_hashes)
        except B0ContractError as e:
            raise EvidenceError(f"B0 evidence lacks the strict runner's reference data: {e}") from e
        if not _HEX64.match(self.run_digest):
            raise EvidenceError("B0 evidence must carry the run digest of the run it describes")
        mine = (
            self.approval_basis,
            self.result_label,
            tuple(self.approval_decision_refs),
            dict(self.table_review_status),
        )
        if mine != (derived.basis, derived.result_label, derived.decision_refs, dict(derived.table_status)):
            raise EvidenceError(
                "B0 evidence approval fields differ from the approval recorded with the tables"
            )

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, indent=2)


def build_evidence(
    *,
    run_kind: str,
    data_class: str,
    strategy_id: str,
    ruleset: str,
    ruleset_hash: str,
    commit: str,
    working_tree_clean: bool | None,
    reference_hashes: Mapping[str, str],
    engine_version: str,
    inputs_hash: str,
    first_session: str | None,
    last_session: str | None,
    variant_number: int,
    approval: RunApproval,
    run_digest: str = "",
    seeds: Mapping[str, int] | None = None,
    parameters: Mapping[str, str] | None = None,
    reproducibility: Mapping[str, str] | None = None,
    now: str | None = None,
) -> EvidenceRecord:
    if data_class not in DATA_CLASSES:
        raise EvidenceError(f"data_class must be one of {DATA_CLASSES}")
    if not _HEX64.match(ruleset_hash):
        raise EvidenceError("ruleset_hash must be a 64-hex SHA-256")
    if commit != "UNKNOWN" and not _GIT.match(commit):
        raise EvidenceError("commit must be a 40-hex git hash or UNKNOWN")
    bad = [k for k, v in reference_hashes.items() if k.endswith("_sha256") and not _HEX64.match(v)]
    if bad:
        raise EvidenceError(f"reference hashes are not SHA-256: {bad}")
    if variant_number < 1:
        raise EvidenceError("variant_number starts at 1")
    return EvidenceRecord(
        run_kind, data_class, strategy_id, ruleset, ruleset_hash, commit, working_tree_clean,
        dict(reference_hashes), engine_version, inputs_hash, first_session, last_session, variant_number,
        now or _utc_now(), approval.basis, tuple(approval.decision_refs), dict(approval.table_status),
        approval.result_label, run_digest, dict(seeds or {}), dict(parameters or {}),
        reproducibility=dict(reproducibility or {}),
    )  # fmt: skip


class VariantLedger:
    """Cumulative count of distinct variants evaluated (plan §2, §9). A JSON file: `{"variants":
    [ids...]}`."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def _read(self) -> list[str]:
        if not self.path.exists():
            return []
        doc = json.loads(self.path.read_text(encoding="utf-8"))
        v = doc.get("variants")
        if not isinstance(v, list) or len(v) != len(set(v)):
            raise EvidenceError("ledger is corrupt (not a list of distinct ids)")
        return [str(x) for x in v]

    def count(self) -> int:
        return len(self._read())

    def register(self, variant_id: str) -> int:
        """Record `variant_id` once and return its number; registering it again returns the same number."""
        ids = self._read()
        if variant_id in ids:
            return ids.index(variant_id) + 1
        ids.append(variant_id)
        self.path.write_text(json.dumps({"variants": ids}, indent=2), encoding="utf-8")
        return len(ids)


@dataclass(frozen=True, slots=True)
class PreRegistration:
    """A draft is allowed to have unset fields (`None`); a frozen one is not. Thresholds are the owner's."""

    experiment: str
    strategy_id: str
    ruleset: str
    ruleset_hash: str | None = None
    commit: str | None = None
    reference_hashes: Mapping[str, str] | None = None
    thresholds: Mapping[str, str] | None = None  # copied from the approved plan; never defaulted here
    approved_by: str | None = None
    status: str = "DRAFT"

    def fingerprint(self) -> str:
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()


def validate_for_freeze(p: PreRegistration, *, actual_commit: str, actual_ruleset_hash: str) -> list[str]:
    """Problems that stop a freeze (empty list = none). It checks consistency; it never supplies a value."""
    problems: list[str] = []
    if p.ruleset_hash is None or not _HEX64.match(p.ruleset_hash):
        problems.append("ruleset_hash is unset or not SHA-256")
    elif p.ruleset_hash != actual_ruleset_hash:
        problems.append("ruleset_hash differs from the actual ruleset")
    if p.commit is None or not _GIT.match(p.commit):
        problems.append("commit is unset or not a 40-hex git hash")
    elif p.commit != actual_commit:
        problems.append("commit differs from the actual commit")
    if not p.reference_hashes:
        problems.append("reference hashes are unset")
    elif any(not _HEX64.match(v) for k, v in p.reference_hashes.items() if k.endswith("_sha256")):
        problems.append("a reference hash is not SHA-256")
    if not p.thresholds:
        problems.append("thresholds are unset (they come from the approved plan, never from this module)")
    if not p.approved_by:
        problems.append("no approver recorded")
    return problems


def verify_evidence_for_result(ev: EvidenceRecord, result: BacktestResult) -> None:
    """The evidence must describe this very run: same digest, inputs, reference data and ruleset hash. Raises
    `EvidenceError` otherwise (evidence from another run, or a result edited after the evidence was built)."""
    rec = result.record
    if ev.strategy_id == B0_STRATEGY and not rec.run_digest:
        raise EvidenceError("the result carries no run digest: it did not come from the strict B0 path")
    if compute_run_digest(rec) != rec.run_digest and rec.run_digest:
        raise EvidenceError("the result's run record was altered after it was built")
    same = (
        ev.run_digest == rec.run_digest
        and ev.inputs_hash == rec.inputs_hash
        and dict(ev.reference_hashes) == dict(rec.reference_data)
        and ev.ruleset_hash == rec.ruleset_hash
        and ev.strategy_id == (rec.strategy_id or "")
    )
    if not same:
        raise EvidenceError("this evidence belongs to a different run")
