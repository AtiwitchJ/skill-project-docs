# Phases, tasks, tests and issues

## Plan and phases

Keep phase meaning and tasks aligned with the project's source plan (named in `.project-docs/rules.md`); if something is unclear, log it as a question to confirm rather than guessing.

- Never append phases beyond the plan. Work that is not in the plan goes under the extra-work heading the project defines in `.project-docs/rules.md`, with its origin noted.
- Each phase lives in `project/phases/phase-<n>/` with exactly one `tasks.md` and one `presentation.html`, created and rescoped together (`deliverable.md` may start as a draft and is required as the final summary at phase closeout). No per-task files.
- Never renumber a referenced task; new tasks take the next number in the phase.
- Each phase also has a generated progress flow in `tasks.md` and `presentation.html`, backed by task headers. Run `sync_presentation.py <N>` or `--all` after changes. Configure meaningful step groups in `.project-docs/presentations/phase-N.json`; do not store duplicated status or inferred durations there. See `rules/presentation-charts.md`.
- Link the phase to its Azure DevOps PBI in the header block (`> **ADO PBI:** #1234`) and each mapped task to its work items (`**ADO:** #1301`). See `integrations/azure-devops.md`.
- Task header markers: `[ ]` not started, `[/]` in progress, `[!]` blocked, `[x]` done and verified.
- Checklist items use only `[ ]` and `[x]` (Markdown preview renders nothing else as a checkbox). A blocked item stays `[ ]` and starts with `⛔ บล็อก: <reason> (IMP-xxx)`.

**Task file format:** period, deliverable, status and roadmap origin, then the groups the project defines (see `.project-docs/rules.md`). Each task has a name, an outcome, and only the checklist needed to finish it; no generic acceptance criteria without real data.

**Roadmap format:** the project defines it in `.project-docs/rules.md`. Update `roadmap.html` in the same pass as `roadmap.md`. `project/README.md` shows the phase table; it is filled by `sync_project_readme.py`, never typed.

## Phase closeout

Before reporting a phase closed, complete router C in `rules/change-router.md`. A green test run or completed checkboxes alone does not finish the documentation handoff.

1. Finalize `project/phases/phase-N/deliverable.md` as the phase's summary and navigation page. Use `templates/phase-closeout.md` when no summary exists; preserve and complete an existing deliverable rather than replacing it or adding another phase README.
2. State the intended outcome versus what was actually delivered; link shipped files/features and relevant decisions. Record the closure date, verification scope/results with links to raw evidence and paired reports, limitations, unresolved Issue IDs and follow-up tasks/owners or the decision needed to assign them. Distinguish completed work from explicitly accepted exceptions; do not invent acceptance, test results or owners. A documentation-only phase can state that execution tests are not applicable and explain what was reviewed.
3. Update or create the user-facing documentation needed for what shipped: tutorials, how-to, reference or explanation pages according to their real purpose. Update `docs/README.md` with descriptive links to those pages. It remains a user-documentation index: do not copy phase status, task lists or test tables there. If no user-doc changes apply, verify the existing index and record the reason in the phase summary instead of creating filler pages.
4. Add a descriptive link to the final summary in `project/README.md` outside its generated `AUTO:phase-status` block, or reuse an existing equivalent phase-summary index. Cover every closed phase without broken or duplicate entries; link tasks/presentation and evidence from the summary. Run `sync_project_readme.py` for the generated counts; never hand-edit its block.
5. Synchronize tasks, phase flow/presentation, roadmap and memory-bank using their existing owner rules. Check links in the summary and both indexes, verify that a reader can navigate project index → phase summary → delivered documentation/evidence, and run the existing sync/gate checks. Review summary completeness manually: the current gate does not check every narrative closeout requirement.

**Closeout passes when:** the final summary and navigation exist; relevant user docs are current and indexed (or the unchanged-docs reason is recorded); claims trace to owner files; outstanding work is linked and any closure exception has the project lead's recorded acceptance; presentation/roadmap/index status is consistent; and required checks pass. Keep the phase open when these are incomplete. State “closed with accepted limitations” where appropriate; never present accepted blocked work as verified completion.

Keep summaries short and link to owners. Task state stays in `tasks.md`, measurements in raw result files, detailed failures in `project/issues.md`, and project decisions in their decision records. Do not duplicate full Task inventories, raw logs or results tables in either index. Do not create a new `.html` closeout companion solely for navigation; maintain a pair if the project already requires or has one.

## Ticking subtasks

Tick `[x]` as soon as a subtask is done and verified with evidence, even if the task is still `[/]`.
- Done but not fully meeting the condition → **split it**: the done part `[x]` with date, how it was checked and its limits (e.g. "ทำกับเอกสารจำลอง"), and the rest `[ ]` stating what it waits for. Never leave a verified item unticked, and never tick a whole item that hides an unfinished part.
- Decisions the AI made on the project lead's behalf may be ticked, but must say who decided, when, and that it can change. Never phrase them as the project lead's approval.
- Results judged by the AI assistant or an LLM judge must say they were not checked by a person.
- Before reporting status, count tasks by script from the `### [x]/[/]/[!]/[ ]` headers and make the counts match everywhere (each `tasks.md`, `roadmap.md`/`.html`, `project/README.md`, memory-bank).

## Test when testable, record at once

If a task can be tested now (even on synthetic data), test it instead of waiting, and record in the same pass:
- Evidence on the subtask, and the results pages (`project/results/`, md and html) updated from the raw result file. Pull numbers, answers and judge reasoning by script; never type them, never trim reasoning until it loses meaning.
- Failed, blocked or unexpected results also go to `project/issues.md`, not only passes.
- Unresolved errors may show in the results tables as they are. **Once fixed, remove the old error text** from both files and show only the corrected result; the history lives in `issues.md`.
- Always state limits: synthetic or real data, number of runs, who or what judged.
- If testing needs changes to the user's personal settings (tool permissions, machine-level config), stop, record what the user must do, and never use permission-bypass flags.

## Issue log

When implementation or verification hits a problem that may recur, search `project/issues.md` first. If nothing matches, add the next ID (`IMP-001`, `IMP-002`, …).

Record only what helps reproduce or fix it:
- The actual symptom/error and context (phase/task, environment, config or commit if known).
- How to reproduce, what was tried, and what each attempt changed.
- Cause, marked confirmed or hypothesis.
- Fix and evidence (command, output, log path, verified task).
- What to wait for, or which condition must change, before retrying.

Status: `OPEN` (not fixed / waiting), `RESOLVED` (fixed with evidence), `REOPENED` (symptom returned), `WONTFIX` (with reason and decider). Tasks link the Issue ID instead of copying details.

Before retesting, compare with the existing issue: if code, config, environment and conditions are unchanged, cite the earlier result instead of rerunning the same diagnostics. If something changed, record it and recheck only what's needed. A RESOLVED issue that recurs becomes `REOPENED` with a new occurrence; never overwrite the earlier fix.

Never close an issue just because code was changed or a request was sent. Verify with a check tied to the original symptom; otherwise keep it `OPEN` and say what it waits for.

## Presentations

Read `templates/presentation.md` before creating or changing `phase-N/presentation.html`. It covers the audience, the standard slide set, HTML rules and the QA steps. `tasks.md` must exist before its presentation.

## Test reports and layout scale

Follow `rules/test-reporting.md` for automatic paired test reports and observed failure-stage workflows. Native unittest captures lifecycle stages; JUnit-only imports do not infer them. Attach via `run_tests.py --phase N`; Task acceptance remains manual and evidence-based. Check readable text, keyboard scrolling, vertical mobile steps, empty/error states and large inventories at phone, tablet and desktop widths. Missing metrics remain explicit.
