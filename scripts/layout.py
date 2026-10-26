"""Where things live in the documented project. The only file that spells out paths.

Every other script imports from here, so moving a folder means editing this file and
`.project-docs/owner-map.md`, nothing else. Standard library only.
"""
from __future__ import annotations

import json
from pathlib import Path

MARKERS = (".project-docs/config.json", "project/roadmap.md")   # first one is the current marker


def find_repo() -> Path:
    """Locate the project root the skill is documenting.

    Walk up from the current directory looking for a marker file (so the scripts work from
    any subfolder of the project), then fall back to walking up from the skill's own location.
    """
    # The directory the command runs in wins; the script's own location only matters when the
    # skill happens to sit inside the project (it is normally global, in ~/.agents/skills).
    cwd = Path.cwd().resolve()
    here = Path(__file__).resolve()
    for start in (cwd, here):
        for parent in (start, *start.parents):
            if any((parent / m).exists() for m in MARKERS):
                return parent
    raise SystemExit(
        f"cannot find the project root: no {MARKERS[0]} in this directory or any parent.\n"
        "These scripts document a project, so run them from that project's root "
        "(the skill is global, in ~/.agents/skills/project-docs/). "
        "New project? Run: python3 ~/.agents/skills/project-docs/scripts/init_project.py"
    )


REPO = find_repo()

# Per-project settings and rules live with the project, next to its data; the skill itself is global.
PROJECT_DOCS = REPO / ".project-docs"
CONFIG_FILE = PROJECT_DOCS / "config.json"
CFG: dict = json.loads(CONFIG_FILE.read_text(encoding="utf-8")) if CONFIG_FILE.exists() else {}
PROJECT_NAME: str = CFG.get("project_name", REPO.name)
ADO: dict = CFG.get("ado", {})
OWNER_MAP = PROJECT_DOCS / "owner-map.md"
GLOSSARY = PROJECT_DOCS / "glossary.md"
STALE_FILE = PROJECT_DOCS / "stale-patterns.json"
POLICY_FILE = PROJECT_DOCS / "flow-policy.json"
DIAGRAMS = PROJECT_DOCS / "diagrams"   # diagram specs (JSON); build_diagram.py writes the .excalidraw they name

# docs/ is for readers who want to understand or use the system (Diátaxis quadrants).
DOCS = REPO / "docs"
DOCS_QUADRANTS = {
    "tutorials": "Tutorial",
    "how-to": "How-to",
    "reference": "Reference",
    "explanation": "Explanation",
}

# project/ is the overview and tracking of the project itself.
PROJECT = REPO / "project"
ROADMAP_MD = PROJECT / "roadmap.md"
ROADMAP_HTML = PROJECT / "roadmap.html"
ISSUES = PROJECT / "issues.md"
PHASES = PROJECT / "phases"
BACKLOG = PROJECT / "backlog"
ADO_SNAPSHOT = BACKLOG / "ado-snapshot.json"
DECISIONS = PROJECT / "decisions"
RESULTS = PROJECT / "results"
CHARTS = RESULTS / "charts"

# Data written by the scripts; nobody reads it by hand.
FLOW_LOG = PROJECT_DOCS / "flow-log.jsonl"

MEMORY_BANK = REPO / "memory-bank"
PROGRESS = MEMORY_BANK / "progress.md"

# Inside the skill itself (reached through symlinks from every agent's skill folder, so resolve first).
SKILL = Path(__file__).resolve().parent.parent
RULES = SKILL / "rules"
INTEGRATIONS = SKILL / "integrations"
TEMPLATES = SKILL / "templates"
PROJECT_TEMPLATE = TEMPLATES / "project"
PRESENTATION_TEMPLATE = TEMPLATES / "presentation-template.html"


def rel(path: Path) -> str:
    """Repo-relative POSIX path, for messages and for matching git output."""
    return path.resolve().relative_to(REPO).as_posix()


def phase_dir(phase: int) -> Path:
    return PHASES / f"phase-{phase}"


def tasks_path(phase: int) -> Path:
    return phase_dir(phase) / "tasks.md"


def presentation_path(phase: int) -> Path:
    return phase_dir(phase) / "presentation.html"


def deliverable_path(phase: int) -> Path:
    return phase_dir(phase) / "deliverable.md"


def phases_present() -> list[int]:
    found = []
    for d in sorted(PHASES.glob("phase-*")):
        try:
            found.append(int(d.name.split("-", 1)[1]))
        except ValueError:
            continue
    return found
