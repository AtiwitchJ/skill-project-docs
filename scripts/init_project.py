#!/usr/bin/env python3
"""Scaffold a new project for the project-docs skill. Never overwrites an existing file.

  python3 init_project.py                              # current directory, name = directory name
  python3 init_project.py --name "My Project" --language Thai
  python3 init_project.py --path ~/work/other-repo --dry-run

Creates (only what is missing):
  .project-docs/   config.json, rules.md, owner-map.md, glossary.md, stale-patterns.json, flow-policy.json, diagrams/
  project/         README.md (with an AUTO phase table), roadmap.md/.html, issues.md, phases/, results/, decisions/, backlog/
  docs/            README.md and the four Diátaxis folders: tutorials/, how-to/, reference/, explanation/
  memory-bank/     progress.md and activeContext.md stubs, only if the folder has none (the memory-bank skill owns them)

Standard library only. Does not import layout.py, because that needs an existing project.
"""
from __future__ import annotations

import argparse
import datetime
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL / "templates" / "project"
KEEP_DIRS = [
    "docs/tutorials", "docs/how-to", "docs/reference", "docs/explanation",
    "project/phases", "project/results/charts", "project/decisions", "project/backlog",
    ".project-docs/diagrams",
    ".project-docs/presentations",
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--path", default=".", help="project root (default: current directory)")
    ap.add_argument("--name", help="project name (default: the directory name)")
    ap.add_argument("--language", default="English", help="language of the docs (default: English)")
    ap.add_argument("--dry-run", action="store_true", help="show what would be created, write nothing")
    args = ap.parse_args()

    root = Path(args.path).expanduser().resolve()
    if not root.is_dir():
        print(f"{root} is not a directory", file=sys.stderr)
        return 1
    if (root / ".project-docs" / "config.json").exists():
        print(f"{root} already has .project-docs/config.json; adding only what is missing")
    subs = {"{{PROJECT_NAME}}": args.name or root.name, "{{LANGUAGE}}": args.language,
            "{{DATE}}": datetime.date.today().isoformat()}

    created: list[str] = []
    skipped: list[str] = []
    memory_bank_taken = (root / "memory-bank").exists() and any((root / "memory-bank").glob("*.md"))
    for src in sorted(p for p in TEMPLATE.rglob("*") if p.is_file()):
        rel = src.relative_to(TEMPLATE)
        dst = root / rel
        if rel.parts[0] == "memory-bank" and memory_bank_taken:
            skipped.append(f"{rel}  (memory-bank already has files)")
            continue
        if dst.exists():
            skipped.append(f"{rel}  (exists)")
            continue
        text = src.read_text(encoding="utf-8")
        for key, value in subs.items():
            text = text.replace(key, value)
        if not args.dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(text, encoding="utf-8")
        created.append(str(rel))
    for d in KEEP_DIRS:
        keep = root / d / ".gitkeep"
        if not keep.exists() and not any((root / d).glob("*")):
            if not args.dry_run:
                keep.parent.mkdir(parents=True, exist_ok=True)
                keep.touch()
            created.append(f"{d}/.gitkeep")

    for c in created:
        print(("would create " if args.dry_run else "created ") + c)
    for s in skipped:
        print("kept    " + s)
    if not args.dry_run:
        for script in ("sync_project_readme.py", "sync_memory_bank.py"):     # fill the derived tables for zero phases
            subprocess.run([sys.executable, str(SKILL / "scripts" / script)], cwd=root, check=False, capture_output=True)
        print(f"""
Next:
  1. Fill .project-docs/rules.md and owner-map.md for this project (what is specific to it).
  2. Add the first phase: project/phases/phase-1/tasks.md (first line "# PHASE 1: <title>", tasks as "### [ ] 1.1 <name>"),
     then python3 {SKILL}/scripts/sync_presentation.py 1 --new   (every phase has a presentation)
     and a roadmap row that links phases/phase-1/tasks.md with its done/total count.
  3. python3 {SKILL}/scripts/sync_project_readme.py; python3 {SKILL}/scripts/sync_memory_bank.py
  4. Check:  cd {root} && python3 {SKILL}/scripts/check_docs.py
  5. Using Azure DevOps? Fill "ado" in .project-docs/config.json and see integrations/azure-devops.md.
     For any tracker, configure "integrations" instead; see integrations/providers.md.
     Run integrations.py upgrade to assign stable Task UIDs and import legacy ADO mappings.
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
