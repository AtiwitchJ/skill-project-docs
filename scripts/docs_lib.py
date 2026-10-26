"""Shared helpers for project-docs scripts. Standard library only.

Single place that reads each phase's tasks.md so the checker and the presentation
sync always agree on the numbers. Paths come from layout.py.
"""
from __future__ import annotations

import html
import re
from collections import Counter
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from layout import (  # noqa: E402,F401  re-exported so callers keep importing from docs_lib
    REPO, CFG, phase_dir, tasks_path, presentation_path, deliverable_path, phases_present,
)

STATUS = {
    "x": ("done", "เสร็จ"),
    "/": ("doing", "กำลังทำ"),
    "!": ("block", "บล็อก"),
    " ": ("todo", "ยังไม่เริ่ม"),
}

HEADER_RE = re.compile(r"^###\s+\[(.)\]\s+(.*\S)\s*$")
CHECKLIST_RE = re.compile(r"^\s*[-*]\s+\[(.)\]\s*(.*)$")
ID_RE = re.compile(r"^(\d+(?:\.\d+)*)\s+(.*)$")
PHASE_TITLE_RE = re.compile(r"PHASE\s*\d+:\s*(.+?)\s*$")
PERIOD_RE = re.compile(r"(?:ระยะเวลา|Period):\*\*\s*(.+?)\s*$", re.M)

AUTO_SUMMARY = ("<!-- AUTO:summary -->", "<!-- /AUTO:summary -->")
AUTO_ROWS = ("<!-- AUTO:status-rows -->", "<!-- /AUTO:status-rows -->")


def parse_tasks(path: Path) -> list[dict]:
    """Return one dict per '### [mark] ...' header. Checklist items are not counted."""
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = HEADER_RE.match(line)
        if not m:
            continue
        mark, text = m.group(1), m.group(2)
        im = ID_RE.match(text)
        tid, title = (im.group(1), im.group(2)) if im else ("", text)
        items.append({"mark": mark, "id": tid, "title": title})
    return items


def parse_tasks_detailed(path: Path) -> list[dict]:
    """Return one dict per '### [mark] ...' header with subtask checklist items and line numbers."""
    items = []
    current_item = None
    lines = path.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines, 1):
        m = HEADER_RE.match(line)
        if m:
            mark, text = m.group(1), m.group(2)
            im = ID_RE.match(text)
            tid, title = (im.group(1), im.group(2)) if im else ("", text)
            current_item = {
                "mark": mark,
                "id": tid,
                "title": title,
                "line_no": i,
                "raw_line": line,
                "subtasks": [],
            }
            items.append(current_item)
            continue
        if current_item is not None:
            uid = re.match(r"^\*\*Task UID:\*\*\s*(\S+)\s*$", line)
            if uid:
                current_item["uid"] = uid.group(1)
            cm = CHECKLIST_RE.match(line)
            if cm:
                current_item["subtasks"].append({
                    "mark": cm.group(1),
                    "text": cm.group(2),
                    "line_no": i,
                })
    return items


def task_stats(task: dict) -> dict:
    subs = task.get("subtasks", [])
    total = len(subs)
    done = sum(1 for s in subs if s["mark"] == "x")
    todo = sum(1 for s in subs if s["mark"] == " ")
    blocked = sum(1 for s in subs if s["mark"] == "!")
    return {
        "total": total,
        "done": done,
        "todo": todo,
        "blocked": blocked,
        "all_done": (total > 0 and done == total),
        "partial": (total > 0 and 0 < done < total),
        "none_done": (total > 0 and done == 0),
    }


def counts(items: list[dict]) -> Counter:
    return Counter(item["mark"] for item in items)


def summary_text(items: list[dict]) -> str:
    c = counts(items)
    if CFG.get("language", "English") != "Thai":
        return f"Done {c['x']} · In progress {c['/']} · Blocked {c['!']} · Not started {c[' ']} ({len(items)} tasks)"
    return (
        f"เสร็จ {c['x']} · กำลังทำ {c['/']} · บล็อก {c['!']} · "
        f"ยังไม่เริ่ม {c[' ']} (รวม {len(items)} Task)"
    )


def status_rows_html(items: list[dict], indent: str = "        ") -> str:
    lines = []
    for item in items:
        cls, label = STATUS.get(item["mark"], ("todo", "ไม่ทราบสถานะ"))
        if CFG.get("language", "English") != "Thai":
            label = {"x": "Done", "/": "In progress", "!": "Blocked", " ": "Not started"}.get(item["mark"], "Unknown")
        name = html.escape(" ".join(p for p in (item["id"], item["title"]) if p))
        lines.append(
            f'{indent}<tr><td>{name}</td>'
            f'<td><span class="pill {cls}">{label}</span></td></tr>'
        )
    return "\n".join(lines)


def replace_block(text: str, markers: tuple[str, str], inner: str) -> tuple[str, bool]:
    begin, end = markers
    pattern = re.compile(re.escape(begin) + r"(.*?)" + re.escape(end), re.S)
    if not pattern.search(text):
        return text, False
    new = pattern.sub(lambda _m: f"{begin}{inner}{end}", text, count=1)
    return new, True


def read_block(text: str, markers: tuple[str, str]) -> str | None:
    begin, end = markers
    m = re.search(re.escape(begin) + r"(.*?)" + re.escape(end), text, re.S)
    return m.group(1) if m else None


def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def expected_blocks(items: list[dict]) -> dict[str, str]:
    return {
        "summary": summary_text(items),
        "rows": "\n" + status_rows_html(items) + "\n      ",
    }
