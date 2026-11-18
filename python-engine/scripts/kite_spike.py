"""T-201 verification spike: what does the Kite API actually allow? Read-only, personal account.

Usage: uv run python scripts/kite_spike.py   (after kite_login.py today)
Probes: instrument master, 5m/15m history depth per request, whether the forming bar is returned,
last-price quote, and the request rate at which HTTP 429 appears. Prints findings; never prints secrets.
"""

from __future__ import annotations

import csv
import io
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
from _kite_env import TOKEN_FILE, load_env, require

IST = ZoneInfo("Asia/Kolkata")
BASE = "https://api.kite.trade"


def main() -> None:
    env = load_env()
    require(env, "KITE_API_KEY")
    if not TOKEN_FILE.exists():
        raise SystemExit("No .kite_token: run scripts/kite_login.py first.")
    headers = {
        "X-Kite-Version": "3",
        "Authorization": f"token {env['KITE_API_KEY']}:{TOKEN_FILE.read_text().strip()}",
    }
    c = httpx.Client(base_url=BASE, headers=headers, timeout=20)

    def get(path: str, **params: object) -> httpx.Response:
        return c.get(path, params={k: v for k, v in params.items() if v is not None})

    print("== instrument master (NSE)")
    r = get("/instruments/NSE")
    print("HTTP", r.status_code)
    if r.status_code != 200:
        raise SystemExit(f"{r.text[:200]}")
    rows = list(csv.DictReader(io.StringIO(r.text)))
    eq = [x for x in rows if x["segment"] == "NSE" and x["instrument_type"] == "EQ"]
    idx = [x for x in rows if x["segment"] == "INDICES"]
    print(f"rows={len(rows)} equities={len(eq)} indices={len(idx)} columns={list(rows[0])}")
    rel = next(x for x in eq if x["tradingsymbol"] == "RELIANCE")
    nifty = next((x for x in idx if x["tradingsymbol"] == "NIFTY 50"), None)
    print("RELIANCE token", rel["instrument_token"], "| NIFTY 50 token", nifty and nifty["instrument_token"])

    fmt = "%Y-%m-%d %H:%M:%S"
    now = datetime.now(IST)
    for interval in ("5minute", "15minute"):
        print(f"== history depth, {interval} (RELIANCE)")
        for days in (30, 60, 100, 200, 400):
            start = now - timedelta(days=days)
            r = get(
                f"/instruments/historical/{rel['instrument_token']}/{interval}",
                **{"from": start.strftime(fmt), "to": now.strftime(fmt)},
            )
            body = r.json()
            if r.status_code == 200:
                candles = body["data"]["candles"]
                first = candles[0][0] if candles else None
                print(f"{days:>4}d  HTTP 200  bars={len(candles)} first={first}")
            else:
                print(f"{days:>4}d  HTTP {r.status_code}  {body.get('error_type')}: {body.get('message')}")
            time.sleep(0.4)

    print("== forming bar check (today, 5minute)")
    r = get(
        f"/instruments/historical/{rel['instrument_token']}/5minute",
        **{"from": now.replace(hour=9, minute=0, second=0).strftime(fmt), "to": now.strftime(fmt)},
    )
    if r.status_code == 200 and r.json()["data"]["candles"]:
        last = r.json()["data"]["candles"][-1]
        print(
            f"now={now:%H:%M:%S} last bar start={last[0]} (start within 5 min of now = forming bar returned)"
        )
    else:
        print("HTTP", r.status_code, "no bars today (market closed?)")

    print("== quote ltp")
    r = get("/quote/ltp", i=["NSE:RELIANCE", "NSE:NIFTY 50"])
    print("HTTP", r.status_code, r.text[:300])

    print("== rate probe: 15 back-to-back historical requests")
    codes: list[int] = []
    t0 = time.monotonic()
    for _ in range(15):
        rr = get(
            f"/instruments/historical/{rel['instrument_token']}/5minute",
            **{"from": (now - timedelta(days=2)).strftime(fmt), "to": now.strftime(fmt)},
        )
        codes.append(rr.status_code)
    print(
        f"{len(codes)} requests in {time.monotonic() - t0:.1f}s; status counts:",
        {s: codes.count(s) for s in sorted(set(codes))},
    )


if __name__ == "__main__":
    main()
