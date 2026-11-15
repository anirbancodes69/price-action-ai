"""Service-token authentication for /internal/v1 (docs/architecture/01_SYSTEM_ARCHITECTURE.md §7)."""

import hmac
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.settings import Settings, get_settings

_bearer = HTTPBearer(auto_error=False)


def require_service_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """Accept the current token or, during rotation, the previous one. Constant-time comparison."""
    accepted = [
        t.get_secret_value()
        for t in (settings.engine_service_token, settings.engine_service_token_previous)
        if t.get_secret_value()
    ]
    if not accepted:
        # Fail closed: an unconfigured engine must not serve internal endpoints.
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="SERVICE_TOKEN_NOT_CONFIGURED")
    presented = credentials.credentials if credentials else ""
    if not any(hmac.compare_digest(presented, t) for t in accepted):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="UNAUTHENTICATED")
