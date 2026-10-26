#!/usr/bin/env python3
"""Validate the skills in this repo and in the user's skill directory so an edited skill still loads.

A skill disappears from the agent's list, or loads an old copy, when:
  - its YAML frontmatter does not parse (an unquoted ': ' in description is enough),
  - two directories in the same skill root declare the same name,
  - a directory under .agents/skills/ has no SKILL.md (an eval workspace, snapshot or
    pristine copy left there shadows the real skill),
  - a SKILL.md is nested inside another skill instead of living at <name>/SKILL.md,
  - a stale copy in ~/.agents/skills/ carries broken frontmatter (the agent falls back
    to it or drops the name entirely),
  - a local addition to a third-party skill was wiped by an upstream reinstall
    (see LOCAL_PATCHES below).

  python3 check_skills.py                   # repo + user level
  python3 check_skills.py --no-user         # repo only
  python3 check_skills.py --json

A name declared at both levels is a WARN, not an ERROR: the project copy wins, but the
two copies drift and the user edits the wrong one. A name declared twice inside one
level is an ERROR. Standard library only; read-only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from docs_lib import REPO  # noqa: E402

SKILLS = REPO / ".agents" / "skills"
USER_SKILLS = Path.home() / ".agents" / "skills"
FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)

# Third-party skills are never edited (see the README). Project rules live in project-docs references,
# so nothing is listed here; an entry would mean a local patch crept back into an upstream SKILL.md.
LOCAL_PATCHES: dict[str, list[tuple[str, str]]] = {}


def parse_frontmatter(text: str) -> tuple[dict, str | None]:
    """Minimal frontmatter reader: enough to catch what stops a skill from loading."""
    m = FM_RE.match(text)
    if not m:
        return {}, "no frontmatter block (--- ... ---)"
    fields: dict[str, str] = {}
    key: str | None = None
    block: str | None = None   # set when the value is a YAML block scalar (> or |)
    for line in m.group(1).splitlines():
        if not line.strip():
            continue
        if block and line[:1] in (" ", "\t"):
            continue            # continuation of a block scalar
        if re.match(r"^[A-Za-z_-]+:", line):
            key, _, value = line.partition(":")
            key, value = key.strip(), value.strip()
            fields[key] = value
            block = value if value[:1] in (">", "|") else None
        elif key and line[:1] in (" ", "\t"):
            fields[key] = (fields[key] + " " + line.strip()).strip()
            block = None
        else:
            return {}, f"line outside any key: {line[:40]}"
    for k, v in fields.items():
        if v[:1] in (">", "|"):
            continue            # block scalar: quotes inside are literal
        if v.startswith('"') or v.endswith('"'):
            if not (v.startswith('"') and v.endswith('"')) or len(v) == 1:
                return fields, f"{k}: unbalanced double quote"
            if '"' in v[1:-1].replace('\\"', ""):
                return fields, f'{k}: inner double quote breaks the value; use single quotes or escape it'
        elif ": " in v:
            return fields, f"{k}: contains ': ' and is not quoted; YAML reads it as a nested mapping"
    return fields, None


def _label(path: Path) -> str:
    """Readable location: repo-relative inside the repo, ~-relative outside it."""
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        pass
    try:
        return "~/" + str(path.relative_to(Path.home()))
    except ValueError:
        return str(path)


def _collect(root: Path, rows: list[dict], scope: str) -> dict[str, str]:
    """Validate one skill root; return name -> file for cross-root duplicate detection."""
    seen: dict[str, str] = {}
    if not root.exists():
        if scope != "repo":      # a project may keep no skills of its own: the project-docs skill is global
            rows.append({"file": _label(root), "level": "ERROR", "scope": scope,
                         "msg": "skills directory missing"})
        return seen

    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        if not (d / "SKILL.md").exists():
            nested = sorted(d.rglob("SKILL.md"))
            hint = f" (contains {len(nested)} nested SKILL.md: {_label(nested[0].parent)})" if nested else ""
            rows.append({"file": _label(d), "level": "ERROR", "scope": scope,
                         "msg": f"directory has no SKILL.md and shadows a skill{hint}"})

    checked: set[Path] = set()
    for md in sorted(root.rglob("SKILL.md")):
        real = md.resolve()
        if real in checked:
            continue                       # a symlink to a skill already checked here
        checked.add(real)
        rel = _label(md)
        if md.parent.parent != root:
            rows.append({"file": rel, "level": "ERROR", "scope": scope,
                         "msg": f"SKILL.md not directly under {_label(root)}/<name>/"})
        fields, err = parse_frontmatter(real.read_text(encoding="utf-8"))
        if err:
            rows.append({"file": rel, "level": "ERROR", "scope": scope, "msg": f"frontmatter: {err}"})
            continue
        name = fields.get("name", "").strip().strip('"')
        if not name:
            rows.append({"file": rel, "level": "ERROR", "scope": scope, "msg": "frontmatter has no name"})
        else:
            if name in seen:
                rows.append({"file": rel, "level": "ERROR", "scope": scope,
                             "msg": f"duplicate skill name '{name}' in the same root, already declared by {seen[name]}"})
            else:
                seen[name] = rel
            if name != md.parent.name:
                rows.append({"file": rel, "level": "WARN", "scope": scope,
                             "msg": f"name '{name}' differs from directory '{md.parent.name}'"})
        if not fields.get("description", "").strip():
            rows.append({"file": rel, "level": "ERROR", "scope": scope, "msg": "frontmatter has no description"})
    return seen


def check_local_patches(rows: list[dict], include_user: bool = True) -> None:
    """A local addition to a third-party skill must survive an upstream update.

    Skills normally live at the user level (~/.agents/skills), so both roots are checked:
    whichever copy the agent actually loads is the one that must carry the patch.
    """
    roots = [SKILLS] + ([USER_SKILLS] if include_user else [])
    for name, patches in LOCAL_PATCHES.items():
        found_any = False
        for root in roots:
            md = root / name / "SKILL.md"
            if not md.is_file():
                continue
            found_any = True
            text = md.read_text(encoding="utf-8", errors="replace")
            for needle, why in patches:
                if needle not in text:
                    rows.append({
                        "file": _label(md), "level": "ERROR",
                        "scope": "repo" if root == SKILLS else "user",
                        "msg": f"local addition '{needle}' is missing ({why}); reapply it after the upstream install",
                    })
        if not found_any and include_user:
            # only an error when we actually looked in the root the skill is expected to live in
            rows.append({"file": name, "level": "ERROR", "scope": "user",
                         "msg": f"patched skill '{name}' is not installed in either skill root"})


def scan(include_user: bool = True) -> list[dict]:
    rows: list[dict] = []
    check_local_patches(rows, include_user)
    repo_names = _collect(SKILLS, rows, "repo")
    if not include_user or not USER_SKILLS.exists():
        return rows

    user_names = _collect(USER_SKILLS, rows, "user")
    for name in sorted(set(repo_names) & set(user_names)):
        rows.append({
            "file": user_names[name],
            "level": "WARN",
            "scope": "both",
            "msg": f"skill '{name}' also exists in the repo ({repo_names[name]}); the project copy wins "
                   f"— keep one source or the copies drift",
        })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-user", action="store_true", help="check the repo only, skip ~/.agents/skills")
    args = ap.parse_args()

    rows = scan(include_user=not args.no_user)
    errors = [r for r in rows if r["level"] == "ERROR"]
    warns = [r for r in rows if r["level"] == "WARN"]

    if args.json:
        print(json.dumps({"findings": rows, "errors": len(errors), "warnings": len(warns)},
                         ensure_ascii=False, indent=2))
    else:
        for r in rows:
            print(f"{r['level']:5} {r['file']}: {r['msg']}")
        names = sorted(seen_names(include_user=not args.no_user))
        print(f"\n{len(names)} skill name(s): {', '.join(names)}")
        print(f"{len(errors)} error(s), {len(warns)} warning(s)")
        if errors:
            print("ANDON: a broken skill does not load. Fix before reporting the skill change done.")
    return 1 if errors else 0


def seen_names(include_user: bool = True) -> list[str]:
    roots = [SKILLS] + ([USER_SKILLS] if include_user else [])
    out, seen = [], set()
    for root in roots:
        if not root.exists():
            continue
        for md in sorted(root.rglob("SKILL.md")):
            real = md.resolve()
            if real in seen:
                continue
            seen.add(real)
            fields, _ = parse_frontmatter(real.read_text(encoding="utf-8"))
            name = fields.get("name", "").strip().strip('"')
            if name and name not in out:
                out.append(name)
    return out


if __name__ == "__main__":
    raise SystemExit(main())
