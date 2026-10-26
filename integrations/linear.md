# Linear

Configure `provider: linear`, `team` as the team ID, and `token_env`. Direct API uses GraphQL at `https://api.linear.app/graphql`; [MCP/CLI bridges](providers.md) use the same normalized record contract.

Personal API keys are sent verbatim in the Authorization header; for an OAuth access token configure `auth: bearer`. Queries request temporarily signed file URLs so source downloads and destination readback can retrieve private Linear assets without forwarding the API key to unrelated hosts. Signed URLs can expire; rerun a failed read/plan to obtain fresh ones.

The API adapter paginates team issues, issue comments and linked attachments. Original Linear UUIDs and display identifiers are preserved separately. Map custom workflow states explicitly. Schema reads provide state/label IDs and team members; user mappings use destination user IDs.

Migration creates issues, adds attributed comments, uploads file bytes through signed upload URLs, links the resulting asset as an attachment, and sets native parent relationships. External attachment URLs may require additional access; an inaccessible download stops planning rather than becoming an empty file. Source raw fields are retained in the private archive.

A Linear token with team write access can create issues, comments and attachments. Limit access to the intended team; the upload step sends only signed-upload headers to storage, never the API bearer token to an unrelated asset host. `doctor` establishes readable schema and reports write permission limitations.

Reference: [Linear developer documentation](https://linear.app/developers). See [migration](migration.md) for recovery and cutover.
