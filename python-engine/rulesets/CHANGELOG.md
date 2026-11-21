# Ruleset changelog

Each ruleset version is an immutable JSON file `rulesets/<code>/<version>.json` (flat dotted keys, TRD-01 §6) and a seeded
`ruleset_versions` row (ARC-03 §7.1). The two must be identical: CI runs `contracts/scripts/check_ruleset_hash.py`.
A change to any value is a new version, never an edit of a released file. Any change that alters golden outputs also
needs an entry here, updated TRD docs (TRD-01 §6 and the TRD that defines the rule) and a bumped version (ADR-008).

The backend seeds from `backend/database/seeders/data/<code>-<version>.json` because the backend container cannot see
this directory; both files are kept byte-identical.

## pa-intraday 0.2.0 (2026-11-21, exploration candidate)

- `0.1.0` plus `setup.liquidity_sweep_enabled: true`: enables `LIQUIDITY_SWEEP_REVERSAL` (TRD-04 §7; vectors TV-SET-20..28). All other values are identical to `0.1.0`, which is unchanged and stays active. Not seeded as active; used for backtests (`run_backtest.py --ruleset pa-intraday@0.2.0`).
- Score version unchanged (`paqs-intraday-0.1.0`): the sweep checklist follows TRD-04 §10; key-level points for non-zone sweep anchors are undefined (OQ-SD-07) and score 0 with `missing = true`.
- Not validated: no backtest has been run on it yet (the original rules lost money on every period tested; see the backtest logs).

## pa-intraday 0.1.0 (2026-11-17)

- First intraday ruleset (ADR-014): 41 parameters in TRD-01 §6 for 5m setups with 15m and daily context, session rules (opening range 15 min, entry cutoff 45 min and exit 15 min before the close), and the owner's risk planning values (0.5% risk, ₹50,000 per position). All `HYPOTHESIS`.
- Not seeded yet: the seeder copy exists (`backend/database/seeders/data/pa-intraday-0.1.0.json`); seeding it as the active ruleset and retiring `pa-core` happens with the I1 schema work (T-I09).
- Score version `paqs-intraday-0.1.0` (components defined when TRD-04 is revised, T-I05).

## pa-core 0.1.0 (retired by ADR-014)

- Kept for history. Its engine and seeder files are still checked against each other; TRD-01 now documents `pa-intraday`, and the `pa-core` registry is in TRD-01 Appendix A.


- Initial registry: the 29 defaults of TRD-01 §6. All values are `HYPOTHESIS` (not validated by backtests).
- Score version `paqs-0.1.0` (TRD-04 §9).
