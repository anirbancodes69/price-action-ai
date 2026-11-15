# ADR-012: GitHub Actions for CI/CD

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-11-15 |
| Deciders | Product owner / Technical lead |
| Version | 1.0 |
| Related | [ENG-10](../engineering/10_GITHUB_ACTIONS_CI_CD.md) · [ENG-09](../engineering/09_GITHUB_REPOSITORY_STRATEGY.md) · [ENG-11](../engineering/11_BRANCHING_AND_RELEASE_STRATEGY.md) |

## Context

Source control is GitHub. The project needs multi-language CI (TS, PHP, Python), service containers (PostgreSQL, Redis), Docker builds, security scanning and gated deployments, with minimal maintenance.

## Decision

Use **GitHub Actions** with GitHub-hosted runners as the mandatory CI/CD platform: a coordinator workflow (`ci.yml`) with path detection invoking reusable component workflows and a single required `ci-gate` check; images published to GHCR; staging auto-deploy; production deploy via manual dispatch with GitHub Environment approval. Third-party actions pinned by SHA; minimal `GITHUB_TOKEN` permissions.

## Alternatives considered

| Alternative | Why not chosen |
|---|---|
| GitLab CI / CircleCI / Jenkins | Capable, but adds another platform or self-hosting burden while code lives on GitHub. |
| Self-hosted runners | Faster/cheaper at scale; unnecessary now and adds security maintenance. |

## Consequences

+ Tight integration with PRs, branch protection, environments, secret scanning, Dependabot, CodeQL, GHCR.
− Hosted-runner minutes and cache limits apply; Docker builds rely on GHA cache.

## Status

Accepted on 2026-11-15. Superseding requires a new ADR referencing this one.
