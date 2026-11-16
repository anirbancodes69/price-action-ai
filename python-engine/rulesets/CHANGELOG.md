# Ruleset changelog

Each ruleset version is an immutable JSON file `rulesets/<code>/<version>.json` (flat dotted keys, TRD-01 §6) and a seeded
`ruleset_versions` row (ARC-03 §7.1). The two must be identical: CI runs `contracts/scripts/check_ruleset_hash.py`.
A change to any value is a new version, never an edit of a released file. Any change that alters golden outputs also
needs an entry here, updated TRD docs (TRD-01 §6 and the TRD that defines the rule) and a bumped version (ADR-008).

The backend seeds from `backend/database/seeders/data/<code>-<version>.json` because the backend container cannot see
this directory; both files are kept byte-identical.

## pa-core 0.1.0

- Initial registry: the 29 defaults of TRD-01 §6. All values are `HYPOTHESIS` (not validated by backtests).
- Score version `paqs-0.1.0` (TRD-04 §9).
