# Disaster Recovery

| Field | Value |
|---|---|
| Document ID | OPS-06 |
| Version | 0.1.0 |
| Status | Specification ready |
| Owner | DevOps / Technical Lead |
| Last updated | 2026-11-15 |
| Related | [OPS-04 Backup](04_DATA_RETENTION_AND_BACKUP.md) · [OPS-01 Rollback](01_DEPLOYMENT_GUIDE.md#6-rollback) · [OPS-03 Alerts](03_MONITORING_AND_OBSERVABILITY.md#4-alerts) |

## 1. Objectives

| Phase | RPO | RTO | Rationale |
|---|---|---|---|
| Personal (G1) | 24 h (≤ 5 min with WAL archiving) | 8 h | Single owner; market data re-fetchable; plans/journal are the irreplaceable data |
| Beta / SaaS (G2/G3) | ≤ 15 min | ≤ 4 h | Multiple users; revisit with managed PG and standby |

Market data and analysis are **reconstructable** (re-ingest + re-analyse; analysis is deterministic). User-entered data (plans, actual trades, journal, settings) and audit logs are not — they drive the RPO.

## 2. Scenarios and runbooks

### 2.1 Host loss (VM destroyed or unrecoverable)

1. Provision new VM (OPS-01 §3); install Docker; restore env files from GitHub Environment secrets.
2. Restore PostgreSQL from latest backup + WAL to the latest point (or managed PG unaffected).
3. Deploy last released version via deploy workflow (images from GHCR).
4. Verify health; run `ingest` for missed trading days (backfill window) and `analyse_batch`; run paper EOD for missed days **in date order** (idempotent).
5. Update DNS if IP changed. Post-incident note.

### 2.2 Database corruption or bad migration

1. Stop writers (`backend`, `backend-queue`, `engine-worker`, scheduler).
2. Restore to a point before the incident (PITR) into a new database; validate (row counts, latest plans/journal timestamps).
3. Switch connection strings; redeploy previous app version if the cause was a release.
4. Re-run EOD pipeline for affected days.

### 2.3 Redis loss

Restart Redis (AOF). If data lost: sessions invalidated (users log in again), queued jobs lost → re-trigger EOD pipeline for the day (idempotent), rate-limit counters reset (acceptable).

### 2.4 Provider outage (Kite)

No DR action; ingestion runs fail/partial, users see "Data delayed". Pipeline retries next scheduled run; manual `market-data/sync` after recovery.

### 2.5 Secret compromise

Rotate affected secrets (ARC-06 §7): `PROVIDER_TOKEN_KEY` → re-encrypt and force reconnect of broker connections (revoke tokens); service tokens → dual-token rotation; `APP_KEY` → rotate with previous keys; LLM/Kite keys → regenerate at provider. Review audit logs for misuse; notify affected users if personal data exposure is possible (OPS-05 §4).

### 2.6 Accidental data deletion by user

Not restorable per-user from backups in MVP without full restore; journal/plan deletion endpoints do not exist (records change status instead), limiting exposure.

## 3. DR drills

| Drill | Frequency | Success criteria |
|---|---|---|
| Automated restore test | Weekly | Restore + sanity queries pass |
| Full host recovery on a scratch VM | Quarterly (from G1) | Service up within RTO, data within RPO |
| Secret rotation rehearsal | Semi-annual | No downtime beyond planned |

Results recorded in `docs/operations/dr-log.md` (created at first drill).

## 4. Dependencies for recovery

GitHub (code, images, secrets), backup storage credentials (stored separately from the VM, e.g. owner's password manager), DNS provider access, Kite developer console access (redirect URL updates).
