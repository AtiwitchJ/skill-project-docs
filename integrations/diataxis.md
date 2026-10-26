# Diátaxis: when and how to use the installed skill

The `diataxis` skill (installed at `.agents/skills/diataxis/`, same content symlinked at `~/.agents/skills/diataxis/`; from [keithpatton/diataxis-agent-skill](https://github.com/keithpatton/diataxis-agent-skill), CC BY-SA 4.0) owns the framework: quadrants, compass, generate policy, anti-patterns, output format. **Do not restate it here and do not copy it into this skill.** Load it with `skill: "diataxis"` when a docs task needs classification, an audit, generation inside one quadrant, or a split.

**Name vs slash command.** The skill's name is `diataxis`; `diataxis-agent-skill` is the repository name and only a prompt alias. In this repo that alias lives at `.github/prompts/diataxis-agent-skill.prompt.md` and just loads the skill plus the overrides below — it carries no framework text. If the prompt file is unavailable in your harness, load the skill directly with `skill: "diataxis"`.

This file only says when that applies in this project and what overrides it.

## The four quadrants (upstream table, for quick reference)

Upstream keeps this table only in its README (`keithpatton/diataxis-agent-skill#the-four-quadrants`) and ships the same content as prose under `## Quadrant Summary` of the installed `SKILL.md`. The installed `SKILL.md` is kept byte-identical to upstream, so this table lives only here, once. Attribution: CC BY-SA 4.0.

| Quadrant | Purpose | User Context |
|---|---|---|
| **Tutorial** | Learning-oriented lesson | Study (acquisition) |
| **How-to** | Goal-oriented directions | Work (application) |
| **Reference** | Information-oriented description | Work (application) |
| **Explanation** | Understanding-oriented discussion | Study (acquisition) |

Where they live: the folder is the quadrant (`docs/tutorials/`, `docs/how-to/`, `docs/reference/`, `docs/explanation/`), so there is no page list to keep. `diataxis_audit.py` checks that a page's declaration matches both its folder and its content.

## When to load it

| Trigger | Mode |
|---|---|
| New page in `docs/tutorials/`, `docs/how-to/`, `docs/reference/`, `docs/explanation/` | generate (confirm the quadrant first) |
| Page grew two jobs (spec + walkthrough, results + reasoning) | restructure |
| Project lead asks "audit the docs", "classify the docs", "diataxis" | audit |
| Unsure where a paragraph belongs | classify |

No load needed for `project/` pages, presentations, diagrams or a wording fix.

## Project overrides

The skill's general rules bend to these; state the override when reporting.

- **Scope:** `docs/tutorials/`, `docs/how-to/`, `docs/reference/`, `docs/explanation/` only. `project/` and `memory-bank/` are not Diátaxis documents — they track work and context. Never rewrite a task file or `test-results.md` into prose to satisfy a quadrant.
- **`project/` pages stay austere:** task files, the issue log, `roadmap.md` and the results pages hold status and results. Reasoning that belongs to a reader goes to `docs/explanation/`.
- **Results pages stay results-only** (tables, numbers, charts), as listed in `.project-docs/config.json` → `results_only`. `check_docs.py` errors on a sequence diagram there.
- **Content language is the project's** (`.project-docs/config.json` → `language`) and its established terms stay as they are; the installed skill's English examples do not change that.
- **Owner rules win over style:** `.project-docs/owner-map.md`, `.project-docs/glossary.md`, no real confidential data or credentials.
- **Splitting costs a link:** when a section moves, leave a relative link at the old place and update `docs/README.md`. A split that breaks links fails the gate.

## Declaration

Every reader-facing page carries its quadrant in the header block, next to the date:

```markdown
> **Diátaxis:** Reference
```

Values: `Tutorial`, `How-to`, `Reference`, `Explanation`.

## Audit

`diataxis_audit.py` is the light check, not a replacement for the skill: it compares the declaration with the signals a page actually has and flags pages that carry two jobs.

```bash
python3 ~/.agents/skills/project-docs/scripts/diataxis_audit.py           # all reader-facing pages
python3 ~/.agents/skills/project-docs/scripts/diataxis_audit.py --path docs/explanation/architecture.md
```

Exit 1 means a split candidate. A WARN (no declaration) is a decision: declare it, or record why the page stays mixed. Findings go in the report as router type K.
