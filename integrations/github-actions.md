# GitHub Actions evidence

Configure `provider: github-actions` (or reuse a GitHub connection), `repository`, and a [transport](providers.md). This source is evidence, never the primary work tracker or a migration destination.

```bash
python3 /path/to/skill/scripts/integrations.py evidence test-results 12345 --uid task-example --commit FULL_COMMIT_SHA --attempt 1 --member results/junit.xml
```

The adapter reads the artifact and the specified run attempt. With no `--attempt`, it tries the latest attempt and refuses an artifact that cannot be attributed to it. Attribution checks artifact creation time against the attempt interval and matches its commit. Bridges must supply the equivalent checks before setting `attempt_verified: true`.

The command refuses expired artifacts, unsuccessful workflows and mismatched commits. It downloads the ZIP, extracts only the named safe member (no archive-wide extraction), and records run ID, attempt, artifact ID, commit, archive/result SHA-256 and source file path. Results must be JUnit XML with actual test cases, or explicit JSON:

```json
{"status":"passed","tests":12,"failures":0,"errors":0}
```

Downloading bytes is not a passing test. Failed test results remain failed evidence. `check` checks result existence/checksum and provenance; none of these commands automatically marks a Task complete. Parsing a supported passing result does not establish requirements coverage, which remains a project decision.

An Actions read token can download artifacts, which may contain private build output. Keep repository access limited. Signed download redirects receive no provider credentials. Result extraction rejects traversal, symlinks and oversized result members.

Reference: [Actions artifacts API](https://docs.github.com/en/rest/actions/artifacts).
