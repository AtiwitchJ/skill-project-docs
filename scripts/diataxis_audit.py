#!/usr/bin/env python3
"""Check that each reader-facing page serves one Diataxis quadrant.

Every page under docs/tutorials/, docs/how-to/, docs/reference/ and docs/explanation/ declares its
quadrant in the header block:

    > **Diátaxis:** Reference

This script detects the signals a page actually has and compares them with the
declaration. Mismatch or no declaration is a WARN (a decision for the project lead);
two strong quadrant signals in one page is a split candidate. The folder is part of the
declaration: a page in docs/how-to/ must declare How-to (layout.DOCS_QUADRANTS), or it is
in the wrong place.

  python3 diataxis_audit.py                 # human-readable report, exit 1 on split candidates
  python3 diataxis_audit.py --json
  python3 diataxis_audit.py --path docs/explanation/architecture.md

project/ and memory-bank/ are not Diataxis documents and are skipped.
Standard library only; read-only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from docs_lib import REPO  # noqa: E402
from layout import DOCS, DOCS_QUADRANTS  # noqa: E402

SCOPE = ["docs/tutorials/**/*.md", "docs/how-to/**/*.md", "docs/reference/**/*.md", "docs/explanation/**/*.md"]
DECL_RE = re.compile(r"\*\*Di[áa]taxis:\*\*\s*(\w[\w-]*)", re.I)
QUADRANTS = {"tutorial", "how-to", "reference", "explanation"}

# Structural signals. Each entry: (quadrant, weight, regex). Scores are counts of
# matching lines normalised per 100 visible lines, so a long reference page is not
# classified reference just because it is long.
SIGNALS = [
    ("tutorial", 4, r"^#{2,4}\s*(?:[^\w\s]{0,3}\s*)?ขั้นที่\s*\d"),
    ("tutorial", 3, r"^(##+\s*)?(ขั้นตอนแรก|Step\s*1\b)"),
    ("tutorial", 3, r"ผลที่ควรเห็น|you'?ll see|ควรเห็นผล"),
    ("tutorial", 3, r"\bwe will\b|\blet'?s\b|คุณจะเห็น|you'?ll (see|notice)"),
    ("how-to", 3, r"^#{2,4}\s*(?:[^\w\s]{0,3}\s*)?(?:\d+[.)]\s*)?(Step\s*\d|To |วิธี|การรัน|การตั้งค่า|การติดตั้ง|การนำเข้า|การสร้าง|รัน|ติดตั้ง|ตั้งค่า|Prerequisite|ขั้นตอน)"),
    ("how-to", 3, r"^```(bash|sh|shell)\b"),
    ("how-to", 3, r"^#{2,4}\s*[^\w\s]{0,3}\s*(?:การ(?:เตรียม|รัน|ตั้งค่า|ติดตั้ง|ทดสอบ|พัฒนา|นำเข้า|สร้าง|เชื่อมต่อ|ตรวจสอบ)|วิธี|ขั้นตอน)"),
    ("how-to", 2, r"^\s*\$\s+\S|^\s*(python3?|npm|npx|pip|go|gcloud|az)\s"),
    ("explanation", 4, r"ทำไม|เพราะฉะนั้น|เหตุผลที่|แนวคิด|เปรียบเหมือน|trade-?off|the reason"),
    ("explanation", 5, r"^#{2,5}.*?(ทำความเข้าใจ|ผ่าลึก|เจาะลึก|เปรียบเหมือน|ทำไม|บทสรุป)"),
    ("explanation", 2, r"^#{2,4}\s*.*(ทำไม|Why|แนวคิด|ภาพรวม|Overview|หลักการ|เปรียบเทียบ|สรุป)"),
    ("explanation", 3, r"type=\"text/x-mermaid\"|```mermaid"),
]

MIN_SIGNAL = 2.5      # below this the page cannot be classified
# A page that is mostly tables is reference whatever else it says; a table is a format,
# and a how-to or explanation that happens to use one is still a how-to or explanation.
TABLE_SHARE = 0.45
MIXED_RATIO = 0.75    # second quadrant this close to the top means two jobs in one page


def visible_lines(text: str) -> list[str]:
    out, fence = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fence = not fence
            continue
        if not fence:
            out.append(line)
    return out


def score(text: str) -> dict[str, float]:
    lines = visible_lines(text)
    n = max(len(lines), 1)
    raw = {q: 0 for q in QUADRANTS}
    for q, w, rx in SIGNALS:
        r = re.compile(rx, re.M | re.I)
        raw[q] += w * sum(1 for line in lines if r.search(line))

    # A table is reference evidence only when it is the page's subject. Inside a section that is
    # explaining ("ทำความเข้าใจ", "ทำไม", "เปรียบเหมือน") or walking a procedure ("Step 1",
    # "ขั้นตอนที่ 3", "1.1 …") the table is the medium of that job, not a lookup surface.
    # Section state is inherited by deeper headings, so `### 1.1` under `## Step 1` stays a step.
    why_heading = re.compile(r"^#{2,5}\s*.*?(ทำความเข้าใจ|ผ่าลึก|เจาะลึก|เปรียบเหมือน|ทำไม|บทสรุป|ตามลำดับ)")
    step_heading = re.compile(r"^#{2,5}\s*(?:[^\w\s]{0,3}\s*)?(?:\d+(?:\.\d+)*[.):]?\s*)?"
                              r"(Step\s*\d|ขั้น|วิธี|การ\w+|Prerequisite|Troubleshoot|แก้ปัญหา|ตั้งค่า|เตรียม|สร้าง|รัน|นำเข้า|อัปโหลด|ทดสอบ|Checklist|ภาพรวมขั้นตอน|ขั้นตอนการ)")
    spec_heading = re.compile(r"^#{2,5}\s*.*?(ตาราง|Table|Matrix|Spec|สเปก|Schema|Compatibility)")
    # A table of contents / "where to find X" table is navigation, not reference data: it carries
    # no facts of its own and every cell is a link.
    nav_heading = re.compile(r"^#{2,5}\s*.*?(สารบัญ|นำทาง|หาเรื่อง|Contents|Navigation)")
    # level -> "why" | "step" | "spec" | "subject". Inheritance is sticky: a heading with no
    # signal of its own keeps the kind of the section it sits in, so `##### Variant A …` under
    # an explanation sub-step stays part of that explanation. Only an explicit heading changes it.
    kind_at: dict[int, str] = {}
    for line in lines:
        h = re.match(r"^(#{2,5})\s", line)
        if h:
            level = len(h.group(1))
            # headings often start with an anchor tag (`## <a id="x"></a>5. …`); strip it so the
            # section-kind patterns see the words, not the markup
            line = re.sub(r"^#{2,5}\s*(?:<a\b[^>]*>\s*</a>\s*)*", "#" * level + " ", line)
            if nav_heading.match(line):
                kind = "nav"
            elif why_heading.match(line):
                kind = "why"
            elif spec_heading.match(line):
                kind = "spec"
            elif step_heading.match(line):
                kind = "step"
            else:
                parent = [k for k in sorted(kind_at) if k < level]
                kind = kind_at[parent[-1]] if parent else "subject"
            kind_at[level] = kind
            raw["reference" if kind == "spec" else "explanation"] += 4 if kind in ("spec", "why") else 0
            for deeper in [k for k in kind_at if k > level]:
                del kind_at[deeper]
        elif kind_at and kind_at[max(kind_at)] in ("subject", "spec"):
            # structural reference evidence: tables, definition lists, ALL_CAPS keys
            if re.match(r"^\s*\|.*\|.*\|", line):
                raw["reference"] += 3
            elif re.match(r"^\s*[-*]\s+`[^`]+`\s*[—:–-]", line):
                raw["reference"] += 3
            elif re.match(r"^\s*\|?\s*`?[A-Z][A-Z0-9_]{2,}`?\s*\|", line):
                raw["reference"] += 2

    rows = sum(1 for line in lines if re.match(r"^\s*\|.*\|.*\|", line))
    if not kind_at and rows >= max(3, n // 4):
        raw["reference"] += 4
    scores = {q: round(100 * v / n, 1) for q, v in raw.items()}
    return scores


def classify(scores: dict[str, float]) -> tuple[str | None, str]:
    ranked = sorted(scores, key=lambda q: scores[q], reverse=True)
    top, second = ranked[0], ranked[1]
    if scores[top] < MIN_SIGNAL:
        return None, "สัญญาณน้อยเกินกว่าจะจำแนก"
    if scores[second] >= MIXED_RATIO * scores[top] and scores[second] >= MIN_SIGNAL:
        return top, f"สัญญาณผสม: {top} {scores[top]} vs {second} {scores[second]}"
    return top, f"{top} {scores[top]} (ที่สอง {second} {scores[second]})"


def audit(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    head = "\n".join(text.splitlines()[:12])
    m = DECL_RE.search(head)
    declared = m.group(1).lower().replace("howto", "how-to") if m else None
    scores = score(text)
    detected, why = classify(scores)
    issues = []
    if declared and declared not in QUADRANTS:
        issues.append(f"ประกาศ quadrant ที่ไม่รู้จัก: {declared}")
    if not declared:
        issues.append("ไม่ประกาศ **Diátaxis:** ในหัวไฟล์")
    elif detected and declared != detected:
        issues.append(f"ประกาศ {declared} แต่สัญญาณเป็น {detected} ({why})")
    if "ผสม" in why:
        issues.append(f"ควรแยกหน้า: {why}")
    folder = None
    try:
        folder = path.resolve().relative_to(DOCS).parts[0]
    except ValueError:
        pass
    expected = DOCS_QUADRANTS.get(folder, "").lower() if folder else ""
    folder_mismatch = bool(declared and expected and declared != expected)
    if folder_mismatch:
        issues.append(f"ประกาศ {declared} แต่อยู่ในโฟลเดอร์ {folder}/ ซึ่งเป็นของ {expected}")
    return {
        "folder": folder,
        "folder_mismatch": folder_mismatch,
        "file": str(path.relative_to(REPO)),
        "declared": declared,
        "detected": detected,
        "why": why,
        "scores": scores,
        "issues": issues,
    }


def audit_all() -> list[dict]:
    """Every reader-facing page, for check_docs.py. Never raises on a missing file."""
    paths = sorted({p for glob in SCOPE for p in REPO.glob(glob) if p.is_file()})
    return [audit(p) for p in paths]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--path", action="append", help="check only this file (repeatable)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    rows = [audit(Path(p) if Path(p).is_absolute() else REPO / p) for p in args.path if
            (Path(p) if Path(p).is_absolute() else REPO / p).exists()] if args.path else audit_all()
    splits = [r for r in rows if any("ควรแยกหน้า" in i for i in r["issues"])]
    undeclared = [r for r in rows if not r["declared"]]
    mismatch = [r for r in rows if r["declared"] and r["detected"] and r["declared"] != r["detected"]]

    if args.json:
        print(json.dumps({"pages": rows, "splits": [r["file"] for r in splits]}, ensure_ascii=False, indent=2))
    else:
        for r in rows:
            mark = "SPLIT" if any("ควรแยกหน้า" in i for i in r["issues"]) else ("WARN " if r["issues"] else "OK   ")
            print(f"{mark} {r['file']}: declared={r['declared'] or '—'} detected={r['detected'] or '—'} · {r['why']}")
            for i in r["issues"]:
                print(f"      {i}")
        print(f"\n{len(rows)} หน้า · {len(splits)} ควรแยก · {len(undeclared)} ไม่ประกาศ · {len(mismatch)} ประกาศไม่ตรงสัญญาณ")
    wrong_folder = [r for r in rows if r.get("folder_mismatch")]
    return 1 if splits or wrong_folder else 0


if __name__ == "__main__":
    raise SystemExit(main())
