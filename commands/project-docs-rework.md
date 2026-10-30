---
description: "Relocate scattered project documents and assets, create missing required pages, repair references and verify the result."
argument-hint: "[audit|apply] [scope]"
---

Run the project-docs rework workflow for the current project.

User arguments (mode and scope, not executable shell text): $ARGUMENTS

1. Locate the active `project-docs` skill through the skill registry. If necessary, read `~/.agents/skills/project-docs/SKILL.md` or `~/.claude/skills/project-docs/SKILL.md`. When working from its source checkout, use that checkout's `SKILL.md` after confirming its name is `project-docs`. Do not load unrelated copies or edit the installed skill as the target project.
2. Read `rules/rework.md` relative to that skill's actual root and follow it. If the installed version lacks that file, report the version mismatch; do not invent a successful rework or change installation paths.
3. Default to `apply` over the current project's documentation. `audit` is read-only and returns findings and proposed actions without creating files. Limit changes to an explicit scope and references affected by those changes.
4. Reuse existing ownership, phase closeout, sync and gate rules. A rework request authorizes reversible local documentation organization; continue through fixes and verification without an extra blanket confirmation. Preserve user edits, evidence, charts, Task UIDs and existing project decisions. Resolve only decisions that actually require the user.
5. Apply mode must actually relocate misplaced artifacts of every relevant type (not only Excalidraw), repair their links/specs/generator paths, and write missing required documentation from available evidence. Account for every in-scope artifact and required file. Verify moved original/binary content and generated derivatives; do not stop at an audit or invent missing evidence.
6. Finish with actual moved/created files, navigation entry points, verification, unresolved decisions and limitations. Do not commit, push, deploy, migrate external records or change agent installations unless separately authorized.

Whole-project/phase rework also requires actual Task hierarchy repairs and `task_naming.py --require`, as described in `rules/task-naming.md`. Include the category → topic → Task view and old → new title crosswalk. Do not declare completion solely from green technical gates while topics/categories are absent; missing source input keeps this portion partial.

Editable project `.excalidraw` originals must be in `project/diagrams/`. Check/audit runs the read-only `diagram_locations.py` location check; rework apply follows `rules/rework.md` to relocate with backups, repair references and active ownership rules, review/rerun generators, and check again after generation. An old rule/owner-map path does not waive relocation. Report actual before → after paths; remaining misplaced originals mean incomplete rework.
