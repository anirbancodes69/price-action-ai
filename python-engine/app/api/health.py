"""Liveness and readiness probes (docs/operations/01_DEPLOYMENT_GUIDE.md §5)."""

import asyncio
from typing import Annotated, Any

import psycopg
import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.settings import Settings, get_settings

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    """Process is up. No dependency checks."""
    return {"status": "ok", "service": "engine"}


async def _check_db(settings: Settings) -> bool:
    url = settings.database_url.get_secret_value()
    if not url:
        return False
    try:
        async with await psycopg.AsyncConnection.connect(
            url, connect_timeout=int(settings.readiness_timeout_s) or 1
        ) as conn:
            await conn.execute("SELECT 1")
        return True
    except Exception:
        return False


async def _check_redis(settings: Settings) -> bool:
    client = aioredis.Redis.from_url(
        settings.redis_url.get_secret_value(), socket_connect_timeout=settings.readiness_timeout_s
    )
    try:
        return bool(await client.ping())
    except Exception:
        return False
    finally:
        await client.aclose()


@router.get("/ready")
async def ready(settings: Annotated[Settings, Depends(get_settings)]) -> JSONResponse:
    """Ready to serve: PostgreSQL and Redis reachable."""
    db_ok, redis_ok = await asyncio.gather(_check_db(settings), _check_redis(settings))
    body: dict[str, Any] = {
        "status": "ok" if db_ok and redis_ok else "degraded",
        "checks": {"database": db_ok, "redis": redis_ok},
    }
    return JSONResponse(body, status_code=200 if db_ok and redis_ok else 503)
