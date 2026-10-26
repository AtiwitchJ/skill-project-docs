#!/usr/bin/env python3
"""Fill the memory bank's derived blocks from their owners.

`memory-bank/progress.md` carries <!-- AUTO:phase-counts --> filled from
phase-N/tasks.md, so the count is counted, never typed. Everything outside the
markers is prose a person writes and this script never touches.

  python3 sync_memory_bank.py            # update the block in place
  python3 sync_memory_bank.py --check    # exit 1 if the block is out of date, change nothing

Standard library only. Run from the repo root.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from docs_lib import (  # noqa: E402
    REPO,
    parse_tasks,
    phases_present,
    read_block,
    replace_block,
    tasks_path,
)

PROGRESS = REPO / "memory-bank" / "progress.md"
MARKERS = ("<!-- AUTO:phase-counts -->", "<!-- /AUTO:phase-counts -->")


def expected() -> str:
    lines = ["\n| Phase | Done / Total | State |", "| :--- | :--- | :--- |"]
    for n in phases_present():
        path = tasks_path(n)
        if not path.exists():
            continue
        items = parse_tasks(path)
        done = sum(1 for i in items if i["mark"] == "x")
        doing = sum(1 for i in items if i["mark"] == "/")
        blocked = sum(1 for i in items if i["mark"] == "!")
        if done == len(items):
            state = "closed"
        elif blocked:
            state = f"{blocked} blocked"
        elif doing:
            state = f"{doing} in progress"
        elif done:
            state = "in progress"
        else:
            state = "not started"
        lines.append(f"| {n} | {done} / {len(items)} | {state} |")
    return "\n" + "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="verify only; exit 1 when out of date")
    args = ap.parse_args()

    if not PROGRESS.exists():
        print(f"{PROGRESS} not found", file=sys.stderr)
        return 1
    text = PROGRESS.read_text(encoding="utf-8")
    want = expected()
    current = read_block(text, MARKERS)
    if current is None:
        print(f"markers {MARKERS[0]} … {MARKERS[1]} missing from {PROGRESS}", file=sys.stderr)
        return 1

    same = " ".join(current.split()) == " ".join(want.split())
    if same:
        print("memory-bank phase counts match TASKS")
        return 0
    if args.check:
        print("memory-bank phase counts are out of date with TASKS (run sync_memory_bank.py)")
        print("--- current ---")
        print(current.strip())
        print("--- expected ---")
        print(want.strip())
        return 1

    new_text, replaced = replace_block(text, MARKERS, want)
    if not replaced:
        print("could not replace the AUTO block", file=sys.stderr)
        return 1
    PROGRESS.write_text(new_text, encoding="utf-8")
    print("updated memory-bank phase counts from TASKS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
