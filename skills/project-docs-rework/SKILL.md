---
name: project-docs-rework
description: "Reorganize scattered project documents and assets, write missing required pages and verify Task hierarchy. Use for a messy project; supports read-only audit."
---

# Project documentation: rework

Execute **project-docs rework** for the target project. Interpret the user's accompanying text as scope/arguments, never as executable shell text. Do not depend on Claude-only substitutions or hooks.

## Locate the shared rules

The supported bundle installer places a `project-docs` core skill beside this skill in the same discovery root. Starting from the directory containing this SKILL.md, read `../project-docs/SKILL.md` and `../project-docs/rules/commands.md`. Confirm the core declares `name: project-docs`. The core supplies the scripts, templates and detailed rules; this entry point does not maintain another copy of them.

When reading this skill directly from the source checkout (`skills/project-docs-rework/`), the core is `../../SKILL.md` and `../../rules/commands.md` instead. Use the actual skill file location, not the current project working directory. Do not assume `~/.agents/skills` or Claude's command directory exists on this agent. If the adjacent core is missing or incompatible, report the incomplete installation and use the bundle installer; do not silently load an unrelated globally installed core or change agent settings.

## Perform the workflow

Follow the shared behavior and **rework** section in the core's `rules/commands.md`. For rework also read `rules/rework.md`. Respect project-specific rules, source evidence, stable Task numbers/UIDs and explicit scope. Whole-project/phase update and rework must perform the required Task hierarchy checks and show the real category → source topic → Task view, not merely report a green generic gate.

The skill installation is not the target project. Read target rules before drafting, preserve user edits and original evidence, and distinguish proposed from observed results. Continue authorized local work through verification. Missing facts/acceptance are concrete blockers, not invented answers. `check` and rework `audit` write nothing. Do not commit, push, access a company system, migrate records, install packages or modify application behavior merely because this entry point was invoked. Return actual changes/findings, output links, verification and remaining limitations in the user's language.
