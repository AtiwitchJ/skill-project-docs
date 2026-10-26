# project-docs

An agent skill that keeps a project's documentation true and consistent. Every fact has one owner file; derived pages are synced from it; a gate script refuses a docs change that leaves errors behind.

It works with Markdown and Excalidraw pages in `project/` (plan, phase tasks, presentations, results, issues, backlog) and `docs/` (tutorials, how-to, reference, explanation, sorted by Diátaxis).

## Install

Download outside the agent's skill folders, pin a reviewed commit, then enable it with symlinks. Keep each version in a separate folder so updates can be reviewed before activation and rolled back. The examples below use Claude Code and require Git.

### 1. Download a specific version

Replace `FULL_COMMIT_SHA` with the full commit SHA you intend to review, obtained from the trusted repository. Run this in a terminal, outside an agent session that might load the downloaded skill:

```bash
(
  set -eu
  skill_commit='FULL_COMMIT_SHA'
  skill_version="$HOME/.local/share/project-docs/versions/$skill_commit"
  mkdir -p "$HOME/.local/share/project-docs/versions"
  git clone --no-checkout https://github.com/AtiwitchJ/skill-project-docs.git "$skill_version"
  git -C "$skill_version" checkout --detach "$skill_commit"
  test "$(git -C "$skill_version" rev-parse HEAD)" = "$skill_commit"
)
```

If a command fails, stop and resolve it before continuing. A pinned SHA identifies the version; it does not prove the code is safe or the publisher is authentic.

### 2. Review before enabling

Review all bundled files, including `SKILL.md`, `scripts/`, `rules/`, `integrations/`, and templates. Check commands that write or delete files, access credentials, contact external services, or load other skills. Review the separately installed dependencies below as well. Do not run bundled scripts as part of this initial review.

The scripts use the Python standard library only (Python 3.9 or newer), except `qa_presentation.py`, which needs Playwright. Install that optional dependency in a separate Python virtual environment if you need presentation QA.

### 3. Enable the reviewed version

Use the same full SHA below. These commands refuse to replace an existing installation, including a dangling symlink:

```bash
(
  set -eu
  skill_commit='FULL_COMMIT_SHA'
  skill_version="$HOME/.local/share/project-docs/versions/$skill_commit"
  test -f "$skill_version/SKILL.md"
  test "$(git -C "$skill_version" rev-parse HEAD)" = "$skill_commit"
  mkdir -p "$HOME/.agents/skills" "$HOME/.claude/skills"
  for skill_link in "$HOME/.agents/skills/project-docs" "$HOME/.claude/skills/project-docs"; do
    if [ -e "$skill_link" ] || [ -L "$skill_link" ]; then
      printf 'Existing installation: %s. Back it up or use the update steps.\n' "$skill_link" >&2
      exit 1
    fi
  done
  ln -s "$skill_version" "$HOME/.agents/skills/project-docs"
  ln -s "$HOME/.agents/skills/project-docs" "$HOME/.claude/skills/project-docs"
)
```

Start a new agent session after activation. The user-level Claude Code link makes the skill available across projects; it does not sandbox the skill. The shared `~/.agents/skills/project-docs` path preserves the script paths used in this guide.

### Update or roll back

Do not run `git pull` in an active version folder or edit its reviewed files. Download a new SHA into its own folder using step 1, compare it with the active version using `git diff OLD_SHA NEW_SHA` in the new clone, and repeat the review in step 2.

Close agent sessions using the skill before switching. Record the current target with `readlink "$HOME/.agents/skills/project-docs"`. After checking that the shared path is a symlink and the new target contains the reviewed `SKILL.md`, remove **only that symlink** with `unlink "$HOME/.agents/skills/project-docs"`, then recreate it with `ln -s /absolute/path/to/reviewed/version "$HOME/.agents/skills/project-docs"`. Keep the Claude Code link pointing to the shared path. Roll back by repeating this switch with the recorded previous target.

For an existing installation that is a real directory, back it up outside the skill folders before following step 3. Do not delete it or overwrite it with a symlink.

References: [Git detached checkout](https://git-scm.com/docs/git-checkout), [Anthropic skill security guidance](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview#security-considerations).

## Dependencies

| Skill | Where it comes from | Why |
|---|---|---|
| `memory-bank` | install separately (upstream) | session context files under `memory-bank/`; this skill never edits it |
| `diataxis` | install separately (upstream) | the four-quadrant framework for `docs/`; this skill never edits it |
| `project-docs-sync` | separate skill, not in this repo | runs the sync flow (drift → change router → report) |
| `project-docs-now` | separate skill, not in this repo | the manual trigger of the same flow |

The skills share one rule: each has one job, and the change router (`rules/change-router.md`) is the only place that orders the work.

## Start a project

```bash
python3 ~/.agents/skills/project-docs/scripts/init_project.py --path <project folder> --name <name> --language Thai
```

This creates `.project-docs/` (config, rules, owner map, glossary, stale patterns, flow policy, diagram specs), `project/`, and the four `docs/` folders. It never overwrites an existing file.

Then fill in `.project-docs/rules.md` and `.project-docs/owner-map.md` for the project, and run the gate:

```bash
python3 ~/.agents/skills/project-docs/scripts/check_docs.py
```

Run the scripts from the project folder or any folder inside it. The project is found by its `.project-docs/config.json` (or `project/roadmap.md`).

## What is in the skill

```
SKILL.md              entry point: when to use it, the workflow, the definition of done
rules/                change router, writing rules, phases, flow, tools, diagrams
integrations/         Azure DevOps, Diátaxis, memory-bank
scripts/              the gate, sync scripts, drift check, diagram builder, tests
templates/            project scaffold, presentation template, diagram spec example
evals/evals.json      scenarios for checking that the skill behaves as its rules say
```

`rules/tools.md` lists every script and what it does.

## Diagrams

A picture can be built from a spec in `.project-docs/diagrams/`:

```bash
python3 ~/.agents/skills/project-docs/scripts/build_diagram.py .project-docs/diagrams/<name>.json --check
python3 ~/.agents/skills/project-docs/scripts/build_diagram.py .project-docs/diagrams/<name>.json
```

The builder checks the geometry before it writes: overlapping boxes, arrows that cross or pass through a box, text that does not fit, labels on top of boxes. The gate checks that each picture is exactly what its spec builds. See `rules/diagrams.md`.

## Tests

```bash
cd <project folder>
python3 ~/.agents/skills/project-docs/scripts/test_build_diagram.py
```

The tests write only to temporary folders.

## Limits

- The text-fit check estimates glyph width at 0.6 em per character. Thai and other wide scripts can be wider, so look at a picture before you trust it.
- The Azure DevOps check is read-only. It never writes to the backlog.
- The quadrant audit and the step-heading signals include Thai words, because the default language of the templates is Thai. Set the language in `.project-docs/config.json` and extend the signals for other languages.

## License

Not chosen yet.
# skill-project-docs
