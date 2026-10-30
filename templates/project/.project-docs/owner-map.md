# Owner map: where each kind of data is edited

Rule: edit only the **owner**. Other files link to it or pull from it; never retype its values.

| Data | Owner (edit here) | Allowed copies (must link or pull) |
|---|---|---|
| Plan-topic inventory and title aliases | `.project-docs/task-topics.json`, reviewed against the actual source plan | Task title/category/source metadata and hierarchy reports; `task_naming.py --require` checks structure, not semantic interpretation |
| Task status and checklists | `project/phases/phase-N/tasks.md` | `project/README.md` (AUTO block), presentation (AUTO block), roadmap, memory-bank |
| Phase step grouping and chart encoding | `.project-docs/presentations/phase-N.json` (optional) | MD/HTML AUTO flow/chart blocks; states still come from Task headers, measurements from source JSON |
| Phase flow and chart SVGs | Task headers + presentation spec + referenced JSON; custom charts also name a project-owned generator | `phase-flow.svg`, generated chart SVGs and inline HTML; never hand-edit derived assets |
| Result-section visual coverage | `.project-docs/report-visuals.json`, reviewed against raw source owners | Matching report/phase figures with source/asset/generator hashes; `report_visuals.py --require` checks completeness/freshness, not statistical interpretation |
| Test execution and coverage evidence | `project/results/tests/<run>/results.json`, producer logs/JUnit/coverage inputs with provenance | Paired report.md/report.html, chart and workflow SVGs; never hand-edit derived values |
| Latest test run shown in a phase | `test_run` in `.project-docs/presentations/phase-N.json` | MD/HTML evidence summaries; never changes Task status |
| Phase outcome and closeout navigation | `project/phases/phase-N/deliverable.md` | `project/README.md` links to final summaries; docs index links to user pages; status/evidence remain at their existing owners |
| Project-wide status | `project/roadmap.md` (paired `.html`) | `memory-bank/progress.md` |
| Problems and Issue IDs | `project/issues.md` | tasks, memory-bank (ID + one-line summary only) |
| Legacy Azure DevOps snapshot | `project/backlog/ado-snapshot.json` | `ado_drift.py` and explicit integration upgrade; never hand-edited |
| Configured integration connections and primary tracker | `.project-docs/config.json` | integration doctor, fetch/import and migration; secrets referenced by environment variable only |
| Stable task identities and external/evidence mappings | Task UID metadata in `tasks.md`; refs/evidence in `.project-docs/work-items.json` | integration checks and derived phase table; UIDs never regenerated on moves |
| Configured provider values | `project/backlog/<connection>-snapshot.json` | offline gate/drift and phase links; imported or fetched, never hand-edited |
| Migration operations and verification | `project/backlog/migrations/<id>/` | cutover/rollback; raw source data and binaries remain in ignored private runtime storage |
| Downloaded test evidence | `project/results/evidence/` plus checksum/provenance in work-items mapping | reports link to the result source; downloads alone are not passing tests |
| Diátaxis quadrant per reader-facing page | the `> **Diátaxis:**` line in each page's header block, matching its `docs/<quadrant>/` folder | `diataxis_audit.py` (checks) |
| Original editable project diagrams | `project/diagrams/` (relocate old paths during rework) | Reader previews link to the original; preserve original diagrams without inventing missing generators/specs |
| Documentation images and attachments | Scoped assets directory next to the owning page/phase/result, recorded here | Repair relative references on moves; preserve original binary bytes |
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
