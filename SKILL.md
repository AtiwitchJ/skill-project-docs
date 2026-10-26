---
name: project-docs
description: "Maintain a project's documentation in project/ (roadmap, phase tasks and presentations, issue log, results and charts, backlog) and docs/ (tutorials, how-to, reference, explanation): keep one owner file per fact, keep derived files and the Azure DevOps backlog mapping in sync, Diátaxis page roles and memory-bank status. Runs together with the installed memory-bank and diataxis skills without copying them. Per-project settings and rules are read from the project's .project-docs/ folder. Use whenever a task is started, finished or blocked, a test is rerun or new numbers arrive, a phase presentation is created or changed, a diagram or comparison is drawn or changed, Azure DevOps PBIs, Tasks or work items are read or drift from the task files, a page mixes two doc roles, two names for one thing must be merged, content must be cut from a doc, or docs must be synced — even for short prompts like 'task 1.2 passed', 'update the docs', 'ปิด Task', 'สรุปผล', 'make a phase presentation', 'sync ADO', 'classify the docs', 'remove X'."
---

# Project Documentation

Keeps a project's docs true and consistent. The skill is installed once (by convention in `~/.agents/skills/project-docs/`, and each agent's skill folder links to it); what is specific to a project lives in that project's `.project-docs/` (`config.json`, `rules.md`, `owner-map.md`, `glossary.md`, `stale-patterns.json`, `flow-policy.json`, `azure-devops.md`). Edit only what the task touches, and keep one owner file per fact.

New project? `python3 ~/.agents/skills/project-docs/scripts/init_project.py` scaffolds `.project-docs/`, `project/` and the four `docs/` folders.

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
9. **Offer folder or structure options first,** then let the owner choose.

## Which file to read

| The task is… | Read |
|---|---|
| every task, first | `.project-docs/rules.md` (this project's rules) and `.project-docs/config.json` |
| any change: pick the type and the order of work | `rules/change-router.md`, then `.project-docs/owner-map.md` |
| writing or editing a page, a diagram, a reply | `rules/writing.md`, `.project-docs/glossary.md` |
| task status, subtasks, tests, issues, the roadmap | `rules/phases.md` |
| a gate ERROR, WIP, rework | `rules/flow.md` |
| the memory bank (start of every task, hand-off) | `integrations/memory-bank.md` (the `memory-bank` skill owns the files) |
| a reader-facing page: its role, split, audit | `integrations/diataxis.md` (the `diataxis` skill owns the framework) |
| Azure DevOps ids, drift, work-item text | `integrations/azure-devops.md`, then `.project-docs/azure-devops.md` |
| a phase presentation | `templates/presentation.md` |
| an `.excalidraw` picture: a spec, lanes, rows, tags, the check | `rules/diagrams.md` (starter: `templates/diagram-spec.example.json`) |
| which script does what | `rules/tools.md` |

Who owns what across the four skills is in the README. When another skill disagrees with this one, the stricter project rule wins (owner-map, glossary, results-only pages, no secrets) and the report says which rule overrode which.

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
| 5. Propagate | Router order · `sync_presentation.py <N>` and `sync_project_readme.py` when status changes · ADO per `integrations/azure-devops.md` | Each derived file is updated or noted "not affected, because …" | Owner turns out wrong → back to step 4 |
| 6. Gate | `flow_log.py finish <id>` (runs `check_docs.py`) | 0 ERROR · every new WARN is fixed or accepted in `.project-docs/flow-policy.json` with a reason | **Andon:** stop, fix, run finish again (the first result is already logged for %C&A) |
| 7. Presentation QA | `templates/presentation.md` §QA, if a presentation was touched | Scripts pass and screenshots were looked at, or the report says they weren't | Fix and recheck |
| 8. Page role | `diataxis_audit.py` when a reader-facing page was added or split, then the `diataxis` skill for the fix | Every touched page declares one quadrant, sits in that folder, and holds one job | Mixed page → propose the split, don't blend |
| 9. Record | `sync_memory_bank.py` for the counts (M), then memory-bank prose (focus, decisions, blockers); new issue if a new problem appeared | The memory bank doesn't contradict `project/` or `docs/` | — |
| 10. Hand over | Report against the Definition of Done | All items below hold | — |

**Definition of Done**
- Every changed value is updated at its owner; no unsynced copies remain. Paired `.md` and `.html` match in the same pass.
- The gate has 0 ERROR and every WARN has a decision.
- `sync_memory_bank.py --check` and `sync_project_readme.py --check` exit 0.
- Touched ADO items are mapped in `tasks.md` (`**ADO:** #id`) and `ado_drift.py` shows no mismatch, or the mismatch is reported with the decision it waits for.
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
