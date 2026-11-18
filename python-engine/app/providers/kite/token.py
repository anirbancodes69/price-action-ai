"""Just-in-time Kite access token for personal use (ARC-06 §5).

The token lives in a local file written by `scripts/kite_login.py` (mode 0600, gitignored). It is read on
each call, never cached on an object, logged or put in a job payload. The file is valid until the next
~06:00 IST after it was written (assumed daily expiry, not yet observed: OQ-INT-01).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from app.providers.base import ProviderAuthExpired

IST = ZoneInfo("Asia/Kolkata")
EXPIRY = time(6, 0)


def next_expiry(written_at: datetime) -> datetime:
    """The first 06:00 IST strictly after `written_at`."""
    local = written_at.astimezone(IST)
    candidate = datetime.combine(local.date(), EXPIRY, IST)
    return candidate if candidate > local else candidate + timedelta(days=1)


class FileTokenSupplier:
    """Callable `() -> str`, usable as `ProviderContext.credentials_supplier`."""

    def __init__(self, path: Path, now: Callable[[], datetime] = lambda: datetime.now(UTC)) -> None:
        self._path, self._now = path, now

    def __call__(self) -> str:
        if not self._path.is_file():
            raise ProviderAuthExpired("no Kite token file; run scripts/kite_login.py")
        written = datetime.fromtimestamp(self._path.stat().st_mtime, UTC)
        if self._now() >= next_expiry(written):
            raise ProviderAuthExpired("Kite token expired; run scripts/kite_login.py")
        token = self._path.read_text(encoding="utf-8").strip()
        if not token:
            raise ProviderAuthExpired("Kite token file is empty")
        return token
