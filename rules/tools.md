# Scripts

Run them from the documented project's root (or any folder inside it). The skill is installed once (by convention in `~/.agents/skills/project-docs/`), and each agent's skill folder links to it. `scripts/layout.py` finds the project by walking up from the current directory to `.project-docs/config.json`, and reads the project's settings from there. Every path comes from `layout.py`; moving a folder means editing that file and `.project-docs/owner-map.md`. What belongs to the project, never to the skill, lives in the project's `.project-docs/` (config, rules, owner map, glossary, stale values, policy, flow log) and `project/backlog/ado-snapshot.json`.

Scripts use the Python standard library except `qa_presentation.py` (Playwright).

| Script | Purpose |
|---|---|
| `check_docs.py` | Gate: structure, checklist markers, broken links in `docs/`, `project/` and `memory-bank/`, leftover TODO, raw backticks, slide numbers, duplicate ids, stale values, WIP limit, task header vs subtasks, tasks vs roadmap, no sequence diagram in test-results, file names, agent-only words in pages people read, quadrant vs folder, owner rows, diagram pictures match their specs (`.project-docs/diagrams/`). Accepted WARNs print as ACK |
| `layout.py` | The one place that knows where things live (project, docs, skill folders) |
| `init_project.py` | Scaffolds `.project-docs/` (incl. `diagrams/`), `project/` and the four `docs/` folders for a new project; never overwrites; runs the two derived-table syncs |
| `test_build_diagram.py` | Unit tests for `build_diagram.py` and the gate's diagram check (17 cases). Run from a project folder; writes only to temporary folders |
| `sync_tasks.py` | Sets task headers (`### [x]`) from their subtask checklists and updates the presentation |
| `sync_presentation.py` | Syncs cover/status plus paired Markdown/HTML step flow and sourced charts; writes SVG assets; `--all`, read-only `--check`, and `--new` scaffolding |
| `phase_visuals.py` | Validates step grouping, derives current states/counts, renders shared flow and chart blocks, and detects stale MD/HTML/assets |
| `presentation_charts.py` | Chooses 16 native chart families by question; reads JSON source, renders SVG/data tables and validates custom SVG provenance |
| `run_tests.py` | Executes unittest or argv commands, imports JUnit/coverage, writes immutable JSON/MD/HTML and optionally attaches phase evidence |
| `test_results.py` / `test_reporting.py` | Observed lifecycle records, evidence validation, conditional charts, failure workflows and responsive reports |
| `chart_families.py` / `build_chart_gallery.py` | Extended native encodings and an explicitly synthetic 16-family gallery |
| `test_testing_reports.py` | Offline lifecycle, failure, JUnit, history, coverage, large-inventory and graceful-render-error regression tests |
| `build_presentation_demo.py` | Builds a clearly labelled synthetic example into an empty directory, including a paired-dot custom chart |
| `test_phase_visuals.py` | Offline tests for flow grouping, chart semantics, custom SVG freshness/safety, paired sync and legacy narrative preservation |
| `sync_project_readme.py` | Fills the phase table of `project/README.md` from each phase's `tasks.md`; `--check` verifies only |
| `sync_memory_bank.py` | Writes the `AUTO:phase-counts` block in `memory-bank/progress.md`; `--check` verifies only (router type M) |
| `qa_presentation.py` | Renders at 1280px and 390px; checks overflow, backticks, status-pill count, Mermaid (needs Playwright) |
| `flow_log.py` | Opens/closes tasks, logs the first gate, rework, and the %C&A report |
| `drift.py` | Lists what the docs are behind on since the last sync (changed owners and code, ADO drift, stale generated files, sync and gate checks) as router items; used by `project-docs-sync` (auto) and `/project-docs-now` (manual) |
| `ado_drift.py` | `--import` saves the ADO snapshot from MCP output; compares it with the `**ADO:**` ids in `tasks.md`. Read-only, never writes ADO |
| `integrations.py` | `doctor`, `fetch`, `import`, `check`, `upgrade`, `evidence`; configured providers, stable Task UIDs, offline drift checks and Actions provenance. Never writes external records |
| `integration_core.py` | Shared configuration, normalized records, atomic JSON writes, mappings and evidence checks; no import-time project discovery |
| `integration_transport.py` | MCP agent request/response bridge, argv/JSON CLI bridge and direct API selection; migration pins the selected transport |
| `provider_api.py` | Provider-specific standard-library API operations; read-only by default, writes available only to migration apply/resume |
| `migrate.py` | Plan/apply/resume/verify/cutover/rollback; all tracker pairs through canonical records; copies destination data, preserves source and local rollback backups |
| `test_integrations.py` | Offline provider/transport/migration/evidence tests; temporary projects and mocks, no real credentials or remote changes |
| `diataxis_audit.py` | Compares each page's `> **Diátaxis:**` declaration with its real signals and its folder; flags pages holding two jobs |
| `check_skills.py` | Validates every `SKILL.md`: frontmatter that breaks a load, duplicate names, shadowing directories, nested copies (router type L) |
| `build_diagram.py` | Builds an `.excalidraw` from a spec in `.project-docs/diagrams/` and checks the geometry first (overlaps, crossing arrows, text fit, stale values); `--check` writes nothing. See `rules/diagrams.md` |
| `docs_lib.py` | Shared `tasks.md` parser (normally no edits needed) |
