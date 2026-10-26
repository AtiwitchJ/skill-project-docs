#!/usr/bin/env python3
"""Gate for project docs. Run before reporting any docs task as done.

  python3 check_docs.py            # human-readable report
  python3 check_docs.py --phase 2  # limit phase checks to one phase

Exit code 1 if any ERROR (the Andon signal: stop and fix before handing over).
WARN items need a decision. A decision to keep one is recorded in
.project-docs/flow-policy.json -> accepted_warnings; it then prints as ACK.
Standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from docs_lib import (  # noqa: E402
    AUTO_ROWS,
    AUTO_SUMMARY,
    REPO,
    expected_blocks,
    parse_tasks,
    parse_tasks_detailed,
    task_stats,
    phases_present,
    presentation_path,
    read_block,
    tasks_path,
)
from layout import (  # noqa: E402
    ADO_SNAPSHOT,
    CFG,
    DIAGRAMS,
    ISSUES,
    OWNER_MAP,
    POLICY_FILE,
    ROADMAP_HTML,
    ROADMAP_MD,
    STALE_FILE,
)


REQUIRED_ROOT = [
    *(p.relative_to(REPO).as_posix() for p in (ROADMAP_MD, ROADMAP_HTML, ISSUES)),
    *CFG.get("required", []),
    "project/README.md",
    "docs/README.md",
    "memory-bank/activeContext.md",
    "memory-bank/progress.md",
]

MARK_OK_CHECKLIST = {" ", "x"}
MARK_OK_HEADER = {" ", "x", "/", "!"}

findings: list[tuple[str, str, str]] = []  # (level, where, message)


def add(level: str, where: str, msg: str) -> None:
    findings.append((level, where, msg))


def rel(p: Path) -> str:
    try:
        return str(p.relative_to(REPO))
    except ValueError:
        return str(p)


def check_structure(phases: list[int]) -> None:
    for f in REQUIRED_ROOT:
        if not (REPO / f).exists():
            add("ERROR", f, "required file missing")
    for n in phases:
        t, p = tasks_path(n), presentation_path(n)
        if not t.exists():
            add("ERROR", rel(t), "TASKS missing for this phase")
        if not p.exists():
            add("ERROR", rel(p), "PRESENTATION missing (run sync_presentation.py --new)")


def check_markers(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    for i, line in enumerate(text.splitlines(), 1):
        m = re.match(r"^\s*[-*]\s+\[(.)\]\s", line)
        if m and m.group(1) not in MARK_OK_CHECKLIST:
            hint = " (blocked item: keep [ ] and start with '⛔ บล็อก: <reason> (IMP-xxx)')" if m.group(1) == "!" else ""
            add("ERROR", f"{rel(path)}:{i}", f"checklist item uses [{m.group(1)}]; only [ ] and [x] are allowed here{hint}")
        h = re.match(r"^###\s+\[(.)\]\s", line)
        if h and h.group(1) not in MARK_OK_HEADER:
            add("ERROR", f"{rel(path)}:{i}", f"task header uses unknown marker [{h.group(1)}]")


def check_task_consistency(path: Path) -> None:
    """Verify that task header marks match the progress of subtask checklist items."""
    tasks = parse_tasks_detailed(path)
    for t in tasks:
        stats = task_stats(t)
        tid = t["id"] or t["title"][:25]
        line = t["line_no"]
        mark = t["mark"]
        if stats["total"] == 0:
            continue

        # Rule 1: All subtasks are done, but task header is not done
        if stats["all_done"] and mark != "x":
            add(
                "ERROR",
                f"{rel(path)}:{line}",
                f"Task {tid} has all {stats['total']} subtasks marked [x], but header is still [{mark}]; change header to [x] (or run sync_tasks.py)",
            )
        # Rule 2: Header is marked done, but some subtasks are still incomplete
        elif mark == "x" and stats["todo"] > 0:
            add(
                "ERROR",
                f"{rel(path)}:{line}",
                f"Task {tid} header is marked [x], but has {stats['todo']} incomplete subtasks [ ]; complete all subtasks or adjust header",
            )
        # Rule 3: Some subtasks are done, but header is still marked not-started [ ]
        elif mark == " " and stats["partial"]:
            add(
                "WARN",
                f"{rel(path)}:{line}",
                f"Task {tid} has {stats['done']}/{stats['total']} subtasks done [x], but header is still [ ]; change header to [/] or [!]",
            )


def check_wip(phase: int, items: list[dict], limit: int) -> None:
    doing = [i["id"] or i["title"][:30] for i in items if i["mark"] == "/"]
    if len(doing) > limit:
        add("WARN", rel(tasks_path(phase)),
            f"WIP limit: {len(doing)} tasks in progress (limit {limit}): {', '.join(doing)}; finish or mark blocked before starting more")


def check_tasks_vs_plan(phase: int, items: list[dict]) -> None:
    plan = ROADMAP_MD
    if not plan.exists():
        return
    needle = f"phase-{phase}/tasks.md"
    line = next((l for l in plan.read_text(encoding="utf-8").splitlines() if needle in l), None)
    if line is None:
        add("WARN", rel(plan), f"no roadmap row links to phase {phase} TASKS")
        return
    m = re.search(r"(\d+)/(\d+)", line)
    done = sum(1 for i in items if i["mark"] == "x")
    if not m:
        add("WARN", rel(plan), f"phase {phase} row has no done/total count")
    elif (int(m.group(1)), int(m.group(2))) != (done, len(items)):
        add("ERROR", rel(plan),
            f"phase {phase} shows {m.group(0)} but TASKS has {done}/{len(items)} done")


def check_presentation(phase: int) -> None:
    path = presentation_path(phase)
    if not path.exists():
        return
    where = rel(path)
    text = path.read_text(encoding="utf-8")
    import phase_visuals
    try:
        for problem in phase_visuals.stale(REPO, phase, parse_tasks_detailed(tasks_path(phase)), text):
            add("ERROR", where, problem+" (run sync_presentation.py)")
    except (ValueError, KeyError, OSError) as exc:
        add("ERROR", where, "phase visuals: "+str(exc))

    items = parse_tasks(tasks_path(phase))
    blocks = expected_blocks(items)
    cur_s, cur_r = read_block(text, AUTO_SUMMARY), read_block(text, AUTO_ROWS)
    if cur_s is None or cur_r is None:
        add("ERROR", where, "AUTO markers missing; add them from presentation-template.html")
    else:
        norm = lambda s: re.sub(r"\s+", " ", s).strip()  # noqa: E731
        if norm(cur_s) != norm(blocks["summary"]):
            add("ERROR", where, "summary line out of date with TASKS (run sync_presentation.py)")
        if norm(cur_r) != norm(blocks["rows"]):
            add("ERROR", where, "status table out of date with TASKS (run sync_presentation.py)")

    visible = re.sub(r"<(script|style|code|pre)\b.*?</\1>", "", text, flags=re.S | re.I)
    visible = re.sub(r"<!--.*?-->", "", visible, flags=re.S)
    visible = re.sub(r"<[^>]+>", " ", visible)
    if "`" in visible:
        add("ERROR", where, "backtick rendered as raw text; wrap the code in <code>")
    if re.search(r"\bTODO\b", text):
        add("ERROR", where, "TODO placeholder still present; fill every narrative slot")
    if "file:///" in text:
        add("ERROR", where, "file:/// link; use a relative path")
    started = sum(1 for i in items if i["mark"] in ("x", "/", "!"))
    if "Planned" in visible and started:
        add("WARN", where, f"'Planned' label still visible but {started} task(s) in TASKS have started")

    slides = re.findall(r'<section[^>]*\bclass="[^"]*\bslide\b[^"]*"[^>]*>(.*?)</section>', text, flags=re.S)
    if not slides:
        add("ERROR", where, "no <section class=\"slide\"> found")
    for idx, body in enumerate(slides, 1):
        if "<h2" not in body and "<h1" not in body:
            add("WARN", where, f"slide {idx} has no heading")
    # Slide number: '<p class="folio">02 · ...' or '<p class="slide-no">Slide 2'. The title slide may be unnumbered.
    num_re = re.compile(r'class="folio">\s*(\d+)\s*·|class="slide-no">\s*Slide\s+(\d+)')
    nums = []
    for idx, body in enumerate(slides):
        m = num_re.search(body)
        if m:
            nums.append(int(m.group(1) or m.group(2)))
        elif idx > 0:
            add("WARN", where, f"slide {idx + 1} has no slide number (folio '02 · ...' or slide-no 'Slide 2')")
    if nums and nums != list(range(1, len(nums) + 1)) and nums != list(range(nums[0], nums[0] + len(nums))):
        add("ERROR", where, f"slide numbers are not consecutive: {nums}")
    ids = re.findall(r'<section[^>]*\bid="([^"]+)"', text)
    for dup in sorted({i for i in ids if ids.count(i) > 1}):
        add("ERROR", where, f'duplicate slide id="{dup}"')
    for needle, what in (("prefers-reduced-motion", "reduced-motion rule"), ("@media print", "print rule")):
        if needle not in text:
            add("WARN", where, f"{what} missing")


def check_test_results() -> None:
    # Pages listed in config.json -> results_only show results and charts only; call flows belong in docs/explanation/
    for f in CFG.get("results_only", []):
        path = REPO / f
        if not path.exists():
            continue
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "sequenceDiagram" in line:
                add("ERROR", f"{f}:{i}", "sequence diagram on a results-only page; keep results and charts only, link to the explanation page")


def check_skills() -> None:
    """A broken SKILL.md silently drops the skill from the agent's list (router type L).

    Only findings inside the repo gate the docs; a duplicate that lives in the user's own
    skill directory is machine-specific and would make the gate fail on one laptop only.
    """
    import check_skills as skills

    for row in skills.scan():
        # A missing local patch is a real defect wherever the skill lives: the agent loads the
        # user copy, so a machine-level break still changes what this project is documented by.
        is_patch = "local addition" in row["msg"] or "is not installed in either skill root" in row["msg"]
        if row["level"] == "ERROR" and (row.get("scope") in ("repo", "both") or is_patch):
            add("ERROR", row["file"], row["msg"])
        elif row["level"] == "WARN" and row.get("scope") == "repo":
            add("WARN", row["file"], row["msg"])


def check_page_role() -> None:
    """Reader-facing pages declare one Diataxis quadrant; the installed diataxis skill owns the framework."""
    import diataxis_audit

    for row in diataxis_audit.audit_all():
        path = REPO / row["file"]
        if not row["declared"]:
            add("WARN", row["file"], "no '> **Diátaxis:** <quadrant>' in the header block (integrations/diataxis.md)")
        elif row["detected"] and row["declared"] != row["detected"]:
            add("WARN", row["file"], f"declares {row['declared']} but reads as {row['detected']} ({row['why']})")
        if any("ควรแยกหน้า" in i for i in row["issues"]):
            add("WARN", row["file"], f"two jobs in one page: {row['why']} (split per integrations/diataxis.md)")
        if row.get("folder_mismatch"):
            add("ERROR", row["file"], f"declares {row['declared']} but lives in docs/{row['folder']}/; move the page or fix the declaration")


NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*\.[a-z0-9]+$")
AGENT_TERMS = re.compile(r"memory[ -]?bank|flow-log|SKILL\.md|\.agents/skills|project-docs", re.I)


def check_names() -> None:
    """File names under docs/ and project/ are lower-case words joined by dashes (README.md excepted)."""
    for root in (REPO / "docs", REPO / "project"):
        for p in sorted(root.rglob("*")):
            if p.is_file() and not p.name.startswith(".") and p.name != "README.md" and not NAME_RE.match(p.name):
                add("ERROR", rel(p), "file name must be lower-case words joined by dashes (e.g. test-results.md)")


def check_human_pages(policy: dict) -> None:
    """Pages people read must not talk about the agent's own tooling."""
    exempt = set(policy.get("agent_pages", []))
    pages = [*(REPO / "docs").rglob("*.md"), REPO / "project" / "README.md", ROADMAP_MD, ROADMAP_HTML,
             *(REPO / "project" / "phases").glob("phase-*/presentation.html")]
    for p in sorted(set(pages)):
        if not p.exists() or rel(p) in exempt:
            continue
        for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            m = AGENT_TERMS.search(line)
            if m:
                add("WARN", f"{rel(p)}:{i}", f"agent-only term '{m.group(0)}' in a page people read; keep it in memory-bank/ or the skill")


def _covers(rel: str, pattern: str) -> bool:
    """True when a path in owner-map.md refers to this file. `N` and `*` stand for a phase number."""
    if "/" not in pattern or not pattern.endswith((".md", ".html", ".svg", ".json")):
        return False
    if pattern.startswith(("docs/**", "docs/*", "**/")):
        return False   # a catch-all, not a specific owner row
    rx = re.escape(pattern)
    rx = rx.replace(r"\*", "[^/]*")
    rx = re.sub(r"<?N>?", "[0-9]+", rx)      # phase-N/tasks.md and phase-N both become digits
    return re.fullmatch(rx, rel) is not None


def check_owner_map() -> None:
    """Every docs page appears in owner-map.md, or is exempt with a reason."""
    om = OWNER_MAP
    if not om.exists():
        add("WARN", ".project-docs/owner-map.md", "owner map missing; no page has a declared owner")
        return
    text = om.read_text(encoding="utf-8")
    for page in sorted((REPO / "docs").rglob("*.md")):
        rel = str(page.relative_to(REPO))
        if rel in text:
            continue
        # a pattern row covers its files: `docs/reference/*.md`, `phase-N/tasks.md`
        if any(_covers(rel, pat) for pat in re.findall(r"`([^`]+)`", text)):
            continue
        add("WARN", ".project-docs/owner-map.md", f"{rel} has no owner row (add one, or list it under Exempt)")


def check_diagrams() -> None:
    """Each diagram spec builds without problems, and its .excalidraw is exactly what that spec builds.

    Catches a hand edit to the picture, a spec changed without a rebuild, and a spec that breaks the
    geometry rules. A project without .project-docs/diagrams/ has nothing to check.
    """
    if not DIAGRAMS.is_dir():
        return
    import build_diagram  # next to this script; imported here so projects without diagrams never load it
    for spec_path in sorted(DIAGRAMS.glob("*.json")):
        where = rel(spec_path)
        try:
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as err:
            add("ERROR", where, f"cannot read the spec: {err}")
            continue
        if not spec.get("file"):
            add("ERROR", where, "spec has no 'file'")
            continue
        elements, drawing, problems = build_diagram.build(spec)
        problems += build_diagram.check(drawing)
        for problem in problems:
            add("ERROR", where, problem)
        if problems:
            continue
        target = REPO / spec["file"]
        rebuild = f"run build_diagram.py {where}"
        if not target.exists():
            add("ERROR", where, f"{spec['file']} is missing: {rebuild}")
            continue
        try:
            current = json.loads(target.read_text(encoding="utf-8")).get("elements")
        except (OSError, json.JSONDecodeError) as err:
            add("ERROR", where, f"{spec['file']} cannot be read: {err}")
            continue
        if json.dumps(current, sort_keys=True) != json.dumps(elements, sort_keys=True):
            add("ERROR", where, f"{spec['file']} is not what this spec builds: {rebuild}")


def check_memory_bank_counts() -> None:
    """progress.md phase counts are derived from TASKS; a hand-typed count must not survive (router M)."""
    progress = REPO / "memory-bank" / "progress.md"
    if not progress.exists():
        return
    markers = ("<!-- AUTO:phase-counts -->", "<!-- /AUTO:phase-counts -->")
    text = progress.read_text(encoding="utf-8")
    current = read_block(text, markers)
    if current is None:
        add("WARN", "memory-bank/progress.md",
            f"AUTO:phase-counts markers missing; counts are then unverified (run sync_memory_bank.py)")
        return
    import sync_memory_bank

    want = sync_memory_bank.expected()
    if " ".join(current.split()) != " ".join(want.split()):
        add("ERROR", "memory-bank/progress.md",
            "AUTO:phase-counts disagrees with TASKS (run sync_memory_bank.py; never hand-edit the block)")


def check_project_readme() -> None:
    """project/README.md's phase table is derived from the task files; a hand-typed table must not survive."""
    import sync_project_readme as spr

    if not spr.README.exists():
        return
    current = read_block(spr.README.read_text(encoding="utf-8"), spr.MARKERS)
    if current is None:
        add("WARN", rel(spr.README), "AUTO:phase-status markers missing; the phase table is then unverified (run sync_project_readme.py)")
    elif " ".join(current.split()) != " ".join(spr.expected().split()):
        add("ERROR", rel(spr.README), "AUTO:phase-status disagrees with the task files (run sync_project_readme.py; never hand-edit the block)")


def check_ado() -> None:
    """ADO mapping exists and the snapshot is not stale. Read-only; never contacts Azure DevOps."""
    if CFG.get("integrations", {}).get("connections"):
        import integration_core
        try:
            integration_core.configuration(REPO)
        except (ValueError, KeyError, OSError) as exc:
            add("ERROR", "integrations", str(exc))
            return
    if CFG.get("integrations", {}).get("primary"):
        import integration_core
        try:
            for row in integration_core.check(REPO):
                add("WARN", "integrations", json.dumps(row, ensure_ascii=False))
        except (ValueError, KeyError, OSError) as exc:
            add("ERROR", "integrations", str(exc))
        return
    if not CFG.get("ado"):        # this project does not use Azure DevOps
        return
    snap = ADO_SNAPSHOT
    if not snap.exists():
        add("WARN", str(snap.relative_to(REPO)), "no ADO snapshot; run ado_drift.py --import with MCP output (integrations/azure-devops.md)")
        return
    import ado_drift

    data = json.loads(snap.read_text(encoding="utf-8"))
    for row in ado_drift.compare(data)[0]:
        if row["kind"] == "state-mismatch":
            add("WARN", f"ADO #{row['ado']}", f"{row['where']}: {row['note']}")
        elif row["kind"] in ("missing", "unknown-state"):
            add("WARN", f"ADO #{row['ado']}", f"{row['where']}: {row['note']}")


def check_links(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    targets = re.findall(r"\]\(([^)\s]+)\)", text) + re.findall(r'(?:href|src)="([^"]+)"', text)
    for t in targets:
        if t.startswith(("http://", "https://", "mailto:", "#")) or "{{" in t:
            continue
        if t.startswith("file:"):
            add("ERROR", rel(path), f"file: link {t}")
            continue
        local = t.split("#", 1)[0].split("?", 1)[0]
        if not local:
            continue
        target = (path.parent / local) if not local.startswith("/") else (REPO / local.lstrip("/"))
        if not target.resolve().exists():
            add("ERROR", rel(path), f"broken link -> {t}")


def check_stale() -> None:
    cfg = json.loads(STALE_FILE.read_text(encoding="utf-8"))
    exempt = {REPO / e for e in cfg.get("exempt", [])}
    files: set[Path] = set()
    for glob in cfg["scope"]:
        files.update(p for p in REPO.glob(glob) if p.is_file())
    for f in sorted(files - exempt):
        lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        for pat in cfg["patterns"]:
            rx = re.compile(pat["regex"])
            for i, line in enumerate(lines, 1):
                if rx.search(line):
                    add("WARN", f"{rel(f)}:{i}", f"matches stale value /{pat['regex']}/: {pat['why']}")


def load_policy() -> dict:
    if POLICY_FILE.exists():
        return json.loads(POLICY_FILE.read_text(encoding="utf-8"))
    return {"wip_limit_per_phase": 1, "accepted_warnings": []}


def is_accepted(where: str, msg: str, accepted: list[dict]) -> dict | None:
    path = where.split(":", 1)[0]
    for a in accepted:
        if a.get("file") == path and a.get("message_contains", "") in msg:
            return a
    return None


def run(phases: list[int] | None = None) -> list[tuple[str, str, str]]:
    """Run every check and return findings; accepted WARNs come back as level ACK."""
    findings.clear()
    policy = load_policy()
    phases = phases if phases else phases_present()
    check_structure(phases)
    for n in phases:
        if tasks_path(n).exists():
            items = parse_tasks(tasks_path(n))
            check_markers(tasks_path(n))
            check_task_consistency(tasks_path(n))
            check_tasks_vs_plan(n, items)
            check_wip(n, items, int(policy.get("wip_limit_per_phase", 1)))
            check_links(tasks_path(n))
        check_presentation(n)
        if presentation_path(n).exists():
            check_links(presentation_path(n))
    for f in (ROADMAP_MD, ROADMAP_HTML):
        if f.exists():
            check_links(f)
    # every doc, project page and memory-bank file, not only the ones the phase loop touches
    for f in sorted([*(REPO / "docs").glob("**/*.md"), *(REPO / "docs").glob("**/*.html"),
                     *(REPO / "project").glob("**/*.md"), *(REPO / "project").glob("**/*.html"),
                     *(REPO / "memory-bank").glob("*.md")]):
        if f.is_file():
            check_links(f)
    check_test_results()
    check_skills()
    check_page_role()
    check_names()
    check_human_pages(policy)
    check_ado()
    check_memory_bank_counts()
    check_project_readme()
    check_owner_map()
    check_diagrams()
    check_stale()

    accepted = policy.get("accepted_warnings", [])
    out = []
    for level, where, msg in findings:
        a = is_accepted(where, msg, accepted) if level == "WARN" else None
        out.append(("ACK", where, f"{msg} [accepted: {a.get('reason', '')}]") if a else (level, where, msg))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phase", type=int, help="check only this phase")
    args = ap.parse_args()
    phases = [args.phase] if args.phase else phases_present()
    results = run(phases)
    counts = {k: sum(1 for r in results if r[0] == k) for k in ("ERROR", "WARN", "ACK")}
    for level, where, msg in results:
        print(f"{level:5} {where}: {msg}")
    print(f"\n{counts['ERROR']} error(s), {counts['WARN']} warning(s), {counts['ACK']} accepted across phases {phases or '[]'}")
    if counts["ERROR"]:
        print("ANDON: gate failed. Stop the flow: fix the errors (or log an issue) before reporting the task done.")
    return 1 if counts["ERROR"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
