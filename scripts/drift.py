#!/usr/bin/env python3
"""List what the docs are behind on, as change-router work items.

Looks at files changed since the last finished docs task in .project-docs/flow-log.jsonl
(commits since then plus uncommitted changes), generated files older than their
inputs, and the sync/gate checks. Prints one line per item with its router letter.

  python3 drift.py                 # since the last finished flow-log task
  python3 drift.py --since 8b11382 # since a git ref
  python3 drift.py --since "2 days ago"

Exit 0 when nothing is pending, 1 otherwise. Standard library only; read-only.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_docs  # noqa: E402
from docs_lib import REPO, phases_present, presentation_path  # noqa: E402

from docs_lib import REPO  # noqa: E402
from layout import ADO_SNAPSHOT, CFG, DOCS_QUADRANTS, FLOW_LOG  # noqa: E402

LOG = FLOW_LOG

# (glob, router letter, what to do). First match wins. These follow the standard layout;
# project-specific routes, pairs and generated files come from .project-docs/config.json -> drift.
ROUTES = [
    ("project/backlog/ado-snapshot.json", "J", "backlog refreshed: re-map ids in TASKS, report drift"),
    (".agents/*", None, ""),
    ("memory-bank/*", "M", "memory-bank changed: sync_memory_bank.py, then check the prose against TASKS"),
    ("project/phases/*/tasks.md", "B", "task status: presentation, roadmap, memory-bank, ADO ids"),
    ("project/issues.md", "D", "issue changed: linked tasks and memory-bank blockers"),
    *[(f"docs/{folder}/*", "K", "reader-facing page: does it still declare one Diataxis quadrant?") for folder in DOCS_QUADRANTS],
    ("docs/*", None, ""),  # derived docs are the output of a sync, not a reason for one
    *[tuple(r) for r in CFG.get("drift", {}).get("routes", [])],
]

PAIRS = [("project/roadmap.md", "project/roadmap.html"),
         *[tuple(p) for p in CFG.get("drift", {}).get("pairs", [])]]

# generated file -> inputs; the generator is rerun when an input is newer (by last commit or mtime)
GENERATED = dict(CFG.get("drift", {}).get("generated", {}))


def run_py(script: str, *args: str) -> tuple[int, str]:
    r = subprocess.run([sys.executable, str(Path(__file__).resolve().parent / script), *args],
                       cwd=REPO, capture_output=True, text=True)
    return r.returncode, r.stdout


def _page_role_ok(path: str) -> bool:
    """A reader-facing page needs no work when its declaration matches what it reads as."""
    try:
        import diataxis_audit
    except ImportError:
        return False
    target = REPO / path
    if not target.is_file():
        return True
    row = diataxis_audit.audit(target)
    return bool(row["declared"]) and row["declared"] == (row["detected"] or row["declared"])


def git(*args: str) -> str:
    r = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def last_sync() -> str | None:
    if not LOG.exists():
        return None
    done = [json.loads(l) for l in LOG.read_text(encoding="utf-8").splitlines() if l.strip()]
    done = [e["finished"] for e in done if e.get("finished")]
    return max(done) if done else None


def changed_since(since: str | None) -> set[str]:
    files: set[str] = set()
    if since:
        is_ref = bool(git("rev-parse", "--verify", "--quiet", since + "^{commit}").strip())
        out = git("diff", "--name-only", f"{since}..HEAD") if is_ref else \
            git("log", f"--since={since}", "--name-only", "--pretty=format:")
        files.update(l for l in out.splitlines() if l.strip())
    for line in git("status", "--porcelain", "--untracked-files=all").splitlines():
        files.add(line[3:].split(" -> ")[-1].strip('"'))
    return {f for f in files if (REPO / f).exists()}


def route(path: str):
    for glob, letter, todo in ROUTES:
        if fnmatch.fnmatch(path, glob):
            return letter, todo
    return None, ""


def stamp(path: str) -> float:
    # last commit time if committed and clean, else mtime (uncommitted edits are newer than any commit)
    dirty = git("status", "--porcelain", "--", path).strip()
    t = git("log", "-1", "--format=%ct", "--", path).strip()
    return (REPO / path).stat().st_mtime if dirty or not t else float(t)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", help="git ref or date; default: last finished task in flow-log")
    args = ap.parse_args()
    since = args.since or last_sync()
    files = changed_since(since)
    items: list[tuple[str, str, str]] = []

    for f in sorted(files):
        letter, todo = route(f)
        if not letter:
            continue
        if letter == "K" and _page_role_ok(f):
            continue          # the page already declares its quadrant correctly
        items.append((letter, f, todo))
    for md, html in PAIRS:
        if (md in files) != (html in files):
            items.append(("G", md if md in files else html, f"pair not changed together with {html if md in files else md}"))
    for out, inputs in GENERATED.items():
        # the generator is a script under scripts/ or a diagram spec under .project-docs/diagrams/ (build_diagram.py)
        if out in files and not any(i.startswith(("scripts/", ".project-docs/diagrams/")) and i in files for i in inputs):
            items.append(("H", out, "generated file changed without its generator: move the edit into the script or the spec"))
        if (REPO / out).exists():
            newer = [i for i in inputs if (REPO / i).exists() and stamp(i) > stamp(out)]
            if newer:
                items.append(("H", out, f"older than {', '.join(newer)}: regenerate"))

    if subprocess.run([sys.executable, str(Path(__file__).parent / "sync_tasks.py"), "--all", "--check"],
                      cwd=REPO, capture_output=True).returncode:
        items.append(("B", "TASKS", "task headers out of sync with subtasks: sync_tasks.py --all"))
    for n in phases_present():
        if presentation_path(n).exists() and subprocess.run(
                [sys.executable, str(Path(__file__).parent / "sync_presentation.py"), str(n), "--check"],
                cwd=REPO, capture_output=True).returncode:
            items.append(("B", f"phase {n}", f"presentation AUTO blocks out of date: sync_presentation.py {n}"))
    for level, where, msg in check_docs.run():
        if level in ("ERROR", "WARN"):
            items.append(("gate", where, f"{level}: {msg}"))

    snap = ADO_SNAPSHOT
    if snap.exists():
        code, out = run_py("ado_drift.py", "--json")
        try:
            drift = json.loads(out) if code in (0, 1) else {}
        except json.JSONDecodeError:
            drift = {}
        if drift.get("drift"):
            items.append(("J", "ADO", f"{len(drift['drift'])} work item(s) disagree with TASKS: ado_drift.py"))
        if drift.get("age_days", 0) > 7:
            items.append(("J", "ADO", f"snapshot is {drift['age_days']} days old: refresh before reporting status"))

    print(f"since: {since or '(no flow-log entry; uncommitted changes only)'}")
    if not items:
        print("docs are up to date")
        return 0
    order = "ABCDEFGHI"
    for letter, where, todo in sorted(items, key=lambda i: (order.find(i[0]) % 99, i[1])):
        print(f"{letter:5} {where}: {todo}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
