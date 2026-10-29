# Task hierarchy, titles and plan traceability

Use when creating, regrouping or renaming phase tasks, especially when a source plan/diagram contains named work boxes. Read the actual source plan first. A suggested table in chat is not evidence that tasks exist, tests passed or scope decisions were accepted.

A title groups and identifies work; it does not replace an understandable Description. Follow `rules/task-descriptions.md` to explain purpose, deliverable, intended use and evidence inside the project-approved format.

## Three levels, with one stable identity

```text
Work category
└── Exact topic from the source plan
    └── Task number [Topic label] Actionable task title
```

For example, a category can be PoC or Experiments, a plan topic can be `Agent with Azure MCP`, and the title can be `2.6 [Agent with Azure MCP] เตรียม Azure MCP`. These names and the number are format examples, not an instruction to create Azure work or claim delivery.

Use this canonical title format in Markdown and in a tracker title prepared for review:

```text
<existing phase.task number> [<plan topic label>] <concrete action and object>
```

Keep a space after the number and after `]`. The parsers also recognize legacy compact headers such as `2.6[Agent with Azure MCP] ...`; normalize spacing without changing the number or UID. Do not add a second numeric prefix or confuse a local Task number with an external work-item ID.

Preserve the existing Task number and `**Task UID:**` across title changes, regrouping and moves. In particular, if `2.6` already names another task, do not reuse it for Azure MCP: use the actual existing Azure task's number or the next available number for genuinely new approved work. A project moving tasks between phases must follow its existing identity/numbering policy rather than renumbering references for visual neatness. External IDs and many-to-many mappings stay in their existing metadata/mapping owners.

The middle level is a logical plan topic, not automatically another remote issue type. Represent it with a consistent title prefix, metadata and, where useful, tags/labels already supported by the configured tracker. The work category can map to a Feature/Epic/PBI only when the project's existing process/owner mapping says so. Do not insert hierarchy nodes, change parents or assume every tracker supports three physical levels just to match the visual tree.

## Markdown structure and ownership

Use `## <Work category>` headings inside the existing phase `tasks.md`; keep `### [mark] ...` for actual Task headers, since scripts parse that level. The topic prefix in each title supplies the middle level; use metadata for exact source/category details rather than a separate per-task file. Example shape:

```markdown
## Experiments

### [ ] 2.6 [Agent with Azure MCP] เตรียม Azure MCP

**Task UID:** existing-stable-uid
**Work category:** Experiments
**Plan topic:** Agent with Azure MCP
**Plan source:** actual source path and exact box/section identifier
**Scope disposition:** in-scope
**ADO:** #existing-external-id

- [ ] Define a real, testable outcome from the approved plan.
```

This is a format illustration. Reuse actual UID/external IDs; omit unmapped tracker metadata instead of inventing IDs. For new identities use the established UID creation/upgrade path. Category/topic/source/disposition fields are ownership metadata checked against a reviewed topic registry by `scripts/task_naming.py`. Generic title parsing still does not build a nested tracker tree or prove that the source-plan interpretation is correct.

Keep the bracket label identical to the source topic where practical. If the project explicitly chooses a shorter label, record the exact original topic and the approved alias in the glossary/owner convention; never silently replace `Setup MCP for testing datastore` with a different phrase and claim an exact match. If the source is an image, cite its actual path and box text; state uncertain reading and ask for that specific ambiguity rather than guessing from the filename. A baseline or evaluation group added outside the original plan needs its explicit origin/decision, not a fabricated source box.

Write action-oriented titles, and place details/acceptance evidence in the body. Keep category membership explicit, rather than guessing that any task containing “MCP” belongs to the same group. If a task spans topics, choose a primary title topic and record the additional sources in its body/mapping; split it only when the work/acceptance boundaries actually justify distinct Tasks. Preserve previous evidence and identity.

## Scope decisions are not completion

Keep cut-out, cancelled, deferred and out-of-scope tasks visible with their original number/UID, source topic, reason, decision date and decider or linked decision/Issue. A date or person is recorded only when known. Do not delete the task to make the phase look complete, or check `[x]` simply because the decision to exclude it is settled.

Use the project's existing exclusion/status policy. With this skill's four Task markers and no separate exclusion model, unresolved blocked work can use `[!]` with an Issue and a clearly labelled `Scope disposition`/decision. Accepted excluded work remains explicitly distinguished from delivered work; phase closure follows router C's recorded-exception rule. Do not invent new checklist markers (`[-]`, `[cancelled]`) unsupported by the parser, silently remove tasks from totals, raise completion percentages by exclusion, or claim that exclusions are automatically deducted by current scripts. Existing done counts still count only `[x]`.

In Azure DevOps or another tracker, use only the actual project's configured state mapping and allowed process transitions. Never assume a universal `Removed` or `Closed - Out of Scope` state, or map a cancelled item to verified done. Unknown provider states require an explicit mapping decision. Normal docs/update/rework commands do not write remote titles, tags, parents or states; they may prepare an exact proposed-title/state table. Remote changes need their own explicit authorization and supported workflow.

## Regroup and verify

1. Inventory real Task numbers/UIDs, existing titles, external mappings, source topics and evidence. Build an old → new title/category/topic table before renaming; reuse existing tasks before proposing new ones.
2. Apply authorized local naming/grouping changes in the owner `tasks.md`, preserving Task and checklist status unless real evidence independently supports a status change. Keep external mappings intact; title text does not replace an ID mapping.
3. Link each source topic to the actual Task UID/number(s) in the phase summary or an existing traceability view. Identify topics with no task, tasks without a plan origin, alias mismatches and explicitly excluded topics. Coverage claims require an enumerated source inventory and reviewed mapping; neither a bracket tag nor a claimed “100% traceability” proves coverage.
4. Update affected glossary/owner rules, phase flow grouping, presentation, indexes and references. The current phase-flow renderer has flat steps; use category/topic labels or task UID groups, not an invented nested-flow schema. Explain grouping versus dependencies accurately.
5. Run phase sync/check and the docs gate, inspect rendered titles/line wrapping, and recheck UID/external-ID continuity. Compare tracker titles only from configured/read evidence; publish proposed remote differences, not an assertion that ADO was changed.

Use `templates/task-grouping-example.md` as a small formatting reference, never as a real project backlog. Preserve the project's established language. Migration between tracker providers changes connections/mappings, not the meaning of category, topic or Task identity.

## Required hierarchy verification

A successful sync, matching counts or a green general gate alone does not prove this naming convention. When update/rework covers Tasks or a user requested this standard, explicitly inspect the hierarchy, perform its local naming/grouping repairs, and run:

```bash
python3 /path/to/skill/scripts/task_naming.py --root . --require --phase 2 --json
```

Without `--phase`, check all known/registered phases. The checker is read-only. `--require` makes a missing registry an error; without a configured contract it reports `not-configured`, not `passed`. Do not present `not-configured` as hierarchy verification. A narrowly scoped reader-document edit can mark Task hierarchy not applicable with a concrete scope reason; a whole-project update/rework cannot silently skip it.

`.project-docs/task-topics.json` owns the reviewed source inventory; start from `templates/task-topics.example.json`, replacing the illustration with actual phase topics, source paths and labels. It is not safe to copy a made-up source plan or fabricate labels merely to satisfy the checker. If the source is unavailable or ambiguous, report the precise missing input, complete independent repairs, and leave the hierarchy work partial. Record the adopted hierarchy requirement in project rules; an explicit user request for this standard establishes its applicability without another blanket confirmation.

The version-1 registry contains `phases` keyed by phase number, each with `topics`. Each topic has `label` (title prefix), `category` (the `##` heading and Work category), `source` (existing project-relative plan file), `source_label` (exact Plan topic metadata), and `disposition`. A deliberate shorter label needs `alias_reason`. Non-active dispositions (`out-of-scope`, `cancelled`, `deferred`, `pending`) need `reason` and `decision` pointing to an actual decision or explicitly pending decision record. Every topic must map to an existing Task, including preserved excluded work; do not create fake implementation work merely to fill coverage.

The checker detects missing category/topic prefixes/provenance, metadata mismatches, duplicate numbers/UIDs, unmapped topics and excluded work counted as done. It normalizes nothing and changes no status. The general docs gate also enforces this contract when the registry exists or config has `"task_naming": {"required": true}`; that setting makes a missing registry fail too. Legacy projects without this contract retain their old gate behavior, so commands must run the explicit required check when the hierarchy is in scope. Do not disable/remove the contract or add warning exceptions to bypass it.

Before reporting completion include an actual old → new title table and a category → topic → Task view, plus the checker result and any pending source decisions. Regenerate affected phase flows/presentations using existing UID groups; do not invent nested-flow support. Local repair and proposed tracker titles must be reported separately from remote writes. Wh clarity and the correctness of the human-reviewed plan inventory remain manual reviews; structural validation cannot establish those meanings.
