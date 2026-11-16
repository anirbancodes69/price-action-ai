---
name: security-guardrails
description: Security workflow for PriceAction AI - Zerodha Kite credential and access-token custody, secrets and .env handling, log redaction, Laravel Sanctum authentication, RBAC policies, tenant isolation and data-source access, internal service-token endpoints, Postgres role grants, API input validation and output whitelisting, rate limits, audit logging, dependency and secret scanning. Use when touching auth, sessions, tokens, provider connections, environment variables, logging, internal endpoints, DB roles or grants, tenant-scoped queries, Dockerfiles exposing ports, CI secrets, or dependency upgrades, and when asked for a security review of PriceAction AI changes.
---

# Security guardrails

Protects, in priority order: broker access tokens, user credentials and PII, users' trading records and capital, licensed market data, and the integrity of analysis outputs ([ARC-06 §1](../../../docs/architecture/06_SECURITY_ARCHITECTURE.md#1-purpose-and-threat-model-summary)). ARC-06 is the authority. This skill is the checklist for applying it.

> Current state: implemented today are the `.env` / `.env.example` split with generated dev secrets (`scripts/setup-env.sh`), log redaction in Laravel (`app/Logging/RedactSensitiveData.php`) and the engine (`app/logging.py`), the service-token-protected `/internal/v1/ping`, the `audit_logs` table (append-only grants when roles exist), gitleaks plus dependency audits in CI, and GitHub secret scanning. **Not yet:** Sanctum auth, policies, tenant scoping traits, provider connections, the JIT token endpoint, per-table grants (T-101d), rate limiting, CSP.

## Required context

Read the ARC-06 section for the area you touch:

| Area | ARC-06 section |
|---|---|
| Login, sessions, CSRF, password rules | §2 |
| Roles and policies | §3 (plus the [ARC-04 §15](../../../docs/architecture/04_API_SPECIFICATION.md#15-authorization-matrix-summary) matrix) |
| Tenant scoping, data-source access | §4, [ADR-011](../../../docs/adr/ADR-011-DATA-MODES-AND-TENANT-ISOLATION.md) |
| Kite tokens | §5, [ARC-08 §4.1–4.2](../../../docs/architecture/08_INTEGRATION_ARCHITECTURE.md#41-authentication-flow) |
| DB roles, encryption | §6 |
| Secrets and rotation | §7, [OPS-02](../../../docs/operations/02_ENVIRONMENT_CONFIGURATION.md) |
| Input and output, headers, internal routes | §8 |
| Audit events | §10 |
| What data may reach which component | §11 |
| Logging and redaction | [ENG-06 §5](../../../docs/engineering/06_ERROR_HANDLING_AND_LOGGING.md#5-redaction-mandatory) |

## Checklist

**Credentials and secrets**
- [ ] No Zerodha password, PIN or 2FA code is collected, ever. `request_token` is exchanged server-side in the same request, then discarded.
- [ ] The access token is encrypted with `PROVIDER_TOKEN_KEY` (versioned). It never appears in API responses, frontend code, engine payloads, Redis/job payloads or logs. Workers fetch it just in time and keep it in memory.
- [ ] No secret in the repo, fixtures, tests, Docker images or CI logs. New variables are added to `.env.example` as placeholders and to OPS-02. Real `.env` is never read into output or committed.
- [ ] Log redaction covers any new sensitive key, with a test that logs a secret and asserts it is redacted.

**Access control**
- [ ] Every tenant-owned query is tenant-scoped. Foreign IDs return 404. There is a two-tenant test per endpoint.
- [ ] Market-data reads are restricted to the tenant's permitted `data_source_id`s. PERSONAL data never crosses tenants.
- [ ] Every controller action authorises via policy. Entitlements are checked separately.
- [ ] `/internal/v1/*` requires the service token and is not reachable from the public network. Engine, DB and Redis ports are not published beyond localhost in dev.
- [ ] Postgres grants follow writers (ARC-01 §6) and roles (ARC-06 §6). Only `app_migrator` has DDL.

**API hygiene**
- [ ] Input is validated (Form Requests, Pydantic). Output goes through whitelisting Resources. No mass assignment, no interpolated SQL.
- [ ] Mutations that matter emit audit events (ARC-06 §10) with secrets redacted from `changes`.
- [ ] Client-supplied quantity or levels are never trusted (TV-API-01). The LLM receives no PII (ARC-06 §11).

**Supply chain**
- [ ] New dependencies are justified, pinned via lockfiles, and pass the CI audits. Third-party GitHub Actions (anything not under `actions/`) are pinned by 40-character commit SHA with a `# vX.Y.Z` comment; Dependabot updates both (T-901).

## Constraints

- Defensive review only. Never print, copy or exfiltrate real secrets found during review: report the location and recommend rotation.
- Do not weaken a control to make a test pass. Changing a security decision follows CLAUDE.md §8 (a new ADR).

## Deliverables

Findings ranked by severity (file:line, scenario, fix), tests added, and ARC-06 / OPS-02 / ENG-06 updates if controls changed, via the `docs-sync` skill. For a broad audit of pending branch changes, the built-in `/security-review` command complements this checklist.
