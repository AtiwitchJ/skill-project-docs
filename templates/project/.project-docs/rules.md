# Project rules: {{PROJECT_NAME}}

Read these with the memory bank at the start of every docs task. They extend the general rules in the project-docs skill (`rules/writing.md`, `rules/phases.md`); where the two differ, this file wins for this project. Delete the sections you do not need.

## Language and names

- Doc content is written in {{LANGUAGE}}. Keep file names, code identifiers and established terms as they are.
- Names for the project's concepts come from `glossary.md` in this folder.

## Diagrams

- Editable project diagrams default to `project/diagrams/`; diagram specs stay in `.project-docs/diagrams/`. Record a different established destination in owner-map. Published previews belong with their reader pages/results.

- (How comparisons are laid out, what labels steps use, which diagrams are generated and by which script.)
- (How many `.excalidraw` files the project keeps. If one: a second diagram is a new block in the same generator. If more: name each file and its owner in `owner-map.md`.)
- (Runtime frames a diagram draws, for example the cloud environment, and what sits outside each frame and where it runs.)

## Results

- (Which pages hold results only; list them in `config.json` → `results_only`. Which scripts generate charts.)

## Plan and phases

- Task titles use the existing number plus `[plan topic]` and an actionable name when plan-topic grouping applies. Category → plan topic → Task follows `rules/task-naming.md` in the skill; preserve original labels or explicitly recorded aliases, Task UIDs and scope decisions.

- (Where the source plan lives, how many phases it has, how off-plan work is recorded, the task and roadmap formats.)

## Data and safety

- (What data may live in the repo; which page, if any, may talk about agent tooling: list it in `flow-policy.json` → `agent_pages`.)
