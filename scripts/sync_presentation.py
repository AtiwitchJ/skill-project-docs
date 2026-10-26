#!/usr/bin/env python3
"""Sync phase Markdown/HTML progress flows, evidence charts and status summaries.

Only AUTO blocks and generated SVGs are touched; manual narrative is preserved.

  python3 sync_presentation.py 2             # update phase 2 presentation in place
  python3 sync_presentation.py 2 --check     # exit 1 if out of date, change nothing
  python3 sync_presentation.py 3 --new       # scaffold phase 3 from the template
  python3 sync_presentation.py --all --check # check both formats/assets for all phases
"""
from __future__ import annotations

import argparse
import html
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
    parse_tasks_detailed,
    phases_present,
    presentation_path,
    read_block,
    replace_block,
    tasks_path,
)
from layout import PRESENTATION_TEMPLATE, REPO, CFG  # noqa: E402
import phase_visuals  # noqa: E402

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
    if CFG.get("language") == "Thai":
        labels = {
            "Follow the route, inspect the evidence": "ติดตามเส้นทางและตรวจหลักฐาน",
            "See the active and blocked steps.": "ดูขั้นตอนที่กำลังทำและติดบล็อก",
            "Verified tasks and remaining work stay visible.": "เห็นงานที่ตรวจแล้วและสิ่งที่ยังค้าง",
            "Use the evidence to answer the phase question.": "ใช้หลักฐานตอบคำถามของ Phase",
            "Make the boundary of the evidence explicit.": "ระบุขอบเขตของหลักฐานให้ชัดเจน",
            "Identify the decision or action that unblocks the route.": "ระบุผู้ตัดสินใจและสิ่งที่ต้องทำเพื่อปลดบล็อก",
            "End with the next verifiable action.": "ส่งต่อพร้อมงานถัดไปที่ตรวจผลได้",
            "Task details and flow": "รายละเอียด Task และเส้นทาง", "Presentation controls": "ควบคุมการนำเสนอ",
            "Previous slide": "สไลด์ก่อนหน้า", "Next slide": "สไลด์ถัดไป", "Slide position": "ตำแหน่งสไลด์",
            "Slide index": "รายการสไลด์", "Evidence charts": "กราฟจากหลักฐาน",
            "Full screen unavailable": "ไม่สามารถเปิดเต็มจอ", "Full screen": "เต็มจอ", "Print / PDF": "พิมพ์ / PDF",
            "Read all": "อ่านทั้งหมด", "Present": "นำเสนอ", "Updated": "อัปเดต", "Phase route": "เส้นทาง Phase",
            "Task status": "สถานะ Task", "Verified evidence": "หลักฐานที่ตรวจแล้ว", "Limits and confidence": "ข้อจำกัดและความมั่นใจ",
            "Blockers and decisions": "สิ่งที่บล็อกและการตัดสินใจ", "Next steps": "งานถัดไป", "Decision needed:": "การตัดสินใจที่ต้องการ:",
            "Project plan": "แผนโครงการ", "Next action": "การดำเนินการถัดไป", "<th>Issue</th>": "<th>ประเด็น</th>",
            "<th>Owner</th>": "<th>ผู้ดำเนินการ</th>", "<th>Status</th>": "<th>สถานะ</th>",
            ">Cover<": ">หน้าปก<", ">Route<": ">เส้นทาง<", ">Tasks<": ">งาน<", ">Evidence<": ">หลักฐาน<", ">Limits<": ">ข้อจำกัด<", ">Blockers<": ">สิ่งที่บล็อก<", ">Next<": ">ถัดไป<",
            "Chart ${i+1}": "กราฟ ${i+1}",
        }
        for original in sorted(labels,key=len,reverse=True): text=text.replace(original,labels[original])
    subs = {
        "PHASE_NUMBER": str(phase),
        "PHASE_TITLE": html.escape(title_m.group(1)) if title_m else "TODO",
        "PERIOD": html.escape(period_m.group(1)) if period_m else "TODO",
        "UPDATED": thai_date(date.today()) if CFG.get("language") == "Thai" else date.today().isoformat(),
        "LANGUAGE": "th" if CFG.get("language") == "Thai" else "en",
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
    generated = phase_visuals.outputs(REPO, phase, parse_tasks_detailed(tasks_path(phase)))
    return phase_visuals.html_blocks(text, generated)


def is_current(phase: int, text: str) -> bool:
    items = parse_tasks(tasks_path(phase))
    blocks = expected_blocks(items)
    cur_s = read_block(text, AUTO_SUMMARY)
    cur_r = read_block(text, AUTO_ROWS)
    if cur_s is None or cur_r is None:
        return False
    norm = lambda s: re.sub(r"\s+", " ", s).strip()  # noqa: E731
    return (norm(cur_s) == norm(blocks["summary"]) and norm(cur_r) == norm(blocks["rows"])
            and not phase_visuals.stale(REPO, phase, parse_tasks_detailed(tasks_path(phase)), text))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("phase", type=int, nargs="?")
    ap.add_argument("--all", action="store_true", help="sync/check all phases")
    ap.add_argument("--check", action="store_true", help="report only; exit 1 if out of date")
    ap.add_argument("--new", action="store_true", help="create the presentation from the template")
    ap.add_argument("--force", action="store_true", help="with --new, overwrite an existing file")
    args = ap.parse_args()
    if (args.phase is None) == (not args.all):
        ap.error("give a phase number or --all")
    if args.check and args.new:
        ap.error("--check and --new cannot be combined")
    failed = 0
    for phase in phases_present() if args.all else [args.phase]:
        try:
            failed += sync_phase(phase, args.check, args.new, args.force)
        except (ValueError, KeyError, OSError) as exc:
            print(f"ERROR phase {phase}: {exc}")
            failed += 1
    return int(bool(failed))


def sync_phase(phase: int, check: bool = False, new: bool = False, force: bool = False) -> int:
    args = argparse.Namespace(phase=phase, check=check, new=new, force=force)

    if not tasks_path(args.phase).exists():
        print(f"ERROR: {tasks_path(args.phase)} not found. TASKS must exist before the presentation.")
        return 1

    if args.new:
        text = build(args.phase, scaffold(args.phase, args.force))
        phase_visuals.write(REPO, args.phase, parse_tasks_detailed(tasks_path(args.phase)))
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
    phase_visuals.write(REPO, args.phase, parse_tasks_detailed(tasks_path(args.phase)))
    if updated == current:
        print(f"phase {args.phase}: already up to date")
    else:
        path.write_text(updated, encoding="utf-8")
        print(f"phase {args.phase}: derived blocks updated in {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
