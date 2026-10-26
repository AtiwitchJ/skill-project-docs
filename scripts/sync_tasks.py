#!/usr/bin/env python3
"""Synchronize Task headers with their subtask checklist items in phase-N/tasks.md,
and update presentations automatically.

Usage:
  python3 sync_tasks.py 1              # sync phase 1 task headers and presentation
  python3 sync_tasks.py 1 --check      # check if phase 1 task headers match subtasks
  python3 sync_tasks.py --all          # sync all phases
  python3 sync_tasks.py --all --check  # check all phases without modifying files
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from docs_lib import (  # noqa: E402
    HEADER_RE,
    parse_tasks_detailed,
    phases_present,
    task_stats,
    tasks_path,
)
from sync_presentation import build, presentation_path  # noqa: E402


def sync_phase_tasks(phase: int, check_only: bool = False) -> tuple[int, list[str]]:
    """Check or update task headers in phase-N/tasks.md based on subtask checklist status.

    Returns:
        (num_changed, list_of_messages)
    """
    path = tasks_path(phase)
    if not path.exists():
        return 0, [f"ERROR: {path} not found"]

    tasks = parse_tasks_detailed(path)
    lines = path.read_text(encoding="utf-8").splitlines()
    changes = []
    modified_lines = list(lines)

    for t in tasks:
        stats = task_stats(t)
        if stats["total"] == 0:
            continue

        line_idx = t["line_no"] - 1
        current_mark = t["mark"]
        expected_mark = None

        if stats["all_done"] and current_mark != "x":
            expected_mark = "x"
            reason = f"all {stats['total']} subtasks completed"

        if expected_mark and expected_mark != current_mark:
            old_header = lines[line_idx]
            new_header = re.sub(r"^###\s+\[.\]", f"### [{expected_mark}]", old_header)
            tid = t["id"] or t["title"][:25]
            msg = f"Task {tid} (line {t['line_no']}): [{current_mark}] -> [{expected_mark}] ({reason})"
            changes.append(msg)
            if not check_only:
                modified_lines[line_idx] = new_header

    if not check_only and changes:
        path.write_text("\n".join(modified_lines) + "\n", encoding="utf-8")
        # Auto-sync presentation for this phase if it exists
        pres = presentation_path(phase)
        if pres.exists():
            pres_text = pres.read_text(encoding="utf-8")
            try:
                new_pres = build(phase, pres_text)
                pres.write_text(new_pres, encoding="utf-8")
                changes.append(f"Auto-synced {pres.name}")
            except Exception as e:
                changes.append(f"WARN: could not auto-sync presentation: {e}")

    return len(changes), changes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("phase", type=int, nargs="?", help="phase number to sync")
    ap.add_argument("--all", action="store_true", help="sync all present phases")
    ap.add_argument("--check", action="store_true", help="check only; exit 1 if any task header is out of sync")
    args = ap.parse_args()

    if not args.phase and not args.all:
        ap.print_help()
        return 1

    phases = phases_present() if args.all else [args.phase]
    total_inconsistencies = 0

    for n in phases:
        count, msgs = sync_phase_tasks(n, check_only=args.check)
        if msgs:
            prefix = "Checked" if args.check else "Synchronized"
            print(f"=== {prefix} Phase {n} ({count} updates) ===")
            for m in msgs:
                print(f"  • {m}")
            total_inconsistencies += count

    if args.check and total_inconsistencies > 0:
        print(f"\nFound {total_inconsistencies} task header(s) out of sync. Run without --check to fix automatically.")
        return 1
    elif not args.check and total_inconsistencies > 0:
        print(f"\nSuccessfully synchronized {total_inconsistencies} task header(s).")
    elif total_inconsistencies == 0:
        print("All task headers match their subtask checklist items.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
