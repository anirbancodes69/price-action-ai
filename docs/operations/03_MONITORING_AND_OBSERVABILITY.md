# Monitoring and Observability

| Field | Value |
|---|---|
| Document ID | OPS-03 |
| Version | 0.1.0 |
| Status | Specification ready (tool choice pending OQ-MON-01) |
| Owner | DevOps / Technical Lead |
| Last updated | 2026-11-15 |
| Related | [ENG-06 Logging](../engineering/06_ERROR_HANDLING_AND_LOGGING.md) · [OPS-01 Health checks](01_DEPLOYMENT_GUIDE.md#5-health-checks) · [PRD-02 Success metrics](../product/02_BRD.md#9-success-metrics) |

## 1. Purpose

What is measured, where it is visible and what alerts the owner, at both application and infrastructure level, sized for a single-host personal deployment that can grow.

## 2. Signals

| Signal | Source | Destination (proposed) |
|---|---|---|
| Logs | JSON stdout (ENG-06) | Docker json-file with rotation → optional Loki/Grafana or hosted log service |
| Metrics | Laravel (Prometheus exporter or custom `/metrics` behind auth), FastAPI (`prometheus-client`), node-exporter, postgres-exporter, redis-exporter | Prometheus + Grafana (self-hosted on the same VM) **or** hosted equivalent |
| Errors | All services | Sentry (hosted) or GlitchTip (self-hosted) |
| Uptime | External probe of `/api/health?deep=1` and `/login` | Uptime monitoring service |
| Business pipeline status | `ingestion_runs`, `analysis_batches`, `backtest_runs` tables | Grafana panels via Postgres datasource (read-only role) |

## 3. Key metrics

### 3.1 Application

| Metric | Type | Labels |
|---|---|---|
| `http_requests_total`, `http_request_duration_seconds` | counter / histogram | service, route, status |
| `engine_sync_call_duration_seconds` | histogram | endpoint |
| `engine_unavailable_total` | counter | — |
| `queue_jobs_total`, `queue_job_duration_seconds`, `queue_depth` | counter / histogram / gauge | queue, job, outcome |
| `ingestion_run_duration_seconds`, `ingestion_instruments_failed_total` | histogram / counter | data_source_mode |
| `provider_requests_total`, `provider_rate_limited_total` | counter | provider, status |
| `data_quality_issues_total` | counter | type, severity |
| `analysis_batch_duration_seconds`, `analysis_runs_total` | histogram / counter | status |
| `determinism_mismatch_total` | counter | — |
| `paper_eod_transitions_total` | counter | transition |
| `llm_requests_total`, `llm_validation_rejections_total`, `llm_cost_usd_total` | counter | outcome, model |
| `auth_failures_total`, `rate_limited_total` | counter | bucket |
| `provider_token_fetch_total` | counter | outcome |

### 3.2 Infrastructure

CPU, memory, disk usage and I/O, container restarts, Postgres connections/locks/replication (if any)/database size, Redis memory and evictions, backup job success and age.

## 4. Alerts

| Alert | Condition | Severity |
|---|---|---|
| EOD pipeline not completed | No `analysis_batches` COMPLETED/PARTIAL for last trading day by 20:00 IST | High |
| Ingestion failed | `ingestion_runs.status = FAILED` | High |
| Provider token expired | Connection `EXPIRED` before pipeline | Medium (user notification also sent) |
| Determinism mismatch | `determinism_mismatch_total` increases | High |
| Engine down | `/ready` failing > 2 min | High |
| Error rate | 5xx > 2% over 10 min | High |
| Queue backlog | `queue_depth{queue="analysis"}` > 1000 for 15 min | Medium |
| Disk | > 80% used | Medium; > 90% High |
| Backup | Last successful backup > 26 h old | High |
| LLM spend | > 80% of daily budget | Low |
| Security | Spike in `auth_failures_total`; unexpected `provider_token_fetch_total` outside job windows | Medium |

Alert channel: email + mobile push via the monitoring tool (personal phase). Each alert links to a runbook section in [OPS-06](06_DISASTER_RECOVERY.md) or this document.

## 5. Dashboards

1. **Daily pipeline:** ingestion runs, issues by type, analysis batch duration/status, paper EOD transitions.
2. **API health:** request rate, latency percentiles, error codes, engine call latency.
3. **Workers:** queue depth, job durations, failures.
4. **Infrastructure:** host and container resources, Postgres, Redis.
5. **AI:** requests, validation rejection rate, fallback rate, cost.

## 6. Determinism monitor

Nightly job re-runs analysis for a random sample of 20 instruments from the latest batch using the stored snapshot and ruleset and compares `result_hash`. Any mismatch is a High alert and blocks ruleset promotions until explained.

## 7. Open questions

| ID | Question |
|---|---|
| OQ-MON-01 | Self-hosted Prometheus/Grafana/GlitchTip vs hosted services (cost vs maintenance). |
