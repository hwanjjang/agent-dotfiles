# Source adoption and update records

The public source set contains selections from pstack, Matt Pocock, Addy Osmani,
Hermes method references, and AK-authored material supplied for public reuse. Private source addresses and
raw history are intentionally absent. Source-level private provenance is retained
locally; public AK packages use this repository's MIT license.

Per-skill `provenance.json` is the authority for origin, selected revision, imported
paths, local changes, dependencies, and validation limits. Public upstream imports
retain their license beside the skill. Required Addy checklists are included inside
the review package so a selected installation does not lose root-level resources.
Portable policies carry attribution and license information in their source.
`license_path` identifies the license in the upstream repository; the redistributed
license is always `skills/<name>/LICENSE`. Archify also retains third-party terms
in its `THIRD_PARTY_NOTICES.md`; the root MIT license does not replace those terms.

The [external tool registry](../../tools/registry.json) separately owns executable
and connection dependencies. Client MCP examples live under `mcp/claude-code/`;
these files are templates and are not activated by this checkout.

## Import decisions

- [Account source selection](../decisions/account-source-import.md): compare all
  three reference collections, retain small communication/execution policies and
  useful review continuity, and import only the existing planning pin's selected
  POSIX runtime. [Runtime provenance](../../account/hooks/planning-with-files/provenance.json)
  records exact source paths, hashes and license. No account installer, generic
  router, private settings or personal permission exceptions are imported.

- [Improvement experience selection](../decisions/improvement-experience.md): adapt
  Harness² (`1cfe254`, Apache-2.0) reflection and earlier-only retrieval methods as
  design rules for the account improvement loop. No Harness² code, prompts or
  runtime are imported; community validation is provisional.

- pstack: port investigation, candidate selection, architecture, and scoped workers;
  retain design resources. Replace Cursor-specific runtime assumptions with declared
  host capabilities. Carry evidence and behavioral-test principles as policies.
- Matt Pocock: bring the interview primitives and domain documentation as a dependency
  group. Bound consequential decisions, preserve existing authority, and document
  missing-dependency behavior. Retain supplied invocation metadata.
- Addy Osmani: bring planning and quality review. Make planning independently usable,
  keep task state isolated, and bundle review checklists. Review experiments use
  disposable workspaces; no review verdict grants publication authority.
- AK-authored source: import SDLC and issue-writing, plus architecture and security
  policies. Remove private links and project attribution; scope communication and
  publication authority to each task. Retain state scripts and their tests.
- Architecture policy: retain three minimum principles after source review and
  maintainer direction. Replace mandatory alternatives sections and dependency
  graphs with task-appropriate guidance; link pstack and Matt design material as
  optional references. This does not change the separate architect or SDLC workflows.
- Required diagram production: include Archify at the selected release with its
  runtime, schemas, templates, and third-party notices. The package moved from the
  3.0.1 baseline to v3.2.0 on 2026-10-21; see the Archify update record below.
- Required screenshot manuals: include a focused source/PNG/PDF workflow with a
  reproducible generator, raster preview, and mandatory visual inspection.
- Logging policy: combine Addy's severity and structured-event guidance with
  Matt's targeted temporary probes and cleanup. The [policy](../../policies/logging.md)
  owns pinned sources, license notices, local adaptations, and runtime verification
  expectations. This imports the selected guidance without requiring both complete
  upstream workflows or claiming individual-skill popularity from collection stars.

The AK source's common MCP list was empty. The three initial connection templates
therefore come from provider documentation, not an inferred private configuration.
Account setup scripts, personal host hooks/settings, project history, raw captures,
and unrelated integration configuration are outside this initial portable import.
Graft and other optional toolchains are deferred to keep the requested minimum.

The [issue workflow policy](../../policies/issue-workflow.md) consolidates common
issue lifecycle rules consumed by issue-writing and SDLC. It owns pinned source
attribution and MIT notices. Its [decision note](../decisions/issue-workflow.md)
records fit, adaptations and limited community evidence. This is a local synthesis
of selected guidance, not installation of the three upstream orchestration stacks.
Affected skill provenance declares the shared policy dependencies; distribution
must preserve their links. Tracker execution remains unverified. Codex source discovery is recorded in
[client verification](../client-verification.md); no account installation is claimed.

The three focused additions and their SDLC integration are described in the
[adoption decision](../decisions/skill-integration.md). Their provenance records
pin upstream source and distinguish local extensions from original methods.
The single tdd method replaces duplicated method prose; SDLC retains executable
evidence validation, additional smoke and existing authority gates.

The [verification pair](../decisions/verification.md) adopts pstack generation and
maintenance with all feature-map examples and MIT notices. Local adaptations
remove hardcoded client paths and implied publication, preserve requested coverage
and distinguish product defects from documentation drift. Optional tooling stays
a reference; no additional MCP server is enabled.

The [formal verification pair](../decisions/formal-verification.md) adopts pstack's
beta create/maintain methods at `190d287` with their MIT notice. Local adaptations
allow model invocation only for explicit requests, keep toolchain installs,
product-source harnesses and scratch breaks within task authority, and label
generated-input fallbacks as bounded testing. Setup offers, guide text and the Claude
harness adapter line are not imported. Community validation is provisional.
On 2026-10-30 the create method moved to `1ba91fc` (pstack 0.15.36) for one change:
generated verify skills read TLA+ results with statechart.

The [statechart adoption](../decisions/statechart.md) vendors pstack's runtime payload
at `1ba91fc` unchanged, with its MIT notice and per-file digests; the upstream test
corpus is not vendored. The author announced it as stable; community validation is
provisional. The same revision supplies arena's cross-family judge rule and the
evidence policy's measured-number recommendation from `principle-explain-the-number`.

The [PR/ticket adoption](../decisions/pr-workflow.md) combines pstack PR planning,
Matt's ticket adapter and the original Cursor Team Kit review-preparation skill
discovered through Denyer's port. It extends the existing Addy planning package,
retains one body authority, and makes source-commitment coverage explicit.
Per-package provenance lists additional pinned method sources and their hashes.
No stack runtime, setup skill, MCP or fixed tracker vocabulary is introduced.

The [spec extraction](../decisions/spec-extraction.md) combines Matt's focused
`to-spec` synthesis with the existing AK specification contract. The spec method
and content checklist moved into one standalone skill; SDLC now links to it.
Automatic issue publication, fixed labels and exhaustive story templates were
not adopted. Current discovery and behavioral limits remain separately recorded.

The [account-content preservation decision](../decisions/account-content-preservation.md)
adds a portable Hermes-derived citation helper and narrowly adapts document/meeting
extraction and feasibility experiments into existing owners. Affected packages
retain selected revisions, hashes and MIT notices, including secondary Hermes/GSD
attribution. Community effectiveness remains provisional.

## Update procedure

1. Inspect the pinned origin and local adaptations before selecting a new revision.
2. Fetch into ignored local staging. Review the upstream delta, license, dependencies,
   client requirements, and permission or output changes.
3. When the upstream has an [author channel](#author-channels-on-x), read the
   author's posts from the delta period and the replies to them.
4. Reapply only adaptations still needed. Preserve method coverage, invocation
   behavior, and resource closure; do not overwrite the local package blindly.
5. Run relevant syntax, resource, executable, and behavioral checks. Record which
   client-level or authenticated checks were actually performed.
6. Update provenance and the map in the same change. Review all public content for
   private links and values before an authorized commit.

### Author channels on X

These authors announce releases and explain changes on X. Each account was checked
on 2026-11-13 against the social link on the author's GitHub profile.

| Upstream | Author account | Also confirmed by |
| --- | --- | --- |
| [pstack](https://github.com/cursor/plugins/tree/main/pstack) | [@poteto](https://x.com/poteto) | The plugin manifest names Lauren Tan as author, and the GitHub account `poteto` that links this X account authors the pstack commits |
| [mattpocock/skills](https://github.com/mattpocock/skills) | [@mattpocockuk](https://x.com/mattpocockuk) | Its profile links aihero.dev, the site on the GitHub profile, and it posts links to the repository |
| [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) | [@addyosmani](https://x.com/addyosmani) | Its profile links addyosmani.com, which links back to the account |

- Use the author's posts for release context and the stated reason for a change.
  They are author statements, not independent community evidence.
- Replies and quote posts can contain firsthand reports. Evaluate them with the
  [community-evidence rules](../../AGENTS.md#external-research-is-part-of-this-project).
- Commits, pull requests and changelogs remain the record of what changed. A post
  does not replace the delta review in step 2.
- X can require sign-in. Record the URL and date of each post you read, and state
  which posts or replies could not be read.

Source presence, structural validation, executable checks, and real client behavior
are separate claims. No account installation, external publication, or complete
SDLC behavioral evaluation was performed by this import.

## Archify update — 2026-10-21

AK selected the update from the 3.0.1 baseline (`d5a1333`) to the published v3.2.0
release (`208acba8d412335185b2056fedf54b3405df43fb`, tree `39069dd`). The skill's
[provenance.json](../../skills/archify/provenance.json) owns the exact identity,
packaging changes and validation; the [tool registry](../../tools/registry.json) and
the catalog entry carry the same pin, and `tests/test_archify_vendored.py` checks that
they agree.

- **Included changes.** Ten diagram types (ERD, class, tree, timeline and waterfall
  join the original five), reader-controlled Live/Still motion built into every diagram
  (a new page starts Still until the reader chooses Live), bundled viewer locales, and
  one-page explainer pages whose charts use unmodified Pele 1.3.0 chunks (MIT). The
  package no longer ships its own tests.
- **Local changes.** None to upstream text or code. Trailing whitespace was normalized
  in 17 text files for repository diff checks. provenance.json lists the normalization and
  the digest of every vendored file, and the test fails on an edit that is not recorded.
- **Behavior to know.** `finalize` and `deliver` make a bounded request (1 second,
  cached for 24 hours) to the project's update manifest and report it in the receipt;
  `ARCHIFY_UPDATE_CHECK_DISABLED=1` removes the check. Since 3.2 the skill lets the agent
  describe the manifest's summary of at most 160 characters and tells it to treat that
  text as untrusted data; it never installs or runs an update. Do not update an
  installed copy in place: it is owned by the account installer, and an edit blocks the
  next update. After an explainer made on request the skill may offer a proactive mode and
  edits a global rules file only if the user accepts.
- **Community evidence.** Limited. Independent first-hand reports were not found; web
  searches returned aggregator pages, release notes and the project's own pages. One
  critical article (braindetox.kr, 2026-09-30) assesses the 3.0.1 documentation, not
  tested results, and says the automated gates check form, not truth. The upstream issues
  read on 2026-10-21 include open viewer, timeline/waterfall, explainer chart and Windows
  reports, and none about the architecture or workflow `finalize` path on Linux. The
  selection is provisional with respect to community validation.
- **Checks.** The payload equals the upstream tree at the pinned revision except the
  whitespace-only files. On Linux with Node.js 22 and a Chromium browser, `doctor` passes,
  every bundled example of the ten types validates, and `finalize` passed its validate,
  deliver, check and browser-check gates for the architecture example and for the
  explainer example with `--browser-check`. Not exercised: Windows, macOS, a model-driven
  session and perceptual review of generated pages.
- **Rollback.** Restore `skills/archify` and the pins from the repository commit before this
  update; its provenance record names upstream `d5a1333`.

## Upstream check — 2026-11-13

The three reference collections were compared with the previous check of 2026-10-30
(recorded in the [statechart decision](../decisions/statechart.md)). Per-skill
provenance owns the selected revisions; this record says what was inspected and decided.

| Upstream | Head at the previous check | Head inspected | Change to adopted paths |
| --- | --- | --- | --- |
| [cursor/plugins](https://github.com/cursor/plugins) (pstack) | `1ba91fc` (0.15.36) | `ec56937` (2026-11-12) | None. No commit touches `pstack/` or `cursor-team-kit/`; the version is still 0.15.36. |
| [mattpocock/skills](https://github.com/mattpocock/skills) | `a496f55` (1.3.2) | `5863806` (2026-11-12) | None since the previous check. Against the `49dd158` pin, `grilling` gained "with a fresh context window" ([#1341](https://github.com/mattpocock/skills/pull/1341)). |
| [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) | `eb07f19` (0.6.14) | `301b02b` (2026-11-01, 0.6.15) | Three files of the vendored review package. |

- **Adopted.** [code-review-and-quality](../../skills/code-review-and-quality/SKILL.md)
  moves from `aeac41d` to `301b02b`. Between those revisions the three vendored files
  change in exactly three ways, and all three are taken with the local adaptations kept.
  The staged-secret check lists the names of matching files instead of printing the
  matching lines, which contained the secret value
  ([#718](https://github.com/addyosmani/agent-skills/pull/718)); it is a keyword
  check, and no output does not prove that no secret is staged. Step 4 tells the
  reviewer to check a finding against callers, guards and tests, to label defects
  already in the base separately from regressions, and that zero findings is a valid
  result ([#736](https://github.com/addyosmani/agent-skills/pull/736)). The
  performance examples use `http://localhost` for Lighthouse and alias the second
  `onINP` import, which did not parse as one module.
- **Checks.** `tests/test_review_checklists.py` runs the staged-secret command in a
  temporary repository, parses the web-vitals snippet with `node --check` and checks
  the Lighthouse target; all four checks failed before the update. #736 reports no
  graded behavioral run. A first pass here ran fresh Claude Sonnet reviewers on two
  fixtures adapted from the upstream eval fixture, with the expected behavior removed
  from the prompt: one run per variant on a regression and on a behavior-neutral change.
  Both variants reported the regression and labelled the base defect. On the neutral
  change the earlier text returned "request changes" for the base defect and the new
  text reported it separately and approved. That is one run per cell on one model, so
  the effect is provisional; the pull request records the repeat on the final files.
- **Not adopted.** Matt's in-progress `software-factory` and `chief-of-staff` changes;
  Matt's fresh-context wording, because the local `grilling` sentence is already
  host-neutral (a wider fresh-context rule for delegation, raised in the 2026-10-30
  review, is undecided); unmerged pstack proposals such as Codex packaging
  ([#1143](https://github.com/cursor/plugins/pull/1143)) and Veil
  ([#1189](https://github.com/cursor/plugins/pull/1189)); and Addy changes to skills
  that are not vendored here.
- **Held.** Changes to `grilling` for stable question numbers and partly answered
  rounds wait for a local evaluation. Upstream reports:
  [#1406](https://github.com/mattpocock/skills/issues/1406),
  [#1386](https://github.com/mattpocock/skills/issues/1386),
  [#1411](https://github.com/mattpocock/skills/issues/1411).
- **Proposed separately.** Recording upstream statechart reports as known limits, and a
  local `domain-modeling` rule to reuse an existing glossary location.

Community evidence for this period is limited and mixed, so the selection is
provisional with respect to community validation.

| Source and date | Context and finding | Limit |
| --- | --- | --- |
| Hacker News comments [50431407](https://news.ycombinator.com/item?id=50431407), [50420665](https://news.ycombinator.com/item?id=50420665), [50374679](https://news.ycombinator.com/item?id=50374679), [50364147](https://news.ycombinator.com/item?id=50364147), [50330866](https://news.ycombinator.com/item?id=50330866), 2026-11-01 to 2026-11-09 | Four users in five comments name Matt's skills as the base of their workflow (grill-with-docs, wayfinder; Claude Code, OpenCode and a local model). | Short mentions without measurements. |
| Hacker News comment [50378737](https://news.ycombinator.com/item?id=50378737), 2026-11-05 | One user runs an adapted poteto-mode with multi-model subagents and reports end-to-end features. | The comment also presents the user's own harness. |
| mattpocock/skills issues [#1406](https://github.com/mattpocock/skills/issues/1406), [#1386](https://github.com/mattpocock/skills/issues/1386), [#1381](https://github.com/mattpocock/skills/issues/1381), 2026-11-03 to 2026-11-09 | Firsthand grilling reports: a partly answered round treated as finished and questions renumbered; 19 sessions with a median of 15 equally weighted questions; decisions started before the goal was established. | Different problems, not one repeated report; #1381 comes from a ChatGPT session, not a coding harness. No maintainer decision. |
| cursor/plugins issues [#1176](https://github.com/cursor/plugins/issues/1176), [#1178](https://github.com/cursor/plugins/issues/1178), 2026-11-05 | One user's benchmark: mandatory delegation spawned no subagents on Claude Code and 181 to 208 per run on Codex at about 20 times the cost. | Single reporter, closed by the reporter as misfiled; no artifacts. Consistent with not importing the orchestrator. |
| addyosmani/agent-skills issues [#776](https://github.com/addyosmani/agent-skills/issues/776), [#781](https://github.com/addyosmani/agent-skills/issues/781), 2026-11-06 to 2026-11-10 | `/build auto` does not enter auto mode on one host; artifact locations differ between worktrees. | Not about the review package. No independent report on #718 or #736 was found. |

Not read: Reddit (the search tool cannot reach it and the site asked for human
verification), the authors' X posts for this period (the X search agent was over its
usage limit) and X replies. Step 3 of the update procedure was therefore not performed
for this check.

## Source-package limitations

- Archify's bundled `package.json` retains upstream monorepo commands that refer to
  sibling `scripts/` and `viewer/` directories absent here, and the package no longer
  ships its tests. Do not use its npm scripts as this checkout's validation command.
  The checked portable entry is `node skills/archify/bin/archify.mjs doctor`, together
  with `tests/test_archify_vendored.py` and the finalize runs listed in the update record.
- The imported AK SDLC still uses `AK` as the authorizer label for reviewer-effort
  overrides and retains historical repository-layout examples in its playbook.
  It is an AK workflow building block, not a fully generalized principal/host adapter.
  Apply the destination project's actual instructions and layout. No historical
  source sentence creates publication authority for a new user or repository.
