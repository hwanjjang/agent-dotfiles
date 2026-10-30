# Client verification boundaries

Source packaging, client discovery and successful task execution are different
checks. The account installer delivers configuration only when explicitly applied;
MCP selections are opt-in and live connections require separate checks.

## Reviewer execution readiness — 2026-10-30

Probes ran on macOS through Paseo, in disposable review worktrees.

- **Codex CLI 0.163.0 (mode `auto`).** It ran the statechart TLC test with no approval
  after the review checkout received the [Codex recipe](../skills/sdlc/references/reviewer-execution.md#codex):
  local binding allowed, no outbound domains. `curl` to api.github.com was blocked.
  Without the recipe, the same test failed on the blocked local port.
- **Grok CLI 1.0.70.** It ran the allowed test without a prompt under auto-approve, and
  a project deny rule refused a denied command. This worked only after `grok --trust`
  recorded this repository; untrusted, Grok ignored the project rules. Its login shell
  resolved Node 20 before Node 24, so the TLC case skipped there.
- **Antigravity.** It offers only full access.

The [review workspace helper](../skills/sdlc/scripts/review_workspace.py) and its 15 tests
are part of the 76 passing SDLC script tests. The tests cover the review findings on its
first version: path escapes, symbolic links, removal outside the helper's own profiles,
integrity checked against files inside the checkout, ignored files, quoted and
Unicode-equivalent names, malformed records and manifests, and missing runtimes. Claude Code
as a reviewer, Linux hosts and other launchers were not exercised. See the
[decision](decisions/reviewer-execution.md).

## Grok and Antigravity with an installed account — 2026-10-22

Neither client is an installer target. Grok reads `~/.claude/skills`, `~/.claude/CLAUDE.md`
and the Claude hook file, so the skills and account instructions work there, but its
observe-only `SessionStart` drops the planning hook's context. Antigravity reads only its
own `.agents/` and `~/.gemini/config/` locations, so it sees none of the installed skills,
instructions or hooks until a `skills.json` entry and an `AGENTS.md` connect them. See the
[Grok and Antigravity record](verification/grok-antigravity.md).

## Account takeover from earlier managers — 2026-10-21

The installer now edits an instruction file that the client entries link to, accepts
repeated legacy receipts and refuses a planning route left by the earlier account
dispatcher. Exercised: unit and round-trip tests in disposable homes that replicate
the layout of an account managed by two earlier tools (shared symlinked instruction
file with two foreign blocks, old hook groups mixed with unrelated ones, old skill
directories and links), on Linux; the same preview, exact-plan apply, status, offline doctor and
rollback through `scripts/setup-account.sh`; and read-only previews of the real account
that reach a plan once every old fragment is named. Nothing was applied to the real account.
Not exercised: native Codex/Claude sessions after a takeover, hook trust in `/hooks`, model
behavior, Hermes plugin hooks and a case-insensitive file system such as the macOS default
(the installer matches its own trees ignoring case and Unicode normalization, but no run was made there). See the [takeover section](../account/README.md#take-over-an-account-managed-by-earlier-tools)
and the [walkthrough](manual/account-takeover.pdf).

## SDLC intake evidence - 2026-10-18

The [intake verification record](verification/sdlc-intake.md) documents bounded
native Claude runs for general requests, issues, PRs and reassessment, including
failures and model differences. Its [recipe](verification/verify-repository/features/sdlc-intake.md)
is separate from browser navigation and account installation checks. The
[integrated guide](manual/user-guide/README.md) explains invocation; neither that
guide nor these runs qualifies every client or an entire live tracker lifecycle.

## Collector capacity and boundary snapshots — 2026-10-18

The later [capacity qualification](../account/observation/capacity.md) executed
10,000 installed dispatcher subprocesses with four writers, verified all expected
records, preserved replay identity and recovered an interrupted reservation. It
passed capacity/recovery and the p95 under 50 ms target (48.16 ms observed) on one
PostToolUse-only reference-host run, excluding boundary probes. Before review
corrections, the prior version-2 run measured 48.04 ms; the version-1 candidate measured 64.71 ms; that
historical miss remains documented rather than being relabeled as a pass.
Two synthetic installed boundary probes also captured delivery snapshots; exact
effective exposure remains false. These results qualify their frozen collector
runtime and synthetic fixture, not a new native model run or all platforms.

## Native observation platform coverage — 2026-10-18

The [native qualification matrix](../account/observation/native.md#native-platform-evidence--2026-10-18)
is the single source of truth for per-platform results, source revisions, cleanup
and remaining gaps. Read its result and source boundary together: actual callbacks,
usable tools, authenticated model behavior and interruption are separate checks.
A historical native run does not requalify a later collector revision. The matrix
links both the offline Linux prerequisite check and a separate authenticated
Codex baseline/interruption at source `329dd76`, where Claude authentication was
unavailable. A later Ubuntu x86_64 run at `7ada8e2` authenticated both clients,
exercised normal/failure/interruption and one native child per client, and added
optional Paseo results. See the [source-bound execution record](decisions/linux-x86-native-qualification.md).
Native parent relationships were observed separately; collector actor/parent stay
null and child lifecycle delivery remains incomplete. The offline and container
mock checks remain distinct; cancellation does not prove process termination,
and no result qualifies later source changes.

The [historical Codex walkthrough](manual/codex-observation.pdf) retains its original
macOS/Linux captures. New platform status documentation supplements that evidence;
it does not rewrite the older receipts or imply WSL or child-scoped collector coverage.

## Doctor review corrections — 2026-10-18

The corrected doctor harness was exercised with actual Codex GPT-6-Luna and
Claude Haiku 5.5. Both bounded spec scenarios passed actual model identity,
installed-source use, exact CLI outcomes, input integrity and native planning
recovery checks. These fresh runs used the existing delivered bundle `ed1da039`;
they qualify the corrected harness against that installation, not a newly
installed candidate or every skill. No trust or permission settings changed.

The corrected harness also passed a disposable install → offline doctor →
uninstall journey delivering doctor PR commit `1df5ade`, with the target home
unchanged by diagnosis. PR #30 records the final candidate hashes, test results,
current-head delivery smoke and independent review. Historical evidence below
retains its original source and coverage limits.

## Account doctor and model scenarios — 2026-10-17

The historical runs in this section used delivered bundle `ed1da039` and a
pre-split doctor orchestrator. At the first doctor PR commit `1df5ade`, only
`account_native.py` and `account_model_check.py` were byte-identical to the final
historical runtime; this did not qualify that entire commit. Subsequent review
corrections change those modules too. Historical model results below therefore
remain evidence for their recorded source. Fresh corrected-harness results are
listed separately above. Current candidate checks and exact revisions are recorded in
[PR #30](https://github.com/hwanjjang/agent-dotfiles/pull/30).

The account verification recipe separates offline ownership,
native readiness and actual model behavior. Codex CLI 0.159.2 and Claude Code
2.1.285 each discovered all 23 installed skill names. Codex source paths matched
the owned bundle. Claude's native SessionStart event recovered a synthetic
selected plan with exit 0. Direct installed-command checks exercised all eight
registered routes, opt-out and refusal to recover a different plan.

A real Codex GPT-6-Luna task read the installed account entry point, four policies
and `to-spec`; successful native tool output established those reads. It returned
the fresh scenario marker and all four exact CLI examples, retained acceptance,
reported proposed tests as unexecuted and left the synthetic input/selected sources
unchanged. This bounded spec task passed; it is not all-skill or complete SDLC proof.

An optional local Paseo/Codex GPT-6-Luna task returned the same behavioral contract.
The first launch established a response but its CLI summary omitted full read
output. A revised task added exact installed-source readback; all six 180-character
prefixes matched, and inspected provider/model, input integrity and owned-resource
archival passed. The grader initially rejected an equivalent `bundle/` key prefix;
that harness gap was repaired without dropping content assertions, and the retained
live result was regraded without another model call. Paseo-created temporary
project registrations were also removed. This is summarized trace plus readback,
not a complete provider tool audit or remote/UI verification.

Claude's initial attempts hit the weekly quota; Haiku 5.5 also produced a CLI
recognition warning. A later authorized retry with the offered Haiku 4.5 model
completed after the quota reset. All six installed sources were read, the four
CLI examples and acceptance criteria passed, and the inputs remained unchanged.
The grader initially mistook Read's line-number prefixes for source content.
A failing regression reproduced that defect; presentation-prefix normalization
fixed it, and the then-current 22 doctor tests passed. The retained live evidence then passed
without another model request; the original failed grade remains private evidence.
Native discovery and SessionStart recovery also passed again. This verifies the
bounded `to-spec` scenario, not every skill or Claude through Paseo.

A subsequent user-requested Haiku 5.5 run also passed this native scenario.
Both initialization and actual usage identified `claude-haiku-5-5`; no recognition
warning, model substitution or permission denial occurred. Source reads, all four
CLI examples, input integrity, 23-skill discovery and SessionStart recovery passed.
The earlier recognition warning does not describe this later successful run.

Initially, seven owned Codex hooks were `modified` pending native `/hooks` review;
those earlier model checks did not override the readiness block. Subsequent
authorized activation and additional checks are recorded below.

Raw native/model outputs, prompts, local paths, quota messages and resource IDs
remain private. Public documentation retains sanitized observations and commands,
not account receipts. Native initializers can update caches/state; offline doctor
alone performs no account writes. Hermes, all lifecycle events, model adherence
on other tasks and remote MCP authentication remained unverified in these runs.
Regression and manual evidence for the PR candidate is separate; historical
sections below retain their original boundaries.

### Historical follow-up coverage — 2026-10-17

- **Codex hooks:** after explicit approval of the exact seven planning hooks and
  their persistent execution outside the sandbox, native `/hooks` trusted them.
  Codex 0.163.0 reported seven enabled/trusted definitions, no duplicates or pending
  reviews. A real GPT-6-Luna turn recovered the synthetic selected plan through
  the owned SessionStart hook. Other observed events included UserPromptSubmit,
  PreToolUse and Stop. Registration of all seven is verified; automatic execution
  of every lifecycle event is not claimed. No trust store editing or bypass occurred.
- **Paseo/Claude:** Haiku 5.5 passed the bounded spec scenario, inspected model ID,
  exact source readback, input integrity and owned-resource cleanup. The original
  180-character readback was inaccurate; a new run used exact first-eight-line
  readback suited to Claude's Read tool, preserving blank lines. Both attempts
  remain recorded. The native grader separately checks initialization and usage IDs.
- **Natural routing:** Codex GPT-6-Luna and Claude Haiku 5.5 each selected the
  installed spec/planning methods without skill names in the task. Both produced
  correct examples and a dependency-ordered plan covering acceptance criteria.
  Initial runs exposed response-shape failures. The maintained scenario now uses
  native structured output and recognizes successful Claude Skill injection with
  its exact owned body. Correct shape alone is insufficient; source use and behavior
  are independently graded. This is spec-to-plan coverage, not full SDLC execution.
- **Linux:** an isolated Linux aarch64 VM/container ran installer/doctor tests and
  the actual shell CLI lifecycle with all 23 skills: install, update to a changed
  committed revision, unchanged update and uninstall. Synthetic personal settings
  and the host-owned Paseo skill survived. This verifies Linux file/config delivery,
  not Linux Codex/Claude authentication or model execution. WSL was excluded because
  no target host was available; no Windows equivalence is inferred.
- **Playwright MCP:** the pinned template connected through Claude/Haiku 5.5,
  navigated a synthetic loopback page, returned its fresh marker from a browser
  snapshot and closed the browser. An optional unallowed find tool was denied,
  followed by successful allowed snapshot recovery. No persistent MCP settings
  changed. GitHub/Context7 live checks were excluded because credentials were absent.

The installer preview now lists exact hook definitions and hashes with execution
effects, so installation and native trust can be approved together. The installer
and doctor still do not grant trust. Automatic approval review initially rejected
bulk trust; explicit scoped user approval resolved that block before activation.

## Portable account installer — 2026-10-17

The installer is designed for macOS/Linux and WSL using Python 3.11+ and Git.
The maintained tests ran on macOS with Python 3.11; Linux/WSL execution and native
Windows are not verified here. The [account guide](../account/README.md) owns
commands and supported default client layouts.

Twenty-four disposable-account tests cover preview without mutation, destination-specific
paths, committed-source selection, revision updates and retired assets, idempotence,
removal, private backups and rollback, caught write failure, local drift and stale
approval, interrupted directory takeover/restoration with retry and later-edit
protection, source checkouts inside selected destinations, symlink rejection, narrow legacy
receipt transfer and unmatched-owner rejection, preserved Paseo/auth/personal settings, hooks opt-out and duplicate
routes, Codex instruction masking, MCP conflicts/disabled state and optional Hermes.
They do not use or change the contributor's real account, HOME or credentials.

A committed candidate snapshot with all 23 packages was installed in two isolated
accounts with different paths (including spaces). Each delivered Codex/Claude and
opt-in Hermes links plus all three MCP definitions. Both passed clean status, a
zero-change update, owned-content removal and rollback of that removal. Paseo and
personal guidance survived. This is two target directories on macOS, not two OSes. A clean receipt proves owned content, not native client trust, automatic
skill selection, instruction adherence, MCP authentication or task effectiveness.
Hermes native hooks/MCP, custom client profiles and client/tool installation are
outside this adapter. Historical source-only checks below retain their original
scope; they are not installation evidence.

The 24 installer tests, ten account-hook tests and 19 map tests pass (53 focused
checks). Both generated maps pass freshness checks. Isolated Chrome verified the
catalog and workflow interactions; the refreshed two-page account walkthrough
was rendered, text-checked and visually inspected. Public source/path probes and
changed Markdown links were checked. These checks do not activate a real account.

## Selective account source import — 2026-10-17

The collection now has 23 skills, ten policies and inactive account hook source
and templates. The [selection decision](decisions/account-source-import.md) compares
pstack, Matt and Addy and records rejected additions. The planning skill pin is
unchanged; its selected POSIX runtime files and license match pinned upstream
SHA-256 records. No private account settings or permission exceptions are imported.

Ten isolated account-hook tests pass with Python 3.11 and the system Python on macOS. They check
upstream hashes, template route validity, no-plan execution, selected-plan recovery
for both clients with space-containing paths, refusal to fall back from a broken
selector, opt-out, event-scoped project precedence, invocation matchers and invalid
inputs/routes. The review correction reproduced missing resume/clear/compact
recovery under a startup-only project registration in both clients before fixing
it. Tool/compaction filters and unsupported or missing matcher input are covered.
Tests use disposable delivery layouts and caches; HOME and real account settings
are not changed. These are direct script checks, not native client activation.

The 19 map tests and 56 SDLC state/reviewer regressions pass, and the SDLC skill
metadata validates. Generated catalog and workflow maps are current. Existing
browser scenarios passed in isolated Chrome after the content update. All six new
catalog entries and five new workflow nodes passed focused usage/source-link
checks; the workflow checks are in the maintained recipe. The overview and planning
hook detail capture were visually inspected for layout and readable content.

Not verified: account installation/rollback, effective native hook registration,
all lifecycle behavior in either client, Windows/Hermes/plugin deployment, MCP
authentication, live provider execution or comparative task effectiveness. A
synthetic plan recovery is not an end-to-end SDLC run. Preserve existing client
features until a separately authorized migration establishes replacement parity.

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

## Formal verification pair and repository pilot — 2026-10-22

The pstack formal verification pair brings the source total to 26. Both packages and
the repository-only verifier pass the strict skill validator with `name` and
`description` only. Their upstream SKILL.md hashes and LICENSE bytes match
cursor/plugins `190d287`; relative links in changed Markdown resolve, and declared
skill and policy dependencies exist. Neither package bundles or installs a verifier.
The map has 76 entries and 128 relationships; the 19 map tests, both freshness checks
and the 61 SDLC tests pass. The full repository suite ran 841 tests with one error,
`test_instruction_links_that_are_not_one_account_markdown_file_are_refused`, which
also fails on unchanged `origin/main` on the macOS case-insensitive filesystem.

The [account transaction verifier](verification/verify-account-transactions/SKILL.md)
ran with Python 3.11.15, OpenJDK 17.0.20 and TLA+ tools 1.7.4 (TLC 2.19) on macOS.
Each full run took about 21 s at first: the base model found 9,642 distinct states at
depth 30 with every action taken; seven witnesses were reached; five broken variants and
five paired code mutations each failed on their expected property; and the real-code
harness passed 206 cases, including 12 real process exits. Two runs gave identical
counts. PR review (Codex) found that the harness skipped directory-descriptor opens.
With every `os.open` injected, the harness runs 813 cases, including 27 real exits, in
about 39 s, and the full run takes about 49 s. No property is violated. In 18 cases a
rollback I/O error surfaces as `Unsafe parent for <path>` after the journal is marked
`rolling-back`; each retry restored every path. The runner now also requires TLC exit 0
for the base model and a non-zero exit (12) for every expected violation. A second review (Gemini) tightened
the lock assumption check and required every fault-free rollback to finish with the journal
`rolled-back` (`RecoveryCompletes`); a code copy without that final write fails it, and
expected case counts are now recorded. A third review (Grok) showed that the vacuity
check read the second coverage number; it now requires the first (distinct states) to be
non-zero for every action except the stutter step `Wait`. It also narrowed the stated scope
to one install-shaped transaction, and made commits touching covered files or changed
excluded helpers report out of sync.

During qualification, the step trace exposed a modeling error, not a code
bug: rollback walks the journal's sorted keys, unlike the undo. A scratch break in a
disposable worktree, journaling `rolled-back` after a failed undo, was reported out of
sync and produced 57 harness violations without a model change (603 with the broadened
harness). TLC failed the same
property after the model followed the code, while the existing account tests passed.
After the worktree was removed, a rerun matched the baseline.

A separate agent applied the maintenance skill in a disposable worktree after a
behavior-preserving rename of a covered function. It ran the check as is (out of
sync, model and harness still passing), read the two commits, updated only the model
reference and coverage record, showed with a break in a copy that the harness still
fails, and reported **updated** with no bug. That is one bounded forward check.

Archify finalize passed validation, delivery, strict provenance and browser checks
for the [lifecycle diagram](architecture/account-transaction-lifecycle.html); its
light 1440×900 capture was visually inspected. Not exercised: native discovery or
automatic selection of the pair in any client, other hosts, Linux, and CI execution
of the model. A follow-up ran the repository browser verifiers with an existing Playwright
installation and Chrome 155.0.8059.85: the catalog check passed, and the workflow check
passed all eight checks, including the formal pair and the account transaction verifier,
after its stale self-improvement expectations were matched to current catalog and workflow map text. Raw TLC
output, harness reports and captures stay local.

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

## Native observation qualification

The [Claude observation adapter](../account/observation/native.md) was exercised on
2026-10-18 with Claude Code 2.1.302 and actual Haiku 5.5, using installer-generated
disposable settings and existing authentication. All five callback types appeared
alongside planning recovery; six metadata records covered a successful Read and an
intentional Read failure. Stored records excluded input/output content, and owned
source files had no drift. Consent and the disposable installation were removed.
This does not establish a hermetic evaluation environment, complete callback
delivery, native Linux behavior, subagent identity or Codex/Paseo observation.
The [recipe](verification/verify-repository/features/native-observation.md) owns
repeatable checks and the [walkthrough](manual/native-observation.pdf) shows the
actual map and sanitized selected run results.

Record client/version, source identity, selected path, check and result, then name
what remains unverified. This is a check procedure, not a claim of installation,
automatic skill selection, MCP connectivity or complete orchestration.
