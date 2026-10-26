# Advanced analytical charts: multi-panel comparisons

Read when one question needs several coordinated panels: per-step breakdowns, cumulative scaling, baseline normalization or comparisons across environments. This extends [chart selection](presentation-charts.md); it is not a new native `type`. Use native charts as separate panels where possible, or a project-owned custom SVG generator for a composite figure.

## What these references teach

These recipes retain the design lessons from two reviewed examples: a multi-hop baseline/scaling dashboard and a Local-versus-Workbench benchmark dashboard. The original SVGs were removed after review at the owner's request; this guide is self-contained. Their benchmark JSON was not supplied, so the examples do not establish verified measurements. Do not reconstruct missing raw observations from bar geometry or rounded labels.

| Reference | Reusable analytical structure | Checks before adapting |
|---|---|---|
| Multi-hop | One identity/color per option; ordered step contributions; total and baseline ratio; cumulative curve; threshold annotation | Sum all hops; distinguish normalization from Pareto concentration; disclose any scale break; derive threshold crossings |
| Local versus Workbench | Four coordinated panels: median latency, active memory, grouped stacked totals and cumulative curves; environment encoded separately from option | Preserve pair identity; show units and measurement protocol; distinguish single-request median from multi-hop total; identify environment confounders |

Preserve the structure that helps a decision, not every visual choice. A multi-panel figure is useful when panels explain different aspects of the same comparison. Split unrelated questions into separate figures.

## Recipe A: step cost, normalized total and cumulative scaling

**Question:** Which option is cheaper across a fixed sequence, and where is the cost incurred?

Require rows with `option`, `run_id`, `hop`, `latency_ms` and an explicitly selected baseline option. Include workload, sample count, warm/cold state, measurement boundary and environment in provenance. Hops must be unique, ordered and complete within a run; validate missing/duplicate hops and nonnegative finite values. An aggregate row requires a named statistic and its source runs.

1. **Step contribution panel:** stack actual per-hop increments in execution order, with a shared linear zero baseline. Show totals above stacks. More than six hop segments requires a custom renderer: native stacked-bar accepts at most six series. Use ordered shades within an option; if thin segments cannot carry labels, put values in the table rather than overlap text.
2. **Baseline comparison:** show an explicit baseline reference line and ratios or a separate ratio panel. A right axis is acceptable only as the exact conversion of the same latency axis, with `100% = B ms`. It must not represent a second unrelated measure. Do not draw a trend line through unordered option categories; use dots or labels for ratios.
3. **Cumulative panel:** use hop number on x and the cumulative sum on y, with the same option identity across panels. Include endpoint values and a separate per-hop view when investigating growth rates. Cumulative values are not new per-hop measurements.
4. **Threshold:** for each series, calculate the first observed hop whose cumulative value reaches the chosen fraction of that series' final total. Label the denominator. A discrete crossing belongs on an observed point; interpolation requires an explicitly justified model.

For hop costs `d[1]...d[n]`:

```text
C[k] = d[1] + ... + d[k]    # mathematical indices, hops 1 through k
T = C[n]
B = baseline total         # B must be > 0
baseline_percent = 100 * T / B
latency_change_percent = 100 * (T - B) / B
speedup = B / T             # require T > 0; less than 1 means slower
fraction_crossing = min(k where C[k] >= fraction * T)
```

Report a positive reduction as `100 * (B - T) / B` with the words “latency reduction”; do not call a negative percent “faster.” If the baseline/total is zero, show the ratio as undefined rather than infinity or a fabricated percentage. Compute using full precision; round only for display.

**Terminology:** baseline-relative percentages are normalization, not a Pareto chart. Reaching 80% of final latency is an “80% cumulative-time crossing,” not proof of the 80/20 principle. A Pareto concentration panel sorts actual contributors by descending cost and shows cumulative share; it has a different x order from chronological hops. A Pareto frontier requires at least two competing objectives and nondominated alternatives, with direction of preference stated for each.

**Outliers:** prefer an honest full-scale overview plus a clearly labelled detail panel sharing the data, or explicitly labelled facets. Do not compress only one bar while showing shared unbroken ticks. A broken axis must show omitted ranges and consistent transformations for every mark/reference line; a zero-baseline bar without breaks is usually easier to assess.

## Recipe B: paired environment benchmark dashboard

**Question:** How do the same options behave across environments, considering latency, memory and sequential work?

Use rows identified by `option`, `environment`, `run_id`, workload and measurement definition. Separate raw request samples, hop increments and memory observations; record aggregation for every panel. Validate matching coverage before claiming paired comparisons. Missing environment measurements remain missing, not zero.

| Panel | Encoding | Data/interpretation |
|---|---|---|
| Single-request latency | Grouped bars or paired dots | Same statistic (e.g. median), boundary, unit and workload in both environments; do not compare a mean with a median |
| Memory | Grouped bars or paired dots in its own panel | Explicit active/peak/RSS/container accounting and MB versus MiB; never combine memory with latency on unrelated dual axes |
| Sequential total | Grouped stacks by option/environment | Stacks use hop increments; total equals the cumulative endpoint. Do not stack cumulative values |
| Scaling | One cumulative line per option/environment | Color consistently encodes option; dash/marker consistently encodes environment, with direct endpoint labels where possible |

Use the same option order in all four panels. Prefer option color in both environments and dash/pattern/outline for environment; if one environment uses gray bars, retain explicit pair labels so option identity is recoverable. Do not rely on color alone. Keep “lower is better” visible for latency/memory; reverse only when the metric actually requires it.

Compute speedup within a matched option/workload: `local_total / remote_total`, explicitly naming the numerator and denominator. A median-speedup label must use medians, not cumulative totals. “Fastest” needs metric, environment, covered alternatives and uncertainty qualification; a point estimate alone does not establish statistical significance.

Record CPU/memory limits, architecture/emulation, network path/region, runtime versions, concurrency, pool settings, cache state and run count. Differences across environments are observations under those conditions; charts alone do not establish whether architecture, networking or a proxy caused them. Add intervals only from real repeats with a stated method. Show a quality/pass panel only when the source includes actual acceptance results.

## Compose, generate and publish

Create one owner JSON and a reviewed project-owned Python generator. Prefer standard-library SVG for a small deterministic dashboard; use a suitable plotting library when statistical plotting or layout warrants it, then export compatible static SVG. Do not add a dependency merely for panel boxes. Reuse the native renderer for individual panels when its limits and semantics fit. The native `pareto` type is concentration, not Recipe A's normalized totals.

A concrete project spec can use this shape (paths/fields must match actual project owners):

```json
{
  "id": "environment-dashboard",
  "type": "custom",
  "title": "Latency, memory and sequential cost by environment",
  "question": "Which option meets our measured latency and memory constraints?",
  "source": {"path": "project/results/environment-runs.json", "pointer": "/observations"},
  "fields": ["option", "environment", "run_id", "metric", "step", "value", "unit"],
  "unit": "Per panel: ms or MiB, as recorded",
  "asset": "project/results/charts/environment-dashboard.svg",
  "generator": "project/results/build_environment_dashboard.py",
  "reason": "Four coordinated panels preserve option/environment identity across different measures and hop sequences.",
  "limitations": "Describe actual runs, environment differences, missing measurements and uncertainty."
}
```

The generator validates input before writing, derives summaries/labels from the same calculations as plotted marks, and writes an accessible title/description plus source and generator SHA-256 metadata. Follow the custom SVG contract in `presentation-charts.md`: presentation attributes, static primitives and no scripts, styles or external resources. The reviewed examples used inline styles and lacked the required provenance metadata/title; future assets must satisfy this contract rather than copy those limitations. Adding a checksum does not validate their claims or substitute for missing raw data.

Run the generator explicitly, then `sync_presentation.py N` and `--check`. Publish the same sourced chart, rationale and full-data link in Markdown and HTML. For interactive HTML, make each panel a separate accessible figure in a responsive CSS grid; two columns only when labels remain legible, one column on narrow screens. Offer the composite SVG as an export if useful. Avoid one fixed 1200px dashboard shrunk to a phone: preserve readable panel size or reflow panels. Dense legends belong in wrapping HTML or a dedicated multiline row; reserve margins for callouts. Never position a legend/callout over axis labels or data.

## Review gates learned from the examples

- **Reconcile text and numbers:** the Workbench reference memory subtitle says 9.0 MB while its Go bar says 10.6 MB. Resolve against the raw owner; do not choose one by appearance. Generate subtitles, summaries and annotations from shared calculations.
- **Avoid overstating growth:** the multi-hop reference says “exponential,” while the displayed cumulative curve looks approximately linear. A steep line does not establish exponential growth; inspect increments and an appropriate fitted model before naming growth complexity.
- **Do not copy distorted scale breaks or a cramped legend:** the multi-hop reference compresses the large first total and its legend crowds neighboring items. Redesign with full-scale/detail panels and measured text bounds instead of reproducing these defects.
- **Cross-check panels:** every stacked total equals its last cumulative point; ratio labels use the configured baseline; displayed samples/counts and environments agree everywhere; threshold callouts are computed, not hand-positioned estimates.
- **Verify geometry in a real browser:** text bounding boxes fit their panel/legend, ticks do not collide, callouts remain outside marks, thin segments retain table access, contrast supports labels. Inspect 390/768/1280px and print/export separately; DOM overflow alone cannot detect SVG text overlaps.
- **Preserve uncertainty:** no raw source means “design reference only.” Do not report the supplied benchmarks as rerun, statistically verified or accepted project evidence.
