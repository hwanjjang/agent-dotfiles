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

The verification pair brought the source total to 20 at that adoption. Their metadata and the
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

## PR and ticket adoption — 2026-10-17

The PR/ticket pair brought the source total to 22 at that adoption. Strict skill validation passed
for `to-tickets`, `make-pr-easy-to-review`, the changed planning skill and the SDLC
entry point. Local links, declared skill/policy dependencies, pinned upstream
hashes and license notices were checked. These packages have not been tested
through native client discovery or authenticated tracker/PR operations.

At that adoption, the generated map contained 51 entries and 76 relationships.
Its six regression tests and freshness check passed. The browser verifier passed again
with Playwright 1.64.1 and Chrome 155.0.8059.82. A focused browser check also searched
and opened all four new entries, checked usage/source links and cleared the search.
Both new skill detail captures were visually inspected; the isolated browsers
closed. Map checks do not establish skill execution or MCP connectivity.

One independent agent applied the skills to three synthetic requests and produced
local artifacts: incomplete export tickets plus independent log cleanup, a fork PR
body/commit recommendation, and recovery after an uncertain issue-creation result.
Artifact inspection confirmed retained IDs and connector ownership, separate task
and PR graphs, destination-template use, qualified evidence and no blind creation
retry. Unresolved product semantics and unavailable live Git/tracker access stayed
explicit. No maintained source corrections were needed from this check. A subsequent
maintainer-requested deduplication replaced repeated rules with links to their
existing authorities; strict metadata, links and source review were repeated,
but the model scenario evaluation was not rerun for that wording revision.

This was bounded simulated application, not a benchmark or native invocation.
Actual history reordering/splitting, per-merge-unit execution, tree equivalence,
remote leases, tracker publication and full SDLC orchestration were not exercised.
No account installation, external publication or live ref mutation occurred.

## Standalone specification — 2026-10-17

`to-spec` brings the source total to 23. Its metadata and the SDLC entry point
pass the strict skill validator. The extracted content contract replaces the
SDLC spec checklist in the stage template and normative gate; the handoff and
routing link to it. Source hashes, license bytes, relative links and declared
policy/skill dependencies were checked. State scripts and receipt schemas did
not change; earlier state tests are historical evidence, not a new execution.

The map now contains 53 entries and 83 relationships. Six generator tests and
freshness passed. The existing repository verifier passed with Playwright 1.64.1
and Chrome 155.0.8059.82; a focused check covered both added entries' search,
usage, type/status filtering, source links and search recovery. The skill screenshot
was visually inspected and isolated browsers closed. These checks do not establish
native skill discovery, automatic selection, tracker access or a full SDLC run.

A separate agent applied `to-spec` to two synthetic requests without reading the
research or decision note. It updated an existing fixture spec in place, retaining
acceptance IDs and an operational note while adding the agreed date-filter change.
It distinguished inspected source from reported behavior and left missing date
contracts explicit. The second request produced an inline-only incomplete draft;
it preserved the undecided recipient policy instead of inventing implementation
readiness. No source code, tracker or SDLC state was changed. Parent inspection
confirmed the fixture source/README hashes and reviewed the actual artifacts.

This is a bounded forward check, not a general model benchmark. The evaluator
noted that the threshold between asking and delivering a qualified draft still
requires task judgment; both supplied requests allowed useful drafting with
explicit gaps. No correction was needed from these cases. Full orchestrator
execution, native discovery and external publication remain unverified.

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
