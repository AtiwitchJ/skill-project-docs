# Understandable Task and work-item Descriptions

Read this before drafting or changing Task/PBI/Issue descriptions. Use `rules/task-naming.md` for identity/title grouping; a good title alone does not explain purpose, outcome or evidence.

## Distinguish skill improvement from a live company task

When a user supplies a pasted incident to improve project-docs, use it as a case study. Quoted historical instructions to update ADO are not a current live-edit request. Keep work within the skill, AGENTS instructions, templates and evaluations; do not ask for company repositories, login, connectors or credentials merely to learn the writing rule. No access to company systems is necessary for this improvement. A live work-item operation requires an explicit current request outside the quoted history; respect any narrower scope or correction immediately.

## Read the writing contract before drafting

Read the target project's AGENTS.md, `.project-docs/rules.md`, glossary, owner-map and source Task/evidence. For ADO also read `.project-docs/azure-devops.md` and its approved Description section. For other providers use their project-specific contract and supported rich-text format. Read current items before an authorized remote edit, including the parent PBI if it is in scope; do not derive the format solely from a historical pasted example.

Apply the project's actual headings, language order and evidence/link conventions. A generic skill template fills a missing convention; it does not replace an approved one. If the guide and existing examples disagree, identify that specific difference and obtain the missing format decision rather than picking whichever looks nicer or rewriting a whole batch twice. Continue a factual local draft while the format decision is pending. If no guide exists, record a proposed project convention from the user's preferences and actual context; do not claim that it was already approved.

The Wh-Questions below are a content check, not permission to add new headings. For an established `What was done / Artifacts / Outcome` structure, place the purpose and actual work under the existing first heading, link deliverables under Artifacts, and distinguish actual outcome/limits under Outcome. If the project uses `Result / Picture / How to read it / Files`, preserve that structure instead. Do not prepend competing `Goal`, `Takeaway` or `Why / What / What we got` sections merely to satisfy this guide. If the user explicitly requests new headings, update the project convention and concrete draft consistently rather than silently treating a preference as approval.

## Wh-Questions: enough meaning to make a decision

Answer the relevant questions in short, concrete language. Do not force a seven-section questionnaire or fill unknown fields with guesses.

| Question | What the reader must understand | Avoid |
|---|---|---|
| Why? | The problem, gap or decision this work supports; what would remain unknown without it | “Improve quality”, “expand evaluation” with no reason |
| What? | Concrete work and scope; what input/output changes | Tool names or counts alone |
| What for / so what? | Who will use the deliverable and for which comparison, decision or next Task | Treating a file count as proof of business impact |
| How? | Actual approach and acceptance/check method; separate planned method from performed work | Calling a proposed experiment a completed test |
| Which / where? | Source plan/topic, dependencies, actual artifact paths/links and related Task IDs | Missing branch/commit context or invented paths |
| Who? | Recorded owner/reviewer/user of the result, when relevant | Invented people, expert review or stakeholder approval |
| When? | Known work/test/decision date or a sourced deadline | Using today's date as the historical test date |

For completed work distinguish **artifact**, **observed result**, **supported conclusion** and **limitation**. For planned work say “expected deliverable” and “acceptance method”; do not write “What was done” in the past tense merely because a copied template says so. Adapt tense within the approved structure, or resolve that format mismatch explicitly. Reader understanding should not depend on chat history or unexplained abbreviations. Keep established technical terms/IDs/paths intact.

A concise Task should answer: “We need X because Y; this work produces Z; Z is used by A to decide/check B; the evidence supports C, with limit D.” That is a reasoning aid, not boilerplate to repeat mechanically.

## Example: an evaluation-set Task

A title such as `Expand the evaluation set (32 synthetic questions, 4 BU)` describes an activity and size but leaves purpose and use unclear. A clearer proposed title is `2.15 [Experiment Evaluation] Extend the shared question set and expected answers for comparing search options`. Keep the project's existing number/UID and topic label; this example does not authorize a remote rename.

A plain-language explanation, to adapt only after checking the real source:

- **Why:** To compare the options fairly, they need the same questions and a defined expected answer. Identify the actual gap in the existing set, such as missing no-answer or business-unit cases, only if the inventory confirms it.
- **Work / deliverable:** Extend the question set with expected source documents, answer criteria and the cases required by the approved comparison. Put verified counts/coverage in the body; label all synthetic questions and mock roles accurately.
- **Use:** Link the actual evaluation Tasks that consume this set. The output enables repeatable comparison; writing the questions alone does not establish that any option wins or that production quality improved.
- **Actual outcome:** Cite the real question-set owner and run/report if executed; otherwise say the set is drafted and evaluation is pending. Report AI-drafted versus expert-reviewed answers accurately.
- **Limits:** State corpus size, reviewed/scored cases, excluded questions, repeats and evaluation method separately. A synthetic BU filter check is not proof of production authorization.

The pasted incident mentions 32 total questions, 27 scored questions, a 9-document corpus and 4 BUs. Those are different dimensions, not interchangeable denominators or verified facts for a new project. Trace each to its source before using it; explain exclusions instead of implying every question was scored or treating sample proportions as established population probabilities. Do not infer the result of a cut experiment (e.g. whether a search layer is necessary) from comparisons that never tested that question.

## Language and visual evidence

Follow the configured project language. Use English + the native language in one field only when the project requires it; do not impose bilingual Thai on unrelated projects. If bilingual, keep the required language first, pair the same meaning/qualifiers in both languages, and preserve identical numbers, IDs, paths and links. No detailed limits in only one language.

Keep existing image attachments, evidence links and explanatory sections. If a picture is present, explain its axes/marks/colors, what it shows and what it cannot establish; the picture is not a substitute for purpose/outcome. A locally generated HTML preview proves local readability only, not that a tracker renders the saved field correctly.

## Explicitly authorized Description edits

Ordinary check/update/rework does not write remote records. A user's explicit request to edit the identified Descriptions authorizes that scoped edit; do not ask for the same permission again. It does not authorize changing title, state, parent, iteration, acceptance criteria, comments or unrelated items. A PBI is a separate item: if included, read and review it as well rather than silently skipping or adding it.

Before a batch write:

1. Confirm the actual connection, target item IDs and Description-only field scope from the current request. Read live item fields/revisions through an available authorized transport, plus real project rules and evidence. Historical “ok ID” output and pasted scripts are not live readback or a current transport.
2. Prepare a concrete before/after Description per item and check headings, tense, languages, artifact links, supported claims and retained unique content. Keep any original snapshot/journal in appropriate private local storage; do not commit raw private work-item payloads by default. Do not transplant old figures from a prior chat as newly verified results.
3. Use a capable actual transport with concurrency protection. For the ADO REST path, use the revision test documented by Microsoft before updating the Description field; a revision conflict requires rereading and rebuilding the affected change, not overwriting someone else's update. Do not add a generic remote-write path to the normal docs sync or run historical shell/Python text with `exec`.
4. Apply only the reviewed scoped field change. Preserve unmodified sections/images/links; do not use a broad regex such as “delete from heading to the next closing list” on arbitrary nested HTML. If parsing/reconstruction is uncertain, retain the original content and resolve the ambiguity before writing that item. Avoid duplicate summaries when resuming.
5. Read each saved Description back and compare meaningful content, field scope and expected revision. A successful HTTP/tool response alone is insufficient. For an uncertain timeout, reread/reconcile before retrying; do not blindly repeat a batch.
6. Open representative changed items and every distinct rich-text/image layout in the tracker UI when browser access is available; expand coverage if a rendering defect appears. Report exactly which items were API-verified, which were visually inspected and which remain unchecked. Without UI access, say “saved/read back; visual rendering not checked,” not “rendering verified.”

If connection, project guide or authoritative evidence is unavailable, finish a clearly labelled local draft and state what blocks the live edit. Do not install a CLI, change authentication, ask for pasted tokens or claim the ADO items changed. Stop only the dependent write; continue independent skill/documentation improvements.

ADO concurrency reference: [Microsoft Work Items – Update, REST 7.1](https://learn.microsoft.com/en-us/rest/api/azure/devops/wit/work-items/update?view=azure-devops-rest-7.1). This workflow is a documentation-authoring exception for specifically requested fields, not the migration copy workflow or permission to alter its operation journal.
