#!/usr/bin/env python3
"""List the documents to review for the files changed on this branch.

Mechanises the change -> document mapping in CLAUDE.md §9 (that table is authoritative;
update RULES below if it changes). Standard library only.

Usage: python3 .claude/skills/docs-sync/scripts/docs_impact.py [--base REF]
"""

from __future__ import annotations

import argparse
import subprocess
import sys

# (path prefix or exact file, area label, documents to review)
RULES: list[tuple[str, str, list[str]]] = [
    ("frontend/", "Frontend", [
        "docs/product/03_PRD.md", "docs/product/06_FEATURE_CATALOG.md",
        "docs/product/07_UI_UX_SPECIFICATION.md",
        "docs/engineering/02_FRONTEND_ARCHITECTURE.md (incl. §9 discrepancies)",
        "docs/architecture/04_API_SPECIFICATION.md (if data needs change)",
    ]),
    ("backend/database/", "Database schema", [
        "docs/architecture/03_DATABASE_DESIGN.md (incl. §2.1 as-migrated notes)",
        "docs/architecture/04_API_SPECIFICATION.md", "docs/architecture/05_DATA_FLOW.md",
        "docs/engineering/03_BACKEND_ARCHITECTURE.md", "related ADRs",
    ]),
    ("backend/routes/", "API", [
        "docs/architecture/04_API_SPECIFICATION.md (+ contracts/)",
        "docs/engineering/03_BACKEND_ARCHITECTURE.md",
        "docs/engineering/02_FRONTEND_ARCHITECTURE.md §8",
        "docs/architecture/06_SECURITY_ARCHITECTURE.md",
    ]),
    ("backend/app/Http/", "API", [
        "docs/architecture/04_API_SPECIFICATION.md (+ contracts/)",
        "docs/engineering/03_BACKEND_ARCHITECTURE.md",
        "docs/architecture/06_SECURITY_ARCHITECTURE.md",
    ]),
    ("backend/", "Backend", ["docs/engineering/03_BACKEND_ARCHITECTURE.md"]),
    ("contracts/", "API contracts", [
        "docs/architecture/04_API_SPECIFICATION.md",
        "docs/engineering/04_PYTHON_ENGINE_ARCHITECTURE.md §8",
        "docs/engineering/02_FRONTEND_ARCHITECTURE.md §8",
    ]),
    ("python-engine/app/domain/", "Trading logic", [
        "docs/trading/01..08 (the TRD docs for the rules touched)",
        "docs/engineering/04_PYTHON_ENGINE_ARCHITECTURE.md",
        "ruleset version bump if outputs change (TRD-01 §6, ENG-04 §5)",
    ]),
    ("python-engine/rulesets/", "Trading logic", [
        "docs/trading/01_TRADING_METHODOLOGY.md §6", "python-engine/rulesets/CHANGELOG.md",
    ]),
    ("python-engine/app/backtest/", "Trading logic", [
        "docs/trading/06_BACKTESTING_METHODOLOGY.md", "docs/trading/08_TRADING_ENGINE_VALIDATION.md",
    ]),
    ("python-engine/app/paper/", "Trading logic", ["docs/trading/07_PAPER_TRADING_SPECIFICATION.md"]),
    ("python-engine/app/providers/", "Market data", [
        "docs/architecture/08_INTEGRATION_ARCHITECTURE.md",
        "docs/engineering/05_DATA_INGESTION_SPECIFICATION.md",
    ]),
    ("python-engine/app/ingestion/", "Market data", [
        "docs/engineering/05_DATA_INGESTION_SPECIFICATION.md",
        "docs/architecture/08_INTEGRATION_ARCHITECTURE.md",
    ]),
    ("python-engine/app/explain/", "LLM", [
        "docs/architecture/07_AI_AND_LLM_ARCHITECTURE.md",
        "docs/adr/ADR-009-LLM-EXPLANATION-ONLY.md",
    ]),
    ("python-engine/", "Python engine", ["docs/engineering/04_PYTHON_ENGINE_ARCHITECTURE.md"]),
    (".github/", "CI / GitHub", [
        "docs/engineering/08_DEVELOPMENT_ENVIRONMENT.md", "docs/engineering/09_GITHUB_REPOSITORY_STRATEGY.md",
        "docs/engineering/10_GITHUB_ACTIONS_CI_CD.md", "docs/engineering/11_BRANCHING_AND_RELEASE_STRATEGY.md",
        "docs/operations/01_DEPLOYMENT_GUIDE.md", "docs/operations/02_ENVIRONMENT_CONFIGURATION.md",
        "docs/architecture/06_SECURITY_ARCHITECTURE.md",
    ]),
    ("docker-compose", "Docker", [
        "docs/engineering/08_DEVELOPMENT_ENVIRONMENT.md", "docs/engineering/10_GITHUB_ACTIONS_CI_CD.md",
        "docs/operations/01_DEPLOYMENT_GUIDE.md", "docs/operations/02_ENVIRONMENT_CONFIGURATION.md",
    ]),
    ("infrastructure/", "Docker", [
        "docs/engineering/08_DEVELOPMENT_ENVIRONMENT.md", "docs/operations/01_DEPLOYMENT_GUIDE.md",
    ]),
    ("Makefile", "Dev environment", ["docs/engineering/08_DEVELOPMENT_ENVIRONMENT.md"]),
    (".env.example", "Configuration", [
        "docs/operations/02_ENVIRONMENT_CONFIGURATION.md", "docs/architecture/06_SECURITY_ARCHITECTURE.md §7",
    ]),
    ("docs/adr/", "Architecture decision", [
        "DECISIONS.md", "docs/adr/README.md", "affected ARC-* specs", "docs/engineering/01_IMPLEMENTATION_ROADMAP.md",
    ]),
    (".claude/", "Claude Code config", ["CLAUDE.md (only if persistent instructions change)"]),
]

ALWAYS = [
    "CURRENT.md (verified state, last-verified line)",
    "TASKS.md (status + verified acceptance evidence)",
    "ROADMAP.md (only if milestone progress changed)",
    "CHANGELOG.md (if significant)",
    "docs/product/06_FEATURE_CATALOG.md (if feature state changed)",
    "docs/DOCUMENTATION_STATUS.md (if a doc status or OQ-* changed)",
]


def git(*args: str) -> list[str]:
    out = subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout
    return [line for line in out.splitlines() if line.strip()]


def changed_files(base: str) -> list[str]:
    files = set(git("diff", "--name-only", f"{base}...HEAD"))
    for line in git("status", "--porcelain", "--untracked-files=all"):
        path = line[3:]
        files.add(path.split(" -> ")[-1])
    return sorted(files)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="main", help="base ref to diff against (default: main)")
    args = parser.parse_args()

    try:
        files = changed_files(args.base)
    except subprocess.CalledProcessError as exc:
        print(f"git failed: {exc.stderr.strip()}", file=sys.stderr)
        return 2

    if not files:
        print("No changes relative to", args.base)
        return 0

    areas: dict[str, set[str]] = {}
    docs: dict[str, set[str]] = {}
    for f in files:
        for prefix, area, targets in RULES:
            if f == prefix or f.startswith(prefix):
                areas.setdefault(area, set()).add(f)
                for t in targets:
                    docs.setdefault(t, set()).add(area)
                break  # first (most specific) matching rule wins
    print(f"Changed files ({len(files)}) vs {args.base}:")
    for f in files:
        print("  ", f)
    print("\nAreas:")
    for area, fs in sorted(areas.items()):
        print(f"  {area}: {len(fs)} file(s)")
    print("\nReview (update only if actually affected):")
    for d, why in sorted(docs.items()):
        print(f"  - {d}  <- {', '.join(sorted(why))}")
    print("\nProject-control files (CLAUDE.md §7 end-of-task):")
    for d in ALWAYS:
        print(f"  - {d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
