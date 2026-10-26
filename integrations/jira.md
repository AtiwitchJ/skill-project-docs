# Jira Cloud

Configure `provider: jira`, the site's `base_url`, and the project key. An API-token connection uses `token_env` and `username_env` for the account email. A bearer-token gateway must expose the configured Jira REST v3 base. See [providers](providers.md) for MCP/CLI alternatives.

The API adapter paginates enhanced JQL search and issue comments, retains Jira IDs and display keys separately, and reads project issue types/statuses. Map workflow status names explicitly to internal todo/doing/blocked/done states. A status with no known mapping is reported, not guessed.

Migration converts descriptions/comments to ADF text while archiving original rich data, uploads attachments, maps account IDs, and uses available transitions. A status listed in the project might still be unreachable from the new Issue's initial status; apply then stops and reports an uncertain operation for reconciliation. Jira subtask types require a migrated parent and are created in parent order. Custom mandatory fields or workflow validators may require a project-specific bridge; never silently omit them.

An account with Create/Edit Issues, Add Comments and Create Attachments permissions can change project records and upload private files. Keep that account restricted to the intended project. Read probes cannot establish every workflow-specific write permission. No secret belongs in project JSON, manifests or logs.

References: [Jira REST v3](https://developer.atlassian.com/cloud/jira/platform/rest/v3/), [issue attachments](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-attachments/).
