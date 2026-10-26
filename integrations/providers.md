# Configured providers and transports

Use this guide for provider selection, snapshots, mappings, and bridge setup. Use [migration.md](migration.md) only for an explicitly requested migration. Ordinary docs work never creates or updates remote items.

## Project configuration

Add connections to `.project-docs/config.json`. Exactly one tracker may be primary; other tracker connections can remain for historical references. PR/MR and Actions connections can be used as evidence alongside the primary tracker.

```json
{
  "integrations": {
    "primary": "team-jira",
    "connections": {
      "team-jira": {
        "provider": "jira",
        "base_url": "https://example.atlassian.net",
        "project": "DOC",
        "transport": "auto",
        "token_env": "PROJECT_DOCS_JIRA_TOKEN",
        "username_env": "PROJECT_DOCS_JIRA_EMAIL",
        "states": {"To Do": "todo", "In Progress": "doing", "Done": "done"}
      },
      "code": {
        "provider": "github",
        "repository": "example/project",
        "transport": "api",
        "token_env": "PROJECT_DOCS_GITHUB_TOKEN"
      },
      "test-results": {
        "provider": "github-actions",
        "repository": "example/project",
        "transport": "api",
        "token_env": "PROJECT_DOCS_GITHUB_TOKEN"
      }
    }
  }
}
```

Provider names: `azure-devops`, `github`, `jira`, `linear`, `gitlab`, `github-actions`. Normalized states: `todo`, `doing`, `blocked`, `done`; all other states are `unknown` until explicitly mapped. A cancelled GitHub issue is not treated as completed. External IDs are scoped by connection **and kind**; an Issue and MR can have the same number.

| Provider | Required scope fields | Specific guide |
|---|---|---|
| Azure DevOps Services | `organization`, `project` | [Azure DevOps](azure-devops.md) |
| GitHub Issues/PRs | `repository` as `owner/repo` | [GitHub](github.md) |
| Jira Cloud | `base_url`, `project` key | [Jira](jira.md) |
| Linear | `team` ID | [Linear](linear.md) |
| GitLab | `project` ID or namespace/path; optional `base_url` | [GitLab](gitlab.md) |
| GitHub Actions | `repository` | [Actions evidence](github-actions.md) |

Provider API support targets Azure DevOps Services REST 7.1, GitHub REST, Jira Cloud REST v3, Linear GraphQL, and GitLab REST v4. Server-specific workflows/required custom fields can prevent writes and must be resolved rather than guessed. Direct API requests require HTTPS. Authentication uses environment references, not tokens committed to JSON. Jira API-token authentication also needs `username_env`; an OAuth deployment may use a suitable configured gateway base URL and bearer token.

External asset URLs are downloaded without provider credentials. Redirects are validated and private-address asset destinations are rejected unless their hostname is explicitly trusted in `asset_hosts` on that connection. Provider API hosts are explicitly configured separately. Migration locking currently requires a POSIX platform (macOS/Linux).

## Commands

Run from the documented project, not the skill repository. Alternatively place `--root /absolute/project` before the subcommand.

```bash
python3 /path/to/skill/scripts/integrations.py doctor --json
python3 /path/to/skill/scripts/integrations.py fetch team-jira --full
python3 /path/to/skill/scripts/integrations.py import team-jira /private/export.json --coverage partial
python3 /path/to/skill/scripts/integrations.py check --json
python3 /path/to/skill/scripts/integrations.py upgrade
```

`doctor` performs reads only. It reports transport readiness, discovered capabilities and missing capabilities; successfully reading a project does not prove write permission. `fetch` saves a normalized snapshot; `--full` also fetches paginated comments/attachments for migration. `import` never contacts a provider. Use `--coverage complete` only for an actual complete project inventory, including all pages. A missing record in a partial snapshot is **not observed**, not deleted.

`check` reads local snapshots and never changes task markers or contacts providers. Exit codes: 0 clean, 1 findings/not ready, 2 invalid input/operation failure/pending bridge work. Snapshots older than `stale_days` (default 7) are reported. `check --connection NAME` selects a secondary connection explicitly.

`upgrade` assigns a permanent `**Task UID:** task-...` under each Task heading. It retains headings, marks and legacy ADO lines, adds or reuses the matching ADO connection without overriding an explicitly selected primary tracker, and translates ADO mappings without replacing the old snapshot. Run it once before migrating an existing project; repeated runs preserve UIDs.

The mapping owner is `.project-docs/work-items.json`:

```json
{
  "version": 1,
  "tasks": {
    "task-example": {
      "refs": [
        {"connection": "team-jira", "kind": "work_item", "id": "10001"},
        {"connection": "code", "kind": "change_request", "id": "42"}
      ],
      "evidence": []
    }
  },
  "phases": {
    "phase-1": [{"connection": "team-jira", "kind": "work_item", "id": "10000"}]
  }
}
```

Never regenerate a UID when a heading is renamed or a task moves to another phase. Mapping is many-to-many. `tasks.md` owns status; snapshots own remote-side values. A closed Issue or merged PR never closes a Task automatically. Completed tasks need an `**Evidence:**` reference in their task body or valid recorded evidence.

## MCP and CLI bridge contract

Auto selection tries configured MCP, then an installed CLI bridge executable, then a populated API token environment variable. Once selected, failed reads are reported; an inaccessible configured tool does not silently switch provider or reuse an unrelated account. Migration pins the transport and endpoint identity in its manifest.

For MCP set `"mcp": {"enabled": true}`. This declares an agent-operated bridge, **not proof that a matching MCP exists**. The agent must inspect its real available tools, establish the configured connection/project, and perform read-only `doctor` probes. Missing tools/permissions must be reported as unavailable.

MCP commands emit request files beneath `.project-docs/runtime/`. The agent reads each request, executes actual provider tools, normalizes the result, writes a matching response, then reruns the original command. Do not invent tool names, responses, readiness or capabilities. No Python subprocess can discover or invoke an agent's MCP tools by itself.

For CLI configure `"cli": ["/absolute/path/to/provider-bridge", "--profile", "team"]`. The executable receives one JSON request on stdin and emits one JSON response on stdout. This is a bridge protocol, **not automatic compatibility with bare `gh`, `az`, `glab` or third-party Jira/Linear CLI commands**. Wrap those tools to implement this contract. Commands run as argv with `shell=False`; stderr is not copied into migration logs.

```json
{"version":1,"request_id":"sha256-of-request","connection":"team-jira","provider":"jira","operation":"get","payload":{"id":"10001"}}
```

```json
{"request_id":"same-request-id","result":{"id":"10001","kind":"work_item","title":"Example","description":"Text","type":"Task","raw_state":"To Do","state":"todo","url":"https://example.atlassian.net/browse/DOC-1","full":true,"comments":[],"attachments":[],"labels":[],"parent":null}}
```

For MCP save the response as `responses/<request_id>.json` alongside the emitted `requests/` directory. Errors use `{"request_id":"...","error":"unavailable"}`. The private runtime directory includes an ignore-all `.gitignore`; keep it with the project until migration verification and recovery no longer need it.

| Operation | Payload | Required result |
|---|---|---|
| `doctor` | none | `capabilities` array; read access and write-permission limits |
| `schema` | none | `types`, `states`, `labels`, `users` arrays; optional `free_labels`, `parent_types` |
| `list` | `full` boolean | version-1 snapshot with connection/provider, UTC `fetched`, `coverage`, `items`; fully paginate before claiming complete |
| `get` | `id` | canonical record; `full:true` only after all comments/attachments have been inventoried |
| `find` | `marker`, `kind` (`item`, `comment`, `attachment`), `item_id` | exhaustive list of matching records, each with `id`; errors must not become an empty list |
| `download` | `url` | base64 bytes in `base64`, optional `sha256` |
| `create` | `item`, `marker` | created `id`; persist marker in description |
| `configure` | `id`, `item` | `id`; set final description/state/labels/assignee idempotently |
| `comment` | `id`, `body`, `marker` | comment `id`; persist marker and provenance text |
| `attach` | `id`, `name`, `base64_data`, `marker` | `id`, `url`, `name`; marker must be discoverable in filename/title |
| `parent` | `id`, `parent_id` | `id`; idempotent native parent relationship |
| `artifact` | `id`, optional `attempt` | Actions metadata described in the Actions guide |

Canonical records also retain the provider payload in `raw`. Comments carry `id`, `body`, `author`, `created`; attachments carry `id`, `name`, `url` and optionally `source_link` for an embedded relative URL. Preserve originals rather than making up unavailable values. For an uncertain MCP write, the agent must reconcile the marker remotely before executing that write again, including if the tool succeeded but its response file was lost.

## Validation boundary

The automated suite uses fixtures, mock HTTP responses, executable CLI bridges and an agent-bridge simulation. It does not establish live account permissions or guarantee parity across different workflow customizations. Run `doctor` with a real configured connection before actual use; validate a representative small migration before moving a whole project.
