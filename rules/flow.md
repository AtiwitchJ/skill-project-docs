# Flow rules: Andon, waste, WIP, %C&A

## Andon and PDCA

Andon means stopping the line the moment a defect appears. Signals here: a gate ERROR, a value with no owner, or two owner files that disagree.
1. **Plan:** stop editing derived files; write what is wrong and which file owns it.
2. **Do:** fix the owner. If you can't (waiting for a decision or access), log an issue or a pending item in memory-bank.
3. **Check:** rerun the gate; no ERROR caused by this task.
4. **Act:** if it can recur, prevent it at the source: add the old value to `.project-docs/stale-patterns.json`, add a check to `check_docs.py`, or fix this skill.

When two owners disagree (e.g. test-results and TASKS report different results), don't pick a side. Report both with evidence and let the project lead decide.

## Waste to remove

| Waste | Here | Prevented by |
|---|---|---|
| Inventory | The same number typed into several files, then updated in some | owner-map, AUTO blocks, links instead of copies |
| Defect | Broken links, bad checklist markers, stale values, raw backticks | `check_docs.py`, `.project-docs/stale-patterns.json` |
| Rework | The user points out an error after handover | Gate before handover; `flow_log.py rework` to see trends |
| Motion | Editing before reading the rules, then redoing it | Steps 1–3 before touching files |
| Over-processing | Tables, slides or sections nobody uses | Ask what decision the reader must make |

## WIP limit

Each phase should have at most `wip_limit_per_phase` (in `.project-docs/flow-policy.json`, set to 1) tasks marked `[/]`. Many open tasks make status stale fast and none of them close. When the gate warns about WIP:
- Close tasks that are really done (`[x]` with evidence).
- Tasks waiting on someone else (access, data, a decision) become `[!]` with an Issue ID; they aren't in progress.
- If exceeding the limit is necessary, record the reason in `accepted_warnings`. Never raise the limit to silence the warning.

## %C&A (Percent Complete & Accurate)

The share of docs tasks handed over without rework.
- A task counts as C&A when its first `flow_log.py finish` has no ERROR **and** nobody finds a defect later.
- When anyone points out an error in delivered work, run `flow_log.py rework <id> "<what was wrong>"` before fixing, however small. It shows which step leaks.
- `flow_log.py report` shows totals. Repeated rework at the same spot → do the Act step.
