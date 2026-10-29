# Agent packages: one core, multiple host formats

This repo owns one `project-docs` core plus six workflow entry points. `build_plugins.py` consumes the same `install_skills.bundle()` payload used by portable installation. Host wrappers contain metadata/layout only; Task rules, Description guidance, hierarchy checks, phase reports and evidence logic are shared.

## Compatibility matrix

| Host / target | Exported native marker | Supported route |
|---|---|---|
| Claude Code / `claude-code` | `.claude-plugin/plugin.json` | Native plugin; generated local Claude marketplace; seven skills |
| Codex / `codex` | `.codex-plugin/plugin.json` | Codex compatibility plugin; generated local marketplace; seven skills |
| Antigravity / `antigravity` | `plugin.json` with Antigravity schema | Native skills-only plugin for surfaces supporting local plugins |
| Copilot / `copilot` | root `plugin.json`, Agent Plugins 1.0 | Native source import in compatible Copilot/VS Code harness |
| Gemini CLI / `gemini-cli` | `gemini-extension.json` | Native extension with skills, not an Antigravity plugin |
| Cursor / `cursor` | `.cursor-plugin/plugin.json` | Native plugin and generated Cursor marketplace; portable fallback where local import is unavailable |
| Agent Plugins 1.0 / `agent-plugins` | root `plugin.json` with standard schema | Standards-format package for clients that implement this standard |
| Kilo, OpenCode, Hermes / `portable-skills` | Seven sibling skill folders | Portable skill install; no fake JavaScript/Python runtime plugin is introduced |
| Other skill hosts | Same portable payload | Explicit configured `--skills-dir`; discovery/invocation must be checked in that host |

Native packages retain the full `project-docs-setup`, `-check`, `-update`, `-rework`, `-close-phase`, `-test` names. A plugin host may add its own namespace. Use its picker/component list to identify the actual invocation instead of assuming `/project-docs-update` always resolves to the plugin copy.

These are packaging targets, not a blanket claim about every product version or cloud session. Local skill paths do not automatically provision remote/cloud runtimes. The builder adds no hooks, global rules, authentication, MCP servers or permissions. Existing provider access remains a separate configured capability; importing a package does not grant company-system access or automatically run the docs gate.

## Build and inspect

```bash
python3 scripts/build_plugins.py --all
python3 scripts/build_plugins.py --target antigravity
```

The default version is a content-derived snapshot such as `0.1.0-dev.g<digest>`. The default output is `dist/plugins/<version>/<selection>/`. The printed directory contains one folder and ZIP per target, `INSTALL.md`, local marketplace catalogs and `build-manifest.json`. ZIPs extract beneath `project-docs/`: extract each into its own host/target directory, never overlay packages for different hosts.

```bash
python3 scripts/build_plugins.py --target claude-code --target codex --version 1.0.0 --output /path/to/new-release
python3 scripts/build_plugins.py --check /path/to/new-release
```

Rebuilding identical source/targets is unchanged. A nonempty destination with different content is rejected; choose a new version/output rather than overwriting a reviewed artifact. Bump an explicit release version whenever the plugin payload changes. Checks verify exact seven-skill placement, shared-core availability, native metadata, safe paths, file hashes and ZIP inventory/content. They do not constitute a signature, an external trust decision, a native schema check for every host or a model-based workflow evaluation.

`dist/` is ignored by Git; commit source changes, not duplicated build trees. Publishing or registering a marketplace is a separate explicit action. Changing the repo alone does not update installed cached plugin copies; use the host's documented refresh/update operation and verify the installed version.

## Install in the intended host

Read the generated `INSTALL.md`, which uses paths relative to its release directory:

- Antigravity: `agy plugin install ./antigravity/project-docs` where the installed CLI supports local package installation. Its `agy plugin validate` command can inspect the local package without installing it.
- Claude Code: `claude --plugin-dir ./claude-code/project-docs` for a temporary local load. Persistent installation uses the generated `.claude-plugin/marketplace.json`, `/plugin marketplace add <absolute-release-path>`, then `/plugin install project-docs@project-docs-claude-local`.
- Codex: `codex plugin marketplace add <absolute-release-path>` registers the generated `.agents/plugins/marketplace.json`. Inspect the resulting source, then install `project-docs@project-docs-codex-local` using the installed CLI's `plugin add` command or the plugin picker on versions that expose installation there. Registering a marketplace alone is not an installed plugin.
- Copilot/VS Code: choose Install a plugin from source in Agent Customizations and select `copilot/project-docs`. Verify the intended harness/workspace; the exporter does not enable settings globally.
- Gemini CLI: `gemini extensions install ./gemini-cli/project-docs`. Use its extension list/reload procedures after installation.
- Cursor: use the local marketplace/plugin import supported by the installed version, with `.cursor-plugin/marketplace.json` and `cursor/project-docs`. If that UI cannot import local packages, use `install_skills.py --agent cursor` instead. No unverified Cursor CLI install command is promised.
- Kilo/OpenCode/Hermes: use `install_skills.py --agent kilo|opencode|hermes` from a reviewed source or the portable package's core; each command selects just one root. Customized or older skill roots use `--skills-dir`.

Do not install both standalone and plugin versions into the same host without reviewing naming/precedence. Do not remove old installations blindly: confirm the new package is visible and works in a small test project, then disable the specific obsolete package using its supported manager. Unknown-source companions and other agent installations are outside this packaging workflow.

## Verification levels

Record these separately:

1. **Offline tests:** byte-identical shared payloads, deterministic archives, safe names/paths, source/version changes, relative marketplace resolution and corruption rejection.
2. **Schema/native static validation:** official schema checks where available; actual `claude plugin validate --strict` and `agy plugin validate` when those CLIs are installed. Do not call an unavailable validator “passed.” These commands are not a live agent task.
3. **Discovery:** after host reload, list the installed plugin/version and all seven skill names. Same-name local/user/plugin copies can shadow one another.
4. **Invocation:** run a small read-only docs check in a documented temporary project, inspect what the host actually invoked, and confirm the intended core/version was used. A plugin appearing in a picker does not prove Task hierarchy or Description semantics.
5. **Real service behavior:** external tracker/MCP access requires separate configuration and authorization. Packaging tests do not establish provider permissions or production correctness.

No user agent configuration, installation, publishing or company-system operation is needed merely to build/test package artifacts.

## Official format references

Formats checked against official documentation on 2026-10-29:

- [Claude plugin manifest](https://code.claude.com/docs/en/plugins-reference) and [marketplace format](https://code.claude.com/docs/en/plugin-marketplaces).
- [Codex/OpenAI plugin packaging](https://developers.openai.com/plugins/build/plugins), including portable Agent Plugins and supported Codex compatibility layout.
- [Antigravity plugins](https://antigravity.google/docs/plugins) and [manifest schema](https://antigravity.google/schemas/v1/plugin.json).
- [Copilot/VS Code agent plugins](https://code.visualstudio.com/docs/agent-customization/agent-plugins) and [Agent Plugins 1.0 schema](https://agent-plugins.org/schemas/1.0.0/plugin.schema.json).
- [Gemini CLI extension reference](https://geminicli.com/docs/extensions/reference/).
- [Cursor plugin reference](https://cursor.com/docs/reference/plugins).
- Native skill roots: [Kilo](https://kilo.ai/docs/customize/skills), [OpenCode](https://opencode.ai/v2/docs/skills), [Hermes upstream guide](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/guides/work-with-skills.md).
