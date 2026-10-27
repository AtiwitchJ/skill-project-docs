# Diagrams from a spec

A project that draws an `.excalidraw` picture with this skill keeps a spec in `.project-docs/diagrams/<name>.json`. `scripts/build_diagram.py` turns the spec into the file named in it and checks the drawing first. A project whose picture is drawn by its own generator keeps that generator (owner-map); this page does not replace it.

Start from `templates/diagram-spec.example.json`: two blocks, a framed runtime lane, tags, an elbow arrow. Copy it into the project and change it.

## Commands

Run from the project folder or any folder inside it.

```
python3 ~/.agents/skills/project-docs/scripts/build_diagram.py .project-docs/diagrams/<name>.json --check   # check only
python3 ~/.agents/skills/project-docs/scripts/build_diagram.py .project-docs/diagrams/<name>.json          # check, then write
python3 ~/.agents/skills/project-docs/scripts/test_build_diagram.py                                         # the skill's own tests
```

The gate (`check_docs.py`) runs the same check on every spec in `.project-docs/diagrams/` and reports ERROR when the picture on disk is not exactly what its spec builds. A project without that folder is not checked.

Exit 0: checked, or written. Exit 1: problems found, nothing written. Exit 2: the spec cannot be read. Standard library only. The same spec always gives the same file.

## The spec

| Key | Meaning |
|---|---|
| `file` | output path from the project root. Name: lower-case words joined by dashes, ending `.excalidraw` |
| `dimensions` | named lists of row values, e.g. `"variant": ["A", "B", "C"]`. Values are strings, in the order they are drawn |
| `row_labels` | optional text shown for a row value, per dimension |
| `tags` | any number of dimensions (auth, env, status). A value may carry `label` and `style`. A tag with a style gets colour and a legend entry |
| `limits` | optional; default 5 lanes, 8 rows, 3 blocks per file. Raise only when `.project-docs/rules.md` says so |
| `blocks` | one picture each, stacked top to bottom in the file |

Block: `id`, `title`, `row_by` (the dimension that gives the rows), `lanes` (columns, left to right), `nodes`, `edges`.

- Lane: `id`, `label`, optional `frame` (a box around the lane, e.g. a runtime): `{"style": "solid" | "dashed", "color": ...}`.
- Node: `id` (unique in the file), `lane`, `row`, `text` (write `\n` for a line break), optional `shape` (`rectangle`, `ellipse`, `diamond`), `style`, `tags`. Without `style` the colour comes from the first tag that has one.
- Edge: `from`, `to` (node ids of the same block), optional `id`, and either `badge` (text on the arrow) or `tag` (text and colour from a tag), plus optional `badge_style`.
- Colours: `white`, `grey`, `blue`, `green`, `red`, `violet`, `yellow`, `orange`. No other values.

## What the builder draws

- One node per lane and row. Lanes are columns; rows follow the order of `row_by`.
- An arrow inside one lane runs vertically; inside one row it runs horizontally; anything else is an elbow that runs in the gap between two lanes. Elbows that share a gap each get their own vertical line.
- A label sits above a horizontal arrow, beside a vertical one, and on the vertical piece of an elbow.
- The legend lists each tag that has a style and is used in the block.
- A frame is drawn behind the boxes of its lane.

## What the check refuses

Each of these is an ERROR and nothing is written:

- two boxes overlap, or two nodes share a lane and row
- an arrow passes through a box that is not its start or end; two arrows cross or run on the same line (arrows that leave or enter the same box may meet there)
- a label covers a box, an arrow or another label
- text does not fit its box. The estimate is 0.6 em per character. Thai has no spaces, so a long Thai phrase stays on one line: break it with `\n` and check by eye
- an emoji or a circled digit (write plain numbers, e.g. step 1), or text matching a pattern in `.project-docs/stale-patterns.json`
- an unknown dimension value, tag, style, shape, lane or row; too many lanes, rows or blocks; a bad file name

## What the check does not see

How the picture reads: balance, meaning, colour contrast, and the real font width. Open the file by eye (excalidraw.com or the VS Code extension). If you cannot open it, say so in the report.

## Where things live

- The spec and the `.excalidraw` are project files. Put the spec in `.project-docs/diagrams/`.
- Never edit the `.excalidraw` by hand. An edit made in the editor is lost on the next build; move the idea into the spec and rebuild.
- Which dimensions, layers and limits a project uses, and any node-text rule, belong in its `.project-docs/rules.md`.
- Keep one `.excalidraw` per project unless `rules.md` says otherwise. A new picture becomes a new block in the same spec.
- List the output under `drift.generated` in the project's `config.json` with the spec as its input. `drift.py` then reports the picture as stale when the spec is newer.

## Workflow (change-router H)

1. Edit the spec, not the picture.
2. Run `build_diagram.py <spec> --check` and fix every ERROR.
3. Run `build_diagram.py <spec>` to write the file.
4. Delete any `Untitled-*.excalidraw` copy the editor left behind.
5. Open the file by eye and say in the report whether you did.
6. Run the gate. It reports ERROR when the picture is a hand edit or was not rebuilt after the spec changed.
6. Run the gate (`flow_log.py finish <id>`).

## Relocating existing diagrams during rework

Follow `rules/rework.md` for repository-wide artifact relocation and missing-file completion. Use the explicit project destination, or `project/diagrams/` for editable project diagrams when none is defined. Update the spec's `file`, generator paths and all links together, then validate the result. Preserve an existing original diagram without a generator as an editable source and register its owner; do not overwrite it with a guessed spec. Reader-facing exports may live with the pages that use them.
