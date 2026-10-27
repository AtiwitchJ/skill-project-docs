# project-docs rework

Use when the user requests `project-docs rework`, `project-docs-rework`, or a broad cleanup of scattered/contradictory project documentation. This is an agent workflow, not a standalone shell program and not `flow_log.py rework` (which records a defect against a previous task).

## Invocation and scope

| Invocation | Behavior |
|---|---|
| `/project-docs-rework` | Relocate misplaced documentation/artifacts, create missing required files, repair references, write indexes/summaries and verify the current project |
| `/project-docs-rework audit` | Read-only inventory, checks and concrete proposed fixes; report in chat |
| `/project-docs-rework apply docs/` | Rework user documentation and repair references affected by those edits |
| `/project-docs-rework apply phase 2` | Rework that phase's docs, evidence navigation and affected indexes/status summaries |
| `project-docs rework audit` | Same workflow expressed in natural language in another agent |

The Claude slash command must first be installed from `commands/project-docs-rework.md`. Other agents can use the main skill's natural-language route. No terminal executable named `project-docs-rework` is installed by this repository.

`apply` is the default because an explicit rework request asks for changes. Respect narrower user instructions. Unknown or contradictory modes/scopes need clarification; never guess a different target repository. Arguments are user scope text, not shell commands. Resolve paths inside the target repository; do not follow symlinks outside it. Respect ignored/dependency directories and submodules. Include documentation outputs and their generators even when generated; do not scan dependency/build caches as documentation. Read an ignored raw artifact only when a known owner explicitly requires it, preserving its ignore/privacy policy.

## 1. Inventory and baseline

Locate the target project independently from the skill installation. Read its AGENTS.md, project rules/config, owner-map, glossary, source plan and relevant existing memory-bank summaries when available. Honor the established language and project layout; do not assume every repository should be renamed into the scaffold.

Search the entire authorized repository for documentation and its related artifacts, including root-level files, legacy folders and files outside `project/` or `docs/`; scanning only the intended folders will miss the files this workflow must relocate. Inspect documentation entry points, phase tasks/presentations/deliverables, measured results and raw evidence, issue/decision records, diagrams/generators, images, downloadable documents and external mappings. Include tracked and relevant untracked documentation; a dirty working tree does not justify stashing or resetting user work. Record the Git state if available and separate pre-existing defects from defects introduced by this task. In a non-Git project, use a file inventory and backups for changed originals.

Build a concise inventory with columns: current path, purpose/reader, authoritative owner, derived copies, defect, proposed destination/action. Find orphan pages, broken links/anchors, mixed-purpose pages, duplicated facts, inconsistent names/status, missing closeout summaries, stale presentations/flows, charts without sources and missing index links. Read enough content to classify meaning; names alone are not evidence of duplication or phase completion.

When configuration exists, run the applicable read-only baseline checks from the target root using the actual skill script paths: `check_docs.py`, `diataxis_audit.py`, `sync_presentation.py --all --check`, `sync_project_readme.py --check`, and `sync_memory_bank.py --check`. `drift.py` is an additional diagnostic when useful; it is not a replacement for a whole-document inventory. Run configured integration checks on local snapshots only; do not fetch external data simply to reorganize docs. A failing baseline is a finding, not permission to hide it.

When `.project-docs/` or expected owner files are absent, inventory first. In `audit`, report bootstrap needs without running `init_project.py`, flow logging, sync writes, backups, Git mutations or creating a report file. Skip unavailable checks explicitly. Return the inventory, proposed moves/merges, baseline findings and decisions, then stop.

## 2. Choose a concrete local repair plan

In `apply`, show a short plan and continue with independently actionable changes. Reuse explicit project layout/owner decisions. When those are absent, the existing `project/` (delivery/status) and `docs/` (reader guidance) scaffold is the default for missing structure; do not demand another general confirmation for this command's documented default. A materially different layout, conflicting factual owners or product/acceptance decisions need a focused question; continue unrelated repairs while awaiting that answer.

For every move, split, merge or archive, identify incoming links, fragment anchors, relative assets, generator inputs, source/pointer paths, mappings and the authoritative destination. Never move a file solely because its title looks untidy. Preserve useful existing URLs with a short forwarding page/link when compatibility requires it. Do not silently flatten subprojects or rename established public documentation paths.

If no project configuration exists, `init_project.py --path <target>` can add missing scaffolding in apply mode after inventory. It never overwrites existing files, but inspect its output for stubs and complete affected required owners from actual evidence. Do not run it merely to reformat a healthy custom layout. Resolve a target language from project rules or existing content; document the choice. If required meaning is unknown, record it as unknown rather than filling invented plan/status/results.

Once the project is configured, log the work using `flow_log.py start F "Rework project documentation"` (router F covers reader-facing pages); use the appropriate router types for affected work, including I for naming, E for presentation restructuring, C for an actual phase closeout and K for page roles. This does not require `project-docs-sync` or `project-docs-now`; follow the bundled router/scripts directly if those companions are missing, and disclose that fallback. Do not install or trust unknown-source companion copies automatically.

## 3. Relocate misplaced files and create what is missing

In apply mode, execute the repair plan. An inventory, recommendations or a prettier index alone is not a completed rework. Actually move misplaced files into their authoritative locations, repair references and write the required pages. If the user names a specific misplaced file or destination, include that request in the move plan.

### Destination and completeness matrix

First use the user's explicit target layout, then project-specific rules/owner-map. For undocumented destinations, use these defaults and record them in the project owner-map/rules. `project/` is the default home for project delivery artifacts; `docs/` is for reader guidance, not a dumping ground for all file types.

| File purpose | Default authoritative location | Required companions / checks |
|---|---|---|
| Editable project diagrams, including `.excalidraw` | `project/diagrams/<name>.excalidraw` | Spec in `.project-docs/diagrams/` or the existing project-owned generator; published preview linked from the relevant explanation/phase |
| Diagram specs and phase visualization settings | `.project-docs/diagrams/`, `.project-docs/presentations/` | Correct output/source paths, source checksums where used, recorded generator ownership |
| Phase tasks, presentation and closeout summary | `project/phases/phase-N/` | `tasks.md` and `presentation.html` for known phases; final `deliverable.md` for closed phases, draft when needed for open work |
| Test/benchmark reports and raw evidence | `project/results/` with project/run grouping | Existing raw source, provenance, charts and established MD/HTML report pairs remain connected; preserve original run IDs and bytes |
| Result chart assets and their generators | Next to their result owner, e.g. `project/results/charts/` or the run directory | Source pointer/path, generator path and checksum metadata updated and validated |
| Issues, decisions and source plan/roadmap | `project/issues.md`, `project/decisions/`, `project/roadmap.md` plus its required HTML pair | Preserve IDs, recorded decisions and real scope; do not invent phases, dates or acceptance |
| Tracker snapshots, mappings and project settings | `project/backlog/` and `.project-docs/` according to existing contracts | Preserve connection IDs, Task UIDs, refs, snapshot scope and configuration semantics |
| User tutorials, procedures, API reference and explanations | The applicable `docs/` quadrant | Descriptive entry in `docs/README.md`; actual content grounded in shipped behavior/source |
| Screenshots, figures, PDFs, office documents and other attachments | Near their owning phase/result, or a scoped `project/assets/` / `docs/assets/` location | Identify the owning page first; preserve binary bytes, captions and relative download/image links; retain original format |
| Project and reader entry points | `project/README.md`, `docs/README.md` | Project → phases/summaries/evidence; docs → reader pages; add a link from the existing root README when absent |
| Agent context and rework bookkeeping | `memory-bank/` under its own rules, `.project-docs/rework/` | Summaries/links, not another copy of reader docs or raw result tables |

This covers artifacts by purpose rather than an extension allowlist. A CSV, JSON, notebook, image, presentation or other file linked from a documented result must also be accounted for. An unknown file stays in place with an explicit classification question; it is not silently ignored, deleted or moved based on its extension. Application source, runtime assets, vendored material and external packages remain at their application-owned paths; update documentation references without reorganizing product code.

Do not assume every `.excalidraw` must move if an explicit project convention owns it elsewhere. When no such convention exists, a loose `architecture.excalidraw` at the repository root or under `notes/` moves to `project/diagrams/`, with its referring pages/specs/generator updated. A reader-facing SVG export may remain under `docs/assets/`; the editable owner and published preview serve different purposes. Existing original diagrams without a generator remain original editable sources: register their ownership rather than inventing a spec that overwrites their content. Do not combine several diagrams merely to meet the one-file preference if doing so risks losing content; record the justified multiple-file convention instead.

### Move, repair, verify, then write the handoff

For each relocation, record source/destination, owner, incoming references and a checksum before changing it. Move one coherent owner/asset group at a time. If the destination exists, compare content and ownership: reuse an identical owner, but never overwrite a different file. Preserve conflicting originals at distinct documented paths and request only the unresolved ownership decision. Keep uncommitted/untracked content recoverable; a Git-tracked filename alone is not proof that its current bytes are in a commit.

After moving, repair Markdown links/images, HTML references, fragment links, indexes, diagram spec `file`, generator source/output paths, chart specifications, project mappings and relevant configuration references. Resolve relative links from their new containing directory. Search the authorized repository for the old paths and verify that any remaining hits are intentional compatibility links or rework history. Make required path-only reference repairs outside a narrow requested folder, but do not expand into unrelated content edits.

Check moved binary/original source files against the recorded hashes. Parse diagrams/JSON when applicable, run the relevant generator/check commands for generated outputs and inspect the visual result when needed. A rebuilt derivative may legitimately change bytes; validate it against its real source/generator while retaining original evidence. Do not casually regenerate or rewrite immutable historical test-run bundles; keep the bundle intact and update its external links, or publish a separate sourced view when a different layout is necessary. Fixing an Excalidraw destination does not finish the workflow until its owner metadata, links and dependent previews agree.

Files outside the repository are separate from files merely outside `project/`. Do not sweep Desktop, Downloads, other projects or symlink targets. When the user explicitly identifies an external artifact as belonging to this project, incorporate a verified copy and document provenance; remove/move the external original only when that removal is authorized. Missing external files become explicit blockers while independent local repairs continue.

Compare the inventory against the matrix to create missing required structure and pages in the same run. Complete scaffolded content from actual project source, task records, decisions and evidence; do not leave generic drafting instructions as a final deliverable. Create missing indexes, applicable user guides, issue/decision registers, known-phase tasks/presentations and closeout summaries as required by the existing rules. Reconstruct an absent generator/spec only when the source structure is known and reproducible; otherwise preserve the original artifact and record the missing reproducibility evidence. Do not fabricate raw results, screenshots, test history, Task UIDs for already identified tasks, dates, owners or acceptance. For a genuinely new Task lacking an identity, use the existing explicit UID upgrade workflow rather than guessing an old identity.

If a required report can be regenerated from real raw input, do that and link it. If the raw input is missing, write a truthful status/limitation in the owning summary and log the missing evidence; an empty result JSON, fake passed test, broken-link placeholder or copied template is not a repaired report. The same principle applies to missing roadmap scope or ambiguous API behavior. Required information that cannot be recovered keeps that portion partial rather than making the whole project appear complete.

Keep a coverage ledger: every discovered in-scope artifact is kept at a justified owner, moved, merged without loss, regenerated from known source, created from evidence, or explicitly pending. Every required-but-absent file is created and checked or has a concrete blocker. Report created and moved files separately; a list of proposed future files does not satisfy apply mode.

## 4. Repair owners and navigation

- Give each fact one owner. Resolve exact duplicates by preserving the authoritative content and linking to it; conflicting facts remain visible with source links and an Issue/decision rather than choosing the prettier version. Keep original material recoverable through Git or a scoped backup outside reader navigation when Git cannot recover it. Do not delete unique content, opaque files or evidence as “cleanup.” Never use a blanket recursive delete or bulk formatter over the repository.
- Separate project plans/status/results from user guidance. For new or split user pages, use the existing Diátaxis integration and available framework skill. If that skill is missing, perform unambiguous navigation repairs and report classification-dependent work as pending instead of claiming the framework was applied.
- Update `project/README.md` as the project/phase entry point and `docs/README.md` as the reader-doc index. Use descriptive links and keep counts in their generated blocks. Do not create several competing indexes or copy full Task/results tables into them.
- Review each closed phase against `rules/phases.md` §Phase closeout: complete its existing `deliverable.md`, link delivered docs/evidence/limitations and index it. Missing closure evidence is a finding; do not fabricate an acceptance date or retroactively mark tasks/phases complete. For open phases, keep a draft summary if needed and label it as such.
- Preserve Task numbers, stable UIDs, external mappings, unresolved issues, original test evidence, charts and custom generators. Update known references when owners move; regenerate derived assets using their reviewed generators. Reorganization is not permission to change product code, invent measurements, rewrite test history or infer done from merged PRs/closed Issues.
- Update terminology consistently and repair relative links, anchors and asset paths in the same pass. Keep public navigation reader-facing; rework logs and agent context belong under `.project-docs/` and memory-bank, not inside the user guide index.

Rework modifies local documentation only. Remote records, provider selection, credentials, account configuration, migration/cutover and deployed sites stay outside its authorization. Do not stage/commit/push or alter agent installations as an incidental cleanup step.

## 5. Synchronize and verify

Use affected router sequences: update the owner first, then relevant paired Markdown/HTML, phase flows/presentations, generated phase table and memory-bank counts. Do not run `sync_tasks.py` as a bulk cleanup if it would infer acceptance without verified Task evidence; reconcile ambiguous status first. Review manual narrative separately from AUTO blocks.

Run the relevant baseline checks again and inspect the diff for lost sections, charts or evidence. Verify project index → phase summary → actual deliverables/evidence and docs index → reader pages, including changed fragments and assets. The current gate does not prove that every external link, HTML fragment, closeout claim or narrative is correct; inspect changed navigation explicitly. Perform presentation screenshot/keyboard QA when HTML was changed, following the existing presentation guide. Run execution tests only when implementation changed or when needed to resolve an evidence question; use the test report wrapper and state what was actually executed.

Finish the flow-log entry with the gate result. A pre-existing ERROR still needs a reported resolution or blocker; do not claim success because it predates this run. Accept warnings only through the project's existing policy with a concrete reason, never by suppressing checks, changing tolerances or weakening a rule to get green output.

## 6. Handoff and resuming

For apply mode, write a scoped report under `.project-docs/rework/<run-id>/report.md` (reuse the same report if resuming that run). Include:

- Target, scope, language/layout decision and baseline state.
- A before → after path/action table with source owner, reason and retained-content/backup location where relevant.
- Working navigation entry points, the artifact coverage ledger and phase-summary coverage, with missing files/evidence clearly identified. List required files actually created and any blocked creations.
- Checks actually run and their results; separate script checks, visual inspection and checks not performed.
- Unresolved contradictions, remaining defects and decisions, plus how to undo the local changes without resetting unrelated work.

Only include counts derived from the actual inventory/checks. Keep secrets and private raw credentials out of reports. In audit mode return this information in chat without writing it. On a repeat run, inspect current files and the earlier report rather than creating duplicate pages, archive trees or Task identities. When nothing needs changing, report a no-op with the checks performed.

Rework is complete only when misplaced in-scope files have actually been relocated, required missing files have been written from evidence or explicitly blocked, scoped repairs are finished, meaningful content/evidence is retained, navigation and applicable checks pass, and remaining accepted limitations are explicit. If blocked on evidence or a decision, hand over the finished repairs and label the run partial; do not claim that a disorganized project was fully repaired when important defects remain.
