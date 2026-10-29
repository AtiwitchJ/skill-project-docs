---
name: project-docs
description: "Maintain project/ and docs/ documentation when tasks, results, phase presentations, progress flows, evidence charts, test executions/reports, diagrams or terminology change. Keep owner files, derived pages and memory-bank summaries consistent; choose charts by the reader's question and support project-owned custom charts; audit Diataxis page roles; compare configured Azure DevOps, GitHub, Jira, Linear or GitLab records and GitHub Actions evidence. Also use for an explicitly requested cross-tracker work-item migration. Use for project-docs rework to organize scattered documentation and repair indexes. Ordinary docs sync never writes to external trackers."
---

# Project Documentation

Keeps a project's docs true and consistent. The skill is installed once (by convention in `~/.agents/skills/project-docs/`, and each agent's skill folder links to it); what is specific to a project lives in that project's `.project-docs/` (`config.json`, `rules.md`, `owner-map.md`, `glossary.md`, `stale-patterns.json`, `flow-policy.json`, `azure-devops.md`). Edit only what the task touches, and keep one owner file per fact.

New project? Run `scripts/init_project.py` from this skill’s actual installation root to scaffold `.project-docs/`, `project/` and the four `docs/` folders. Paths starting with `~/.agents/skills/project-docs` in this guide are the shared-install convention, not a requirement: portable bundles may live in the selected agent’s native skill root. Resolve resources relative to the actual core, not another agent’s installation.

**Language:** write doc content in the language set in `.project-docs/config.json` (`language`), matching the existing pages. Keep file names, code identifiers and the project's established terms as they are. Reply to the user in the language they used.

## Working principles (read first)

1. **Pictures and tables over prose.** One column per alternative; `.excalidraw` flowcharts with peers on one level, no crossing lines, light colours. The project's own conventions (order, labels) are in `.project-docs/rules.md`.
2. **Short orders are decisions** (e.g. "remove X"): do it, don't ask again. Never cut charts. Results pages hold results only.
3. **One name per thing** (`.project-docs/glossary.md`). Rename everywhere in the same pass.
4. **Real evidence.** Say whether code changed. "Tested" means run, with limits stated. Show the raw JSON when asked.
5. **A request to finish means finish.** Fix what you find wrong; ask only what only the project lead can decide.
6. **Every phase has `tasks.md` and `presentation.html`.** The HTML must not look machine-made: light, plain, no emoji clutter.
7. **Problems go in `project/issues.md`** so a failure is not retested for nothing.
8. **Agent tooling stays out of pages people read** (memory bank, flow log, skill files). The gate warns.
9. **Offer folder or structure options first,** then let the owner choose. An explicit `project-docs rework` invocation uses its documented defaults in `rules/rework.md`; ask only about materially different layouts or unresolved ownership decisions.

## Which file to read

| The task is… | Read |
|---|---|
| Setup/check/update/close-phase/test commands | `rules/commands.md`, then the selected operation’s rules |
| every task, first | `.project-docs/rules.md` (this project's rules) and `.project-docs/config.json` |
| any change: pick the type and the order of work | `rules/change-router.md`, then `.project-docs/owner-map.md` |
| writing or editing a page, a diagram, a reply | `rules/writing.md`, `.project-docs/glossary.md` |
| task status, subtasks, tests, issues, the roadmap | `rules/phases.md` |
| Task/PBI/Issue Description clarity, purpose/outcomes or Wh-Questions | `rules/task-descriptions.md`, then the target project’s AGENTS.md and provider authoring contract; read before drafting |
| Task hierarchy, topic prefixes, plan-to-Task traceability or tracker titles | `rules/task-naming.md`; category → exact plan topic → numbered actionable Task |
| Closing a phase or summarizing its deliverables and documentation | `rules/phases.md` §Phase closeout, router C, and `templates/phase-closeout.md` |
| Organize a messy project: `project-docs rework` or `/project-docs-rework` | `rules/rework.md`; command adapter: `commands/project-docs-rework.md` |
| a gate ERROR, WIP, defect rework logging | `rules/flow.md` |
| the memory bank (start of every task, hand-off) | `integrations/memory-bank.md` (the `memory-bank` skill owns the files) |
| a reader-facing page: its role, split, audit | `integrations/diataxis.md` (the `diataxis` skill owns the framework) |
| Tracker connections, stable Task UIDs, mappings, snapshots or drift | `integrations/providers.md`, then only the configured provider's guide |
| Legacy Azure DevOps ids or work-item text | `integrations/azure-devops.md`, then `.project-docs/azure-devops.md` |
| GitHub Actions test evidence | `integrations/github-actions.md` |
| Explicitly requested copying of work items between trackers | `integrations/migration.md`; this is separate from ordinary docs sync |
| Running tests, importing JUnit, failure workflows or test-report charts | `rules/test-reporting.md`; run through `scripts/run_tests.py` |
| a phase presentation | `templates/presentation.md` |
| Phase step flow, chart selection or a custom evidence chart | `rules/presentation-charts.md`; sync both task Markdown and presentation HTML |
| Complex multi-panel benchmarks, multi-hop costs, baseline ratios or environment comparisons | `rules/advanced-chart-recipes.md`; distinguish design references from measured evidence |
| an `.excalidraw` picture: a spec, lanes, rows, tags, the check | `rules/diagrams.md` (starter: `templates/diagram-spec.example.json`) |
| which script does what | `rules/tools.md` |

Who owns what across the four skills is in the README. When another skill disagrees with this one, the stricter project rule wins (owner-map, glossary, results-only pages, no secrets) and the report says which rule overrode which.

## Integrations and migration

Read `.project-docs/config.json` to select the primary tracker and secondary evidence connections. Do not infer provider choice from installed tools. Read `integrations/providers.md` for connection/bridge setup and run `integrations.py doctor` before live access; configured MCP availability is not proof of a usable tool. If a tool or permission is missing, report it rather than inventing a response. Ordinary checks use local snapshots and never modify remote work items.

`tasks.md` owns status. Stable `**Task UID:**` metadata and `.project-docs/work-items.json` own external mappings. Preserve UIDs across task moves and provider changes; use the explicit `integrations.py upgrade` command for legacy ADO projects. Closed Issues and merged PRs alone are not acceptance evidence. Unknown statuses, stale snapshots and partial coverage must be reported. Normal commands never auto-close Tasks.

Only an explicitly requested migration may create destination items/comments/files. Follow `integrations/migration.md`: plan the concrete copy, preserve source originals, apply/resume with operation markers, verify readback, then cut over. Never write to the source or automatically delete destination items during rollback. Existing authorization for the specified copy persists; do not repeatedly ask for it. If the endpoint, scope or accepted limitations change, update the concrete plan before writing.

## Understandable Task descriptions

Before drafting a Description, read the target project’s authoring contract and `rules/task-descriptions.md`. Explain why the work matters, what it produces, who uses it for which decision and how evidence supports the result. Wh-Questions guide meaning inside the approved headings; they do not authorize a new template. Preserve language order, links, evidence and identity. For an explicit remote Description-edit request, prepare the concrete scoped change, protect concurrent edits, read back and report UI checks separately. Normal docs sync remains read-only toward trackers.

## Test evidence and readable layouts

Run tests through `run_tests.py` by default, following `rules/test-reporting.md`; preserve failure exit codes and link both reports and raw JSON. Use `--phase N` when the phase is known. Never mark tasks complete just because the runner returned zero: check actual executed cases and project acceptance evidence. Unknown JUnit stages, absent coverage and unsupported history stay explicit.

Generated HTML must be readable at phone, tablet and desktop widths. Keep text legible, scroll wide charts inside their container, offer vertical workflow steps, search/paginate large inventories and retain outcomes when charts fail. Inspect screenshots and keyboard controls before claiming layout QA.

## Distribution formats

`skills/` contains the six portable entry points. `scripts/install_skills.py` installs the core and entry points into one selected native skill root. `scripts/build_plugins.py` exports native plugin/extension formats for the documented clients and a portable fallback from those same files; see `integrations/agent-packages.md`. Do not promise universal plugin compatibility or UI verification based on packaging alone, and do not install/enable/publish as an incidental documentation action.

## Everyday commands

Portable entry points live at `skills/project-docs-<verb>/SKILL.md`; the bundle installer puts these six skills beside the shared core in the selected agent’s discovery root. Use `scripts/install_skills.py` as documented in the README; installing only a thin wrapper does not include its core dependency.

Use `rules/commands.md` for `project-docs setup`, `check`, `update`, `close-phase` and `test`; each has a matching `/project-docs-<verb>` Claude adapter in `commands/`. `setup` creates missing scaffold, `check` reads without writing, `update` synchronizes real owner facts, `close-phase` enforces the phase handoff, and `test` preserves actual execution reports and failures. `rework` handles broad artifact relocation/completion. These are agent workflows; use the explicit scripts for terminal execution. Installation instructions and examples are in the README.

## Rework a disorganized project

`project-docs rework` applies the repair workflow in `rules/rework.md`; add `audit` for a read-only assessment, or a scope such as `phase 2` or `docs/`. The optional Claude adapter exposes `/project-docs-rework [audit|apply] [scope]`. Apply mode actually relocates misplaced documentation/assets to their owners, creates missing required pages from available evidence, repairs references/specs/generator paths and verifies the result. Cover all relevant artifact types, not only Excalidraw; preserve original content/evidence and report unrecoverable gaps explicitly. This is local documentation work, not an external migration or a request to modify product behavior.

## Automatic sync

When a task changed docs, tasks, results or skills — or `drift.py` / the gate reports something — run the flow in `~/.agents/skills/project-docs-sync/SKILL.md` (drift → router A–M → report). Read that file by path rather than relying on the registry: a skill added mid-session does not appear until the window reloads. `/project-docs-now` is the manual door to the same flow; change its rules in `project-docs-sync` only.

## Workflow

Docs flow from owner files to derived files. Skipping a step leaves stale values in files you didn't touch, and the owner usually finds them first. Do not move on until a step passes.

| Step | Do | Passes when | If not |
|---|---|---|---|
| 0. Open | `python3 ~/.agents/skills/project-docs/scripts/flow_log.py start <type> "<summary>"` | You have the task id | — |
| 1. Classify | Pick type A–M in `rules/change-router.md` | You can name the type and the files to touch | Not enough info → ask |
| 2. Read state | The memory bank, per the `memory-bank` skill | You know the focus, blockers and Issue IDs | — |
| 3. Baseline | Recorded by `flow_log.py start` (runs `check_docs.py`) | You know the pre-existing ERROR/WARN | — |
| 4. Fix the owner | Find the owner in `.project-docs/owner-map.md` and edit it | Every value you write has an owner, and the owner is updated | **Andon:** a value with no owner (e.g. numbers given in chat without a raw result file) → ask for the file or log an issue. Never type it into a derived file |
| 5. Propagate | Router order · `sync_presentation.py <N>` and `sync_project_readme.py` when status changes · configured tracker per `integrations/providers.md`, or legacy ADO guide | Each derived file is updated or noted "not affected, because …" | Owner turns out wrong → back to step 4 |
| 6. Gate | `flow_log.py finish <id>` (runs `check_docs.py`) | 0 ERROR · every new WARN is fixed or accepted in `.project-docs/flow-policy.json` with a reason | **Andon:** stop, fix, run finish again (the first result is already logged for %C&A) |
| 7. Presentation QA | `templates/presentation.md` §QA, if a presentation was touched | Scripts pass and screenshots were looked at, or the report says they weren't | Fix and recheck |
| 8. Page role | `diataxis_audit.py` when a reader-facing page was added or split, then the `diataxis` skill for the fix | Every touched page declares one quadrant, sits in that folder, and holds one job | Mixed page → propose the split, don't blend |
| 9. Record | `sync_memory_bank.py` for the counts (M), then memory-bank prose (focus, decisions, blockers); new issue if a new problem appeared | The memory bank doesn't contradict `project/` or `docs/` | — |
| 10. Hand over | Report against the Definition of Done | All items below hold | — |

**Definition of Done**
- Every changed value is updated at its owner; no unsynced copies remain. Paired `.md` and `.html` match in the same pass.
- Every touched phase has current flow blocks in tasks Markdown and presentation HTML. Evidence charts explain their selection, units, source and limits; custom source/generator checksums are current.
- A phase being closed has a final `deliverable.md` with evidence and handoff links; `project/README.md` indexes that summary and `docs/README.md` indexes the relevant user documentation. Follow `rules/phases.md` §Phase closeout before reporting closure.
- Whole-project/Task/phase update or rework explicitly checks and repairs category → source topic → existing Task naming, with a hierarchy view/title crosswalk and `task_naming.py --require` result. Missing source/registry remains partial; a generic green gate or matching counts alone is insufficient.
- The gate has 0 ERROR and every WARN has a decision.
- `sync_memory_bank.py --check` and `sync_project_readme.py --check` exit 0.
- Touched ADO items are mapped in `tasks.md` (`**ADO:** #id`) and `ado_drift.py` shows no mismatch, or the mismatch is reported with the decision it waits for.
- Configured integrations pass `integrations.py check --json`, or each finding and evidence limitation is reported. An explicit migration includes a verification report; unresolved failures cannot be called a complete copy.
- Touched reader-facing pages declare one Diátaxis quadrant, sit in that folder, and hold one job.
- Any skill edited under `.agents/skills/` still loads by name: `check_skills.py` has 0 ERROR.
- No "do not use" name from `.project-docs/glossary.md` appears in touched files.
- The report is short, says whether code changed, and separates what was checked by script, what was looked at by eye, and what was not checked.

## Layout

```text
docs/        tutorials/ · how-to/ · reference/ · explanation/ · README.md   understand and use (Diátaxis: one quadrant per folder)
project/     README.md · roadmap.md/.html · issues.md · phases/phase-N/{tasks.md,presentation.html,deliverable.md}
             results/ (measured results, charts/) · decisions/ · backlog/ (ado-snapshot.json)
memory-bank/ agent context, English        .project-docs/  rules, owner map, diagram specs (diagrams/*.json), script data (flow log)
```

- `project/` holds the plan and phase status; never duplicate timelines or checklists in `docs/`.
- `project/results/` is the one place for measured results (one md + html pair per report): totals, per-category summary, per-question matrix, and full per-question detail (full question, rewritten query, expected vs retrieved documents, each method's real answer, judge score with full reasoning, time, tokens), plus limitations and how to rerun. A reader must learn "what we got" without opening raw JSON.
- `docs/` explains and teaches; design, API reference and setup guides live in `reference/` and `how-to/`.
- `memory-bank/` carries context across sessions. It is not another copy of `docs/` or the task list.
