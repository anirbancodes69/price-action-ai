# Security Architecture

| Field | Value |
|---|---|
| Document ID | ARC-06 |
| Version | 0.1.0 |
| Status | Specification ready |
| Owner | Solution Architect (security) |
| Last updated | 2026-11-15 |
| Related | [ARC-01 Auth boundaries](01_SYSTEM_ARCHITECTURE.md#8-authentication-boundaries) · [ARC-03](03_DATABASE_DESIGN.md) · [ARC-04](04_API_SPECIFICATION.md) · [ARC-08](08_INTEGRATION_ARCHITECTURE.md) · [OPS-02 Secrets](../operations/02_ENVIRONMENT_CONFIGURATION.md) · [OPS-05 Compliance](../operations/05_COMPLIANCE_AND_RISK_CONSIDERATIONS.md) |

## 1. Purpose and threat model summary

Defines security controls for PriceAction AI. Assets in priority order: (1) broker access tokens, (2) user credentials and PII, (3) users' trading records and capital figures, (4) licensed market data (redistribution risk), (5) integrity of analysis outputs.

| Threat | Primary controls |
|---|---|
| Broker token theft | Server-side custody, encryption at rest, never sent to browser, JIT fetch by workers, short-lived in memory, audit |
| Account takeover | Strong hashing, rate-limited login, session rotation, password reset revocation, optional 2FA (future) |
| Cross-tenant data access | Tenant scoping, 404 on foreign IDs, automated isolation tests, RLS (M10) |
| Data redistribution violation | Data-source isolation by mode, export controls, entitlement checks |
| Tampered/incorrect analysis | Deterministic engine, immutable snapshots, result hashes, LLM cannot change numbers |
| Prompt injection via user questions | LLM has no tools/side effects; output validation; context only from DB |
| Secret leakage via repo/CI | Secret scanning, `.env` never committed, GitHub Environments |
| SSRF / internal exposure | Engine/DB/Redis not publicly exposed; outbound allow-list for workers (Kite, LLM) |

## 2. Authentication

| Control | Specification |
|---|---|
| Mechanism | Laravel Sanctum SPA session cookies ([ARC-04 §2.2](04_API_SPECIFICATION.md#22-authentication)). No tokens in `localStorage`. |
| Password hashing | Laravel `Hash` with Argon2id (or bcrypt cost ≥ 12 if Argon2 unavailable). |
| Password policy | ≥ 8 chars, ≥ 1 letter and 1 digit (matches current frontend `validatePassword(strict)`), checked against a breached-password list (`Password::uncompromised()`). |
| Login protection | Rate limit 5/min per IP+email; generic error messages; lockout notification email after 10 failures/hour. |
| Session | Redis store; `HttpOnly; Secure; SameSite=Lax`; idle timeout 7 days with "remember me", 12 h without; session ID regenerated on login and privilege change. |
| Password reset | Single-use token, 60-minute expiry, all sessions revoked on reset. |
| Email verification | Required before accessing tenant data. |
| CSRF | Sanctum XSRF cookie/header on all mutating requests. |
| 2FA | Future scope (TOTP); required before SaaS GA (release gate in [PRD-02 BRD](../product/02_BRD.md)). |

Current frontend state: the login page accepts any syntactically valid email/password and routes to `/dashboard`; there is no route protection. This is **demo-only behaviour** and must be replaced in M7 (Next.js middleware/proxy redirecting unauthenticated users using `/api/v1/me`).

## 3. Authorization (RBAC)

Roles per tenant membership: `OWNER`, `ADMIN`, `MEMBER`, `VIEWER`. Platform flag `is_platform_admin` for operator-only endpoints (Horizon, ingestion admin). Laravel Policies implement the matrix; every controller action calls `authorize()`.

| Permission | OWNER | ADMIN | MEMBER | VIEWER |
|---|---|---|---|---|
| Read tenant analysis, scanner, watchlists | ✔ | ✔ | ✔ | ✔ |
| Manage own watchlists, plans, paper/actual trades, journal | ✔ | ✔ | ✔ | — |
| Run backtests, AI explanations (subject to entitlement) | ✔ | ✔ | ✔ | — |
| Change risk profile (own) | ✔ | ✔ | ✔ | — |
| Select data source, trigger personal sync | ✔ | ✔ | — | — |
| Connect/disconnect broker | ✔ | — | — | — |
| Manage memberships | ✔ | ✔ | — | — |
| Delete tenant/account | ✔ | — | — | — |

In MVP all tenants are `PERSONAL` with a single `OWNER`. Entitlements are an orthogonal check (`EntitlementGate::allows($tenant, 'feature')`).

## 4. Tenant isolation

1. Every tenant-owned model uses a `BelongsToTenant` trait adding a global scope `where tenant_id = current tenant` and setting `tenant_id` on create.
2. Route model binding resolves only within the tenant → foreign IDs produce 404.
3. Market-data access goes through a `DataSourceAccess` service that returns the set of data source IDs a tenant may read (entitled global sources + its own personal sources). Analysis and candle queries must include `data_source_id IN (...)`.
4. Engine-worker jobs carry `tenant_id` and must include it in every tenant-scoped query; Python repository functions require `tenant_id` as a mandatory parameter.
5. Automated tests: for every tenant-scoped endpoint, a feature test creates two tenants and asserts 404 cross-access (generated test matrix, CI-required).
6. M10: PostgreSQL RLS on tenant-owned tables as defense in depth ([ARC-03 §9](03_DATABASE_DESIGN.md#9-tenant-isolation-in-the-schema)).

## 5. Broker credential protection (Zerodha)

| Rule | Detail |
|---|---|
| Never collected | Zerodha user ID password, TOTP/2FA codes, PIN. The user authenticates only on Zerodha's own login page (Kite Connect login flow). |
| `request_token` | Received on the callback, exchanged server-side within the same request together with the app's `api_secret` checksum, then discarded. Never logged. |
| `api_key` / `api_secret` | Deployment secrets (env / secret store), never in the database for platform-app mode, never in frontend bundles. |
| `access_token` | Encrypted at rest in `provider_connections.access_token_encrypted` using a dedicated key `PROVIDER_TOKEN_KEY` (AES-256-GCM via Laravel encrypter instance), with `key_version` for rotation. |
| Exposure | Never returned by any public API (only status and masked user id). Never sent to the frontend, engine API payloads, Redis job payloads or logs. |
| Worker access | engine-worker fetches the token just-in-time from `GET /internal/v1/provider-connections/{id}/access-token` (service-token authenticated, network-restricted, audited, rate-limited), holds it in memory for the duration of the job only. |
| Expiry | Kite access tokens expire daily (provider behaviour — verify in M2). Connection status becomes `EXPIRED`; user is notified to reconnect. No automated re-login (that would require storing credentials, which is forbidden). |
| Disconnect | Token deleted; provider-side invalidation called where the API supports it; audit entry. |
| Log redaction | Monolog/structlog processors redact keys matching `token|secret|password|authorization|api_key|request_token`. |

## 6. Encryption and database privileges

- In transit: TLS at the edge (HSTS, TLS 1.2+); internal Docker network traffic is plaintext on a private bridge network in single-host deployments (accepted risk, documented); managed Postgres connections use `sslmode=require`.
- At rest: managed disk encryption for DB volumes/backups; application-level encryption for tokens (above). Backups encrypted ([OPS-04](../operations/04_DATA_RETENTION_AND_BACKUP.md)).
- Postgres roles: `app_backend` (DML on Laravel-owned tables, SELECT on engine-owned), `app_engine` (DML on engine-owned tables, SELECT on needed Laravel tables, UPDATE on `trade_plans.status`-related columns and paper tables), `app_migrator` (DDL, used only by the migration step), `app_readonly` (support/analytics). No role besides migrator has DDL.

## 7. Secret management

| Environment | Store |
|---|---|
| Local | `.env` files from `.env.example` templates; `.env*` gitignored |
| CI | GitHub Actions secrets (minimal; CI uses ephemeral generated keys and no real provider credentials) |
| Staging/Production | GitHub Environments secrets injected at deploy into server-side env files with `0600` permissions, or a secret manager if the host provides one (OQ-SEC-02) |

Rotation: `APP_KEY` (with `APP_PREVIOUS_KEYS`), `PROVIDER_TOKEN_KEY` (versioned re-encryption job), `ENGINE_SERVICE_TOKEN` and `BACKEND_INTERNAL_TOKEN` (dual-token acceptance window), LLM API keys. Variable inventory in [OPS-02](../operations/02_ENVIRONMENT_CONFIGURATION.md).

## 8. API security

- Input validation with Laravel Form Requests on every endpoint; engine validates with Pydantic (defense in depth).
- Output: API Resources whitelist fields (no mass exposure of model attributes).
- Mass assignment protection (`$fillable`), no raw SQL with interpolated input.
- Security headers on frontend responses: CSP (scripts self + required hashes; no inline eval), `X-Content-Type-Options`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy`, `frame-ancestors 'none'`. The existing theme bootstrap inline script (`ThemeScript`) needs a CSP hash/nonce.
- CORS: not needed (same-origin via rewrite); if enabled, explicit origin allow-list.
- Internal endpoints (`/internal/v1/*`) are served on a separate route group that rejects requests not coming from the internal network and lacking the service token.
- File uploads: none in MVP (journal screenshots are future scope; will require type sniffing, size caps, private storage).

## 9. Rate limiting

Defined in [ARC-04 §2.7](04_API_SPECIFICATION.md#27-rate-limits-defaults-per-user-unless-stated), implemented with Laravel `RateLimiter` on Redis. Outbound provider rate limits are enforced by the provider adapter ([ARC-08 §4](08_INTEGRATION_ARCHITECTURE.md)). LLM spend is capped per tenant/day and globally ([ARC-07 §9](07_AI_AND_LLM_ARCHITECTURE.md)).

## 10. Audit logging

Audited actions (minimum): login success/failure, logout, password change/reset, email verification, risk profile change, data-source selection, broker connect/disconnect/token fetch by service, trade plan create/edit/cancel, paper trade stop move/close, actual trade/fill create, journal edit, backtest create, entitlement change, account deletion request, admin actions. Stored in `audit_logs` (append-only; [ARC-03 §4.6](03_DATABASE_DESIGN.md)). Secrets are redacted from `changes`.

## 11. Data access boundaries

| Data | Frontend (browser) | Laravel | Engine API | engine-worker | LLM provider |
|---|---|---|---|---|---|
| Passwords | Entered only | Hash only | ✘ | ✘ | ✘ |
| Broker access token | ✘ | ✔ (encrypted) | ✘ | JIT, memory only | ✘ |
| Kite api_secret | ✘ | ✔ (env) | ✘ | ✘ | ✘ |
| User email/name | Own only | ✔ | ✘ | ✘ | ✘ |
| Capital, risk profile | Own only | ✔ | Values for calculation | Values for paper/backtest | ✘ |
| Analysis results | ✔ (entitled sources) | ✔ | ✔ | ✔ | Only the specific run's facts, no PII |
| Candles | Via API (entitled) | ✔ | ✔ | ✔ | Summary facts only, never bulk data |

The LLM context contains **no PII** (no email, name, capital) and no bulk candle data — only the analysis facts needed for the explanation ([ARC-07 §4](07_AI_AND_LLM_ARCHITECTURE.md)).

## 12. Data retention and backup

See [OPS-04](../operations/04_DATA_RETENTION_AND_BACKUP.md). Security-relevant points: tokens deleted on disconnect and on account deletion; audit logs retained 2 years; backups encrypted and access-restricted; restore tested quarterly ([OPS-06](../operations/06_DISASTER_RECOVERY.md)).

## 13. Security in CI

Dependency scanning, secret scanning, SAST and container scanning — [ENG-10 §8](../engineering/10_GITHUB_ACTIONS_CI_CD.md).

## 14. Open questions

| ID | Question |
|---|---|
| OQ-SEC-01 | Kite app model: single platform app (users authorise it) vs bring-your-own api_key per user. Affects token custody and terms compliance; see OPS-05. |
| OQ-SEC-02 | Secret manager for production (host-provided vs SOPS-encrypted files vs GitHub Environments only). |
| OQ-SEC-03 | When to make 2FA mandatory (proposed: before any non-owner user is onboarded). |
