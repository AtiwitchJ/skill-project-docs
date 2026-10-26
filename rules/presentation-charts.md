# Select and customize charts for the audience's question

Read this when a phase needs measured evidence or a custom visual. Use `templates/presentation.md` for slide structure and QA. Workflow status is a **flow**, not a measurement chart. Task counts do not estimate effort or elapsed time.

## Choose the encoding before the appearance

| Reader's question | `intent` → automatic type | Data required | Interpretation and limits |
|---|---|---|---|
| Which category is larger/smaller? | `comparison` → `bar` | unique category + finite numeric value | Aligned lengths, zero baseline; horizontal bars allow longer labels |
| How does a measure change across time or ordered runs? | `trend` → `line` | strictly increasing numeric/date x + numeric y | Connection implies order; do not connect arbitrary methods/categories |
| Are two measures associated? | `relationship` → `scatter` | numeric x/y observations | Show association, not causation; inspect sample size and confounders |
| How do parts contribute to each total? | `composition` → `stacked-bar` | category + 1–6 nonnegative numeric series in one unit | Absolute totals, not automatically percentages; middle segments are hard to compare |
| Where are patterns across two categorical dimensions? | `matrix` → `heatmap` | unique x/y cells + numeric value | Show scale and exact values; missing cells are explicitly missing, not zero |
| How do series compare within categories? | `grouped-comparison` → `grouped-bar` | category + 1–6 series in one unit | Common zero baseline |
| How do several series change? | `series-trend` → `multi-line` | ordered x + 1–6 series | No interpolation of missing observations |
| How does volume change? | `volume` → `area` | ordered x + nonnegative y | Zero baseline; not accumulated totals |
| How are observations distributed? | `distribution` → `histogram` | raw `value`, optional `bins` | Explicit equal-width bins; shape depends on binning |
| How do distributions differ? | `spread` → `box` | group `x` + raw `y` | Linear quartiles, Tukey 1.5-IQR whiskers and outliers; not confidence intervals |
| What fraction falls below a value? | `cumulative-distribution` → `ecdf` | raw `value` | Observed cumulative fraction; no fitted distribution |
| What intervals were measured? | `uncertainty` → `range` | category `x`, `low`, `high`, optional `value` | Describe the interval's actual statistical meaning |
| What changed within matched cases? | `paired-comparison` → `dumbbell` | category `x`, `before`, `after` | Preserve pairing |
| What explains a change in total? | `contribution` → `waterfall` | category `x`, signed `y`, numeric `start`, optional `end` | Contributions must reconcile with end |
| When is work planned? | `schedule` → `timeline` | category `x`, `start_field`, `end_field` | Supplied numbers or ISO dates; no inferred dependencies |
| Which categories contribute most? | `concentration` → `pareto` | category `x`, nonnegative `y` | Descending bars and separately labelled cumulative share |

All 16 families have deterministic native SVG renderers. See [the English gallery](../examples/chart-gallery/gallery.html) and its [reproducible specs](../examples/chart-gallery/chart-specs.json). Use a project-owned custom SVG when the question needs another encoding. Pie/donut, radar, gauges, 3D and decorative animation are not defaults. More available chart types does not justify filling missing dimensions with invented data.

## One source, two outputs

The optional owner spec is `.project-docs/presentations/phase-N.json`. It owns step grouping, chart choice and written interpretation, never copied measurement values or status. Source JSON remains the measurement owner.

```json
{
  "version": 1,
  "flow": {
    "steps": [
      {"id": "prepare", "label": "Prepare the source", "tasks": ["task-stable-uid-1", "task-stable-uid-2"]},
      {"id": "verify", "label": "Verify the result", "tasks": ["1.3"]}
    ]
  },
  "charts": [
    {
      "id": "method-latency",
      "title": "Compare latency by method",
      "question": "Which method is faster on the representative workload?",
      "type": "auto",
      "intent": "comparison",
      "source": {"path": "project/results/benchmark.json", "pointer": "/measurements"},
      "x": "method",
      "y": "latency_ms",
      "x_label": "Method",
      "y_label": "Latency",
      "unit": "ms",
      "color": "#17665c",
      "takeaway": "Author-written interpretation, only after checking the actual values.",
      "annotations": ["State any relevant sample or environment caveat."],
      "limitations": "Name real/synthetic data, run/sample count, run date, environment and who checked it."
    }
  ]
}
```

The selected array must contain row objects, e.g. `{"method":"A","latency_ms":120}`. The example number explains the format; it is not benchmark evidence. `pointer` follows JSON Pointer escaping (`~0`, `~1`). All paths are project-relative and must remain inside the project, including symlink resolution.

Flow defaults to one step per Task in file order. Explicit groups must cover each task exactly once; use stable Task UIDs when available, or unique task numbers. A group's state is done only when all its Task headers are done, blocked when any is blocked, in progress when any is active/partly completed, otherwise not started. Several steps may be active together. The displayed order is the planned route, not an inferred dependency graph or a critical-path calculation.

Run from the documented project's root:

```bash
python3 /path/to/skill/scripts/sync_presentation.py 1
python3 /path/to/skill/scripts/sync_presentation.py --all
python3 /path/to/skill/scripts/sync_presentation.py --all --check
```

Sync updates `tasks.md` AUTO flow/chart blocks, `presentation.html` AUTO blocks and inline SVGs, `phase-flow.svg`, and chart SVG assets. It leaves manual narrative intact. Both formats include chart rationale, source path/pointer/checksum, limitations, and source-value tables (first 100 rows, with the full JSON linked). The HTML stays usable offline, without a CDN chart library; Markdown shows SVG plus textual status and data tables. On small screens the flow uses a readable step list and charts scroll **inside** their container.

No chart spec means an explicit no-results state, not invented measurements. Hand edits to generated assets, changed source files, stale custom generators and mismatched MD/HTML are rejected by `--check` and the docs gate. Native renderers reject missing/NaN/infinite values and booleans instead of substituting zero. They reject ambiguous duplicate categories/cells and unordered line data. Large category sets need an explicit aggregation or a custom view, never silent truncation.

## Advanced composite charts

For multi-hop breakdowns, baseline normalization, cumulative thresholds or Local/cloud benchmark dashboards following the reviewed dashboard patterns, read [advanced chart recipes](advanced-chart-recipes.md). These are custom compositions using the existing provenance contract, not additional native renderer types.

## Custom charts that fit the work

Start from `templates/paired-chart-example.py` for a paired comparison; adapt the generator to the actual reader question. A custom spec uses `type: custom`, `asset`, `generator`, `reason`, `fields` and the same `source`, `question`, `unit`, `limitations` contract. Both the SVG and generator must exist in the project. Generators are **not executed automatically** from a JSON spec; review and run the project-owned generator explicitly.

The source SVG must have a viewBox, accessible title, and these metadata elements:

```xml
<metadata id="project-docs-source-sha256">SHA256_OF_WHOLE_SOURCE_JSON</metadata>
<metadata id="project-docs-generator-sha256">SHA256_OF_GENERATOR_FILE</metadata>
```

The paired example writes them automatically. A data or generator change requires regeneration before sync. Embedded copies namespace IDs and remove internal build metadata; the caption retains source provenance. Use static SVG primitives and presentation attributes; scripts, style tags/attributes, external resources, entities, images, use references and animations are rejected. Flatten unsupported SVG constructs when exporting from another plotting tool. Checksums establish build freshness, not the truth of an author's interpretation: inspect the encoding against the source table.

For distributions and uncertainty, use established plotting tools when appropriate, then produce a compatible static SVG. Do not make a custom chart merely to decorate a single number. A table or a clearly labelled statement is often better for very small datasets.

## Readability, scale and failure states

Keep chart text at a readable size: charts retain a 960px canvas and scroll inside a keyboard-focusable container with a visible hint. Do not shrink labels to fit a phone. Phase flows switch to vertical steps below 1000px; failure lifecycles use vertical cards on mobile. Keep page width within the viewport, wrap long titles/paths and retain visible focus. Print exposes all content.

Native category views reject oversized category sets rather than silently dropping data. Test summaries explicitly label top-N/Other aggregations; underlying JSON retains every case. Histogram/box/ECDF accept up to 200,000 raw observations; other extended types accept up to 5,000 rows with additional category limits. Choose explicit aggregation or a justified custom chart beyond those limits. Test-report inventories use search and 50-record pagination; source previews show 100 rows with a full-data link. A report chart-rendering failure shows an error while preserving case outcomes, tracebacks and raw data; the runner returns nonzero. Invalid phase specs fail sync rather than publishing misleading output.

Verify desktop, tablet and phone layouts, long labels, empty/all-skipped results, unknown data, many cases and chart errors. Check screenshot readability as well as DOM overflow; no page-level horizontal scrolling. Source tables may scroll in their own containers.
