# Everyday project-docs commands

These are agent workflows exposed by the Markdown adapters in `commands/`, not shell executables. The command selects intent; existing project rules, ownership, evidence and router sequences still apply. `project-docs <verb>` in chat is the equivalent route for other agents.

## Shared behavior

For a portable `project-docs-<verb>` skill, resolve the adjacent `project-docs` core from that entry point first; do not redirect to another agent’s global path. Otherwise locate the active skill root using its registry entry or `~/.agents/skills/project-docs/SKILL.md` / `~/.claude/skills/project-docs/SKILL.md`; use a verified source checkout when working there. Read the relevant bundled rule relative to that root, not a guessed project-local rule. If an installed version lacks the command/rule, report the version mismatch. Locate the target project separately; an installed skill is not the target project.

Read the target's rules/config/owner-map and applicable AGENTS.md when present. Before Task/Issue/PBI Description work, also read its provider-specific authoring contract and `rules/task-descriptions.md`; do not write first and inspect conventions afterward. Parse arguments as mode/scope/path text, never interpolate the entire argument string into a shell command or treat it as executable code. Invoke scripts using their actual paths and argument arrays. Resolve relative paths from the target; do not silently switch projects or follow unrelated external directories. Respect dirty work and existing Task UIDs. Ask only for genuinely missing target/phase/acceptance decisions; continue independent authorized work.

Only `setup` may scaffold an unconfigured project. Read-only commands do not write flow logs, backups, reports, configuration or derived blocks. Mutating commands may update local documentation as described below; they do not authorize application-code edits, live tracker fetch/writes, migrations, publishing, package installation, commits, pushes or agent-configuration changes. Do not invoke unknown-source companion skills; bundled scripts/rules are sufficient for these commands. These names deliberately avoid the separate `project-docs-sync` / `project-docs-now` companions.

Return a concise result in the user's language: affected scope, actual changes or findings, checks performed, links to outputs, and remaining limitations. A zero exit code or checked Task alone is not acceptance evidence. Preserve original nonzero test/check results in the handoff and distinguish script checks from visual QA. Repeated calls reuse existing owners rather than duplicating files or inventing work.

## Task hierarchy is a separate completion condition

For any whole-project or Task/phase-scoped check/update/rework/close-phase, inspect `rules/task-naming.md` explicitly. Run `task_naming.py --root <target> --require --json` with the relevant `--phase N` when scoped. In apply/update modes, create or repair the reviewed topic registry and Task category/topic/title metadata from actual source material, preserving IDs/status, then rerun this check. `check` and rework `audit` only report findings and never create the registry. Do not skip the inspection merely because all tasks are checked, sync reports “up to date,” a generic gate passes, or the naming file is optional for legacy projects.

If the task scope genuinely excludes Tasks (e.g. a wording-only edit to one user guide), state that exclusion and reason. Otherwise missing plan topics/registry are explicit partial-work blockers, not a reason to report the whole run complete. New explicit naming requirements take precedence over an old ungrouped presentation; update local owner rules accordingly rather than using them to silently ignore the user's requested hierarchy. Separate legitimate custom file locations from missing Task organization.

The handoff must show **category → exact source topic → existing Task number/title**, an old → new title table (or checked no-change), IDs preserved, the explicit hierarchy-check result and unresolved source decisions. Green technical checks are not a substitute for this view. Do not mark hierarchy ERRORs as accepted WARNs, weaken rules or create generic exemption entries just to obtain green output. Provider updates remain out of scope unless separately requested.

## Result updates include new graphics

When result reports are in scope, read `rules/result-visuals.md`. Update/rework must create missing new-result charts and persistent generators as well as regenerate affected existing ones, embed them in report Markdown/HTML and affected phase views, and run `report_visuals.py --require` for the actual owners. Do not ask whether to make already-required graphics after claiming the reports are complete. An unchanged historical chart can remain correctly sourced, but does not cover a new comparison. Check mode runs read-only coverage diagnostics; no registry/asset creation there. Distinguish comparable metrics, real source snapshots, structural checks and actual visual inspection. Missing inputs or pending visual QA are explicit partial-work limits.

## setup — initialize documentation

Invocation: `/project-docs-setup [project-path]`. Default: the current project.

1. Inventory existing documentation/settings and identify project name/language from explicit arguments, existing rules or source documentation. If the supplied project path does not exist, create it only when the user explicitly requested that new destination; otherwise resolve the current project.
2. Run `init_project.py --path <target> --name <known-name> --language <project-language>` to create missing scaffold only. Preserve existing files and custom layout; never overwrite configuration, provider credentials or a real document with a template. This command does not install the skill into the agent.
3. Complete missing entry-point links and required owner settings from known facts. Map existing phases/docs; do not invent a phase plan, dates, acceptance or provider choice. For a substantial legacy cleanup use the rework workflow only if the user's setup request also authorizes that reorganization; otherwise identify the additional work.
4. Run the applicable sync/check scripts and report created versus preserved paths, the project/docs entry points, draft fields/unknown decisions and readiness. Distinguish “scaffold created” from “fully configured.” No external connection is selected just because a tool exists.

See `scripts/init_project.py`, `rules/phases.md` and `templates/project/`.

## check — read-only documentation health

Invocation: `/project-docs-check [scope]`, such as `phase 2`. Default: all configured project documentation.

Run applicable read-only checks: `check_docs.py` (use `--phase N` for an explicit phase), phase sync `--check` (explicit N or `--all`), `sync_project_readme.py --check`, `sync_memory_bank.py --check`, and `diataxis_audit.py` on relevant reader pages. Use local integration snapshot checks only when configured. Do not refresh/fetch snapshots or run an external doctor handshake merely for a docs check. Report project-wide findings from global checks separately when a narrower phase was requested.

If config is absent, inventory available files and report which checks require setup; do not call init or write defaults. Report ERROR/WARN, stale owners, broken navigation and unknown evidence with source locations. Do not fix findings, change checkboxes, suppress warnings or create reports in this mode. Recommend the matching update/rework operation.

See `rules/tools.md`; audit scope does not promise that the scripts check every HTML fragment or manual claim.

## update — synchronize existing documentation

Invocation: `/project-docs-update [scope]`, such as `phase 2` or `docs/`. Default: changes supported by current owner/evidence files.

Read `rules/change-router.md` and identify changed facts at their owners (use `drift.py` when useful). Repair relevant local docs and propagate actual owners to phase Markdown/HTML, flows/charts, overview/roadmap and memory-bank counts using the applicable sync scripts. Update relevant indexes/closeout summaries and review manual narrative. Run `--check` and the gate afterward. Keep missing/conflicting evidence explicit; do not infer new acceptance or run `sync_tasks.py` blindly to force closed tasks. An update repairs synchronization; broad artifact relocation follows `rules/rework.md` only within an explicitly requested rework scope.

This route works without the separate sync companion and must not claim that companion was run. Use presentation QA when touching HTML and keep result numbers sourced.

## close-phase — complete the phase handoff

Invocation: `/project-docs-close-phase N`. Require a positive, existing phase number. If omitted, infer it only when the target has one unambiguous active phase; otherwise ask which phase.

Read `rules/phases.md` §Phase closeout and router C. Check actual acceptance evidence and unresolved exceptions first. Finalize/create the phase deliverable summary, update required user guides and both indexes, synchronize presentation/roadmap/memory-bank, verify links and run checks. Use `templates/phase-closeout.md` for a missing summary. Move to a next focus only when the actual plan establishes it; do not invent a phase.

When Task grouping/titles need repair, follow `rules/task-naming.md`, preserving the original number/UID and explicit scope decisions. Missing evidence, required documents or unaccepted blocked work leaves closure pending. Finish independent documentation repairs and report exactly what still prevents closure. Never fabricate acceptance or declare a phase complete merely because its summary was written.

## test — execute tests and retain reports

Invocation: `/project-docs-test [test-target or phase N]`. Default: the project's documented local test command, when unambiguous.

Read `rules/test-reporting.md`. Inspect project test configuration/scripts to choose the actual test runner and scope. A phase number determines report attachment, not an invented test-to-phase mapping: use documented tests or ask when that mapping is unclear. Missing/ambiguous test targets require clarification rather than guessing a passing command. Do not install dependencies, start external services or run deployment/migration operations just because a script is named “test.” Report necessary prerequisites.

Execute through `run_tests.py` using a fresh `project/results/tests/<run-id>/` directory: native `unittest` for Python unittest, `command -- argv...` for other documented runners, or `junit FILE` only when the user requested import rather than execution. Use real JUnit/coverage inputs when supported and available. A generic command without case-level output still gets process evidence, but does not establish test counts/stages/coverage. Pass `--phase N` only for a known existing phase when requested/established. No Task markers are changed automatically.

Retain JSON, paired reports and original failure status even on failures/interruptions; link the outputs and disclose unavailable metrics. The command does not fix application code as an incidental side effect. See the testing guide for observed versus unknown failure-stage limitations.

## rework — reorganize and complete project documentation

Invocation: `/project-docs-rework [audit|apply] [scope]`. Default: apply. Follow `rules/rework.md` in full: inventory across the authorized repo, actually relocate misplaced artifacts, repair references/specs/generators, create required missing files from evidence, verify, and retain a coverage report. `audit` is strictly read-only.

Editable project `.excalidraw` originals must be in `project/diagrams/`. Check/audit runs the read-only `diagram_locations.py` location check; rework apply follows `rules/rework.md` to relocate with backups, repair references and active ownership rules, review/rerun generators, and check again after generation. An old rule/owner-map path does not waive relocation. Report actual before → after paths; remaining misplaced originals mean incomplete rework.
