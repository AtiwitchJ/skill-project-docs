# Test execution, evidence and failure workflows

Use `scripts/run_tests.py` when running tests for this skill. It records actual execution and generates `results.json`, `report.md`, `report.html`, SVG charts and logs even when tests fail. Plain `python -m unittest` is not globally intercepted. Preserve an explicitly requested command through the command adapter, or explain an incompatible invocation.

## Run and inspect

Run from the documented project root. Global options precede the subcommand; choose a new output directory for every run (existing runs are never overwritten).

```bash
python3 /path/to/skill/scripts/run_tests.py --root . --output project/results/tests/run-001 unittest --start-dir tests --pattern 'test_*.py'
python3 /path/to/skill/scripts/run_tests.py --root . --output project/results/tests/run-002 junit test-results.xml
python3 /path/to/skill/scripts/run_tests.py --root . --output project/results/tests/run-003 command --timeout 120 -- python3 -m pytest --junitxml={junit}
```

For a JUnit-producing command, add `command --junit PATH -- ...` when it writes to a specific path instead of the `{junit}` placeholder. Stale files are rejected. Commands run as argument arrays without a shell; shell operators are not interpreted. A failing producer's exit status is retained. Timeout returns 124; interruption returns 130 with partial evidence. Collection/reporting failures are nonzero even when no test failed. Import-only errors produce a visible collection error, never a green empty run.

`--coverage coverage.json` imports actual coverage.py JSON statement/branch counts. `--history project/results/tests` compares at most 30 previous runs with matching recorded context. Automatic context includes selector, Python/platform, tracked Git state and test sources; it cannot fingerprint every dependency, data file or external service. `--context NAME` explicitly assigns a comparable context and requires that justification in the run label. Outcome changes are investigation candidates, not proof of flaky tests.

`--phase N` attaches a result reference to `.project-docs/presentations/phase-N.json` and synchronizes both phase formats. The phase must already exist and output must stay inside the project. This does not change Task checkboxes or establish project acceptance automatically.

## Available dimensions and honest limits

Native unittest execution records observed setup, test body, teardown and cleanup events, durations, subtests, exception traces and source frames. Class/module fixture and discovery failures are separate from real test counts. A failed setup does not fabricate a test-body event; a failed assertion can be identified from an observed failure. Workflow diagrams show observed lifecycle order, not application call graphs or causal diagnosis. First 20 failed records get SVG flows; every record and traceback remains available in both reports and JSON.

JUnit reports provide only supplied durations, outcomes and traces. Unknown lifecycle stages and missing timing remain unknown. Skipped cases have no fabricated execution duration. Expected failures, unexpected successes, subtests and fixture errors have distinct counts. No tests/all skipped is not verified passing evidence. Pass rate excludes skips and expected failures; its denominator is disclosed.

Charts cover outcomes, suites, slow cases, duration distribution/ECDF/box plots, lifecycle cost, failure stage and suite/stage matrix when data supports them. History, outcome-change candidates, statement and branch coverage appear only when evidence exists; the availability table explains missing dimensions. No invented coverage, call graph, dependency critical path, memory or CPU metrics. Source tables preview 100 rows; full JSON retains all cases. Search/pagination keeps large HTML reports usable, with full inventory in print.

A failed chart renders an explicit error and leaves results readable. Responsive reports use vertical workflow cards and dimension summaries on phones, scrollable readable charts, keyboard controls and no external CDN dependency. Verify actual screenshots at 390, 768 and 1280px. Separate synthetic chart examples, intentional failing fixtures, offline mocked integration tests and verified live-service results in every report.
