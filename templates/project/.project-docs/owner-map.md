# Owner map: where each kind of data is edited

Rule: edit only the **owner**. Other files link to it or pull from it; never retype its values.

| Data | Owner (edit here) | Allowed copies (must link or pull) |
|---|---|---|
| Task status and checklists | `project/phases/phase-N/tasks.md` | `project/README.md` (AUTO block), presentation (AUTO block), roadmap, memory-bank |
| Project-wide status | `project/roadmap.md` (paired `.html`) | `memory-bank/progress.md` |
| Problems and Issue IDs | `project/issues.md` | tasks, memory-bank (ID + one-line summary only) |
| Azure DevOps snapshot | `project/backlog/ado-snapshot.json` | `ado_drift.py` (only reader; never hand-edited) |
| Diátaxis quadrant per reader-facing page | the `> **Diátaxis:**` line in each page's header block, matching its `docs/<quadrant>/` folder | `diataxis_audit.py` (checks) |
| Picture drawn from a diagram spec | `.project-docs/diagrams/<name>.json` (the spec, edited by hand) | the `.excalidraw` it names is output, never edited; `build_diagram.py` builds it, the gate checks it matches |
| Docs task log (%C&A) | `.project-docs/flow-log.jsonl` | `flow_log.py report` |
| Cross-session context | `memory-bank/*.md` | — (a summary, not a copy) |

Add a row for every other kind of data (measurements, settings, names) as it appears.

## Values never typed by hand

- Counts of tasks done, in progress, blocked (count from `tasks.md` with `docs_lib.parse_tasks`).
- Numbers from result files: name the source file next to the value.

## No owner found

If a value has no owner file, stop and log an issue or ask the project lead. Never guess.

## Page inventory (every page has one job)

`check_docs.py` warns about any Markdown page under `docs/` that no row names. Add a row when you add a page; if a page is genuinely nobody's owner, list it under **Exempt** with the reason.

### Project (`project/`)

| Page | Owns | Notes |
|---|---|---|
| `project/README.md` | the project's front page and its phase table | phase table is an AUTO block filled by `sync_project_readme.py` |
| `project/roadmap.md` / `.html` | roadmap and phase status | pair must match in the same pass |
| `project/issues.md` | Issue IDs, symptom, cause, status | only `OPEN`/`REOPENED` block work |

### Docs by quadrant (`docs/`)

| Page | Owns | Quadrant |
|---|---|---|
| `docs/README.md` | the docs entry point and its TOC | Reference (navigation) |

## Exempt

| Path | Reason |
|---|---|
