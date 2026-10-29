# Azure DevOps backlog

For new multi-provider projects use [configured providers](providers.md) and `integrations.py`. This page also documents the supported legacy `ado_drift.py` flow; its commands, snapshot format and Markdown lines remain compatible. `integrations.py upgrade` is the explicit conversion to stable Task UIDs and shared mappings. See [migration.md](migration.md) only when a cross-system copy has been requested.

The direct API connection uses `provider: azure-devops`, `organization`, `project` and `token_env` for a PAT. The token needs work-item read scope for reads; migration destination writes additionally need work-item write access and project permission. A holder with write access can create work items, comments and attachments. Normal docs sync never invokes those writes, and migration never modifies the source project. Project-specific processes can require additional fields or disallow a proposed state transition; report that failure rather than guessing.

Azure DevOps is where the project lead reviews work; each phase's `tasks.md` stays the owner of task status. Read ADO to catch drift, never to write status. Never copy work-item descriptions verbatim into `docs/`; summarize in your own words.

Project-specific facts live in the project, not here: organization, project and Feature id are in `.project-docs/config.json` → `ado`; the backlog tree, examples and any rules about writing Descriptions are in `.project-docs/azure-devops.md` (read it first). No PAT is needed to read the backlog: use the MCP server or `az`.

## Writing and explicitly updating Descriptions

Read the target project’s AGENTS.md and `.project-docs/azure-devops.md` before drafting; follow `rules/task-descriptions.md` for Wh-Questions, planned versus observed outcomes, bilingual consistency and preserved evidence. Keep the approved headings rather than adding competing summary sections. An explicit request to edit specified Descriptions authorizes that field scope; it is separate from normal read-only sync and from migration. Read live fields/revisions, prepare exact changes, protect concurrent edits, read back and verify rendering where possible. Missing live access/rules/evidence leaves a labelled draft, not a claimed ADO update.

## Task titles and plan topics

Follow `rules/task-naming.md` for category → plan topic → Task naming, e.g. `2.6 [Agent with Azure MCP] เตรียม Azure MCP`. Keep the local Task number distinct from the ADO ID. Topic brackets are a logical grouping, not a requirement to add a remote hierarchy level. Prepare title changes for review during normal docs work; do not write ADO titles/states without explicit authorization. Use actual process/state mappings for cancelled or out-of-scope work, never assume that “Removed” exists or means completed.

## The tree

```text
Epic
└── Feature          ← one Feature per project
    └── PBI          ← a phase maps to a PBI; many PBIs may sit under the Feature
        └── Task/Bug ← map to one or more tasks in a phase file (many-to-many)
```

- Phase → PBI is many-to-one or one-to-one depending on how the owner split the work; do not assume one PBI per phase.
- PBIs that are not part of the project's phases still appear under the Feature. List them, don't force a mapping.

## How to read it (MCP)

The MCP tool is `mcp__azure-devops__search_workitem`. Tested behaviour:

- Searching by exact id works (`searchText: "<id>"` returns that work item).
- Wildcard or whole-project search does not work (`searchText: "*"` returns 0). There is no query by parent.
- Results carry no `System.Parent`. The Feature/PBI tree comes from the docs (`**ADO PBI:**`, `**ADO:**`), not from MCP.
- Field names are lowercase (`system.id`, `system.state`). `ado_drift.py` reads them case-insensitively.

Steps:

1. Collect the ids that `tasks.md` maps (PBIs and Tasks):

   ```bash
   grep -rhoE "ADO PBI:\*\*\s*#[0-9]+|ADO:\*\*\s*#[0-9, #]+" project/phases/ | grep -oE "[0-9]+" | sort -un
   ```

2. For each id, call `search_workitem` with `searchText: "<id>"`, `project: ["<ado.project>"]`, `top: 3`. Keep only the result whose `system.id` equals that id. Include the Feature id (`ado.feature`) as well.
3. Save the kept results as `{"results": [ ... ]}` in a temporary file outside the repo.
4. Run:

   ```bash
   python3 ~/.agents/skills/project-docs/scripts/ado_drift.py --import <temporary file>   # -> project/backlog/ado-snapshot.json
   python3 ~/.agents/skills/project-docs/scripts/ado_drift.py                              # compare with tasks.md
   ```

Limit: an ADO work item whose id is not written in `tasks.md` cannot be seen through this MCP. The unmapped list covers only the ids that were searched. Report this limit every time the drift is refreshed.

The snapshot is the owner of legacy ADO-side values; `ado_drift.py` reads it, and the explicit integration upgrade can import it without replacing it. Never hand-edit `project/backlog/ado-snapshot.json`.

## Mapping written into the docs

Phase file, in the header block (one line):

```markdown
> **ADO PBI:** #1234 (Feature #1000 Feature title)
```

Task: a line directly under the task heading, before the description. It never goes into the heading, because headings feed the presentation status table.

```markdown
### [x] 1.1 Task title

**ADO:** #1301
```

- Several ids: `**ADO:** #1301, #1302`.
- No ADO item yet: leave the line out. The drift script lists it as unmapped; that is a fact to report, not an error to hide.
- Never renumber a task to match ADO. The task number is ours; the ADO id is theirs.

## State mapping

| ADO state | tasks.md header | Note |
|---|---|---|
| New, Approved, Committed, To Do, Proposed | `[ ]` | Committed still means not started |
| Active, In Progress, Doing | `[/]` or `[!]` | |
| Blocked, Impediment | `[!]` + Issue ID | Add the Issue ID to the task, not to ADO |
| Done, Closed, Resolved, Completed | `[x]` | Only when our own evidence check passes too |

An unknown state is an Andon: add it to `ado_drift.py` or fix the state in ADO. Never guess.

## When docs and ADO disagree

`tasks.md` wins for our records. Then:

1. ADO says Done, `tasks.md` says not done → there is no evidence yet. Keep `tasks.md` as it is, report "ADO ปิดแล้ว แต่ยังไม่มีหลักฐานของเรา", and list what evidence is missing.
2. `tasks.md` says done, ADO still open → ask the project lead to close it in ADO (or name who should). Do not close ADO yourself unless the owner asked.
3. Item exists in ADO with no task → report as a note; propose where it belongs, don't create a task silently.
4. Task exists with no ADO item → report; the owner decides whether to open one.

Never edit ADO from a docs task. Writing to ADO (including a Description) is a separate, explicit request from the project lead; `.project-docs/azure-devops.md` says what to write.

## What to show in docs

- Phase file header: the PBI line above. `project/README.md` shows each phase's PBI link in its phase table (filled by `sync_project_readme.py`).
- Roadmap row: link the PBI so the owner can jump from plan to backlog.
- Presentations: a link to the PBI on the blockers slide when a blocker is owned by someone else.
- `memory-bank/progress.md`: ADO ids in the status line only when an item is blocked or unmapped. Do not mirror the backlog there.
