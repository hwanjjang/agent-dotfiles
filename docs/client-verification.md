# Client verification boundaries

Source packaging, client discovery and successful task execution are different
checks. This collection does not install account configuration or enable servers.

## Observed checks — 2026-10-17

- The initial 18 source packages were discovered by the installed Codex CLI 0.159.2 app-server through
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

## Verification pair and repository pilot — 2026-10-17

Two added portable packages bring the source total to 20. Their metadata and the
repository-only verifier pass the strict skill validator. The new pair has not
been exercised through native client discovery or independently measured for
model adherence; the earlier 18-package discovery result does not cover it.

The repository verifier was executed with Playwright 1.64.1 and isolated Chrome
155.0.8059.82: map freshness, search/no-results/recovery and usage/source links
passed. Captures were visually inspected; the browser closed and evidence survived.
A deliberately broken recovery in an isolated source-consistent fixture produced
a failed search scenario and not-run downstream scenario, with browser cleanup.
An unavailable browser failed qualification; an existing evidence directory was
refused without overwriting its report. Six map tests cover source validation and
stale/missing generated output rejection without mutation. The 52 SDLC tests remain
green. These are scoped checks, not all-feature, MCP or account-installation proof.

A separate read-only agent applied the maintenance skill to source and existing
evidence under an explicit no-browser limit. It preserved audit-only authority,
reported live coverage blocked and identified harness reporting/assertion gaps
that were corrected. This is one bounded forward check, not a benchmark or proof
that every client/model follows the skills. Raw runs stay local; maintained recipes
and the [adoption decision](decisions/verification.md) document the reusable method.

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
