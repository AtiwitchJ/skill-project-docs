# Change router: change type → order of work

Classify the change first, then follow that type's order without skipping. If a step doesn't apply, note "not affected, because …".

Before every type: `flow_log.py start <letter> "<summary>"` (records the baseline), then read `memory-bank/activeContext.md` and `progress.md`.
After every type: `flow_log.py finish <id>` with no ERROR, then check the type's **Passes when**. Failing it is an Andon: stop, fix, finish again.

## A. New or rerun test results

1. Read `rules/test-reporting.md` and execute through `run_tests.py` for automatic JSON/MD/HTML and failure workflows. The raw JSON owner comes first, with timestamp and source; use immutable `project/results/tests/<run>/` for this runner, or retain the established evaluation owner for other results.
2. `project/results/test-results.md`: update tables from the JSON values; regenerate affected charts from their scripts.
3. `test-results.html` matches the MD in the same pass.
4. TASKS citing this result: add evidence to the subtask with date and limits. If the result completes every subtask, set the header to `[x]` now (or run `sync_tasks.py <N>`).
5. Fixed errors or bugs: remove the old error text from the tables; keep the history in the issue.
6. Failures or surprises: add to `issues.md`.
7. Presentation: `sync_presentation.py <N>` for numbers and status, then fix narrative if its meaning changed.
8. Pages in `docs/`: summary and link only; never copy the tables.
9. memory-bank: `activeContext.md` (latest result), `progress.md` (status).

**Passes when:** the JSON holds every value used (path and timestamp given) · test-results md and html match the JSON · no derived file holds a value missing from the JSON · superseded values added to `stale-patterns.json` · `sync_tasks.py --check` passes · charts still present, no sequence diagram in test-results.

## B. Task status changes (start, done, blocked)

1. `phase-N/tasks.md`: set the header marker (`[/]`, `[x]`, `[!]`) to match progress, or run `sync_tasks.py <N>`. Hard rule: when every subtask is `[x]`, the header must be `[x]`, or `check_docs.py` raises an ERROR. Never tick `[x]` before verifying the real result.
2. Blocked: put the Issue ID on the header and create or update the issue in `issues.md`.
3. `sync_presentation.py <N>` (or `sync_tasks.py <N>`) so the cover and status table match TASKS.
4. `roadmap.md` and `.html`: roadmap row and done/total.
5. memory-bank: `activeContext.md` = focus, `progress.md` = status.

**Passes when:** header markers match the evidence · `sync_presentation.py <N> --check` passes · done/total in roadmap md and html match TASKS · blocked tasks carry an Issue ID · WIP within limit or justified in `flow-policy.json`.

## C. Close a phase

1. Every task is `[x]`, or `[!]` with an issue; deliverables exist as files.
2. `phase-N/deliverable.md` moves from draft to final, with limitations.
3. Phase presentation: no "Planned" or "กำลังทำ" left in any slide's narrative.
4. roadmap: phase status and Mermaid timeline.
5. memory-bank: focus moves to the next phase.

**Passes when:** every task is `[x]` (or `[!]` with an issue the project lead accepted) · deliverable is final · no stale status in presentation narrative · roadmap and memory-bank point to the next phase · every WARN has a decision.

## D. New problem (issue)

1. Search `issues.md` for an existing ID first.
2. If none, add the next ID with symptom, reproduction, cause (confirmed/hypothesis) and status `OPEN`.
3. Affected tasks: link the ID on the header or the related checklist item (don't copy details).
4. memory-bank: one-line blocker in `activeContext.md` and `progress.md`.
5. `RESOLVED` only with a check tied to the original symptom. On resolve or reopen, update the issue, the task and memory-bank in the same pass.

**Passes when:** the issue has symptom, reproduction, cause (confirmed/hypothesis) and status · every reference to the ID exists in the register · memory-bank has a one-line blocker with the ID.

## E. New presentation or restructure

1. The phase's TASKS must exist (if not, stop and write TASKS first).
2. `sync_presentation.py <N> --new` creates it from `templates/presentation-template.html`.
3. Fill every `TODO` per the standard slide set in `templates/presentation.md`.
4. `sync_presentation.py <N>` pulls status from TASKS.
5. QA per `templates/presentation.md` §4.
6. memory-bank and roadmap if the phase status changed.

**Passes when:** no `TODO` left · every item in `presentation.md` §4 passes · the report says whether screenshots were looked at.

## F. Pages in docs/

1. Find the fact's owner (owner-map).
2. If it has an owner, fix the owner first; the page summarizes and links.
3. No unsourced numbers; no "สำเร็จ 100%" while a client or test round is open.
4. Update the "อัปเดตล่าสุด" date in the file header on every content change.
5. If a permanent fact changed, check `systemPatterns.md`, `techContext.md`, `projectbrief.md`, `productContext.md`.

**Passes when:** every number on the page links to its owner · no duplicated content on the page · header date updated · no broken links.

## G. Paired presentation and .md

Route by the data that changed (A or B), then check the pair together. Never leave `.md` and `.html` out of sync across passes.

**Passes when:** both files changed in the same pass and changed values match in both (compare by script or grep).

## H. Diagram or chart

1. If the project has a spec in `.project-docs/diagrams/`, edit the spec; otherwise find the generator in owner-map and edit the script. Never hand-edit `.excalidraw` or `.svg`. A new diagram is a new block in the existing file (`rules/writing.md` → Diagrams before prose; spec workflow in `rules/diagrams.md`).
2. Spec: run `python3 ~/.agents/skills/project-docs/scripts/build_diagram.py <spec> --check`, fix every ERROR, then run it without `--check` to write. Generator: rerun the script from the repo root. Delete any `Untitled-*.excalidraw` autosave copy the editor left behind.
3. Check the "Diagrams before prose" rules in `rules/writing.md` and the project's diagram conventions in `.project-docs/rules.md` (column order, step labels), glossary names, symmetric boxes.
4. Open the file by eye (excalidraw.com or the VS Code extension); if you can't, say it wasn't looked at.
5. `.md` pages that reference the diagram link to the file instead of copying the flow as long text.

**Passes when:** the generated file matches the latest script run (rerun → `git diff` unchanged) · no circled numbers or banned names · no `Untitled-*` autosave copy in the repo · the report says whether the image was looked at.

## I. Duplicate names, or an order to cut content

Duplicate names:

1. Propose one name (or use the user's choice) and add a row to `.project-docs/glossary.md`.
2. `grep` the old name across `docs/`, `memory-bank/`, `scripts/` and fix every hit in one pass, including diagram and chart generators; rerun them.
3. Add the old name to `stale-patterns.json`.

Cutting content ("remove X"):

1. Remove it from the named file and its `.md`/`.html` pair in the same pass. Don't move it elsewhere.
2. Never remove a chart unless told to remove that chart.
3. Remove links and TOC entries pointing to the cut part.

**Passes when:** `grep` finds the old name only in sentences saying it is retired · no broken links · existing charts all still present.

## J. Configured tracker drift and migration

If `integrations.primary` is configured, read `integrations/providers.md` and the selected provider guide. Run `integrations.py check --json` against the latest snapshot; preserve Task UIDs and external refs. Refresh through the actual configured transport when live access is needed. Report unknown states, missing/not-observed records, unmapped work and stale snapshots. Task status changes still follow B and require evidence; a closed remote item or merged PR does not tick a Task.

An explicit cross-tracker copy follows `integrations/migration.md`, including plan, operation journal, verification and a separate cutover. This is the only general integration flow that writes destination records. Source records stay unchanged; normal drift checks never create, close or rewrite remote items.

For projects that still use only legacy `ado` configuration, follow the existing flow below.

Read `integrations/azure-devops.md`. TASKS owns status; ADO is what the project lead reviews.

1. Refresh: `wit_query` (wiql) → `wit_work_item get_batch` for the ids → save JSON.
2. `ado_drift.py --import <file>` then `ado_drift.py`. Exit 1 means drift; read every `DRIFT` line before touching docs.
3. ADO Done but TASKS not done: keep TASKS as it is, report which evidence is missing. Do not tick `[x]` because ADO says so.
4. TASKS done but ADO open: report it and name who should close it. Do not write to ADO.
5. ADO item with no task: report as a note with the proposed phase; do not create a task silently.
6. Task with no ADO item: report; the owner decides whether to open one.
7. If a phase maps to a new PBI, add the `> **ADO PBI:**` line and the `**ADO:**` lines in the same pass. Never renumber tasks to match ADO.
8. If the owner explicitly asks for a Description, write it the way `.project-docs/azure-devops.md` says. Never write to ADO without that request.

**Passes when:** the configured integration check (or legacy `ado_drift.py`) passes, or every finding has a recorded decision · snapshot age/coverage is reported · no remote write occurred during docs sync · mappings preserve stable IDs · an explicit migration has a readback report before cutover.

## K. Page role (Diátaxis)

Load the `diataxis` skill for the actual work; this step is the project wrapper.

1. `python3 ~/.agents/skills/project-docs/scripts/diataxis_audit.py --path <file>` for the page you touch.
2. No declaration → add `> **Diátaxis:** <quadrant>` in the header block, based on what the page actually does.
3. Two jobs in one page → propose the split with the skill's restructure mode before editing. Move, don't copy; leave a relative link and update `docs/README.md`.
   - Split by **reader job**, not by size. A long page that answers one question stays whole; a short page that answers two gets split.
   - Tables are not automatically Reference. Inside a "ทำความเข้าใจ / ทำไม / เปรียบเหมือน" section they are the medium of an explanation; inside "Step 1 / ขั้นที่ 2" they belong to the procedure. Read the section heading before judging the table.
   - New reference pages register in `.project-docs/owner-map.md` so the next editor knows where the number lives.
4. `project/` pages, presentations and `memory-bank/` are out of scope: note "not a Diátaxis document, because it tracks work" and stop.

**Passes when:** every touched reader-facing page declares one quadrant · `diataxis_audit.py` reports no new SPLIT for those pages · links still resolve (`check_docs.py`) · the report names the quadrant and the skill's confidence.

## L. Skill self-check (after editing anything under `.agents/skills/`)

The agent loads skills by name and by path; a broken file makes the skill silently disappear from the list or load an old copy.

1. Every `SKILL.md` has valid YAML frontmatter. A `description` containing `: ` must be quoted, or the whole skill is dropped.
2. One `name:` per skill in each root, and every skill lives directly under `<root>/<name>/`. An eval workspace, snapshot or `pristine/` copy inside the root shadows the real one.
3. **Both roots matter:** `.agents/skills/` (project, wins) and `~/.agents/skills/` (user). A stale user-level copy with broken YAML takes the name down even when the repo copy is correct — keep one source, symlink the other.
4. `python3 ~/.agents/skills/project-docs/scripts/check_skills.py` — frontmatter, duplicate names per root, cross-root duplicates (WARN), shadowing directories, nested copies. `--no-user` for the repo alone.
5. Ask the agent to load the skill by name. "Failed to read skill file" or "not found" means the registry holds a stale path: reload the window, don't rename the directory to work around it.
6. A slash command needs a prompt file: `.github/prompts/<command>.prompt.md`. A skill's `name:` is not a command, and the repository name is not the skill name (`keithpatton/diataxis-agent-skill` installs as `diataxis`).

**Passes when:** `check_skills.py` exits 0 · loading each edited skill by name succeeds · every `/command` the skill text mentions has a prompt file · no copy of a skill lives inside another skill's directory.

## M. Memory-bank counts (derived block)

`memory-bank/progress.md` does not hold numbers of its own: phase counts live between `AUTO:phase-counts` markers and are written from TASKS.

1. `python3 ~/.agents/skills/project-docs/scripts/sync_memory_bank.py` after any task status change, phase close, or new phase.
2. `python3 ~/.agents/skills/project-docs/scripts/sync_memory_bank.py --check` must exit 0.
3. Never hand-edit the block. If it disagrees with TASKS, the block is wrong — run the script, don't change TASKS to match.
4. Everything outside the block (focus, decisions, next steps, known issues) stays prose a person writes; review it against `activeContext.md` before handover.

**Passes when:** `sync_memory_bank.py --check` exits 0 · `check_docs.py` shows no `AUTO:phase-counts` ERROR · `activeContext.md` focus names the phase actually in progress.
