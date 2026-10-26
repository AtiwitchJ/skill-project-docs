# Memory bank: handshake with project/ and docs/

The `memory-bank` skill (installed, `~/.agents/skills/memory-bank/SKILL.md`) owns the files, their templates, the startup read order and the update workflow. **Do not restate or copy it here.** This file only says how the memory bank hands off to `project/`, `docs/explanation/` and `docs/reference/`, which the memory-bank skill does not know about.

## Division of ownership

| Question | Owner |
|---|---|
| What is left to do, and its state | `project/phases/phase-N/tasks.md` |
| Project-wide status and dates | `project/roadmap.md` (paired `.html`) |
| Troubleshooting detail | `project/issues.md` |
| How the system works, why | `docs/explanation/`, `docs/reference/` |
| What an agent needs to resume | `memory-bank/` |

Memory-bank holds a **summary plus a link**, never a copy. If a fact has a `docs/` owner, fix the owner and point at it.

## What the memory bank may not carry

- Counts or numbers typed by hand. Task counts come from `parse_tasks`; test numbers cite the results page or its JSON and the run date.
- Copied tables, charts or backlog listings.
- Secrets, tokens, real confidential content.
- A second status narrative that drifts from `roadmap.md`.

## Handshake points

| Event | Update, same pass |
|---|---|
| Task starts / done / blocked | `activeContext.md` focus; `progress.md` status. Counts from TASKS, Issue IDs from the register |
| Phase closes | focus → next phase; `roadmap.md` phase status |
| New permanent fact (architecture, setup, scope) | the matching memory-bank file **and** the `docs/explanation/` or `docs/reference/` page it came from |
| ADO drifted or a work item is unmapped | one line in `progress.md` with the ADO id; detail stays in `integrations/azure-devops.md` |

Skip the memory bank for formatting or wording-only edits.

## Closing check

1. `activeContext.md` focus names the phase actually being worked.
2. Every phase count in `progress.md` equals the count from TASKS.
3. Every blocker has an Issue ID that exists in `issues.md`.
4. Nothing in the memory bank contradicts `project/` or `docs/`.
5. No page in `docs/` or `project/` points readers at the memory bank; it is the agent's, not the reader's (the gate warns).

## What this skill gives back (the other half of the contract)

The `memory-bank` skill is installed and does not know this project. These are the guarantees `project-docs` provides so a memory-bank update never has to guess:

| The memory bank needs | Where it comes from |
|---|---|
| How many tasks are done in a phase | `project/phases/phase-<n>/tasks.md` headers, counted by `docs_lib.parse_tasks`; written into `progress.md` between `<!-- AUTO:phase-counts -->` markers by `scripts/sync_memory_bank.py` |
| Which blocker is real and still open | `project/issues.md` — the `OPEN` / `REOPENED` entries are the only valid blocker IDs |
| What changed recently, without reading all of `docs/` | the last entries of `project/roadmap.md` status line + the results page header date |
| Whether a fact is permanent or still a plan | `docs/explanation/` and `docs/reference/` for what is true now, `project/` for what is planned |

**Never read `docs/` end to end to update the memory bank.** Open TASKS, the issue register and the file the change is about; that is enough.

### AUTO block (counts are derived, not typed)

```markdown
<!-- AUTO:phase-counts -->
| Phase | Done / Total |
|---|---|
| 1 | 24 / 26 |
<!-- /AUTO:phase-counts -->
```

- `sync_memory_bank.py` writes it from TASKS; `check_docs.py` raises an ERROR when it disagrees.
- Never hand-edit the block: run the script. Hand-editing is exactly the drift the check exists to catch.
- Everything outside the block stays prose that a person writes (focus, decisions, next steps).

### Language

`memory-bank/` is **English** — it is read by the agent at the start of every session and English keeps it token-cheap and unambiguous. `docs/` is **Thai** because people read it. Do not translate one into the other; link across.
