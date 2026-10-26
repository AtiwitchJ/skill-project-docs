# GitLab Issues and merge requests

Configure `provider: gitlab`, `project` as a numeric ID or namespace/project, `token_env`, and optionally `base_url` (default `https://gitlab.com`). Direct API uses REST v4; self-hosted instances must support the endpoints used by their adapter.

Issue and MR inventories are paginated independently and distinguished by kind. The same IID can occur in both. Issue states opened/closed are mapped separately from MR merge state. Merging an MR does not automatically prove a task's acceptance criteria passed.

Direct migration creates Issues and notes, copies labels/assignees/state, and uploads binary files with a discoverable note linking each upload. Embedded `/uploads/...` links are inventoried and rewritten after copy. This adapter does not advertise native parent support: unsupported hierarchy must be reported and retained in the source archive, or handled by a capable bridge.

The project token needs permission for the intended reads or migration writes. A token with API write scope can create Issues/notes and upload project data; keep its project membership restricted. Normal docs check/import operations never invoke remote writes.

References: [Issues API](https://docs.gitlab.com/api/issues/), [Merge requests API](https://docs.gitlab.com/api/merge_requests/), [Markdown uploads API](https://docs.gitlab.com/api/project_markdown_uploads/).
