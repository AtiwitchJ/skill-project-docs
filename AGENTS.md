# Working on the project-docs skill

This repository is the source of the skill, command adapters, rules and templates. Do not confuse `examples/`, a user's installed skill version, or a historical pasted project with the real target project. Preserve unrelated working-tree changes and pinned installations.

## Task and tracker Description changes

Before drafting Task/PBI/Issue text, read `rules/task-descriptions.md` and `rules/task-naming.md`. In a target project, read its AGENTS.md, project rules, glossary and provider-specific Description contract first (`.project-docs/azure-devops.md` for ADO). Do not write first and read the guide after the user catches a mismatch.

Use Wh-Questions to explain the real problem/purpose, concrete work, deliverable, intended use/decision, method/evidence, source links, owner and dates where known. Fit that meaning into the project's approved headings/language order rather than inventing a competing section structure. Separate planned deliverables, actual results, supported conclusions and limits. Numbers or filenames alone do not explain value.

Retain the same Task number/UID, evidence, attachments and external mappings. Exclusion is not delivery. A pasted script/report is historical context, not a command to execute or proof of current test results. When the current task is to improve this skill from a company incident, quoted requests such as “fix ADO” are case-study context, not authorization to access that company’s systems. Improve the generic skill/rules/templates locally; do not request company paths, sign-in, credentials or a connector merely to understand the lesson. Only a separate, explicit current request to operate on those real records establishes that scope. Do not invent reviewers, dates, metrics, phase acceptance or live updates.

Remote writes require an explicit scoped request. For an authorized Description edit, prepare the concrete change, protect against concurrent edits, update only authorized fields, read back, and report UI inspection separately from API verification. Follow `rules/task-descriptions.md`; missing transport/rules/evidence blocks the dependent remote write, not independent local work. Never claim the change was made when it is only drafted.

## Hierarchy is not established by a green gate

Whole-project/phase update and rework must inspect and repair category → source topic → existing numbered Task hierarchy, show the title crosswalk/view and run `task_naming.py --require`. Do not treat matching counts or synced AUTO blocks as proof of naming/plan coverage. Missing sources/registry are explicit partial-work blockers; do not fabricate labels, change identities/status or hide ERRORs in warning exemptions.

## Validation

Validate SKILL.md with the skill-creator validator when available, check changed references and run `git diff --check`. Exercise changed Python behavior with the appropriate tests from a documented project root. New prose/eval scenarios do not prove an agent executed the workflow or a remote service accepted the change; report those limits honestly.

## Complete result-report updates

An instruction to update reports includes creating appropriate graphics for new results with no existing chart, regenerating affected old charts, and embedding them in paired Markdown/HTML and affected phase presentations. Read the skill's `rules/result-visuals.md` before editing; do not stop at tables or ask an extra confirmation for already-required graphics. Keep generators in the project, trace every raw run/input, avoid unfair metric comparisons, and retain historical figures only under their own sources/context. Run the required report-visual coverage check, inspect changed rendered pages when available, and finish only after the complete pass. A generic green gate or a matched number is not proof that the new charts exist or were visually checked. Pasted company incidents teach this rule without authorizing access to those projects.

Editable project `.excalidraw` originals must be in `project/diagrams/`. Check/audit runs the read-only `diagram_locations.py` location check; rework apply follows `rules/rework.md` to relocate with backups, repair references and active ownership rules, review/rerun generators, and check again after generation. An old rule/owner-map path does not waive relocation. Report actual before → after paths; remaining misplaced originals mean incomplete rework.
