---
description: "Read-only check of documentation health, links, evidence and derived outputs."
argument-hint: "[scope]"
---

Run **project-docs check** for the current project.

Arguments (scope/target text, not executable shell code): $ARGUMENTS

Locate the active `project-docs` skill and read its `SKILL.md`, then `rules/commands.md` relative to the actual skill root. If needed, resolve the skill through `~/.agents/skills/project-docs/SKILL.md`, `~/.claude/skills/project-docs/SKILL.md`, or this verified source checkout. The skill installation is not the target project.

Follow the shared command behavior and the **check** section in `rules/commands.md`, including its existing router, evidence and verification requirements. Do the authorized work through completion; do not stop at a plan. If the installed version lacks the command guide, report that mismatch instead of inventing the workflow or silently changing the installation. Return actual results, output links and remaining blockers.
