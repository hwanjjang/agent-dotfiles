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

### Review installation and hook activation together

The preview's `hook_activation` section lists the exact Codex event, matcher,
command and definition hash for the selected source revision. Its seven planning
events are SessionStart, UserPromptSubmit, PreToolUse, PostToolUse,
PermissionRequest, PreCompact and Stop. The preview also states that trusted hooks
run outside the model sandbox and that native trust persists. Keep previews local:
their resolved commands contain host paths.

When requesting an account transition, include both installation and activation
in one concrete approval: identify the target, source revision, reviewed preview
and these execution effects. For example: “Apply this reviewed preview and trust
only its listed Codex planning hooks through native /hooks; their execution is
outside the sandbox and trust persists.” Reuse that authority while the definitions
and scope match. Reconcile any changed definition before trusting it. An external
approval reviewer may still require clarification; this repository cannot override
its decision.

The installer registers hooks but does not grant native trust. After applying,
check ownership with `doctor`, compare native `/hooks` definitions with the reviewed
preview, activate only authorized definitions, then verify native/model behavior.
`doctor` remains diagnostic and never approves hooks. This workflow avoids an
ambiguous “check the hooks” request without introducing a trust-bypass option.

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

## Diagnose and exercise the installation

`status` checks receipt ownership. `doctor` adds actionable setup diagnostics; use
it after installation, updates, client upgrades or a missing skill/hook report.
Run from this checkout with the same Python 3.11+ entry point:

```sh
# Local files/settings only: no client process, model request or account writes.
sh scripts/setup-account.sh doctor
sh scripts/setup-account.sh doctor --json

# Query installed clients without a model turn. Start with Codex.
sh scripts/setup-account.sh doctor --native --client codex
sh scripts/setup-account.sh doctor --native --client claude
```

Offline checks reuse the ownership receipt and detect changed assets/fragments,
missing or conflicting skill paths, masking instructions, competing planning
routes and missing client executables. Same-source legacy aliases are allowed.
Native Codex checks actual skill source paths and effective hook trust. A
`modified` or untrusted hook is **blocked**, with `/hooks` as the next action; the
command never trusts hooks or bypasses review. Claude initialization checks skill
commands and actual SessionStart recovery of a synthetic selected plan.

Native checks run on the current account only; `--home` remains useful for offline
inspection of another/disposable target. Native clients may update their local
state/caches and run existing startup hooks. The probe sends no user/model turn,
uses temporary synthetic project data and tears down its own processes.

A real model scenario is a separate, explicit opt-in:

```sh
# Replace MODEL_ID with a low-cost model actually offered by this client.
sh scripts/setup-account.sh doctor --model-smoke --client codex --model MODEL_ID \
  --evidence-dir .local/account-checks/codex-001
sh scripts/setup-account.sh doctor --model-smoke --client claude --model MODEL_ID \
  --evidence-dir .local/account-checks/claude-001

# Natural selection: no skill names in the task; specification → task planning.
sh scripts/setup-account.sh doctor --model-smoke --scenario routing \
  --client claude --model MODEL_ID --evidence-dir .local/account-checks/routing-001

# Paseo is optional. This includes a second actual model task via the local daemon.
sh scripts/setup-account.sh doctor --model-smoke --client codex --model MODEL_ID \
  --with-paseo --evidence-dir .local/account-checks/paseo-001
# Connection-only Paseo diagnostic, without model requests:
sh scripts/setup-account.sh doctor --with-paseo
```

The model must read the installed `to-spec`, account entry point and four selected
policies, then draft a specification for synthetic CLI requirements. The grader
checks a fresh scenario marker, four exact stdout/stderr/exit-code examples,
acceptance criteria, no fabricated test execution, source-reading evidence and
unchanged inputs. Native tool traces establish source reads. Paseo's summarized
logs are supplemented by exact source-content readback and its inspected actual
model ID; this is not a complete tool audit. A valid reply or successful launch
alone cannot pass. This bounded scenario does not certify every skill or a full SDLC.

`--scenario routing` checks native Codex/Claude selection of the installed spec and
planning methods without naming them in the task. It uses the client's structured
output facility and checks source reads or successful native skill injection,
acceptance coverage, prior-task dependencies and concrete verification. It does
not publish tickets, implement code or run the full SDLC; it cannot be combined
with `--with-paseo`. Default `spec` remains the explicitly selected skill scenario.

Model identity is checked automatically. Claude must report the requested ID in
initialization and actual usage. Codex uses the native app-server's thread model,
completed turn and reroute events, with provider model fallback disabled. Missing
or conflicting identity cannot pass; this is client-observed identity, not an
independent audit of the provider's internal routing.

Choose an exact model ID from the installed client's catalog; there is no silent
fallback or retry. A low-cost model is sufficient for this small task. Availability
and pricing change, so the tool requires `--model` rather than pinning a default.
Models receive account instructions and selected installed source content through
the authenticated client; inspect that material and obtain any required transfer
approval before running. Authentication, personal memory, session history and
unrelated account files are excluded by the test prompt. Codex uses read-only /
approval-never; Claude exposes Read, plus Skill for routing. Existing client startup hooks still apply.
The scenario does not modify trust or persistent permission settings.

Model checks may consume subscription/API quota. `--timeout` bounds each subprocess
(default 90 seconds, maximum 300); no automatic retries or expensive fallbacks run.
Claude also requests a USD 0.50 CLI budget. Codex/Paseo have no verified hard-dollar
cap here: bounded runtime and a small prompt are not a guaranteed spending limit.
Paseo reuses the selected model at low effort, an isolated local workspace, and the
provider's normal `auto` (Codex) or `plan` (Claude) mode. It archives only resources
created by this check, then removes its temporary project registration. Remote
Paseo hosts, UI interaction and other providers are
outside this adapter; Paseo is never required unless selected. If native model
execution fails, an additional Paseo request is not sent.

Evidence directories must be new, private and ignored/outside the checkout. They
retain source identity, prompt, synthetic input, native logs, answer and grades;
Paseo adds owned resource IDs and cleanup records. Raw output may contain account
paths or context. Never publish it as part of this public repository. Reusing an
existing directory is refused. Failures and quota limits are retained, not erased.

Reports use **pass / fail / blocked / skipped** per check. Exit 0 means the selected
scope passed, 1 means a finding or blocked check, and 2 means invalid usage or an
execution error. A skipped native/model/MCP check is not a pass. Combine `--native`
with `--model-smoke` to see both readiness and model results; a passing model
scenario does not override a blocked hook. MCP authentication and native Hermes
execution remain outside this check. See the [verification recipe](../docs/verification/verify-repository/features/account-verification.md).

Doctor reports identify `evidence_kind: account_qualification`, with
`comparison.status: not_run` and `comparison.promotion_eligible: false`, including
successful model scenarios. Use them for setup readiness and deployment checks.
The [improvement-loop contract](../docs/decisions/account-improvement-loop.md#account-qualification-and-reuse)
owns comparison, failure-to-case triage and promotion requirements. Doctor neither
activates collection nor writes events to the observation store. Existing observation
records and grants remain outside installer ownership through update, rollback and
uninstall; use the observation CLI to revoke or prune them explicitly.

`native_activation_by_client` and `native_activation_verified` summarize observed
SessionStart recovery for the selected clients, not every lifecycle event. Codex
defers SessionStart until its first turn, so `--native` alone checks registration
and trust; add `--model-smoke` to establish recovery. Claude initialization can
establish recovery without a model request. Missing or blocked evidence remains
false, and a mixed-client summary is true only when every selected client passes.

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
