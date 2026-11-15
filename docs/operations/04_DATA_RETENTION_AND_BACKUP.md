# Data Retention and Backup

| Field | Value |
|---|---|
| Document ID | OPS-04 |
| Version | 0.1.0 |
| Status | Specification ready (retention periods need owner/legal confirmation) |
| Owner | DevOps / Product Owner |
| Last updated | 2026-11-15 |
| Related | [ARC-03 per-table retention](../architecture/03_DATABASE_DESIGN.md) · [OPS-06 DR](06_DISASTER_RECOVERY.md) · [OPS-05 Compliance](05_COMPLIANCE_AND_RISK_CONSIDERATIONS.md) |

## 1. Retention schedule

> **ASSUMPTION:** periods below are engineering proposals; confirm against legal advice (data protection law, provider terms) before Phase B (OQ-RET-01).

| Data | Retention | Deletion mechanism |
|---|---|---|
| Users, profiles, preferences, risk profiles | Life of account; PII purged 30 days after deletion request | `retention:run` job; anonymise audit references |
| Provider access tokens | Until disconnect, expiry cleanup or account deletion — deleted immediately | Disconnect handler; daily sweep of expired tokens > 7 days |
| Trade plans, paper/actual trades, journal | Life of account | Deleted with account (after 30-day grace) |
| Audit logs | 2 years online, then archived to encrypted cold storage for 3 more years, then deleted | Monthly partition detach + export |
| Candles — PERSONAL source | While the tenant exists **and** permitted by provider terms (OQ-RET-02); deleted on account deletion or explicit request | Cascade by data source |
| Candles — LICENSED | Per licence terms | Vendor-specific |
| Candles — DEMO | Regenerable; no retention concern | — |
| Candle snapshots | While referenced by an analysis run that is retained | Weekly GC of unreferenced snapshots |
| Analysis runs + children | Latest run per instrument indefinitely; history 2 years, except runs referenced by plans, explanations or backtests (kept with them) | Monthly purge job |
| AI explanations | 1 year | Monthly purge |
| Backtests | `USER` 1 year; `EXPLORATION`/`OOS`/`HOLDOUT` indefinitely (validation evidence) | Monthly purge |
| Ingestion runs, data quality issues | 1 year | Monthly purge |
| Notifications | 180 days | Daily purge |
| Application logs | 14 days on host (rotation), 30 days in log service | Rotation/TTL |
| Redis data | Ephemeral (cache, queues, sessions, job status 24 h) | TTLs |

## 2. Backups

| Item | Method | Frequency | Retention | Location |
|---|---|---|---|---|
| PostgreSQL | Managed service PITR **or** `pg_dump -Fc` + WAL archiving (pgBackRest/WAL-G) for self-hosted | Continuous WAL + daily full | 7 daily, 4 weekly, 3 monthly | Off-host object storage, encrypted (server-side + client-side key) |
| Pre-deploy snapshot | `pg_dump -Fc` | Each production deploy | 14 days | Same |
| Env files / secrets | Stored in GitHub Environments (source of truth) | On change | — | GitHub |
| Redis | **Not backed up** (reconstructable); AOF `everysec` enabled to survive restarts without losing queued jobs | — | — | Local volume |
| Code / images | GitHub + GHCR | — | — | GitHub |

Redis persistence: AOF with `everysec` limits queued-job loss to ~1 s on crash; arq/Horizon jobs are idempotent and the EOD pipeline can be re-triggered, so loss is recoverable.

## 3. Backup verification

- Automated weekly restore of the latest backup into a scratch container, run migrations status check and row-count sanity queries; alert on failure.
- Quarterly full restore drill (OPS-06).
- Backup age alert at 26 h (OPS-03).

## 4. Deletion requests

Account deletion (API A12): immediate token deletion and session revocation; 30-day grace; then hard-delete tenant-owned rows and personal data source candles; audit entries retained with actor pseudonymised. Backups age out per schedule (deleted data disappears from backups within 3 months — documented in privacy policy).

## 5. Open questions

| ID | Question |
|---|---|
| OQ-RET-01 | Legal confirmation of retention periods and privacy policy wording (India's Digital Personal Data Protection framework). |
| OQ-RET-02 | Whether provider terms limit storage duration of personally fetched historical data. |
