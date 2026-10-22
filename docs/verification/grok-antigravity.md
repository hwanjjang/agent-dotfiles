# Grok and Antigravity with an installed account — 2026-10-22

Codex, Claude Code and an opted-in Hermes are the installer's clients. This record
checks what two other installed CLIs pick up from an account set up by
`scripts/setup-account.sh` at `4130e05`, without changing the installer. It is a
bounded observation on one Linux host, not support for either client.

## Method

- Clients: Grok CLI 1.0.62 (model `grok-4.7`) and Antigravity CLI `agy` 1.4.4
  (default model Gemini 3.8 Flash, high).
- Behavior claims come from the documentation each CLI ships with that version:
  Grok's `~/.grok/README.md` and its hooks guide, and Antigravity's built-in
  `agy-customizations` skill with its rules, skills, JSON-configuration and hooks guides.
- Discovery was read with `grok inspect`. Behavior was read from headless sessions in
  throwaway Git repositories with read-only tools or no tools, and from Grok's debug
  log of which hooks ran.
- The installed account was not changed. Probe repositories, logs and a Grok
  folder-trust entry the probe added were removed afterwards.

## Grok

| Surface | Result |
|---|---|
| Skills | Grok reads `~/.claude/skills`, so all 24 installed skills are listed. A session loaded `sdlc` and quoted its first heading, and listed `planning-with-files`. |
| Account instructions | `~/.claude/CLAUDE.md` is loaded as a global rule. A session found and read the delivered `account/instructions.md`. |
| MCP | Registrations in `~/.claude.json` are loaded. |
| Hooks | Grok runs the hooks in `~/.claude/settings.json` without a trust step. The installer's planning `SessionStart` hook does not take effect; see below. |

The planning `SessionStart` hook has two blockers in Grok:

1. Its matcher is Claude's `startup|resume|clear|compact`. Grok tests `new` or `load`
   for `SessionStart`, so the hook never ran in the debug log.
2. A copy of the same command with the matcher `new|load`, placed in a trusted probe
   repository, ran to completion, but the plan it printed did not reach the model.
   Grok's hooks guide treats `SessionStart` as observe-only: it reads only a top-level
   `systemMessage` and drops `additionalContext`. It also drops an allowing
   `UserPromptSubmit` hook's context.

Changing the matcher therefore would not restore automatic planning recovery in Grok.
Invoke `/planning-with-files` instead. Grok also logs that the hook's `statusMessage`
field is unsupported and runs the hook without it. The field is used by the Codex
hook, so it is harmless.

## Antigravity

| Surface | Result |
|---|---|
| Skills | Only the two built-in skills are visible. Antigravity does not read `~/.agents/skills`, `~/.claude/skills` or `~/.gemini/skills`. |
| Account instructions | None. Antigravity does not read `~/.claude/CLAUDE.md` or `~/.agents/AGENTS.md`. |
| Hooks | None. Antigravity reads its own `hooks.json`, not Claude or Codex hook files. |

Antigravity discovers customizations in a project `.agents/` directory, from the
working directory up to the repository root, and globally in `~/.gemini/config/`.
Rules come from `GEMINI.md` or `AGENTS.md` in those directories. Other skill
locations are declared in a `skills.json` file. A throwaway repository tested that wiring:

- An `AGENTS.md` holding the installed instruction block was loaded as a rule.
- A `.agents/skills.json` entry for the delivered bundle
  (`~/.agents/agent-dotfiles/bundle/skills`) exposed all 18 model-invoked skills,
  including `sdlc` and `planning-with-files`. The six user-invoked skills
  (`disable-model-invocation: true`) stay out of the model's list, as intended.
- An entry for `~/.agents/skills`, a directory of skill links, exposed nothing. A skill
  link placed directly in `.agents/skills/` was discovered.

Antigravity hooks use their own schema. A `SessionStart` handler must print
`injectSteps` with a `systemMessage`. The installed planning hook prints the Claude and
Codex shape, so automatic planning recovery would need a separate output adapter.

## Not covered and next steps

- The global equivalents (`~/.gemini/config/skills.json` and a global rules file) were
  not exercised. The bundled guide does not name the global rules file, so that needs a
  native check before the installer writes one.
- No task-level behavior, model comparison, macOS run or MCP connection was tested.
- Supporting either client would be a new opt-in installer target with its own receipt,
  rollback and native checks, like Hermes. For Antigravity that means a `skills.json`
  entry for the bundle and an instruction entry point. Planning recovery in Grok is not
  possible through its current hook contract.
