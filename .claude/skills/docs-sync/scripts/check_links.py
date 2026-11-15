#!/usr/bin/env python3
"""Check relative Markdown links and #anchors in the repository.

External links (http, https, mailto) are not fetched. Anchors are resolved with
GitHub's heading-slug rules. Links inside fenced code blocks and inline code are ignored.
Standard library only. Exit code 1 if any link is broken.

Usage: python3 .claude/skills/docs-sync/scripts/check_links.py [PATH ...]
       (default: every *.md under the repository root)
"""

from __future__ import annotations

import re
import subprocess
import sys
from functools import cache
from pathlib import Path

SKIP_DIRS = {"node_modules", "vendor", ".git", ".git-backups", ".next", ".venv", "storage",
             ".pytest_cache", ".mypy_cache", ".ruff_cache"}
LINK_RE = re.compile(r"!?\[(?:[^\]\[]|\[[^\]]*\])*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
INLINE_CODE_RE = re.compile(r"`[^`]*`")


def repo_root() -> Path:
    out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return Path(out.stdout.strip()) if out.returncode == 0 else Path.cwd()


def iter_lines_outside_code(text: str):
    in_fence = False
    for no, line in enumerate(text.splitlines(), 1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            yield no, line


def slugify(heading: str) -> str:
    h = re.sub(r"<[^>]+>", "", heading)                          # strip HTML
    h = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", h)             # links -> text
    h = h.replace("`", "").lower()
    h = re.sub(r"[^\w\- ]", "", h, flags=re.UNICODE)             # GitHub keeps word chars, '-', ' '
    return h.replace(" ", "-")


@cache
def anchors_for(path: Path) -> frozenset[str]:
    seen: dict[str, int] = {}
    result: set[str] = set()
    for _, line in iter_lines_outside_code(path.read_text(encoding="utf-8", errors="replace")):
        m = HEADING_RE.match(line)
        if not m:
            continue
        base = slugify(m.group(2))
        n = seen.get(base, 0)
        result.add(base if n == 0 else f"{base}-{n}")
        seen[base] = n + 1
    return frozenset(result)


def md_files(root: Path, targets: list[str]) -> list[Path]:
    paths = [root / t for t in targets] if targets else [root]
    files: list[Path] = []
    for p in paths:
        if p.is_file() and p.suffix == ".md":
            files.append(p)
        elif p.is_dir():
            files.extend(f for f in p.rglob("*.md") if not SKIP_DIRS.intersection(f.relative_to(root).parts))
    return sorted(set(files))


def main() -> int:
    root = repo_root()
    errors: list[str] = []
    checked = 0
    for md in md_files(root, sys.argv[1:]):
        for no, line in iter_lines_outside_code(md.read_text(encoding="utf-8", errors="replace")):
            for target in LINK_RE.findall(INLINE_CODE_RE.sub("", line)):
                if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I):    # http:, mailto:, etc.
                    continue
                checked += 1
                file_part, _, anchor = target.partition("#")
                dest = md if not file_part else (md.parent / file_part).resolve()
                rel = md.relative_to(root)
                if not dest.exists():
                    errors.append(f"{rel}:{no}: missing file -> {target}")
                    continue
                if anchor and dest.is_file() and dest.suffix == ".md" and anchor not in anchors_for(dest):
                    errors.append(f"{rel}:{no}: missing anchor -> {target}")
    for e in errors:
        print(e)
    print(f"{checked} relative links checked, {len(errors)} broken.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
