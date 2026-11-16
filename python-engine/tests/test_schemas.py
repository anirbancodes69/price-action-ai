"""Engine contract models (ARC-08 §5) and the JSON Schema export (ENG-04 §8)."""

import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas import (
    EXPORTED_MODELS,
    AnalyseRequest,
    ExplanationRequest,
    PositionSizeRequest,
    ProviderAccessToken,
    RiskResult,
)

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "export_engine_schemas.py"


def _sizing(**over: object) -> dict[str, object]:
    """TRD-05 §3.1 inputs: ₹1,00,000 capital, 0.5% risk, ₹50,000 cap, no positions, no loss today."""
    base: dict[str, object] = {
        "book": "PAPER",
        "direction": "LONG",
        "capital": "100000.00",
        "risk_pct": "0.5",
        "entry": "1498.10",
        "stop": "1485.25",
        "target": "1529.00",
        "tick_size": "0.05",
        "lot_size": 1,
        "max_position_value": "50000.00",
        "max_open_positions": 2,
        "max_open_risk_pct": "1.0",
        "daily_loss_limit_pct": "1.5",
        "max_consecutive_losses": 3,
        "account_state": {
            "realised_net_pnl_today": "0.00",
            "open_risk": "0.00",
            "open_cost_basis": "0.00",
            "open_positions": 0,
            "losing_streak": 0,
        },
        "as_of_ts": "2026-11-13T09:45:00+05:30",
        "entry_cutoff_at": "2026-11-13T14:45:00+05:30",
        "ruleset_version": "0.1.0",
    }
    return base | over


def test_money_is_held_as_decimal_and_serialised_as_string() -> None:
    req = PositionSizeRequest.model_validate(_sizing())
    assert req.entry == Decimal("1498.10")
    dumped = json.loads(req.model_dump_json())
    assert dumped["entry"] == "1498.10"
    assert isinstance(dumped["capital"], str)


def test_unknown_fields_and_bad_enums_are_rejected() -> None:
    with pytest.raises(ValidationError):
        PositionSizeRequest.model_validate(_sizing(quantity=100))  # quantity is never client-supplied
    with pytest.raises(ValidationError):
        PositionSizeRequest.model_validate(_sizing(book="BOTH"))
    with pytest.raises(ValidationError):
        AnalyseRequest.model_validate(
            {"data_source_id": str(uuid4()), "instrument_id": str(uuid4()), "ruleset_version": "v1"}
        )
    with pytest.raises(ValidationError):
        AnalyseRequest.model_validate(
            {
                "data_source_id": str(uuid4()),
                "instrument_id": str(uuid4()),
                "ruleset_version": "0.1.0",
                "as_of": "2026-11-13",
            }
        )


def test_models_are_immutable() -> None:
    req = PositionSizeRequest.model_validate(_sizing())
    with pytest.raises(ValidationError):
        req.entry = Decimal("1")  # type: ignore[misc]


@pytest.mark.parametrize(
    ("kind", "question", "ok"),
    [
        ("SETUP_SUMMARY", None, True),
        ("SETUP_SUMMARY", "why?", False),
        ("CHART_QA", "Why is this a retest?", True),
        ("CHART_QA", None, False),
        ("CHART_QA", "no", False),  # shorter than 3 characters
    ],
)
def test_question_exists_exactly_for_chart_qa(kind: str, question: str | None, ok: bool) -> None:
    payload = {"analysis_run_id": str(uuid4()), "kind": kind, "question": question}
    if ok:
        assert ExplanationRequest.model_validate(payload).kind == kind
    else:
        with pytest.raises(ValidationError):
            ExplanationRequest.model_validate(payload)


def test_access_token_never_appears_in_repr_or_dump() -> None:
    token = ProviderAccessToken.model_validate(
        {"access_token": "s3cr3t-token", "expires_at": "2026-11-17T09:00:00+05:30"}
    )
    assert "s3cr3t-token" not in repr(token)
    assert "s3cr3t-token" not in str(token.model_dump())
    assert token.access_token.get_secret_value() == "s3cr3t-token"


def test_risk_result_matches_the_trd05_worked_example() -> None:
    """TRD-05 §3.1: qty 33, binding POSITION_CAP, actual risk ₹424.05."""
    result = RiskResult.model_validate(
        {
            "quantity": 33,
            "risk_budget": "500.00",
            "risk_per_share": "12.85",
            "actual_risk": "424.05",
            "actual_risk_pct": "0.4241",
            "position_value": "49437.30",
            "rr": "2.4047",
            "rr_after_costs": "2.2800",
            "est_round_trip_costs": "53.08",
            "binding_constraint": "POSITION_CAP",
            "constraints": {
                "qty_risk": 38,
                "qty_capital": 66,
                "qty_position_cap": 33,
                "qty_open_risk": 77,
                "qty_daily_loss": 116,
            },
            "account_state": {
                "realised_net_pnl_today": "0.00",
                "open_risk": "0.00",
                "losing_streak": 0,
                "remaining_daily_loss": "1500.00",
                "blocked_reason": None,
            },
            "rounding": {"entry": "1498.10", "stop": "1485.25", "target": "1529.00"},
            "warnings": [],
            "errors": [],
            "ruleset_version": "pa-intraday 0.1.0",
        }
    )
    assert result.quantity == 33
    assert result.constraints.qty_position_cap == 33


def test_sizing_request_needs_account_state_and_session_clock() -> None:
    with pytest.raises(ValidationError):
        PositionSizeRequest.model_validate({k: v for k, v in _sizing().items() if k != "account_state"})
    with pytest.raises(ValidationError):
        PositionSizeRequest.model_validate({k: v for k, v in _sizing().items() if k != "entry_cutoff_at"})
    with pytest.raises(ValidationError):
        PositionSizeRequest.model_validate(_sizing(max_position_pct="25.0"))  # daily-scope field is gone


def test_exported_schemas_are_canonical_and_named_after_models() -> None:
    names = {m.__name__ for m in EXPORTED_MODELS}
    assert len(names) == len(EXPORTED_MODELS)
    for model in EXPORTED_MODELS:
        schema = model.model_json_schema()
        assert schema["title"] == model.__name__
        assert schema.get("additionalProperties") is False


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, check=False)  # noqa: S603


def test_export_writes_then_check_passes_and_detects_staleness(tmp_path: Path) -> None:
    out = tmp_path / "engine"
    assert _run("--out", str(out)).returncode == 0
    files = sorted(p.name for p in out.glob("*.json"))
    assert files == sorted(f"{m.__name__}.json" for m in EXPORTED_MODELS)
    assert _run("--check", "--out", str(out)).returncode == 0

    stale = out / "AnalyseRequest.json"
    stale.write_text(stale.read_text().replace('"as_of_ts"', '"asof"'))
    result = _run("--check", "--out", str(out))
    assert result.returncode == 1
    assert "stale" in result.stdout and "AnalyseRequest.json" in result.stdout

    (out / "Extra.json").write_text("{}\n")
    (out / "JobCreate.json").unlink()
    result = _run("--check", "--out", str(out))
    assert result.returncode == 1
    assert "unknown" in result.stdout and "missing" in result.stdout


def test_export_is_deterministic(tmp_path: Path) -> None:
    _run("--out", str(tmp_path / "a"))
    _run("--out", str(tmp_path / "b"))
    for f in (tmp_path / "a").glob("*.json"):
        assert f.read_text() == (tmp_path / "b" / f.name).read_text()
