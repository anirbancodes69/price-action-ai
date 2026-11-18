"""Shared helpers for the local Kite scripts. Never prints secrets."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOKEN_FILE = ROOT / ".kite_token"  # gitignored; the access token expires daily


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for line in (ROOT / ".env").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    env.update({k: v for k, v in os.environ.items() if k.startswith("KITE_")})
    return env


def require(env: dict[str, str], *keys: str) -> None:
    missing = [k for k in keys if not env.get(k)]
    if missing:
        raise SystemExit(f"Missing in .env: {', '.join(missing)}")
