"""Pure, deterministic trading domain library.

Rules (docs/engineering/04_PYTHON_ENGINE_ARCHITECTURE.md §3):
- imports only the standard library, numpy and app.domain.*
- no I/O, clock, randomness, database or network access
- every derived object carries `index` and `confirmed_at_index` (no look-ahead)

Implementation starts in M3 (pivots and market structure, docs/trading/02).
"""
