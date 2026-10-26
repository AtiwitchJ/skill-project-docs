#!/usr/bin/env python3
"""Fill the phase table of project/README.md from each phase's tasks.md.

The table sits between <!-- AUTO:phase-status --> markers, so counts and links are derived,
never typed. Everything outside the markers is prose a person writes and this script
never touches it.

  python3 sync_project_readme.py            # update the block in place
  python3 sync_project_readme.py --check    # exit 1 if the block is out of date, change nothing

Standard library only. Run from the repo root.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from docs_lib import (  # noqa: E402
    PHASE_TITLE_RE,
    parse_tasks,
    phases_present,
    read_block,
    replace_block,
    tasks_path,
)
from layout import ADO_SNAPSHOT, CFG, PROJECT, phase_dir, presentation_path  # noqa: E402

README = PROJECT / "README.md"
MARKERS = ("<!-- AUTO:phase-status -->", "<!-- /AUTO:phase-status -->")
PBI_RE = re.compile(r"ADO\s*PBI:\*\*.*?#(\d+)")
WORDS = {
    "Thai": {"head": ["Phase", "ชื่อ", "คืบหน้า", "เอกสาร", "ADO"], "tasks": "รายการงาน", "deck": "นำเสนอ"},
    "English": {"head": ["Phase", "Title", "Progress", "Docs", "ADO"], "tasks": "Tasks", "deck": "Presentation"},
}


def ado_url(item_id: int) -> str | None:
    if not ADO_SNAPSHOT.exists():
        return None
    snap = json.loads(ADO_SNAPSHOT.read_text(encoding="utf-8"))
    org, project = snap.get("organization"), snap.get("project")
    if not (org and project):
        return None
    return f"https://dev.azure.com/{org}/{project}/_workitems/edit/{item_id}"


def expected() -> str:
    w = WORDS.get(CFG.get("language"), WORDS["English"])   # language comes from .project-docs/config.json
    primary = CFG.get("integrations", {}).get("primary")
    headings = list(w["head"])
    if primary:
        headings[-1] = "Tracker"
    rows = ["| " + " | ".join(headings) + " |", "| " + " | ".join([":---"] * len(headings)) + " |"]
    for n in phases_present():
        path = tasks_path(n)
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        first = text.splitlines()[0] if text else ""
        m = PHASE_TITLE_RE.search(first)
        title = m.group(1) if m else f"Phase {n}"
        items = parse_tasks(path)
        done = sum(1 for i in items if i["mark"] == "x")
        base = phase_dir(n).relative_to(PROJECT).as_posix()
        docs = f"[{w['tasks']}]({base}/tasks.md)"
        if presentation_path(n).exists():
            docs += f" · [{w['deck']}]({base}/presentation.html)"
        pbi = PBI_RE.search("\n".join(text.splitlines()[:10]))
        ado = "—"
        if primary:
            from integration_core import mapping, load, snapshot_path
            refs = mapping(PROJECT.parent).get("phases", {}).get(f"phase-{n}", [])
            snapshot = load(snapshot_path(PROJECT.parent, primary), {"items": []})
            urls = {str(i["id"]): i.get("url", "") for i in snapshot["items"]}
            links = []
            for ref in refs:
                if ref["connection"] == primary:
                    label = str(ref["id"]).replace("|", "\\|").replace("]", "")
                    url = ref.get("url") or urls.get(str(ref["id"]))
                    links.append(f"[{label}]({url})" if url else label)
            ado = " · ".join(links) or "—"
        elif pbi:
            url = ado_url(int(pbi.group(1)))
            ado = f"[#{pbi.group(1)}]({url})" if url else f"#{pbi.group(1)}"
        rows.append(f"| {n} | {title} | {done} / {len(items)} | {docs} | {ado} |")
    return "\n" + "\n".join(rows) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="verify only; exit 1 when out of date")
    args = ap.parse_args()

    if not README.exists():
        print(f"{README} not found", file=sys.stderr)
        return 1
    text = README.read_text(encoding="utf-8")
    want = expected()
    current = read_block(text, MARKERS)
    if current is None:
        print(f"markers {MARKERS[0]} … {MARKERS[1]} missing from {README}", file=sys.stderr)
        return 1

    if " ".join(current.split()) == " ".join(want.split()):
        print("project/README.md phase table matches tasks.md")
        return 0
    if args.check:
        print("project/README.md phase table is out of date (run sync_project_readme.py)")
        print("--- current ---")
        print(current.strip())
        print("--- expected ---")
        print(want.strip())
        return 1

    new_text, replaced = replace_block(text, MARKERS, want)
    if not replaced:
        print("could not replace the AUTO block", file=sys.stderr)
        return 1
    README.write_text(new_text, encoding="utf-8")
    print("updated project/README.md phase table from tasks.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
