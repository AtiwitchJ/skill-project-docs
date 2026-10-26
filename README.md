# project-docs

An agent skill that keeps a project's documentation true and consistent. Every fact has one owner file; derived pages are synced from it; a gate script refuses a docs change that leaves errors behind.

It works with Markdown and Excalidraw pages in `project/` (plan, phase tasks, presentations, results, issues, backlog) and `docs/` (tutorials, how-to, reference, explanation, sorted by Diátaxis).

## Visual overview

The English infographic covers configured integrations, phase flows, charts, test reports and explicit migration. The animated walkthrough shows an illustrative task closure: update the owner file, sync derived blocks, catch a remaining mismatch at the gate, fix it, and hand over with evidence. It is a simulated explanation, not a recording of a live project or a measured result. Narrative text still needs review.

![Animated project-docs workflow: owner file, sync, gate, correction, and handover](assets/project-docs/project-docs-workflow.gif)

<details>
<summary>Open the English infographic</summary>

![English infographic explaining project-docs responsibilities and workflow](assets/project-docs/project-docs-infographic.png)

</details>

[Infographic PNG](assets/project-docs/project-docs-infographic.png) · [Animated GIF](assets/project-docs/project-docs-workflow.gif) · [Still preview](assets/project-docs/project-docs-workflow-poster.png)

The infographic was created with ImageGen and checked against `SKILL.md` and `rules/tools.md`. The GIF uses original code-drawn graphics; rebuild it on macOS with `python3 assets/project-docs/build-gif.py` (requires Swift/AppKit and Pillow).

## Install

Download from `main` outside the agent's skill folders, review the downloaded version, then enable it with symlinks. Keep each version in a separate folder so updates can be reviewed before activation and rolled back. The examples below use Claude Code and require Git.

### 1. Download from main

Use `main` as the installation source. You do not need to find or enter a commit SHA. The commands resolve `main` to a commit automatically and record the downloaded version, so activation uses the same code you reviewed even if `main` changes afterward.

| Toolkit MANIFEST setting | Value |
|---|---|
| Repository | `https://github.com/AtiwitchJ/skill-project-docs.git` |
| Branch / ref | `main` |
| Shared activation path | `~/.agents/skills/project-docs` |
| Claude Code activation path | `~/.claude/skills/project-docs` (symlink to the shared path) |

If a toolkit installer uses a MANIFEST, configure this repository URL and branch/ref `main` using its existing schema. This repository does not supply that installer's MANIFEST. The installer should record the resolved commit in its installation report. A manual SHA is optional when you specifically need an older version; do not leave an unresolved commit placeholder that causes installation to be skipped.

Run this in a terminal, outside an agent session that might load the downloaded skill:

```bash
(
  set -eu
  skill_repo='https://github.com/AtiwitchJ/skill-project-docs.git'
  skill_ref='main'
  skill_commit=$(git ls-remote --exit-code "$skill_repo" "refs/heads/$skill_ref" | cut -f1)
  test "${#skill_commit}" -eq 40
  case "$skill_commit" in *[!0-9a-f]*) exit 1 ;; esac
  skill_version="$HOME/.local/share/project-docs/versions/$skill_commit"
  mkdir -p "$HOME/.local/share/project-docs/versions"
  if [ ! -e "$skill_version" ] && [ ! -L "$skill_version" ]; then
    git clone --no-checkout "$skill_repo" "$skill_version"
    git -C "$skill_version" checkout --detach "$skill_commit"
  fi
  skill_version=$(cd "$skill_version" && pwd -P)
  test "$(git -C "$skill_version" rev-parse --show-toplevel)" = "$skill_version"
  test "$(git -C "$skill_version" rev-parse HEAD)" = "$skill_commit"
  test -z "$(git -C "$skill_version" status --porcelain --untracked-files=all)"
  test -f "$skill_version/SKILL.md"
  printf '%s\n' "$skill_commit" > "$HOME/.local/share/project-docs/candidate-commit"
  printf 'Downloaded %s at %s\nReview this folder: %s\n' "$skill_ref" "$skill_commit" "$skill_version"
)
```

An existing version folder is reused only if it is the expected clean Git checkout at that commit. If any command fails, stop and inspect that folder; do not delete it or overwrite it automatically. The commands resolve the version folder to its canonical path before verification.

### 2. Review before enabling

Review all bundled files, including `SKILL.md`, `scripts/`, `rules/`, `integrations/`, and templates. Check commands that write or delete files, access credentials, contact external services, or load other skills. Review the separately installed dependencies below as well. Do not run bundled scripts as part of this initial review.

The scripts use the Python standard library only (Python 3.9 or newer), except `qa_presentation.py`, which needs Playwright. Install that optional dependency in a separate Python virtual environment if you need presentation QA. Playwright is not required to install the skill or run its ordinary documentation checks.

### 3. Back up existing installations and enable

After review, close Claude Code and other agent sessions using this shared skill. Run the following in a standalone terminal. It handles fresh installs, existing real directories, ordinary files and dangling symlinks. Existing entries are **moved intact** into a unique backup folder outside the skill discovery paths; they are never recursively deleted. Both activation paths are then linked to the version recorded in step 1. If you rerun step 1, review that newly recorded candidate before activating it.

```bash
(
  set -eu
  skill_commit=$(cat "$HOME/.local/share/project-docs/candidate-commit")
  test "${#skill_commit}" -eq 40
  case "$skill_commit" in *[!0-9a-f]*) exit 1 ;; esac
  skill_version="$HOME/.local/share/project-docs/versions/$skill_commit"
  skill_version=$(cd "$skill_version" && pwd -P)
  test "$(git -C "$skill_version" rev-parse --show-toplevel)" = "$skill_version"
  test "$(git -C "$skill_version" rev-parse HEAD)" = "$skill_commit"
  test -z "$(git -C "$skill_version" status --porcelain --untracked-files=all)"
  test -f "$skill_version/SKILL.md"
  mkdir -p "$HOME/.agents/skills" "$HOME/.claude/skills" "$HOME/.local/share/skill-backups/project-docs"
  skill_backup=$(mktemp -d "$HOME/.local/share/skill-backups/project-docs/activation.XXXXXX")
  printf 'Backup directory: %s\n' "$skill_backup"
  for skill_scope in agents claude; do
    skill_link="$HOME/.$skill_scope/skills/project-docs"
    if [ -e "$skill_link" ] || [ -L "$skill_link" ]; then
      mv "$skill_link" "$skill_backup/$skill_scope-project-docs"
    fi
  done
  ln -s "$skill_version" "$HOME/.agents/skills/project-docs"
  ln -s "$HOME/.agents/skills/project-docs" "$HOME/.claude/skills/project-docs"
  test "$(readlink "$HOME/.agents/skills/project-docs")" = "$skill_version"
  test "$(readlink "$HOME/.claude/skills/project-docs")" = "$HOME/.agents/skills/project-docs"
  test -f "$HOME/.claude/skills/project-docs/SKILL.md"
  printf 'Enabled project-docs at %s\nRetain this backup: %s\n' "$skill_commit" "$skill_backup"
)
```

Record the printed backup path. If activation stops midway, the old entries remain in that folder as `agents-project-docs` and/or `claude-project-docs`. Resolve the failed step or restore them before starting agents again. Moving an old symlink preserves the link itself, not a copy of its target; keep its original target available for rollback.

Start new agent sessions after activation. The Claude Code link makes the skill available across projects; it does not sandbox the skill. Other agents already using the shared `~/.agents/skills/project-docs` path will also see this version, so this is a shared update even when Claude Code initiated installation. Review separately if your toolkit promises to modify only one agent.

### 4. Verify the installation and companion skills

These checks read metadata only and do not run the downloaded skill's scripts:

```bash
readlink "$HOME/.agents/skills/project-docs"
readlink "$HOME/.claude/skills/project-docs"
git -C "$HOME/.agents/skills/project-docs" rev-parse HEAD
test -f "$HOME/.claude/skills/project-docs/SKILL.md"
```

The commit must match the download report and `~/.local/share/project-docs/candidate-commit` from the installation you just activated. This records the installed version; it does not make you configure a SHA manually. After restarting Claude Code, check that project-docs is discoverable without a second active copy.

`project-docs-sync` and `project-docs-now` are separate companion skills, not bundled here. The automatic sync route in `SKILL.md` refers to them. If already installed, establish and review their source/version before relying on that automation; do not overwrite unknown-source copies. No installation source for these companions is prescribed by this repository. Without them, use the explicit documentation scripts listed in [rules/tools.md](rules/tools.md) and report that the companion automation is unavailable. Their absence does not prevent downloading or activating project-docs itself.

### Update or roll back

Do not run `git pull` in an active version folder or edit its reviewed files. To update, rerun step 1 to download the current `main`, compare the recorded old and new commits using `git diff OLD_SHA NEW_SHA` in the new clone, and repeat review and activation. Downloading does not change the active installation. Choosing an exact historical SHA remains an optional advanced workflow. Keep older versions and activation backups.

For rollback, close affected agent sessions first. Verify that both current activation entries are symlinks installed by the activation block. Remove only those links with `unlink`, then move the saved `agents-project-docs` and `claude-project-docs` entries back to their corresponding paths. Restore only entries that actually existed in that backup; a previously absent path can remain absent. If either current entry is now a real directory/file, move it to a separate backup rather than unlinking or deleting it. Verify the restored paths and restart agents. Never recursively delete the old installation.

References: [Git detached checkout](https://git-scm.com/docs/git-checkout), [Anthropic skill security guidance](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview#security-considerations).

## Phase flows and evidence presentations

Every phase can show its steps and current progress in both `tasks.md` and `presentation.html`. Status is derived from Task headers: all active and blocked steps remain visible, and verified task counts are not presented as estimates of effort or time. Optional grouping lives in `.project-docs/presentations/phase-N.json`; no status is duplicated there.

The HTML template adds reading/presentation modes, a slide index/counter, keyboard navigation, full screen, print/PDF styles and inspectable source-value tables. Charts are inline SVG and work offline. Selection follows the reader's question: bars compare categories, lines show ordered change, scatter plots show relationships, stacked bars show contributions, and heatmaps show categorical patterns. Every chart explains why it was chosen and names its source, units and limitations.

Custom charts use a project-owned SVG generator with source/generator checksums. The example includes a paired-dot chart, which keeps each scenario's before/after values together. Native renderers also cover distributions, uncertainty intervals, waterfalls and schedules. Use a justified custom generator for coordinated multi-panel compositions or encodings beyond the native contracts.

```bash
python3 /path/to/skill/scripts/sync_presentation.py 1
python3 /path/to/skill/scripts/sync_presentation.py --all --check
```

See the [HTML example](examples/phase-presentation/project/phases/phase-1/presentation.html), [paired Markdown flow and charts](examples/phase-presentation/project/phases/phase-1/tasks.md), and [chart selection/customization guide](rules/presentation-charts.md). The example contains **synthetic fixtures only**, not measured project performance. Rebuild an example in a new empty directory with `python3 scripts/build_presentation_demo.py --output /path/to/empty-directory`.

## Integrations and migration

Choose the tracker in each project's config; installed tools do not choose it for you. Keep one primary tracker and add separate code/evidence connections.

| Integration | Reads and checks | Migration destination via direct API |
|---|---|---|
| Azure DevOps | Work items, comments, attachments, hierarchy | Work items, comments, files, parent links |
| GitHub | Issues, PR merge metadata, comments, sub-issues | Issues, comments and parent links; files need a capable bridge or an explicit archived-only limitation |
| Jira Cloud | Issues, workflow status, comments, attachments | Issues, transitions, comments, files and supported parent links |
| Linear | Issues, status, comments, linked attachments | Issues, comments, files and parent links |
| GitLab | Issues, MRs, notes and embedded uploads | Issues, notes and files; hierarchy is an explicit adapter limitation |
| GitHub Actions | Run/attempt/commit-bound test artifacts | Evidence source, not a tracker destination |

All 20 directed tracker pairs use the same migration engine. Actual features depend on the chosen transport's discovered capabilities and destination workflow. MCP is agent-operated; CLI requires a JSON bridge wrapper; direct APIs use Python standard-library HTTP clients. Normal docs checks are read-only externally; destination writes are restricted to explicit migration apply/resume operations.

Start with [provider configuration and bridge contract](integrations/providers.md), [Actions evidence](integrations/github-actions.md), or the [copy, verify, cutover and rollback guide](integrations/migration.md). Legacy ADO commands/config/Markdown mappings continue to work; `integrations.py upgrade` explicitly adds stable Task UIDs and shared mappings.

**Validation:** the offline suite exercises all 20 directions against a canonical simulated service and tests provider payloads, mocked API calls, CLI/MCP bridges, interruption recovery and artifact provenance. It does not prove live account permissions or full feature parity between providers. No real account data was migrated during development.

```bash
python3 -m unittest discover -s scripts -p test_integrations.py -v
```

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
integrations/         tracker providers, Actions evidence, migration, Diátaxis, memory-bank
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

## Test reports and readable charts

Use the [test-reporting guide](rules/test-reporting.md) to run tests and generate paired English Markdown/HTML, raw JSON, logs and failure workflows automatically:

```bash
python3 /path/to/skill/scripts/run_tests.py --root . --output project/results/tests/run-001 unittest --start-dir tests --pattern 'test_*.py'
```

For complex dashboards using multi-hop and Local/Workbench comparison patterns, use [advanced chart recipes](rules/advanced-chart-recipes.md): coordinated panels, step costs, cumulative curves, baseline ratios, environment comparisons and honest scaling. The design lessons are retained in the guide; the original SVG references were removed after review, and their benchmark JSON is not included.

There are **16 native chart families plus custom SVG charts**: comparison, series, trends, composition, relationships, matrices, distributions, intervals, paired changes, contributions and schedules. See the [interactive offline gallery](examples/chart-gallery/gallery.html), [Markdown gallery](examples/chart-gallery/gallery.md) and [selection rules](rules/presentation-charts.md). Reports select charts from actual available evidence; missing coverage/history stays explicit.

Examples: [intentional failure report](examples/test-report-fixture/verified/report.html) · [failure report Markdown](examples/test-report-fixture/verified/report.md) · [actual offline repository test report](examples/phase-presentation/project/results/tests/layout-verified/report.html).

HTML supports readable scrolling charts, vertical mobile workflows, responsive summaries, case search with pagination, source tables, print and visible error states. Test failures retain reports and their original nonzero exit code. Plain unittest commands outside this wrapper do not automatically create reports. Sample failure reports are intentionally failing fixtures, not production defects; integration tests use mocks, not live-service verification.

## Tests

```bash
cd <project folder>
python3 ~/.agents/skills/project-docs/scripts/test_build_diagram.py
```

The tests write only to temporary folders. To run the complete offline repository suite with reports, run `scripts/run_tests.py` from `examples/phase-presentation` and select `../../scripts` as `--start-dir`; the diagram tests require a documented project root.

## Limits

- The text-fit check estimates glyph width at 0.6 em per character. Thai and other wide scripts can be wider, so look at a picture before you trust it.
- The Azure DevOps check is read-only. It never writes to the backlog.
- The quadrant audit and the step-heading signals include Thai words, because the default language of the templates is Thai. Set the language in `.project-docs/config.json` and extend the signals for other languages.

## License

Not chosen yet.
# skill-project-docs
