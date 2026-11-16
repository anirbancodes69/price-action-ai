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
    base: dict[str, object] = {
        "book": "PAPER",
        "direction": "LONG",
        "capital": "1000000.00",
        "risk_pct": "1.0",
        "entry": "1495.50",
        "stop": "1477.00",
        "target": "1560.00",
        "tick_size": "0.10",
        "lot_size": 1,
        "open_positions": [],
        "max_open_positions": 5,
        "max_heat_pct": "5.0",
        "max_position_pct": "25.0",
        "ruleset_version": "0.1.0",
    }
    return base | over


def test_money_is_held_as_decimal_and_serialised_as_string() -> None:
    req = PositionSizeRequest.model_validate(_sizing())
    assert req.entry == Decimal("1495.50")
    dumped = json.loads(req.model_dump_json())
    assert dumped["entry"] == "1495.50"
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


def test_risk_result_matches_the_arc04_example() -> None:
    result = RiskResult.model_validate(
        {
            "quantity": 167,
            "risk_budget": "10000.00",
            "risk_per_share": "18.50",
            "actual_risk": "3089.50",
            "actual_risk_pct": "0.3090",
            "position_value": "249748.50",
            "rr": "3.4865",
            "binding_constraint": "POSITION_CAP",
            "constraints": {"qty_risk": 540, "qty_capital": 668, "qty_position_cap": 167, "qty_heat": 2702},
            "rounding": {"entry": "1495.50", "stop": "1477.00", "target": "1560.00"},
            "warnings": [],
            "errors": [],
            "ruleset_version": "pa-core 0.1.0",
        }
    )
    assert result.quantity == 167


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
    stale.write_text(stale.read_text().replace('"as_of"', '"asof"'))
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
