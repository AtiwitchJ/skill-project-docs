#!/usr/bin/env python3
"""Compare the Azure DevOps backlog with each phase's tasks.md. Read-only, both ways.

TASKS is the owner of task status. Azure DevOps is the backlog the project lead
reviews; this script never writes to Azure DevOps and never edits TASKS. It prints
the drift and exits 1 so the agent can fix TASKS or report the decision.

  python3 ado_drift.py --import <file>        # normalise MCP output into project/backlog/ado-snapshot.json
  python3 ado_drift.py                        # compare the snapshot with TASKS
  python3 ado_drift.py --stale-days 7         # also fail when the snapshot is older than 7 days
  python3 ado_drift.py --json                 # machine-readable result

Mapping lives in the docs, not in this script:

  tasks.md header:            > **ADO PBI:** #1234
  task body (not the header): **ADO:** #1301 · #1302

Many-to-many is allowed (one phase task covered by several ADO tasks, or the
reverse). Standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from docs_lib import parse_tasks_detailed, phases_present, tasks_path  # noqa: E402

from docs_lib import REPO  # noqa: E402
from layout import ADO, ADO_SNAPSHOT  # noqa: E402

SKILL = Path(__file__).resolve().parent.parent
SNAPSHOT = ADO_SNAPSHOT

PBI_RE = re.compile(r"ADO\s*PBI:\*\*.*?#(\d+)")
ADO_RE = re.compile(r"ADO:\*\*\s*#\s*(\d[\d,\s#]*)")
TASK_TYPES = {"Task", "Bug"}

# ADO state -> TASKS header mark. Anything else is reported, never guessed.
DONE = {"done", "closed", "resolved", "completed"}
DOING = {"active", "in progress", "doing", "started", "resolved in build"}
BLOCKED = {"blocked", "impediment"}
TODO = {"new", "approved", "committed", "to do", "proposed", "open", "ready"}

MARK_LABEL = {"x": "เสร็จ", "/": "กำลังทำ", "!": "บล็อก", " ": "ยังไม่เริ่ม"}


def expected_marks(state: str) -> set[str] | None:
    s = (state or "").strip().lower()
    if s in DONE:
        return {"x"}
    if s in DOING:
        return {"/", "!"}
    if s in BLOCKED:
        return {"!"}
    if s in TODO:
        return {" "}
    return None


def normalise(raw) -> dict:
    """Accept MCP search_workitem output ({"results": [...]}), a get_batch list, a flat item list,
    or an already-built snapshot. The MCP search returns lowercase field names (system.id), so
    every field is read case-insensitively."""
    if isinstance(raw, dict) and "items" in raw:
        raw_items = raw["items"]
        feature = raw.get("feature")
    elif isinstance(raw, dict) and "workItems" in raw:
        raw_items = raw["workItems"]
        feature = None
    elif isinstance(raw, dict) and "results" in raw:
        raw_items = raw["results"]
        feature = None
    else:
        raw_items = raw if isinstance(raw, list) else []
        feature = None

    items = []
    for it in raw_items:
        f = {str(k).lower(): v for k, v in it.get("fields", it).items()}
        wid = it.get("id") or f.get("system.id")
        if wid is None:
            continue
        parent = f.get("system.parent")   # not returned by search_workitem; None means "unknown"
        items.append(
            {
                "id": int(wid),
                "type": f.get("system.workitemtype", ""),
                "title": f.get("system.title", ""),
                "state": f.get("system.state", ""),
                "parent": int(parent) if parent is not None else None,
                "iteration": f.get("system.iterationpath", ""),
            }
        )
    if feature is None:
        f_item = next((i for i in items if i["type"] == "Feature"), None)
        feature = {"id": f_item["id"], "title": f_item["title"], "state": f_item["state"]} if f_item else None
    return {
        "fetched": datetime.now().astimezone().isoformat(timespec="seconds"),
        "organization": ADO.get("organization", ""),
        "project": ADO.get("project", ""),
        "feature": feature,
        "items": sorted(items, key=lambda i: i["id"]),
    }


def cmd_import(path: Path) -> int:
    raw = json.loads(path.read_text(encoding="utf-8"))
    snap = normalise(raw)
    if not snap["items"]:
        print(f"no work items in {path}", file=sys.stderr)
        return 1
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(json.dumps(snap, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    kinds: dict[str, int] = {}
    for i in snap["items"]:
        kinds[i["type"]] = kinds.get(i["type"], 0) + 1
    feat = snap["feature"]
    print(f"wrote {SNAPSHOT.relative_to(REPO)} · {len(snap['items'])} items "
          f"({', '.join(f'{v}× {k}' for k, v in sorted(kinds.items()))}) · "
          f"feature {('#' + str(feat['id']) + ' ' + feat['title']) if feat else 'ไม่พบ Feature'}")
    return 0


def task_map() -> tuple[dict[int, list[dict]], dict[int, int | None], list[str]]:
    """Return (ado_id -> tasks, phase -> PBI id, notes). One ADO item may cover several tasks."""
    by_ado: dict[int, list[dict]] = {}
    pbi_of: dict[int, int | None] = {}
    notes: list[str] = []
    for n in phases_present():
        p = tasks_path(n)
        if not p.exists():
            continue
        lines = p.read_text(encoding="utf-8").splitlines()
        m = PBI_RE.search("\n".join(lines[:10]))
        pbi_of[n] = int(m.group(1)) if m else None
        tasks = parse_tasks_detailed(p)
        for idx, t in enumerate(tasks):
            start = t["line_no"]
            end = tasks[idx + 1]["line_no"] - 1 if idx + 1 < len(tasks) else len(lines)
            ids = ADO_RE.search("\n".join(lines[start:end]))
            if not ids:
                continue
            ref = {"phase": n, "task": t["id"] or t["title"][:30], "mark": t["mark"], "line": t["line_no"]}
            for num in re.findall(r"\d+", ids.group(1)):
                by_ado.setdefault(int(num), []).append(ref)
    if not by_ado:
        notes.append("ยังไม่มี Task ใดผูกกับ ADO (ใส่ `**ADO:** #<id>` ใต้หัว Task)")
    return by_ado, pbi_of, notes


def compare(snap: dict) -> tuple[list[dict], list[str]]:
    by_ado, pbi_of, notes = task_map()
    items = {i["id"]: i for i in snap["items"]}
    rows: list[dict] = []

    for ado_id, refs in sorted(by_ado.items()):
        it = items.get(ado_id)
        if it is None:
            for t in refs:
                rows.append({"kind": "missing", "ado": ado_id, "where": f"Phase {t['phase']} Task {t['task']}",
                             "ado_state": "—", "mark": t["mark"],
                             "note": "ผูกไว้ใน TASKS แต่ไม่พบใน snapshot (ปิด/ลบใน ADO หรือ snapshot เก่า)"})
            continue
        allowed = expected_marks(it["state"])
        for t in refs:
            where = f"Phase {t['phase']} Task {t['task']}"
            if allowed is None:
                rows.append({"kind": "unknown-state", "ado": ado_id, "where": where,
                             "ado_state": it["state"], "mark": t["mark"],
                             "note": "สถานะ ADO ไม่รู้จัก: เพิ่มใน ado_drift.py หรือแก้สถานะใน ADO"})
            elif t["mark"] not in allowed:
                rows.append({"kind": "state-mismatch", "ado": ado_id, "where": where,
                             "ado_state": it["state"], "mark": t["mark"],
                             "note": f"ADO = {it['state']} แต่ TASKS = [{t['mark']}] {MARK_LABEL.get(t['mark'], '')}"})

    for i in snap["items"]:
        if i["type"] in TASK_TYPES and i["id"] not in by_ado:
            where = f"PBI #{i['parent']}" if i["parent"] else "parent ไม่ทราบ"
            rows.append({"kind": "unmapped-ado", "ado": i["id"], "where": where,
                         "ado_state": i["state"], "mark": "—",
                         "note": f"มีใน ADO แต่ยังไม่ผูกกับ Task ใด: {i['title'][:70]}"})

    pbi_ids = {i["id"] for i in snap["items"] if i["type"] == "Product Backlog Item"}
    for phase, pbi in sorted(pbi_of.items()):
        if pbi is None:
            notes.append(f"Phase {phase}: ยังไม่ระบุ `> **ADO PBI:** #<id>`")
        elif pbi not in pbi_ids:
            notes.append(f"Phase {phase}: PBI #{pbi} ไม่อยู่ใน snapshot (อาจอยู่ใต้ Feature อื่น)")
    for pbi in sorted(pbi_ids - {p for p in pbi_of.values() if p}):
        it = items[pbi]
        kids = sum(1 for i in snap["items"] if i["parent"] == pbi)
        notes.append(f"PBI #{pbi} {it['state']} · {kids} task ยังไม่ผูกกับ Phase ใด: {it['title'][:60]}")
    return rows, notes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--import", dest="import_file", metavar="FILE", help="normalise MCP output and save the snapshot")
    ap.add_argument("--stale-days", type=int, default=0, help="fail when the snapshot is older than N days")
    ap.add_argument("--json", action="store_true", help="print the result as JSON")
    args = ap.parse_args()

    if args.import_file:
        return cmd_import(Path(args.import_file))
    if not SNAPSHOT.exists():
        print("ยังไม่มี snapshot: รัน `ado_drift.py --import <file>` ด้วยผลจาก MCP azure-devops ก่อน")
        return 1

    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    fetched = datetime.fromisoformat(snap["fetched"]).date()
    age = (date.today() - fetched).days
    rows, notes = compare(snap)
    drift = [r for r in rows if r["kind"] in ("state-mismatch", "missing", "unknown-state")]
    stale = bool(args.stale_days) and age > args.stale_days

    if args.json:
        print(json.dumps({"age_days": age, "drift": drift, "unmapped": rows, "notes": notes},
                         ensure_ascii=False, indent=2))
    else:
        feat = snap.get("feature") or {}
        print(f"ADO {snap.get('project')} · Feature #{feat.get('id')} {feat.get('title', '')} "
              f"({feat.get('state', '?')}) · snapshot {fetched} ({age} วันก่อน)")
        for r in drift:
            print(f"DRIFT {r['ado']:>6} {r['where']}: {r['note']}")
        for r in rows:
            if r["kind"] == "unmapped-ado":
                print(f"FYI   {r['ado']:>6} {r['where']} [{r['ado_state']}]: {r['note']}")
        for n in notes:
            print(f"NOTE  {n}")
        if not drift:
            print("ไม่มีความขัดแย้งระหว่าง ADO กับ TASKS")
        if stale:
            print(f"ANDON snapshot เก่า {age} วัน (เกิน {args.stale_days}): ดึง ADO ใหม่")

    return 1 if drift or stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
