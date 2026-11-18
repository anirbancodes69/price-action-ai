"""arq worker configuration (docs/engineering/04_PYTHON_ENGINE_ARCHITECTURE.md §7).

M0 registers only a heartbeat job so the worker container and `arq --check` health probe can be
verified. Ingestion, analysis, backtest, paper and AI jobs are added in M2-M9.
"""

import logging
from typing import Any, ClassVar

from arq import cron
from arq.connections import RedisSettings

from app.logging import configure_logging
from app.settings import get_settings
from app.workers.ingest import ingest_tick

configure_logging("engine-worker")
log = logging.getLogger(__name__)


async def ping(ctx: dict[str, Any]) -> str:
    log.info("worker_ping", extra={"job_id": ctx.get("job_id")})
    return "pong"


async def startup(ctx: dict[str, Any]) -> None:
    log.info("worker_started")


class WorkerSettings:
    functions: ClassVar[list[Any]] = [ping, ingest_tick]
    # Every minute: the market calendar in Postgres decides whether a bar is due (cheap when nothing is).
    cron_jobs: ClassVar[list[Any]] = [cron(ingest_tick, second=10, timeout=240, max_tries=1, unique=True)]
    on_startup = startup
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url.get_secret_value())
    health_check_interval = 30
