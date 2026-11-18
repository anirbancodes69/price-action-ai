"""Engine configuration (see docs/operations/02_ENVIRONMENT_CONFIGURATION.md §2.4)."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    database_url: SecretStr = SecretStr("")
    redis_url: SecretStr = SecretStr("redis://redis:6379/0")
    engine_service_token: SecretStr = SecretStr("")
    engine_service_token_previous: SecretStr = SecretStr("")
    active_ruleset: str = "pa-core@0.1.0"
    readiness_timeout_s: float = 2.0
    # Intraday ingestion (ENG-05 §12). Personal mode: one data source, a local Kite token file.
    ingest_enabled: bool = False
    ingest_provider: str = "KITE"  # KITE or DEMO
    ingest_data_source_id: str = ""
    ingest_universe_code: str = "NIFTY50"
    kite_api_key: SecretStr = SecretStr("")
    kite_token_file: str = ".kite_token"  # noqa: S105 - a path, not a secret


@lru_cache
def get_settings() -> Settings:
    return Settings()
