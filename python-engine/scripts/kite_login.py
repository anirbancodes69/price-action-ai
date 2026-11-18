"""Daily Kite login: exchange the request_token for an access token (ARC-08 §4.1, manual form).

Usage: uv run python scripts/kite_login.py
1. Open the printed login URL and log in to Zerodha.
2. Your browser is redirected to KITE_REDIRECT_URL?request_token=...&status=success. The page may fail
   to load: that is fine. Copy the full address-bar URL and paste it here.
The access token is written to .kite_token (gitignored, mode 600). Nothing secret is printed.
"""

from __future__ import annotations

import hashlib
import sys
from urllib.parse import parse_qs, urlparse

import httpx
from _kite_env import TOKEN_FILE, load_env, require


def main() -> None:
    env = load_env()
    require(env, "KITE_API_KEY", "KITE_API_SECRET")
    key, secret = env["KITE_API_KEY"], env["KITE_API_SECRET"]
    print(f"Open and log in:\n  https://kite.zerodha.com/connect/login?v=3&api_key={key}\n")
    pasted = input("Paste the full redirected URL (or just the request_token): ").strip()
    query = parse_qs(urlparse(pasted).query)
    if "request_token" in query:
        token = query["request_token"][0]
    elif pasted.startswith(("http://", "https://")):
        sys.exit(
            "That URL has no request_token. After logging in, click the address bar (Chrome may hide "
            "the query string) and copy the whole URL, which must contain ?request_token=..."
        )
    else:
        token = pasted
    if query.get("status", ["success"])[0] != "success":
        sys.exit("Login did not succeed (status != success).")
    checksum = hashlib.sha256((key + token + secret).encode()).hexdigest()
    resp = httpx.post(
        "https://api.kite.trade/session/token",
        headers={"X-Kite-Version": "3"},
        data={"api_key": key, "request_token": token, "checksum": checksum},
        timeout=15,
    )
    body = resp.json()
    if resp.status_code != 200 or body.get("status") != "success":
        sys.exit(
            f"Token exchange failed: HTTP {resp.status_code} {body.get('error_type')}: {body.get('message')}"
        )
    TOKEN_FILE.write_text(body["data"]["access_token"])
    TOKEN_FILE.chmod(0o600)
    print(
        f"OK. Token saved to {TOKEN_FILE.name} (user {body['data'].get('user_id')}); valid until ~06:00 IST."
    )


if __name__ == "__main__":
    main()
