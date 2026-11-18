"""FastAPI internal service entry point.

Internal only: bound to the Docker network, never exposed publicly (ARC-01 §8).
Risk (T-I76/T-I77), scan and analysis detail are live; /jobs and analysis persistence are not built.
"""

from fastapi import APIRouter, Depends, FastAPI

from app import __version__
from app.api import health, risk, scan
from app.api.security import require_service_token
from app.logging import configure_logging
from app.settings import get_settings

configure_logging("engine")

app = FastAPI(
    title="PriceAction AI engine (internal)",
    version=__version__,
    docs_url="/docs" if get_settings().app_env == "local" else None,
    redoc_url=None,
    openapi_url="/openapi.json" if get_settings().app_env == "local" else None,
)
app.include_router(health.router)

internal = APIRouter(prefix="/internal/v1", dependencies=[Depends(require_service_token)])


@internal.get("/ping")
async def ping() -> dict[str, str]:
    """Authenticated connectivity check used by the backend health probe."""
    settings = get_settings()
    return {"status": "ok", "engine_version": __version__, "ruleset": settings.active_ruleset}


internal.include_router(risk.router)
internal.include_router(scan.router)
app.include_router(internal)
