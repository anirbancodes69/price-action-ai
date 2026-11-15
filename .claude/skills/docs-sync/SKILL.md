---
name: docs-sync
description: Documentation Definition-of-Done workflow for PriceAction AI. Maps changed files to the specs that must be reviewed (CLAUDE.md §9), syncs the project-control files (CURRENT.md, TASKS.md, ROADMAP.md, CHANGELOG.md, DECISIONS.md, PRD-06 feature catalog, DOCUMENTATION_STATUS), records code-vs-spec discrepancies and open questions, follows the ADR decision-change protocol, and checks relative Markdown links and anchors. Use at the end of every substantial task, before a PR, when asked to update docs or project status, when a spec and the code disagree, or when an architectural or product decision would change.
---

# Docs sync

In this repo, documentation is part of done (CLAUDE.md §7–§9, [docs/README.md §4–§5](../../../docs/README.md#4-source-of-truth-rules)). This skill turns that rule into a repeatable procedure. CLAUDE.md §9 holds the change → doc mapping; the script below applies it mechanically.

## Workflow

1. **Find what changed and which docs to review:**
   ```bash
   python3 .claude/skills/docs-sync/scripts/docs_impact.py            # vs main, includes uncommitted files
   python3 .claude/skills/docs-sync/scripts/docs_impact.py --base origin/main
   ```
   The output lists candidate docs. Review each one and update **only** those actually affected. Do not touch unrelated docs to show activity.
2. **Update the authoritative home first** (one fact, one home, docs/README §4.1):
   - parameters in TRD-01 §6;
   - rules in TRD-02..07;
   - schema in ARC-03 (with as-migrated deviations in §2.1);
   - API in ARC-04, plus `contracts/` from M1;
   - feature status in PRD-06;
   - frontend discrepancies in ENG-02 §9;
   - decisions in ADRs.

   Then fix summaries and links that point at it. Bump the doc's metadata version (minor for additions, major for changed meaning) and set "Last updated".
3. **Sync the project-control files** with **verified** state only:
   - `CURRENT.md`: "Last verified" line (date and `main` SHA), component table, work in progress, immediate next task, blockers, inconsistencies.
   - `TASKS.md`: status. Move a task to Completed only when its acceptance criteria were verified, and cite the evidence (PR number, test counts).
   - `ROADMAP.md`: only if milestone progress changed.
   - `CHANGELOG.md`: significant changes, under `[Unreleased]`.
   - `docs/product/06_FEATURE_CATALOG.md`: if a feature's state changed.
   - `docs/DOCUMENTATION_STATUS.md`: if a document's status changed or an `OQ-*` was added or closed.
4. **Code and spec disagree?** Do not silently pick one. Record it (ENG-02 §9 for frontend, ARC-03 §2.1 for schema, or the CURRENT.md "Pending decisions and inconsistencies" table) and state which side should change.
5. **A decision changes?** Follow CLAUDE.md §8: a new `docs/adr/ADR-NNN-*.md` superseding the old one, the old one marked `Superseded by ADR-NNN`, and updates to DECISIONS.md, `docs/adr/README.md` and the affected specs. Unresolved questions become `OQ-*` items; never resolve them by assumption.
6. **Check links:**
   ```bash
   python3 .claude/skills/docs-sync/scripts/check_links.py           # all tracked-style *.md files
   python3 .claude/skills/docs-sync/scripts/check_links.py docs CURRENT.md
   ```
   It checks relative file links and `#anchors` (GitHub heading slugs). Fix every broken link you introduced.

## Constraints

- Progress reflects repository state, not intentions. A spec existing does not make a feature implemented.
- Never copy a spec's content into another doc or a skill. Link to it.
- Keep CLAUDE.md short. Change it only when persistent instructions change.
- If an authoritative doc is renamed or a section is renumbered, update references in `.claude/skills/**` too (the link check covers them).

## Deliverables

A list of docs updated (with a one-line reason each), docs reviewed but unchanged, discrepancies or `OQ-*` recorded, and the link-check result.
