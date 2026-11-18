#!/usr/bin/env python3
"""Fail on high/critical npm advisories that have no valid, unexpired exception (ENG-10 §4.6).

Usage: check_npm_audit.py AUDIT_JSON EXCEPTIONS_JSON [TODAY]

AUDIT_JSON is the output of `npm audit --json` (npm exits non-zero when it finds problems, so the workflow ignores
its exit code and lets this script decide). EXCEPTIONS_JSON is `.github/security-exceptions.json`:

    {"exceptions": [{"id": "GHSA-...", "package": "...", "justification": "...", "owner": "...", "expires": "YYYY-MM-DD"}]}

An advisory is excepted by its GHSA id. An exception with a missing field or a past expiry date is an error, so a
waiver cannot silently outlive its review date. Exceptions that match no current finding are reported, not failed.
Standard library only. TODAY (YYYY-MM-DD) exists for tests.
"""

import json
import sys
from datetime import date
from pathlib import Path

BLOCKING = {"high", "critical"}
REQUIRED = ("id", "package", "justification", "owner", "expires")


def advisories(audit: dict) -> dict[str, dict]:
    """GHSA id -> advisory for every high/critical advisory in an `npm audit --json` report."""
    found: dict[str, dict] = {}
    for vuln in audit.get("vulnerabilities", {}).values():
        for via in vuln.get("via", []):
            if isinstance(via, dict) and via.get("severity") in BLOCKING:
                ghsa = str(via.get("url", "")).rstrip("/").rsplit("/", 1)[-1]
                found[ghsa or str(via.get("source"))] = via
    return found


def load_exceptions(config: dict, today: date) -> tuple[dict[str, dict], list[str]]:
    valid: dict[str, dict] = {}
    problems: list[str] = []
    for entry in config.get("exceptions", []):
        missing = [k for k in REQUIRED if not str(entry.get(k, "")).strip()]
        if missing:
            problems.append(f"exception {entry.get('id', '?')}: missing {', '.join(missing)}")
            continue
        try:
            expires = date.fromisoformat(entry["expires"])
        except ValueError:
            problems.append(f"exception {entry['id']}: expires must be YYYY-MM-DD, got {entry['expires']!r}")
            continue
        if expires < today:
            problems.append(f"exception {entry['id']} ({entry['package']}) expired on {entry['expires']}: review it")
            continue
        valid[entry["id"]] = entry
    return valid, problems


def check(audit: dict, config: dict, today: date) -> tuple[list[str], list[str]]:
    """(errors, notes)."""
    found = advisories(audit)
    valid, errors = load_exceptions(config, today)
    notes: list[str] = []
    for ghsa, adv in sorted(found.items()):
        if ghsa in valid:
            e = valid[ghsa]
            notes.append(f"excepted {ghsa} ({adv.get('name')}, {adv.get('severity')}) until {e['expires']}: {e['justification']}")
        else:
            errors.append(f"{adv.get('severity')} advisory without an exception: {ghsa} {adv.get('name')} - {adv.get('title')}")
    notes.extend(f"exception {g} matches no current finding (remove it when the package is fixed)" for g in valid if g not in found)
    return errors, notes


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    audit = json.loads(Path(argv[1]).read_text())
    if "error" in audit and "vulnerabilities" not in audit:
        print(f"npm audit failed to run: {audit['error']}")
        return 1
    config = json.loads(Path(argv[2]).read_text())
    today = date.fromisoformat(argv[3]) if len(argv) > 3 else date.today()
    errors, notes = check(audit, config, today)
    for n in notes:
        print(f"note: {n}")
    for e in errors:
        print(f"ERROR: {e}")
    if errors:
        print(f"\nDependency audit FAILED ({len(errors)} problem(s)).")
        return 1
    print("Dependency audit OK: no unexcepted high/critical advisories.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
