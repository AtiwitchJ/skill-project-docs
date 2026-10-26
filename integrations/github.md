# GitHub Issues and pull requests

Configure `provider: github`, `repository: owner/repo`, and a [transport](providers.md). Direct API authentication uses `token_env`; the default host is `https://api.github.com`.

Snapshots distinguish `work_item` (Issue) from `change_request` (PR), even when the numbers coincide. Issue status uses open/closed; `state_reason: not_planned` requires explicit handling rather than completion. Pull details are read to retain merge metadata. A merged PR is supporting evidence, never an automatic Task completion signal.

Direct API migration creates Issues, comments, labels/assignees, state changes and native sub-issue relationships. Parent reads preserve same-repository parent numbers; cross-repository parents are reported as outside the migration scope. Schema reads discover existing labels and assignable users. This adapter does not advertise native attachment upload: use a capable MCP/CLI bridge, or explicitly accept archived-only files. Do not claim files were copied through an unavailable API.

Public embedded attachment URLs can be downloaded without credentials. Private GitHub web attachments may require a capable bridge; the adapter does not forward an API token to the GitHub web host or manufacture an empty file when access fails.

GitHub account roles matter: a token able to create Issues or comments can change that repository's work records. Use a token limited to the configured repository; normal check/plan commands never execute create/update operations. `doctor` verifies reads; it reports writes as unverified until an actual authorized write.

References: [Issues API](https://docs.github.com/en/rest/issues/issues), [Pull requests API](https://docs.github.com/en/rest/pulls/pulls), [sub-issues API](https://docs.github.com/en/rest/issues/sub-issues). See [Actions](github-actions.md) for test artifacts and [migration](migration.md) for cross-system copies.
