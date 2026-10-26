# Copy work between trackers

This flow applies only when the owner requests a migration. Docs sync remains read-only externally. The implementation supports all 20 directed source/destination pairs between Azure DevOps, GitHub Issues, Jira, Linear and GitLab Issues through a shared record contract. PR/MR records are excluded from creation; their existing references remain intact.

## Prepare and plan

Configure both connections using [providers.md](providers.md), run `doctor`, and run `integrations.py upgrade` if tasks do not yet have UIDs. Choose the source project/repository explicitly: the migration inventories **all work items in that configured scope**, not only those mentioned in tasks.md. Coordinate source changes during the copy; the immutable archive represents the point-in-time inventory, not a continuing two-way sync.

Create a private mapping JSON file. Status and type targets must exist in destination schema; never infer an unfamiliar status. User mappings use provider identities (Jira account ID, Linear ID, GitLab numeric ID, GitHub login, or ADO identity). Labels can also be mapped.

```json
{
  "types": {"Task": "Issue", "Bug": "Issue"},
  "states": {"New": "open", "Active": "open", "Done": "closed"},
  "users": {"source-user-id": "destination-user-id"},
  "labels": {"old-label": "existing-label"},
  "accept": {}
}
```

```bash
python3 /path/to/skill/scripts/migrate.py plan old-tracker new-tracker --id move-001 --mapping /private/mapping.json
```

Plan performs no external writes. It discovers destination schema/capabilities, fetches the full source inventory and comments, downloads attachment bytes into ignored private runtime storage, and creates an inspectable manifest. Raw provider fields, custom metadata, authors and timestamps are preserved in the private source archive. Cross-system formatting is normalized to text; the raw format remains archived.

Unmatched users, unsupported hierarchy, unavailable labels and attachment/comment limitations are listed with stable codes. Missing required type/state mappings stop planning. Missing mandatory create/get/find/configure capabilities cannot be waived. Other limitations block apply until explicitly accepted with a nonempty reason in `accept` and a **new plan ID**, for example `"123.assignee": "Keep original identity in archive; leave unassigned"`. Acceptance stays visible in verification; it does not make an archived-only attachment a copied remote attachment.

Inspect scope, intended changes, limitations and local backup before applying the plan. No new confirmation is needed when the owner has already authorized that concrete migration. Never expand an authorization for docs checks into a migration.

## Copy, recover, and verify

```bash
python3 /path/to/skill/scripts/migrate.py apply move-001
python3 /path/to/skill/scripts/migrate.py resume move-001
python3 /path/to/skill/scripts/migrate.py verify move-001
```

Creates run before dependent operations; parent-required item types are created in parent order. Attachment copies precede final document/comment text so embedded source URLs can be rewritten to copied assets. Original authors/times are included as attribution when native history cannot be retained. Source records are never edited or deleted.

The atomic operation journal records destination IDs. Source identity plus destination identity produces stable remote markers. After timeout, resume searches for the marker before retrying create/comment/upload. Multiple matches stop recovery. Configure/parent operations are idempotent. Concurrent migration commands for the same ID are excluded by a process lock. Do not remove operation markers while recovery is in progress.

Verification reads destination data, checks titles/types/status, descriptions, labels, mapped users, comments, parent links and attachment byte checksums. It separates `missing`, `failed`, `unsupported` and checked IDs. An unavailable read or missing file never counts as a success. A successful report binds the current plan and journal hashes.

MCP steps can return pending work. Complete the actual emitted tool requests and rerun the same command. Never replace an unknown result with an empty search result. If an external write might have succeeded without a response, reconcile its operation marker first.

## Cut over or roll back locally

```bash
python3 /path/to/skill/scripts/migrate.py cutover move-001
python3 /path/to/skill/scripts/migrate.py rollback move-001
```

Cutover requires successful verification, switches the primary tracker, adds destination refs for tasks/phases while retaining source refs, saves a partial destination snapshot of verified records, and regenerates the phase table. It does not change Task UIDs or task markers. Local config/mapping immediately before cutover are backed up.

Rollback restores those local files and regenerates the phase table. It does **not** delete destination items, undo remote comments/files, or modify the source. Keep both the migration directory and the private runtime archive to support recovery. The manifest/journal/reports are in `project/backlog/migrations/<id>/`; source originals and binary files are beneath the ignored `.project-docs/runtime/migrations/<id>/`.

The archive and reviewable manifest may contain confidential project data, including copied descriptions/comments. Access is the local filesystem user's access; it is not encrypted by the skill. Provider credentials remain outside the archive. Do not publish private migration material or copy private source content into a public destination unintentionally.
