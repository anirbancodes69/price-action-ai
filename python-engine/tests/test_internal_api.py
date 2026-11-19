"""Internal risk, scan and analysis endpoints (T-I76..T-I81). Expected values are hand-computed."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.scan import get_analyse_fn, get_snapshot_source
from app.backtest.replay import SessionSpec, SymbolData
from app.main import app
from app.settings import Settings, get_settings

from .backtest.test_replay import CLOSE, OPEN, day, make_analyse

AUTH = {"Authorization": "Bearer t"}
SRC = str(uuid.uuid4())


@pytest.fixture
def client() -> Iterator[TestClient]:
    app.dependency_overrides[get_settings] = lambda: Settings(engine_service_token="t")  # type: ignore[arg-type]
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def sizing_body(**over: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "book": "PAPER",
        "direction": "LONG",
        "capital": "100000",
        "risk_pct": "0.5",
        "entry": "1498.10",
        "stop": "1485.25",
        "target": "1529.00",
        "tick_size": "0.05",
        "lot_size": 1,
        "max_position_value": "50000",
        "max_open_positions": 2,
        "max_open_risk_pct": "1.0",
        "daily_loss_limit_pct": "1.5",
        "max_consecutive_losses": 3,
        "min_rr": None,
        "account_state": {
            "realised_net_pnl_today": "0",
            "open_risk": "0",
            "open_cost_basis": "0",
            "open_positions": 0,
            "losing_streak": 0,
        },
        "as_of_ts": "2026-11-18T05:00:00+00:00",
        "entry_cutoff_at": "2026-11-18T09:15:00+00:00",
        "ruleset_version": "0.1.0",
    }
    body.update(over)
    return body


def test_risk_endpoints_require_the_service_token(client: TestClient) -> None:
    assert client.post("/internal/v1/risk/position-size", json=sizing_body()).status_code == 401
    assert client.post("/internal/v1/scan", json={}).status_code == 401


def test_position_size_matches_the_trd05_worked_example(client: TestClient) -> None:
    res = client.post("/internal/v1/risk/position-size", json=sizing_body(), headers=AUTH)
    assert res.status_code == 200
    r = res.json()
    assert (r["quantity"], r["binding_constraint"], r["errors"]) == (33, "POSITION_CAP", [])
    assert (r["risk_budget"], r["risk_per_share"], r["actual_risk"], r["position_value"]) == (
        "500.0",
        "12.85",
        "424.05",
        "49437.30",
    )
    assert r["constraints"] == {
        "qty_risk": 38,
        "qty_capital": 66,
        "qty_position_cap": 33,
        "qty_open_risk": 77,
        "qty_daily_loss": 116,
    }
    assert r["rounding"] == {"entry": "1498.10", "stop": "1485.25", "target": "1529.00"}
    assert (
        r["account_state"]["remaining_daily_loss"] == "1500.0"
        and r["account_state"]["blocked_reason"] is None
    )
    assert round(float(r["rr"]), 2) == 2.40
    # TRD-06 §5 illustration: costs 53.08, net 966.62 / risk 424.05 = 2.28R
    assert r["est_round_trip_costs"] == "53.08" and round(float(r["rr_after_costs"]), 2) == 2.28
    assert "COSTS_UNVERIFIED" in r["warnings"] and r["ruleset_version"] == "pa-intraday 0.1.0"


def test_position_size_rejections_are_error_codes_not_http_errors(client: TestClient) -> None:
    short = client.post(
        "/internal/v1/risk/position-size", json=sizing_body(direction="SHORT"), headers=AUTH
    ).json()
    assert short["errors"] == ["SHORT_NOT_SUPPORTED"] and short["quantity"] == 0
    state = sizing_body()["account_state"] | {"realised_net_pnl_today": "-1500"}
    blocked = client.post(
        "/internal/v1/risk/position-size", json=sizing_body(account_state=state), headers=AUTH
    ).json()
    assert blocked["errors"] == ["DAILY_LOSS_LIMIT_REACHED"]
    assert blocked["account_state"]["blocked_reason"] == "DAILY_LOSS_LIMIT_REACHED"
    bad_rr = client.post(
        "/internal/v1/risk/position-size", json=sizing_body(target="1505"), headers=AUTH
    ).json()
    assert bad_rr["errors"] == ["RR_BELOW_MINIMUM"] and bad_rr["quantity"] == 0
    after_cutoff = sizing_body(as_of_ts="2026-11-18T09:20:00+00:00")
    assert client.post("/internal/v1/risk/position-size", json=after_cutoff, headers=AUTH).json()[
        "errors"
    ] == ["ENTRY_CUTOFF_PASSED"]


def account_body(**over: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "book": "ACTUAL",
        "capital": "100000",
        "daily_loss_limit_pct": "1.5",
        "max_consecutive_losses": 3,
        "max_open_positions": 2,
        "account_state": sizing_body()["account_state"],
        "session_open": True,
        "as_of_ts": "2026-11-18T05:00:00+00:00",
        "entry_cutoff_at": "2026-11-18T09:15:00+00:00",
    }
    body.update(over)
    return body


def test_account_state_reports_what_remains_and_the_first_blocking_rule(client: TestClient) -> None:
    def call(**over: Any) -> dict[str, Any]:
        res = client.post("/internal/v1/risk/account-state", json=account_body(**over), headers=AUTH)
        assert res.status_code == 200
        return res.json()  # type: ignore[no-any-return]

    ok = call()
    assert ok["daily_loss_limit"] == "1500.0" and ok["account_state"]["remaining_daily_loss"] == "1500.0"
    assert ok["account_state"]["blocked_reason"] is None

    # A 400 loss with 250 of open risk leaves 1500 - 650 = 850.
    used = sizing_body()["account_state"] | {"realised_net_pnl_today": "-400", "open_risk": "250"}
    assert call(account_state=used)["account_state"]["remaining_daily_loss"] == "850.0"

    # Only realised losses trip the daily limit; the first failing rule is reported (TRD-05 §8 order).
    lost = sizing_body()["account_state"] | {"realised_net_pnl_today": "-1500", "losing_streak": 3}
    assert call(account_state=lost)["account_state"]["blocked_reason"] == "DAILY_LOSS_LIMIT_REACHED"
    streak = sizing_body()["account_state"] | {"losing_streak": 3}
    assert call(account_state=streak)["account_state"]["blocked_reason"] == "MAX_CONSECUTIVE_LOSSES_REACHED"
    full = sizing_body()["account_state"] | {"open_positions": 2}
    assert call(account_state=full)["account_state"]["blocked_reason"] == "MAX_POSITIONS_REACHED"
    assert call(session_open=False)["account_state"]["blocked_reason"] == "SESSION_CLOSED"
    late = call(as_of_ts="2026-11-18T09:20:00+00:00")
    assert late["account_state"]["blocked_reason"] == "ENTRY_CUTOFF_PASSED"
    assert client.post("/internal/v1/risk/account-state", json={}, headers=AUTH).status_code == 422


def test_unknown_ruleset_version_and_invalid_body(client: TestClient) -> None:
    res = client.post(
        "/internal/v1/risk/position-size", json=sizing_body(ruleset_version="9.9.9"), headers=AUTH
    )
    assert (res.status_code, res.json()["detail"]) == (422, "UNKNOWN_RULESET_VERSION")
    assert (
        client.post("/internal/v1/risk/position-size", json={"book": "PAPER"}, headers=AUTH).status_code
        == 422
    )
    extra = client.post("/internal/v1/risk/position-size", json=sizing_body(nope=1), headers=AUTH)
    assert extra.status_code == 422  # unknown fields are rejected by the contract


def test_validate_levels(client: TestClient) -> None:
    def call(**over: Any) -> dict[str, Any]:
        body = {
            "direction": "LONG",
            "entry": "1000.02",
            "stop": "980.07",
            "target": "1060",
            "tick_size": "0.05",
            "min_rr": None,
            "ruleset_version": "0.1.0",
        } | over
        return client.post("/internal/v1/risk/validate-levels", json=body, headers=AUTH).json()

    ok = call()
    assert ok["errors"] == []
    assert {k: D(v) for k, v in ok["rounding"].items()} == {
        "entry": D("1000.05"),
        "stop": D("980.05"),
        "target": D("1060"),
    }
    assert call(stop="979.9")["errors"] == ["STOP_TOO_WIDE"]
    assert call(stop="999.00")["errors"] == ["STOP_TOO_TIGHT"]
    assert call(stop="1001")["errors"] == ["STOP_NOT_BELOW_ENTRY"]
    assert call(target="1010")["errors"] == ["RR_BELOW_MINIMUM"]
    assert call(direction="SHORT")["errors"] == ["SHORT_NOT_SUPPORTED"]
    assert call(min_rr="4")["errors"] == ["RR_BELOW_MINIMUM"]  # a stricter user floor applies (3.0 < 4)


SPEC = SessionSpec(OPEN.date(), OPEN, CLOSE)


def sym(name: str, n: int = 3) -> SymbolData:
    return SymbolData(name, day({}, n=n), [], None, D("0.05"))


from decimal import Decimal as D  # noqa: E402


class FakeSource:
    def __init__(self, items: list[SymbolData] | None = None, mode: str = "DEMO") -> None:
        self.items = items if items is not None else [sym("A"), sym("B")]
        self.mode = mode
        self.calls: list[tuple[Any, ...]] = []

    def source_info(self, source: uuid.UUID) -> tuple[str, str] | None:
        return None if str(source) != SRC else (self.mode, "DEMO")

    def universe(
        self, source: uuid.UUID, code: str, as_of: datetime, lookback: int, replay: bool
    ) -> list[Any]:
        self.calls.append(("universe", code, replay, lookback))
        return [(s, SPEC) for s in self.items]

    def symbol(self, source: uuid.UUID, symbol: str, as_of: datetime | None, lookback: int) -> Any:
        self.calls.append(("symbol", symbol, as_of))
        match = [s for s in self.items if s.symbol == symbol]
        return (match[0], SPEC) if match else None


def wire(fake: FakeSource, fn: Any) -> None:
    app.dependency_overrides[get_snapshot_source] = lambda: fake
    app.dependency_overrides[get_analyse_fn] = lambda: fn


def scan_body(**over: Any) -> dict[str, Any]:
    return {"data_source_id": SRC, "universe_code": "NIFTY50", "account": {"capital": "100000"}} | over


def test_scan_returns_sized_actionable_rows(client: TestClient) -> None:
    fake = FakeSource()
    wire(fake, make_analyse({("A", 2): 80}))
    now = sym("A").bars_5m[-1].end.isoformat()  # replay at the last bar so the data is not stale
    res = client.post("/internal/v1/scan", json=scan_body(as_of_ts=now), headers=AUTH)
    assert res.status_code == 200
    body = res.json()
    assert body["data_mode"] == "DEMO" and body["ruleset_version"] == "pa-intraday 0.1.0"
    assert "place any order yourself" in body["notice"]
    [row] = body["rows"]  # B is NO_TRADE and hidden by default
    assert (row["symbol"], row["signal"], row["paqs"], row["quantity"]) == ("A", "ENTRY_CONFIRMED", 80, 500)
    assert (row["entry"], row["stop"], row["target"], row["risk_amount"]) == ("100", "99", "103", "500.0")
    assert (row["last_close"], row["prev_day_close"], row["structure_state"]) == ("100", None, None)
    assert (row["direction"], row["trigger_price"]) == ("LONG", "100")
    assert fake.calls == [("universe", "NIFTY50", True, 5)]
    both = client.post(
        "/internal/v1/scan", json=scan_body(as_of_ts=now, include_no_trade=True), headers=AUTH
    ).json()
    assert [r["symbol"] for r in both["rows"]] == ["A", "B"]


def test_scan_applies_the_callers_account_state(client: TestClient) -> None:
    wire(FakeSource(), make_analyse({("A", 2): 80}))
    acct = {"capital": "100000", "realised_net_pnl_today": "-1500"}
    row = client.post("/internal/v1/scan", json=scan_body(account=acct), headers=AUTH).json()["rows"][0]
    assert row["quantity"] is None and "DAILY_LOSS_LIMIT_REACHED" in row["reasons"]
    streak = {"capital": "100000", "losing_streak": 3}
    row = client.post("/internal/v1/scan", json=scan_body(account=streak), headers=AUTH).json()["rows"][0]
    assert "MAX_CONSECUTIVE_LOSSES_REACHED" in row["reasons"]
    risk = {"capital": "100000", "open_risk": "1000", "open_cost_basis": "50000", "open_positions": 1}
    row = client.post("/internal/v1/scan", json=scan_body(account=risk), headers=AUTH).json()["rows"][0]
    assert row["quantity"] is None  # the 1.0 % open-risk limit is already used


def test_scan_replay_unknown_source_and_stale_rows(client: TestClient) -> None:
    fake = FakeSource()
    wire(fake, make_analyse({("A", 2): 80}))
    past = (OPEN + timedelta(minutes=15)).isoformat()
    assert client.post("/internal/v1/scan", json=scan_body(as_of_ts=past), headers=AUTH).status_code == 200
    assert fake.calls[-1][2] is True  # replay: only bars that ended by as_of
    unknown = client.post("/internal/v1/scan", json=scan_body(data_source_id=str(uuid.uuid4())), headers=AUTH)
    assert (unknown.status_code, unknown.json()["detail"]) == (404, "DATA_SOURCE_NOT_FOUND")
    # live scan far from the data: rows are flagged stale even when quiet
    rows = client.post("/internal/v1/scan", json=scan_body(), headers=AUTH).json()["rows"]
    assert rows and all(r["stale"] for r in rows)  # the fixture bars are from 2026-11-18, "now" is later


def test_analysis_detail_runs_the_real_analysis(client: TestClient) -> None:
    from app.backtest.replay import default_analyse

    flat = day({}, n=160)
    fifteen = [b for i, b in enumerate(flat) if i < 80]
    fifteen = [
        b.__class__(b.start, b.start + timedelta(minutes=15), b.open, b.high, b.low, b.close) for b in fifteen
    ]
    fake = FakeSource([SymbolData("Z", flat, fifteen, None, D("0.05"))])
    wire(fake, default_analyse)
    res = client.post("/internal/v1/analysis", json={"data_source_id": SRC, "symbol": "Z"}, headers=AUTH)
    assert res.status_code == 200
    d = res.json()
    assert (d["symbol"], d["status"], d["state_5m"], d["ruleset_version"]) == (
        "Z",
        "VALID",
        "SIDEWAYS",
        "pa-intraday 0.1.0",
    )
    assert d["signal"]["signal"] == "NO_TRADE" and d["levels"]["session_high"] is not None
    assert d["session_date"] == OPEN.date().isoformat() and isinstance(d["pivots"], list)


def test_analysis_detail_short_history_and_errors(client: TestClient) -> None:
    from app.backtest.replay import default_analyse

    wire(FakeSource([sym("Z")]), default_analyse)
    d = client.post("/internal/v1/analysis", json={"data_source_id": SRC, "symbol": "Z"}, headers=AUTH).json()
    assert d["status"] == "INSUFFICIENT_HISTORY" and d["state_5m"] is None and d["setups"] == []
    assert any("5m bars" in p for p in d["problems"])
    missing = client.post(
        "/internal/v1/analysis", json={"data_source_id": SRC, "symbol": "NOPE"}, headers=AUTH
    )
    assert (missing.status_code, missing.json()["detail"]) == (404, "NO_BARS_FOR_SYMBOL")
    bad_src = client.post(
        "/internal/v1/analysis", json={"data_source_id": str(uuid.uuid4()), "symbol": "Z"}, headers=AUTH
    )
    assert bad_src.status_code == 404 and UTC is not None


def test_analysis_detail_carries_setups_and_levels(client: TestClient) -> None:
    from dataclasses import replace

    base = make_analyse({("A", 2): 80})

    def with_setups(s: SymbolData, k: int, spec: SessionSpec, p: Any) -> Any:
        res = base(s, k, spec, p)
        prim = res.signal.primary if res.signal else None
        return replace(res, setups=(prim,) if prim else ())

    wire(FakeSource([sym("A")]), with_setups)
    d = client.post("/internal/v1/analysis", json={"data_source_id": SRC, "symbol": "A"}, headers=AUTH).json()
    [s] = d["setups"]
    assert (s["type"], s["status"], s["paqs"], s["rr"], s["target"]) == (
        "OPENING_RANGE_BREAKOUT",
        "ENTRY_CONFIRMED",
        80,
        "3",
        "103",
    )
    assert d["signal"]["signal"] == "ENTRY_CONFIRMED" and d["signal"]["reasons"] == []
