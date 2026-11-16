#!/usr/bin/env python3
"""Check that contracts/api/openapi.yaml and ARC-04 describe the same endpoints.

Usage: check_arc04_coverage.py OPENAPI_JSON [ARC04_MD]

OPENAPI_JSON is the bundled spec as JSON (CI produces it with `redocly bundle --ext json`), so this script needs
only the standard library. Every ARC-04 endpoint id (A1, O2, N16, R1, ...) must appear exactly once as `x-arc04-id`
with the same HTTP method and path, and the spec must not carry ids that ARC-04 does not define. Exit code 1 on any
difference.
"""
import json
import re
import sys
from pathlib import Path

DEFAULT_ARC04 = Path(__file__).resolve().parents[2] / "docs" / "architecture" / "04_API_SPECIFICATION.md"
METHODS = ("get", "post", "put", "patch", "delete")
ROW = re.compile(r"^(?:\| ([A-Z]\d+) \| |\*\*([A-Z]\d+)\*\* )`(GET|POST|PUT|PATCH|DELETE) ([^`?\s]+)")


def arc04_endpoints(md: str) -> dict[str, tuple[str, str]]:
    found: dict[str, tuple[str, str]] = {}
    for line in md.splitlines():
        m = ROW.match(line)
        if not m:
            continue
        eid = m.group(1) or m.group(2)
        if eid in found:
            raise SystemExit(f"ARC-04 defines endpoint id {eid} twice")
        found[eid] = (m.group(3).lower(), m.group(4))
    return found


def spec_endpoints(spec: dict) -> dict[str, tuple[str, str]]:
    found: dict[str, tuple[str, str]] = {}
    problems = []
    operation_ids: set[str] = set()
    for path, item in spec.get("paths", {}).items():
        for method in METHODS:
            op = item.get(method)
            if op is None:
                continue
            eid = op.get("x-arc04-id")
            if not eid:
                problems.append(f"{method.upper()} {path} has no x-arc04-id")
                continue
            if eid in found:
                problems.append(f"x-arc04-id {eid} is used twice")
            found[eid] = (method, path)
            oid = op.get("operationId")
            if not oid or oid in operation_ids:
                problems.append(f"{method.upper()} {path}: missing or duplicate operationId")
            operation_ids.add(oid)
    if problems:
        raise SystemExit("\n".join(problems))
    return found


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    spec = json.loads(Path(argv[1]).read_text())
    md_path = Path(argv[2]) if len(argv) > 2 else DEFAULT_ARC04
    doc = arc04_endpoints(md_path.read_text())
    api = spec_endpoints(spec)

    errors = []
    for eid in sorted(set(doc) - set(api), key=lambda x: (x[0], int(x[1:]))):
        errors.append(f"{eid} {doc[eid][0].upper()} {doc[eid][1]} is in ARC-04 but missing from the OpenAPI file")
    for eid in sorted(set(api) - set(doc), key=lambda x: (x[0], int(x[1:]))):
        errors.append(f"{eid} {api[eid][0].upper()} {api[eid][1]} is in the OpenAPI file but not in ARC-04")
    for eid in sorted(set(doc) & set(api), key=lambda x: (x[0], int(x[1:]))):
        if doc[eid] != api[eid]:
            errors.append(f"{eid}: ARC-04 says {doc[eid][0].upper()} {doc[eid][1]}, OpenAPI says {api[eid][0].upper()} {api[eid][1]}")

    if errors:
        print("\n".join(errors))
        print(f"\nARC-04 coverage check FAILED ({len(errors)} problem(s)).")
        return 1
    print(f"ARC-04 coverage OK: {len(doc)} endpoints in both documents.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
