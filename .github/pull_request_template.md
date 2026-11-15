## Summary
<!-- What changes and why. Link the spec section(s) this implements, e.g. TRD-04 §3, ARC-04 T2. -->

Closes #<!-- issue -->  <!-- or: add label `no-issue` and explain why -->

## Type
- [ ] feat  - [ ] fix  - [ ] refactor  - [ ] docs  - [ ] chore/ci/build  - [ ] ruleset change

## Testing evidence
<!-- Commands run, new/updated tests, screenshots for UI, sample outputs for engine changes. -->

## Checklist
- [ ] Tests added/updated; CI green
- [ ] Documentation updated (authoritative doc in `docs/`; DOCUMENTATION_STATUS if status changed)
- [ ] Feature catalog status updated (PRD-06) if a feature changed state
- [ ] **Migrations:** none / reviewed (backward compatible with previous release, expand→contract, no long locks)
- [ ] **API compatibility:** none / additive only / breaking (requires /v2 + ADR)
- [ ] **Contracts regenerated** (OpenAPI / engine schemas) if changed
- [ ] **Ruleset:** golden outputs unchanged, or ruleset version bumped + CHANGELOG entry
- [ ] **Security:** no secrets; tokens/PII not logged; authz + tenant scoping on new endpoints; inputs validated
- [ ] **Constraints respected:** no order placement; demo never shown as live; no LLM in calculations; plans/trades kept separate; long-only actionability
- [ ] Data-mode / licensing impact considered (personal data not shared across tenants)
