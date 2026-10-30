# Complete result updates include the visuals

Read for “update all reports”, new/rerun results, new numeric comparison sections or changed implementation/environment coverage. A matching table and a generic green gate do not prove visual completeness.

## Authorized scope

An instruction to update result reports includes creating an appropriate chart for a new result that has no chart, regenerating affected existing charts, and embedding the result in the paired Markdown/HTML and relevant phase presentation. Do not ask a second blanket “Should I create the chart?” question for that already authorized work. Ask only for a real missing source, acceptance or comparability decision, and continue independent repairs.

Choose a chart for the question using `presentation-charts.md` and `advanced-chart-recipes.md`. A single fact or categorical environment specification may belong in a table; it does not need a decorative image. Record the specific table-only rationale and its reviewed decision/policy instead of silently skipping a meaningful multi-option comparison. Do not create charts with invented data merely to satisfy a visual count.

## Result-to-visual coverage inventory

Before editing, list each affected report section, its actual source run(s), metrics/methods, existing graphic/generator, paired HTML location and phase placement. Cover new sections as well as old ones. Use source ownership and stable section IDs; a search for an old number or a common “1.11” alone cannot distinguish a section from a Task number.

For each changed result select an explicit action:

- Regenerate an affected existing chart from its real source/generator.
- Create a chart and durable project-owned generator for a new result or newly supported option/environment.
- Preserve a historical chart whose documented source/run is unchanged, and separately add the graphic required by the new comparison. An old correctly sourced image in section 1.8 does not cover a new section 1.11.
- Keep a table-only presentation only with a concrete reviewed reason/decision, not a general warning exemption or “no time.”

Retain run identifiers, source checksums, dates and limitations. Source data should be immutable/versioned for each experiment; do not overwrite a run and then silently reuse its earlier values. If an older source was already overwritten, label the missing evidence and limitation; do not reconstruct supposedly measured samples from a chart, chat log or printed summary. Do not globally replace old values belonging to another valid run.

A generator prototyped in a scratchpad must be retained as a reviewed project-owned script before handoff. It must read the actual raw files and compute chart values/captions from those same inputs. A temporary “replace exact text” script is not a reproducible chart pipeline. For multi-source plots, retain provenance/checksums for every input; a derived chart-data JSON may combine them only with explicit origin/context, no silent mixing of runs.

## Compare only comparable measures

Record metric definition/unit, sample count, workload, corpus, resource limits, platform, run date, warm/cold state and authentication/permission context when relevant. A median from one request and a median from ten requests are not a fair shared performance ranking. Exclude that ranking, split panels with explicit method limits, or leave the unresolved comparison pending; the task is not blocked from plotting other genuinely comparable measures such as a defined RAM observation or a matching sequential workload.

Use separate panels for different units. Local and remote runs need consistent series identities and explicit environment differences. Model/LLM-judge results, synthetic corpora and mock permission tests retain their limits. A service-account denial followed by a successful personal-identity run does not prove service-account access. Keep logical options versus runtime/language variants consistent with the glossary; do not silently rename architectures merely because there are more implementation columns.

## Embed and review in the same pass

Write the chart asset, source-backed table and caption together. The new figure must actually appear in its own Markdown report section, paired HTML container and each affected phase slide; a text link to an image elsewhere is not an embedded visual. Keep meaningful source tables and make the chart's question, encoding, units, takeaway and limitations readable. Preserve existing useful charts; their presence elsewhere does not cover the new data.

For an HTML `<img>`, point to the registered asset. For an inline SVG, stamp the actual `<svg>` element with `data-asset-sha256` matching its exported source asset, so the coverage checker can trace it. That stamp establishes provenance, not numerical correctness or safety; follow the existing static SVG contract and inspect the visual. Add stable IDs to result/slide containers when needed and repair the section index/slide numbering without duplicate folios.

Inspect desktop and mobile rendering for the changed report/slide: chart appears, labels/legend/axes fit, source links work, units are correct and scrolling stays inside the container. A script-only source comparison is not visual QA. If browser access is unavailable, finish generated outputs and structural checks but clearly report visual QA pending rather than “all presentations verified.” Never use company-account access merely to improve this generic skill from a pasted incident.

## Deterministic coverage check

Maintain `.project-docs/report-visuals.json` from the actual coverage inventory; start from `templates/report-visuals.example.json`, replacing illustrative paths/checksums with real values. The agent writes this metadata from the files it generated; the user does not need to hand-fill hashes. The registry links a Markdown report/section to its paired HTML container, every input source/checksum, chart asset/checksum, permanent generator/checksum and phase presentation placements. It also records the reader question and real limitations.

```bash
python3 /path/to/skill/scripts/report_visuals.py --root . --require --json
python3 /path/to/skill/scripts/report_visuals.py --root . --require --report project/results/test-results.md --json
```

The read-only checker detects unregistered numeric-table sections, absent/old-source graphics, changed source/generator/asset bytes, missing images in Markdown/paired HTML and missing declared presentation images. Default scope is direct `project/results/*.md` plus all registered reports; explicitly add custom owners (e.g. a project-owned `reports/` folder) or pass `--report` for the affected files. Nested immutable run bundles are not silently scanned/rebuilt as current aggregate reports. Inventory all affected owners manually; numeric-table detection is a heuristic and cannot identify every result in prose or a picture-only section, so register those sections explicitly too.

Use exact Markdown heading text and a stable `html_id` on the corresponding containing HTML section/div, not just a heading element that closes before its image. `presentations` lists the affected phase HTML paths/container IDs; a known phase/Task result cannot silently omit them. A truly standalone result can use an empty list plus a concrete `no_presentation_reason`. `kind: table-only` needs a substantive `reason` and actual `decision` file and is still paired with HTML. These records require semantic review: a policy file existing does not prove that a human approved an exception or that the chart is correct.

The normal docs gate enforces the coverage registry when present, or when config sets `"report_visuals": {"required": true}`. Missing/unregistered result sections then fail as ERRORs. Existing unconfigured projects retain their legacy gate behavior, so update/rework must call the explicit `--require` check whenever numeric result reports are in scope. `not-configured` is not a pass; `not-applicable` means no candidates were found in the declared scope and needs a scope explanation. Do not remove the contract, invent inputs, or add accepted-warning entries to hide missing visuals.

## Finish only after the complete pass

Use router A for new/rerun results. Run the existing syncs/gate plus visual coverage check only after tables, figures, captions, phase views, indexes and persistent generators are updated. Do not finish the flow log midway and then call the full work complete. Preserve the actual exit status of every check: use subprocess return codes or pipefail where supported, not a trailing `tail`, `grep`, or `$?` from another command as proof of a passing gate. Prefer `rg` with quoted patterns over shell-expanded include globs.

The handoff states which chart was created/regenerated/retained/table-only for each changed result, the source run(s), where it is embedded, generation/check commands, actual visual inspection and unresolved limits. “Updated all reports” is justified only by that coverage, not by matched counts or a generic green gate. Missing evidence/visual QA leaves the corresponding portion explicitly partial.
