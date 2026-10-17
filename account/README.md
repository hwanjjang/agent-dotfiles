# Install and maintain an account

Use [setup-account.sh](../scripts/setup-account.sh) to deliver this repository's
committed policies, skills and planning runtime to another account. The script
supports **macOS and Linux**, including Linux inside WSL. Native Windows is not
supported. It never copies the contributor's installed account configuration.

Codex and Claude Code are the default clients. Hermes is optional and requires
an installed `hermes` executable. No client, model account or credentials are
installed by this tool. Install Python 3.11+ and Git first; the shell entry point
finds a compatible Python on PATH, or accepts `AGENT_DOTFILES_PYTHON`.

## Install, update and remove

Clone this repository on the destination host and run these commands there.
Commands preview their changes unless `--apply` is present. The default target
is that host's home; `--home /path/to/account` selects an existing target directory
without changing HOME. Close agent sessions while applying changes.

```sh
# Inspect the committed version and proposed paths first.
sh scripts/setup-account.sh install
sh scripts/setup-account.sh install --apply

# After fetching/reviewing a newer source revision:
sh scripts/setup-account.sh update --revision origin/main
sh scripts/setup-account.sh update --revision origin/main --apply

sh scripts/setup-account.sh status
sh scripts/setup-account.sh uninstall
sh scripts/setup-account.sh uninstall --apply
```

`--revision` reads a local Git commit (HEAD by default); the script never fetches
or installs uncommitted edits. The receipt records the resolved commit. Updates
remove assets/skill links retired by the selected revision. Uninstall removes only
this installation's owned assets and configuration fragments, preserving other
settings. Empty parent directories, receipts from other managers and transaction
backups remain. Modified managed content blocks update/removal until reconciled;
there is no blanket force-delete option.

### Optional integrations

```sh
# Opt in only if Hermes is already installed on this host.
sh scripts/setup-account.sh install --with-hermes
sh scripts/setup-account.sh install --with-hermes --apply
sh scripts/setup-account.sh update --without-hermes --apply

# MCP connections are opt-in. Supply credentials through the client environment.
sh scripts/setup-account.sh update --mcp github,context7,playwright
sh scripts/setup-account.sh update --mcp github,context7,playwright --apply
sh scripts/setup-account.sh update --mcp none --apply

# Remove/re-add only the managed planning hook registrations/runtime.
sh scripts/setup-account.sh update --without-hooks --apply
sh scripts/setup-account.sh update --with-hooks --apply
```

Selections persist across updates when their flags are omitted. `--without-hermes`
removes only the managed Hermes links/instruction block. Hermes support covers
skills and a shared-instruction pointer in SOUL.md; it leaves personality text,
config.yaml, plugins and native hooks unchanged. Planning remains manually usable;
this installer does not supply Hermes lifecycle recovery or MCP integration.

Codex and Claude receive the selected MCP entries from the existing templates;
GitHub remains read-only. Missing environment variables must be supplied locally:
`GITHUB_MCP_TOKEN` and `CONTEXT7_API_KEY`. Existing names are conflicts, not implicit
overwrite permission. Disabled state and unrelated connections are preserved.
See [MCP templates](../mcp/README.md) for transports and service limits. Configuration
delivery does not prove authentication or a working connection.

## Ownership and conflicts

| Content | Owner and treatment |
| --- | --- |
| Delivered source snapshot | `.agents/agent-dotfiles/bundle/`, copied from the chosen commit with skill/policy relative paths intact. |
| Shared skills | Individual links under `.agents/skills/`; Claude uses `.claude/skills/`. Codex reads the shared location; only the planning runtime also needs a `.codex/skills/planning-with-files` compatibility link. |
| Optional Hermes skills | Individual links under `.hermes/skills/`, only after opt-in. |
| Account instructions | A small managed block in `.codex/AGENTS.md`, `.claude/CLAUDE.md` and optionally `.hermes/SOUL.md` points to [instructions.md](instructions.md) in the delivered bundle. Repository-root AGENTS.md/CLAUDE.md are not distributed as account instructions. |
| Planning runtime | [Documented default client paths](hooks/README.md), with only owned JSON hook groups merged into settings. |
| Paseo and host/system plugins | Preserved under their existing manager; all six Paseo skills are excluded from ownership. |
| Authentication, preferences, model choices, trust and permission settings | Local and preserved. No authorization, hook trust or MCP credentials are added implicitly. |
| State and backups | `.agents/agent-dotfiles/state/`, local only. Never commit or share raw receipts, plans or backups. |

Overlap with any replacement/removal target (including a skill directory containing
the source checkout), symlinked parent directories, symlinked configuration
files, malformed settings, duplicate planning routes and changed managed content
are rejected before writing. Default client directories are the supported layout;
nondefault CODEX_HOME, CLAUDE_CONFIG_DIR or selected HERMES_HOME profiles are
reported rather than silently installing into the wrong profile. An active
Codex AGENTS.override.md must be reconciled because it masks AGENTS.md.

An existing selected skill directory or runtime file is not assumed to be ours.
Save and inspect a preview, then pass that **exact** plan to authorize its takeover:

```sh
umask 077
sh scripts/setup-account.sh install > /tmp/account-plan.json
# Inspect conflicts and before/after fingerprints; keep this plan private.
sh scripts/setup-account.sh install --apply --approve-plan /tmp/account-plan.json
```

The plan includes fingerprints rather than configuration contents. Any change to
the account, selected revision or options invalidates approval. Before writing,
the installer rechecks the account and keeps originals in a private backup.

For an earlier receipt-based setup, `--legacy-receipt /path/to/old-receipt.json`
can retire its exact instruction blocks and hook groups in supported client files.
Use the same option in preview and apply, with `--approve-plan`. This is a narrow
v1 receipt adapter, not a universal legacy uninstaller: unmatched/changed fragments
are rejected, older tools/plugins/MCP entries remain with their existing owner,
and colliding selected assets still require exact-plan approval. Retire the old
updater separately so two managers do not write the same paths.

## Recovery and checks

Each applied operation returns a transaction ID. Caught write failures attempt
rollback. A pending journal also supports recovery after interruption:

```sh
sh scripts/setup-account.sh rollback --transaction TRANSACTION_ID
sh scripts/setup-account.sh rollback --transaction TRANSACTION_ID --apply
```

Rollback restores that transaction's originals only if touched paths still match
its recorded before/after state or a journaled directory-move interruption. Original
directories remain in the private transaction folder until recovery is no longer
needed; restoring them uses a rename instead of a partial directory copy. Directory
takeover requires the target and state directory to share a filesystem; a failed
cross-device rename rolls back without deleting the source. Later edits stop recovery rather than being
clobbered. Roll back newest transactions first. Backups may contain private
configuration; keep them local until recovery is no longer needed. Uninstall does
not automatically reactivate a replaced legacy setup; rollback is the explicit
restoration path.

`status` checks owned files/links and managed instruction, hook and MCP fragments.
Its clean result is an ownership check, not proof that a model followed instructions.
The installer reports missing executables; Git, rg, gh, Node.js 18+, browser support
and [PDF dependencies](../skills/screenshot-manual/requirements.txt) remain under
the host's package managers. No registry entry currently declares a managed CLI
installation recipe. An optional MCP stdio command may download its pinned package
when the client starts it; preview/apply does not run servers.

After installation, inspect each client's effective skill list and instruction
sources, review/trust Codex hooks in the native client, exercise a selected-plan
recovery and check MCP tools only for the connections you opted into. Do not install
a second plugin/copy of the same collection. See [client verification](../docs/client-verification.md)
for checks actually exercised and [the design decision](../docs/decisions/account-installation.md)
for source comparisons and limits.

A [screenshot walkthrough](../docs/manual/account-source.pdf) shows where to find
these commands and the hook guide in the workflow map.
