# Reviewer execution readiness

Adopted: 2026-10-30. In the review of PR #103, the required Codex reviewer and the
additional Grok reviewer could not run the checks the review depended on, while Gemini
under full access ran all of them. The [host adapter contract](../../skills/sdlc/references/host-adapters.md#reviewer-execution-readiness)
now prepares each reviewer's execution before dispatch, and the
[host recipes](../../skills/sdlc/references/reviewer-execution.md) record verified settings.

## What failed and why

| Reviewer | Observed | Cause, from reproduction |
| --- | --- | --- |
| Codex CLI 0.163.0, Paseo mode `auto` | TLC failed with `java.rmi.server.ExportException: Listen failed on port: 0`; 71 repository tests failed; `gh api` was blocked; escalation requests reached the coordinator | The workspace-write sandbox allows no network and no local socket binding. `codex sandbox -P :workspace` reproduces the TLC failure. |
| Grok CLI 1.0.70, Paseo ACP | Every shell command outside the read-only list asked for approval; Grok reviewed by reading only | Default ask mode; Paseo forwards prompts to the coordinator. Project rules were not loaded in an untrusted repository. |
| Grok, after the above | The statechart TLC case skipped | Its captured login shell resolved Homebrew Node 20 before an nvm Node 24, below the launcher's minimum (22.18). |
| Coordinator, Claude Code in auto mode | Its approvals of reviewer commands and its writing of reviewer permission files were refused | Granting another agent permission to run commands is a decision for the user. |

## What was verified

- **Codex.** A project `.codex/config.toml` in the review checkout with
  `[sandbox_workspace_write] network_access = true` and `[features.network_proxy]`
  `enabled = true`, `allow_local_binding = true`, and no allowed domains. A Paseo-launched
  session ran the TLC test with no approval, and `curl https://api.github.com` was blocked.
  Under the same setting, `codex sandbox` cut the 71 failing tests to 2: the isolation
  canary, which starts a nested sandbox, and the child-process query. A permission profile
  chosen with `default_permissions` worked for `codex sandbox -P` but not in the Paseo
  session.
- **Grok.**
  - Running `grok --trust` in a review worktree recorded the main repository path. After
    that, `grok inspect` showed the project trusted and the checkout's rules loaded.
  - Project `allow` rules still did not stop prompts in Paseo's ACP sessions.
  - Auto-approve (Paseo `auto_accept`) together with project `deny` rules worked. The
    allowed test ran without a prompt, and a denied command was refused rather than
    prompted.
- **Antigravity.** Only `full-access` is offered; checks run without isolation.

Each probe ran in a disposable review worktree; probe files were removed afterwards.

## Decision

- Prepare reviewer execution before dispatch rather than approving commands mid-review:
  the narrowest setting the host supports, a preflight in the reviewer's own environment,
  offline evidence and an integrity check after the return. Full access stays allowed
  when nothing narrower exists, with no isolation recorded.
- Apply settings per review checkout. Global client settings would change every session
  of those clients, and Grok's deny rules would block ordinary editing. The
  [helper](../../skills/sdlc/scripts/review_workspace.py) writes the profiles, builds
  hashed bundles that refuse names colliding on case-insensitive file systems, reports
  runtime versions and checks integrity. It changes no account settings.
- Keep permission grants with the user. Folder trust for Grok and the auto-approve choice
  are recorded as account decisions. Do not add a coordinator rule that approves other
  agents' prompts.

On this account, AK authorized the change on 2026-10-30. Grok trust was recorded for this
repository; no global Codex or Grok setting changed.

## Community evidence and limits

Searches on 2026-10-30 found no firsthand report of these exact reviewer setups.

| Source | Finding | Limit |
| --- | --- | --- |
| [openai/codex#23973](https://github.com/openai/codex/issues/23973) | `allow_local_binding = true` in a custom profile worked in the CLI but not in another client's command path. | Codex 0.133.0. It matches the profile-selection difference seen here. |
| [openai/codex#35437](https://github.com/openai/codex/issues/35437) | `writable_roots` was dropped when a client passed an explicit turn policy, while network flags still applied. | macOS. It suggests why the legacy keys work under Paseo. |
| [Cursor forum: ACP approval mode ignored](https://forum.cursor.com/t/acp-approvalmode-auto-review-classifier-and-autorun-instructions-are-ignored-auto-review-degrades-to-plain-allowlist-and-cursor-permissions-json-is-never-read/165665) | Another product's ACP route ignored its permission configuration. | A different CLI, cited as an analogy only. |

Primary sources: OpenAI's [sandboxing](https://learn.chatgpt.com/docs/sandboxing.md),
[approvals and security](https://learn.chatgpt.com/docs/agent-approvals-security.md) and
[configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)
pages, and Grok's installed user guide (permissions and safety, configuration, sandbox,
hooks).

**Limits.**
- One macOS host, one launcher (Paseo), Codex 0.163.0 and Grok 1.0.70.
- Claude Code as a reviewer and Linux hosts were not exercised.
- The recipes record observations, not guarantees for other versions.
