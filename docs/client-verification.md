# Client verification boundaries

Source packaging, client discovery and successful task execution are different
checks. This collection does not install account configuration or enable servers.

## Observed checks — 2026-10-17

- All 18 source packages were discovered by the installed Codex CLI 0.159.2 app-server through
  `skills/list` in a temporary project's `.agents/skills/` directory, with zero
  source-package discovery errors. The temporary copies were removed afterwards.
  No model turn, hook activation or persistent skill installation was performed.
- An extra-user-root request did not discover these packages on that installed
  version; project-local discovery did. Do not assume a current documentation
  feature is present in every installed client.
- New tdd, diagnosing-bugs and writing-for-agents metadata and the changed SDLC
  entry point pass the strict skill-creator validator. Older packages retain
  upstream metadata extensions; successful Codex discovery does not establish
  matching hook or invocation semantics in all clients.
- SDLC evidence-mode regression tests cover default TDD, explicit alternatives,
  no-refactor reuse, stale/failed evidence and separate smoke requirements.
  Structural checks cannot judge whether an agent's assertions are true.
- Claude Code MCP templates have JSON/source inspection only. Remote GitHub and
  Context7 authentication and an actual Playwright MCP browser session remain
  unverified. Existing direct browser checks are not MCP connection evidence.

Reference: [Codex app-server skill discovery](https://learn.chatgpt.com/docs/app-server).

## Scoped adoption checks

For a selected client and authorized installation, preserve existing settings and
duplicate-name overrides. Place the selected skill dependency closure in its
supported discovery location. Preserve shared-policy relative references too:
these source packages are not standalone folders when provenance declares policy
dependencies. Verify the discovered path matches the intended copy, then exercise
one bounded task and inspect the actual artifact. Never infer the selected version
from the skill name alone.

For the SDLC routing contract, check a small bug fix, a clarified feature plan,
an unavailable design provider, and two conflicting implementation slices. Verify
task scope, actual provider identity, one integration writer, meaningful tests and
honest missing-capability reports. Do not claim three-provider or parallel execution
from a sequential rehearsal. These target-host executions have not been performed.

For MCP, use the [template verification layers](../mcp/README.md): configuration
discovery, authentication, actual tool listing, and one scoped operation. Keep
credentials local and record only sanitized results. GitHub's current profile is
read-only; use the registered `gh` tool for authorized writes or separately select
a suitable write profile. Do not remove the read-only header just to make a test
pass. Playwright checks should use an isolated synthetic page and disposable state.

Record client/version, source identity, selected path, check and result, then name
what remains unverified. This is a check procedure, not a claim of installation,
automatic skill selection, MCP connectivity or complete orchestration.
