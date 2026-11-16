#!/usr/bin/env python3
"""Export the engine contract (Pydantic models) as JSON Schema files in ``contracts/engine/``.

    python scripts/export_engine_schemas.py            # write the files
    python scripts/export_engine_schemas.py --check    # exit 1 if the committed files are stale (CI)
    python scripts/export_engine_schemas.py --out DIR  # another directory (default: <repo>/contracts/engine)

One file per model in ``app.schemas.EXPORTED_MODELS``, named after the model. Output is canonical (sorted
keys, two-space indent, trailing newline) so a diff means the contract changed (ENG-04 §8).
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # make `app` importable when run as a script

from app.schemas import EXPORTED_MODELS

DEFAULT_OUT = Path(__file__).resolve().parents[2] / "contracts" / "engine"
DRAFT = "https://json-schema.org/draft/2020-12/schema"


def render() -> dict[str, str]:
    """File name to file content for every exported model."""
    files: dict[str, str] = {}
    for model in EXPORTED_MODELS:
        schema = {"$schema": DRAFT, **model.model_json_schema(mode="validation")}
        files[f"{model.__name__}.json"] = (
            json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        )
    return files


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--check", action="store_true", help="do not write; fail if files differ")
    args = parser.parse_args(argv)

    expected = render()
    out: Path = args.out

    if args.check:
        problems = []
        for name, content in expected.items():
            path = out / name
            if not path.exists():
                problems.append(f"missing: {path}")
            elif path.read_text() != content:
                problems.append(f"stale:   {path}")
        if out.exists():
            problems.extend(f"unknown: {p}" for p in sorted(out.glob("*.json")) if p.name not in expected)
        if problems:
            print("\n".join(problems))
            print("Engine schemas are out of date. Run: make export-schemas")
            return 1
        print(f"Engine schemas up to date ({len(expected)} files in {out}).")
        return 0

    out.mkdir(parents=True, exist_ok=True)
    for stale in out.glob("*.json"):
        if stale.name not in expected:
            stale.unlink()
    for name, content in expected.items():
        (out / name).write_text(content)
    print(f"Wrote {len(expected)} schemas to {out}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
