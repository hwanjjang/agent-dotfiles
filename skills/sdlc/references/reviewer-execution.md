# Reviewer execution recipes

Verified settings that let review hosts run required checks under
[reviewer execution readiness](host-adapters.md#reviewer-execution-readiness). Each
entry names the version, date and observation behind it. Recheck after a host upgrade
and record what you observe; an entry for another version is a starting point, not
evidence.

The [helper](../scripts/review_workspace.py) applies the file-based parts:

```sh
python3 <skill>/scripts/review_workspace.py profile --checkout <checkout> --host codex
python3 <skill>/scripts/review_workspace.py profile --checkout <checkout> --host grok --check-grok
python3 <skill>/scripts/review_workspace.py bundle --checkout <checkout> --name review-bundle --file intent.md=<path>
python3 <skill>/scripts/review_workspace.py runtimes --min node=22.18 --min java=11
python3 <skill>/scripts/review_workspace.py integrity --checkout <checkout> --head <sha>
python3 <skill>/scripts/review_workspace.py remove --checkout <checkout>
```

The reviewer runs `runtimes` in its own environment; the coordinator runs the rest.
`profile` refuses to replace an existing file with other content, and `integrity`
accepts only files the helper placed.

## Codex

Observed with Codex CLI 0.163.0 on macOS, launched through Paseo in mode `auto`
(workspace-write, on-request approvals), 2026-10-30.

- The default sandbox allows no network and no local socket binding. TLC fails with
  `java.rmi.server.ExportException: Listen failed on port: 0` (`SocketException:
  Operation not permitted`), tests that open local sockets fail, and escalation
  requests go to the coordinator. `codex sandbox -P :workspace` reproduces this.
- Place this project `.codex/config.toml` in the review checkout. Codex loads project
  config only for a trusted project; a worktree of a trusted repository qualified.

  ```toml
  [sandbox_workspace_write]
  network_access = true

  [features.network_proxy]
  enabled = true
  allow_local_binding = true
  ```

  The proxy has no allowed domains, so outbound requests stay blocked while local
  binding works. Observed: the TLC test passed, `curl https://api.github.com` was
  blocked by the proxy allowlist, and no approval was requested.
- A permission profile chosen with `default_permissions` worked for
  `codex sandbox -P` but not in the Paseo session, which sets the legacy sandbox mode.
- Still unavailable inside the sandbox: starting a nested sandbox and inspecting
  other processes. Under the setting above this repository's suite failed only the
  isolation canary and child-process query tests for those reasons; cite CI or other
  evidence for them.

Primary sources: [sandboxing](https://learn.chatgpt.com/docs/sandboxing.md),
[approvals and security](https://learn.chatgpt.com/docs/agent-approvals-security.md),
[configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).

## Grok

Observed with Grok CLI 1.0.70 through Paseo's ACP launcher, 2026-10-30.

- In the default ask mode every shell command outside Grok's read-only list prompts,
  and Paseo forwards the prompt to the coordinator.
- Project `allow` rules did not suppress those prompts in the Paseo session. What
  worked: start the agent with auto-approve (Paseo feature `auto_accept`, ACP
  `_meta.yoloMode`) and place `deny` rules in the project `.grok/config.toml`. Deny
  rules hold under auto-approve; a denied command is refused, not prompted.
- Project rules load only in a trusted repository: check `grok inspect --json` for
  `projectTrusted` and `permissions.loaded`. Running `grok --trust` in a worktree
  records the main repository path, which covers its worktrees. Trust also loads that
  repository's project instructions, skills, hooks and MCP servers, so it is the
  user's decision.
- Commands run in a captured login shell. On the observed host it resolved Homebrew
  Node 20 before an nvm Node 24, below the statechart launcher's minimum; have the
  reviewer run `runtimes` and pass an explicit `PATH` prefix when a runtime is too old.
- Without a sandbox profile Grok is not isolated: the deny list and the integrity
  check are the boundary.

Primary sources: Grok's installed user guide, chapters on permissions and safety,
configuration, sandbox and hooks (folder trust).

## Antigravity (Gemini)

Observed through Paseo, 2026-10-30: the only mode is `full-access`
(`--dangerously-skip-permissions`). Checks run and nothing is isolated. Use review-only
instructions and the integrity check, and record that no isolation applied.

## Claude Code as coordinator

Observed 2026-10-30: in auto mode, Claude Code refused the coordinator's approval of
reviewer commands and its writing of reviewer permission files. Do not route review
execution through coordinator approvals, and do not add a blanket rule that lets the
coordinator approve other agents' prompts; prepare profiles with the user's authority
before dispatch, or record the gap.

Claude Code as a reviewer is not covered by these observations.
