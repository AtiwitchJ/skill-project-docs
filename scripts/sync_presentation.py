#!/usr/bin/env python3
"""Keep the derived parts of phase-N/presentation.html in sync with phase-N/tasks.md.

Only the blocks between AUTO markers are touched; narrative text is never changed.

  python3 sync_presentation.py 2             # update phase 2 presentation in place
  python3 sync_presentation.py 2 --check     # exit 1 if out of date, change nothing
  python3 sync_presentation.py 3 --new       # scaffold phase 3 from the template
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from docs_lib import (  # noqa: E402
    AUTO_ROWS,
    AUTO_SUMMARY,
    PERIOD_RE,
    PHASE_TITLE_RE,
    expected_blocks,
    parse_tasks,
    presentation_path,
    read_block,
    replace_block,
    tasks_path,
)
from layout import PRESENTATION_TEMPLATE  # noqa: E402

TEMPLATE = PRESENTATION_TEMPLATE


THAI_MONTHS = ["", "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
               "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]


def thai_date(d: date) -> str:
    return f"{d.day} {THAI_MONTHS[d.month]} {d.year + 543}"


def scaffold(phase: int, force: bool) -> str:
    out = presentation_path(phase)
    if out.exists() and not force:
        raise SystemExit(f"refusing to overwrite {out} (use --force)")
    tasks = tasks_path(phase).read_text(encoding="utf-8")
    title_m = PHASE_TITLE_RE.search(tasks.splitlines()[0]) if tasks else None
    period_m = PERIOD_RE.search(tasks)
    text = TEMPLATE.read_text(encoding="utf-8")
    subs = {
        "PHASE_NUMBER": str(phase),
        "PHASE_TITLE": title_m.group(1) if title_m else "TODO",
        "PERIOD": period_m.group(1) if period_m else "TODO",
        "UPDATED": thai_date(date.today()),
    }
    for key, value in subs.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def build(phase: int, text: str) -> str:
    items = parse_tasks(tasks_path(phase))
    blocks = expected_blocks(items)
    text, ok_s = replace_block(text, AUTO_SUMMARY, blocks["summary"])
    text, ok_r = replace_block(text, AUTO_ROWS, blocks["rows"])
    if not (ok_s and ok_r):
        missing = [n for n, ok in (("summary", ok_s), ("status-rows", ok_r)) if not ok]
        raise SystemExit(f"AUTO markers missing in presentation: {', '.join(missing)}")
    return text


def is_current(phase: int, text: str) -> bool:
    items = parse_tasks(tasks_path(phase))
    blocks = expected_blocks(items)
    cur_s = read_block(text, AUTO_SUMMARY)
    cur_r = read_block(text, AUTO_ROWS)
    if cur_s is None or cur_r is None:
        return False
    norm = lambda s: re.sub(r"\s+", " ", s).strip()  # noqa: E731
    return norm(cur_s) == norm(blocks["summary"]) and norm(cur_r) == norm(blocks["rows"])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("phase", type=int)
    ap.add_argument("--check", action="store_true", help="report only; exit 1 if out of date")
    ap.add_argument("--new", action="store_true", help="create the presentation from the template")
    ap.add_argument("--force", action="store_true", help="with --new, overwrite an existing file")
    args = ap.parse_args()

    if not tasks_path(args.phase).exists():
        print(f"ERROR: {tasks_path(args.phase)} not found. TASKS must exist before the presentation.")
        return 1

    if args.new:
        text = build(args.phase, scaffold(args.phase, args.force))
        presentation_path(args.phase).write_text(text, encoding="utf-8")
        print(f"created {presentation_path(args.phase)} (fill every TODO before reporting done)")
        return 0

    path = presentation_path(args.phase)
    if not path.exists():
        print(f"ERROR: {path} not found. Use --new to scaffold it.")
        return 1
    current = path.read_text(encoding="utf-8")

    if args.check:
        if is_current(args.phase, current):
            print(f"phase {args.phase}: derived blocks up to date")
            return 0
        print(f"phase {args.phase}: derived blocks OUT OF DATE, run without --check")
        return 1

    updated = build(args.phase, current)
    if updated == current:
        print(f"phase {args.phase}: already up to date")
    else:
        path.write_text(updated, encoding="utf-8")
        print(f"phase {args.phase}: derived blocks updated in {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
