#!/usr/bin/env python3
"""Check that every ruleset is identical everywhere it lives (ENG-04 §5, ENG-10, ADR-008).

For each `python-engine/rulesets/<code>/<version>.json` this verifies that
  1. the backend seeder copy `backend/database/seeders/data/<code>-<version>.json` has the same parameters, so the
     seeded `ruleset_versions` row and the engine's file hash identically, and
  2. for the version documented in TRD-01 §6, the file has exactly the documented keys and default values.
It prints the canonical sha256 (sorted keys, compact separators), which the seeder computes the same way.

Usage: check_ruleset_hash.py [REPO_ROOT]
Exit code 1 on any difference. Standard library only.
"""

import hashlib
import json
import re
import sys
from pathlib import Path

ROW = re.compile(r"^\| `([a-z_]+(?:\.[a-z0-9_]+)+)` \| ([^|]+?) \|")
RULESET_FILE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*-\d+\.\d+\.\d+\.json$")
VERSION = re.compile(r"Ruleset ID: \*\*`([a-z0-9-]+)`\*\*, version \*\*`(\d+\.\d+\.\d+)`\*\*")


def canonical(parameters: dict[str, object]) -> str:
    return json.dumps(parameters, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256(parameters: dict[str, object]) -> str:
    return hashlib.sha256(canonical(parameters).encode()).hexdigest()


def load(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return data


def documented(md: str) -> tuple[tuple[str, str] | None, dict[str, object]]:
    """The (code, version) and the key -> default values of the TRD-01 §6 registry."""
    version = VERSION.search(md)
    start = md.find("## 6. Ruleset Parameter Registry")
    end = md.find("\n## 7.", start)
    rows: dict[str, object] = {}
    for line in md[start:end].splitlines():
        m = ROW.match(line)
        if not m:
            continue
        raw = m.group(2).strip()
        rows[m.group(1)] = True if raw == "true" else False if raw == "false" else float(raw)
    return (version.groups() if version else None), rows  # type: ignore[return-value]


def same_value(a: object, b: object) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    return isinstance(a, int | float) and isinstance(b, int | float) and float(a) == float(b)


def check(root: Path) -> list[str]:
    problems: list[str] = []
    engine_files = sorted((root / "python-engine" / "rulesets").glob("*/*.json"))
    # Only `<code>-<x.y.z>.json` files are rulesets; other seed data (e.g. the market calendar) is ignored.
    seeder_files = sorted(
        p for p in (root / "backend" / "database" / "seeders" / "data").glob("*.json") if RULESET_FILE.match(p.name)
    )
    if not engine_files:
        return ["no engine rulesets found under python-engine/rulesets"]

    trd = root / "docs" / "trading" / "01_TRADING_METHODOLOGY.md"
    doc_id, doc_rows = documented(trd.read_text())

    engine_names = set()
    for path in engine_files:
        code, version = path.parent.name, path.stem
        engine_names.add(f"{code}-{version}.json")
        seeder = root / "backend" / "database" / "seeders" / "data" / f"{code}-{version}.json"
        if not seeder.exists():
            problems.append(f"{code} {version}: no seeder copy at {seeder.relative_to(root)}")
            continue
        params, seeded = load(path), load(seeder)
        if sha256(params) != sha256(seeded):
            problems.append(f"{code} {version}: engine file and seeder file differ")
            for key in sorted(set(params) | set(seeded)):
                if params.get(key) != seeded.get(key):
                    problems.append(f"    {key}: engine={params.get(key)!r} seeder={seeded.get(key)!r}")
        if doc_id == (code, version):
            for key in sorted(set(doc_rows) - set(params)):
                problems.append(f"{code} {version}: {key} is in TRD-01 §6 but not in the ruleset file")
            for key in sorted(set(params) - set(doc_rows)):
                problems.append(f"{code} {version}: {key} is in the ruleset file but not in TRD-01 §6")
            for key in sorted(set(doc_rows) & set(params)):
                if not same_value(doc_rows[key], params[key]):
                    problems.append(f"{code} {version}: {key} is {params[key]!r} in the file but {doc_rows[key]!r} in TRD-01 §6")
        print(f"{code} {version}: sha256 {sha256(params)}")
    problems.extend(f"seeder file {p.name} has no engine ruleset" for p in seeder_files if p.name not in engine_names)
    return problems


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parents[2]
    problems = check(root)
    if problems:
        print("\n".join(problems))
        print(f"\nRuleset check FAILED ({len(problems)} problem(s)).")
        return 1
    print("Ruleset check OK: engine files, seeder files and TRD-01 §6 agree.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
