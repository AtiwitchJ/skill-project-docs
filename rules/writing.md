# Writing rules: for the project lead

The project lead decides from real numbers and diagrams, reads fast, gives short orders, and checks whether anything real changed. Every doc and every reply follows these rules. Rules that depend on the project (language, names, diagram conventions, which pages are results-only, the source plan) are in `.project-docs/rules.md`; read it too.

**Replies**
- First line answers the question (done / not done / blocked on what). No theory, no explaining concepts the team already uses.
- Always say **whether code changed**: list doc files and code/script/config files separately. If only docs changed, say so. A doc that says "fixed" while the code is unchanged is an overclaim.
- Short orders such as "remove X" are decisions. Do it, don't ask again, and don't move the content somewhere else.
- **Tone & style:** Write human, crisp bullet points rather than wordy, robotic AI prose. Avoid fluff, repetitive boilerplate, and generic praise.
- **Evidence & visuals:** When presenting benchmark or test results, embed the real result chart or visual artifact directly. Follow each image with concise bullets explaining: (1) what the axes, markers, and colors mean, (2) the core numbers observed, and (3) caveats or what the picture does not show.

**Diagrams before prose**
- Multi-step workflows and architecture go in an open, editable diagram format (`.excalidraw`), not long text blocks. A generated diagram is changed by editing its generator and rerunning it; never hand-edit the output (the next run overwrites it).
- Change a diagram in the generator, not in the editor: a rerun overwrites what was edited in the editor, so paste the idea into the script and rerun.
- Keep one `.excalidraw` file per project unless `.project-docs/rules.md` says otherwise. A second diagram becomes another block in the same generator, not a new file.
- Editor autosave copies (`Untitled-*.excalidraw`, or a copy made while a diagram is open in the editor) are deleted at once. They hold stale elements, and the gate fails them by the lower-case file-name rule.
- When a diagram shows where parts run, draw the runtime as one labelled frame. A part that runs elsewhere sits outside the frame and says where it runs. The project names its frames in `.project-docs/rules.md`.
- Comparisons use one column per alternative, with the same dimensions in every column. Missing data reads as an explicit "no result yet", never blank.
- Keep layouts symmetric: equal box sizes per row, equal spacing, no crossing arrows. Alternatives that are peers sit on the same level in every diagram.
- Step labels are plain numbers, never circled digits.
- Easy to read, not machine-looking: one flowchart per page (unless the project names a multi-block file in `.project-docs/rules.md`), a node holds a short phrase (about 6 words) and the detail stays in prose elsewhere; no emoji; show "who talks to whom" as boxes and arrows, not text walls; mark a special point with a small badge on the arrow, not extra paragraphs; light colours the owner can see clearly.
- Check the drawing after generating it: no box overlaps, no arrow through a box, no text outside its box (`scripts/build_diagram.py --check` checks these for a spec-built diagram; it does not judge how the picture reads). If you cannot open the diagram tool, render a quick preview and say it was not looked at in the tool itself.

**Results = numbers + charts**
- A results page holds results only: tables, numbers and charts. No sequence diagrams there; call flows belong on an explanation page. The gate raises an ERROR for the pages listed in `.project-docs/config.json` → `results_only`.
- When cutting content, **never cut charts** unless told to remove that chart. When data changes, regenerate the chart from its script; never hand-edit generated SVG.
- Show raw evidence when asked (the JSON that was sent and received), not a description of it.

**One name per thing**
- Use the names in `.project-docs/glossary.md` only. When two terms mean the same thing, propose one name, fix every file in the same pass, and add the old name to the glossary and `.project-docs/stale-patterns.json`.
- Never coin a new name for something that already has one.

**Cut to the core**
- Include only what the page's reader needs to decide. Out-of-scope content stays out; link to its owner if one exists.
- No unrequested sections, callouts or "deep-dive analysis" boxes. Don't define terms the team already uses.

**Security must be concrete**
- When a doc covers roles, permissions or credentials, write it as a threat model: what an attacker holding this role can do, which tools/APIs are dangerous, and what limits the damage. Name real roles, not generic wording.

**Pages people read keep agent tooling out**
- `docs/` and `project/` never mention the memory bank, the flow log or skill files; those live in `memory-bank/`, `.project-docs/` and the agent's skill folders. The gate warns on it (exception: pages listed in `.project-docs/flow-policy.json` → `agent_pages`, whose job is agent tooling).

**Reader-facing pages in `docs/`**
- Start at `docs/README.md`. Organize by the questions readers ask; add a page only for a topic that stands on its own.
- Readable without the chat history; spell out abbreviations when first needed.
- Repo facts only. Separate confirmed facts from plans, assumptions and pending decisions. Never invent results, status or system details.
- When a fact has an owner (task, config, code, architecture, setup guide), fix the owner when assigned; the page summarizes and links. Avoid long or fast-changing copies.
- Project scope only. No real or confidential data, no credentials.
- Relative links. Update `docs/README.md` when pages are added, moved or removed.
- File names are lower-case words joined by dashes (`architecture-matrix.md`); the gate enforces it.
