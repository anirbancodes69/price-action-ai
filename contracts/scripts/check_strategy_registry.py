#!/usr/bin/env python3
"""Check that every layer agrees on the strategy (setup type) identifiers (Phase 1 P4).

Compares `contracts/strategy-registry.json` with
  - the engine's `SetupType` enum and the setup types each ruleset enables,
  - the OpenAPI `SetupType` enum,
  - Laravel's scanner `setup_type` filter and trade-plan `SETUP_TYPES`,
  - the frontend `SETUP_TYPE` map.
Usage: check_strategy_registry.py [REPO_ROOT]. Exit code 1 on any difference. Standard library only.
"""

import json
import re
import sys
from pathlib import Path

ID = re.compile(r"[A-Z][A-Z_]{3,}")


def ids(text: str) -> set[str]:
    return set(ID.findall(text))


def block(text: str, start: str, end: str) -> str:
    i = text.index(start)
    return text[i + len(start) : text.index(end, i + len(start))]


def collect(root: Path) -> dict[str, set[str]]:
    reg = json.loads((root / "contracts/strategy-registry.json").read_text())["strategies"]
    engine = (root / "python-engine/app/domain/setups/types.py").read_text()
    enum = block(engine, "class SetupType", "TYPE_ORDER")
    openapi = (root / "contracts/api/openapi.yaml").read_text()
    scanner = (root / "backend/app/Http/Requests/Api/V1/ScannerRequest.php").read_text()
    plan = (root / "backend/app/Http/Requests/Api/V1/TradePlanRequest.php").read_text()
    front = (root / "frontend/src/lib/api/scanner.ts").read_text()
    return {
        "registry engine_enum": {k for k, v in reg.items() if v["engine_enum"]},
        "engine SetupType": set(re.findall(r'^\s+[A-Z_]+ = "([A-Z_]+)"', enum, re.M)),
        "registry scanner_filter": {k for k, v in reg.items() if v["scanner_filter"]},
        "laravel scanner filter": ids(block(scanner, "'setup_type'", "'setup_status'")),
        "registry trade_plan": {k for k, v in reg.items() if v["trade_plan"]},
        "laravel trade plan": ids(block(plan, "SETUP_TYPES = [", "];")),
        "registry all": set(reg),
        "openapi SetupType": set(re.findall(r'- "([A-Z_]+)"', block(openapi, "    SetupType:", "description:"))),
        "frontend SETUP_TYPE": set(re.findall(r"^\s+([A-Z_]+): \"", block(front, "export const SETUP_TYPE", "};"), re.M)),
    }


def problems(root: Path) -> list[str]:
    c = collect(root)
    out = []
    for a, b in [
        ("registry engine_enum", "engine SetupType"),
        ("registry scanner_filter", "laravel scanner filter"),
        ("registry trade_plan", "laravel trade plan"),
        ("registry all", "openapi SetupType"),
    ]:
        if c[a] != c[b]:
            out.append(f"{a} != {b}: only in first {sorted(c[a] - c[b])}, only in second {sorted(c[b] - c[a])}")
    missing = c["registry engine_enum"] - c["frontend SETUP_TYPE"]
    if missing:
        out.append(f"frontend SETUP_TYPE lacks engine types {sorted(missing)} (they would render as range-bound)")
    return out


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
    found = problems(root)
    for p in found:
        print("FAIL:", p)
    print("strategy registry:", "FAIL" if found else "OK")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
