# Reviewer execution recipes

Verified settings that let review hosts run required checks under
[reviewer execution readiness](host-adapters.md#reviewer-execution-readiness). Each
entry names the version, date and observation behind it. Recheck after a host upgrade
and record what you observe; an entry for another version is a starting point, not
evidence.

The [helper](../scripts/review_workspace.py) applies the file-based parts:

```sh
# Coordinator, before dispatch; one record per review checkout, kept outside it
python3 <skill>/scripts/review_workspace.py profile --checkout <checkout> --record <record> --host codex
python3 <skill>/scripts/review_workspace.py profile --checkout <checkout> --record <record> --host grok --check-grok
python3 <skill>/scripts/review_workspace.py bundle --checkout <checkout> --record <record> --name review-bundle --file intent.md=<path>
# Reviewer, in its own environment
python3 <skill>/scripts/review_workspace.py runtimes --min node=22.18 --min java=11
python3 <skill>/scripts/review_workspace.py verify-bundle <checkout>/reports/review-bundle
# Coordinator, after the return
python3 <skill>/scripts/review_workspace.py integrity --checkout <checkout> --record <record> --head <sha> --expect-record-sha256 <digest> --allow '*__pycache__/*'
python3 <skill>/scripts/review_workspace.py remove --checkout <checkout> --record <record> --expect-record-sha256 <digest>
```

Keep each record in the coordinator's ignored task directory, never in a reviewer's
checkout, and note the `record_sha256` that the last preparation step reports.
Every command checks the record's structure before it writes. `profile` refuses to
replace an existing file with other content, writes refuse symbolic links on the way,
and `remove` deletes only the helper's unchanged profiles.
`integrity` reads the placed profiles, the bundles, the checkout's `.git` entry and
every other file's bytes and executable bit from disk, and compares them with the
snapshot taken at preparation. It does not rely on git's view of tracked files, which
index flags and filters set inside the checkout can bend. Only after those reads does it
run git, and then only `git rev-parse` with hooks and fsmonitor disabled, to confirm the
checkout top and HEAD; no filter, hook or fsmonitor program from the checkout's
configuration runs during the check. An unreadable folder fails it. `--allow` names
expected byproducts of the checks, such as Python bytecode. Contents inside `.git` and
extended attributes are not compared, and a reviewer with full access could defeat the
check: it reports drift and is not a security boundary.

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
- Without a sandbox Grok is not isolated. The deny list limits its tools, but an
  allowed shell command can still write anywhere the user can; the integrity check only
  reports drift afterwards.

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

## Claude Code as a reviewer

Observed with Claude Code 2.1.302 through Paseo's Claude provider (model
`claude-sonnet-5-5`), 2026-10-30, in review checkouts prepared with the helper.

- `auto` mode ran every check without a prompt, including the statechart TLC test. It
  also ran a write in the checkout and an outbound request, so nothing is isolated. The
  integrity check reported the stray file.
- `default` mode loaded a project `.claude/settings.local.json` placed in the review
  checkout. Allowed commands ran without a prompt, and denied commands were refused
  without one.

  ```json
  {
    "permissions": {
      "allow": ["Read", "Grep", "Glob", "Bash(git rev-parse:*)", "Bash(git status:*)",
                "Bash(git diff:*)", "Bash(git log:*)", "Bash(git show:*)",
                "Bash(python3.11:*)", "Bash(env:*)"],
      "deny": ["Edit", "Write", "NotebookEdit", "Bash(git push:*)", "Bash(git commit:*)",
               "Bash(git reset:*)", "Bash(git checkout:*)", "Bash(rm:*)", "Bash(touch:*)",
               "Bash(curl:*)", "Bash(wget:*)", "Bash(gh:*)"]
    }
  }
  ```

  A command that expanded a shell variable (`env PATH=...:$PATH ...`) still prompted
  despite the `env` allow rule. The same check with literal values
  (`env TLA2TOOLS=/abs/path/tla2tools.jar python3.11 -m unittest ...`) ran without one,
  so give Claude Code reviewers commands without variable expansion.
- The rules limit tools, not effects: an allowed interpreter can still write files, and
  the integrity check only reports drift afterwards.
- Write the settings file before the helper's last preparation step so the record's
  snapshot includes it, and delete it after the review; `remove` deletes only the
  helper's own profiles.
- Paseo started Claude Code from the nvm Node 24 installation, so its commands resolved
  Node 24 on the observed host, unlike Grok's login shell.
- Provider independence still applies: when the builder is a Claude model, a Claude Code
  reviewer is the same-provider fallback, not reviewer 1 or 2.
