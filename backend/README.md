# PriceAction AI — Laravel backend

Modular-monolith application backend: identity, tenants, onboarding, plans, journal, notifications
and the public REST API under `/api/v1`. Specification:
[docs/engineering/03_BACKEND_ARCHITECTURE.md](../docs/engineering/03_BACKEND_ARCHITECTURE.md).

Status (M0): Laravel 13 skeleton. `GET /api/health` (shallow) and `?deep=1` (PostgreSQL, Redis,
engine ping), JSON logs with secret redaction. The default skeleton migrations
(users/cache/jobs) are placeholders and are replaced by the ARC-03 schema in M1.

```bash
make test-backend    # vendor/bin/phpunit inside the dev container
make lint-backend    # Pint
make migrate         # runs as the schema-owner role app_migrator
```
